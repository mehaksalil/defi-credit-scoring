# Step 6: Backend API (integration layer)

## What we added

- **GET /wallet/{address}/report** — Single response with everything the dashboard needs:
  - `address`, `tx_count`, `score`, `risk_level`, `fraud_probability`, `is_fraud`
  - Uses cached transactions and both ML models; returns 503 if either model isn’t trained.

This avoids the frontend making three calls (/transactions, /score, /fraud) and simplifies loading state.

## API summary

| Endpoint | Purpose |
|----------|----------|
| GET / | Links to docs, health |
| GET /health | Health check |
| GET /wallet/{address}/transactions | Raw normalized tx list |
| GET /wallet/{address}/features | Feature vector for ML |
| GET /wallet/{address}/score | Credit score 0–100 + risk level |
| GET /wallet/{address}/fraud | Fraud probability + is_fraud |
| GET /wallet/{address}/report | Combined: tx_count, score, risk, fraud |

All wallet endpoints accept `?use_cache=true` (default) to use cached Etherscan data.

## Next (Step 7)

Smart contracts: ERC-20 token, lending pool with deposit/borrow/repay and credit-score–based rules.
