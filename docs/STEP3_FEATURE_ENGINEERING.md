# Step 3: Feature engineering

## What we built

1. **Feature list (`app/services/features.py`)**  
   A fixed list `FEATURE_NAMES` so the credit and fraud models (Steps 4 and 5) always see the same columns in the same order.

2. **Single-wallet feature computation**  
   `compute_features(df, wallet_address)` takes the normalized transaction DataFrame and returns one `pd.Series` with:
   - **wallet_age_days** — time between first and last tx (activity window).
   - **tx_count** — number of transactions.
   - **tx_frequency_per_day** — tx_count / max(wallet_age_days, 1).
   - **total_volume_wei** — sum of all value_wei (both sides).
   - **avg_value_wei**, **median_value_wei** — central tendency of transfer size.
   - **total_outflow_wei**, **total_inflow_wei** — from wallet’s perspective (is_outgoing).
   - **failed_tx_ratio** — share of txs with is_error=1 (reverted).
   - **contract_interaction_ratio** — share of txs with value=0 and non-empty to_address (heuristic for contract calls / DeFi).
   - **outflow_volatility_wei**, **inflow_volatility_wei** — std of outgoing/incoming amounts (0 if fewer than 2 txs in that direction).
   - **unique_counterparties** — number of unique addresses (from ∪ to) excluding the wallet.

3. **API**  
   `GET /wallet/{address}/features?use_cache=true` returns `{ "address", "features", "feature_names" }`. It uses the same transaction pipeline as Step 2, then runs feature engineering.

## Why these features

- **Age, count, frequency** — longevity and activity level; useful as a proxy for “reputation” and experience.
- **Volume and avg/median value** — scale of behavior; helps separate large vs small users and bots.
- **Failed tx ratio** — high rate can mean poor planning, testing, or probing (e.g. flash loans, failed exploits).
- **Contract interaction ratio** — value=0 + non-empty `to` is a simple heuristic for “contract call”; more of these suggests more DeFi/smart-contract usage.
- **Inflow/outflow volatility** — erratic flows can indicate risk, wash trading, or unusual patterns.
- **Unique counterparties** — very low diversity can be suspicious; very high can indicate mixing or heavy DEX use.

All amounts stay in **wei** so the model sees consistent units; you can convert to ETH in the UI or in a later layer.

## Why one function per wallet

- Keeps the pipeline clear: one DataFrame in → one feature vector out.
- In Step 4 we’ll build a training set by calling this for many wallets and stacking the rows; the same function is used at inference for a single wallet.

## How to run

1. Start the API from `backend/` (as in Step 2).
2. Call:
   ```text
   GET http://127.0.0.1:8000/wallet/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045/features
   ```
   You get the 13 features for that address (transactions are loaded from cache if available).

## Next (Step 4)

We’ll add the **credit scoring model**: proxy labels from heuristics, train a supervised model (e.g. XGBoost) on the feature matrix, and output a score 0–100 plus a risk level (Low / Medium / High).
