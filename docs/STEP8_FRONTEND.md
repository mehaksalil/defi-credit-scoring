# Step 8: Frontend Dashboard

## What we built

A modern React frontend with:
1. **Wallet Connection** - MetaMask integration using Ethers.js
2. **Credit Score Display** - Shows score, risk level, fraud status from backend API
3. **Lending Pool Interface** - Deposit, withdraw, borrow, repay functionality
4. **Real-time Updates** - Fetches wallet data and pool balances

## Features

- Connect/disconnect MetaMask wallet
- View credit score report (score, risk level, fraud status)
- Deposit tokens as collateral
- Withdraw collateral (if no debt or sufficient remaining)
- Borrow tokens (requires score ≥ 40, not fraud)
- Repay debt
- View current balances (token, collateral, debt, borrow limit)

## Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Configure environment:**
```bash
cp .env.example .env
```

Update `.env` with your contract addresses:
```env
VITE_API_URL=http://localhost:8000
VITE_TOKEN_ADDRESS=0x...  # From contract deployment
VITE_LENDING_POOL_ADDRESS=0x...  # From contract deployment
VITE_CHAIN_ID=31337  # Hardhat default
```

3. **Start development server:**
```bash
npm run dev
```

The app will run on http://localhost:3000

## Usage Flow

1. **Start backend:**
```bash
cd backend
uvicorn app.main:app --reload
```

2. **Start Hardhat node (if testing locally):**
```bash
cd contracts
npx hardhat node
```

3. **Deploy contracts:**
```bash
npx hardhat run scripts/deploy.js --network localhost
```

4. **Update frontend .env** with the deployed addresses

5. **Start frontend:**
```bash
cd frontend
npm run dev
```

6. **Connect wallet** and interact with the lending pool!

## Architecture

- **React + Vite** - Fast build tool and dev server
- **Ethers.js v6** - Wallet connection and contract interaction
- **Tailwind CSS** - Modern, responsive styling
- **Axios** - HTTP client for backend API calls

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── WalletConnection.jsx    # Wallet connect/disconnect UI
│   │   ├── CreditScoreCard.jsx     # Credit score display
│   │   └── LendingPool.jsx         # Lending pool interactions
│   ├── contracts/
│   │   └── abis.js                 # Contract ABIs
│   ├── utils/
│   │   ├── api.js                  # Backend API calls
│   │   └── wallet.js               # Wallet utilities
│   ├── App.jsx                     # Main app component
│   ├── main.jsx                    # React entry point
│   ├── index.css                   # Global styles
│   └── config.js                   # Configuration
├── public/                         # Static assets
├── index.html                      # HTML template
├── package.json                    # Dependencies
├── vite.config.js                  # Vite configuration
├── tailwind.config.js              # Tailwind CSS config
└── .env                            # Environment variables
```

## Component Details

### WalletConnection
- Handles MetaMask connection
- Shows connected address
- Displays connection errors
- Allows disconnection

### CreditScoreCard
- Displays credit score (0-100)
- Shows risk level (Low/Medium/High)
- Indicates fraud status
- Shows transaction count and fraud probability
- Color-coded based on score

### LendingPool
- Displays user balances (token, collateral, debt, borrow limit)
- Four actions: deposit, withdraw, borrow, repay
- Validates borrow eligibility based on credit score
- Handles token approvals automatically
- Updates balances after transactions

## Integration Points

1. **Backend API** (`/wallet/{address}/report`)
   - Fetches credit score, risk level, fraud status
   - Called when wallet connects or refresh button clicked

2. **Smart Contracts**
   - LendingPool contract for lending operations
   - MockERC20 contract for token operations
   - Reads balances and writes transactions

## Error Handling

- Network errors (wrong chain ID)
- API errors (backend unavailable)
- Transaction errors (insufficient balance, etc.)
- User-friendly error messages displayed in UI

## Next Steps

- Add transaction history display
- Add loading states for better UX
- Add toast notifications for transactions
- Add network switching UI
- Deploy to production (Vercel/Netlify)
- Add unit tests
- Add E2E tests with Cypress/Playwright
