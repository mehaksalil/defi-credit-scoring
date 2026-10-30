"""
FastAPI app entrypoint.
Endpoints for wallet score, health, on-chain oracle sync, and a local faucet.
"""
import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, ORACLE_API_KEY
from app.services import oracle
from app.services.blockchain_data import get_transactions
from app.services.credit_model import get_credit_score_for_wallet
from app.services.fraud_model import get_fraud_for_wallet
from app.services.fraud_model_kaggle import get_kaggle_fraud_for_wallet
from app.services.features import FEATURE_NAMES, compute_features
from app.services.lending_history import LendingHistoryError, get_lending_history
from app.services.lending_features import LENDING_FEATURE_NAMES, compute_lending_features
from app.services.lending_scoring import compute_lending_behavior_score
from app.services.combined_scoring import combine_credit_scores

app = FastAPI(
    title="DeFi Credit Scoring API",
    description="AI-based credit score and fraud detection for wallet addresses",
    version="0.1.0",
)

# CORS: allow the local Vite frontend (http://localhost:3000 by default) to call
# this API. Configure allowed origins via CORS_ORIGINS in backend/.env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


COMBINED_BEHAVIORAL_WEIGHT = 0.70
COMBINED_LENDING_WEIGHT = 0.30


def _get_lending_score_and_composite(address: str, behavioral_score: float):
    """Return verified lending history, lending index, and provisional composite."""
    history = get_lending_history(address)
    features = compute_lending_features(history)
    lending_score = compute_lending_behavior_score(features)
    composite = combine_credit_scores(
        behavioral_score=float(behavioral_score),
        lending_behavior_score=lending_score.get("lending_behavior_score"),
    )
    return history, lending_score, composite


def require_oracle_key(x_oracle_key: str | None = Header(default=None)):
    """
    DEMO-GRADE protection for the endpoints that spend the oracle's on-chain
    authority (writing credit data, minting test tokens). Compares a static
    shared secret from backend/.env (ORACLE_API_KEY) against an X-Oracle-Key
    request header.

    This is NOT real authentication or authorization. It has no rate limiting,
    no per-caller identity, and no rotation. It only exists so the endpoints
    aren't wide open to anyone who can reach the API. For anything beyond a
    local sandbox, replace this with a real auth layer.
    """
    if not ORACLE_API_KEY:
        # No key configured: block by default rather than silently allowing
        # anyone to trigger on-chain writes.
        raise HTTPException(
            status_code=503,
            detail=(
                "Oracle endpoints are disabled: ORACLE_API_KEY is not set in "
                "backend/.env. Set it to any local secret to enable this endpoint."
            ),
        )
    if x_oracle_key != ORACLE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Oracle-Key header")


