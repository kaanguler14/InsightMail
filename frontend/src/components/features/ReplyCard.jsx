import CopyButton from '../ui/CopyButton';
import styles from './ReplyCard.module.css';

export default function ReplyCard({ index, subject, body }) {
  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <span className={styles.label}>Suggestion {index + 1}</span>
        <CopyButton text={`Subject: ${subject}\n\n${body}`} />
      </header>
      {subject && <p className={styles.subject}>{subject}</p>}
      <p className={styles.body}>{body}</p>
    </article>
  );
}
