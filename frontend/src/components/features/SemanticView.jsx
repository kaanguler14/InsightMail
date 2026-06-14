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
      <p className={styles.docLabel}>Features</p>
      <div id="search" className={styles.titleRow}>
        <h1 className={styles.title}>Semantic Search</h1>
        {elapsed && data && (
          <span className={styles.timing}>
            {data.contexts?.length || 0} results &middot; {elapsed}s
          </span>
        )}
      </div>
      <p className={styles.docSubtitle}>Find emails by meaning, not just keywords. Returns the most relevant chunks.</p>

      <div className={styles.toolbar}>
        <Input
          ref={inputRef}
          placeholder="Search emails by meaning..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Search query"
        />
        <div className={styles.limitWrap}>
          <Tabs options={TOP_K_OPTIONS} value={topK} onChange={setTopK} />
          <span className={styles.infoTrigger} aria-label="What are these numbers?">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="7" cy="7" r="6" />
              <path d="M7 6.5v0M7 9.5v-2" />
            </svg>
            <span className={styles.infoTooltip} role="tooltip">
              Number of most relevant email chunks to return (no AI answer, just raw results).
            </span>
          </span>
        </div>
        <Button onClick={handleSubmit} loading={loading} size="lg">
          Search
        </Button>
      </div>

      <section id="results" className={styles.results} aria-live="polite">
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
