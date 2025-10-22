import { useEffect, useState, useCallback } from 'react';
import { getWebSocketService } from '@/services/websocket';
import { WebSocketMessage } from '@/types/metrics';

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [lastHeartbeat, setLastHeartbeat] = useState(Date.now());

  useEffect(() => {
    const ws = getWebSocketService();

    ws.connect();

    const unsubscribeConnection = ws.onConnectionChange((isConnected) => {
      setConnected(isConnected);
    });

    const unsubscribeMessage = ws.onMessage((message) => {
      if (message.type === 'health') {
        setLastHeartbeat(Date.now());
      }
    });

    return () => {
      unsubscribeConnection();
      unsubscribeMessage();
      ws.disconnect();
    };
  }, []);

  const send = useCallback((message: WebSocketMessage) => {
    const ws = getWebSocketService();
    ws.send(message);
  }, []);

  return { connected, lastHeartbeat, send };
}

export function useWebSocketMessages<T>(
  messageType: string,
  initialValue: T
): [T, boolean] {
  const [data, setData] = useState<T>(initialValue);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ws = getWebSocketService();

    const unsubscribe = ws.onMessage((message) => {
      if (message.type === messageType) {
        setData(message.data as T);
        setLoading(false);
      }
    });

    return unsubscribe;
  }, [messageType]);

  return [data, loading];
}
