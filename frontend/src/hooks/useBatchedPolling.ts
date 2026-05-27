import { useState, useEffect, useCallback, useRef } from "react";
import { useFleetRefresh } from "./FleetRefreshContext";

/**
 * Batched polling hook. Calls `fetchFn` on mount and every time 
 * the global 15-second `tick` from FleetRefreshContext fires.
 */
export function useBatchedPolling<T>(fetchFn: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { tick, secondsRemaining } = useFleetRefresh();
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const result = await fetchFn();
      if (mountedRef.current) {
        setData(result);
        setError(null);
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetchFn]);

  // Initial fetch on mount, and then fetch whenever 'tick' changes
  useEffect(() => {
    mountedRef.current = true;
    refresh();
    
    return () => {
      mountedRef.current = false;
    };
  }, [tick, refresh]);

  return { data, loading, error, refresh, secondsRemaining };
}
