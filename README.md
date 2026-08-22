# DeFi AI Credit Scoring & Lending Platform

A complete decentralized finance (DeFi) application that uses artificial intelligence to assess creditworthiness of Ethereum wallet addresses and enables lending based on on-chain transaction history.

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Folder Structure Explanation](#folder-structure-explanation)
3. [Step-by-Step Guide to Rebuild](#step-by-step-guide-to-rebuild)
4. [Installation Instructions](#installation-instructions)
5. [How to Run the Project](#how-to-run-the-project)
6. [How to Use the Application](#how-to-use-the-application)
7. [Suggestions for Improvements](#suggestions-for-improvements)

---

## 🎯 Project Overview

### What Problem Does This Solve?

Traditional lending requires credit bureaus, bank accounts, and extensive paperwork. In decentralized finance (DeFi), there's no central authority to verify creditworthiness. This project solves this by:

1. **Analyzing on-chain behavior**: Instead of credit history, we analyze Ethereum transaction patterns
2. **AI-powered scoring**: Uses machine learning to predict creditworthiness from transaction data
3. **Automated lending**: Smart contracts enforce lending rules based on credit scores
4. **Fraud detection**: Identifies suspicious wallet patterns before lending

### High-Level Architecture

The system consists of three main components that work together:

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Frontend  │─────▶│   Backend   │─────▶│  Contracts  │
│   (React)  │◀─────│   (FastAPI) │◀─────│  (Solidity) │
└─────────────┘      └─────────────┘      └─────────────┘
     │                     │                     │
     │                     │                     │
     └─────────────────────┼─────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Blockchain │
                    │  (Ethereum) │
                    └─────────────┘
```

**Frontend (React)**: User interface where users connect wallets, view credit scores, and interact with the lending pool.

**Backend (Python/FastAPI)**: 
- Fetches transaction data from blockchain
- Computes features from transactions
- Runs ML models to generate credit scores
- Provides REST API for frontend

**Smart Contracts (Solidity)**: 
- Manages lending pool (deposit, borrow, repay)
- Enforces credit score-based rules
- Stores collateral and debt on-chain

### Data Flow Explained Simply

1. **User connects wallet** → Frontend gets Ethereum address
2. **Frontend requests score** → Calls backend API with wallet address
3. **Backend fetches transactions** → Gets wallet's transaction history from Etherscan API
4. **Backend computes features** → Extracts patterns (transaction count, age, failure rate, etc.)
5. **Backend runs ML models** → Generates credit score (0-100) and fraud probability
6. **Backend updates contract** → Sets credit score in smart contract (oracle role)
7. **User interacts with pool** → Can deposit, borrow (if eligible), repay based on score
8. **Contract enforces rules** → Blocks borrowing if score too low or fraud detected

---

## 📁 Folder Structure Explanation

```
defi-credit-scoring/
├── backend/              # Python backend - Core ML and API logic
│   ├── app/
│   │   ├── main.py      # FastAPI application entry point
│   │   ├── config.py    # Configuration (API keys, paths)
│   │   └── services/    # Business logic modules
│   │       ├── blockchain_data.py    # Fetch transactions from Etherscan
│   │       ├── features.py           # Compute features from transactions
│   │       ├── credit_model.py       # Credit scoring ML model
│   │       ├── fraud_model.py        # Fraud detection ML model
│   │       └── proxy_labels.py       # Generate training labels
│   ├── models/          # Trained ML models (gitignored)
│   ├── data/            # Cached transaction data (gitignored)
│   ├── requirements.txt # Python dependencies
│   └── train_credit_model.py  # Script to train ML models
│
├── contracts/           # Solidity smart contracts
│   ├── contracts/
│   │   ├── MockERC20.sol      # Test token (ERC-20 standard)
│   │   └── LendingPool.sol    # Lending pool with credit rules
│   ├── scripts/
│   │   └── deploy.js          # Deployment script
│   └── hardhat.config.js      # Hardhat configuration
│
├── frontend/            # React frontend application
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── components/       # React components
│   │   │   ├── WalletConnection.jsx   # MetaMask connection
│   │   │   ├── CreditScoreCard.jsx    # Display credit score
│   │   │   └── LendingPool.jsx        # Lending interactions
│   │   ├── utils/            # Helper functions
│   │   │   ├── api.js        # Backend API calls
│   │   │   └── wallet.js     # Wallet utilities
│   │   └── contracts/        # Contract ABIs
│   │       └── abis.js       # Contract interfaces
│   └── package.json          # Node.js dependencies
│
└── docs/                # Documentation
    ├── STEP1_PROJECT_SETUP.md
    ├── STEP2_DATA_PIPELINE.md
    ├── STEP3_FEATURE_ENGINEERING.md
    ├── STEP4_CREDIT_MODEL.md
    ├── STEP5_FRAUD_MODEL.md
    ├── STEP6_BACKEND_API.md
    ├── STEP7_SMART_CONTRACTS.md
    ├── STEP8_FRONTEND.md
    └── METAMASK_SETUP.md
```

### Core vs Support Files

**Core (Essential for functionality):**
- `backend/app/services/*.py` - All business logic
- `backend/app/main.py` - API server
- `contracts/contracts/*.sol` - Smart contracts
- `frontend/src/components/*.jsx` - UI components
- `frontend/src/utils/*.js` - Frontend utilities

**Support (Configuration and setup):**
- `requirements.txt`, `package.json` - Dependencies
- `*.config.js` - Build tool configurations
- `.env.example` - Environment variable templates
- `docs/*.md` - Documentation

**Generated (Created at runtime, gitignored):**
- `backend/models/*.pkl` - Trained ML models
- `backend/data/*.json` - Cached transaction data
- `node_modules/`, `venv/` - Installed dependencies

---

## 🔨 Step-by-Step Guide to Rebuild

This guide explains **why** each step exists and what it accomplishes. Follow in order.

### Step 1: Project Setup & Structure

**Purpose**: Create a clean, organized project structure that separates concerns.

**What to do**:
1. Create root directory: `defi-credit-scoring/`
2. Create subdirectories: `backend/`, `contracts/`, `frontend/`, `docs/`
3. Initialize Python virtual environment in `backend/`
4. Initialize Node.js project in `contracts/` and `frontend/`

**Why**: Separating backend, contracts, and frontend allows:
- Independent development and deployment
- Different teams can work on different parts
- Clear separation of concerns (ML vs blockchain vs UI)

**Files created**:
- `backend/requirements.txt` - Python dependencies
- `contracts/package.json` - Node.js dependencies for contracts
- `frontend/package.json` - Node.js dependencies for frontend

---

### Step 2: Data Pipeline

**Purpose**: Fetch and normalize blockchain transaction data so we can analyze it.

**What to do**:
1. Create `backend/app/config.py` - Load API keys from environment
2. Create `backend/app/services/blockchain_data.py`:
   - `fetch_transactions_etherscan()` - Calls Etherscan API
   - `normalize_transactions()` - Converts to standard format
   - `get_transactions()` - Caches results to avoid repeated API calls

**Why**: 
- Etherscan API provides indexed transaction data (easier than scanning blocks)
- Normalization ensures consistent data format for later steps
- Caching saves API calls and speeds up development

**Key concepts**:
- **Etherscan API**: Free service that indexes Ethereum transactions
- **Normalization**: Converting API response to a fixed schema (columns: `timestamp`, `value_wei`, `from_address`, `to_address`, etc.)
- **Caching**: Save fetched data to disk so we don't re-fetch for the same wallet

---

### Step 3: Feature Engineering

**Purpose**: Extract meaningful patterns from raw transaction data that ML models can learn from.

**What to do**:
1. Create `backend/app/services/features.py`:
   - `compute_features()` - Calculates features like:
     - `tx_count` - Total transactions
     - `age_days` - Wallet age
     - `failed_tx_ratio` - Percentage of failed transactions
     - `unique_counterparties` - Number of unique addresses interacted with
     - `avg_value_eth` - Average transaction value
     - `inflow_outflow_ratio` - Money in vs money out

**Why**: 
- Raw transactions are too complex for ML models
- Features summarize behavior patterns
- Good features = better predictions

**Key concepts**:
- **Features**: Numerical summaries of wallet behavior
- **Feature engineering**: The process of creating these summaries
- **Why these features**: They capture creditworthiness signals (activity, reliability, diversity)

---

### Step 4: Credit Scoring Model

**Purpose**: Train a machine learning model that predicts creditworthiness from features.

**What to do**:
1. Create `backend/app/services/proxy_labels.py`:
   - `proxy_label_from_features()` - Creates training labels using heuristics
   - Labels wallets as "creditworthy" (1) or "not creditworthy" (0)

2. Create `backend/app/services/credit_model.py`:
   - `train_credit_model()` - Trains XGBoost classifier
   - `predict_credit()` - Generates score (0-100) and risk level

3. Create `backend/train_credit_model.py`:
   - Script that fetches data, computes features, trains model, saves it

**Why**:
- **Proxy labels**: We don't have real default data, so we use heuristics (e.g., "wallets with many failed transactions are risky")
- **XGBoost**: Powerful ML algorithm that handles non-linear patterns
- **Score 0-100**: Easy to understand and use in smart contracts

**Key concepts**:
- **Supervised learning**: Model learns from labeled examples
- **Training**: Model adjusts its parameters to minimize prediction error
- **Inference**: Using trained model to predict on new data

---

### Step 5: Fraud Detection Model

**Purpose**: Identify suspicious wallets that might be scams or bots.

**What to do**:
1. Create `backend/app/services/fraud_model.py`:
   - Uses Isolation Forest (unsupervised learning)
   - Detects outliers in feature space
   - Returns fraud probability (0-1)

**Why**:
- **Unsupervised**: No labeled fraud data needed
- **Isolation Forest**: Good at finding anomalies
- **Separate from credit score**: Fraud is different from low credit

**Key concepts**:
- **Unsupervised learning**: Finds patterns without labels
- **Anomaly detection**: Identifies unusual patterns
- **Why separate model**: Fraud and creditworthiness are different problems

---

### Step 6: Backend API

**Purpose**: Expose ML models and data through a REST API that frontend can call.

**What to do**:
1. Create `backend/app/main.py`:
   - FastAPI application with endpoints:
     - `GET /wallet/{address}/transactions` - Get transaction history
     - `GET /wallet/{address}/features` - Get computed features
     - `GET /wallet/{address}/score` - Get credit score
     - `GET /wallet/{address}/fraud` - Get fraud probability
     - `GET /wallet/{address}/report` - Get everything in one call

**Why**:
- **REST API**: Standard way for frontend to communicate with backend
- **Single report endpoint**: Reduces frontend API calls
- **Error handling**: Returns proper HTTP status codes

**Key concepts**:
- **REST API**: HTTP endpoints that return JSON
- **FastAPI**: Modern Python web framework with automatic docs
- **Endpoints**: URLs that perform specific actions

---

### Step 7: Smart Contracts

**Purpose**: Create on-chain lending pool that enforces credit score rules.

**What to do**:
1. Create `contracts/contracts/MockERC20.sol`:
   - ERC-20 token for testing (can mint tokens)

2. Create `contracts/contracts/LendingPool.sol`:
   - `deposit()` - User deposits tokens as collateral
   - `withdraw()` - User withdraws collateral (if safe)
   - `borrow()` - User borrows tokens (requires score ≥ 40, not fraud)
   - `repay()` - User repays borrowed tokens
   - `setCreditData()` - Backend updates credit score (oracle role)

**Why**:
- **On-chain**: Rules enforced by blockchain, can't be cheated
- **Credit-based rules**: Higher score = better borrowing terms
- **Collateral ratios**: Score determines how much you can borrow

**Key concepts**:
- **Smart contract**: Code that runs on blockchain
- **Collateral**: Assets locked to secure a loan
- **Collateral ratio**: How much you can borrow vs collateral (e.g., 50% = borrow 2x collateral)

---

### Step 8: Frontend

**Purpose**: Create user interface for connecting wallet, viewing scores, and interacting with lending pool.

**What to do**:
1. Create React app structure:
   - `src/App.jsx` - Main app component
   - `src/components/WalletConnection.jsx` - MetaMask connection
   - `src/components/CreditScoreCard.jsx` - Display credit score
   - `src/components/LendingPool.jsx` - Lending interactions

2. Create utilities:
   - `src/utils/api.js` - Backend API calls
   - `src/utils/wallet.js` - Wallet connection helpers
   - `src/contracts/abis.js` - Contract interfaces

**Why**:
- **React**: Popular, component-based UI framework
- **Ethers.js**: Library for interacting with Ethereum
- **Tailwind CSS**: Utility-first CSS for quick styling

**Key concepts**:
- **Component**: Reusable UI piece (e.g., button, card)
- **State**: Data that changes (e.g., wallet address, credit score)
- **ABI**: Application Binary Interface - describes contract functions

---

## 💻 Installation Instructions

### Prerequisites

Before starting, ensure you have:

1. **Python 3.8+** - [Download](https://www.python.org/downloads/)
   - Check: `python --version`

2. **Node.js 16+** - [Download](https://nodejs.org/)
   - Check: `node --version`

3. **MetaMask Browser Extension** - [Install](https://metamask.io/download/)
   - Required for wallet connection
   - See `docs/METAMASK_SETUP.md` for detailed setup

4. **Etherscan API Key** (free) - [Get one here](https://etherscan.io/apis)
   - Used to fetch transaction data
   - Free tier allows 5 calls/second

5. **Git** (optional) - For cloning the repository

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     venv\Scripts\activate.bat
     ```
   - **Mac/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables:**
   ```bash
   copy .env.example .env  # Windows
   # or
   cp .env.example .env   # Mac/Linux
   ```

6. **Edit `.env` file:**
   ```env
   ETHERSCAN_API_KEY=your_api_key_here
   ```

### Contracts Setup

1. **Navigate to contracts directory:**
   ```bash
   cd contracts
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Verify Hardhat installation:**
   ```bash
   npx hardhat --version
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   copy .env.example .env  # Windows
   # or
   cp .env.example .env   # Mac/Linux
   ```

4. **Edit `.env` file** (you'll fill this after deploying contracts):
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_TOKEN_ADDRESS=
   VITE_LENDING_POOL_ADDRESS=
   VITE_CHAIN_ID=31337
   ```

---

## 🚀 How to Run the Project

### Complete Startup Sequence

Follow these steps **in order**:

#### 1. Train ML Models (First Time Only)

```bash
cd backend
# Make sure venv is activated
python train_credit_model.py
```

**What happens**: 
- Fetches transaction data for sample wallets
- Computes features
- Trains credit and fraud models
- Saves models to `backend/models/`

**Expected output**: 
```
Training credit model...
Model trained and saved to backend/models/credit_model.joblib
Training fraud model...
Fraud model trained and saved to backend/models/fraud_model.joblib
```

**Common errors**:
- `ETHERSCAN_API_KEY not found`: Add your API key to `.env`
- `No module named 'xgboost'`: Run `pip install -r requirements.txt`

---

#### 2. Start Backend API Server

**Terminal 1:**
```bash
cd backend
# Activate venv if not already
uvicorn app.main:app --reload
```

**What happens**: 
- Starts FastAPI server on http://localhost:8000
- API docs available at http://localhost:8000/docs

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Common errors**:
- `uvicorn: command not found`: Activate virtual environment
- `Address already in use`: Port 8000 is taken, change port or kill process

---

#### 3. Start Hardhat Local Blockchain

**Terminal 2:**
```bash
cd contracts
npx hardhat node
```

**What happens**: 
- Starts local Ethereum node on http://127.0.0.1:8545
- Creates 20 test accounts with 10,000 ETH each
- Shows private keys (save one for MetaMask)

**Expected output**:
```
Started HTTP and WebSocket server on http://127.0.0.1:8545/

Accounts
========
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
Private Key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
...
```

**Common errors**:
- `Port 8545 already in use`: Kill existing Hardhat node or change port

---

#### 4. Deploy Smart Contracts

**Terminal 3:**
```bash
cd contracts
npx hardhat run scripts/deploy.js --network localhost
```

**What happens**: 
- Deploys MockERC20 token
- Deploys LendingPool contract
- Mints tokens to deployer and pool

**Expected output**:
```
Deploying with account: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
MockERC20 deployed to: 0x5FbDB2315678afecb367f032d93F642f64180aa3
LendingPool deployed to: 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512

Done. Use these in the frontend:
TOKEN_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
LENDING_POOL_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
```

**Important**: Copy `TOKEN_ADDRESS` and `LENDING_POOL_ADDRESS` to `frontend/.env`

---

#### 5. Configure Frontend

Edit `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
VITE_TOKEN_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
VITE_LENDING_POOL_ADDRESS=0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
VITE_CHAIN_ID=31337
```

---

#### 6. Start Frontend Development Server

**Terminal 4:**
```bash
cd frontend
npm run dev
```

**What happens**: 
- Starts Vite dev server on http://localhost:3000
- Opens browser automatically (or navigate manually)

**Expected output**:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

---

#### 7. Configure MetaMask

1. **Add Hardhat Network**:
   - Open MetaMask → Network dropdown → "Add Network" → "Add a network manually"
   - Network Name: `Hardhat Local`
   - RPC URL: `http://127.0.0.1:8545`
   - Chain ID: `31337`
   - Currency Symbol: `ETH`
   - Save

2. **Import Test Account**:
   - Copy a private key from Terminal 2 (Hardhat node output)
   - MetaMask → Account icon → "Import Account"
   - Paste private key → Import

---

### Verification Checklist

✅ Backend running on http://localhost:8000  
✅ Hardhat node running on http://127.0.0.1:8545  
✅ Contracts deployed (have addresses)  
✅ Frontend running on http://localhost:3000  
✅ MetaMask connected to Hardhat Local network  
✅ Test account imported in MetaMask  

---

## 📱 How to Use the Application

### User Flow

1. **Open Application**
   - Navigate to http://localhost:3000
   - You should see "Connect Your Wallet" button

2. **Connect Wallet**
   - Click "Connect Wallet"
   - MetaMask popup appears
   - Select account and approve connection
   - Wallet address appears at top

3. **View Credit Score**
   - After connecting, backend fetches your wallet's transaction history
   - Credit score card displays:
     - **Score**: 0-100 (higher is better)
     - **Risk Level**: Low/Medium/High
     - **Fraud Status**: Verified or Flagged
     - **Transaction Count**: Total transactions
     - **Fraud Probability**: 0-100%

4. **Interact with Lending Pool**

   **Deposit Collateral**:
   - Click "Deposit" tab
   - Enter amount (e.g., 100)
   - Click "Deposit"
   - Approve token spending in MetaMask
   - Confirm transaction
   - Collateral balance updates

   **Borrow Tokens**:
   - Requires credit score ≥ 40 and not flagged as fraud
   - Click "Borrow" tab
   - Enter amount (must be ≤ borrow limit)
   - Click "Borrow"
   - Confirm transaction
   - Debt balance updates

   **Repay Debt**:
   - Click "Repay" tab
   - Enter amount to repay
   - Click "Repay"
   - Approve token spending
   - Confirm transaction
   - Debt decreases

   **Withdraw Collateral**:
   - Click "Withdraw" tab
   - Enter amount (must leave enough collateral for debt)
   - Click "Withdraw"
   - Confirm transaction
   - Collateral decreases

### Example Usage Scenario

**Scenario**: Alice wants to borrow 50 tokens

1. Alice connects wallet (address: `0x123...`)
2. Backend analyzes her transactions:
   - 150 transactions
   - Wallet age: 180 days
   - Low failure rate
   - Score: 75 (Low risk)
3. Alice deposits 100 tokens as collateral
4. With score 75, collateral ratio is 50% → can borrow up to 200 tokens
5. Alice borrows 50 tokens (well within limit)
6. Alice's balances:
   - Collateral: 100 tokens
   - Debt: 50 tokens
   - Borrow limit: 200 tokens
   - Available to borrow: 150 tokens

### Understanding Credit Scores

- **70-100**: Low risk, can borrow up to 2× collateral (50% ratio)
- **40-69**: Medium risk, can borrow up to 1.25× collateral (80% ratio)
- **0-39**: High risk, cannot borrow
- **Fraud flagged**: Cannot borrow regardless of score

### Inputs and Outputs

**Inputs**:
- Ethereum wallet address (from MetaMask)
- Transaction amounts (for deposit/borrow/repay)

**Outputs**:
- Credit score (0-100)
- Risk level (Low/Medium/High)
- Fraud probability (0-1)
- Borrow limit (based on score and collateral)
- Current balances (token, collateral, debt)

---

## 🔧 Suggestions for Improvements

### Performance Optimizations

1. **Backend Caching**:
   - Add Redis for API response caching
   - Cache credit scores for 24 hours (scores don't change frequently)
   - Reduce Etherscan API calls

2. **Database Integration**:
   - Replace file-based caching with PostgreSQL/MongoDB
   - Store transaction history in database
   - Enable faster queries and analytics

3. **Model Optimization**:
   - Use model quantization to reduce size
   - Implement batch prediction for multiple wallets
   - Add model versioning system

### Feature Enhancements

1. **Credit Score Updates**:
   - Automatic periodic re-scoring (e.g., daily)
   - Real-time score updates when new transactions occur
   - Score history tracking

2. **Advanced Features**:
   - Multi-token support (not just MockERC20)
   - Interest rate calculation (currently 0%)
   - Liquidation mechanism for undercollateralized loans
   - Flash loan support

3. **User Experience**:
   - Transaction history display
   - Toast notifications for successful/failed transactions
   - Loading states and progress indicators
   - Error recovery and retry mechanisms

### Code Quality Improvements

1. **Testing**:
   - Unit tests for ML models
   - Integration tests for API endpoints
   - Contract tests with Hardhat
   - E2E tests with Playwright/Cypress

2. **Error Handling**:
   - Better error messages for users
   - Retry logic for API failures
   - Graceful degradation when models unavailable

3. **Documentation**:
   - API documentation with examples
   - Code comments explaining complex logic
   - Architecture diagrams
   - Deployment guides

### Security Enhancements

1. **Oracle Security**:
   - Multi-signature for `setCreditData()` function
   - Time-locked updates (prevent manipulation)
   - Rate limiting on score updates

2. **Frontend Security**:
   - Input validation and sanitization
   - Protection against XSS attacks
   - Secure storage of sensitive data

3. **Smart Contract Audits**:
   - Professional security audit
   - Formal verification of critical functions
   - Bug bounty program

### Scalability Improvements

1. **Microservices Architecture**:
   - Separate service for data fetching
   - Separate service for ML inference
   - Message queue for async processing

2. **Multi-Chain Support**:
   - Support for Polygon, Arbitrum, etc.
   - Cross-chain credit score aggregation
   - Unified frontend for all chains

3. **Production Deployment**:
   - Docker containers for backend
   - CI/CD pipeline
   - Monitoring and logging (Prometheus, Grafana)
   - Load balancing for API

### Refactoring Opportunities

1. **Backend**:
   - Use dependency injection for services
   - Implement repository pattern for data access
   - Add type hints throughout (use mypy)

2. **Frontend**:
   - State management with Redux/Zustand
   - Component library (reusable UI elements)
   - Custom hooks for wallet/contract interactions

3. **Contracts**:
   - Use OpenZeppelin libraries (ERC20, AccessControl)
   - Upgradeable contracts pattern
   - Gas optimization

---

## 📚 Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Ethers.js Documentation**: https://docs.ethers.org/
- **Hardhat Documentation**: https://hardhat.org/docs
- **React Documentation**: https://react.dev/
- **Etherscan API Docs**: https://docs.etherscan.io/

## 🤝 Contributing

This is a learning project. Feel free to:
- Fork and experiment
- Add new features
- Fix bugs
- Improve documentation
- Share your improvements

## 📄 License

This project is for educational purposes. Use at your own risk.

---

## 🆘 Troubleshooting

### Backend Issues

**Problem**: `uvicorn: command not found`  
**Solution**: Activate virtual environment: `.\venv\Scripts\Activate.ps1`

**Problem**: `503: Model not trained`  
**Solution**: Run `python train_credit_model.py` first

**Problem**: `502: Etherscan API error`  
**Solution**: Check API key in `.env`, verify internet connection

### Frontend Issues

**Problem**: `MetaMask is not installed`  
**Solution**: Install MetaMask extension, refresh page

**Problem**: `Wrong network`  
**Solution**: Switch MetaMask to Hardhat Local network (Chain ID 31337)

**Problem**: `Cannot read properties of undefined`  
**Solution**: Check `.env` file has correct contract addresses

### Contract Issues

**Problem**: `Insufficient funds`  
**Solution**: Import Hardhat test account with ETH

**Problem**: `Transaction failed`  
**Solution**: Check console for error, verify you have enough tokens/collateral

---

**Happy Building! 🚀**
