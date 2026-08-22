# DeFi Credit — Smart Contracts

- **MockERC20**: Mintable ERC20 for testing; used as collateral and borrow token.
- **LendingPool**: Deposit, withdraw, borrow, repay. Credit score and fraud flag (set by oracle) control eligibility and collateral ratio.

## Credit logic (on-chain)

- Only `creditOracle` can call `setCreditData(user, score, fraud)` (your backend or a dedicated key).
- **Borrow** requires: `!isFraud`, `score >= 40`, and `collateral >= borrowAmount * ratio(score)`:
  - Score ≥ 70: ratio 50% (borrow up to 2× collateral).
  - Score 40–69: ratio 80% (borrow up to 1.25× collateral).
  - Score < 40: no borrow.

## Setup

```bash
cd contracts
npm install
npx hardhat compile
```

## Deploy (local Hardhat network)

```bash
npx hardhat node
# In another terminal:
npx hardhat run scripts/deploy.js --network localhost
```

Then set `TOKEN_ADDRESS` and `LENDING_POOL_ADDRESS` in your frontend. Your backend (or a small script) should call `setCreditData(user, score, isFraud)` after computing score/fraud from the API so the user can borrow.
