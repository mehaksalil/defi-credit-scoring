# Step 7: Smart contracts (lending protocol)

## What we built

1. **MockERC20** (`contracts/contracts/MockERC20.sol`)
   - Mintable ERC20 for testing; owner can mint. Used as the single token for both collateral and borrows in the pool.

2. **LendingPool** (`contracts/contracts/LendingPool.sol`)
   - **deposit(amount)** — User sends token to the pool; `collateral[user]` increases.
   - **withdraw(amount)** — User withdraws token; reverts if withdrawal would leave collateral below the amount required to back existing debt (by score ratio).
   - **borrow(amount)** — User receives token from the pool; requires:
     - `!isFraud[user]`
     - `creditScore[user] >= 40`
     - `collateral[user] >= borrowAmount * collateralRatio(score) / 100`
     - Pool has enough token balance (liquidity).
   - **repay(amount)** — User sends token back to the pool; `debt[user]` decreases.
   - **setCreditData(user, score, fraud)** — Callable only by `creditOracle` (set at deploy; backend or script calls this after getting score/fraud from the API).

3. **Collateral ratio by score**
   - Score ≥ 70: ratio 50% → user can borrow up to 2× collateral.
   - Score 40–69: ratio 80% → borrow up to 1.25× collateral.
   - Score < 40: no borrow (ratio 100% and min score check fails).

4. **Deploy script** (`contracts/scripts/deploy.js`)
   - Deploys MockERC20 and LendingPool, mints to deployer and to the pool for initial liquidity.

## Flow (backend + contract)

1. User connects wallet; frontend calls your API: `GET /wallet/{address}/report`.
2. Backend returns `score`, `risk_level`, `is_fraud`.
3. Backend (or a script with the oracle key) calls `LendingPool.setCreditData(userAddress, score, is_fraud)`.
4. User can then deposit, borrow (if eligible), and repay in the frontend.

## How to run

```bash
cd contracts
npm install
npx hardhat compile
npx hardhat node
# In another terminal:
npx hardhat run scripts/deploy.js --network localhost
```

Use the printed `TOKEN_ADDRESS` and `LENDING_POOL_ADDRESS` in the frontend (Step 8).

## Next (Step 8)

Frontend dashboard: wallet connection, display report (score, risk, fraud), deposit/borrow/repay UI calling these contracts.