@app.get("/")
def root():
    """Root: links to docs and health."""
    return {
        "message": "DeFi Credit Scoring API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    """Health check for deployment and scripts."""
    return {"status": "ok"}


@app.get("/wallet/{address}/transactions")
def wallet_transactions(address: str, use_cache: bool = True):
    """
    Step 2: Fetch and return normalized transaction data for a wallet.
    address: Ethereum address (0x...).
    use_cache: If True, use cached file when available to avoid re-calling Etherscan.
    """
    try:
        df = get_transactions(address, use_cache=use_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    # Return as list of dicts for JSON; omit DataFrame index
    return {
        "address": address,
        "count": len(df),
        "transactions": df.to_dict(orient="records") if len(df) > 0 else [],
    }


@app.get("/wallet/{address}/features")
def wallet_features(address: str, use_cache: bool = True):
    """
    Step 3: Get feature vector for a wallet (from its transaction history).
    address: Ethereum address (0x...).
    use_cache: If True, use cached transactions when available.
    """
    try:
        df = get_transactions(address, use_cache=use_cache)
        features = compute_features(df, address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    # Convert to JSON-serializable dict (numpy scalars -> Python float)
    feature_dict = {}
    for k, v in features.items():
        if isinstance(v, (np.floating, np.integer)):
            feature_dict[k] = float(v)
        elif isinstance(v, (int, float)):
            feature_dict[k] = v
        else:
            feature_dict[k] = v
    return {
        "address": address,
        "features": feature_dict,
        "feature_names": FEATURE_NAMES,
    }


@app.get("/wallet/{address}/score")
def wallet_score(address: str, use_cache: bool = True):
    """
    Behavioral credit score (0–100) and risk level for a wallet.
    For the historical-data model, run train_behavioral_credit_model.py.
    """
    try:
        result = get_credit_score_for_wallet(address, use_cache=use_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Credit model not trained. Run: python train_behavioral_credit_model.py",
        )
    return result


@app.get("/wallet/{address}/fraud")
def wallet_fraud(address: str, use_cache: bool = True):
    """
    Step 5: Get fraud probability (0–1) and is_fraud flag for a wallet.
    Requires a trained fraud model; run train_credit_model.py (trains both models).
    """
    try:
        result = get_fraud_for_wallet(address, use_cache=use_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Fraud model not trained. Run: python train_credit_model.py",
        )
    return result


@app.get("/wallet/{address}/fraud-v2-experimental")
def wallet_fraud_v2(address: str, use_cache: bool = True):
    """
    EXPERIMENTAL. Kaggle-trained RandomForest fraud classifier (47 features,
    real labels, 0.999 ROC-AUC on the held-out Kaggle CSV) applied to live
    Etherscan data. Several input features are approximations or unvalidated
    against live data -- see app/services/features_v2.py's module docstring
    for exactly which ones and why, before trusting this over /fraud.
    """
    try:
        result = get_kaggle_fraud_for_wallet(address, use_cache=use_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Kaggle fraud model not found in backend/models/.",
        )
    return result


@app.get("/wallet/{address}/report")
def wallet_report(address: str, use_cache: bool = True):
    """
    Complete wallet risk report.

    Uses:
    - behavioral model for wallet behavior score
    - Kaggle-trained Random Forest for supervised fraud probability

    The behavioral score and fraud probability are kept separate because
    they measure different things.
    """
    try:
        df = get_transactions(address, use_cache=use_cache)
        tx_count = len(df)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Behavioral score
    try:
        credit = get_credit_score_for_wallet(
            address,
            use_cache=use_cache
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if credit is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Behavioral model not trained. "
                "Run: python train_behavioral_credit_model.py"
            ),
        )

    # NEW: Kaggle supervised fraud classifier
    try:
        fraud = get_kaggle_fraud_for_wallet(
            address,
            use_cache=use_cache
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if fraud is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Kaggle fraud model not found. "
                "Make sure fraud_detection_rf_kaggle.joblib "
                "and its feature files exist in backend/models/."
            ),
        )

    # Derive a separate lending index from verified local LendingPool events.
    # The current Isolation Forest score remains visible as its own component.
    try:
        _history, lending, composite = _get_lending_score_and_composite(
            address, behavioral_score=float(credit["score"])
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LendingHistoryError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "address": address,
        "tx_count": tx_count,

        # Primary displayed score: provisional, transparent composite.
        "score": composite["combined_credit_score"],
        "risk_level": composite["combined_risk_level"],
        "score_type": composite["score_type"],
        "combined_credit_score": composite["combined_credit_score"],
        "combined_risk_level": composite["combined_risk_level"],
        "combined_score_weights": composite["weights"],
        "combined_score_formula": composite["formula"],

        # Preserve the original Isolation Forest output independently.
        "behavioral_score": credit["score"],
        "behavioral_risk_level": credit["risk_level"],
        "behavioral_score_type": credit.get(
            "score_type", "unsupervised_behavioral"
        ),

        # On-chain lending-behavior component (experimental).
        "lending_behavior_score": lending.get("lending_behavior_score"),
        "lending_behavior_status": lending.get("status"),
        "lending_evidence_level": lending.get("evidence_level"),
        "lending_evidence_factor": lending.get("evidence_factor"),
        "lending_borrow_event_count": lending.get("borrow_event_count", 0),
        "lending_components": lending.get("components"),
        "lending_score_explanation": lending.get("explanation"),

        # Supervised fraud model
        "fraud_probability": fraud["fraud_probability"],
        "is_fraud": fraud["is_fraud"],
        "fraud_model": fraud.get(
            "model",
            "kaggle_rf_v2_experimental"
        ),

        # Important transparency warning
        "fraud_model_warning": fraud.get("warning"),
    }


@app.get("/wallet/{address}/lending-history")
def wallet_lending_history(address: str):
    """Return verified deposits, withdrawals, borrows, and repayments from LendingPool events."""
    try:
        return get_lending_history(address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LendingHistoryError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/wallet/{address}/lending-features")
def wallet_lending_features(address: str):
    """Return lending-behavior features computed from verified on-chain history.

    This endpoint prepares features for the next scoring-policy stage. It does
    not change the existing trained behavioral model or assign credit points.
    """
    try:
        history = get_lending_history(address)
        features = compute_lending_features(history)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LendingHistoryError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        "address": history["address"],
        "pool_address": history["pool_address"],
        "feature_source": history["history_source"],
        "feature_count": len(features),
        "feature_names": LENDING_FEATURE_NAMES,
        "features": features,
        "scoring_status": "features_only_not_yet_applied_to_credit_score",
        "notes": [
            "Features are derived from confirmed LendingPool events and current contract state.",
            "Repayment timeliness cannot be measured until the contract records loan due dates or default events.",
            "The existing trained behavioral model is unchanged; no score points are assigned by this endpoint.",
        ],
    }


@app.get("/wallet/{address}/lending-score")
def wallet_lending_score(address: str):
    """Return an explainable, experimental lending-behavior index.

    This score is kept separate from the existing Isolation Forest wallet score.
    It is a transparent heuristic, not a validated default-probability model.
    """
    try:
        history = get_lending_history(address)
        features = compute_lending_features(history)
        result = compute_lending_behavior_score(features)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LendingHistoryError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "address": history["address"],
        "pool_address": history["pool_address"],
        "score_type": "rule_based_lending_behavior_index_experimental",
        "feature_source": history["history_source"],
        **result,
        "limitations": [
            "This is an experimental, rule-based lending-behavior index, not a validated creditworthiness or default-probability estimate.",
            "Repayment coverage uses cumulative repaid divided by cumulative borrowed and does not link each repayment to a particular loan.",
            "The contract does not record due dates or default events, so repayment timeliness cannot be assessed.",
            "The existing Isolation Forest score and fraud model are not modified by this endpoint.",
        ],
    }


@app.post("/wallet/{address}/sync-onchain", dependencies=[Depends(require_oracle_key)])
def sync_wallet_onchain(address: str, use_cache: bool = True):
    """
    Step 7 gap fix: the actual oracle bridge.

    Recomputes this wallet's credit score + fraud flag (same logic as /report)
    and submits them on-chain via LendingPool.setCreditData(address, score, isFraud),
    signed with ORACLE_PRIVATE_KEY (backend-only environment variable -- never
    sent by or exposed to the frontend).

    Requires the X-Oracle-Key header to match ORACLE_API_KEY (see backend/.env.example).
    This is a demo-grade protection, not real auth -- see app/services/oracle.py.
    """
    credit = get_credit_score_for_wallet(address, use_cache=use_cache)
    fraud = get_fraud_for_wallet(address, use_cache=use_cache)
    if credit is None or fraud is None:
        raise HTTPException(
            status_code=503,
            detail="Credit/fraud model not trained. Run train_behavioral_credit_model.py and train_credit_model.py.",
        )

    try:
        _history, lending, composite = _get_lending_score_and_composite(
            address, behavioral_score=float(credit["score"])
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LendingHistoryError as e:
        raise HTTPException(status_code=502, detail=str(e))

    try:
        result = oracle.sync_credit_onchain(
            address=address,
            score=composite["combined_credit_score"],
            is_fraud=fraud["is_fraud"],
        )
    except oracle.OracleConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except oracle.OracleTransactionError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "address": result["address"],
        "synced_score": result["score"],
        "synced_is_fraud": result["is_fraud"],
        "tx_hash": result["tx_hash"],
        "lending_pool_address": result["lending_pool_address"],
        "score_type": composite["score_type"],
        "combined_credit_score": composite["combined_credit_score"],
        "behavioral_score": round(float(credit["score"]), 2),
        "lending_behavior_score": lending.get("lending_behavior_score"),
        "combined_score_weights": composite["weights"],
    }


@app.post("/faucet/{address}", dependencies=[Depends(require_oracle_key)])
def faucet(address: str, amount: float = 1000.0):
    """
    Local-demo convenience: mint MOCK test tokens to `address` so you don't have
    to manually run a Hardhat console command before depositing/borrowing.

    This ONLY makes sense against a local Hardhat network where TOKEN_ADDRESS's
    owner is the same key as ORACLE_PRIVATE_KEY (true by default after running
    contracts/scripts/deploy.js). Never point this at a real network.
    """
    if amount <= 0 or amount > 1_000_000:
        raise HTTPException(status_code=400, detail="amount must be between 0 and 1,000,000")
    try:
        result = oracle.mint_test_tokens(address=address, amount_ether=amount)
    except oracle.OracleConfigError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except oracle.OracleTransactionError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result
