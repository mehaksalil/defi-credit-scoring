"""
Train the credit scoring model and the fraud (anomaly) model.

Run from backend/:
  python train_credit_model.py

Requires ETHERSCAN_API_KEY in .env. Uses cache when available.

CHANGES from the original version (see comments inline for why):
- KNOWN_FRAUD_ADDRESSES_FOR_EVAL added and kept OUT of fraud-model training.
  Mixing known-phishing wallets into the same set used to define "normal"
  behavior for IsolationForest would teach it that phishing behavior IS
  normal -- exactly backwards. These are held out and used only to sanity
  check the trained fraud model at the end.
- Added a real train/test split + printed metrics for the credit model, so a
  broken run (e.g. single-class labels) is visible immediately instead of
  silently saving a useless model.
- Still only ~7 "normal" addresses. That is not fixed by this script alone --
  see the printed warning at the end. Add more addresses across a range of
  activity levels (not just exchanges/whales) for this to be a real detector.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path so "app" resolves
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

from app.services.blockchain_data import get_transactions
from app.services.credit_model import train_credit_model, _get_feature_matrix
from app.services.features import compute_features, FEATURE_NAMES
from app.services.fraud_model import train_fraud_model, predict_fraud
from app.services.proxy_labels import proxy_labels_for_dataframe

# "Normal" wallets used to train BOTH models. Still small (7) and still skewed
# toward high-activity exchange/whale wallets -- this is a known limitation,
# not solved by this script. Add more addresses spanning low/medium/high
# activity levels before treating this as a real detector rather than a demo.
DEFAULT_ADDRESSES = [
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # Vitalik
    "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance 14
    "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503",  # Binance 8
    "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3",  # Coinbase 1
    "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43",  # Coinbase 2
    "0x5041ed759Dd4aFc3a72b8192C143F72f4724081A",  # Rainbow
    "0xDA9dfA130Df4dE4673b89022EE50ff26f6EA73cf",  # Example EOA
]

# Real Etherscan-labeled phishing addresses (sources: Etherscan public
# reports / ScamSniffer / GoPlusSecurity). Used ONLY to evaluate the trained
# fraud model afterward -- never included in training. Verify these are
# still labeled as such on Etherscan before relying on them; labels can be
# added or (rarely) disputed/removed over time.
KNOWN_FRAUD_ADDRESSES_FOR_EVAL = [
    "0xba83e9ce38b10522e3d6061a12779b7526839eda",  # Fake_Phishing3
    "0xd13b093eafa3878de27183388fea7d0d2b0abf9e",  # Fake_Phishing6102
    "0x474057adf42f9f955e86aa1142740f9d7763e41e",  # Fake_Phishing710
    "0x5167052b83f36952d1a9901e0de2b2038c3dd1a3",  # Fake_Phishing201325
]


def _fetch_features(addresses: list[str]) -> pd.DataFrame:
    rows = []
    for i, addr in enumerate(addresses):
        print(f"  Fetching features for {addr} ({i + 1}/{len(addresses)})...")
        try:
            df = get_transactions(addr, use_cache=True)
            rows.append(compute_features(df, addr))
        except Exception as e:
            print(f"    Skip {addr}: {e}")
    if not rows:
        return pd.DataFrame(columns=FEATURE_NAMES)
    return pd.DataFrame(rows)[FEATURE_NAMES]


def main() -> None:
    print("Fetching training wallets (used for BOTH models)...")
    feature_df = _fetch_features(DEFAULT_ADDRESSES)
    if feature_df.empty:
        print("No feature rows; add addresses or check Etherscan API key.")
        sys.exit(1)
    print(f"Got {len(feature_df)} training wallets.")

    # --- Credit model: proxy labels + real train/test evaluation -----------
    labels = proxy_labels_for_dataframe(feature_df)
    print(f"Proxy label distribution: {labels.value_counts().to_dict()}")
    if labels.nunique() < 2:
        print(
            "STOP: proxy labels are single-class with this address list. "
            "XGBoost cannot learn a decision boundary from one class -- "
            "training would either error or produce a model that always "
            "predicts the same thing regardless of input. Add wallets that "
            "the proxy rule would score differently (e.g. low-activity or "
            "higher-failure-rate wallets) before proceeding."
        )
        sys.exit(1)

    if len(feature_df) >= 6:
        # Small-sample stratified split; only meaningful as a sanity check,
        # not a real generalization estimate, at n this small.
        X_train, X_test, y_train, y_test = train_test_split(
            feature_df, labels, test_size=0.3, random_state=42, stratify=labels
        )
        model, scaler = train_credit_model(X_train, y_train)
        X_test_mat = scaler.transform(_get_feature_matrix(X_test))
        y_pred = model.predict(X_test_mat)
        print("\n--- Credit model held-out evaluation (n is tiny, treat as a smoke test) ---")
        print(classification_report(y_test, y_pred, zero_division=0))
        try:
            y_proba = model.predict_proba(X_test_mat)[:, 1]
            print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")
        except ValueError as e:
            print(f"ROC-AUC unavailable: {e}")
        # Refit on all data for the model that actually gets saved/served.
        print("Refitting credit model on all training wallets for deployment...")
        train_credit_model(feature_df, labels)
    else:
        print("Too few wallets for a held-out split; fitting on all data with no evaluation.")
        train_credit_model(feature_df, labels)

    # --- Fraud model: unsupervised, trained ONLY on presumed-normal wallets ---
    print("\nTraining fraud (Isolation Forest) model on presumed-normal wallets only...")
    fraud_model, fraud_scaler = train_fraud_model(feature_df)

    # --- Sanity check: does it actually flag known phishing addresses? -----
    print("\n--- Fraud model sanity check against held-out KNOWN phishing addresses ---")
    print("(these were NOT used in training)")
    eval_rows = _fetch_features(KNOWN_FRAUD_ADDRESSES_FOR_EVAL)
    if eval_rows.empty:
        print("Could not fetch any known-fraud addresses to evaluate against.")
    else:
        for addr, (_, row) in zip(KNOWN_FRAUD_ADDRESSES_FOR_EVAL, eval_rows.iterrows()):
            prob, is_fraud = predict_fraud(fraud_model, fraud_scaler, row)
            print(f"  {addr}: fraud_probability={prob:.3f}  is_fraud={is_fraud}")
        print(
            "If these mostly show LOW fraud_probability, the model isn't "
            "actually separating fraud from normal on these features -- "
            "that's a real finding, not something to hide. It likely means "
            "the current 13 features don't capture what makes these "
            "particular wallets look like phishing wallets."
        )

    print("\nDone. Credit and fraud models saved to backend/models/.")
    print(
        f"REMINDER: training set is still only {len(feature_df)} wallets, "
        "all high-activity. This is a demo-scale detector, not a validated "
        "one. Add more addresses across varied activity levels before "
        "presenting results as reliable."
    )


if __name__ == "__main__":
    main()
