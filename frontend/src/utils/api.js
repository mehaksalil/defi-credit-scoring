import axios from 'axios';
import { CONFIG } from '../config';

const api = axios.create({
  baseURL: CONFIG.API_URL,
});

export const getWalletReport = async (address) => {
  const response = await api.get(`/wallet/${address}/report`);
  return response.data;
};

// Triggers the backend's oracle bridge: the backend recomputes this wallet's
// score/fraud flag and signs+submits LendingPool.setCreditData() itself, using
// a private key that only ever lives on the backend. The frontend never
// touches that key -- it just asks the backend to do the write and reports
// back the resulting transaction hash.
//
// Requires backend/.env to have ORACLE_API_KEY set; this demo passes the same
// value back as a header from the frontend's own .env (VITE_ORACLE_API_KEY).
// That is a local-demo convenience, not a real security boundary -- see
// backend/app/services/oracle.py and README.md for the full caveat.
export const syncScoreOnChain = async (address) => {
  const response = await api.post(
    `/wallet/${address}/sync-onchain`,
    null,
    {
      headers: CONFIG.ORACLE_API_KEY
        ? { 'X-Oracle-Key': CONFIG.ORACLE_API_KEY }
        : {},
    }
  );
  return response.data;
};

// Local-demo faucet: asks the backend to mint MOCK test tokens to `address`
// using the same oracle/deployer key. Only meaningful on a local Hardhat
// network. See backend/app/services/oracle.py for details/caveats.
export const requestTestTokens = async (address, amount = 1000) => {
  const response = await api.post(
    `/faucet/${address}`,
    null,
    {
      params: { amount },
      headers: CONFIG.ORACLE_API_KEY
        ? { 'X-Oracle-Key': CONFIG.ORACLE_API_KEY }
        : {},
    }
  );
  return response.data;
};
