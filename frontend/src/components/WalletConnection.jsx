import { useState } from 'react';
import { connectWallet, formatAddress } from '../utils/wallet';

function WalletIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5H19a1.5 1.5 0 0 1 1.5 1.5V19H6a2 2 0 0 1-2-2V7.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M4.5 8H19a1.5 1.5 0 0 1 1.5 1.5v2H16a2 2 0 0 0 0 4h4.5" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M16 13.5h.01" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" />
    </svg>
  );
}

export default function WalletConnection({ onConnect, address }) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState('');
  const isMetaMaskInstalled = typeof window.ethereum !== 'undefined';

  const handleConnect = async () => {
    setIsConnecting(true);
    setError('');
    try {
      if (!isMetaMaskInstalled) {
        throw new Error('MetaMask is not installed. Install the browser extension to continue.');
      }
      const result = await connectWallet();
      onConnect(result.address);
    } catch (err) {
      setError(err.message || 'Unable to connect wallet.');
    } finally {
      setIsConnecting(false);
    }
  };

  if (address) {
    return (
      <div className="wallet-connected">
        <span className="wallet-connected-dot" />
        <span className="wallet-label">Connected</span>
        <span className="wallet-address">{formatAddress(address)}</span>
        <button
          type="button"
          className="wallet-disconnect"
          onClick={() => onConnect(null)}
        >
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <div className="wallet-connection-wrap">
      <button
        type="button"
        onClick={handleConnect}
        disabled={isConnecting || !isMetaMaskInstalled}
        className="btn btn-primary wallet-connect-button"
      >
        <WalletIcon />
        {isConnecting ? 'Connecting…' : isMetaMaskInstalled ? 'Connect wallet' : 'MetaMask required'}
      </button>
      {error && <div className="wallet-error" role="alert">{error}</div>}
      {!isMetaMaskInstalled && (
        <a className="wallet-install-link" href="https://metamask.io/download/" target="_blank" rel="noopener noreferrer">
          Install MetaMask
        </a>
      )}
    </div>
  );
}
