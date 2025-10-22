import { useTrades } from '@/hooks/useTrades';
import { formatDistanceToNow } from 'date-fns';
import './TradeTimeline.css';

export function TradeTimeline() {
  const { trades, loading } = useTrades(50);

  const getStatusClass = (status: string): string => {
    switch (status) {
      case 'filled':
        return 'status-filled';
      case 'cancelled':
        return 'status-cancelled';
      case 'rejected':
        return 'status-rejected';
      default:
        return 'status-pending';
    }
  };

  const getSideClass = (side: string): string => {
    return side === 'buy' ? 'side-buy' : 'side-sell';
  };

  if (loading) {
    return (
      <div className="trade-timeline">
        <h2>Trade Timeline</h2>
        <div className="timeline-loading">Loading trades...</div>
      </div>
    );
  }

  return (
    <div className="trade-timeline">
      <h2>Trade Timeline</h2>

      <div className="timeline-stats">
        <div className="stat">
          <span className="stat-label">Total Trades:</span>
          <span className="stat-value">{trades.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Filled:</span>
          <span className="stat-value">
            {trades.filter((t) => t.status === 'filled').length}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Pending:</span>
          <span className="stat-value">
            {trades.filter((t) => t.status === 'pending' || t.status === 'open').length}
          </span>
        </div>
      </div>

      <div className="timeline-list">
        {trades.map((trade) => (
          <div key={trade.id} className="timeline-item">
            <div className="timeline-marker">
              <div className={`marker-dot ${getStatusClass(trade.status)}`} />
              <div className="marker-line" />
            </div>

            <div className="timeline-content">
              <div className="trade-header">
                <span className={`trade-side ${getSideClass(trade.side)}`}>
                  {trade.side.toUpperCase()}
                </span>
                <span className="trade-symbol">{trade.symbol}</span>
                <span className={`trade-status ${getStatusClass(trade.status)}`}>
                  {trade.status}
                </span>
              </div>

              <div className="trade-details">
                <div className="detail">
                  <span className="detail-label">Price:</span>
                  <span className="detail-value">${trade.price.toFixed(2)}</span>
                </div>
                <div className="detail">
                  <span className="detail-label">Quantity:</span>
                  <span className="detail-value">
                    {trade.filled_quantity}/{trade.quantity}
                  </span>
                </div>
                <div className="detail">
                  <span className="detail-label">Type:</span>
                  <span className="detail-value">{trade.type}</span>
                </div>
                {trade.pnl !== undefined && (
                  <div className="detail">
                    <span className="detail-label">PnL:</span>
                    <span
                      className={`detail-value ${trade.pnl >= 0 ? 'positive' : 'negative'}`}
                    >
                      ${trade.pnl.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              <div className="trade-footer">
                <span className="trade-time">
                  {formatDistanceToNow(trade.timestamp, { addSuffix: true })}
                </span>
                {trade.execution_time_ms && (
                  <span className="trade-execution-time">
                    Execution: {trade.execution_time_ms}ms
                  </span>
                )}
                {trade.slippage && (
                  <span className="trade-slippage">
                    Slippage: {(trade.slippage * 100).toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
