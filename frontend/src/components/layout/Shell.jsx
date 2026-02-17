import styles from './Shell.module.css';

export default function Shell({ sidebar, children }) {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>{sidebar}</aside>
      <div className={styles.content}>{children}</div>
    </div>
  );
}
