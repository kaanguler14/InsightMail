import { useState, useEffect, useCallback } from 'react';
import { fetchHealth, fetchRecentContacts } from '../../api/client';
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

export default function Sidebar({ activeView, isHorizontal, onNavigate, onSelectContact }) {
  const [health, setHealth] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [isLoadingContacts, setIsLoadingContacts] = useState(false);

  const refreshContacts = useCallback(() => {
    setIsLoadingContacts(true);
    fetchRecentContacts()
      .then((data) => {
        if (data?.contacts) setContacts(data.contacts);
      })
      .catch(console.error)
      .finally(() => setIsLoadingContacts(false));
  }, []);

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then(() => { if (!cancelled) setHealth('connected'); })
      .catch(() => { if (!cancelled) setHealth('offline'); });

    refreshContacts();

    const interval = setInterval(() => {
      if (cancelled) return;
      fetchRecentContacts()
        .then((data) => {
          if (!cancelled && data?.contacts) setContacts(data.contacts);
        })
        .catch(() => {});
    }, 60_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [refreshContacts]);

  return (
    <nav className={`${styles.sidebar} ${isHorizontal ? styles.horizontal : styles.vertical}`} aria-label="Main navigation">
      <button
        type="button"
        className={styles.brand}
        onClick={() => onNavigate('home')}
        aria-label="Go to InsightMail overview"
      >
        <div className={styles.logoMark}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 4.5L8 8.5L14 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <rect x="1.5" y="3" width="13" height="10" rx="2" stroke="currentColor" strokeWidth="1.5"/>
          </svg>
        </div>
        <span className={styles.logoText}>InsightMail</span>
      </button>

      {!isHorizontal && <h2 className={styles.navSectionTitle}>FEATURES</h2>}
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

      {/* Horizontal Contacts List (facepile) */}
      {isHorizontal && (
        <div className={styles.contactsAreaHorizontal}>
          <div className={styles.separator} />
          <span className={styles.contactsLabel}>Recent</span>
          <div className={styles.contactsListHorizontal} role="list">
            {isLoadingContacts && <span className={styles.hint}>Loading...</span>}
            {!isLoadingContacts && contacts.slice(0, 5).map(contact => (
              <button
                key={contact.email}
                className={styles.contactAvatar}
                title={`${contact.name || contact.email} (${contact.email})`}
                onClick={() => onSelectContact(contact.email)}
              >
                {(contact.name || contact.email).charAt(0).toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Vertical Contacts List (full list) */}
      {!isHorizontal && (
        <div className={styles.contactsAreaVertical}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionTitle}>Recent Contacts</span>
            <span className={styles.sectionCount}>{contacts.length}</span>
          </div>
          <div className={styles.contactsListVertical}>
            {isLoadingContacts && <span className={styles.hint}>Fetching contacts...</span>}
            {!isLoadingContacts && contacts.length === 0 && (
               <span className={styles.hint}>No recent contacts found.</span>
            )}
            {!isLoadingContacts && contacts.map(contact => (
              <ContactChip
                key={contact.email}
                name={contact.name}
                email={contact.email}
                onClick={() => onSelectContact(contact.email)}
              />
            ))}
          </div>
        </div>
      )}

      <div className={styles.status}>
        <span
          className={`${styles.dot} ${health === 'connected' ? styles.dotOnline : styles.dotOffline}`}
          aria-hidden="true"
        />
        <span className={styles.statusLabel}>
          {health === 'connected' ? 'API connected' : health === 'offline' ? 'API offline' : 'Connecting...'}
        </span>
      </div>
    </nav>
  );
}
