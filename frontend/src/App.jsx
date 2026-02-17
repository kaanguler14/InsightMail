import { useState, useCallback, useEffect } from 'react';
import Shell from './components/layout/Shell';
import Sidebar from './components/layout/Sidebar';
import SummaryView from './components/features/SummaryView';
import ReplyView from './components/features/ReplyView';
import SearchView from './components/features/SearchView';
import SemanticView from './components/features/SemanticView';
import styles from './App.module.css';

const VIEW_KEYS = ['summary', 'reply', 'search', 'semantic'];
const VIEWS = {
  summary: SummaryView,
  reply: ReplyView,
  search: SearchView,
  semantic: SemanticView,
};

export default function App() {
  const [activeView, setActiveView] = useState('summary');
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

  const ActiveComponent = VIEWS[activeView];

  return (
    <Shell
      sidebar={
        <Sidebar
          activeView={activeView}
          onNavigate={setActiveView}
          onSelectContact={handleSelectContact}
        />
      }
    >
      <div className={styles.page}>
        <ActiveComponent
          contactEmail={contactEmail}
          onContactChange={setContactEmail}
        />
      </div>
    </Shell>
  );
}
