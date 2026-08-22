import { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { CONFIG } from '../config';
import { LENDING_POOL_ABI, MOCK_ERC20_ABI } from '../contracts/abis';
import { formatEther, parseEther } from '../utils/wallet';

export default function LendingPool({ address, report }) {
  const [poolData, setPoolData] = useState(null);
  const [tokenBalance, setTokenBalance] = useState('0');
  const [collateral, setCollateral] = useState('0');
  const [debt, setDebt] = useState('0');
  const [borrowLimit, setBorrowLimit] = useState('0');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [action, setAction] = useState('deposit');
  const [amount, setAmount] = useState('');

  useEffect(() => {
    if (address && CONFIG.LENDING_POOL_ADDRESS) {
      loadPoolData();
    }
  }, [address]);

  const loadPoolData = async () => {
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const poolContract = new ethers.Contract(
        CONFIG.LENDING_POOL_ADDRESS,
        LENDING_POOL_ABI,
        provider
      );
      const tokenAddress = await poolContract.token();
      const tokenContract = new ethers.Contract(
        tokenAddress,
        MOCK_ERC20_ABI,
        provider
      );

      const signer = await provider.getSigner();
      const userAddress = await signer.getAddress();

      const [balance, coll, userDebt, limit] = await Promise.all([
        tokenContract.balanceOf(userAddress),
        poolContract.collateral(userAddress),
        poolContract.debt(userAddress),
        poolContract.getBorrowLimit(userAddress),
      ]);

      setTokenBalance(formatEther(balance));
      setCollateral(formatEther(coll));
      setDebt(formatEther(userDebt));
      setBorrowLimit(formatEther(limit));
    } catch (err) {
      console.error('Error loading pool data:', err);
      setError('Failed to load pool data');
    }
  };

  const handleAction = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setError('Please enter a valid amount');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const poolContract = new ethers.Contract(
        CONFIG.LENDING_POOL_ADDRESS,
        LENDING_POOL_ABI,
        signer
      );
      const tokenAddress = await poolContract.token();
      const tokenContract = new ethers.Contract(
        tokenAddress,
        MOCK_ERC20_ABI,
        signer
      );

      const amountWei = parseEther(amount);

      if (action === 'deposit') {
        // Approve first
        const approveTx = await tokenContract.approve(CONFIG.LENDING_POOL_ADDRESS, amountWei);
        await approveTx.wait();
        // Then deposit
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

      setAmount('');
      await loadPoolData();
    } catch (err) {
      setError(err.message || 'Transaction failed');
      console.error('Transaction error:', err);
    } finally {
      setLoading(false);
    }
  };

  const canBorrow = report && !report.is_fraud && report.score >= 40;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-6">Lending Pool</h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-50 p-4 rounded">
          <div className="text-sm text-gray-600">Your Token Balance</div>
          <div className="text-2xl font-bold">{parseFloat(tokenBalance).toFixed(4)} MOCK</div>
        </div>
        <div className="bg-gray-50 p-4 rounded">
          <div className="text-sm text-gray-600">Collateral</div>
          <div className="text-2xl font-bold">{parseFloat(collateral).toFixed(4)} MOCK</div>
        </div>
        <div className="bg-gray-50 p-4 rounded">
          <div className="text-sm text-gray-600">Debt</div>
          <div className="text-2xl font-bold">{parseFloat(debt).toFixed(4)} MOCK</div>
        </div>
        <div className="bg-gray-50 p-4 rounded">
          <div className="text-sm text-gray-600">Borrow Limit</div>
          <div className="text-2xl font-bold">{parseFloat(borrowLimit).toFixed(4)} MOCK</div>
        </div>
      </div>

      <div className="border-t pt-6">
        <div className="mb-4">
          <div className="flex space-x-2 mb-4">
            {['deposit', 'withdraw', 'borrow', 'repay'].map((act) => (
              <button
                key={act}
                onClick={() => {
                  setAction(act);
                  setAmount('');
                  setError('');
                }}
                className={`px-4 py-2 rounded capitalize ${
                  action === act
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
                disabled={act === 'borrow' && !canBorrow}
              >
                {act}
              </button>
            ))}
          </div>

          {action === 'borrow' && !canBorrow && (
            <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
              {report?.is_fraud
                ? 'Cannot borrow: Wallet flagged as fraud'
                : report?.score < 40
                ? 'Cannot borrow: Credit score too low (minimum 40)'
                : 'Cannot borrow: Check your credit score'}
            </div>
          )}

          <div className="flex space-x-2">
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="Amount"
              className="flex-1 border border-gray-300 rounded px-4 py-2"
              step="0.0001"
            />
            <button
              onClick={handleAction}
              disabled={loading || !amount}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded disabled:opacity-50"
            >
              {loading ? 'Processing...' : action.charAt(0).toUpperCase() + action.slice(1)}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
