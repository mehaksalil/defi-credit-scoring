"""
Step 2: Data pipeline — fetch and normalize wallet transaction data.

Why Etherscan API (not only Web3):
- Web3 requires an RPC node and block-by-block scanning to get "all txs for an address."
- Etherscan already indexes this; one HTTP call returns a paginated list.
- Free tier is enough for development; we use it as the single source of truth for txs.

Why normalize to a fixed schema:
- Feature engineering (Step 3) expects consistent column names and types.
- We store value in wei (int) and add timestamp as datetime so we can compute age, frequency, etc.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from app.config import (
    DATA_DIR,
    ETHERSCAN_API_KEY,
    ETHERSCAN_BASE_URL,
    ETHERSCAN_CHAIN_ID,
    MAX_TXS_PER_WALLET,
)

# Etherscan returns addresses and numbers as strings; we normalize to this schema
NORMAL_COLUMNS = [
    "block_number",
    "timestamp",       # Unix (int)
    "hash",
    "from_address",
    "to_address",
    "value_wei",       # int
    "gas",
    "gas_price",
    "gas_used",
    "is_error",        # 0 = success, 1 = reverted
]


def _validate_address(address: str) -> str:
    """Ensure address is 0x + 40 hex chars (Ethereum)."""
    a = address.strip()
    if not re.fullmatch(r"0x[a-fA-F0-9]{40}", a):
        raise ValueError(f"Invalid Ethereum address: {address}")
    return a


def _int_safe(s: Any) -> int:
    """Parse string/int to int; 0 if missing or invalid."""
    if s is None or s == "":
        return 0
    if isinstance(s, int):
        return s
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


def fetch_transactions_etherscan(address: str) -> list[dict[str, Any]]:
    """
    Fetch normal (external) transactions for one address from Etherscan.
    Paginates until we have up to MAX_TXS_PER_WALLET transactions.
    """
    address = _validate_address(address)
    all_txs: list[dict[str, Any]] = []
    page = 1
    offset = 1000  # Etherscan max per page is 10000; 1000 is a safe default

    with httpx.Client(timeout=30.0) as client:
        while len(all_txs) < MAX_TXS_PER_WALLET:
            params: dict[str, Any] = {
                "chainid": ETHERSCAN_CHAIN_ID,  # V2 required: 1 = Ethereum mainnet
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99999999,
                "page": page,
                "offset": offset,
                "sort": "asc",  # oldest first so we can compute wallet age
            }
            if ETHERSCAN_API_KEY:
                params["apikey"] = ETHERSCAN_API_KEY

            resp = client.get(ETHERSCAN_BASE_URL, params=params)
            data = resp.json()

            if data.get("status") != "1" or data.get("message") != "OK":
                msg = data.get("message", "Unknown error")
                result = data.get("result")
                if isinstance(result, str):
                    raise RuntimeError(f"Etherscan API error: {result}")
                raise RuntimeError(f"Etherscan API error: {msg}")

            result = data.get("result")
            if isinstance(result, str):
                # e.g. "No transactions found"
                result = []
            if result is None:
                result = []
            if not isinstance(result, list):
                raise RuntimeError(f"Unexpected Etherscan result type: {type(result)}")

            if not result:
                break

            for tx in result:
                if not isinstance(tx, dict):
                    continue
                all_txs.append(tx)
                if len(all_txs) >= MAX_TXS_PER_WALLET:
                    break

            if len(result) < offset:
                break
            page += 1

    return all_txs


def normalize_transactions(raw_txs: list[dict[str, Any]], wallet_address: str) -> pd.DataFrame:
    """
    Convert Etherscan-style transaction list to a DataFrame with fixed schema.
    Feature engineering will rely on these column names and types.
    """
    if not raw_txs:
        return pd.DataFrame(columns=NORMAL_COLUMNS)

    rows = []
    for tx in raw_txs:
        rows.append({
            "block_number": _int_safe(tx.get("blockNumber")),
            "timestamp": _int_safe(tx.get("timeStamp")),
            "hash": str(tx.get("hash", "")),
            "from_address": str(tx.get("from", "")).lower(),
            "to_address": str(tx.get("to", "")).lower() if tx.get("to") else "",
            "value_wei": _int_safe(tx.get("value")),
            "gas": _int_safe(tx.get("gas")),
            "gas_price": _int_safe(tx.get("gasPrice")),
            "gas_used": _int_safe(tx.get("gasUsed")),
            "is_error": _int_safe(tx.get("isError")),
        })

    df = pd.DataFrame(rows)
    # Tag which side of the tx is our wallet (for inflow/outflow in Step 3)
    df["is_outgoing"] = (df["from_address"] == wallet_address.lower())
    return df


def get_transactions(address: str, use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch transactions for a wallet and return a normalized DataFrame.
    If use_cache is True and we have a cached file for this address, load it instead of re-fetching.
    """
    address = _validate_address(address)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = DATA_DIR / f"txs_{address.lower()}.json"

    if use_cache and cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            raw = json.load(f)
        raw_txs = raw if isinstance(raw, list) else raw.get("result", raw)
        return normalize_transactions(raw_txs, address)

    raw_txs = fetch_transactions_etherscan(address)
    # Cache raw response so we can re-normalize later if schema changes
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(raw_txs, f, indent=0)
    return normalize_transactions(raw_txs, address)
