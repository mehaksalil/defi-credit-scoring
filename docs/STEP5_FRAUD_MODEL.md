# Step 5: Fraud & anomaly detection

## What we built

1. **Unsupervised model** (`app/services/fraud_model.py`)
   - **Isolation Forest** on the same feature set as credit (no labels).
   - Learns “normal” behavior from the training wallets; points that are easy to isolate are flagged as anomalous (e.g. flash-loan-like patterns, abnormal bursts, very inconsistent behavior).
   - **StandardScaler** fitted on the same feature matrix so inputs are on a comparable scale.
   - **Output:** `fraud_probability` in [0, 1] (from anomaly score via sigmoid) and **is_fraud** (True when fraud_probability ≥ 0.5).

2. **Train**
   - Same script as credit: `python train_credit_model.py` now trains both credit and fraud models.
   - Fraud model is fitted on the same `feature_df` (no labels); `contamination=0.1` so the model expects ~10% of training points to be outliers.

3. **API**
   - **GET /wallet/{address}/fraud?use_cache=true**
   - Returns `{ "address", "fraud_probability", "is_fraud" }`.
   - 503 if the fraud model has not been trained yet.

## Why this approach

- **No labels:** We don’t have “this wallet committed fraud” labels; unsupervised anomaly detection is a good fit.
- **Isolation Forest:** Works well with mixed feature types and doesn’t assume a distribution; “easy to isolate” = anomalous.
- **Same features as credit:** One feature pipeline for both models; the contract and frontend can use credit score + fraud flag together.

## How to run

1. **Train (if not already):** From `backend/`, run `python train_credit_model.py` (trains both credit and fraud).
2. **API:** `GET http://127.0.0.1:8000/wallet/<address>/fraud` returns fraud probability and flag.

## Next (Step 6)

Backend API is already in place; Step 6 can add a **combined** endpoint (e.g. score + fraud in one response) and any extra wiring. Then Step 7: smart contracts (lending protocol).
