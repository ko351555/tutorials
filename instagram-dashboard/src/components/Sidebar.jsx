export default function Sidebar({ activeSection, setActiveSection, isOpen, setIsOpen }) {
  const navItems = [
    { id: 'content', icon: '📊', label: 'Content Analyzer' },
    { id: 'viral', icon: '🚀', label: 'Viral Planner', badge: '7-Day' },
    { id: 'collab', icon: '🤝', label: 'Collab Hub', badge: '11 brands' },
    { id: 'monetize', icon: '💰', label: 'Monetization' },
    { id: 'mediakit', icon: '📄', label: 'Media Kit' },
    { id: 'growth', icon: '📈', label: 'Growth Tracker' },
  ];

  const handleNav = (id) => {
    setActiveSection(id);
    setIsOpen(false);
  };

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-brand">
        <div className="brand-logo">
          <div className="brand-icon">✨</div>
          <div>
            <div className="brand-name">Creator Pro</div>
          </div>
        </div>
        <div className="brand-tagline">Instagram Growth Dashboard</div>
      </div>

      <div className="sidebar-account">
        <div className="account-chip">
          <div className="account-handle">@thecozyfamily.ai</div>
          <div className="account-niche">🤖 AI Pixar Family · Glasgow, UK</div>
        </div>
      </div>

      <div className="sidebar-quick-stats">
        <div className="qs-pill">
          <div className="qs-value">2,975</div>
          <div className="qs-label">Followers</div>
        </div>
        <div className="qs-pill">
          <div className="qs-value">1.3M</div>
          <div className="qs-label">Views</div>
        </div>
        <div className="qs-pill">
          <div className="qs-value">557K</div>
          <div className="qs-label">Best Reel</div>
        </div>
        <div className="qs-pill">
          <div className="qs-value">12.8%</div>
          <div className="qs-label">Eng Rate</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-group-label">Dashboard</div>
        {navItems.map(item => (
          <div
            key={item.id}
            className={`nav-item ${activeSection === item.id ? 'active' : ''}`}
            onClick={() => handleNav(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
            {item.badge && <span className="nav-badge">{item.badge}</span>}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="footer-text">
          ✨ Built for @thecozyfamily.ai<br />
          <span style={{ color: 'var(--gold)', fontWeight: 600 }}>Glasgow, Scotland 🏴󠁧󠁢󠁳󠁣󠁴󠁿</span>
        </div>
      </div>
    </aside>
  );
}
