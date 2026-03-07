import { useState, useCallback, useRef, useEffect } from 'react';
import { postReplySuggest } from '../../api/client';
import useAsync from '../../hooks/useAsync';
import Input from '../ui/Input';
import Button from '../ui/Button';
import Tabs from '../ui/Tabs';
import EmptyState from '../ui/EmptyState';
import ReplyCard from './ReplyCard';
import styles from './ReplyView.module.css';

const TONE_OPTIONS = [
  { value: 'formal', label: 'Formal' },
  { value: 'friendly', label: 'Friendly' },
  { value: 'brief', label: 'Brief' },
];

export default function ReplyView({ contactEmail, onContactChange }) {
  const [tone, setTone] = useState('friendly');
  const inputRef = useRef(null);
  const { data, loading, error, elapsed, execute } = useAsync(postReplySuggest);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = useCallback(() => {
    const email = contactEmail.trim();
    if (!email) return;
    execute(email, tone);
  }, [contactEmail, tone, execute]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') handleSubmit();
  }, [handleSubmit]);

  const original = data?.original_email;

  return (
    <div className={styles.view}>
      <p className={styles.docLabel}>Features</p>
      <div id="overview" className={styles.titleRow}>
        <h1 className={styles.title}>Reply Suggestions</h1>
        {elapsed && data && (
          <span className={styles.timing}>{elapsed}s</span>
        )}
      </div>
      <p className={styles.docSubtitle}>Generate context-aware reply drafts to a contact&apos;s latest email.</p>

      <div id="suggestions" className={styles.toolbar}>
        <Input
          ref={inputRef}
          placeholder="Enter contact email..."
          value={contactEmail}
          onChange={(e) => onContactChange(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Contact email"
        />
        <Tabs options={TONE_OPTIONS} value={tone} onChange={setTone} />
        <Button onClick={handleSubmit} loading={loading} size="lg">
          Generate
        </Button>
      </div>

      <section className={styles.results} aria-live="polite">
        {loading && (
          <EmptyState
            loading
            message="Generating replies... This may take 20-40 seconds."
          />
        )}

        {error && <EmptyState error={error} />}

        {data && !loading && (
          <>
            {!original?.subject && (!data.suggestions || data.suggestions.length === 0) && (
              <EmptyState message="Could not generate reply suggestions." />
            )}

            {(original?.subject || data.suggestions?.length > 0) && (
              <div className={styles.columns}>
                {original && original.subject && (
                  <aside className={styles.context}>
                    <div className={styles.contextLabel}>
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2 4l5 3.5L12 4" />
                        <rect x="1.5" y="2.5" width="11" height="9" rx="2" />
                      </svg>
                      Replying to
                    </div>
                    <h3 className={styles.origSubject}>{original.subject}</h3>
                    <p className={styles.origMeta}>
                      {original.from_addr}
                      {original.date && <span> &middot; {original.date}</span>}
                    </p>
                    {original.body_preview && (
                      <p className={styles.origBody}>{original.body_preview}</p>
                    )}
                  </aside>
                )}

                <div className={styles.primary}>
                  {data.suggestions?.length > 0 ? (
                    <div className={styles.suggestions}>
                      {data.suggestions.map((s, i) => (
                        <ReplyCard
                          key={i}
                          index={i}
                          subject={s.subject}
                          body={s.body}
                        />
                      ))}
                    </div>
                  ) : (
                    <EmptyState message="Could not generate reply suggestions." />
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
