import { useEffect } from 'react';
import { 
  X, 
  Bot, 
  Store, 
  Truck, 
  CheckCircle2, 
  XCircle, 
  Clock
} from 'lucide-react';

export default function TranscriptModal({ negotiation, isOpen, onClose }) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !negotiation) return null;

  const { product, transcript, status, roundsCount, summary, finalAgreedPrice, deliveryTerms } = negotiation;
  const advertisedPrice = Number(product?.advertisedPrice || 0);
  const agreedPrice = finalAgreedPrice != null ? Number(finalAgreedPrice) : null;
  const actualSavings = agreedPrice != null ? Math.max(0, advertisedPrice - agreedPrice) : 0;

  return (
    <div 
      className="modal-backdrop" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="transcript-modal-title"
    >
      <div 
        className="modal-window negotiation-expanded transcript-modal-window"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-avatar-badge">
              <Bot size={22} className="modal-bot-icon" />
            </div>
            <div>
              <h2 id="transcript-modal-title" className="modal-title">
                Auditable Negotiation Transcript
              </h2>
              <span className="modal-subtitle">
                {product?.name} &bull; {product?.merchant}
              </span>
            </div>
          </div>
          <button 
            type="button" 
            className="modal-close-btn" 
            onClick={onClose}
            aria-label="Close transcript"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body: Active Transcript Stream */}
        <div className="modal-body modal-body-negotiation" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Top Status Bar */}
          <div className="transcript-meta-bar">
            <div className="transcript-meta-info">
              <span className="meta-label">Session ID:</span>
              <code>{negotiation.id}</code>
            </div>
            <div className="transcript-meta-info">
              <span className="meta-label">List Price:</span>
              <strong>${advertisedPrice.toFixed(2)}</strong>
            </div>
            {agreedPrice != null && (
              <div className="transcript-meta-info">
                <span className="meta-label">Agreed Price:</span>
                <strong style={{ color: '#16a34a' }}>${agreedPrice.toFixed(2)}</strong>
              </div>
            )}
            <div className={`turn-action-badge ${status}`} style={{ textTransform: 'capitalize' }}>
              {status === 'deal_reached' ? `Deal Reached (${roundsCount} Rds)` : status.replace('_', ' ')}
            </div>
          </div>

          {/* Transcript Message Stream */}
          <div className="transcript-stream" style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }} role="log">
            {transcript && transcript.length > 0 ? (
              transcript.map((turn, index) => {
                const isBuyer = turn.agent === 'buyer';
                const actionClass = turn.action;
                const roundNumber = turn.round_number;
                const isFirstInRound = index === 0 || transcript[index - 1]?.round_number !== roundNumber;

                return (
                  <div key={index}>
                    {/* Round separator marker */}
                    {isFirstInRound && (
                      <div className="transcript-round-marker">
                        <span className="round-marker-line"></span>
                        <span className="round-marker-pill">Round {roundNumber}</span>
                        <span className="round-marker-line"></span>
                      </div>
                    )}

                    {/* Turn Card */}
                    <div className={`transcript-turn ${isBuyer ? 'buyer' : 'seller'}`}>
                      <div className="turn-avatar-col">
                        <div className={`agent-avatar ${isBuyer ? 'buyer' : 'seller'}`} style={{ width: 34, height: 34 }}>
                          {isBuyer ? <Bot size={18} /> : <Store size={18} />}
                        </div>
                      </div>

                      <div className="turn-content-col">
                        <div className="turn-header-row">
                          <div className={`turn-agent-tag ${isBuyer ? 'buyer' : 'seller'}`}>
                            <span>{isBuyer ? 'NEGOZA Buyer Agent' : `${product?.merchant || 'Merchant'} Seller Agent`}</span>
                          </div>
                          <span className={`turn-action-badge ${actionClass}`}>
                            {turn.action.replace('_', ' ')}
                          </span>
                        </div>

                        {/* Offer Price & Delivery Conditions */}
                        {turn.proposed_price != null && (
                          <div className="turn-offer-banner">
                            <span className={`turn-price-figure ${isBuyer ? 'buyer' : 'seller'}`}>
                              ${Number(turn.proposed_price).toFixed(2)}
                            </span>
                            {turn.delivery_conditions && (
                              <span className="turn-delivery-pill">
                                <Truck size={13} />
                                <span>{turn.delivery_conditions}</span>
                              </span>
                            )}
                          </div>
                        )}

                        {/* Agent Dialogue Message */}
                        <p className="turn-message-bubble">{turn.agent_response}</p>

                        {/* Agent Strategic Reasoning */}
                        {turn.reasoning && (
                          <div className={`turn-reasoning-box ${isBuyer ? 'buyer' : 'seller'}`}>
                            <span className="turn-reasoning-label">
                              {isBuyer ? 'Buyer Strategy Rationale' : 'Merchant Commercial Rationale'}
                            </span>
                            <span>{turn.reasoning}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px 0' }}>
                No transcript turns recorded for this session.
              </p>
            )}
          </div>

          {/* Outcome Footer */}
          <div className="transcript-modal-footer">
            <div className="outcome-summary-col">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {status === 'deal_reached' ? (
                  <CheckCircle2 size={18} color="#16a34a" />
                ) : status === 'maximum_rounds_reached' ? (
                  <Clock size={18} color="#ca8a04" />
                ) : (
                  <XCircle size={18} color="#dc2626" />
                )}
                <strong style={{ fontSize: 14, color: '#0f172a' }}>
                  {summary || (status === 'deal_reached' ? 'Agreement Reached' : 'Negotiation Concluded')}
                </strong>
              </div>
              {status === 'deal_reached' && (
                <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  Delivery: <strong>{deliveryTerms || 'Standard'}</strong> &bull; Savings: <strong style={{ color: '#16a34a' }}>${actualSavings.toFixed(2)}</strong>
                </span>
              )}
            </div>

            <button
              type="button"
              className="modal-start-btn"
              onClick={onClose}
              style={{ padding: '8px 18px', fontSize: 14 }}
            >
              Close Transcript
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
