import styles from './TopBar.module.css';

export default function TopBar({ onNavigate }) {
  return (
    <header className={styles.topBar} role="banner">
      <button
        type="button"
        className={styles.logo}
        onClick={() => onNavigate('home')}
        aria-label="InsightMail home"
      >
        <span className={styles.logoMark}>IM</span>
        <span className={styles.logoText}>InsightMail</span>
      </button>
      <div className={styles.right}>
        <span className={styles.statusDot} aria-hidden />
        <span className={styles.statusText}>API</span>
      </div>
    </header>
  );
}
