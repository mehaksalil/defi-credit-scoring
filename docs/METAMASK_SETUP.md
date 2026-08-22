# MetaMask Setup Guide

## Installing MetaMask

MetaMask is a browser extension wallet required to interact with the DeFi Credit Scoring frontend.

### Step 1: Install MetaMask Extension

1. **Chrome/Edge/Brave:**
   - Go to https://metamask.io/download/
   - Click "Install MetaMask for Chrome" (or your browser)
   - Click "Add to Chrome" and confirm

2. **Firefox:**
   - Go to https://addons.mozilla.org/en-US/firefox/addon/ether-metamask/
   - Click "Add to Firefox" and confirm

### Step 2: Create or Import Wallet

1. Open MetaMask extension
2. Click "Get Started"
3. Choose "Create a new wallet" or "Import an existing wallet"
4. Follow the setup wizard
5. **Save your seed phrase securely!**

### Step 3: Add Hardhat Local Network

For local development, you need to add Hardhat's localhost network:

1. Open MetaMask
2. Click the network dropdown (top center, usually shows "Ethereum Mainnet")
3. Click "Add Network" → "Add a network manually"
4. Fill in:
   - **Network Name:** Hardhat Local
   - **RPC URL:** http://127.0.0.1:8545
   - **Chain ID:** 31337
   - **Currency Symbol:** ETH
   - **Block Explorer URL:** (leave empty)
5. Click "Save"

### Step 4: Get Test ETH (for Hardhat)

When running Hardhat locally, you'll get test accounts with ETH automatically. To import one:

1. Start Hardhat node:
   ```bash
   cd contracts
   npx hardhat node
   ```

2. Copy one of the private keys from the Hardhat output

3. In MetaMask:
   - Click the account icon (top right)
   - Click "Import Account"
   - Paste the private key
   - Click "Import"

Now you have a test account with ETH on the local network!

## Alternative: Use MetaMask Without Installation (Development Only)

If you want to test the frontend without MetaMask, you can modify the code to use a mock wallet provider, but this won't allow actual contract interactions.

## Troubleshooting

### "MetaMask is not installed" error
- Make sure MetaMask extension is installed and enabled
- Refresh the browser page
- Check browser console for errors

### "Wrong network" error
- Make sure Hardhat node is running (`npx hardhat node`)
- Switch MetaMask to "Hardhat Local" network
- Check that Chain ID is 31337

### "Insufficient funds" error
- Import a Hardhat test account (see Step 4 above)
- Or mint tokens using the deploy script

## Next Steps

After MetaMask is set up:
1. Start Hardhat node: `cd contracts && npx hardhat node`
2. Deploy contracts: `npx hardhat run scripts/deploy.js --network localhost`
3. Start backend: `cd backend && uvicorn app.main:app --reload`
4. Start frontend: `cd frontend && npm run dev`
5. Connect MetaMask and interact with the app!
