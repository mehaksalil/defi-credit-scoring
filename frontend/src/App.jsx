import { useCallback, useEffect, useState } from 'react';
import WalletConnection from './components/WalletConnection';
import CreditScoreCard from './components/CreditScoreCard';
import LendingPool from './components/LendingPool';
import { getWalletReport } from './utils/api';
import { CONFIG } from './config';

function RefreshIcon({ spinning = false }) {
  return (
    <svg className={spinning ? 'icon icon-spin' : 'icon'} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M20 7v5h-5M4 17v-5h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 9a7 7 0 0 1 11.8-2L20 12M4 12l2.7 5A7 7 0 0 0 18.5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function App() {
  const [address, setAddress] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadReport = useCallback(async () => {
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
  }, [address]);

  useEffect(() => {
    if (address) {
      loadReport();
    } else {
      setReport(null);
      setError('');
    }
  }, [address, loadReport]);

  const displayAddress = address
    ? `${address.slice(0, 6)}…${address.slice(-4)}`
    : null;

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />

      <header className="topbar">
        <a className="brand" href="/" aria-label="DeFiScore home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 34 34" fill="none">
              <path d="M17 3.7 28.3 10v14L17 30.3 5.7 24V10L17 3.7Z" stroke="currentColor" strokeWidth="1.5" />
              <path d="m17 8.5 7 4v8l-7 4-7-4v-8l7-4Z" fill="currentColor" opacity=".22" />
              <path d="m12 17 3.2 3.2L22.5 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="brand-copy">
            <strong>DeFi<span>Score</span></strong>
            <small>Credit intelligence</small>
          </span>
        </a>

        <div className="topbar-right">
          <span className="network-pill"><span className="network-dot" /> Hardhat Local</span>
          <WalletConnection address={address} onConnect={setAddress} />
        </div>
      </header>

      <main className="main-content">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line" /> DECENTRALIZED CREDIT INTELLIGENCE</div>
            <h1>Credit that moves<br className="desktop-break" /> with <span>your on-chain story.</span></h1>
            <p>Understand your wallet profile, build lending history, and manage collateral—all from one transparent dashboard.</p>
          </div>
          <div className="hero-side">
            <div className="hero-side-icon" aria-hidden="true">
              <svg viewBox="0 0 48 48" fill="none">
                <path d="M24 4.5 39 13v22L24 43.5 9 35V13L24 4.5Z" stroke="currentColor" strokeWidth="1.6" />
                <path d="M16 24.5 21.5 30 33 18.5" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <strong>Transparent by design</strong>
              <span>Scores, evidence, and on-chain actions in one place.</span>
            </div>
          </div>
        </section>

        {address && (
          <div className="dashboard-toolbar">
            <div>
              <span className="section-kicker">YOUR WORKSPACE</span>
              <h2>Wallet overview</h2>
              <p>Connected account <span className="mono-address">{displayAddress}</span></p>
            </div>
            <button className="btn btn-secondary" onClick={loadReport} disabled={loading}>
              <RefreshIcon spinning={loading} />
              {loading ? 'Refreshing…' : 'Refresh report'}
            </button>
          </div>
        )}

        {!address && (
          <section className="welcome-panel">
            <div className="welcome-orb" aria-hidden="true">
              <svg viewBox="0 0 60 60" fill="none">
                <path d="M30 5 49 16v28L30 55 11 44V16L30 5Z" stroke="currentColor" strokeWidth="1.7" />
                <path d="M20 30.5 27 37l14-15" stroke="currentColor" strokeWidth="2.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="section-kicker">START HERE</span>
            <h2>Your wallet. A clearer picture.</h2>
            <p>Connect MetaMask to load your credit report, review verified lending activity, and interact with the local lending pool.</p>
            <div className="welcome-points">
              <span><i>01</i> Review your score</span>
              <span><i>02</i> Understand the evidence</span>
              <span><i>03</i> Manage lending activity</span>
            </div>
          </section>
        )}

        {address && error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">!</span>
            <div><strong>Report unavailable</strong><p>{error}</p></div>
            <button className="alert-dismiss" onClick={() => setError('')} aria-label="Dismiss error">×</button>
          </div>
        )}

        {address && (
          <div className="dashboard-stack">
            <CreditScoreCard report={report} isLoading={loading} />
            {CONFIG.LENDING_POOL_ADDRESS ? (
              <LendingPool address={address} report={report} onReportRefresh={loadReport} />
            ) : (
              <div className="alert alert-warning">
                <span className="alert-icon">!</span>
                <div><strong>Lending pool not configured</strong><p>Set VITE_LENDING_POOL_ADDRESS in your frontend environment file.</p></div>
              </div>
            )}
          </div>
        )}

        <footer className="app-footer">
          <div className="footer-brand"><span className="footer-mark">D</span> DeFiScore</div>
          <span>Local development environment · Hardhat network</span>
          <span className="footer-note">Experimental index, not financial advice.</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
