export interface Metrics {
  pnl: number;
  pnl_percent: number;
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;
  avg_loss: number;
  largest_win: number;
  largest_loss: number;
  timestamp: number;
}

export interface SystemHealth {
  latency_ms: number;
  websocket_connected: boolean;
  last_heartbeat: number;
  memory_usage_mb: number;
  cpu_usage_percent: number;
  active_connections: number;
  uptime_seconds: number;
}

export interface RiskMetrics {
  position_size: number;
  leverage: number;
  margin_used: number;
  margin_available: number;
  liquidation_price?: number;
  risk_score: number;
}

export interface ExecutionStep {
  stage: 'data' | 'signal' | 'risk' | 'execution' | 'confirmation';
  status: 'pending' | 'processing' | 'success' | 'error';
  timestamp: number;
  duration_ms?: number;
  details?: string;
  error?: string;
}

export interface Decision {
  id: string;
  timestamp: number;
  type: 'buy' | 'sell' | 'hold';
  symbol: string;
  price: number;
  quantity: number;
  confidence: number;
  reasoning: string;
  factors: DecisionFactor[];
}

export interface DecisionFactor {
  name: string;
  value: number;
  weight: number;
  impact: 'positive' | 'negative' | 'neutral';
}

export interface WebSocketMessage {
  type: 'metrics' | 'trade' | 'orderbook' | 'execution' | 'decision' | 'log' | 'health';
  data: unknown;
  timestamp: number;
}
