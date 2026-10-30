function clampScore(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(0, Math.min(100, number)) : 0;
}

function riskClass(risk) {
  return `risk-${String(risk || 'unknown').toLowerCase()}`;
}

function ScoreIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 19V5m0 14h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="m7 15 4-4 3 2 5-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M16 7h3v3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Skeleton() {
  return (
    <section className="panel score-panel">
      <div className="panel-header">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-pill" />
      </div>
      <div className="skeleton-score-layout">
        <div className="skeleton skeleton-score" />
        <div className="skeleton skeleton-gauge" />
      </div>
      <div className="skeleton skeleton-bar" />
      <div className="skeleton-grid">
        <div className="skeleton skeleton-box" />
        <div className="skeleton skeleton-box" />
      </div>
    </section>
  );
}

export default function CreditScoreCard({ report, isLoading }) {
  if (isLoading && !report) return <Skeleton />;

  if (!report) {
    return (
      <section className="panel empty-report">
        <div className="empty-report-icon"><ScoreIcon /></div>
        <h2>Your credit profile will appear here</h2>
        <p>Connect your wallet and refresh the report to calculate your current score and lending signals.</p>
      </section>
    );
  }

  const primaryScore = clampScore(
    report.combined_credit_score ?? report.behavioral_score ?? report.score
  );
  const primaryRisk = report.combined_risk_level ?? report.behavioral_risk_level ?? report.risk_level ?? 'Unknown';
  const hasCombined = report.combined_credit_score !== undefined && report.combined_credit_score !== null;
  const hasLendingScore = report.lending_behavior_score !== undefined && report.lending_behavior_score !== null;
  const behavioralScore = clampScore(report.behavioral_score ?? report.score);
  const lendingScore = hasLendingScore ? clampScore(report.lending_behavior_score) : null;
  const weights = report.combined_score_weights || report.weights || { behavioral: 0.3, lending: 0.7 };
  const behavioralWeight = Number(weights.behavioral ?? 0.3);
  const lendingWeight = Number(weights.lending ?? 0.7);
  const behavioralPct = Math.round(behavioralWeight * 100);
  const lendingPct = Math.round(lendingWeight * 100);
  const fraudProbability = Number(report.fraud_probability);
  const txCount = Number(report.tx_count);
  const normalizedFraudProbability = Number.isFinite(fraudProbability)
    ? (fraudProbability <= 1 ? fraudProbability * 100 : fraudProbability)
    : null;
  const scoreColor = primaryScore >= 70 ? 'score-high' : primaryScore >= 40 ? 'score-medium' : 'score-low';
  const evidenceCount = report.lending_borrow_event_count ?? 0;

  return (
    <section className="panel score-panel">
      <div className="panel-header score-panel-heading">
        <div>
          <div className="section-kicker"><span className="kicker-dot" /> CREDIT PROFILE</div>
          <h2>Credit score report</h2>
          <p className="panel-subtitle">A view of your wallet behavior and lending activity.</p>
        </div>
        <div className="score-header-badges">
          <span className={`risk-chip ${riskClass(primaryRisk)}`}>{primaryRisk} risk</span>
          <span className={`fraud-chip ${report.is_fraud ? 'fraud-flagged' : 'fraud-clear'}`}>
            <span className="chip-dot" />
            {report.is_fraud ? 'Flagged' : 'Not flagged'}
          </span>
        </div>
      </div>

      <div className="score-hero">
        <div className="score-primary">
          <span className="field-label">{hasCombined ? 'COMBINED SCORE · EXPERIMENTAL' : 'WALLET BEHAVIOR SCORE'}</span>
          <div className={`score-number ${scoreColor}`}>{primaryScore.toFixed(2)}</div>
          <div className="score-caption"><span>out of 100</span><span className="caption-separator">·</span><span>{report.score_type === 'experimental_weighted_composite' ? 'Weighted composite' : 'Behavioral model'}</span></div>
          <div className="score-progress" aria-label={`Score ${primaryScore} out of 100`}>
            <div className={`score-progress-fill ${scoreColor}`} style={{ width: `${primaryScore}%` }} />
          </div>
          <p className="score-supporting-text">
            {primaryScore >= 70
              ? 'Your current index is in the upper band.'
              : primaryScore >= 40
              ? 'Your current index is in the middle band.'
              : 'Your current index is in the lower band.'}
          </p>
        </div>

        <div className="score-gauge-column">
          <div className={`score-gauge ${scoreColor}`} style={{ '--score-value': `${primaryScore * 3.6}deg` }}>
            <div className="score-gauge-center">
              <span>{Math.round(primaryScore)}</span>
              <small>SCORE</small>
            </div>
          </div>
          <div className="gauge-caption">
            <span className="gauge-caption-dot" />
            {report.lending_evidence_level === 'low' ? 'Early evidence' : 'Latest report'}
          </div>
        </div>
      </div>

      {hasCombined && (
        <div className="score-breakdown">
          <div className="subsection-heading">
            <div>
              <h3>Score composition</h3>
              <p>See how each signal contributes to the result.</p>
            </div>
            <span className="provisional-tag">Provisional weights</span>
          </div>

          <div className="component-grid">
            <div className="component-card">
              <div className="component-topline">
                <span className="component-symbol wallet-symbol">W</span>
                <span className="component-weight">{behavioralPct}% weight</span>
              </div>
              <div className="component-title">Wallet behavior</div>
              <div className="component-score-line">
                <strong>{behavioralScore.toFixed(2)}</strong><span>/ 100</span>
              </div>
              <div className="component-track">
                <div className="component-fill component-fill-wallet" style={{ width: `${behavioralScore}%` }} />
              </div>
              <p>Historical Ethereum transaction patterns</p>
            </div>

            <div className="component-card">
              <div className="component-topline">
                <span className="component-symbol lending-symbol">L</span>
                <span className="component-weight">{lendingPct}% weight</span>
              </div>
              <div className="component-title">Lending behavior</div>
              <div className="component-score-line">
                <strong>{lendingScore === null ? '—' : lendingScore.toFixed(2)}</strong><span>/ 100</span>
              </div>
              <div className="component-track">
                <div className="component-fill component-fill-lending" style={{ width: `${lendingScore ?? 0}%` }} />
              </div>
              <p>{hasLendingScore ? `${evidenceCount} observed borrow event${Number(evidenceCount) === 1 ? '' : 's'} · ${report.lending_evidence_level || 'unrated'} evidence` : 'No lending score available yet'}</p>
            </div>
          </div>

          <div className="methodology-note">
            <span className="note-icon">i</span>
            <p>
              Experimental weighted index, not a validated default-risk estimate.
              {report.combined_score_formula ? ` Formula: ${report.combined_score_formula}.` : ''}
            </p>
          </div>
        </div>
      )}

      <div className="score-footer-metrics">
        <div className="footer-metric">
          <span className="metric-icon metric-icon-purple"><ScoreIcon /></span>
          <div><span className="field-label">TRANSACTION COUNT</span><strong>{Number.isFinite(txCount) ? txCount.toLocaleString() : '—'}</strong></div>
        </div>
        <div className="footer-metric">
          <span className="metric-icon metric-icon-mint">%</span>
          <div>
            <span className="field-label">FRAUD PROBABILITY</span>
            <strong>{normalizedFraudProbability === null ? '—' : `${normalizedFraudProbability.toFixed(2)}%`}</strong>
          </div>
        </div>
      </div>
    </section>
  );
}
