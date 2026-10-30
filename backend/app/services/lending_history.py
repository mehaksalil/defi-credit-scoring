"""Read verified lending activity from LendingPool events on the configured chain.

This module reports facts from confirmed contract logs and current contract state.
It deliberately does not assign credit points; scoring policy is a separate step.
"""
from __future__ import annotations

from decimal import Decimal
import os
from typing import Any

from web3 import Web3

from app.config import CHAIN_ID, ETH_RPC_URL, LENDING_POOL_ADDRESS, LENDING_POOL_DEPLOYMENT_BLOCK

LENDING_POOL_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "Deposit", "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "Withdraw", "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "Borrow", "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "Repay", "type": "event",
    },
    {
        "inputs": [], "name": "token", "outputs": [{"type": "address", "name": ""}],
        "stateMutability": "view", "type": "function",
    },
    {
        "inputs": [{"type": "address", "name": ""}],
        "name": "collateral", "outputs": [{"type": "uint256", "name": ""}],
        "stateMutability": "view", "type": "function",
    },
    {
        "inputs": [{"type": "address", "name": ""}],
        "name": "debt", "outputs": [{"type": "uint256", "name": ""}],
        "stateMutability": "view", "type": "function",
    },
]

TOKEN_ABI = [
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8", "name": ""}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"type": "string", "name": ""}], "stateMutability": "view", "type": "function"},
]

EVENT_NAMES = ("Deposit", "Withdraw", "Borrow", "Repay")
DEPLOYMENT_BLOCK = max(0, LENDING_POOL_DEPLOYMENT_BLOCK)
BLOCK_CHUNK_SIZE = max(1, int(os.getenv("LENDING_HISTORY_BLOCK_CHUNK_SIZE", "1000")))


class LendingHistoryError(RuntimeError):
    """Raised when the configured chain or LendingPool history cannot be read."""


def _format_amount(raw_amount: int, decimals: int) -> float:
    return float(Decimal(int(raw_amount)) / (Decimal(10) ** decimals))


def _get_event_logs(event, start_block: int, end_block: int, address: str):
    """Support both snake_case and camelCase web3.py event APIs."""
    try:
        return event.get_logs(
            from_block=start_block,
            to_block=end_block,
            argument_filters={"user": address},
        )
    except TypeError as snake_case_error:
        try:
            return event.get_logs(
                fromBlock=start_block,
                toBlock=end_block,
                argument_filters={"user": address},
            )
        except TypeError:
            raise snake_case_error


def get_lending_history(address: str) -> dict[str, Any]:
    """Return confirmed event totals and current LendingPool state for a wallet."""
    if not Web3.is_address(address):
        raise ValueError("Invalid Ethereum wallet address")
    if not ETH_RPC_URL:
        raise LendingHistoryError("ETH_RPC_URL is not configured")
    if not LENDING_POOL_ADDRESS:
        raise LendingHistoryError("LENDING_POOL_ADDRESS is not configured")

    wallet = Web3.to_checksum_address(address)
    pool_address = Web3.to_checksum_address(LENDING_POOL_ADDRESS)
    w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL, request_kwargs={"timeout": 10}))
    try:
        if not w3.is_connected():
            raise LendingHistoryError(f"Cannot connect to configured chain at {ETH_RPC_URL}")
        actual_chain_id = int(w3.eth.chain_id)
        if actual_chain_id != CHAIN_ID:
            raise LendingHistoryError(
                f"Connected chain ID is {actual_chain_id}, but backend CHAIN_ID is {CHAIN_ID}. "
                "Check ETH_RPC_URL and CHAIN_ID."
            )
        code = w3.eth.get_code(pool_address)
        if not code or bytes(code) == b"":
            raise LendingHistoryError(
                f"No contract code found at LendingPool {pool_address}. "
                "Check that Hardhat is running and the deployed address matches backend/.env."
            )

        pool = w3.eth.contract(address=pool_address, abi=LENDING_POOL_ABI)
        token_address = Web3.to_checksum_address(pool.functions.token().call())
        token = w3.eth.contract(address=token_address, abi=TOKEN_ABI)
        decimals = int(token.functions.decimals().call())
        try:
            symbol = token.functions.symbol().call()
        except Exception:
            symbol = "TOKEN"

        latest_block = int(w3.eth.block_number)
        start_block = max(0, DEPLOYMENT_BLOCK)
        if start_block > latest_block:
            start_block = latest_block

        all_events: list[dict[str, Any]] = []
        totals_raw = {name: 0 for name in EVENT_NAMES}
        counts = {name: 0 for name in EVENT_NAMES}

        for chunk_start in range(start_block, latest_block + 1, BLOCK_CHUNK_SIZE):
            chunk_end = min(chunk_start + BLOCK_CHUNK_SIZE - 1, latest_block)
            for event_name in EVENT_NAMES:
                event_factory = getattr(pool.events, event_name)
                decoded_logs = _get_event_logs(event_factory(), chunk_start, chunk_end, wallet)
                for log in decoded_logs:
                    args = log["args"]
                    amount_raw = int(args["amount"])
                    totals_raw[event_name] += amount_raw
                    counts[event_name] += 1
                    tx_hash = log.get("transactionHash")
                    all_events.append({
                        "type": event_name.lower(),
                        "amount": _format_amount(amount_raw, decimals),
                        "amount_raw": str(amount_raw),
                        "block_number": int(log["blockNumber"]),
                        "transaction_hash": tx_hash.hex() if tx_hash is not None else "",
                        "log_index": int(log.get("logIndex", 0)),
                    })

        all_events.sort(key=lambda item: (item["block_number"], item["log_index"]), reverse=True)
        current_collateral = int(pool.functions.collateral(wallet).call())
        current_debt = int(pool.functions.debt(wallet).call())

        return {
            "address": wallet,
            "pool_address": pool_address,
            "token_address": token_address,
            "token_symbol": symbol,
            "token_decimals": decimals,
            "from_block": start_block,
            "to_block": latest_block,
            "event_count": len(all_events),
            "counts": {name.lower(): counts[name] for name in EVENT_NAMES},
            "totals": {
                "deposited": _format_amount(totals_raw["Deposit"], decimals),
                "withdrawn": _format_amount(totals_raw["Withdraw"], decimals),
                "borrowed": _format_amount(totals_raw["Borrow"], decimals),
                "repaid": _format_amount(totals_raw["Repay"], decimals),
            },
            "current_state": {
                "collateral": _format_amount(current_collateral, decimals),
                "debt": _format_amount(current_debt, decimals),
            },
            # Keep the response small while aggregates above use all retrieved logs.
            "recent_events": all_events[:20],
            "history_source": "confirmed_lending_pool_events",
        }
    except LendingHistoryError:
        raise
    except ValueError:
        raise
    except Exception as exc:
        raise LendingHistoryError(f"Could not read LendingPool history: {exc}") from exc
