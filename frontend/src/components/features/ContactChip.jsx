import styles from './ContactChip.module.css';

export default function ContactChip({ email, name, onClick }) {
  const displayName = name && name !== email
    ? name.replace(/<[^>]+>/g, '').trim()
    : email;
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <button className={styles.chip} onClick={onClick} title={email}>
      <span className={styles.avatar} aria-hidden="true">{initial}</span>
      <span className={styles.info}>
        <span className={styles.name}>{displayName}</span>
        {displayName !== email && (
          <span className={styles.email}>{email}</span>
        )}
      </span>
    </button>
  );
}
