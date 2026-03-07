import { useState, useCallback, useEffect } from 'react';
import Shell from './components/layout/Shell';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import SummaryView from './components/features/SummaryView';
import ReplyView from './components/features/ReplyView';
import SearchView from './components/features/SearchView';
import SemanticView from './components/features/SemanticView';
import WelcomeView from './components/features/WelcomeView';
import styles from './App.module.css';

const VIEW_KEYS = ['summary', 'reply', 'search', 'semantic'];
const VIEWS = {
  summary: SummaryView,
  reply: ReplyView,
  search: SearchView,
  semantic: SemanticView,
};

export default function App() {
  const [activeView, setActiveView] = useState('home');
  const [contactEmail, setContactEmail] = useState('');

  const handleSelectContact = useCallback((email) => {
    setContactEmail(email);
  }, []);

  useEffect(() => {
    function onKeyDown(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      const idx = parseInt(e.key, 10) - 1;
      if (idx >= 0 && idx < VIEW_KEYS.length) {
        setActiveView(VIEW_KEYS[idx]);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const ActiveComponent = activeView && VIEWS[activeView];

  const isHome = activeView === 'home';

  return (
    <Shell
      isHorizontal={isHome}
      topBar={<TopBar onNavigate={setActiveView} />}
      sidebar={
        !isHome ? (
          <Sidebar
            activeView={activeView}
            isHorizontal={false}
            onNavigate={setActiveView}
            onSelectContact={handleSelectContact}
          />
        ) : null
      }
    >
      <div className={isHome ? styles.homePage : styles.page}>
        {isHome && (
          <WelcomeView onNavigate={setActiveView} />
        )}

        {!isHome && ActiveComponent && (
          <article className={styles.doc}>
            <ActiveComponent
              contactEmail={contactEmail}
              onContactChange={setContactEmail}
            />
          </article>
        )}
      </div>
    </Shell>
  );
}
