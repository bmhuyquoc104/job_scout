import { useEffect, useEffectEvent, useState, type DependencyList } from "react";
import { ApiError } from "./client";

interface Settled<T> {
  key: string;
  data: T | null;
  error: string;
}

/**
 * Runs `load` whenever `deps` change (deps must be JSON-serialisable) and ignores results
 * from superseded requests. While a new request is in flight the previous data stays visible.
 */
export function useApi<T>(load: () => Promise<T>, deps: DependencyList, fallbackError: string) {
  const key = JSON.stringify(deps);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const run = useEffectEvent(load);

  useEffect(() => {
    let active = true;
    run()
      .then((data) => active && setSettled({ key, data, error: "" }))
      .catch((reason: unknown) => {
        const error = reason instanceof ApiError ? reason.message : fallbackError;
        if (active) setSettled({ key, data: null, error });
      });
    return () => {
      active = false;
    };
  }, [key, fallbackError]);

  const loading = settled?.key !== key;
  return { data: settled?.data ?? null, error: loading ? "" : (settled?.error ?? ""), loading };
}
