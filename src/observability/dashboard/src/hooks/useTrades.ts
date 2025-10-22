import { useState, useEffect } from 'react';
import { Trade, OrderBook, Position } from '@/types/trades';
import { useWebSocketMessages } from './useWebSocket';
import { getTrades, getOrderBook, getPositions } from '@/services/api';

export function useTrades(limit = 100) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [wsTrade, loading] = useWebSocketMessages<Trade>('trade', {} as Trade);

  useEffect(() => {
    getTrades(limit)
      .then(setTrades)
      .catch(console.error);
  }, [limit]);

  useEffect(() => {
    if (!loading && wsTrade.id) {
      setTrades((prev) => [wsTrade, ...prev.slice(0, limit - 1)]);
    }
  }, [wsTrade, loading, limit]);

  return { trades, loading };
}

export function useOrderBook(symbol: string) {
  const [orderBook, setOrderBook] = useState<OrderBook | null>(null);
  const [wsOrderBook, loading] = useWebSocketMessages<OrderBook>(
    'orderbook',
    {} as OrderBook
  );

  useEffect(() => {
    if (symbol) {
      getOrderBook(symbol)
        .then(setOrderBook)
        .catch(console.error);
    }
  }, [symbol]);

  useEffect(() => {
    if (!loading && wsOrderBook.symbol === symbol) {
      setOrderBook(wsOrderBook);
    }
  }, [wsOrderBook, loading, symbol]);

  return { orderBook, loading };
}

export function usePositions() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPositions = () => {
      getPositions()
        .then((data) => {
          setPositions(data);
          setLoading(false);
        })
        .catch(console.error);
    };

    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);

    return () => clearInterval(interval);
  }, []);

  return { positions, loading };
}
