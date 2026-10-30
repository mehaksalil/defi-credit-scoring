"""
Integration tests for the on-chain oracle bridge and its API endpoints.

These tests are NOT unit tests with mocks -- they exercise real signed
transactions against a real (local) Ethereum node, because the whole point of
this bridge is "does a signed setCreditData/mint transaction actually land
on-chain correctly". Mocking web3 would just test that our mock was called.

Prerequisites to run this file:
  1. A local Hardhat node running:            npx hardhat node
  2. Contracts deployed to it:                 npx hardhat run scripts/deploy.js --network localhost
  3. backend/.env (or exported env vars) pointing at that deployment:
       ETH_RPC_URL=http://127.0.0.1:8545
       ORACLE_PRIVATE_KEY=<hardhat account #0 private key, printed by `hardhat node`>
       LENDING_POOL_ADDRESS=<from deployed-addresses.json>
       TOKEN_ADDRESS=<from deployed-addresses.json>
       CHAIN_ID=31337
       ORACLE_API_KEY=test-local-secret

If those aren't set, these tests are skipped rather than failed, since they
depend on infrastructure this test file cannot spin up itself (a JS/Hardhat
process, not a Python one).

Run with:  pytest backend/tests/test_oracle_and_api.py -v
"""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from web3 import Web3

from app.config import LENDING_POOL_ADDRESS, ORACLE_API_KEY, ORACLE_PRIVATE_KEY, TOKEN_ADDRESS
from app.services import oracle

pytestmark = pytest.mark.skipif(
    not (ORACLE_PRIVATE_KEY and LENDING_POOL_ADDRESS and TOKEN_ADDRESS),
    reason=(
        "Requires a live local Hardhat node with contracts deployed and "
        "ORACLE_PRIVATE_KEY/LENDING_POOL_ADDRESS/TOKEN_ADDRESS set in the "
        "environment. See module docstring."
    ),
)

# A funded local Hardhat test account (#2 by default from deploy.js), distinct
# from the oracle/deployer account, used as the "user" in these tests.
TEST_USER = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"


def _make_client():
    import app.main as m

    return TestClient(m.app)


def test_oracle_module_writes_score_onchain():
    result = oracle.sync_credit_onchain(TEST_USER, score=81.9, is_fraud=False)
    assert result["score"] == 82  # rounded
    assert result["is_fraud"] is False
    assert result["tx_hash"]

    # Verify independently by reading the contract directly.
    w3 = Web3(Web3.HTTPProvider(os.environ.get("ETH_RPC_URL", "http://127.0.0.1:8545")))
    pool_abi = [
        {
            "inputs": [{"name": "", "type": "address"}],
            "name": "creditScore",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    pool = w3.eth.contract(address=LENDING_POOL_ADDRESS, abi=pool_abi)
    assert pool.functions.creditScore(TEST_USER).call() == 82


def test_oracle_rejects_score_above_100_before_it_even_reaches_the_chain():
    # The Python bridge clamps to [0, 100] before sending, mirroring the
    # contract's own require(score <= 100). Confirm the clamp actually happens.
    result = oracle.sync_credit_onchain(TEST_USER, score=150, is_fraud=False)
    assert result["score"] == 100


def test_faucet_mints_tokens():
    w3 = Web3(Web3.HTTPProvider(os.environ.get("ETH_RPC_URL", "http://127.0.0.1:8545")))
    token_abi = [
        {
            "inputs": [{"name": "", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    token = w3.eth.contract(address=TOKEN_ADDRESS, abi=token_abi)
    before = token.functions.balanceOf(TEST_USER).call()

    oracle.mint_test_tokens(TEST_USER, amount_ether=42)

    after = token.functions.balanceOf(TEST_USER).call()
    assert after - before == w3.to_wei(42, "ether")


@pytest.mark.skipif(not ORACLE_API_KEY, reason="Requires ORACLE_API_KEY set to exercise the HTTP endpoint's auth")
def test_sync_endpoint_requires_correct_header():
    with patch(
        "app.main.get_credit_score_for_wallet",
        return_value={"address": TEST_USER, "score": 65.0, "risk_level": "Medium"},
    ), patch(
        "app.main.get_fraud_for_wallet",
        return_value={"fraud_probability": 0.05, "is_fraud": False},
    ):
        client = _make_client()

        r = client.post(f"/wallet/{TEST_USER}/sync-onchain")
        assert r.status_code == 401

        r = client.post(f"/wallet/{TEST_USER}/sync-onchain", headers={"X-Oracle-Key": "wrong"})
        assert r.status_code == 401

        r = client.post(
            f"/wallet/{TEST_USER}/sync-onchain",
            headers={"X-Oracle-Key": ORACLE_API_KEY},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["synced_score"] == 65
        assert body["synced_is_fraud"] is False
        assert body["tx_hash"]
