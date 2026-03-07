import { useState, useCallback } from 'react';
import styles from './WelcomeView.module.css';

const CARDS = [
  {
    key: 'summary',
    title: 'Inbox Summaries',
    description: 'Quickly grasp long email threads with intelligent auto-summaries.',
    count: '3',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2.5" />
        <path d="M8 8h8M8 12h5M8 16h6" />
      </svg>
    ),
  },
  {
    key: 'reply',
    title: 'Smart Replies',
    description: 'Draft perfect, context-aware responses with generic AI assistance.',
    count: '5',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 10L4 15l5 5" />
        <path d="M4 15h7a4 4 0 004-4V4" />
      </svg>
    ),
  },
  {
    key: 'search',
    title: 'Insightful Q&A',
    description: 'Ask deep questions about your mailbox and receive sourced answers.',
    count: '8',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="6" />
        <path d="M16 16l4 4" />
      </svg>
    ),
  },
  {
    key: 'semantic',
    title: 'Semantic Search',
    description: 'Find emails by their meaning and intent rather than just keywords.',
    count: '12',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 6h18M6 12h12M4 18h8" />
      </svg>
    ),
  },
  {
    key: 'summary',
    title: 'Privacy First',
    description: 'Everything strictly runs locally on your machine. No cloud storage.',
    count: '—',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
      </svg>
    ),
  },
  {
    key: 'search',
    title: 'Knowledge Base',
    description: 'Your complete email history turned into a searchable knowledge base.',
    count: '—',
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <path d="M9 9h6M9 13h6M9 17h4" />
      </svg>
    ),
  },
];

export default function WelcomeView({ onNavigate }) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchSubmit = useCallback((e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onNavigate('search');
    }
  }, [searchQuery, onNavigate]);

  return (
    <div className={styles.wrapper}>
      <section className={styles.hero} aria-label="Welcome">
        <h1 className={styles.greeting}>How can we help you?</h1>
        <form className={styles.searchForm} onSubmit={handleSearchSubmit}>
          <span className={styles.searchIcon} aria-hidden>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </span>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search your emails or ask a question..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search or ask"
          />
          <kbd className={styles.searchKbd}>⌘K</kbd>
        </form>
      </section>

      <section className={styles.cardsSection} aria-label="Features">
        <div className={styles.cardsGrid}>
          {CARDS.map((card, i) => (
            <button
              key={`${card.title}-${i}`}
              type="button"
              className={styles.card}
              onClick={() => onNavigate(card.key)}
            >
              <span className={styles.cardIcon}>{card.icon}</span>
              <h2 className={styles.cardTitle}>{card.title}</h2>
              <p className={styles.cardDesc}>{card.description}</p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
