"""
Step 4: Credit scoring model — train and predict score 0–100 and risk level.

- Uses proxy labels (from proxy_labels.py) for training; no real default data.
- StandardScaler so features are on similar scale; XGBoost for robustness to mixed types.
- Score = probability of "good" class × 100; risk level from score bands.
"""
from __future__ import annotations

import joblib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from xgboost import XGBClassifier

from app.services.features import FEATURE_NAMES
from app.services.proxy_labels import proxy_label_from_features

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
CREDIT_MODEL_FILE = MODELS_DIR / "credit_model.joblib"
CREDIT_SCALER_FILE = MODELS_DIR / "credit_scaler.joblib"
BEHAVIORAL_CREDIT_MODEL_FILE = MODELS_DIR / "behavioral_credit_model.joblib"
RISK_LEVELS = [(0, 40, "High"), (40, 70, "Medium"), (70, 101, "Low")]


def _ensure_models_dir() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _get_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Extract FEATURE_NAMES columns in order; fill missing with 0."""
    for col in FEATURE_NAMES:
        if col not in df.columns:
            df = df.copy()
            df[col] = 0.0
    return df[FEATURE_NAMES].astype(np.float64).fillna(0).values


def _behavioral_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Prepare features for the unsupervised model.

    Transaction counts and values span orders of magnitude, so they are
    log-transformed before scaling.  The two ratio features stay linear.
    """
    frame = df.reindex(columns=FEATURE_NAMES, fill_value=0.0).copy()
    frame = frame.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    for name in FEATURE_NAMES:
        if name not in {"failed_tx_ratio", "contract_interaction_ratio"}:
            frame[name] = np.log1p(frame[name].clip(lower=0.0))
    return frame.to_numpy(dtype=np.float64)


def train_behavioral_credit_model(feature_df: pd.DataFrame) -> dict:
    """Train an unlabelled transaction-behavior model and save it.

    This does not learn repayment/default risk.  It learns how typical a
    wallet looks relative to the historical transaction population.
    """
    if len(feature_df) < 100:
        raise ValueError("At least 100 wallet feature rows are required for behavioral training.")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(_behavioral_feature_matrix(feature_df))
    model = IsolationForest(
        n_estimators=200,
        max_samples=min(256, len(X_scaled)),
        contamination="auto",
        random_state=42,
        # Single-process is reliable on Windows/OneDrive environments where
        # worker-process creation can be restricted.
        n_jobs=1,
    )
    model.fit(X_scaled)
    bundle = {
        "model": model,
        "scaler": scaler,
        "reference_scores": np.sort(model.decision_function(X_scaled)),
        "training_wallets": int(len(feature_df)),
        "score_type": "unsupervised_behavioral",
        "feature_names": FEATURE_NAMES,
    }
    _ensure_models_dir()
    joblib.dump(bundle, BEHAVIORAL_CREDIT_MODEL_FILE)
    return bundle


def _predict_behavioral_credit(bundle: dict, feature_row: pd.DataFrame | pd.Series) -> tuple[float, str]:
    frame = pd.DataFrame([feature_row]) if isinstance(feature_row, pd.Series) else feature_row
    X_scaled = bundle["scaler"].transform(_behavioral_feature_matrix(frame))
    decision = float(bundle["model"].decision_function(X_scaled)[0])
    reference = bundle["reference_scores"]
    score = float(100.0 * np.searchsorted(reference, decision, side="right") / len(reference))
    score = max(0.0, min(100.0, score))
    return score, score_to_risk_level(score)


def train_credit_model(feature_df: pd.DataFrame, labels: pd.Series | None = None) -> tuple[XGBClassifier, StandardScaler]:
    """Train the existing proxy-label XGBoost model and save it."""
    if labels is None:
        labels = feature_df.apply(proxy_label_from_features, axis=1)
    X = _get_feature_matrix(feature_df)
    y = np.asarray(labels).ravel()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_scaled, y)
    _ensure_models_dir()
    joblib.dump(model, CREDIT_MODEL_FILE)
    joblib.dump(scaler, CREDIT_SCALER_FILE)
    return model, scaler


def load_credit_model() -> tuple[XGBClassifier | None, StandardScaler | None]:
    if not CREDIT_MODEL_FILE.exists() or not CREDIT_SCALER_FILE.exists():
        return None, None
    return joblib.load(CREDIT_MODEL_FILE), joblib.load(CREDIT_SCALER_FILE)


def score_to_risk_level(score: float) -> str:
    for low, high, level in RISK_LEVELS:
        if low <= score < high:
            return level
    return "Medium"


def predict_credit(model: XGBClassifier, scaler: StandardScaler, feature_row: pd.DataFrame | pd.Series) -> tuple[float, str]:
    if isinstance(feature_row, pd.Series):
        df = pd.DataFrame([feature_row])
    else:
        df = feature_row
    X_scaled = scaler.transform(_get_feature_matrix(df))
    proba = model.predict_proba(X_scaled)[0]
    score = float(proba[1] * 100.0) if proba.shape[0] == 2 else float(proba[0] * 100.0)
    score = max(0.0, min(100.0, score))
    return score, score_to_risk_level(score)


def get_credit_score_for_wallet(address: str, use_cache: bool = True) -> dict | None:
    from app.services.blockchain_data import get_transactions
    from app.services.features import compute_features

    features = compute_features(get_transactions(address, use_cache=use_cache), address)
    if BEHAVIORAL_CREDIT_MODEL_FILE.exists():
        bundle = joblib.load(BEHAVIORAL_CREDIT_MODEL_FILE)
        score, risk_level = _predict_behavioral_credit(bundle, features)
        return {
            "address": address,
            "score": round(score, 2),
            "risk_level": risk_level,
            "score_type": bundle["score_type"],
            "training_wallets": bundle["training_wallets"],
        }

    model, scaler = load_credit_model()
    if model is None or scaler is None:
        return None
    score, risk_level = predict_credit(model, scaler, features)
    return {"address": address, "score": round(score, 2), "risk_level": risk_level}
