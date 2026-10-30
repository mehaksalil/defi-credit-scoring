"""Train behavioral credit scoring from the supplied raw-transaction archive.

Run from ``backend/``:
    .\\venv\\Scripts\\python.exe train_behavioral_credit_model.py

The source has no credit/default labels.  The model therefore produces a
behavioral-normality score, not a repayment prediction.  CSVs are streamed in
chunks; only per-wallet aggregate statistics are retained in memory.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.credit_model import train_behavioral_credit_model
from app.services.features import FEATURE_NAMES

# The archives sit beside the project directory, not inside backend/.
DEFAULT_ARCHIVE = Path(__file__).resolve().parents[2] / "archive (1).zip"
DATASETS = ("first_order_df.csv", "second_order_df.csv")
MAX_COUNTERPARTIES_PER_WALLET = 128


def _empty_stats() -> dict:
    return {
        "min_ts": float("inf"), "max_ts": 0.0, "count": 0, "total": 0.0,
        "out": 0.0, "incoming": 0.0, "out_sq": 0.0, "in_sq": 0.0,
        "out_count": 0, "in_count": 0, "errors": 0, "counterparties": set(),
    }


def _add(
    stats: dict, address: str, counterparty: str, timestamp: float,
    value_wei: float, is_error: int, outgoing: bool,
) -> None:
    if not address or address == "nan":
        return
    stats["min_ts"] = min(stats["min_ts"], timestamp)
    stats["max_ts"] = max(stats["max_ts"], timestamp)
    stats["count"] += 1
    stats["total"] += value_wei
    stats["errors"] += is_error
    if len(stats["counterparties"]) < MAX_COUNTERPARTIES_PER_WALLET and counterparty and counterparty != "nan":
        stats["counterparties"].add(counterparty)
    if outgoing:
        stats["out"] += value_wei
        stats["out_sq"] += value_wei * value_wei
        stats["out_count"] += 1
    else:
        stats["incoming"] += value_wei
        stats["in_sq"] += value_wei * value_wei
        stats["in_count"] += 1


def _std(total: float, total_sq: float, count: int) -> float:
    if count < 2:
        return 0.0
    return math.sqrt(max(total_sq / count - (total / count) ** 2, 0.0))


def _to_features(address: str, stats: dict) -> dict:
    age_days = max((stats["max_ts"] - stats["min_ts"]) / 86400.0, 0.0)
    count = stats["count"]
    # A streaming pass cannot calculate an exact median. Mean transfer value is
    # used as a documented, stable proxy for this one feature.
    mean_value = stats["total"] / max(count, 1)
    return {
        "address": address,
        "wallet_age_days": age_days,
        "tx_count": count,
        "tx_frequency_per_day": count / max(age_days, 1.0),
        "total_volume_wei": stats["total"],
        "avg_value_wei": mean_value,
        "median_value_wei": mean_value,
        "total_outflow_wei": stats["out"],
        "total_inflow_wei": stats["incoming"],
        "failed_tx_ratio": stats["errors"] / max(count, 1),
        # The raw data does not include calldata, so contract interaction is
        # unavailable for historical training examples.
        "contract_interaction_ratio": 0.0,
        "outflow_volatility_wei": _std(stats["out"], stats["out_sq"], stats["out_count"]),
        "inflow_volatility_wei": _std(stats["incoming"], stats["in_sq"], stats["in_count"]),
        "unique_counterparties": len(stats["counterparties"]),
    }


def _is_sampled(address: str, sample_rate: float) -> bool:
    """Stable address sampling, avoiding an unbounded all-wallets dictionary."""
    if not address or address == "nan":
        return False
    bucket = int.from_bytes(hashlib.blake2b(address.encode(), digest_size=8).digest(), "big")
    return bucket / 2**64 < sample_rate


def build_feature_dataframe(
    archive_path: Path, chunk_size: int, max_wallets: int, sample_rate: float,
) -> pd.DataFrame:
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")
    wallets: dict[str, dict] = defaultdict(_empty_stats)

    with zipfile.ZipFile(archive_path) as archive:
        for name in DATASETS:
            if name not in archive.namelist():
                raise ValueError(f"{name} is missing from {archive_path}")
            print(f"Reading {name} in {chunk_size:,}-row chunks...")
            with archive.open(name) as stream:
                for number, chunk in enumerate(pd.read_csv(stream, chunksize=chunk_size), start=1):
                    required = {"From", "To", "TimeStamp", "Value", "isError"}
                    if not required.issubset(chunk.columns):
                        raise ValueError(f"{name} does not have required columns: {sorted(required)}")
                    rows = zip(
                        chunk["From"].astype(str).str.lower(),
                        chunk["To"].astype(str).str.lower(),
                        pd.to_numeric(chunk["TimeStamp"], errors="coerce").fillna(0.0),
                        pd.to_numeric(chunk["Value"], errors="coerce").fillna(0.0),
                        pd.to_numeric(chunk["isError"], errors="coerce").fillna(0).astype(int),
                    )
                    for sender, recipient, timestamp, value, error in rows:
                        # A few source rows have missing addresses; pandas can
                        # represent those as float NaN despite the string cast.
                        sender = str(sender).lower()
                        recipient = str(recipient).lower()
                        value_wei = max(float(value), 0.0) * 1e18
                        if _is_sampled(sender, sample_rate):
                            _add(wallets[sender], sender, recipient, float(timestamp), value_wei, int(error), True)
                        if _is_sampled(recipient, sample_rate):
                            _add(wallets[recipient], recipient, sender, float(timestamp), value_wei, int(error), False)
                    if number % 10 == 0:
                        print(f"  processed {number * chunk_size:,}+ rows; wallets seen: {len(wallets):,}")

    eligible = [address for address, stats in wallets.items() if stats["count"] >= 5]
    if len(eligible) > max_wallets:
        eligible = list(np.random.default_rng(42).choice(eligible, size=max_wallets, replace=False))
    print(f"Building features for {len(eligible):,} wallets (minimum 5 transactions)...")
    return pd.DataFrame([_to_features(address, wallets[address]) for address in eligible])[FEATURE_NAMES]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--chunk-size", type=int, default=250_000)
    parser.add_argument("--max-wallets", type=int, default=100_000)
    parser.add_argument("--sample-rate", type=float, default=0.02)
    args = parser.parse_args()
    if not 0 < args.sample_rate <= 1:
        parser.error("--sample-rate must be greater than 0 and at most 1")
    features = build_feature_dataframe(args.archive, args.chunk_size, args.max_wallets, args.sample_rate)
    bundle = train_behavioral_credit_model(features)
    print(f"Saved behavioral_credit_model.joblib trained on {bundle['training_wallets']:,} wallets.")


if __name__ == "__main__":
    main()
