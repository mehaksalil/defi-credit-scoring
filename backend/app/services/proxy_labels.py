"""
Step 4: Proxy labels for credit scoring.

We don't have true "defaulted" labels on-chain, so we use heuristic rules to mark
wallets as "good" (1) or "bad" (0) for training. The model learns from these proxies.

Rules (conservative):
- Good: some history (age + tx count), low failure rate, some counterparty diversity.
- Bad: very few txs, or high failed_tx_ratio, or no diversity.
"""
from __future__ import annotations

import pandas as pd


def proxy_label_from_features(row: pd.Series) -> int:
    """
    Return 1 (creditworthy) or 0 (not) from a single feature row.
    Used to build training labels when we have no real default data.
    """
    age = row.get("wallet_age_days", 0) or 0
    tx_count = row.get("tx_count", 0) or 0
    failed_ratio = row.get("failed_tx_ratio", 1.0) or 1.0
    unique_cp = row.get("unique_counterparties", 0) or 0

    # Clearly bad: almost no activity or very high failure rate
    if tx_count < 3:
        return 0
    if failed_ratio > 0.25:
        return 0
    # Good: enough history, low failure, some diversity
    if age >= 30 and tx_count >= 10 and failed_ratio <= 0.1 and unique_cp >= 2:
        return 1
    # Moderate activity and low failure -> good
    if tx_count >= 5 and failed_ratio <= 0.15 and unique_cp >= 1:
        return 1
    return 0


def proxy_labels_for_dataframe(feature_df: pd.DataFrame) -> pd.Series:
    """Apply proxy_label_from_features to each row. Index preserved."""
    return feature_df.apply(proxy_label_from_features, axis=1)
