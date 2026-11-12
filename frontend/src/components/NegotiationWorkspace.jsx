import { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Store, 
  Sparkles, 
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  AlertCircle,
  Truck, 
  ArrowRight, 
  RefreshCw, 
  FileText, 
  Check, 
  Clock,
  X,
  CreditCard,
  ExternalLink,
  Lock
} from 'lucide-react';
import { createPayPalOrder, capturePayPalOrder } from '../services/api';

export default function NegotiationWorkspace({
  product,
  targetBudget,
  maxBudget,
  negotiationData,
  isLoading,
  errorMessage,
  onReset,
  onClose,
  onUpdateDealPayment,
}) {
  const [showReviewDeal, setShowReviewDeal] = useState(false);
  const transcriptEndRef = useRef(null);

  // PayPal Sandbox Checkout State
  const [paypalState, setPaypalState] = useState('idle'); // 'idle' | 'creating' | 'created' | 'capturing' | 'captured' | 'not_approved' | 'error'
  const [paypalOrder, setPaypalOrder] = useState(null);
  const [captureResult, setCaptureResult] = useState(null);
  const [paypalErrorMessage, setPaypalErrorMessage] = useState(null);

  const advertisedPrice = Number(product.advertisedPrice);

  // Financial calculations when a deal is reached
  const finalPrice = negotiationData?.final_agreed_price != null ? Number(negotiationData.final_agreed_price) : null;
  const isFreeDelivery = (negotiationData?.delivery_terms || '').toLowerCase().includes('free');
  
  // Extract numeric delivery fee if not free
  let deliveryFee = 0;
  if (!isFreeDelivery && negotiationData?.delivery_terms) {
    const feeMatch = negotiationData.delivery_terms.match(/\$([0-9.]+)/);
    deliveryFee = feeMatch ? parseFloat(feeMatch[1]) : 0;
  }
  const totalPayable = finalPrice != null ? finalPrice + deliveryFee : null;
  const actualSavings = finalPrice != null ? Math.max(0, advertisedPrice - finalPrice) : 0;
  const savingsPercent = advertisedPrice > 0 ? Math.round((actualSavings / advertisedPrice) * 100) : 0;

  // Auto-scroll transcript to bottom when new messages arrive
  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [negotiationData?.transcript, isLoading]);

  // Handle initiating PayPal Sandbox Checkout
  const handleInitiatePayPal = async () => {
    if (!totalPayable || totalPayable <= 0) return;
    setShowReviewDeal(true);
    setPaypalState('creating');
    setPaypalErrorMessage(null);

    const payload = {
      negotiation_id: negotiationData?.negotiation_id || `deal-${Date.now()}`,
      product_name: product.name,
      amount: totalPayable,
      currency: 'USD'
    };

    const res = await createPayPalOrder(payload);
    if (res.success && res.data) {
      setPaypalOrder(res.data);
      setPaypalState('created');
      if (onUpdateDealPayment) {
        onUpdateDealPayment({
          negotiationId: negotiationData?.negotiation_id,
          paypalOrder: res.data,
          paymentStatus: 'order_created'
        });
      }
    } else {
      setPaypalState('error');
      setPaypalErrorMessage(res.error || 'Failed to initiate PayPal Sandbox checkout.');
    }
  };

  // Handle capturing PayPal Sandbox payment
  const handleCapturePayment = async () => {
    if (!paypalOrder?.order_id) return;
    setPaypalState('capturing');
    setPaypalErrorMessage(null);

    const res = await capturePayPalOrder(paypalOrder.order_id);
    if (res.success && res.data) {
      setCaptureResult(res.data);
      if (res.data.status === 'COMPLETED') {
        setPaypalState('captured');
        if (onUpdateDealPayment) {
          onUpdateDealPayment({
            negotiationId: negotiationData?.negotiation_id,
            paypalCapture: res.data,
            paymentStatus: 'purchased'
          });
        }
      } else {
        // Authentic PayPal response (e.g. ORDER_NOT_APPROVED)
        setPaypalState('not_approved');
      }
    } else {
      setPaypalState('error');
      setPaypalErrorMessage(res.error || 'Failed to capture PayPal Sandbox payment.');
    }
  };

  return (
    <div className="negotiation-workspace">
      {/* 1. FIXED HEADER: Visual Active Agents Comparison */}
      <div className="negotiation-agents-header">
        {/* Buyer Agent Identity (Purple) */}
        <div className="agent-identity-box buyer">
          <div className="agent-avatar buyer">
            <Bot size={22} />
          </div>
          <div className="agent-info">
            <span className="agent-name buyer">NEGOZA Buyer Agent</span>
            <span className="agent-role-tag">Customer Representative</span>
            <span className="agent-metric-subtext">
              Target: ${targetBudget} &bull; Ceiling: ${maxBudget}
            </span>
          </div>
        </div>

        {/* Center Live Protocol Badge */}
        <div className="negotiation-vs-divider">
          <span className="vs-badge">VS</span>
          <div className="live-protocol-pulse">
            <span className="agent-pulse-dot"></span>
            <span>
              {isLoading 
                ? 'Negotiating...' 
                : negotiationData?.status === 'deal_reached'
                  ? 'Agreement Reached'
                  : 'Autonomous Protocol'
              }
            </span>
          </div>
        </div>

        {/* Seller Agent Identity (Teal) */}
        <div className="agent-identity-box seller">
          <div className="agent-info">
            <span className="agent-name seller">{product.merchant} Seller Agent</span>
            <span className="agent-role-tag">Merchant Representative</span>
            <span className="agent-metric-subtext">
              Advertised List: ${advertisedPrice}
            </span>
          </div>
          <div className="agent-avatar seller">
            <Store size={22} />
          </div>
        </div>
      </div>

      {/* 2. PRIMARY SCROLLABLE AREA: Loading, Error or Transcript */}
      <div className="negotiation-main-content">
        {/* Loading State: Agents Exchanging Proposals */}
        {isLoading && (
          <div className="agent-loading-view">
            <div className="agent-loading-spinner-wrap">
              <div className="agent-spinner-ring"></div>
              <Sparkles size={28} className="agent-spinner-bot" />
            </div>
            <div className="agent-loading-heading">
              Agents Actively Negotiating...
            </div>
            <p className="agent-loading-desc">
              Your Buyer Agent is exchanging counter-proposals with {product.merchant}’s Seller Agent across price, warranty, and delivery terms.
            </p>
          </div>
        )}

        {/* Error State */}
        {!isLoading && errorMessage && (
          <div className="agent-error-view">
            <div className="agent-error-header">
              <AlertTriangle size={20} />
              <span>Negotiation Engine Disruption</span>
            </div>
            <p className="agent-error-msg">{errorMessage}</p>
            <div className="negotiation-actions-bar" style={{ justifyContent: 'flex-start' }}>
              <button
                type="button"
                className="modal-cancel-btn"
                onClick={onReset}
              >
                <RefreshCw size={14} />
                <span>Adjust Target & Retry</span>
              </button>
            </div>
          </div>
        )}

        {/* Chronological Conversation Transcript */}
        {!isLoading && negotiationData && negotiationData.transcript && (
          <div className="transcript-stream" role="log" aria-label="Negotiation conversation transcript">
            {negotiationData.transcript.map((turn, index) => {
              const isBuyer = turn.agent === 'buyer';
              const actionClass = turn.action;
              const roundNumber = turn.round_number;
              const isFirstInRound = index === 0 || negotiationData.transcript[index - 1]?.round_number !== roundNumber;

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
                    {/* Avatar Icon Column */}
                    <div className="turn-avatar-col">
                      <div className={`agent-avatar ${isBuyer ? 'buyer' : 'seller'}`} style={{ width: 34, height: 34 }}>
                        {isBuyer ? <Bot size={18} /> : <Store size={18} />}
                      </div>
                    </div>

                    {/* Message & Offer Content Column */}
                    <div className="turn-content-col">
                      <div className="turn-header-row">
                        <div className={`turn-agent-tag ${isBuyer ? 'buyer' : 'seller'}`}>
                          <span>{isBuyer ? 'NEGOZA Buyer Agent' : `${product.merchant} Seller Agent`}</span>
                        </div>
                        <span className={`turn-action-badge ${actionClass}`}>
                          {turn.action.replace('_', ' ')}
                        </span>
                      </div>

                      {/* Offer Price & Delivery Tag if proposed */}
                      {turn.proposed_price != null && (
                        <div className="turn-offer-banner">
                          <span className={`turn-price-figure ${isBuyer ? 'buyer' : 'seller'}`}>
                            ${turn.proposed_price.toFixed(2)}
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

                      {/* Agent Strategic Reasoning / Rationale */}
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
            })}
            <div ref={transcriptEndRef} style={{ height: 1 }} />
          </div>
        )}
      </div>

      {/* 3. FIXED BOTTOM FOOTER: Final Deal Summary & Action Buttons */}
      {!isLoading && negotiationData && (
        <div className="negotiation-footer-container">
          {/* Outcome 1: Deal Reached */}
          {negotiationData.status === 'deal_reached' && (
            <div className="deal-outcome-card deal_reached">
              <div className="deal-outcome-header">
                <div className="deal-status-badge deal_reached">
                  <CheckCircle2 size={16} />
                  <span>DEAL REACHED IN ROUND {negotiationData.rounds_count}</span>
                </div>
                <button
                  type="button"
                  className="deal-review-btn"
                  onClick={() => setShowReviewDeal(true)}
                  aria-label="Review Deal Details"
                >
                  <FileText size={15} />
                  <span>Review Deal</span>
                  <ArrowRight size={14} />
                </button>
              </div>

              <p className="deal-summary-text">{negotiationData.summary}</p>

              {/* Comprehensive Financial Metrics Breakdown */}
              <div className="deal-breakdown-grid">
                <div className="deal-metric-box">
                  <span className="deal-metric-title">List Price</span>
                  <span className="deal-metric-amount">${advertisedPrice.toFixed(2)}</span>
                </div>
                <div className="deal-metric-box">
                  <span className="deal-metric-title">Agreed Price</span>
                  <span className="deal-metric-amount">${finalPrice?.toFixed(2)}</span>
                </div>
                <div className="deal-metric-box">
                  <span className="deal-metric-title">Delivery</span>
                  <span className="deal-metric-amount">
                    {isFreeDelivery ? 'Free ($0)' : `+$${deliveryFee.toFixed(2)}`}
                  </span>
                </div>
                <div className="deal-metric-box">
                  <span className="deal-metric-title">Your Savings</span>
                  <span className="deal-metric-savings">${actualSavings.toFixed(2)} ({savingsPercent}%)</span>
                </div>
                <div className="deal-metric-box payable">
                  <span className="deal-metric-title">Total Payable</span>
                  <span className="deal-metric-amount">${totalPayable?.toFixed(2)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Outcome 2: Negotiation Failed */}
          {negotiationData.status === 'negotiation_failed' && (
            <div className="deal-outcome-card negotiation_failed">
              <div className="deal-outcome-header">
                <div className="deal-status-badge negotiation_failed">
                  <XCircle size={16} />
                  <span>NEGOTIATION CONCLUDED WITHOUT AGREEMENT</span>
                </div>
              </div>
              <p className="deal-summary-text">{negotiationData.summary}</p>
            </div>
          )}

          {/* Outcome 3: Maximum Rounds Reached */}
          {negotiationData.status === 'maximum_rounds_reached' && (
            <div className="deal-outcome-card maximum_rounds_reached">
              <div className="deal-outcome-header">
                <div className="deal-status-badge maximum_rounds_reached">
                  <Clock size={16} />
                  <span>MAXIMUM ROUNDS EXHAUSTED</span>
                </div>
              </div>
              <p className="deal-summary-text">{negotiationData.summary}</p>
            </div>
          )}

          {/* Primary Action Buttons Bar */}
          <div className="negotiation-actions-bar">
            {negotiationData.status === 'deal_reached' ? (
              <>
                <button
                  type="button"
                  className="modal-cancel-btn"
                  onClick={onReset}
                >
                  <RefreshCw size={14} />
                  <span>New Negotiation</span>
                </button>
                <button
                  type="button"
                  className="modal-start-btn"
                  onClick={handleInitiatePayPal}
                >
                  <CreditCard size={16} />
                  <span>Approve & Pay (${totalPayable?.toFixed(2)})</span>
                  <ArrowRight size={14} />
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="modal-cancel-btn"
                  onClick={onClose}
                >
                  <span>Close</span>
                </button>
                <button
                  type="button"
                  className="modal-start-btn"
                  onClick={onReset}
                >
                  <RefreshCw size={14} />
                  <span>Adjust Budget & Retry</span>
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Review Deal Summary Sheet (Modal Overlay with PayPal Sandbox Checkout) */}
      {showReviewDeal && (
        <div 
          className="deal-review-overlay"
          onClick={() => setShowReviewDeal(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="deal-review-title"
        >
          <div 
            className="deal-review-sheet"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="deal-review-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <CheckCircle2 size={22} color="#16a34a" />
                <h3 id="deal-review-title" className="deal-review-title">
                  Negotiated Deal Summary & Approval
                </h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowReviewDeal(false)}
                aria-label="Close summary"
              >
                <X size={18} />
              </button>
            </div>

            <div className="deal-review-body">
              {/* Product Brief */}
              <div className="modal-product-summary">
                <img
                  src={product.image}
                  alt={product.name}
                  className="modal-product-img"
                  style={{ width: 60, height: 60 }}
                />
                <div className="modal-product-details">
                  <span className="modal-product-merchant">{product.merchant}</span>
                  <h4 className="modal-product-name">{product.name}</h4>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Session Ref: <code>{negotiationData?.negotiation_id}</code>
                  </span>
                </div>
              </div>

              {/* Itemized Commercial Table */}
              <div className="deal-invoice-table">
                <div className="invoice-row">
                  <span>Original Advertised Price</span>
                  <span>${advertisedPrice.toFixed(2)}</span>
                </div>
                <div className="invoice-row">
                  <span>Agent Negotiated Discount</span>
                  <span className="invoice-savings-badge">-${actualSavings.toFixed(2)} ({savingsPercent}%)</span>
                </div>
                <div className="invoice-row">
                  <span>Final Agreed Product Price</span>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                    ${finalPrice?.toFixed(2)}
                  </span>
                </div>
                <div className="invoice-row">
                  <span>Delivery Terms</span>
                  <span>
                    {isFreeDelivery ? 'Free Delivery ($0.00)' : `Standard Delivery ($${deliveryFee.toFixed(2)})`}
                  </span>
                </div>
                <div className="invoice-row total">
                  <span>Total Payable Amount</span>
                  <span className="invoice-value">${totalPayable?.toFixed(2)}</span>
                </div>
              </div>

              {/* Safe Milestone Notice */}
              <div className="deal-security-notice">
                <ShieldCheck size={20} style={{ flexShrink: 0, marginTop: 1, color: '#16a34a' }} />
                <span>
                  <strong>Autonomous deal verified:</strong> Both the Buyer Agent and {product.merchant} Seller Agent have signed off on these commercial terms.
                </span>
              </div>

              {/* =========================================================
                 REAL PAYPAL SANDBOX CHECKOUT SECTION
                 ========================================================= */}
              <div className="paypal-checkout-section">
                <div className="paypal-section-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Lock size={16} color="#003087" />
                    <span style={{ fontWeight: 700, color: '#0f172a' }}>PayPal Sandbox Authorization</span>
                  </div>
                  <span className="paypal-badge-sandbox">SANDBOX ENVIRONMENT</span>
                </div>

                {/* State 1: Idle (Not initiated yet) */}
                {paypalState === 'idle' && (
                  <div className="paypal-state-box">
                    <p style={{ fontSize: 13.5, color: '#475569', margin: '0 0 12px 0', lineHeight: 1.5 }}>
                      Ready to approve this deal. Click below to initiate a live order via the PayPal Sandbox REST API.
                    </p>
                    <button
                      type="button"
                      className="paypal-action-btn primary"
                      onClick={handleInitiatePayPal}
                    >
                      <CreditCard size={16} />
                      <span>Approve & Initiate PayPal Order (${totalPayable?.toFixed(2)})</span>
                    </button>
                  </div>
                )}

                {/* State 2: Creating Order */}
                {paypalState === 'creating' && (
                  <div className="paypal-state-box loading">
                    <RefreshCw size={18} className="search-btn-spinner" />
                    <span>Communicating with PayPal Sandbox REST API...</span>
                  </div>
                )}

                {/* State 3: Order Created in Sandbox */}
                {paypalState === 'created' && paypalOrder && (
                  <div className="paypal-order-details-card">
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">PayPal Order ID:</span>
                      <code className="paypal-order-code">{paypalOrder.order_id}</code>
                    </div>
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">Status:</span>
                      <span className="paypal-order-status-pill">{paypalOrder.status}</span>
                    </div>
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">Authorized Total:</span>
                      <strong style={{ color: '#0f172a' }}>${paypalOrder.amount.toFixed(2)} {paypalOrder.currency}</strong>
                    </div>

                    <p className="paypal-order-instruction">
                      Order successfully created on PayPal Sandbox. Authorize payment using your Sandbox account, then click <strong>Verify & Capture</strong>.
                    </p>

                    <div className="paypal-order-actions-row">
                      {paypalOrder.approve_url && (
                        <a
                          href={paypalOrder.approve_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="paypal-action-btn gold"
                        >
                          <span>Authorize on PayPal Sandbox</span>
                          <ExternalLink size={14} />
                        </a>
                      )}
                      <button
                        type="button"
                        className="paypal-action-btn capture"
                        onClick={handleCapturePayment}
                      >
                        <Check size={16} />
                        <span>Verify & Capture Payment</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* State 4: Capturing Order */}
                {paypalState === 'capturing' && (
                  <div className="paypal-state-box loading">
                    <RefreshCw size={18} className="search-btn-spinner" />
                    <span>Verifying and capturing payment with PayPal Sandbox...</span>
                  </div>
                )}

                {/* State 5: Capture Success (Real COMPLETED) */}
                {paypalState === 'captured' && captureResult && (
                  <div className="paypal-success-card">
                    <div className="paypal-success-header">
                      <CheckCircle2 size={22} color="#16a34a" />
                      <strong style={{ color: '#166534', fontSize: 15 }}>Payment Confirmed & Captured!</strong>
                    </div>
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">Capture ID:</span>
                      <code className="paypal-order-code">{captureResult.capture_id}</code>
                    </div>
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">Captured Amount:</span>
                      <strong style={{ color: '#166534' }}>${captureResult.amount?.toFixed(2)} {captureResult.currency}</strong>
                    </div>
                    {captureResult.payer_email && (
                      <div className="paypal-order-meta-row">
                        <span className="paypal-order-label">Payer:</span>
                        <span>{captureResult.payer_email}</span>
                      </div>
                    )}
                    <p style={{ fontSize: 13, color: '#15803d', margin: '8px 0 0 0' }}>
                      {captureResult.message}
                    </p>
                  </div>
                )}

                {/* State 6: Order Not Yet Approved by Buyer */}
                {paypalState === 'not_approved' && (
                  <div className="paypal-warning-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#b45309', fontWeight: 700 }}>
                      <AlertCircle size={18} />
                      <span>PayPal Sandbox Notice: Order Not Yet Approved</span>
                    </div>
                    <p style={{ fontSize: 13, color: '#78350f', margin: '6px 0 10px 0', lineHeight: 1.5 }}>
                      {captureResult?.message || 'Payer has not yet approved the order in the PayPal Sandbox window.'}
                    </p>
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                      {paypalOrder?.approve_url && (
                        <a
                          href={paypalOrder.approve_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="paypal-action-btn gold"
                          style={{ fontSize: 13, padding: '8px 14px' }}
                        >
                          <span>Open Sandbox Approval Window</span>
                          <ExternalLink size={13} />
                        </a>
                      )}
                      <button
                        type="button"
                        className="paypal-action-btn capture"
                        style={{ fontSize: 13, padding: '8px 14px' }}
                        onClick={handleCapturePayment}
                      >
                        <RefreshCw size={13} />
                        <span>Re-Check Capture</span>
                      </button>
                    </div>
                  </div>
                )}

                {/* State 7: Error State */}
                {paypalState === 'error' && (
                  <div className="paypal-error-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#991b1b', fontWeight: 700 }}>
                      <AlertTriangle size={18} />
                      <span>PayPal Sandbox API Error</span>
                    </div>
                    <p style={{ fontSize: 13, color: '#7f1d1d', margin: '6px 0 10px 0' }}>
                      {paypalErrorMessage}
                    </p>
                    <button
                      type="button"
                      className="paypal-action-btn primary"
                      style={{ fontSize: 13, padding: '8px 14px' }}
                      onClick={handleInitiatePayPal}
                    >
                      <RefreshCw size={13} />
                      <span>Retry PayPal Checkout</span>
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="deal-review-footer">
              <button
                type="button"
                className="modal-start-btn"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => setShowReviewDeal(false)}
              >
                <Check size={16} />
                <span>Return to Transcript</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
