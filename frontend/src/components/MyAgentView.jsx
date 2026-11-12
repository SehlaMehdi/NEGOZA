import { useState } from 'react';
import { 
  Bot, 
  Sparkles, 
  Save, 
  Check, 
  DollarSign, 
  Percent, 
  Truck, 
  FileText, 
  Eye, 
  ArrowRight,
  Clock,
  Activity
} from 'lucide-react';
import TranscriptModal from './TranscriptModal';

export default function MyAgentView({
  agentSettings,
  onSaveSettings,
  negotiations = [],
  onNavigateTo,
  backendStatus = 'connected'
}) {
  // Form State initialized from persistent agentSettings
  const [maxSpendLimit, setMaxSpendLimit] = useState(agentSettings?.maxSpendLimit || 500);
  const [targetDiscountPercent, setTargetDiscountPercent] = useState(agentSettings?.targetDiscountPercent || 15);
  const [deliveryPreference, setDeliveryPreference] = useState(agentSettings?.deliveryPreference || 'Free standard delivery');
  const [additionalRequirements, setAdditionalRequirements] = useState(agentSettings?.additionalRequirements || '');
  const [isSavedFeedback, setIsSavedFeedback] = useState(false);

  // Modal transcript viewer state
  const [viewingNegotiation, setViewingNegotiation] = useState(null);

  const handleSave = (e) => {
    e.preventDefault();
    onSaveSettings({
      maxSpendLimit: Number(maxSpendLimit) || 500,
      targetDiscountPercent: Math.max(1, Math.min(50, Number(targetDiscountPercent) || 15)),
      deliveryPreference: deliveryPreference.trim() || 'Free standard delivery',
      additionalRequirements: additionalRequirements.trim(),
    });
    setIsSavedFeedback(true);
    setTimeout(() => {
      setIsSavedFeedback(false);
    }, 2800);
  };

  // Derive actual agent events from real user sessions (zero fabricated data)
  const realAgentEvents = negotiations.slice(0, 10).map((neg) => {
    const isDeal = neg.status === 'deal_reached';
    const isPurchased = neg.paymentStatus === 'purchased';
    let eventTitle;
    let eventType;

    if (isPurchased) {
      eventTitle = `Payment captured via PayPal Sandbox for ${neg.product?.name} ($${Number(neg.paypalCapture?.amount || neg.finalAgreedPrice || 0).toFixed(2)})`;
      eventType = 'payment';
    } else if (isDeal) {
      eventTitle = `Deal agreed for ${neg.product?.name} at $${Number(neg.finalAgreedPrice).toFixed(2)} with ${neg.product?.merchant} in ${neg.roundsCount} rounds`;
      eventType = 'deal';
    } else if (neg.status === 'maximum_rounds_reached') {
      eventTitle = `Maximum negotiation rounds reached for ${neg.product?.name}`;
      eventType = 'concluded';
    } else {
      eventTitle = `Negotiation concluded without agreement for ${neg.product?.name}`;
      eventType = 'rejected';
    }

    return {
      id: neg.id,
      timestamp: neg.createdAt ? new Date(neg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recently',
      title: eventTitle,
      type: eventType,
      negotiation: neg
    };
  });

  return (
    <div className="agent-workspace-view">
      {/* 1. Header Banner */}
      <section className="agent-hero-banner">
        <div className="agent-hero-content">
          <div className="view-badge">
            <Sparkles size={13} className="badge-icon" />
            <span>AUTONOMOUS BUYER AGENT</span>
          </div>
          <h1 className="agent-view-title">Buyer Agent Workspace</h1>
          <p className="agent-view-subtitle">
            Configure your AI buyer agent's purchasing boundaries and default negotiation strategy. These rules apply automatically whenever you activate your agent on products in Discover.
          </p>
        </div>

        {/* Live Operational Status Card */}
        <div className="agent-live-status-pill">
          <div className="agent-avatar buyer" style={{ width: 38, height: 38 }}>
            <Bot size={20} />
          </div>
          <div className="status-pill-text">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="agent-pulse-dot" style={{ backgroundColor: '#10b981' }}></span>
              <strong style={{ fontSize: 13.5, color: '#0f172a' }}>Google Gemini Agent Ready</strong>
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {backendStatus === 'connected' ? 'FastAPI Backend Online' : 'Connecting to API...'}
            </span>
          </div>
        </div>
      </section>

      {/* 2. Main Two-Column Layout */}
      <div className="agent-workspace-grid">
        {/* Left Column: Editable Configuration Controls */}
        <div className="agent-config-card">
          <div className="config-card-header">
            <div className="config-icon-box">
              <Bot size={20} />
            </div>
            <div>
              <h2 className="config-title">Negotiation Parameters & Guardrails</h2>
              <p className="config-desc">
                Saved preferences are automatically injected as defaults into your Discover activation modal.
              </p>
            </div>
          </div>

          <form onSubmit={handleSave} className="agent-config-form">
            {/* Field 1: Max Spending Limit */}
            <div className="config-form-group">
              <label htmlFor="max-spend" className="config-label">
                Default Maximum Budget Ceiling ($)
              </label>
              <span className="config-sublabel">
                The absolute highest amount your agent is authorized to pay for any single item.
              </span>
              <div className="input-with-adornment">
                <span className="adornment-icon">
                  <DollarSign size={16} />
                </span>
                <input
                  id="max-spend"
                  type="number"
                  min="10"
                  max="10000"
                  step="1"
                  value={maxSpendLimit}
                  onChange={(e) => setMaxSpendLimit(e.target.value)}
                  className="budget-input"
                  required
                />
              </div>
            </div>

            {/* Field 2: Target Discount Percentage */}
            <div className="config-form-group">
              <label htmlFor="target-discount" className="config-label">
                Target Discount Goal (%)
              </label>
              <span className="config-sublabel">
                The percentage discount below list price your agent targets during opening counteroffers.
              </span>
              <div className="input-with-adornment">
                <span className="adornment-icon">
                  <Percent size={16} />
                </span>
                <input
                  id="target-discount"
                  type="number"
                  min="5"
                  max="40"
                  step="1"
                  value={targetDiscountPercent}
                  onChange={(e) => setTargetDiscountPercent(e.target.value)}
                  className="budget-input"
                  required
                />
              </div>
              <div className="quick-budget-pills" style={{ marginTop: 6 }}>
                {[10, 15, 20, 25].map((pct) => (
                  <button
                    key={pct}
                    type="button"
                    className={`quick-pill ${Number(targetDiscountPercent) === pct ? 'active' : ''}`}
                    onClick={() => setTargetDiscountPercent(pct)}
                  >
                    {pct}% Target
                  </button>
                ))}
              </div>
            </div>

            {/* Field 3: Delivery Preference */}
            <div className="config-form-group">
              <label htmlFor="delivery-pref" className="config-label">
                Default Delivery Requirement
              </label>
              <span className="config-sublabel">
                Shipping conditions your agent will request during negotiations.
              </span>
              <div className="input-with-adornment">
                <span className="adornment-icon">
                  <Truck size={16} />
                </span>
                <input
                  id="delivery-pref"
                  type="text"
                  value={deliveryPreference}
                  onChange={(e) => setDeliveryPreference(e.target.value)}
                  className="budget-input"
                  placeholder="e.g. Free standard delivery, Express courier"
                  required
                />
              </div>
            </div>

            {/* Field 4: Additional Requirements */}
            <div className="config-form-group">
              <label htmlFor="additional-reqs" className="config-label">
                Mandatory Buying Requirements (Optional)
              </label>
              <span className="config-sublabel">
                Quality, packaging, or warranty clauses your agent should insist upon.
              </span>
              <div className="input-with-adornment">
                <span className="adornment-icon">
                  <FileText size={16} />
                </span>
                <input
                  id="additional-reqs"
                  type="text"
                  value={additionalRequirements}
                  onChange={(e) => setAdditionalRequirements(e.target.value)}
                  className="budget-input"
                  placeholder="e.g. Include 1-year warranty, Original retail box"
                />
              </div>
            </div>

            {/* Action Bar */}
            <div className="config-form-actions">
              <button
                type="submit"
                className="save-settings-btn"
              >
                <Save size={16} />
                <span>Save & Apply Agent Settings</span>
              </button>

              {isSavedFeedback && (
                <div className="saved-feedback-badge">
                  <Check size={14} />
                  <span>Preferences saved and active!</span>
                </div>
              )}
            </div>
          </form>
        </div>

        {/* Right Column: Real Agent Event Stream */}
        <div className="agent-stream-card">
          <div className="config-card-header">
            <div className="config-icon-box" style={{ background: '#f0fdf4', color: '#16a34a' }}>
              <Activity size={20} />
            </div>
            <div>
              <h2 className="config-title">Live Agent Activity Log</h2>
              <p className="config-desc">
                Auditable event stream generated from your real negotiation sessions.
              </p>
            </div>
          </div>

          <div className="agent-events-list">
            {realAgentEvents.length > 0 ? (
              realAgentEvents.map((evt) => (
                <div key={evt.id} className="agent-event-item">
                  <div className={`event-dot ${evt.type}`}></div>
                  <div className="event-body">
                    <div className="event-header-row">
                      <span className="event-time">{evt.timestamp}</span>
                      <button
                        type="button"
                        className="event-transcript-link"
                        onClick={() => setViewingNegotiation(evt.negotiation)}
                        title="View complete agent dialogue"
                      >
                        <span>Transcript</span>
                        <ArrowRight size={11} />
                      </button>
                    </div>
                    <p className="event-title">{evt.title}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-events-state">
                <Clock size={28} className="empty-clock-icon" />
                <h4 style={{ fontSize: 15, fontWeight: 700, margin: '8px 0 4px 0', color: '#0f172a' }}>
                  Agent Standing By
                </h4>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
                  No negotiation sessions have occurred yet. Open <strong>Discover</strong> and click <strong>Add my Agent</strong> on any sponsored product to start.
                </p>
                <button
                  type="button"
                  className="modal-start-btn"
                  style={{ marginTop: 12, padding: '8px 16px', fontSize: 13 }}
                  onClick={() => onNavigateTo?.('discover')}
                >
                  <span>Go to Discover Feed</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Bottom Section: Active & Past Negotiations Table */}
      <section className="agent-sessions-section">
        <div className="sessions-header">
          <div>
            <h2 className="sessions-title">Initiated Agent Negotiations</h2>
            <p className="sessions-desc">
              All multi-round conversations between your Buyer Agent and merchant Seller Agents.
            </p>
          </div>
          <span className="sessions-count-tag">
            {negotiations.length} {negotiations.length === 1 ? 'Session' : 'Sessions'} Recorded
          </span>
        </div>

        {negotiations.length > 0 ? (
          <div className="sessions-table-container">
            <table className="sessions-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Merchant</th>
                  <th>List Price</th>
                  <th>Agreed Price</th>
                  <th>Status</th>
                  <th>Rounds</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {negotiations.map((neg) => {
                  const isDeal = neg.status === 'deal_reached';
                  const isPurchased = neg.paymentStatus === 'purchased';
                  const listPrice = Number(neg.product?.advertisedPrice || 0);
                  const agreed = neg.finalAgreedPrice != null ? Number(neg.finalAgreedPrice) : null;

                  return (
                    <tr key={neg.id}>
                      <td className="product-cell">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <img
                            src={neg.product?.image || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'}
                            alt={neg.product?.name}
                            className="session-thumb"
                          />
                          <span className="session-product-name" title={neg.product?.name}>
                            {neg.product?.name}
                          </span>
                        </div>
                      </td>
                      <td>{neg.product?.merchant || 'Retailer'}</td>
                      <td>${listPrice.toFixed(2)}</td>
                      <td>
                        {agreed != null ? (
                          <strong style={{ color: '#16a34a' }}>${agreed.toFixed(2)}</strong>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td>
                        <span className={`turn-action-badge ${neg.status}`}>
                          {isPurchased 
                            ? 'Purchased' 
                            : isDeal 
                              ? 'Deal Reached' 
                              : neg.status.replace('_', ' ')
                          }
                        </span>
                      </td>
                      <td>{neg.roundsCount || 1}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button
                            type="button"
                            className="session-action-btn"
                            onClick={() => setViewingNegotiation(neg)}
                            title="Inspect full conversation"
                          >
                            <Eye size={13} />
                            <span>View</span>
                          </button>

                          {isDeal && (
                            <button
                              type="button"
                              className="session-action-btn primary"
                              onClick={() => onNavigateTo?.('my-deals')}
                              title="Go to Deal in My Deals"
                            >
                              <span>Review Deal</span>
                              <ArrowRight size={12} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-sessions-box">
            <Bot size={32} className="empty-bot-icon" />
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: '8px 0 4px 0', color: '#0f172a' }}>
              No Active Negotiations Found
            </h3>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', maxWidth: 440, margin: '0 auto 14px auto' }}>
              Whenever you activate an agent from Discover, the complete conversation, counteroffers, and signed deals will appear here.
            </p>
            <button
              type="button"
              className="modal-start-btn"
              onClick={() => onNavigateTo?.('discover')}
            >
              <span>Explore Discover Feed</span>
              <ArrowRight size={14} />
            </button>
          </div>
        )}
      </section>

      {/* Transcript Modal Viewer */}
      <TranscriptModal
        negotiation={viewingNegotiation}
        isOpen={Boolean(viewingNegotiation)}
        onClose={() => setViewingNegotiation(null)}
      />
    </div>
  );
}
