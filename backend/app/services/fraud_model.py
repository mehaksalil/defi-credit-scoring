"""
Step 5: Fraud / anomaly detection — unsupervised.

- No labels: we learn "normal" behavior from a set of wallets; outliers get high fraud score.
- Isolation Forest: good for high-dimensional data, flags points that are easy to isolate (anomalous).
- Same features as credit model so we can run both from one feature vector.
"""
from __future__ import annotations

import joblib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.services.features import FEATURE_NAMES

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
FRAUD_MODEL_FILE = MODELS_DIR / "fraud_model.joblib"
FRAUD_SCALER_FILE = MODELS_DIR / "fraud_scaler.joblib"
FRAUD_SCORE_RANGE_FILE = MODELS_DIR / "fraud_score_range.joblib"

# Threshold above which we flag as fraud (fraud_probability)
FRAUD_THRESHOLD = 0.5


def _ensure_models_dir() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _get_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Extract FEATURE_NAMES columns in order; fill missing with 0."""
    df = df.copy()
    for col in FEATURE_NAMES:
        if col not in df.columns:
            df[col] = 0.0
    return df[FEATURE_NAMES].astype(np.float64).fillna(0).values


def train_fraud_model(feature_df: pd.DataFrame) -> tuple[IsolationForest, StandardScaler]:
    """
    Fit Isolation Forest and scaler on feature matrix (no labels).
    Outliers in this set will get high anomaly score; we use the same features as credit.
    Saves model and scaler to MODELS_DIR.
    """
    X = _get_feature_matrix(feature_df)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = IsolationForest(
        n_estimators=100,
        max_samples="auto",
        contamination=0.1,  # expect ~10% anomalies in training set
        random_state=42,
    )
    model.fit(X_scaled)

    # --- Fix: score_samples() has no fixed scale (typically a narrow band like
    # -0.7 to -0.3), so a raw sigmoid on it barely moves and clusters everything
    # around 0.5-0.7 regardless of how anomalous a point actually is (verified:
    # 50/50 synthetic normal points got fraud_prob > 0.5 with the old code).
    #
    # Fix: use decision_function() = score_samples() - offset_, where offset_ is
    # the threshold IsolationForest itself derived from `contamination`. A point
    # exactly AT that boundary should map to fraud_probability == FRAUD_THRESHOLD
    # (0.5) by construction -- that's what "contamination=0.1" already promised.
    # We scale the sigmoid by the training decision values' std so the 0-1 range
    # isn't arbitrarily steep or flat.
    train_decision = model.decision_function(X_scaled)
    decision_scale = float(np.std(train_decision))
    if decision_scale < 1e-9:
        decision_scale = 1.0  # degenerate: near-identical training scores

    _ensure_models_dir()
    joblib.dump(model, FRAUD_MODEL_FILE)
    joblib.dump(scaler, FRAUD_SCALER_FILE)
    joblib.dump({"decision_scale": decision_scale}, FRAUD_SCORE_RANGE_FILE)
    return model, scaler


def load_fraud_model() -> tuple[IsolationForest | None, StandardScaler | None]:
    """Load saved model and scaler. Returns (None, None) if not found."""
    if not FRAUD_MODEL_FILE.exists() or not FRAUD_SCALER_FILE.exists():
        return None, None
    return joblib.load(FRAUD_MODEL_FILE), joblib.load(FRAUD_SCALER_FILE)


def _load_decision_scale() -> float:
    """Load the training decision_function() std saved by train_fraud_model()."""
    if not FRAUD_SCORE_RANGE_FILE.exists():
        # Fallback for models trained before this fix; not calibrated, but at
        # least documents the gap instead of silently misbehaving.
        return 1.0
    return joblib.load(FRAUD_SCORE_RANGE_FILE)["decision_scale"]


def _anomaly_to_fraud_prob(decision_value: float, decision_scale: float) -> float:
    """
    decision_value = IsolationForest.decision_function() output for one point:
    positive = more normal than the contamination-derived boundary, negative =
    more anomalous. Map through a sigmoid scaled by the training std, so a point
    exactly at the boundary (decision_value == 0) gives fraud_probability == 0.5,
    consistent with the `contamination` rate the model was trained with.
    """
    return float(1.0 / (1.0 + np.exp(decision_value / decision_scale)))


def predict_fraud(
    model: IsolationForest, scaler: StandardScaler, feature_row: pd.DataFrame | pd.Series
) -> tuple[float, bool]:
    """
    Predict fraud probability (0-1) and binary is_fraud flag for one wallet.
    feature_row: one row with FEATURE_NAMES columns, or a Series.
    """
    if isinstance(feature_row, pd.Series):
        df = pd.DataFrame([feature_row])
    else:
        df = feature_row
    X = _get_feature_matrix(df)
    X_scaled = scaler.transform(X)
    decision_value = model.decision_function(X_scaled)[0]
    decision_scale = _load_decision_scale()
    fraud_probability = _anomaly_to_fraud_prob(decision_value, decision_scale)
    is_fraud = fraud_probability >= FRAUD_THRESHOLD
    return fraud_probability, is_fraud


def get_fraud_for_wallet(address: str, use_cache: bool = True) -> dict | None:
    """
    High-level: load fraud model, get features for address, return fraud prob and flag.
    Returns None if model not trained yet.
    """
    model, scaler = load_fraud_model()
    if model is None or scaler is None:
        return None
    from app.services.blockchain_data import get_transactions
    from app.services.features import compute_features

    df = get_transactions(address, use_cache=use_cache)
    features = compute_features(df, address)
    fraud_probability, is_fraud = predict_fraud(model, scaler, features)
    return {
        "address": address,
        "fraud_probability": round(fraud_probability, 4),
        "is_fraud": is_fraud,
    }
