import { useEffect, useState } from "react";

// Minimal data-fetching hook: runs `fn`, tracks loading/error/data.
// Safe for server-side rendering (effect does not run) and tests.
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({
    loading: true,
    data: null,
    error: null,
  });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, data: null, error: null });
    Promise.resolve()
      .then(fn)
      .then((data) => {
        if (!cancelled) setState({ loading: false, data, error: null });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            loading: false,
            data: null,
            error: String((err && err.message) || err),
          });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const refresh = () => setTick((t) => t + 1);

  return { ...state, refresh };
}
