import { useCallback, useEffect, useState } from 'react';
import type { DashboardData } from '../types/api';
import { getDashboardData, ApiError } from '../api/client';
import { useSSE } from './useSSE';

interface UseDashboardDataResult {
  data: DashboardData | null;
  connected: boolean;
  authRequired: boolean;
  loading: boolean;
}

export function useDashboardData(): UseDashboardDataResult {
  const [data, setData] = useState<DashboardData | null>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sseEnabled, setSseEnabled] = useState(false);

  // Initial fetch
  useEffect(() => {
    getDashboardData()
      .then((d) => {
        setData(d);
        setAuthRequired(false);
        setSseEnabled(true);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          setAuthRequired(true);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSSEMessage = useCallback((d: DashboardData) => {
    setData(d);
  }, []);

  const { connected } = useSSE('/dashboard/stream', handleSSEMessage, sseEnabled);

  return { data, connected, authRequired, loading };
}
