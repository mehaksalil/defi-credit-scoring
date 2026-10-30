"""
Step 3: Feature engineering — turn normalized transaction DataFrame into one feature vector per wallet.

Why these features:
- Wallet age, tx count, frequency: longevity and activity (proxy for "reputation").
- Avg/median value, volume: size of activity; helps separate whales from small users.
- Failed tx ratio: reverted txs suggest poor planning or malicious probing.
- Contract interaction ratio: value=0 often means DeFi/smart contract call; more = more DeFi exposure.
- Inflow/outflow volatility: erratic flows can indicate risk or wash trading.
- Unique counterparties: diversity of counterparties; very low can be suspicious.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Ordered list so training and inference use the same columns. Used in Step 4.
FEATURE_NAMES = [
    "wallet_age_days",
    "tx_count",
    "tx_frequency_per_day",
    "total_volume_wei",
    "avg_value_wei",
    "median_value_wei",
    "total_outflow_wei",
    "total_inflow_wei",
    "failed_tx_ratio",
    "contract_interaction_ratio",
    "outflow_volatility_wei",
    "inflow_volatility_wei",
    "unique_counterparties",
]


def compute_features(df: pd.DataFrame, wallet_address: str) -> pd.Series:
    """
    Compute one feature vector from a normalized transaction DataFrame for the given wallet.
    Returns a pd.Series with FEATURE_NAMES as index. Safe for empty DataFrame.
    """
    wallet = wallet_address.lower().strip()
    out = {}

    if df is None or len(df) == 0:
        for name in FEATURE_NAMES:
            out[name] = 0.0
        return pd.Series(out)

    # --- Time-based ---
    ts = df["timestamp"]
    min_ts, max_ts = ts.min(), ts.max()
    wallet_age_seconds = max(max_ts - min_ts, 0)
    wallet_age_days = wallet_age_seconds / 86400.0
    out["wallet_age_days"] = wallet_age_days
    out["tx_count"] = len(df)
    out["tx_frequency_per_day"] = len(df) / max(wallet_age_days, 1.0)

    # --- Value-based (all txs). Use float64: wei can exceed np.int64 (e.g. 1e18 = 1 ETH). ---
    value = pd.to_numeric(df["value_wei"], errors="coerce").fillna(0).astype(np.float64)
    out["total_volume_wei"] = float(value.sum())
    out["avg_value_wei"] = float(value.mean())
    out["median_value_wei"] = float(value.median())

    # --- Inflow / outflow from wallet perspective ---
    outgoing = df[df["is_outgoing"]].copy()
    incoming = df[~df["is_outgoing"]].copy()
    outgoing_val = pd.to_numeric(outgoing["value_wei"], errors="coerce").fillna(0).astype(np.float64)
    incoming_val = pd.to_numeric(incoming["value_wei"], errors="coerce").fillna(0).astype(np.float64)
    out["total_outflow_wei"] = float(outgoing_val.sum())
    out["total_inflow_wei"] = float(incoming_val.sum())

    # --- Reliability ---
    out["failed_tx_ratio"] = float(df["is_error"].mean())

    # --- DeFi / contract interaction heuristic: value 0 often means contract call ---
    contract_like = (value == 0) & (df["to_address"] != "")
    out["contract_interaction_ratio"] = float(contract_like.mean())

    # --- Volatility (std of transfer amounts; use 0 if no txs in that direction) ---
    out["outflow_volatility_wei"] = float(outgoing_val.std()) if len(outgoing) > 1 else 0.0
    out["inflow_volatility_wei"] = float(incoming_val.std()) if len(incoming) > 1 else 0.0
    # Replace NaN from single-tx case
    if np.isnan(out["outflow_volatility_wei"]):
        out["outflow_volatility_wei"] = 0.0
    if np.isnan(out["inflow_volatility_wei"]):
        out["inflow_volatility_wei"] = 0.0

    # --- Counterparty diversity ---
    from_addrs = set(df["from_address"].dropna()) - {wallet}
    to_addrs = set(df["to_address"].dropna()) - {wallet, ""}
    out["unique_counterparties"] = float(len(from_addrs | to_addrs))

    return pd.Series(out)


def get_feature_df_for_wallet(df: pd.DataFrame, wallet_address: str) -> pd.DataFrame:
    """
    Return a single-row DataFrame with FEATURE_NAMES columns, for use in the API or model.
    """
    s = compute_features(df, wallet_address)
    return pd.DataFrame([s])[FEATURE_NAMES]
