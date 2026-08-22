"""
FastAPI app entrypoint.
Endpoints for wallet score, health, etc. will be added in Step 6.
"""
import numpy as np
from fastapi import FastAPI, HTTPException

from app.services.blockchain_data import get_transactions
from app.services.credit_model import get_credit_score_for_wallet
from app.services.fraud_model import get_fraud_for_wallet
from app.services.features import FEATURE_NAMES, compute_features

app = FastAPI(
    title="DeFi Credit Scoring API",
    description="AI-based credit score and fraud detection for wallet addresses",
    version="0.1.0",
)


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
    Step 4: Get AI credit score (0–100) and risk level (Low/Medium/High) for a wallet.
    Requires a trained model; run train_credit_model.py first.
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
            detail="Credit model not trained. Run: python train_credit_model.py",
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


@app.get("/wallet/{address}/report")
def wallet_report(address: str, use_cache: bool = True):
    """
    Step 6: One-shot report for the dashboard: tx count, credit score, risk level, fraud.
    Saves the frontend from calling /transactions, /score, /fraud separately.
    """
    try:
        df = get_transactions(address, use_cache=use_cache)
        tx_count = len(df)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    credit = get_credit_score_for_wallet(address, use_cache=use_cache)
    fraud = get_fraud_for_wallet(address, use_cache=use_cache)
    if credit is None:
        raise HTTPException(
            status_code=503,
            detail="Credit model not trained. Run: python train_credit_model.py",
        )
    if fraud is None:
        raise HTTPException(
            status_code=503,
            detail="Fraud model not trained. Run: python train_credit_model.py",
        )

    return {
        "address": address,
        "tx_count": tx_count,
        "score": credit["score"],
        "risk_level": credit["risk_level"],
        "fraud_probability": fraud["fraud_probability"],
        "is_fraud": fraud["is_fraud"],
    }
