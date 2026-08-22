# Step 4: Credit scoring model

## What we built

1. **Proxy labels** (`app/services/proxy_labels.py`)  
   - `proxy_label_from_features(row)` returns 1 (creditworthy) or 0 (not) using heuristics:  
     - Bad: `tx_count < 3` or `failed_tx_ratio > 0.25`  
     - Good: e.g. `age >= 30`, `tx_count >= 10`, `failed_tx_ratio <= 0.1`, `unique_counterparties >= 2`, or moderate activity with low failure  
   - Used only for training; we have no real default data on-chain.

2. **Model pipeline** (`app/services/credit_model.py`)  
   - **Train:** `train_credit_model(feature_df, labels=None)` — if `labels` is None, uses proxy labels; fits `StandardScaler` + `XGBClassifier`; saves `credit_model.joblib` and `credit_scaler.joblib` under `backend/models/`.  
   - **Load:** `load_credit_model()` returns `(model, scaler)` or `(None, None)` if not trained.  
   - **Predict:** `predict_credit(model, scaler, feature_row)` → `(score_0_100, risk_level)`.  
     - Score = probability of “good” class × 100.  
     - Risk: 0–40 High, 40–70 Medium, 70–100 Low.

3. **Training script** (`backend/train_credit_model.py`)  
   - Fetches transactions (with cache) for a built-in list of addresses.  
   - Computes features, trains the model with proxy labels, saves to `backend/models/`.  
   - Run from `backend/`: `python train_credit_model.py`.

4. **API**  
   - `GET /wallet/{address}/score?use_cache=true`  
   - Returns `{ "address", "score", "risk_level" }`.  
   - 503 if the model is not trained yet (run `train_credit_model.py` first).

## Why this approach

- **Proxy labels:** No “default” flag on-chain; heuristics give a noisy but usable training signal so we can still train a classifier.  
- **StandardScaler:** Puts all features on a similar scale so XGBoost isn’t dominated by large wei values.  
- **XGBoost:** Handles mixed feature types and non-linear boundaries; works well with limited data.  
- **Score = proba × 100:** Gives a 0–100 score from a binary classifier; risk bands map that to Low/Medium/High for the frontend and contracts.

## How to run

1. **Train (once)** from `backend/`:  
   `python train_credit_model.py`  
   (Uses Etherscan cache when available.)

2. **API:**  
   `GET http://127.0.0.1:8000/wallet/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045/score`  
   Returns `score` and `risk_level` for that address.

## Next (Step 5)

Fraud detection: unsupervised model (e.g. Isolation Forest or autoencoder) on the same features, outputting a fraud probability and binary flag.
