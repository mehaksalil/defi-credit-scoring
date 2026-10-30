# """
# Step 5b (experimental): Kaggle-trained, LABELED fraud classifier.

# Unlike fraud_model.py (unsupervised IsolationForest on 13 features, ~7
# training wallets), this uses a RandomForestClassifier trained on the public
# "Ethereum Fraud Detection Dataset" (9,841 real wallets, real Etherscan-sourced
# FLAG labels, 47 usable features after cleaning). Verified held-out performance
# on that CSV: precision/recall ~0.99, ROC-AUC 0.999.

# IMPORTANT CAVEAT, not a footnote: that accuracy is on the STATIC CSV. Whether
# it holds on LIVE wallets depends entirely on features_v2.py computing the same
# 47 columns the same way the original dataset's authors did -- and several of
# those columns are marked [APPROXIMATION] or [UNRELIABLE] there because they
# require contract-detection or have ambiguous original definitions. This has
# NOT been validated against live Etherscan data (no network access in the
# environment this was built in). Treat this endpoint's output as experimental
# until you've run the validation described in features_v2.py's docstring.
# """
# from __future__ import annotations

# import joblib
# from pathlib import Path

# import pandas as pd

# from app.services.features_v2 import compute_features_v2, FEATURE_NAMES_V2

# MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
# KAGGLE_MODEL_FILE = MODELS_DIR / "fraud_detection_rf_kaggle.joblib"
# KAGGLE_FEATURES_FILE = MODELS_DIR / "fraud_detection_rf_kaggle_features.joblib"
# LE_SENT_FILE = MODELS_DIR / "le_sent.joblib"
# LE_REC_FILE = MODELS_DIR / "le_rec.joblib"


# def load_kaggle_fraud_model():
#     """Returns (model, feature_names, sent_encoder, rec_encoder) or all-None if not trained."""
#     if not KAGGLE_MODEL_FILE.exists():
#         return None, None, None, None
#     model = joblib.load(KAGGLE_MODEL_FILE)
#     feature_names = joblib.load(KAGGLE_FEATURES_FILE) if KAGGLE_FEATURES_FILE.exists() else FEATURE_NAMES_V2
#     sent_enc = joblib.load(LE_SENT_FILE) if LE_SENT_FILE.exists() else None
#     rec_enc = joblib.load(LE_REC_FILE) if LE_REC_FILE.exists() else None
#     return model, feature_names, sent_enc, rec_enc


# def get_kaggle_fraud_for_wallet(address: str, use_cache: bool = True) -> dict | None:
#     """
#     High-level: fetch live tx + token tx, compute the 47-column feature vector,
#     run the Kaggle-trained RF classifier. Returns None if model isn't trained.
#     EXPERIMENTAL -- see module docstring.
#     """
#     model, feature_names, sent_enc, rec_enc = load_kaggle_fraud_model()
#     if model is None:
#         return None

#     from app.services.blockchain_data import get_transactions, get_token_transactions

#     df = get_transactions(address, use_cache=use_cache)
#     token_df = get_token_transactions(address, use_cache=use_cache)
#     features = compute_features_v2(df, token_df, address, sent_enc, rec_enc)

#     X = pd.DataFrame([features])[feature_names]
#     proba = model.predict_proba(X)[0]
#     fraud_probability = float(proba[1]) if len(proba) == 2 else float(proba[0])
#     return {
#         "address": address,
#         "fraud_probability": round(fraud_probability, 4),
#         "is_fraud": fraud_probability >= 0.5,
#         "model": "kaggle_rf_v2_experimental",
#         "warning": (
#             "Experimental: several input features are approximated or "
#             "unvalidated against live data. See features_v2.py docstring."
#         ),
#     }

"""
Kaggle-trained labeled Ethereum fraud classifier.

Production-oriented inference wrapper around the Random Forest trained on
the Ethereum Fraud Detection Dataset.

IMPORTANT:
The model is only trustworthy for live-wallet inference if the feature
pipeline used here produces the same feature definitions that were used
during training.

This module therefore:
1. Loads the trained model and feature schema.
2. Validates the feature schema.
3. Computes live features.
4. Checks for missing / extra / non-finite values.
5. Preserves the exact training feature order.
6. Uses the model's probability output.
7. Applies an explicit configurable fraud threshold.
8. Returns diagnostics so the API can expose model status honestly.

It does NOT silently substitute the old Isolation Forest model.
"""

