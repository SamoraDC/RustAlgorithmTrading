import { useState, useEffect } from 'react';
import { Metrics } from '@/types/metrics';
import { useWebSocketMessages } from './useWebSocket';
import { getMetrics } from '@/services/api';

const INITIAL_METRICS: Metrics = {
  pnl: 0,
  pnl_percent: 0,
  win_rate: 0,
  sharpe_ratio: 0,
  max_drawdown: 0,
  total_trades: 0,
  winning_trades: 0,
  losing_trades: 0,
  avg_win: 0,
  avg_loss: 0,
  largest_win: 0,
  largest_loss: 0,
  timestamp: Date.now(),
};

export function useMetrics() {
  const [metrics, setMetrics] = useState<Metrics>(INITIAL_METRICS);
  const [history, setHistory] = useState<Metrics[]>([]);
  const [wsMetrics, loading] = useWebSocketMessages<Metrics>('metrics', INITIAL_METRICS);

  // Fetch initial metrics
  useEffect(() => {
    getMetrics()
      .then(setMetrics)
      .catch(console.error);
  }, []);

  // Update from WebSocket
  useEffect(() => {
    if (!loading && wsMetrics.timestamp > metrics.timestamp) {
      setMetrics(wsMetrics);
      setHistory((prev) => [...prev.slice(-99), wsMetrics]);
    }
  }, [wsMetrics, loading, metrics.timestamp]);

  return { metrics, history, loading };
}
