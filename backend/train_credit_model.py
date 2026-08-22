"""
Train the credit scoring model: fetch transactions for a list of addresses,
compute features, apply proxy labels, train XGBoost, save model and scaler.

Run from backend/:
  python train_credit_model.py

Requires ETHERSCAN_API_KEY in .env. Uses cache when available.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path so "app" resolves
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from app.services.blockchain_data import get_transactions
from app.services.credit_model import train_credit_model
from app.services.features import compute_features, FEATURE_NAMES
from app.services.fraud_model import train_fraud_model

# Example addresses to build training data (mix of active wallets; replace or extend as needed)
DEFAULT_ADDRESSES = [
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # Vitalik
    "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance 14
    "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503",  # Binance 8
    "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3",  # Coinbase 1
    "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43",  # Coinbase 2
    "0x5041ed759Dd4aFc3a72b8192C143F72f4724081A",  # Rainbow
    "0xDA9dfA130Df4dE4673b89022EE50ff26f6EA73cf",  # Example EOA
]


def main() -> None:
    rows = []
    for i, addr in enumerate(DEFAULT_ADDRESSES):
        print(f"Fetching features for {addr} ({i+1}/{len(DEFAULT_ADDRESSES)})...")
        try:
            df = get_transactions(addr, use_cache=True)
            feats = compute_features(df, addr)
            rows.append(feats)
        except Exception as e:
            print(f"  Skip {addr}: {e}")
    if not rows:
        print("No feature rows; add addresses or check Etherscan API key.")
        sys.exit(1)
    feature_df = pd.DataFrame(rows)[FEATURE_NAMES]
    print(f"Training on {len(feature_df)} wallets...")
    train_credit_model(feature_df)
    print("Training fraud (Isolation Forest) model...")
    train_fraud_model(feature_df)
    print("Done. Credit and fraud models saved to backend/models/.")


if __name__ == "__main__":
    main()
