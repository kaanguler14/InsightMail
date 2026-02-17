import styles from './EmptyState.module.css';
import Spinner from './Spinner';

export default function EmptyState({ loading, error, message }) {
  if (error) {
    return (
      <div className={styles.error} role="alert">
        {error}
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.wrapper}>
        <Spinner size={24} />
        <p className={styles.text}>{message || 'Processing...'}</p>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <p className={styles.text}>{message || 'No results yet.'}</p>
    </div>
  );
}
