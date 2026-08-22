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
    _ensure_models_dir()
    joblib.dump(model, FRAUD_MODEL_FILE)
    joblib.dump(scaler, FRAUD_SCALER_FILE)
    return model, scaler


def load_fraud_model() -> tuple[IsolationForest | None, StandardScaler | None]:
    """Load saved model and scaler. Returns (None, None) if not found."""
    if not FRAUD_MODEL_FILE.exists() or not FRAUD_SCALER_FILE.exists():
        return None, None
    return joblib.load(FRAUD_MODEL_FILE), joblib.load(FRAUD_SCALER_FILE)


def _anomaly_to_fraud_prob(score_sample: float) -> float:
    """
    IsolationForest.score_samples: higher = more normal, lower/negative = more anomalous.
    Map to fraud probability in [0, 1]: high anomaly -> high fraud_prob.
    """
    # score_sample is "normalcy"; negate to get anomaly magnitude
    anomaly = -float(score_sample)
    # Sigmoid so we get a 0-1 probability; scale so typical range maps nicely
    return float(1.0 / (1.0 + np.exp(-anomaly)))


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
    score = model.score_samples(X_scaled)[0]
    fraud_probability = _anomaly_to_fraud_prob(score)
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
