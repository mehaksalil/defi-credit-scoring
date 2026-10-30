import { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { CONFIG } from '../config';
import { LENDING_POOL_ABI, MOCK_ERC20_ABI } from '../contracts/abis';
import { formatEther, parseEther } from '../utils/wallet';
import { syncScoreOnChain, requestTestTokens } from '../utils/api';

const actionDetails = {
  deposit: {
    title: 'Add collateral',
    helper: 'Deposit MOCK to increase your available collateral.',
    button: 'Deposit MOCK',
  },
  withdraw: {
    title: 'Withdraw collateral',
    helper: 'Move available collateral back to your wallet.',
    button: 'Withdraw MOCK',
  },
  borrow: {
    title: 'Borrow MOCK',
    helper: 'Borrow against eligible collateral when your on-chain score meets the protocol rules.',
    button: 'Borrow MOCK',
  },
  repay: {
    title: 'Repay your loan',
    helper: 'Repay outstanding debt to restore your available borrowing capacity.',
    button: 'Repay MOCK',
  },
};

function StatIcon({ kind }) {
  const paths = {
    balance: <><rect x="3.5" y="6" width="17" height="13" rx="2.5" /><path d="M3.5 10h17M7 15h3" /></>,
    collateral: <><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" /><path d="m8.5 12 2.2 2.2 4.8-4.8" /></>,
    debt: <><circle cx="12" cy="12" r="8.5" /><path d="M15 9.5c-.6-.8-1.5-1.2-2.8-1.2-1.4 0-2.4.7-2.4 1.8 0 2.9 5.1 1 5.1 4 0 1.1-1 2-2.6 2-1.4 0-2.5-.5-3.2-1.5M12.2 6.5v11" /></>,
    limit: <><path d="M4 18.5h16M6 16V9m6 7V5m6 11v-4" /><path d="m4.5 7 5-3 4 2 5-3" /></>,
  };
  return (
    <span className={`stat-icon stat-icon-${kind}`} aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[kind]}</svg>
    </span>
  );
}

