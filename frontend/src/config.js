// Update these with your deployed contract addresses
export const CONFIG = {
  // Backend API URL (default: localhost:8000)
  API_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  
  // Contract addresses (update after deploying contracts)
  TOKEN_ADDRESS: import.meta.env.VITE_TOKEN_ADDRESS || '',
  LENDING_POOL_ADDRESS: import.meta.env.VITE_LENDING_POOL_ADDRESS || '',
  
  // Network configuration
  CHAIN_ID: import.meta.env.VITE_CHAIN_ID || '31337', // Hardhat default

  // Shared-secret header for the backend's oracle-sync/faucet endpoints.
  // IMPORTANT: this ends up in the built frontend JS bundle, so it is NOT a
  // real secret once shipped -- anyone can read it out of the browser bundle.
  // It only exists to stop the endpoints from being called by accident from
  // arbitrary browser tabs during local development. Do not rely on it for
  // anything beyond a local demo; see README.md "Security limitations".
  ORACLE_API_KEY: import.meta.env.VITE_ORACLE_API_KEY || '',
};
