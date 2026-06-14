import styles from './Shell.module.css';

export default function Shell({ isHorizontal, sidebar, children, topBar }) {
  if (isHorizontal) {
    return (
      <div className={styles.shellHorizontal}>
        {topBar && <div className={styles.topBarSlot}>{topBar}</div>}
        {sidebar && <aside className={styles.sidebarHorizontal}>{sidebar}</aside>}
        <div className={styles.content}>{children}</div>
      </div>
    );
  }
  return (
    <div className={styles.shellVertical}>
      {topBar && <div className={styles.topBarSlot}>{topBar}</div>}
      <div className={styles.docRow}>
        {sidebar && <aside className={styles.sidebarVertical}>{sidebar}</aside>}
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
