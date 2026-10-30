# Step 1: Project structure & environment

## What we did

1. **Created a single project root** (`defi-credit-scoring`)  
   So everything (backend, contracts, frontend) lives in one repo. You can clone once and run the full system.

2. **Separated backend / contracts / frontend**  
   - **Backend (Python):** Data fetching, feature engineering, ML models, REST API. All “off-chain” logic.  
   - **Contracts (Solidity):** Lending logic, ERC-20, deposit/borrow/repay. Runs on-chain.  
   - **Frontend (React):** Wallet connect, UI, calls backend for score and contracts for actions.  
   This keeps concerns separate: you can change the model without touching Solidity, and vice versa.

3. **Added `data/` and `backend/models/`**  
   - Raw and processed data stay in `data/` (or `backend/data/`); we gitignore them so we don’t commit large files or secrets.  
   - Trained models (`.pkl` / `.joblib`) go in `backend/models/` and are also gitignored; only code is committed.

4. **Chose `requirements.txt` (no Conda/poetry for now)**  
   - One file, works everywhere, easy to read.  
   - We list minimal versions (`>=`) so you can use newer compatible versions.  
   - Later you can switch to `pyproject.toml` or Conda if your team prefers.

5. **Backend dependencies**  
   - **pandas, numpy:** Data manipulation and feature engineering.  
   - **scikit-learn:** Preprocessing, train/test split, metrics, and baseline models (e.g. Logistic Regression).  
   - **xgboost:** Strong supervised model for credit score (handles mixed features and non-linearity).  
   - **joblib:** Save/load sklearn and XGBoost models.  
   - **fastapi, uvicorn, httpx:** API server and HTTP client for calling Etherscan/other APIs.  
   - **web3:** Optional; for direct RPC calls to a node if we need more than Etherscan.  
   - **python-dotenv:** Load API keys from `.env` so they’re not in code.

## Why this order

We set up the project **before** writing data or ML code so that:

- Imports and paths are consistent from day one.  
- Anyone (or you in 6 months) can run `pip install -r requirements.txt` and know exactly what’s needed.  
- We have a clear place for data and models, so we don’t mix them with source code.

## Next (Step 2)

We’ll implement the **data pipeline**: fetch transaction history for a wallet (e.g. via Etherscan API), normalize it, and store it so the feature engineering step can read from a single, predictable format.
