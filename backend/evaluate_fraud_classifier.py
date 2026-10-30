"""Held-out evaluation for the Ethereum wallet fraud Random Forest.

Run from the backend folder:
    python evaluate_fraud_classifier.py

This trains a fresh model on a stratified 80/20 split and evaluates only on
rows that were not used to fit this evaluation model. It does not overwrite
or change the deployed .joblib model.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

BACKEND_DIR = Path(__file__).resolve().parent
DATASET_PATH = BACKEND_DIR.parent / "ethereum_fraud_detection" / "transaction_dataset.csv"
FEATURES_PATH = BACKEND_DIR / "models" / "fraud_detection_rf_kaggle_features.joblib"
OUTPUT_DIR = BACKEND_DIR / "evaluation_results"
RANDOM_STATE = 42
TEST_SIZE = 0.20
CATEGORICAL_FEATURES = {
    "ERC20_most_sent_token_type",
    "ERC20_most_rec_token_type",
}


def normalize_column(name: str) -> str:
    """Map raw CSV column labels to the model's saved feature names."""
    name = str(name).strip()
    replacements = {
        "Avg min between sent tnx": "Avg_min_between_sent_tnx",
        "Avg min between received tnx": "Avg_min_between_received_tnx",
        "Time Diff between first and last (Mins)": "Time_Diff_between_first_and_last_(Mins)",
        "Sent tnx": "Sent_tnx",
        "Received Tnx": "Received_Tnx",
        "Number of Created Contracts": "Number_of_Created_Contracts",
        "Unique Received From Addresses": "Unique_Received_From_Addresses",
        "Unique Sent To Addresses": "Unique_Sent_To_Addresses",
        "min value received": "min_value_received",
        "max value received": "max_value_received",
        "avg val received": "avg_val_received",
        "min val sent": "min_val_sent",
        "max val sent": "max_val_sent",
        "avg val sent": "avg_val_sent",
        "min value sent to contract": "min_value_sent_to_contract",
        "max val sent to contract": "max_val_sent_to_contract",
        "avg value sent to contract": "avg_value_sent_to_contract",
        "total transactions (including tnx to create contract": "total_transactions_(including_tnx_to_create_contract",
        "total Ether sent": "total_Ether_sent",
        "total ether received": "total_ether_received",
        "total ether sent contracts": "total_ether_sent_contracts",
        "total ether balance": "total_ether_balance",
        "Total ERC20 tnxs": "Total_ERC20_tnxs",
        "ERC20 total Ether received": "ERC20_total_Ether_received",
        "ERC20 total ether sent": "ERC20_total_ether_sent",
        "ERC20 total Ether sent contract": "ERC20_total_Ether_sent_contract",
        "ERC20 uniq sent addr": "ERC20_uniq_sent_addr",
        "ERC20 uniq rec addr": "ERC20_uniq_rec_addr",
        "ERC20 uniq sent addr.1": "ERC20_uniq_sent_addr.1",
        "ERC20 uniq rec contract addr": "ERC20_uniq_rec_contract_addr",
        "ERC20 avg time between sent tnx": "ERC20_avg_time_between_sent_tnx",
        "ERC20 avg time between rec tnx": "ERC20_avg_time_between_rec_tnx",
        "ERC20 avg time between rec 2 tnx": "ERC20_avg_time_between_rec_2_tnx",
        "ERC20 avg time between contract tnx": "ERC20_avg_time_between_contract_tnx",
        "ERC20 min val rec": "ERC20_min_val_rec",
        "ERC20 max val rec": "ERC20_max_val_rec",
        "ERC20 avg val rec": "ERC20_avg_val_rec",
        "ERC20 min val sent": "ERC20_min_val_sent",
        "ERC20 max val sent": "ERC20_max_val_sent",
        "ERC20 avg val sent": "ERC20_avg_val_sent",
        "ERC20 min val sent contract": "ERC20_min_val_sent_contract",
        "ERC20 max val sent contract": "ERC20_max_val_sent_contract",
        "ERC20 avg val sent contract": "ERC20_avg_val_sent_contract",
        "ERC20 uniq sent token name": "ERC20_uniq_sent_token_name",
        "ERC20 uniq rec token name": "ERC20_uniq_rec_token_name",
        "ERC20 most sent token type": "ERC20_most_sent_token_type",
        "ERC20 most rec token type": "ERC20_most_rec_token_type",
        "ERC20_most_rec_token_type": "ERC20_most_rec_token_type",
    }
    return replacements.get(name, name)


