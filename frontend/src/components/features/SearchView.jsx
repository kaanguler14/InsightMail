import { useState, useCallback, useRef, useEffect } from 'react';
import { postSearchStream } from '../../api/client';
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
  const [answer, setAnswer] = useState('');
  const [contexts, setContexts] = useState([]);
  const [loading, setLoading] = useState(false);   // istek gönderildi, ilk veri bekleniyor
  const [streaming, setStreaming] = useState(false); // token akışı sürüyor
  const [error, setError] = useState(null);
  const [elapsed, setElapsed] = useState(null);
  const [started, setStarted] = useState(false);
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
    return () => abortRef.current?.abort();
  }, []);

  const handleSubmit = useCallback(() => {
    const q = query.trim();
    if (!q) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setAnswer('');
    setContexts([]);
    setError(null);
    setElapsed(null);
    setStarted(true);
    setLoading(true);
    setStreaming(false);
    const start = performance.now();

    postSearchStream(q, parseInt(topK, 10), {
      signal: controller.signal,
      onSources: (d) => {
        setContexts(d.contexts || []);
        setLoading(false);
        setStreaming(true);
      },
      onToken: (t) => setAnswer((prev) => prev + t),
      onDone: (d) => {
        if (d.answer != null) setAnswer(d.answer);
        if (d.contexts) setContexts(d.contexts);
        setStreaming(false);
        setLoading(false);
        setElapsed(((performance.now() - start) / 1000).toFixed(1));
      },
      onError: (err) => {
        setError(err.message || 'An error occurred');
        setLoading(false);
        setStreaming(false);
      },
    });
  }, [query, topK]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') handleSubmit();
  }, [handleSubmit]);

  const hasContent = Boolean(answer) || contexts.length > 0;

  return (
    <div className={styles.view}>
      <p className={styles.docLabel}>Features</p>
      <div id="ask" className={styles.titleRow}>
        <h1 className={styles.title}>Q&A</h1>
        {elapsed && !streaming && (
          <span className={styles.timing}>{elapsed}s</span>
        )}
      </div>
      <p className={styles.docSubtitle}>Ask natural language questions across your mailbox and get grounded answers with sources.</p>

      <div className={styles.toolbar}>
        <Input
          ref={inputRef}
          placeholder="Ask a full question, e.g. “What did Temu send me?”"
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
        <Button onClick={handleSubmit} loading={loading || streaming} size="lg">
          Ask
        </Button>
      </div>

      <section id="answer" className={styles.results} aria-live="polite">
        {loading && (
          <EmptyState loading message="Searching and generating answer..." />
        )}

        {error && <EmptyState error={error} />}

        {started && !loading && !error && (
          <>
            {!hasContent && !streaming && (
              <EmptyState message="No results found. Try a different question." />
            )}

            {hasContent && (
              <div className={styles.columns}>
                <div className={styles.primary}>
                  {(answer || streaming) && (
                    <article className={styles.answerCard}>
                      <div className={styles.cardLabel}>
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="7" cy="7" r="5.5" />
                          <path d="M5.5 5.5a1.5 1.5 0 013 0c0 1-1.5 1-1.5 2.5" />
                          <circle cx="7" cy="10" r="0.5" fill="currentColor" />
                        </svg>
                        Answer
                      </div>
                      <p className={styles.answerText}>
                        {answer}
                        {streaming && <span className={styles.cursor} aria-hidden="true">▋</span>}
                      </p>
                    </article>
                  )}
                </div>

                {contexts.length > 0 && (
                  <aside id="sources" className={styles.context}>
                    <div className={styles.contextHead}>
                      <span className={styles.contextTitle}>Sources</span>
                      <span className={styles.contextCount}>{contexts.length}</span>
                    </div>
                    <ol className={styles.sourceList}>
                      {contexts.map((ctx, i) => (
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
