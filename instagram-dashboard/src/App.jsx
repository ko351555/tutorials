import { useState } from 'react';
import './index.css';
import Sidebar from './components/Sidebar';
import ContentAnalyzer from './components/sections/ContentAnalyzer';
import ViralPlanner from './components/sections/ViralPlanner';
import CollabHub from './components/sections/CollabHub';
import MonetizationTracker from './components/sections/MonetizationTracker';
import MediaKit from './components/sections/MediaKit';
import GrowthTracker from './components/sections/GrowthTracker';

export default function App() {
  const [activeSection, setActiveSection] = useState('content');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const sections = {
    content: <ContentAnalyzer />,
    viral: <ViralPlanner />,
    collab: <CollabHub />,
    monetize: <MonetizationTracker />,
    mediakit: <MediaKit />,
    growth: <GrowthTracker />,
  };

  return (
    <div className="app-layout">
      <button
        className="mobile-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? '✕' : '☰'}
      </button>

      <div
        className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      <Sidebar
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        isOpen={sidebarOpen}
        setIsOpen={setSidebarOpen}
      />

      <main className="main-content" key={activeSection}>
        {sections[activeSection]}
      </main>
    </div>
  );
}
