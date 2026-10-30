"""
Step 7 gap fix: on-chain oracle bridge.

The backend computes credit score + fraud flag (see credit_model.py / fraud_model.py)
but on its own never writes them anywhere the LendingPool contract can see. This
module closes that gap: it signs and submits `setCreditData(user, score, isFraud)`
using a private key that lives ONLY in this backend's environment.

SECURITY NOTES (read before using this outside a local demo):
- ORACLE_PRIVATE_KEY must come from an environment variable on the backend host.
  It is never accepted as a request parameter and never returned in a response.
- This module intentionally does not implement real key management (no KMS/HSM,
  no multisig, no rotation). For anything beyond a local sandbox, the oracle key
  should be held by a dedicated signer service, ideally behind a multisig or
  threshold-signature scheme, with rate limiting and monitoring on top.
- The `/sync-onchain` and `/faucet` API endpoints that call into this module are
  gated by a single static shared-secret header (ORACLE_API_KEY). That is a
  demo-grade speed bump, not real authentication/authorization.
"""
from __future__ import annotations

from functools import lru_cache

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app.config import (
    CHAIN_ID,
    ETH_RPC_URL,
    LENDING_POOL_ADDRESS,
    ORACLE_PRIVATE_KEY,
    TOKEN_ADDRESS,
)

# Minimal ABIs -- only the functions this bridge actually calls.
LENDING_POOL_ABI = [
    {
        "inputs": [
            {"name": "user", "type": "address"},
            {"name": "score", "type": "uint256"},
            {"name": "fraud", "type": "bool"},
        ],
        "name": "setCreditData",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "creditOracle",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]

MOCK_ERC20_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class OracleConfigError(RuntimeError):
    """Raised when required on-chain env vars are missing."""


class OracleTransactionError(RuntimeError):
    """Raised when a signed transaction fails to send or reverts."""


def _require_config() -> None:
    missing = []
    if not ETH_RPC_URL:
        missing.append("ETH_RPC_URL")
    if not ORACLE_PRIVATE_KEY:
        missing.append("ORACLE_PRIVATE_KEY")
    if not LENDING_POOL_ADDRESS:
        missing.append("LENDING_POOL_ADDRESS")
    if missing:
        raise OracleConfigError(
            "Missing required on-chain oracle env vars: " + ", ".join(missing)
        )


@lru_cache(maxsize=1)
def _get_web3() -> Web3:
    _require_config()
    w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL))
    # Harmless on a plain Hardhat node; needed if pointed at a PoA testnet later.
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected():
        raise OracleTransactionError(f"Could not connect to ETH_RPC_URL={ETH_RPC_URL}")
    return w3


def _get_oracle_account(w3: Web3):
    return w3.eth.account.from_key(ORACLE_PRIVATE_KEY)


def _send_signed(w3: Web3, account, tx: dict) -> str:
    """Sign a transaction dict with the oracle's private key and broadcast it."""
    signed = w3.eth.account.sign_transaction(tx, private_key=ORACLE_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    if receipt.status != 1:
        raise OracleTransactionError(f"Transaction reverted: {tx_hash.hex()}")
    return tx_hash.hex()


def sync_credit_onchain(address: str, score: float, is_fraud: bool) -> dict:
    """
    Sign and submit LendingPool.setCreditData(address, round(score), is_fraud).

    Raises OracleConfigError if env vars are missing, OracleTransactionError if
    the transaction fails to send or is reverted on-chain (e.g. because the
    configured key is not the contract's creditOracle).
    """
    _require_config()
    w3 = _get_web3()
    account = _get_oracle_account(w3)

    pool = w3.eth.contract(
        address=Web3.to_checksum_address(LENDING_POOL_ADDRESS), abi=LENDING_POOL_ABI
    )

    # Conservative conversion: never round a score upward.
    score_int = int(max(0, min(100, score))) # mirror the contract's own bounds check

    nonce = w3.eth.get_transaction_count(account.address, "pending")
    tx = pool.functions.setCreditData(
        Web3.to_checksum_address(address), score_int, bool(is_fraud)
    ).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": CHAIN_ID,
        }
    )
    tx_hash = _send_signed(w3, account, tx)
    return {
        "address": Web3.to_checksum_address(address),
        "score": score_int,
        "is_fraud": bool(is_fraud),
        "tx_hash": tx_hash,
        "lending_pool_address": Web3.to_checksum_address(LENDING_POOL_ADDRESS),
    }


def mint_test_tokens(address: str, amount_ether: float) -> dict:
    """
    Local-demo faucet: mint MOCK test tokens to `address` using the same
    oracle/deployer key. Only meaningful against a local Hardhat network with
    a MockERC20 whose `owner` is this same account -- never use against a
    real network.
    """
    _require_config()
    if not TOKEN_ADDRESS:
        raise OracleConfigError("Missing required env var: TOKEN_ADDRESS")

    w3 = _get_web3()
    account = _get_oracle_account(w3)

    token = w3.eth.contract(
        address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=MOCK_ERC20_ABI
    )

    amount_wei = w3.to_wei(amount_ether, "ether")
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    tx = token.functions.mint(
        Web3.to_checksum_address(address), amount_wei
    ).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": CHAIN_ID,
        }
    )
    tx_hash = _send_signed(w3, account, tx)
    return {
        "address": Web3.to_checksum_address(address),
        "amount": amount_ether,
        "tx_hash": tx_hash,
        "token_address": Web3.to_checksum_address(TOKEN_ADDRESS),
    }