from __future__ import annotations

from pathlib import Path
from pyexpat import features
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.services.features_v2 import (
    compute_features_v2,
    FEATURE_NAMES_V2,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MODELS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "models"
)

KAGGLE_MODEL_FILE = (
    MODELS_DIR / "fraud_detection_rf_kaggle.joblib"
)

KAGGLE_FEATURES_FILE = (
    MODELS_DIR / "fraud_detection_rf_kaggle_features.joblib"
)

LE_SENT_FILE = (
    MODELS_DIR / "le_sent.joblib"
)

LE_REC_FILE = (
    MODELS_DIR / "le_rec.joblib"
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Keep this explicit.
#
# 0.50 is the normal classification threshold, but it should NOT be hidden
# inside the model code.
#
# Later, after threshold analysis on the validation set, this can be changed
# to the threshold selected according to the project's objective.
DEFAULT_FRAUD_THRESHOLD = 0.50


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class FraudModelError(RuntimeError):
    """Base exception for fraud-model failures."""


class FraudModelNotTrainedError(FraudModelError):
    """Raised when the trained Kaggle model is unavailable."""


class FeatureSchemaError(FraudModelError):
    """Raised when live features don't match the model schema."""


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_kaggle_fraud_model():
    """
    Load the trained Kaggle Random Forest and its supporting artifacts.

    Returns:
        (
            model,
            feature_names,
            sent_encoder,
            rec_encoder
        )

    Raises:
        FraudModelNotTrainedError:
            If the model or required feature schema is missing.
    """

    if not KAGGLE_MODEL_FILE.exists():
        raise FraudModelNotTrainedError(
            f"Kaggle fraud model not found: {KAGGLE_MODEL_FILE}"
        )

    if not KAGGLE_FEATURES_FILE.exists():
        raise FraudModelNotTrainedError(
            f"Kaggle feature schema not found: "
            f"{KAGGLE_FEATURES_FILE}"
        )

    model = joblib.load(KAGGLE_MODEL_FILE)
    feature_names = joblib.load(KAGGLE_FEATURES_FILE)

    sent_enc = (
        joblib.load(LE_SENT_FILE)
        if LE_SENT_FILE.exists()
        else None
    )

    rec_enc = (
        joblib.load(LE_REC_FILE)
        if LE_REC_FILE.exists()
        else None
    )

    if not isinstance(feature_names, (list, tuple)):
        raise FeatureSchemaError(
            "Saved feature schema is not a list/tuple."
        )

    feature_names = list(feature_names)

    if not feature_names:
        raise FeatureSchemaError(
            "Saved feature schema is empty."
        )

    return model, feature_names, sent_enc, rec_enc


# ---------------------------------------------------------------------------
# Feature validation
# ---------------------------------------------------------------------------

def _validate_feature_schema(
    features: dict[str, Any],
    expected_features: list[str],
) -> pd.DataFrame:
    """
    Validate and construct the model input dataframe.

    This is deliberately strict.

    We do NOT silently:
    - add missing features with zero
    - remove unexpected features
    - reorder based on assumptions
    - convert NaN into arbitrary values

    The live feature pipeline must explicitly produce the expected schema.
    """

    if isinstance(features, pd.Series):
        features = features.to_dict()
    elif isinstance(features, pd.DataFrame):
        if len(features) != 1:
            raise FeatureSchemaError(
                "Expected exactly one row of features."
                )
        features = features.iloc[0].to_dict()

    if not isinstance(features, dict):
        raise FeatureSchemaError(
            "Feature extractor must return a dictionary, "
            "pandas Series, or single-row DataFrame."
        )

    actual_features = set(features.keys())
    expected_set = set(expected_features)

    missing = sorted(expected_set - actual_features)
    extra = sorted(actual_features - expected_set)

    if missing:
        raise FeatureSchemaError(
            "Live feature vector is missing required model features: "
            + ", ".join(missing)
        )

    if extra:
        # Extra features are not necessarily dangerous, but they should not
        # silently enter the model.
        #
        # We ignore them only after explicitly reporting them through the
        # diagnostics generated later.
        pass

    # Exact model order.
    row = {
        name: features[name]
        for name in expected_features
    }

    X = pd.DataFrame([row], columns=expected_features)

    # Force numeric values.
    for column in expected_features:
        try:
            X[column] = pd.to_numeric(X[column])
        except Exception as exc:
            raise FeatureSchemaError(
                f"Feature '{column}' is not numeric: "
                f"{X[column].iloc[0]!r}"
            ) from exc

    values = X.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        bad_columns = []

        for column in expected_features:
            value = X[column].iloc[0]

            if not np.isfinite(float(value)):
                bad_columns.append(column)

        raise FeatureSchemaError(
            "Live feature vector contains NaN/Inf values in: "
            + ", ".join(bad_columns)
        )

    return X


# ---------------------------------------------------------------------------
# Probability extraction
# ---------------------------------------------------------------------------

def _get_fraud_probability(model, X: pd.DataFrame) -> float:
    """
    Extract the probability corresponding to fraud = 1.
    """

    if not hasattr(model, "predict_proba"):
        raise FraudModelError(
            "Loaded fraud model does not support predict_proba()."
        )

    probabilities = model.predict_proba(X)

    if probabilities.ndim != 2:
        raise FraudModelError(
            f"Unexpected probability shape: {probabilities.shape}"
        )

    classes = getattr(model, "classes_", None)

    if classes is None:
        raise FraudModelError(
            "Model does not expose classes_."
        )

    classes = list(classes)

    if 1 not in classes:
        raise FraudModelError(
            f"Fraud class 1 is missing from model classes: {classes}"
        )

    fraud_index = classes.index(1)

    probability = float(
        probabilities[0][fraud_index]
    )

    if not 0.0 <= probability <= 1.0:
        raise FraudModelError(
            f"Invalid fraud probability: {probability}"
        )

    return probability


# ---------------------------------------------------------------------------
# Main inference function
# ---------------------------------------------------------------------------

def get_kaggle_fraud_for_wallet(
    address: str,
    use_cache: bool = True,
    threshold: float = DEFAULT_FRAUD_THRESHOLD,
) -> dict[str, Any] | None:
    """
    Compute fraud probability for a live Ethereum wallet.

    Args:
        address:
            Ethereum wallet address.

        use_cache:
            Whether blockchain_data.py should use cached transactions.

        threshold:
            Probability threshold used to convert probability into
            binary fraud classification.

    Returns:
        Dictionary containing:
            address
            fraud_probability
            is_fraud
            threshold
            model
            feature_count
            feature_schema_valid
            warning
    """

    if not address:
        raise ValueError("Wallet address is required.")

    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            "Fraud threshold must be between 0 and 1."
        )

    model, feature_names, sent_enc, rec_enc = (
        load_kaggle_fraud_model()
    )

    # Import here to avoid unnecessary dependency loading at module import.
    from app.services.blockchain_data import (
        get_transactions,
        get_token_transactions,
    )

    # -----------------------------------------------------------------------
    # Fetch blockchain data
    # -----------------------------------------------------------------------

    tx_df = get_transactions(
        address,
        use_cache=use_cache,
    )

    token_df = get_token_transactions(
        address,
        use_cache=use_cache,
    )

    # -----------------------------------------------------------------------
    # Compute live features
    # -----------------------------------------------------------------------

    features = compute_features_v2(
        tx_df,
        token_df,
        address,
        sent_enc,
        rec_enc,
    )

    # -----------------------------------------------------------------------
    # Validate feature schema
    # -----------------------------------------------------------------------

    X = _validate_feature_schema(
        features,
        feature_names,
    )

    # -----------------------------------------------------------------------
    # Predict
    # -----------------------------------------------------------------------

    fraud_probability = _get_fraud_probability(
        model,
        X,
    )

    is_fraud = fraud_probability >= threshold

    # -----------------------------------------------------------------------
    # Diagnostics
    # -----------------------------------------------------------------------

    expected_set = set(feature_names)
    actual_set = set(features.keys())

    extra_features = sorted(
        actual_set - expected_set
    )

    return {
        "address": address,

        "fraud_probability": round(
            fraud_probability,
            6,
        ),

        "is_fraud": bool(is_fraud),

        "threshold": threshold,

        "model": "kaggle_random_forest",

        "feature_count": len(feature_names),

        "feature_schema_valid": True,

        "extra_live_features": extra_features,

        "warning": (
            "Live prediction is valid only to the extent that "
            "features_v2.py reproduces the Kaggle training feature "
            "definitions. Validate feature parity before presenting "
            "this as production-grade fraud detection."
        ),
    }