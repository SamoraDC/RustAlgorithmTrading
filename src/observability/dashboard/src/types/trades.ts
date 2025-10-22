export type OrderSide = 'buy' | 'sell';
export type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit';
export type OrderStatus = 'pending' | 'open' | 'filled' | 'cancelled' | 'rejected';

export interface Trade {
  id: string;
  timestamp: number;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  price: number;
  quantity: number;
  filled_quantity: number;
  status: OrderStatus;
  pnl?: number;
  commission: number;
  slippage?: number;
  execution_time_ms?: number;
}

export interface OrderBookEntry {
  price: number;
  quantity: number;
  total: number;
}

export interface OrderBook {
  symbol: string;
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
  timestamp: number;
  spread: number;
  mid_price: number;
}

export interface Position {
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
  duration_seconds: number;
}

export interface LogEntry {
  timestamp: number;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  component?: string;
  details?: Record<string, unknown>;
}