def fit_encode_features(X_train: pd.DataFrame, X_test: pd.DataFrame):
    """Fit preprocessing on train only; apply that learned mapping to test."""
    train = X_train.copy()
    test = X_test.copy()

    for col in train.columns:
        if col in CATEGORICAL_FEATURES:
            train_values = train[col].fillna("<MISSING>").astype(str).str.strip()
            test_values = test[col].fillna("<MISSING>").astype(str).str.strip()
            categories = {value: index for index, value in enumerate(sorted(train_values.unique()))}
            train[col] = train_values.map(categories).astype(float)
            # Unknown categories in the test split get a dedicated sentinel.
            test[col] = test_values.map(categories).fillna(-1).astype(float)
        else:
            train[col] = pd.to_numeric(train[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
            test[col] = pd.to_numeric(test[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
            median = train[col].median()
            if pd.isna(median):
                median = 0.0
            train[col] = train[col].fillna(median)
            test[col] = test[col].fillna(median)

    return train.astype(float), test.astype(float)


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_PATH}. Place transaction_dataset.csv "
            "in the ethereum_fraud_detection folder beside backend."
        )
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Model feature schema not found at {FEATURES_PATH}. Make sure the backend/models files are present."
        )

    df = pd.read_csv(DATASET_PATH).rename(columns=lambda c: normalize_column(c))
    if "FLAG" not in df.columns:
        raise ValueError("The dataset must contain a FLAG target column.")
    feature_names = list(joblib.load(FEATURES_PATH))
    missing = [name for name in feature_names if name not in df.columns]
    if missing:
        raise ValueError("Missing model feature columns after normalizing names: " + ", ".join(missing))

    df = df.dropna(subset=["FLAG"]).copy()
    y = pd.to_numeric(df["FLAG"], errors="raise").astype(int)
    if set(y.unique()) != {0, 1}:
        raise ValueError(f"Expected binary FLAG labels 0/1; found {sorted(y.unique())}")
    X = df[feature_names].copy()

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    X_train, X_test = fit_encode_features(X_train_raw, X_test_raw)

    # Mirror the saved classifier's main hyperparameters, but train a fresh
    # model only on the training split to get an honest held-out estimate.
    model = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    class_order = list(model.classes_)
    fraud_col = class_order.index(1)
    probabilities = model.predict_proba(X_test)[:, fraud_col]

    cm = confusion_matrix(y_test, predictions, labels=[0, 1])
    tn, fp, fn, tp = (int(v) for v in cm.ravel())
    metrics = {
        "dataset_path": str(DATASET_PATH),
        "total_records": int(len(df)),
        "total_columns_in_csv": int(pd.read_csv(DATASET_PATH, nrows=0).shape[1]),
        "model_features": int(len(feature_names)),
        "train_records": int(len(X_train)),
        "test_records": int(len(X_test)),
        "label_counts_total": {str(int(k)): int(v) for k, v in y.value_counts().sort_index().items()},
        "label_counts_test": {str(int(k)): int(v) for k, v in y_test.value_counts().sort_index().items()},
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision_fraud": float(precision_score(y_test, predictions, pos_label=1, zero_division=0)),
        "recall_fraud": float(recall_score(y_test, predictions, pos_label=1, zero_division=0)),
        "f1_fraud": float(f1_score(y_test, predictions, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix_labels": ["normal(0)", "fraud(1)"],
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "evaluation_note": "Fresh Random Forest fitted only on the training split; held-out static-dataset metrics, not validation on live wallets or proof of loan-default prediction.",
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "fraud_evaluation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "fraud_classification_report.txt").write_text(
        classification_report(y_test, predictions, labels=[0, 1], target_names=["Normal", "Fraud"], zero_division=0),
        encoding="utf-8",
    )
    pd.DataFrame(cm, index=["Actual normal", "Actual fraud"], columns=["Predicted normal", "Predicted fraud"]).to_csv(OUTPUT_DIR / "fraud_confusion_matrix.csv")

    print("=" * 68)
    print("HELD-OUT ETHEREUM FRAUD CLASSIFIER EVALUATION")
    print("=" * 68)
    print(f"Dataset records:       {len(df)}")
    print(f"CSV columns:           {pd.read_csv(DATASET_PATH, nrows=0).shape[1]}")
    print(f"Model input features:  {len(feature_names)}")
    print(f"Training records:      {len(X_train)}")
    print(f"Held-out test records: {len(X_test)}")
    print(f"FLAG counts:           {y.value_counts().sort_index().to_dict()} (0=normal, 1=fraud)")
    print("\nMETRICS (fraud is positive class)")
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision_fraud']:.4f}")
    print(f"Recall:    {metrics['recall_fraud']:.4f}")
    print(f"F1-score:  {metrics['f1_fraud']:.4f}")
    print(f"ROC-AUC:   {metrics['roc_auc']:.4f}")
    print("\nCONFUSION MATRIX: rows=actual [normal, fraud], columns=predicted [normal, fraud]")
    print(cm)
    print(f"TN={tn}, FP={fp}, FN={fn}, TP={tp}")
    print("\nCLASSIFICATION REPORT")
    print(classification_report(y_test, predictions, labels=[0, 1], target_names=["Normal", "Fraud"], zero_division=0))
    print(f"Files saved to: {OUTPUT_DIR}")
    print("NOTE: These are held-out metrics on the static dataset, not live-wallet validation.")


if __name__ == "__main__":
    main()
