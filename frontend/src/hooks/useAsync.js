import { useState, useCallback, useRef } from 'react';

export default function useAsync(asyncFn) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [elapsed, setElapsed] = useState(null);
  const counterRef = useRef(0);

  const execute = useCallback(async (...args) => {
    const id = ++counterRef.current;
    setLoading(true);
    setError(null);
    setData(null);
    setElapsed(null);

    const start = performance.now();
    try {
      const result = await asyncFn(...args);
      if (counterRef.current === id) {
        setData(result);
        setElapsed(((performance.now() - start) / 1000).toFixed(1));
      }
    } catch (err) {
      if (counterRef.current === id) {
        setError(err.message || 'An error occurred');
      }
    } finally {
      if (counterRef.current === id) {
        setLoading(false);
      }
    }
  }, [asyncFn]);

  const reset = useCallback(() => {
    counterRef.current++;
    setData(null);
    setLoading(false);
    setError(null);
    setElapsed(null);
  }, []);

  return { data, loading, error, elapsed, execute, reset };
}
