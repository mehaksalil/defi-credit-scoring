import axios from 'axios';
import { CONFIG } from '../config';

const api = axios.create({
  baseURL: CONFIG.API_URL,
});

export const getWalletReport = async (address) => {
  const response = await api.get(`/wallet/${address}/report`);
  return response.data;
};

export const updateCreditData = async (address, score, isFraud) => {
  // This would typically be called by a backend service with oracle permissions
  // For now, we'll just log it - in production, this should be a backend endpoint
  console.log('Credit data update:', { address, score, isFraud });
};
