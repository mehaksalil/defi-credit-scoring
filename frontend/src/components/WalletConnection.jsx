import { useState } from 'react';
import { connectWallet, formatAddress } from '../utils/wallet';

export default function WalletConnection({ onConnect, address }) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState('');

  const handleConnect = async () => {
    setIsConnecting(true);
    setError('');
    try {
      if (typeof window.ethereum === 'undefined') {
        throw new Error('MetaMask is not installed. Please install MetaMask to continue.');
      }
      const { address } = await connectWallet();
      onConnect(address);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsConnecting(false);
    }
  };

  if (address) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="font-mono text-sm">{formatAddress(address)}</span>
        </div>
        <button
          onClick={() => onConnect(null)}
          className="text-red-600 hover:text-red-800 text-sm font-medium"
        >
          Disconnect
        </button>
      </div>
    );
  }

  const isMetaMaskInstalled = typeof window.ethereum !== 'undefined';

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 text-center">
      <h2 className="text-xl font-bold mb-4">Connect Your Wallet</h2>
      <p className="text-gray-600 mb-6">
        Connect your MetaMask wallet to get started with DeFi Credit Scoring
      </p>
      
      {!isMetaMaskInstalled && (
        <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
          <p className="font-semibold mb-2">MetaMask is not installed</p>
          <p className="text-sm mb-3">
            You need MetaMask browser extension to use this application.
          </p>
          <a
            href="https://metamask.io/download/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded text-sm"
          >
            Install MetaMask →
          </a>
        </div>
      )}

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
          {error.includes('not installed') && (
            <div className="mt-2">
              <a
                href="https://metamask.io/download/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-red-800 underline text-sm"
              >
                Download MetaMask here
              </a>
            </div>
          )}
        </div>
      )}
      
      <button
        onClick={handleConnect}
        disabled={isConnecting || !isMetaMaskInstalled}
        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isConnecting ? 'Connecting...' : 'Connect Wallet'}
      </button>
      
      {!isMetaMaskInstalled && (
        <div className="mt-4 text-sm text-gray-500">
          <p>After installing MetaMask:</p>
          <ol className="list-decimal list-inside mt-2 space-y-1">
            <li>Refresh this page</li>
            <li>Click "Connect Wallet"</li>
            <li>Approve the connection in MetaMask</li>
          </ol>
        </div>
      )}
    </div>
  );
}
