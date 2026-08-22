export default function CreditScoreCard({ report, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-12 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 text-center text-gray-500">
        Connect your wallet to see your credit score
      </div>
    );
  }

  const getScoreColor = (score) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRiskColor = (risk) => {
    const colors = {
      Low: 'bg-green-100 text-green-800',
      Medium: 'bg-yellow-100 text-yellow-800',
      High: 'bg-red-100 text-red-800',
    };
    return colors[risk] || colors.Medium;
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-6">Credit Score Report</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="text-sm text-gray-600 mb-2">Credit Score</div>
          <div className={`text-5xl font-bold ${getScoreColor(report.score)}`}>
            {report.score}
          </div>
          <div className="text-xs text-gray-500 mt-1">out of 100</div>
        </div>

        <div>
          <div className="text-sm text-gray-600 mb-2">Risk Level</div>
          <span className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${getRiskColor(report.risk_level)}`}>
            {report.risk_level}
          </span>
          
          <div className="mt-4">
            <div className="text-sm text-gray-600 mb-2">Fraud Status</div>
            {report.is_fraud ? (
              <span className="inline-block px-4 py-2 rounded-full text-sm font-semibold bg-red-100 text-red-800">
                ⚠️ Flagged as Fraud
              </span>
            ) : (
              <span className="inline-block px-4 py-2 rounded-full text-sm font-semibold bg-green-100 text-green-800">
                ✓ Verified
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 pt-6 border-t">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-600">Transaction Count</div>
            <div className="font-semibold">{report.tx_count}</div>
          </div>
          <div>
            <div className="text-gray-600">Fraud Probability</div>
            <div className="font-semibold">{(report.fraud_probability * 100).toFixed(2)}%</div>
          </div>
        </div>
      </div>
    </div>
  );
}
