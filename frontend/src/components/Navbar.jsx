import { useState } from 'react';
import { 
  Bot, 
  Compass, 
  Tag, 
  Bell, 
  Menu, 
  X, 
  ChevronDown, 
  Sparkles
} from 'lucide-react';

export default function Navbar({ 
  activeTab = 'discover', 
  onTabChange = () => {},
  backendStatus = 'checking',
  onRetryBackend = () => {}
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'discover', label: 'Discover', icon: Compass },
    { id: 'my-agent', label: 'My Agent', icon: Bot },
    { id: 'my-deals', label: 'My Deals', icon: Tag },
  ];

  const handleTabClick = (tabId) => {
    onTabChange(tabId);
    setMobileMenuOpen(false);
  };

  const getBackendStatusText = () => {
    switch (backendStatus) {
      case 'connected':
        return 'Connected';
      case 'disconnected':
        return 'Disconnected';
      case 'checking':
      default:
        return 'Checking';
    }
  };

  return (
    <header className="navbar-header">
      <div className="navbar-container">
        {/* Brand Logo & Name */}
        <div className="navbar-brand-group">
          <button 
            type="button" 
            className="navbar-brand" 
            onClick={() => handleTabClick('discover')}
            aria-label="NEGOZA Home"
          >
            <div className="brand-logo-mark">
              <Sparkles className="brand-icon" size={18} strokeWidth={2.4} />
            </div>
            <div className="brand-text-container">
              <span className="brand-title">NEGOZA</span>
              <span className="brand-tagline">AGENTIC COMMERCE</span>
            </div>
          </button>
        </div>

        {/* Desktop Navigation Links */}
        <nav className="navbar-links" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-link ${isActive ? 'active' : ''}`}
                onClick={() => handleTabClick(item.id)}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon size={17} className="nav-link-icon" />
                <span>{item.label}</span>
                {isActive && <span className="active-pill" />}
              </button>
            );
          })}
        </nav>

        {/* Right Section: Backend Status, Agent Status, Notifications & Profile */}
        <div className="navbar-actions">
          {/* Backend Connection Status Indicator */}
          <button 
            type="button"
            className={`backend-status-pill status-${backendStatus}`}
            onClick={onRetryBackend}
            title={
              backendStatus === 'connected'
                ? 'Backend API Connected (FastAPI)'
                : backendStatus === 'disconnected'
                ? 'Backend API Unavailable — Click to re-check'
                : 'Verifying Backend API connection...'
            }
            aria-label={`Backend connection status: ${getBackendStatusText()}`}
          >
            <span className={`status-dot dot-${backendStatus}`}></span>
            <span className="backend-status-text">
              Backend: <strong>{getBackendStatusText()}</strong>
            </span>
          </button>

          {/* Agent Status Pill */}
          <div className="agent-status-pill" title="Buyer Agent Status">
            <span className="status-dot"></span>
            <span className="status-label">Agent Ready</span>
          </div>

          {/* Notifications Button Placeholder */}
          <button 
            type="button" 
            className="navbar-icon-button" 
            aria-label="Notifications"
          >
            <Bell size={18} />
          </button>

          {/* User Profile / Avatar Placeholder */}
          <div className="user-profile-widget" tabIndex={0} role="button" aria-label="User Account">
            <div className="avatar-placeholder">
              <span className="avatar-initials">AN</span>
            </div>
            <div className="user-info">
              <span className="user-name">Alex N.</span>
              <span className="user-role">Buyer</span>
            </div>
            <ChevronDown size={14} className="user-chevron" />
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            className="mobile-toggle-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Dropdown Panel */}
      {mobileMenuOpen && (
        <div className="mobile-nav-panel">
          <div className="mobile-nav-links">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`mobile-nav-link ${isActive ? 'active' : ''}`}
                  onClick={() => handleTabClick(item.id)}
                >
                  <Icon size={19} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>

          <div className="mobile-nav-footer">
            {/* Mobile Backend Connection Indicator */}
            <div 
              className={`mobile-backend-status status-${backendStatus}`}
              onClick={onRetryBackend}
              role="button"
              tabIndex={0}
            >
              <span className={`status-dot dot-${backendStatus}`}></span>
              <span>Backend API: <strong>{getBackendStatusText()}</strong></span>
            </div>

            <div className="mobile-agent-status">
              <span className="status-dot"></span>
              <span>Buyer Agent: Ready & Active</span>
            </div>
            <div className="mobile-user-profile">
              <div className="avatar-placeholder">
                <span className="avatar-initials">AN</span>
              </div>
              <div className="user-info">
                <span className="user-name">Alex N.</span>
                <span className="user-role">alex.negoza@domain.com</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
