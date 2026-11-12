import Navbar from './Navbar';
import { ShieldCheck } from 'lucide-react';

export default function Layout({ 
  children, 
  activeTab, 
  onTabChange,
  backendStatus,
  onRetryBackend
}) {
  return (
    <div className="negoza-app-layout">
      {/* Reusable Top Navigation Bar */}
      <Navbar 
        activeTab={activeTab} 
        onTabChange={onTabChange} 
        backendStatus={backendStatus}
        onRetryBackend={onRetryBackend}
      />

      {/* Main Content Area */}
      <main className="negoza-main-content">
        <div className="negoza-content-container">
          {children}
        </div>
      </main>

      {/* Subtle Startup Platform Footer */}
      <footer className="negoza-footer">
        <div className="footer-container">
          <div className="footer-left">
            <span className="footer-brand">NEGOZA</span>
            <span className="footer-divider">•</span>
            <span className="footer-desc">Autonomous Agentic Commerce</span>
          </div>
          <div className="footer-right">
            <span className="footer-security-pill">
              <ShieldCheck size={14} className="security-icon" />
              <span>Verified Agent Protocol & PayPal Checkout Ready</span>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
