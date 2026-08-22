import { useState, useEffect } from 'react';
import WalletConnection from './components/WalletConnection';
import CreditScoreCard from './components/CreditScoreCard';
import LendingPool from './components/LendingPool';
import { getWalletReport } from './utils/api';
import { CONFIG } from './config';

function App() {
  const [address, setAddress] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (address) {
      loadReport();
    } else {
      setReport(null);
    }
  }, [address]);

  const loadReport = async () => {
    if (!address) return;
    
    setLoading(true);
    setError('');
    try {
      const data = await getWalletReport(address);
      setReport(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load credit report');
      console.error('Error loading report:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            DeFi Credit Scoring
          </h1>
          <p className="text-white/80">
            AI-powered credit scoring and decentralized lending
          </p>
        </header>

        <div className="space-y-6">
          <WalletConnection address={address} onConnect={setAddress} />

          {address && (
            <>
              {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex justify-end mb-4">
                <button
                  onClick={loadReport}
                  disabled={loading}
                  className="bg-white hover:bg-gray-100 text-gray-800 font-bold py-2 px-4 rounded disabled:opacity-50"
                >
                  {loading ? 'Loading...' : 'Refresh Report'}
                </button>
              </div>

              <CreditScoreCard report={report} isLoading={loading} />

              {CONFIG.LENDING_POOL_ADDRESS && (
                <LendingPool address={address} report={report} />
              )}

              {!CONFIG.LENDING_POOL_ADDRESS && (
                <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
                  ⚠️ Lending pool not configured. Please set VITE_LENDING_POOL_ADDRESS in your .env file.
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
