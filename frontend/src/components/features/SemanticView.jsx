import { useState, useCallback, useRef, useEffect } from 'react';
import { postAsk } from '../../api/client';
import useAsync from '../../hooks/useAsync';
import Input from '../ui/Input';
import Button from '../ui/Button';
import Tabs from '../ui/Tabs';
import EmptyState from '../ui/EmptyState';
import styles from './SemanticView.module.css';

const TOP_K_OPTIONS = [
  { value: '3', label: '3' },
  { value: '5', label: '5' },
  { value: '10', label: '10' },
];

export default function SemanticView() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState('5');
  const inputRef = useRef(null);
  const { data, loading, error, elapsed, execute } = useAsync(postAsk);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = useCallback(() => {
    const q = query.trim();
    if (!q) return;
    execute(q, parseInt(topK, 10));
  }, [query, topK, execute]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') handleSubmit();
  }, [handleSubmit]);

  return (
    <div className={styles.view}>
      <div className={styles.titleRow}>
        <h1 className={styles.title}>Semantic Search</h1>
        {elapsed && data && (
          <span className={styles.timing}>
            {data.contexts?.length || 0} results &middot; {elapsed}s
          </span>
        )}
      </div>

      <div className={styles.toolbar}>
        <Input
          ref={inputRef}
          placeholder="Search emails by meaning..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Search query"
        />
        <Tabs options={TOP_K_OPTIONS} value={topK} onChange={setTopK} />
        <Button onClick={handleSubmit} loading={loading} size="lg">
          Search
        </Button>
      </div>

      <section className={styles.results} aria-live="polite">
        {loading && (
          <EmptyState loading message="Searching your emails..." />
        )}

        {error && <EmptyState error={error} />}

        {data && !loading && (
          <>
            {data.contexts?.length > 0 ? (
              <ol className={styles.resultList}>
                {data.contexts.map((ctx, i) => (
                  <li key={i} className={styles.resultItem}>
                    <span className={styles.resultNum}>{i + 1}</span>
                    <p className={styles.resultText}>{ctx}</p>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState message="No matching emails found. Try different terms." />
            )}
          </>
        )}
      </section>
    </div>
  );
}
