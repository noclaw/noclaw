import { useEffect, useRef, useState } from 'react';
import type { DashboardData } from '../types/api';

export function useSSE(
  url: string,
  onMessage: (data: DashboardData) => void,
  enabled = true
): { connected: boolean } {
  const [connected, setConnected] = useState(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!enabled) return;

    const source = new EventSource(url);

    source.onopen = () => setConnected(true);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as DashboardData;
        onMessageRef.current(data);
      } catch {
        // ignore parse errors
      }
    };

    source.onerror = () => setConnected(false);

    return () => {
      source.close();
      setConnected(false);
    };
  }, [url, enabled]);

  return { connected };
}
