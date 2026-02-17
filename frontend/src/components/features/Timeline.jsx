import Badge from '../ui/Badge';
import styles from './Timeline.module.css';

export default function Timeline({ emails }) {
  if (!emails || emails.length === 0) return null;

  return (
    <section className={styles.timeline}>
      <h3 className={styles.heading}>
        Email History
        <span className={styles.count}>{emails.length}</span>
      </h3>
      <ol className={styles.list} role="list">
        {emails.map((em, i) => {
          const isSent = em.direction === 'giden';
          return (
            <li
              key={`${em.date}-${i}`}
              className={`${styles.item} ${isSent ? styles.sent : styles.received}`}
            >
              <span className={styles.dot} aria-hidden="true" />
              <div className={styles.content}>
                <div className={styles.meta}>
                  <Badge variant={isSent ? 'sent' : 'received'}>
                    {isSent ? 'Sent' : 'Received'}
                  </Badge>
                  <time className={styles.date}>{em.date}</time>
                </div>
                <p className={styles.subject}>{em.subject || '(No subject)'}</p>
                {em.body_preview && (
                  <p className={styles.body}>{em.body_preview}</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
