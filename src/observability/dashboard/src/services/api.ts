import { Metrics, SystemHealth } from '@/types/metrics';
import { Trade, OrderBook, Position } from '@/types/trades';

const API_BASE = '/api';

async function fetchJSON<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  return response.json();
}

export async function getMetrics(): Promise<Metrics> {
  return fetchJSON<Metrics>('/metrics');
}

export async function getSystemHealth(): Promise<SystemHealth> {
  return fetchJSON<SystemHealth>('/health');
}

export async function getTrades(limit = 100): Promise<Trade[]> {
  return fetchJSON<Trade[]>(`/trades?limit=${limit}`);
}

export async function getOrderBook(symbol: string): Promise<OrderBook> {
  return fetchJSON<OrderBook>(`/orderbook/${symbol}`);
}

export async function getPositions(): Promise<Position[]> {
  return fetchJSON<Position[]>('/positions');
}

export async function getHistoricalMetrics(
  period: '1h' | '24h' | '7d' | '30d'
): Promise<Metrics[]> {
  return fetchJSON<Metrics[]>(`/metrics/history?period=${period}`);
}
