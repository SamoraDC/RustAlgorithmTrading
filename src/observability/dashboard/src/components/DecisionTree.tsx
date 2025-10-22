import { useEffect, useState } from 'react';
import { Decision } from '@/types/metrics';
import { useWebSocketMessages } from '@/hooks/useWebSocket';
import './DecisionTree.css';

export function DecisionTree() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [wsDecision, loading] = useWebSocketMessages<Decision>('decision', {} as Decision);

  useEffect(() => {
    if (!loading && wsDecision.id) {
      setDecisions((prev) => [wsDecision, ...prev.slice(0, 9)]);
    }
  }, [wsDecision, loading]);

  const latestDecision = decisions[0];

  const getTypeClass = (type: string): string => {
    return type === 'buy' ? 'type-buy' : type === 'sell' ? 'type-sell' : 'type-hold';
  };

  const getImpactClass = (impact: string): string => {
    return impact === 'positive'
      ? 'impact-positive'
      : impact === 'negative'
      ? 'impact-negative'
      : 'impact-neutral';
  };

  return (
    <div className="decision-tree">
      <h2>Decision Analysis</h2>
      {latestDecision ? (
        <div className="decision-latest">
          <div className="decision-header">
            <span className={`decision-type ${getTypeClass(latestDecision.type)}`}>
              {latestDecision.type.toUpperCase()}
            </span>
            <span className="decision-symbol">{latestDecision.symbol}</span>
            <span className="decision-confidence">
              Confidence: {(latestDecision.confidence * 100).toFixed(1)}%
            </span>
          </div>

          <div className="decision-details">
            <div className="decision-price">
              Price: ${latestDecision.price.toFixed(2)}
            </div>
            <div className="decision-quantity">
              Qty: {latestDecision.quantity}
            </div>
            <div className="decision-time">
              {new Date(latestDecision.timestamp).toLocaleTimeString()}
            </div>
          </div>

          <div className="decision-reasoning">
            <h3>Reasoning</h3>
            <p>{latestDecision.reasoning}</p>
          </div>

          <div className="decision-factors">
            <h3>Contributing Factors</h3>
            {latestDecision.factors.map((factor, idx) => (
              <div key={idx} className="factor">
                <div className="factor-header">
                  <span className="factor-name">{factor.name}</span>
                  <span className={`factor-impact ${getImpactClass(factor.impact)}`}>
                    {factor.impact}
                  </span>
                </div>
                <div className="factor-metrics">
                  <div className="factor-value">Value: {factor.value.toFixed(4)}</div>
                  <div className="factor-weight">Weight: {factor.weight.toFixed(2)}</div>
                </div>
                <div className="factor-bar">
                  <div
                    className={`factor-bar-fill ${getImpactClass(factor.impact)}`}
                    style={{ width: `${Math.abs(factor.value) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="decision-empty">No decisions yet</div>
      )}

      <div className="decision-history">
        <h3>Recent Decisions</h3>
        {decisions.slice(1, 10).map((decision) => (
          <div key={decision.id} className="decision-history-item">
            <span className={`decision-type ${getTypeClass(decision.type)}`}>
              {decision.type}
            </span>
            <span className="decision-symbol">{decision.symbol}</span>
            <span className="decision-price">${decision.price.toFixed(2)}</span>
            <span className="decision-time">
              {new Date(decision.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
