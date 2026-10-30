"""Evaluate a separate Isolation Forest anomaly-detection baseline.

Run from backend/ after evaluate_fraud_classifier.py has been installed:
    python evaluate_isolation_forest_benchmark.py

Important: this is an exploratory 47-feature benchmark baseline using the
Kaggle dataset schema. It is NOT the same as the currently deployed
13-feature Isolation Forest model. It is included to illustrate how an
unsupervised detector behaves against labeled benchmark records, not to claim
metrics for the deployed model.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
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

from evaluate_fraud_classifier import fit_encode_features, normalize_column

BACKEND_DIR = Path(__file__).resolve().parent
DATASET_PATH = BACKEND_DIR.parent / "ethereum_fraud_detection" / "transaction_dataset.csv"
FEATURES_PATH = BACKEND_DIR / "models" / "fraud_detection_rf_kaggle_features.joblib"
OUTPUT_DIR = BACKEND_DIR / "evaluation_results"
RANDOM_STATE = 42
TEST_SIZE = 0.20


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(f"Saved 47-feature schema not found: {FEATURES_PATH}")

    df = pd.read_csv(DATASET_PATH).rename(columns=lambda c: normalize_column(c))
    if "FLAG" not in df.columns:
        raise ValueError("Dataset is missing the FLAG target column")
    feature_names = list(joblib.load(FEATURES_PATH))
    missing = [c for c in feature_names if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    df = df.dropna(subset=["FLAG"]).copy()
    y = pd.to_numeric(df["FLAG"], errors="raise").astype(int)
    if set(y.unique()) != {0, 1}:
        raise ValueError(f"Expected FLAG labels 0/1; got {sorted(y.unique())}")
    X = df[feature_names].copy()

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    X_train, X_test = fit_encode_features(X_train_raw, X_test_raw)
    normal_train = X_train.loc[y_train.to_numpy() == 0]
    if normal_train.empty:
        raise ValueError("No normal examples in training split")

    # Unsupervised fit: model sees ONLY normal training rows; labels are only
    # used afterward to evaluate predictions on held-out test rows.
    model = IsolationForest(
        n_estimators=100,
        max_samples="auto",
        contamination=0.1,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(normal_train)
    predicted = (model.predict(X_test) == -1).astype(int)
    anomaly_score = -model.decision_function(X_test)  # larger => more anomalous
    cm = confusion_matrix(y_test, predicted, labels=[0, 1])
    tn, fp, fn, tp = (int(v) for v in cm.ravel())
    metrics = {
        "evaluation_type": "exploratory_isolation_forest_47_feature_baseline",
        "warning": "NOT the deployed 13-feature Isolation Forest. Benchmark labels are used only for held-out evaluation; model fitted on normal training rows only.",
        "dataset_path": str(DATASET_PATH),
        "total_records": int(len(df)),
        "total_csv_columns": int(pd.read_csv(DATASET_PATH, nrows=0).shape[1]),
        "feature_count": int(len(feature_names)),
        "train_records": int(len(X_train)),
        "normal_training_records": int(len(normal_train)),
        "test_records": int(len(X_test)),
        "label_counts_total": {str(int(k)): int(v) for k, v in y.value_counts().sort_index().items()},
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "contamination": 0.1,
        "accuracy": float(accuracy_score(y_test, predicted)),
        "precision_fraud": float(precision_score(y_test, predicted, zero_division=0)),
        "recall_fraud": float(recall_score(y_test, predicted, zero_division=0)),
        "f1_fraud": float(f1_score(y_test, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, anomaly_score)),
        "confusion_matrix_labels": ["normal(0)", "fraud(1)"],
        "confusion_matrix": cm.tolist(),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "isolation_forest_benchmark_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "isolation_forest_benchmark_report.txt").write_text(
        classification_report(y_test, predicted, labels=[0, 1], target_names=["Normal", "Fraud"], zero_division=0)
        + "\nWARNING: exploratory 47-feature baseline, NOT the deployed 13-feature Isolation Forest.\n",
        encoding="utf-8",
    )
    pd.DataFrame(cm, index=["Actual normal", "Actual fraud"], columns=["Predicted normal", "Predicted fraud"]).to_csv(
        OUTPUT_DIR / "isolation_forest_benchmark_confusion_matrix.csv"
    )

    print("=" * 68)
    print("EXPLORATORY ISOLATION FOREST BENCHMARK")
    print("=" * 68)
    print("IMPORTANT: This is a separate 47-feature benchmark baseline, NOT the deployed 13-feature Isolation Forest.")
    print(f"Dataset records:          {len(df)}")
    print(f"Training records:          {len(X_train)}")
    print(f"Normal rows used to fit:   {len(normal_train)}")
    print(f"Held-out test records:    {len(X_test)}")
    print(f"Features:                 {len(feature_names)}")
    print(f"Accuracy:                 {metrics['accuracy']:.4f}")
    print(f"Fraud precision:          {metrics['precision_fraud']:.4f}")
    print(f"Fraud recall:             {metrics['recall_fraud']:.4f}")
    print(f"Fraud F1-score:            {metrics['f1_fraud']:.4f}")
    print(f"ROC-AUC:                  {metrics['roc_auc']:.4f}")
    print("Confusion matrix [[TN, FP], [FN, TP]]:")
    print(cm)
    print(f"TN={tn}, FP={fp}, FN={fn}, TP={tp}")
    print(f"Saved outputs to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
