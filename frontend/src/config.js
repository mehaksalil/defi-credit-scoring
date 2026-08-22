// Update these with your deployed contract addresses
export const CONFIG = {
  // Backend API URL (default: localhost:8000)
  API_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  
  // Contract addresses (update after deploying contracts)
  TOKEN_ADDRESS: import.meta.env.VITE_TOKEN_ADDRESS || '',
  LENDING_POOL_ADDRESS: import.meta.env.VITE_LENDING_POOL_ADDRESS || '',
  
  // Network configuration
  CHAIN_ID: import.meta.env.VITE_CHAIN_ID || '31337', // Hardhat default
};
