import { useCallback, useRef, useEffect, useState } from 'react';
import { postSummarize } from '../../api/client';
import useAsync from '../../hooks/useAsync';
import Input from '../ui/Input';
import Button from '../ui/Button';
import Tabs from '../ui/Tabs';
import EmptyState from '../ui/EmptyState';
import Badge from '../ui/Badge';
import styles from './SummaryView.module.css';

const LIMIT_OPTIONS = [
  { value: '3', label: '3' },
  { value: '5', label: '5' },
  { value: '10', label: '10' },
  { value: '15', label: '15' },
];

export default function SummaryView({ contactEmail, onContactChange }) {
  const inputRef = useRef(null);
  const [limit, setLimit] = useState('5');
  const { data, loading, error, elapsed, execute } = useAsync(postSummarize);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = useCallback(() => {
    const email = contactEmail.trim();
    if (!email) return;
    execute(email, parseInt(limit, 10));
  }, [contactEmail, limit, execute]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') handleSubmit();
  }, [handleSubmit]);

  return (
    <div className={styles.view}>
      <div className={styles.titleRow}>
        <h1 className={styles.title}>Conversation Summary</h1>
        {elapsed && data && (
          <span className={styles.timing}>{elapsed}s</span>
        )}
      </div>

      <div className={styles.toolbar}>
        <Input
          ref={inputRef}
          placeholder="Enter contact email..."
          value={contactEmail}
          onChange={(e) => onContactChange(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Contact email"
        />
        <Tabs
          options={LIMIT_OPTIONS}
          value={limit}
          onChange={setLimit}
        />
        <Button onClick={handleSubmit} loading={loading} size="lg">
          Summarize
        </Button>
      </div>

      <section className={styles.results} aria-live="polite">
        {loading && (
          <EmptyState
            loading
            message="Analyzing conversation... This may take 15-30 seconds."
          />
        )}

        {error && <EmptyState error={error} />}

        {data && !loading && (
          <>
            {!data.summary && (!data.emails || data.emails.length === 0) && (
              <EmptyState message="No emails found with this contact." />
            )}

            {(data.summary || (data.emails && data.emails.length > 0)) && (
              <div className={styles.columns}>
                <div className={styles.primary}>
                  {data.summary && (
                    <article className={styles.summaryCard}>
                      <div className={styles.cardLabel}>
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="2" y="2" width="10" height="10" rx="2" />
                          <path d="M4.5 5h5M4.5 7h3.5M4.5 9h4" />
                        </svg>
                        Analysis
                      </div>
                      <p className={styles.summaryText}>{data.summary}</p>
                    </article>
                  )}
                </div>

                {data.emails && data.emails.length > 0 && (
                  <aside className={styles.context}>
                    <div className={styles.contextHead}>
                      <span className={styles.contextTitle}>Thread</span>
                      <span className={styles.contextCount}>{data.emails.length}</span>
                    </div>
                    <ol className={styles.emailList}>
                      {data.emails.map((em, i) => {
                        const isSent = em.direction === 'giden';
                        return (
                          <li key={`${em.date}-${i}`} className={styles.emailItem}>
                            <div className={styles.emailHead}>
                              <Badge variant={isSent ? 'sent' : 'received'}>
                                {isSent ? 'Sent' : 'In'}
                              </Badge>
                              <time className={styles.emailDate}>{em.date}</time>
                            </div>
                            <p className={styles.emailSubject}>{em.subject || '(No subject)'}</p>
                            {em.body_preview && (
                              <p className={styles.emailBody}>{em.body_preview}</p>
                            )}
                          </li>
                        );
                      })}
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
