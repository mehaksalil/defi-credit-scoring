# Step 2: Data pipeline (fetch & store blockchain data)

## What we built

1. **Config (`app/config.py`)**  
   - Loads `ETHERSCAN_API_KEY` and `MAX_TXS_PER_WALLET` from env.  
   - Uses Etherscan so we don’t run our own node; free tier is enough for dev.

2. **Fetch (`app/services/blockchain_data.py`)**  
   - `fetch_transactions_etherscan(address)`  
     - Calls Etherscan `txlist` with pagination (page size 1000).  
     - Stops when we have `MAX_TXS_PER_WALLET` txs or no more pages.  
   - Uses `sort=asc` (oldest first) so we can compute “wallet age” and time-based features later.

3. **Normalize**  
   - `normalize_transactions(raw_txs, wallet_address)`  
     - Converts Etherscan’s string numbers to ints (`value_wei`, `gas_used`, `timestamp`, etc.).  
     - Renames to a fixed schema: `block_number`, `timestamp`, `from_address`, `to_address`, `value_wei`, `gas`, `gas_price`, `gas_used`, `is_error`.  
     - Adds `is_outgoing` (true if `from_address == wallet`) for inflow/outflow in Step 3.

4. **Cache**  
   - `get_transactions(address, use_cache=True)`  
     - If `backend/data/txs_<address>.json` exists, load from file and normalize.  
     - Otherwise fetch from Etherscan, save raw JSON, then normalize.  
   - Saves **raw** API response so we can change the normalizer later without re-fetching.

5. **API**  
   - `GET /wallet/{address}/transactions?use_cache=true`  
     - Returns `{ "address", "count", "transactions" }`.  
     - 400 for invalid address, 502 if Etherscan fails.

## Why this approach

- **Etherscan instead of raw Web3 for “all txs”**  
  Getting “every transaction for an address” with Web3 means scanning blocks or using a provider’s index. Etherscan already indexes this; one (paginated) API is simpler and sufficient for our use case.

- **Single normalizer and fixed schema**  
  Step 3 (feature engineering) will assume columns like `value_wei`, `timestamp`, `is_error`, `is_outgoing`. One place to normalize keeps the rest of the pipeline consistent.

- **Cache by address**  
  Avoids hitting Etherscan on every request; you can refresh by deleting the file or calling with `use_cache=false`.

- **Value in wei (int)**  
  Keeps precision; we can convert to ETH in features or UI when needed.

## How to run

1. Get an API key from https://etherscan.io/apis and set in `backend/.env`:
   ```bash
   ETHERSCAN_API_KEY=YourKey
   ```
2. From `backend/`:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Try (use a known Ethereum address):
   ```text
   GET http://127.0.0.1:8000/wallet/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045/transactions
   ```
   First call fetches from Etherscan; next calls with same address use cache.

## Next (Step 3)

We’ll add **feature engineering**: one function that takes the normalized transaction DataFrame and outputs a single row of features per wallet (wallet age, tx count, frequency, avg value, balance stability, DeFi-like interactions, failed tx ratio, etc.) for the credit and fraud models.
