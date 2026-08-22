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
from xgboost import XGBClassifier

from app.services.features import FEATURE_NAMES
from app.services.proxy_labels import proxy_label_from_features

# backend/app/services/credit_model.py -> backend/models
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
CREDIT_MODEL_FILE = MODELS_DIR / "credit_model.joblib"
CREDIT_SCALER_FILE = MODELS_DIR / "credit_scaler.joblib"

# Score bands for risk level (score 0–100; higher = more creditworthy)
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


def train_credit_model(feature_df: pd.DataFrame, labels: pd.Series | None = None) -> tuple[XGBClassifier, StandardScaler]:
    """
    Train XGBoost classifier and scaler. If labels is None, use proxy labels.
    Returns (model, scaler) and saves them to MODELS_DIR.
    """
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
        use_label_encoder=False,
        eval_metric="logloss",
    )
    model.fit(X_scaled, y)
    _ensure_models_dir()
    joblib.dump(model, CREDIT_MODEL_FILE)
    joblib.dump(scaler, CREDIT_SCALER_FILE)
    return model, scaler


def load_credit_model() -> tuple[XGBClassifier | None, StandardScaler | None]:
    """Load saved model and scaler. Returns (None, None) if not found."""
    if not CREDIT_MODEL_FILE.exists() or not CREDIT_SCALER_FILE.exists():
        return None, None
    return joblib.load(CREDIT_MODEL_FILE), joblib.load(CREDIT_SCALER_FILE)


def score_to_risk_level(score: float) -> str:
    """Map score 0–100 to Low / Medium / High risk."""
    for low, high, level in RISK_LEVELS:
        if low <= score < high:
            return level
    return "Medium"


def predict_credit(model: XGBClassifier, scaler: StandardScaler, feature_row: pd.DataFrame | pd.Series) -> tuple[float, str]:
    """
    Predict credit score (0–100) and risk level for one wallet.
    feature_row: one row with FEATURE_NAMES columns, or a Series.
    """
    if isinstance(feature_row, pd.Series):
        df = pd.DataFrame([feature_row])
    else:
        df = feature_row
    X = _get_feature_matrix(df)
    X_scaled = scaler.transform(X)
    # Probability of class 1 (good) -> score 0–100
    proba = model.predict_proba(X_scaled)[0]
    # Assume binary: index 1 is "good"
    if proba.shape[0] == 2:
        score = float(proba[1] * 100.0)
    else:
        score = float(proba[0] * 100.0)
    score = max(0.0, min(100.0, score))
    return score, score_to_risk_level(score)


def get_credit_score_for_wallet(address: str, use_cache: bool = True) -> dict | None:
    """
    High-level: load model, get features for address, return score and risk.
    Returns None if model not trained yet; caller can return default or 503.
    """
    model, scaler = load_credit_model()
    if model is None or scaler is None:
        return None
    from app.services.blockchain_data import get_transactions
    from app.services.features import compute_features

    df = get_transactions(address, use_cache=use_cache)
    features = compute_features(df, address)
    score, risk_level = predict_credit(model, scaler, features)
    return {"address": address, "score": round(score, 2), "risk_level": risk_level}
