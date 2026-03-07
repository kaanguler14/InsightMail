import { useState, useCallback, useRef, useEffect } from 'react';
import { postSearch } from '../../api/client';
import useAsync from '../../hooks/useAsync';
import Input from '../ui/Input';
import Button from '../ui/Button';
import Tabs from '../ui/Tabs';
import EmptyState from '../ui/EmptyState';
import styles from './SearchView.module.css';

const TOP_K_OPTIONS = [
  { value: '3', label: '3' },
  { value: '5', label: '5' },
  { value: '10', label: '10' },
];

export default function SearchView() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState('5');
  const inputRef = useRef(null);
  const { data, loading, error, elapsed, execute } = useAsync(postSearch);

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
      <div id="ask" className={styles.titleRow}>
        <h1 className={styles.title}>Q&A</h1>
        {elapsed && data && (
          <span className={styles.timing}>{elapsed}s</span>
        )}
      </div>
      <p className={styles.docSubtitle}>Ask natural language questions across your mailbox and get grounded answers with sources.</p>

      <div className={styles.toolbar}>
        <Input
          ref={inputRef}
          placeholder="Ask about your emails..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Question"
        />
        <div className={styles.limitWrap}>
          <Tabs options={TOP_K_OPTIONS} value={topK} onChange={setTopK} />
          <span className={styles.infoTrigger} aria-label="What are these numbers?">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="7" cy="7" r="6" />
              <path d="M7 6.5v0M7 9.5v-2" />
            </svg>
            <span className={styles.infoTooltip} role="tooltip">
              Number of email chunks to retrieve and use as context for the AI answer (top N most relevant).
            </span>
          </span>
        </div>
        <Button onClick={handleSubmit} loading={loading} size="lg">
          Ask
        </Button>
      </div>

      <section id="answer" className={styles.results} aria-live="polite">
        {loading && (
          <EmptyState loading message="Searching and generating answer..." />
        )}

        {error && <EmptyState error={error} />}

        {data && !loading && (
          <>
            {!data.answer && (!data.contexts || data.contexts.length === 0) && (
              <EmptyState message="No results found. Try a different question." />
            )}

            {(data.answer || data.contexts?.length > 0) && (
              <div className={styles.columns}>
                <div className={styles.primary}>
                  {data.answer && (
                    <article className={styles.answerCard}>
                      <div className={styles.cardLabel}>
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="7" cy="7" r="5.5" />
                          <path d="M5.5 5.5a1.5 1.5 0 013 0c0 1-1.5 1-1.5 2.5" />
                          <circle cx="7" cy="10" r="0.5" fill="currentColor" />
                        </svg>
                        Answer
                      </div>
                      <p className={styles.answerText}>{data.answer}</p>
                    </article>
                  )}
                </div>

                {data.contexts?.length > 0 && (
                  <aside id="sources" className={styles.context}>
                    <div className={styles.contextHead}>
                      <span className={styles.contextTitle}>Sources</span>
                      <span className={styles.contextCount}>{data.contexts.length}</span>
                    </div>
                    <ol className={styles.sourceList}>
                      {data.contexts.map((ctx, i) => (
                        <li key={i} className={styles.sourceItem}>
                          <span className={styles.sourceNum}>{i + 1}</span>
                          <p className={styles.sourceText}>{ctx}</p>
                        </li>
                      ))}
                    </ol>
                  </aside>
                )}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