function RefreshMiniIcon({ spinning = false }) {
  return (
    <svg className={spinning ? 'icon icon-spin' : 'icon'} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M20 7v5h-5M4 17v-5h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 9a7 7 0 0 1 11.8-2L20 12M4 12l2.7 5A7 7 0 0 0 18.5 15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function LendingPool({ address, report, onReportRefresh }) {
  const [tokenBalance, setTokenBalance] = useState('0');
  const [collateral, setCollateral] = useState('0');
  const [debt, setDebt] = useState('0');
  const [borrowLimit, setBorrowLimit] = useState('0');
  const [onChainScore, setOnChainScore] = useState(0);
  const [onChainFraud, setOnChainFraud] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingPool, setLoadingPool] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [fauceting, setFauceting] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');
  const [syncKind, setSyncKind] = useState('success');
  const [error, setError] = useState('');
  const [action, setAction] = useState('deposit');
  const [amount, setAmount] = useState('');

  useEffect(() => {
    if (address && CONFIG.LENDING_POOL_ADDRESS) loadPoolData();
  }, [address]);

  const loadPoolData = async () => {
    setLoadingPool(true);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const poolContract = new ethers.Contract(CONFIG.LENDING_POOL_ADDRESS, LENDING_POOL_ABI, provider);
      const tokenAddress = await poolContract.token();
      const tokenContract = new ethers.Contract(tokenAddress, MOCK_ERC20_ABI, provider);
      const userAddress = address || await (await provider.getSigner()).getAddress();

      const [balance, coll, userDebt, limit, score, fraud] = await Promise.all([
        tokenContract.balanceOf(userAddress),
        poolContract.collateral(userAddress),
        poolContract.debt(userAddress),
        poolContract.getBorrowLimit(userAddress),
        poolContract.creditScore(userAddress),
        poolContract.isFraud(userAddress),
      ]);

      setTokenBalance(formatEther(balance));
      setCollateral(formatEther(coll));
      setDebt(formatEther(userDebt));
      setBorrowLimit(formatEther(limit));
      setOnChainScore(Number(score));
      setOnChainFraud(fraud);
    } catch (err) {
      console.error('Error loading pool data:', err);
      setError('Unable to load the Lending Pool. Check MetaMask is on Hardhat Local and the deployed contract addresses match.');
    } finally {
      setLoadingPool(false);
    }
  };

  const handleSyncOnChain = async () => {
    if (!address) return;
    setSyncing(true);
    setError('');
    setSyncMessage('');
    try {
      const result = await syncScoreOnChain(address);
      setSyncKind('success');
      setSyncMessage(
        `Score synced successfully · ${result.synced_score}/100 · ${result.synced_is_fraud ? 'Fraud flag raised' : 'No fraud flag'} · Tx ${result.tx_hash.slice(0, 10)}…`
      );
      if (onReportRefresh) await onReportRefresh();
      await loadPoolData();
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Sync failed';
      setError(`Score sync failed: ${detail}`);
      console.error('Sync error:', err);
    } finally {
      setSyncing(false);
    }
  };

  const handleFaucet = async () => {
    if (!address) return;
    setFauceting(true);
    setError('');
    setSyncMessage('');
    try {
      const result = await requestTestTokens(address, 1000);
      setSyncKind('success');
      setSyncMessage(`1000 MOCK added to your wallet · Tx ${result.tx_hash.slice(0, 10)}…`);
      await loadPoolData();
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Faucet request failed';
      setError(`Test-token request failed: ${detail}`);
      console.error('Faucet error:', err);
    } finally {
      setFauceting(false);
    }
  };

  const handleAction = async () => {
    if (!amount || !Number.isFinite(Number(amount)) || Number(amount) <= 0) {
      setError('Enter an amount greater than zero.');
      return;
    }
    if (action === 'borrow' && !canBorrow) {
      setError(onChainFraud
        ? 'Borrowing is disabled because this wallet is flagged by the contract.'
        : `Borrowing requires an on-chain score of at least 40. Current score: ${onChainScore}.`);
      return;
    }

    setLoading(true);
    setError('');
    setSyncMessage('');

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const poolContract = new ethers.Contract(CONFIG.LENDING_POOL_ADDRESS, LENDING_POOL_ABI, signer);
      const tokenAddress = await poolContract.token();
      const tokenContract = new ethers.Contract(tokenAddress, MOCK_ERC20_ABI, signer);
      const amountWei = parseEther(amount);

      if (action === 'deposit') {
        const approveTx = await tokenContract.approve(CONFIG.LENDING_POOL_ADDRESS, amountWei);
        await approveTx.wait();
        const tx = await poolContract.deposit(amountWei);
        await tx.wait();
      } else if (action === 'withdraw') {
        const tx = await poolContract.withdraw(amountWei);
        await tx.wait();
      } else if (action === 'borrow') {
        const tx = await poolContract.borrow(amountWei);
        await tx.wait();
      } else if (action === 'repay') {
        const approveTx = await tokenContract.approve(CONFIG.LENDING_POOL_ADDRESS, amountWei);
        await approveTx.wait();
        const tx = await poolContract.repay(amountWei);
        await tx.wait();
      }

      const submittedAction = action;
      setAmount('');
      setSyncKind('success');
      setSyncMessage(`${submittedAction.charAt(0).toUpperCase() + submittedAction.slice(1)} confirmed. Updating your credit profile…`);
      await loadPoolData();

      // Sync only after the lending transaction is confirmed.
      try {
        const syncResult = await syncScoreOnChain(address);
        setSyncMessage(
          `${submittedAction.charAt(0).toUpperCase() + submittedAction.slice(1)} confirmed · Score synced to ${syncResult.synced_score} · Tx ${syncResult.tx_hash.slice(0, 10)}…`
        );
        if (onReportRefresh) await onReportRefresh();
      } catch (syncErr) {
        const detail = syncErr?.response?.data?.detail || syncErr.message || 'Score sync failed';
        setSyncKind('warning');
        setSyncMessage(`${submittedAction.charAt(0).toUpperCase() + submittedAction.slice(1)} confirmed, but score sync failed: ${detail}`);
      }
      await loadPoolData();
    } catch (err) {
      const detail = err?.shortMessage || err?.reason || err?.response?.data?.detail || err.message || 'Transaction failed';
      setError(detail);
      setSyncMessage('');
      console.error('Transaction error:', err);
    } finally {
      setLoading(false);
    }
  };

  const apiScore = Number(report?.combined_credit_score ?? report?.score ?? report?.behavioral_score ?? 0);
  const apiRisk = report?.combined_risk_level ?? report?.risk_level ?? report?.behavioral_risk_level ?? 'Unknown';
  const expectedOnChainScore = Math.floor(Math.max(0, Math.min(100, Number(apiScore) || 0)));
  const scoresAreOutOfSync = Boolean(report) && expectedOnChainScore !== onChainScore;
  const canBorrow = !onChainFraud && onChainScore >= 40;
  const currentAction = actionDetails[action];

  const formatAmount = (value) => {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 }) : '0.00';
  };

  return (
    <section className="panel lending-panel">
      <div className="panel-header lending-heading">
        <div>
          <div className="section-kicker"><span className="kicker-dot kicker-dot-mint" /> LOCAL LENDING PROTOCOL</div>
          <h2>Lending pool</h2>
          <p className="panel-subtitle">Use MOCK collateral to explore borrowing on your local test network.</p>
        </div>
        <div className="protocol-pill"><span className="protocol-pulse" /> Contract connected</div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <span className="alert-icon">!</span>
          <div><strong>Action needs attention</strong><p>{error}</p></div>
          <button className="alert-dismiss" onClick={() => setError('')} aria-label="Dismiss error">×</button>
        </div>
      )}

      {syncMessage && (
        <div className={`alert ${syncKind === 'warning' ? 'alert-warning' : 'alert-success'}`} role="status">
          <span className="alert-icon">{syncKind === 'warning' ? '!' : '✓'}</span>
          <div><strong>{syncKind === 'warning' ? 'Partial success' : 'Transaction update'}</strong><p>{syncMessage}</p></div>
          <button className="alert-dismiss" onClick={() => setSyncMessage('')} aria-label="Dismiss message">×</button>
        </div>
      )}

      <div className="credit-status-box">
        <div className="credit-status-heading">
          <div>
            <h3>Credit status</h3>
            <p>Off-chain calculation compared with the contract value.</p>
          </div>
          {scoresAreOutOfSync && <span className="sync-needed-tag">Sync needed</span>}
          {!scoresAreOutOfSync && report && <span className="synced-tag"><span className="chip-dot" /> In sync</span>}
        </div>
        <div className="credit-status-grid">
          <div className="credit-status-item">
            <span className="field-label">OFF-CHAIN REPORT</span>
            <div className="credit-status-value">{report ? `${apiScore.toFixed(2)}` : '—'}<span>/100</span></div>
            <small>{report ? `${apiRisk} risk` : 'Report unavailable'}</small>
          </div>
          <div className="credit-status-divider" />
          <div className="credit-status-item">
            <span className="field-label">ON-CHAIN SCORE</span>
            <div className="credit-status-value">{onChainScore}<span>/100</span></div>
            <small className={onChainFraud ? 'text-danger' : 'text-success'}>{onChainFraud ? 'Fraud flag raised' : 'No fraud flag'}</small>
          </div>
          <div className="credit-status-actions">
            <button type="button" className="btn btn-primary" onClick={handleSyncOnChain} disabled={syncing || !report}>
              <RefreshMiniIcon spinning={syncing} />
              {syncing ? 'Syncing score…' : 'Sync score'}
            </button>
            <button type="button" className="btn btn-quiet" onClick={loadPoolData} disabled={loadingPool}>
              <RefreshMiniIcon spinning={loadingPool} />
              Refresh chain
            </button>
          </div>
        </div>
        {scoresAreOutOfSync && (
          <div className="inline-notice">
            Your report and contract differ. Sync the latest experimental score before borrowing.
          </div>
        )}
      </div>

      <div className="pool-stats-grid">
        <div className="pool-stat-card">
          <div className="stat-topline"><span>Your token balance</span><StatIcon kind="balance" /></div>
          <strong>{formatAmount(tokenBalance)} <small>MOCK</small></strong>
          <span className="stat-footnote">Wallet balance</span>
        </div>
        <div className="pool-stat-card stat-card-collateral">
          <div className="stat-topline"><span>Collateral</span><StatIcon kind="collateral" /></div>
          <strong>{formatAmount(collateral)} <small>MOCK</small></strong>
          <span className="stat-footnote">Supplied to the pool</span>
        </div>
        <div className="pool-stat-card stat-card-debt">
          <div className="stat-topline"><span>Outstanding debt</span><StatIcon kind="debt" /></div>
          <strong>{formatAmount(debt)} <small>MOCK</small></strong>
          <span className="stat-footnote">{Number(debt) > 0 ? 'Repayment due through the demo' : 'No active debt'}</span>
        </div>
        <div className="pool-stat-card stat-card-limit">
          <div className="stat-topline"><span>Borrowing limit</span><StatIcon kind="limit" /></div>
          <strong>{formatAmount(borrowLimit)} <small>MOCK</small></strong>
          <span className="stat-footnote">Based on on-chain rules</span>
        </div>
      </div>

      <div className="pool-actions">
        <div className="pool-actions-heading">
          <div>
            <div className="section-kicker">TAKE AN ACTION</div>
            <h3>Manage your position</h3>
            <p>Transactions are confirmed by MetaMask on the local Hardhat network.</p>
          </div>
          <button type="button" className="btn btn-secondary faucet-button" onClick={handleFaucet} disabled={fauceting}>
            {fauceting ? 'Requesting tokens…' : 'Get 1,000 test tokens'}
          </button>
        </div>

        <div className="action-tabs" role="tablist" aria-label="Lending action">
          {['deposit', 'withdraw', 'borrow', 'repay'].map((act) => (
            <button
              type="button"
              role="tab"
              aria-selected={action === act}
              key={act}
              onClick={() => {
                setAction(act);
                setAmount('');
                setError('');
                setSyncMessage('');
              }}
              className={`action-tab ${action === act ? 'action-tab-active' : ''}`}
              disabled={act === 'borrow' && !canBorrow}
              title={act === 'borrow' && !canBorrow ? 'Requires on-chain score of at least 40 and no fraud flag' : undefined}
            >
              <span className={`action-tab-symbol action-symbol-${act}`}>{act === 'deposit' ? '+' : act === 'withdraw' ? '↗' : act === 'borrow' ? '↓' : '↺'}</span>
              <span>{act.charAt(0).toUpperCase() + act.slice(1)}</span>
              {act === 'borrow' && !canBorrow && <span className="tab-lock" aria-label="Disabled">•</span>}
            </button>
          ))}
        </div>

        <div className="action-form">
          <div className="action-form-copy">
            <h4>{currentAction.title}</h4>
            <p>{currentAction.helper}</p>
            {action === 'borrow' && !canBorrow && (
              <div className="borrow-eligibility-note">
                <span className="note-icon">i</span>
                {onChainFraud
                  ? 'Borrowing is disabled because the contract has flagged this wallet.'
                  : `Borrowing requires an on-chain score of at least 40. Your current score is ${onChainScore}.`}
              </div>
            )}
          </div>
          <div className="amount-control">
            <label htmlFor="lending-amount">Amount to {action}</label>
            <div className="amount-input-row">
              <div className="amount-input-wrap">
                <input
                  id="lending-amount"
                  type="number"
                  min="0"
                  step="0.0001"
                  inputMode="decimal"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  disabled={loading}
                />
                <span className="input-token">MOCK</span>
              </div>
              <button
                type="button"
                className="btn btn-action"
                onClick={handleAction}
                disabled={loading || !amount || (action === 'borrow' && !canBorrow)}
              >
                {loading ? <><span className="button-spinner" /> Processing…</> : currentAction.button}
              </button>
            </div>
            <p className="amount-footnote">Make sure the amount matches your available balance and protocol limits.</p>
          </div>
        </div>
      </div>
      <div className="panel-bottomline">
        <span><span className="network-dot" /> Connected to local Hardhat</span>
        <span>MOCK is a test token for this demonstration.</span>
      </div>
    </section>
  );
}
