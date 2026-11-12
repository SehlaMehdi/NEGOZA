import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import DiscoverFeed from './components/DiscoverFeed';
import MyAgentView from './components/MyAgentView';
import MyDealsView from './components/MyDealsView';
import { checkBackendHealth } from './services/api';

const DEFAULT_AGENT_SETTINGS = {
  maxSpendLimit: 500,
  targetDiscountPercent: 15,
  deliveryPreference: 'Free standard delivery',
  additionalRequirements: ''
};

function App() {
  const [activeTab, setActiveTab] = useState('discover');
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'

  // Persistent Agent Settings
  const [agentSettings, setAgentSettings] = useState(() => {
    try {
      const saved = localStorage.getItem('negoza_agent_settings');
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return DEFAULT_AGENT_SETTINGS;
  });

  // Persistent User Negotiations
  const [negotiations, setNegotiations] = useState(() => {
    try {
      const saved = localStorage.getItem('negoza_negotiations');
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return [];
  });

  // Save settings handler
  const handleSaveSettings = (newSettings) => {
    setAgentSettings(newSettings);
    try {
      localStorage.setItem('negoza_agent_settings', JSON.stringify(newSettings));
    } catch {
      // ignore
    }
  };

  // Add or update completed negotiation session
  const handleNegotiationComplete = (sessionRecord) => {
    setNegotiations((prev) => {
      const existingIdx = prev.findIndex(
        (n) => n.id === sessionRecord.id || n.negotiation_id === sessionRecord.negotiation_id
      );
      let updated;
      if (existingIdx >= 0) {
        updated = [...prev];
        updated[existingIdx] = { ...updated[existingIdx], ...sessionRecord };
      } else {
        updated = [sessionRecord, ...prev];
      }
      try {
        localStorage.setItem('negoza_negotiations', JSON.stringify(updated));
      } catch {
        // ignore
      }
      return updated;
    });
  };

  // Update deal with PayPal order or capture information
  const handleUpdateDealPayment = ({ negotiationId, paypalOrder, paypalCapture, paymentStatus }) => {
    setNegotiations((prev) => {
      const updated = prev.map((n) => {
        if (n.id === negotiationId || n.negotiation_id === negotiationId) {
          return {
            ...n,
            ...(paypalOrder ? { paypalOrder } : {}),
            ...(paypalCapture ? { paypalCapture } : {}),
            ...(paymentStatus ? { paymentStatus } : {})
          };
        }
        return n;
      });
      try {
        localStorage.setItem('negoza_negotiations', JSON.stringify(updated));
      } catch {
        // ignore
      }
      return updated;
    });
  };

  // Verify backend health on mount
  useEffect(() => {
    let isMounted = true;

    const verifyConnection = async () => {
      setBackendStatus('checking');
      const result = await checkBackendHealth();
      if (isMounted) {
        setBackendStatus(result.isHealthy ? 'connected' : 'disconnected');
      }
    };

    verifyConnection();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleRetryBackend = async () => {
    setBackendStatus('checking');
    const result = await checkBackendHealth();
    setBackendStatus(result.isHealthy ? 'connected' : 'disconnected');
  };

  return (
    <Layout 
      activeTab={activeTab} 
      onTabChange={setActiveTab}
      backendStatus={backendStatus}
      onRetryBackend={handleRetryBackend}
    >
      {activeTab === 'discover' && (
        <DiscoverFeed 
          agentSettings={agentSettings}
          onNegotiationComplete={handleNegotiationComplete}
          onUpdateDealPayment={handleUpdateDealPayment}
        />
      )}

      {activeTab === 'my-agent' && (
        <MyAgentView
          agentSettings={agentSettings}
          onSaveSettings={handleSaveSettings}
          negotiations={negotiations}
          onNavigateTo={setActiveTab}
          backendStatus={backendStatus}
        />
      )}

      {activeTab === 'my-deals' && (
        <MyDealsView
          negotiations={negotiations}
          onUpdateDealPayment={handleUpdateDealPayment}
          onNavigateTo={setActiveTab}
        />
      )}
    </Layout>
  );
}

export default App;
