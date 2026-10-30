"""
Load config from environment. Keeps API keys out of code.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Etherscan: free tier ~5 calls/sec. Get key at https://etherscan.io/apis
# V2 base (V1 deprecated Aug 2025): https://docs.etherscan.io/v2-migration
ETHERSCAN_API_KEY: str = os.getenv("ETHERSCAN_API_KEY", "")
ETHERSCAN_BASE_URL: str = "https://api.etherscan.io/v2/api"
ETHERSCAN_CHAIN_ID: int = int(os.getenv("ETHERSCAN_CHAIN_ID", "1"))  # 1 = Ethereum mainnet

# Max transactions to fetch per wallet (Etherscan returns up to 10k per page; we cap for speed)
MAX_TXS_PER_WALLET: int = int(os.getenv("MAX_TXS_PER_WALLET", "2000"))

# Where to cache raw/processed data (relative to backend/)
DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"

# --- On-chain oracle bridge (Step 7 gap fix) --------------------------------
# These control the backend's ability to write ML results on-chain via
# LendingPool.setCreditData(user, score, isFraud). For a purely local Hardhat
# demo, ETH_RPC_URL is usually http://127.0.0.1:8545 and ORACLE_PRIVATE_KEY is
# one of Hardhat's well-known local test account keys (the same address the
# LendingPool contract's creditOracle is set to at deploy time).
#
# SECURITY: ORACLE_PRIVATE_KEY must NEVER be sent to, stored in, or read by
# the frontend. It only ever lives in this backend process's environment.
ETH_RPC_URL: str = os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545")
ORACLE_PRIVATE_KEY: str = os.getenv("ORACLE_PRIVATE_KEY", "")
LENDING_POOL_ADDRESS: str = os.getenv("LENDING_POOL_ADDRESS", "")
# Block at which the configured LendingPool was deployed. 0 is fine for local Hardhat demos.
LENDING_POOL_DEPLOYMENT_BLOCK: int = int(os.getenv("LENDING_POOL_DEPLOYMENT_BLOCK", "0"))
TOKEN_ADDRESS: str = os.getenv("TOKEN_ADDRESS", "")
CHAIN_ID: int = int(os.getenv("CHAIN_ID", "31337"))  # 31337 = local Hardhat default

# Shared-secret header required to call the oracle-sync / faucet endpoints.
# This is a DEMO-GRADE protection only (a single static key compared with a
# plain string equality check) -- it is not a substitute for real auth/authz,
# rate limiting, or multisig control in anything beyond a local sandbox.
ORACLE_API_KEY: str = os.getenv("ORACLE_API_KEY", "")

# CORS: comma-separated list of allowed frontend origins for local dev.
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

