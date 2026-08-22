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
