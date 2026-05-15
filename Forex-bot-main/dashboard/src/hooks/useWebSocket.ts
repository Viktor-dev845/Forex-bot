import { useEffect, useRef } from 'react';
import { useTradingStore } from '../store/tradingStore';

export const useWebSocket = () => {
  const { setBotState, updateTicks, setConnected } = useTradingStore();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      // Connect to FastAPI backend
      const ws = new WebSocket('ws://localhost:8000/ws/live');
      
      ws.onopen = () => {
        setConnected(true);
        console.log('Connected to QuantAI backend');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'state_update') {
            setBotState(message.data);
          } else if (message.type === 'tick_update') {
            updateTicks(message.data);
          }
        } catch (err) {
          console.error('Failed to parse WS message', err);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        console.log('WS disconnected, reconnecting in 2s...');
        // Auto reconnect
        reconnectTimer = setTimeout(connect, 2000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        ws.close();
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [setBotState, updateTicks, setConnected]);

  return wsRef.current;
};
