import { ethers } from 'ethers';
import { CONFIG } from '../config';

export const connectWallet = async () => {
  if (typeof window.ethereum !== 'undefined') {
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send('eth_requestAccounts', []);
      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      const network = await provider.getNetwork();
      console.log('DEBUG actual chainId:', JSON.stringify(network.chainId.toString()));
      console.log('DEBUG expected CHAIN_ID:', JSON.stringify(CONFIG.CHAIN_ID));

      // Check if we're on the correct network
      if (network.chainId.toString() !== CONFIG.CHAIN_ID) {
        throw new Error(`Please switch to chain ID ${CONFIG.CHAIN_ID}`);
      }

      return { provider, signer, address };
    } catch (error) {
      throw new Error(`Failed to connect wallet: ${error.message}`);
    }
  } else {
    throw new Error('MetaMask is not installed');
  }
};

export const getProvider = () => {
  if (typeof window.ethereum !== 'undefined') {
    return new ethers.BrowserProvider(window.ethereum);
  }
  return null;
};

export const formatAddress = (address) => {
  if (!address) return '';
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

export const formatEther = (value) => {
  return ethers.formatEther(value || '0');
};

export const parseEther = (value) => {
  return ethers.parseEther(value || '0');
};
