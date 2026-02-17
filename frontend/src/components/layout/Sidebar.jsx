import { useState, useEffect } from 'react';
import { fetchRecentContacts, fetchHealth } from '../../api/client';
import ContactChip from '../features/ContactChip';
import styles from './Sidebar.module.css';

const NAV_ITEMS = [
  {
    key: 'summary',
    label: 'Summary',
    shortcut: '1',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="2" width="11" height="11" rx="2.5" />
        <path d="M5 5h5M5 7.5h3.5M5 10h4" />
      </svg>
    ),
  },
  {
    key: 'reply',
    label: 'Reply',
    shortcut: '2',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5.5 3L2 6.5l3.5 3.5" />
        <path d="M2 6.5h7a3.5 3.5 0 013.5 3.5v1" />
      </svg>
    ),
  },
  {
    key: 'search',
    label: 'Q&A',
    shortcut: '3',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6.5" cy="6.5" r="4" />
        <path d="M9.5 9.5L13 13" />
      </svg>
    ),
  },
  {
    key: 'semantic',
    label: 'Search',
    shortcut: '4',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 4h11M4 7.5h7M6 11h3" />
      </svg>
    ),
  },
];

export default function Sidebar({ activeView, onNavigate, onSelectContact }) {
  const [contacts, setContacts] = useState([]);
  const [contactsLoaded, setContactsLoaded] = useState(false);
  const [contactsError, setContactsError] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchRecentContacts()
      .then((data) => {
        if (!cancelled) {
          setContacts(data.contacts || []);
          setContactsLoaded(true);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setContactsError(err.message);
          setContactsLoaded(true);
        }
      });
    fetchHealth()
      .then(() => { if (!cancelled) setHealth('connected'); })
      .catch(() => { if (!cancelled) setHealth('offline'); });
    return () => { cancelled = true; };
  }, []);

  return (
    <nav className={styles.sidebar} aria-label="Main navigation">
      <div className={styles.brand}>
        <div className={styles.logoMark}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 4.5L8 8.5L14 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <rect x="1.5" y="3" width="13" height="10" rx="2" stroke="currentColor" strokeWidth="1.5"/>
          </svg>
        </div>
        <span className={styles.logoText}>InsightMail</span>
      </div>

      <ul className={styles.nav} role="list">
        {NAV_ITEMS.map((item) => (
          <li key={item.key}>
            <button
              className={`${styles.navBtn} ${activeView === item.key ? styles.navActive : ''}`}
              onClick={() => onNavigate(item.key)}
              aria-current={activeView === item.key ? 'page' : undefined}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span className={styles.navLabel}>{item.label}</span>
              <kbd className={styles.navKbd}>{item.shortcut}</kbd>
            </button>
          </li>
        ))}
      </ul>

      <div className={styles.separator} />

      <section className={styles.contacts}>
        <div className={styles.sectionHead}>
          <span className={styles.sectionTitle}>Recent</span>
          {contactsLoaded && contacts.length > 0 && (
            <span className={styles.sectionCount}>{contacts.length}</span>
          )}
        </div>
        {!contactsLoaded && (
          <p className={styles.hint}>Loading contacts...</p>
        )}
        {contactsError && (
          <p className={styles.hint}>{contactsError}</p>
        )}
        {contactsLoaded && !contactsError && contacts.length === 0 && (
          <p className={styles.hint}>No recent contacts</p>
        )}
        <div className={styles.contactsList}>
          {contacts.map((c) => (
            <ContactChip
              key={c.email}
              email={c.email}
              name={c.name}
              onClick={() => onSelectContact(c.email)}
            />
          ))}
        </div>
      </section>

      <div className={styles.footer}>
        <div className={styles.status}>
          <span
            className={`${styles.dot} ${health === 'connected' ? styles.dotOnline : styles.dotOffline}`}
            aria-hidden="true"
          />
          <span className={styles.statusLabel}>
            {health === 'connected' ? 'API connected' : health === 'offline' ? 'API offline' : 'Connecting...'}
          </span>
        </div>
      </div>
    </nav>
  );
}
