import { useState } from 'react';
import { 
  Tag, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  FileText, 
  Eye, 
  ExternalLink, 
  CreditCard, 
  ShieldCheck, 
  Lock, 
  RefreshCw, 
  AlertCircle, 
  AlertTriangle, 
  Check, 
  X,
  Store
} from 'lucide-react';
import { createPayPalOrder, capturePayPalOrder } from '../services/api';
import TranscriptModal from './TranscriptModal';

export default function MyDealsView({
  negotiations = [],
  onUpdateDealPayment,
  onNavigateTo
}) {
  const [activeTabFilter, setActiveTabFilter] = useState('pending'); // 'pending' | 'purchased' | 'all'
  const [reviewingDeal, setReviewingDeal] = useState(null);
  const [viewingTranscript, setViewingTranscript] = useState(null);

  // PayPal Sandbox checkout state inside the deal inspector
  const [paypalState, setPaypalState] = useState('idle'); // 'idle' | 'creating' | 'created' | 'capturing' | 'captured' | 'not_approved' | 'error'
  const [paypalErrorMessage, setPaypalErrorMessage] = useState(null);

  // Categorize real deals (zero fabricated data)
  const pendingDeals = negotiations.filter(
    (n) => n.status === 'deal_reached' && n.paymentStatus !== 'purchased'
  );
  const purchasedDeals = negotiations.filter((n) => n.paymentStatus === 'purchased');
  const allDeals = negotiations;

  // Calculate cumulative realized savings
  const totalSavingsDollars = negotiations.reduce((acc, n) => {
    if (n.status === 'deal_reached' && n.finalAgreedPrice != null) {
      const list = Number(n.product?.advertisedPrice || 0);
      const agreed = Number(n.finalAgreedPrice);
      return acc + Math.max(0, list - agreed);
    }
    return acc;
  }, 0);

  // Open the detailed Deal Review modal
  const handleOpenReview = (deal) => {
    setReviewingDeal(deal);
    if (deal.paymentStatus === 'purchased') {
      setPaypalState('captured');
    } else if (deal.paypalOrder) {
      setPaypalState('created');
    } else {
      setPaypalState('idle');
    }
    setPaypalErrorMessage(null);
  };

  const handleCloseReview = () => {
    setReviewingDeal(null);
    setPaypalState('idle');
    setPaypalErrorMessage(null);
  };

  // Initiate PayPal Sandbox Order for this specific deal
  const handleInitiatePayPal = async (deal) => {
    if (!deal) return;
    const finalPrice = Number(deal.finalAgreedPrice || deal.product?.advertisedPrice || 0);
    const isFree = (deal.deliveryTerms || '').toLowerCase().includes('free');
    let deliveryFee = 0;
    if (!isFree && deal.deliveryTerms) {
      const feeMatch = deal.deliveryTerms.match(/\$([0-9.]+)/);
      deliveryFee = feeMatch ? parseFloat(feeMatch[1]) : 0;
    }
    const total = finalPrice + deliveryFee;

    setPaypalState('creating');
    setPaypalErrorMessage(null);

    const payload = {
      negotiation_id: deal.id,
      product_name: deal.product?.name || 'Product',
      amount: total,
      currency: 'USD'
    };

    const res = await createPayPalOrder(payload);
    if (res.success && res.data) {
      // Update persistent deal
      onUpdateDealPayment({
        negotiationId: deal.id,
        paypalOrder: res.data,
        paymentStatus: 'order_created'
      });
      // Update local reviewing deal object
      setReviewingDeal((prev) => ({
        ...prev,
        paypalOrder: res.data,
        paymentStatus: 'order_created'
      }));
      setPaypalState('created');
    } else {
      setPaypalState('error');
      setPaypalErrorMessage(res.error || 'Failed to initiate PayPal Sandbox checkout.');
    }
  };

  // Capture PayPal Sandbox Payment
  const handleCapturePayPal = async (deal) => {
    const orderId = deal?.paypalOrder?.order_id;
    if (!orderId) return;

    setPaypalState('capturing');
    setPaypalErrorMessage(null);

    const res = await capturePayPalOrder(orderId);
    if (res.success && res.data) {
      if (res.data.status === 'COMPLETED') {
        // Confirmed payment capture
        onUpdateDealPayment({
          negotiationId: deal.id,
          paypalCapture: res.data,
          paymentStatus: 'purchased'
        });
        setReviewingDeal((prev) => ({
          ...prev,
          paypalCapture: res.data,
          paymentStatus: 'purchased'
        }));
        setPaypalState('captured');
      } else {
        // e.g. ORDER_NOT_APPROVED
        onUpdateDealPayment({
          negotiationId: deal.id,
          paypalCapture: res.data,
          paymentStatus: 'order_created'
        });
        setReviewingDeal((prev) => ({
          ...prev,
          paypalCapture: res.data,
          paymentStatus: 'order_created'
        }));
        setPaypalState('not_approved');
      }
    } else {
      setPaypalState('error');
      setPaypalErrorMessage(res.error || 'Failed to capture PayPal Sandbox payment.');
    }
  };

  // Determine current active list
  const currentList = 
    activeTabFilter === 'pending'
      ? pendingDeals
      : activeTabFilter === 'purchased'
      ? purchasedDeals
      : allDeals;

  return (
    <div className="deals-pipeline-view">
      {/* 1. Header Section */}
      <section className="deals-hero-banner">
        <div className="deals-hero-content">
          <div className="view-badge">
            <Sparkles size={13} className="badge-icon" />
            <span>DEAL PORTFOLIO & CHECKOUT</span>
          </div>
          <h1 className="deals-view-title">Negotiated Deals & Approvals</h1>
          <p className="deals-view-subtitle">
            Review finalized terms agreed between your Buyer Agent and merchant Seller Agents. Authorize purchases through PayPal Sandbox when you're satisfied with the discount.
          </p>
        </div>

        {/* Financial Metrics Summary (Calculated from Real Data) */}
        <div className="deals-summary-metrics">
          <div className="deal-summary-stat">
            <span className="stat-label">Pending Approval</span>
            <span className="stat-value">{pendingDeals.length} Deals</span>
          </div>
          <div className="deal-summary-stat">
            <span className="stat-label">Purchased Deals</span>
            <span className="stat-value" style={{ color: '#16a34a' }}>{purchasedDeals.length} Paid</span>
          </div>
          <div className="deal-summary-stat">
            <span className="stat-label">Total Realized Savings</span>
            <span className="stat-value" style={{ color: 'var(--accent-purple)' }}>
              ${totalSavingsDollars.toFixed(2)}
            </span>
          </div>
        </div>
      </section>

      {/* 2. Filter Navigation Bar */}
      <div className="deals-filter-bar">
        <div className="deals-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTabFilter === 'pending'}
            className={`deals-tab-btn ${activeTabFilter === 'pending' ? 'active' : ''}`}
            onClick={() => setActiveTabFilter('pending')}
          >
            <span>Pending Approval</span>
            <span className="deals-counter">{pendingDeals.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTabFilter === 'purchased'}
            className={`deals-tab-btn ${activeTabFilter === 'purchased' ? 'active' : ''}`}
            onClick={() => setActiveTabFilter('purchased')}
          >
            <span>Purchased Deals</span>
            <span className="deals-counter">{purchasedDeals.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTabFilter === 'all'}
            className={`deals-tab-btn ${activeTabFilter === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTabFilter('all')}
          >
            <span>All Negotiations</span>
            <span className="deals-counter">{allDeals.length}</span>
          </button>
        </div>
      </div>

      {/* 3. Deal Cards Stream */}
      <div className="deals-cards-stream">
        {currentList.length > 0 ? (
          currentList.map((deal) => {
            const listPrice = Number(deal.product?.advertisedPrice || 0);
            const agreedPrice = deal.finalAgreedPrice != null ? Number(deal.finalAgreedPrice) : null;
            const isFree = (deal.deliveryTerms || '').toLowerCase().includes('free');
            let deliveryFee = 0;
            if (!isFree && deal.deliveryTerms) {
              const feeMatch = deal.deliveryTerms.match(/\$([0-9.]+)/);
              deliveryFee = feeMatch ? parseFloat(feeMatch[1]) : 0;
            }
            const totalPayable = agreedPrice != null ? agreedPrice + deliveryFee : listPrice;
            const savings = agreedPrice != null ? Math.max(0, listPrice - agreedPrice) : 0;
            const savingsPct = listPrice > 0 ? Math.round((savings / listPrice) * 100) : 0;
            const isDeal = deal.status === 'deal_reached';
            const isPurchased = deal.paymentStatus === 'purchased';
            const isOrderCreated = deal.paymentStatus === 'order_created';

            return (
              <article key={deal.id} className="deal-pipeline-card">
                {/* Media Column */}
                <div className="deal-pipeline-media">
                  <img
                    src={deal.product?.image || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'}
                    alt={deal.product?.name}
                    className="deal-pipeline-img"
                  />
                  {savings > 0 && (
                    <div className="deal-pipeline-badge">
                      Save ${savings.toFixed(0)} ({savingsPct}%)
                    </div>
                  )}
                </div>

                {/* Content Column */}
                <div className="deal-pipeline-body">
                  <div className="deal-pipeline-header">
                    <div className="deal-merchant-row">
                      <span className="merchant-name" style={{ fontSize: 13 }}>
                        <Store size={14} className="merchant-icon" />
                        <span>{deal.product?.merchant || 'Retailer Partner'}</span>
                      </span>
                      {deal.product?.productUrl && (
                        <a
                          href={deal.product.productUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="deal-external-link"
                          title="Visit merchant retailer site"
                        >
                          <span>Visit Store</span>
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                    <h3 className="deal-pipeline-title">{deal.product?.name}</h3>
                  </div>

                  {/* Financial Breakdown Grid */}
                  <div className="deal-pipeline-metrics-grid">
                    <div className="pipeline-metric-col">
                      <span className="metric-col-label">Advertised List</span>
                      <span className="metric-col-val">${listPrice.toFixed(2)}</span>
                    </div>
                    <div className="pipeline-metric-col">
                      <span className="metric-col-label">Agreed Price</span>
                      <span className="metric-col-val" style={{ color: isDeal ? '#16a34a' : '#0f172a' }}>
                        {agreedPrice != null ? `$${agreedPrice.toFixed(2)}` : '—'}
                      </span>
                    </div>
                    <div className="pipeline-metric-col">
                      <span className="metric-col-label">Delivery</span>
                      <span className="metric-col-val">
                        {isFree ? 'Free ($0)' : `+$${deliveryFee.toFixed(2)}`}
                      </span>
                    </div>
                    <div className="pipeline-metric-col payable">
                      <span className="metric-col-label">Total Payable</span>
                      <span className="metric-col-val" style={{ color: '#047857', fontWeight: 800 }}>
                        ${totalPayable.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {/* Status Banner Row */}
                  <div className="deal-pipeline-status-row">
                    <div className="deal-status-tags-group">
                      <span className={`turn-action-badge ${deal.status}`}>
                        {deal.status === 'deal_reached' 
                          ? `Agreement Reached (Round ${deal.roundsCount})` 
                          : deal.status.replace('_', ' ')
                        }
                      </span>

                      {/* Payment Status Tag */}
                      {isPurchased ? (
                        <span className="pipeline-payment-pill success">
                          <CheckCircle2 size={13} />
                          <span>Purchased (PayPal Sandbox)</span>
                        </span>
                      ) : isOrderCreated ? (
                        <span className="pipeline-payment-pill warning">
                          <Clock size={13} />
                          <span>PayPal Order Generated</span>
                        </span>
                      ) : isDeal ? (
                        <span className="pipeline-payment-pill pending">
                          <CreditCard size={13} />
                          <span>Awaiting Checkout</span>
                        </span>
                      ) : null}
                    </div>

                    {/* Action Buttons */}
                    <div className="deal-pipeline-actions">
                      <button
                        type="button"
                        className="pipeline-btn secondary"
                        onClick={() => setViewingTranscript(deal)}
                      >
                        <Eye size={14} />
                        <span>View Transcript</span>
                      </button>

                      {isDeal && (
                        <button
                          type="button"
                          className="pipeline-btn primary"
                          onClick={() => handleOpenReview(deal)}
                        >
                          <FileText size={14} />
                          <span>{isPurchased ? 'View Receipt' : 'Review & Pay'}</span>
                          <ArrowRight size={13} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            );
          })
        ) : (
          <div className="empty-deals-box">
            <Tag size={36} className="empty-tag-icon" />
            <h3 style={{ fontSize: 18, fontWeight: 700, margin: '10px 0 6px 0', color: '#0f172a' }}>
              {activeTabFilter === 'pending'
                ? 'No Deals Pending Approval'
                : activeTabFilter === 'purchased'
                ? 'No Purchased Deals Recorded'
                : 'No Negotiations Recorded Yet'}
            </h3>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', maxWidth: 460, margin: '0 auto 16px auto', lineHeight: 1.5 }}>
              {activeTabFilter === 'pending'
                ? 'When your Buyer Agent successfully negotiates an agreed price with a merchant seller agent, the signed deal appears here awaiting your final checkout confirmation.'
                : activeTabFilter === 'purchased'
                ? 'Deals that have completed PayPal Sandbox checkout and have an authentic captured payment transaction ID will appear here.'
                : 'Browse the sponsored feed in Discover and activate your agent on any product to initiate live negotiations.'}
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
      </div>

      {/* 4. Deal Review & PayPal Sandbox Checkout Modal */}
      {reviewingDeal && (
        <div 
          className="deal-review-overlay"
          onClick={handleCloseReview}
          role="dialog"
          aria-modal="true"
          aria-labelledby="deal-inspector-title"
        >
          <div 
            className="deal-review-sheet"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: 580 }}
          >
            <div className="deal-review-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <CheckCircle2 size={22} color="#16a34a" />
                <h3 id="deal-inspector-title" className="deal-review-title">
                  Negotiated Deal Review & Approval
                </h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={handleCloseReview}
                aria-label="Close deal review"
              >
                <X size={18} />
              </button>
            </div>

            <div className="deal-review-body">
              {/* Product Brief */}
              <div className="modal-product-summary">
                <img
                  src={reviewingDeal.product?.image}
                  alt={reviewingDeal.product?.name}
                  className="modal-product-img"
                  style={{ width: 64, height: 64 }}
                />
                <div className="modal-product-details">
                  <span className="modal-product-merchant">{reviewingDeal.product?.merchant}</span>
                  <h4 className="modal-product-name">{reviewingDeal.product?.name}</h4>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Session Ref: <code>{reviewingDeal.id}</code>
                  </span>
                </div>
              </div>

              {/* Itemized Commercial Table */}
              {(() => {
                const list = Number(reviewingDeal.product?.advertisedPrice || 0);
                const agreed = Number(reviewingDeal.finalAgreedPrice || list);
                const isFree = (reviewingDeal.deliveryTerms || '').toLowerCase().includes('free');
                let delFee = 0;
                if (!isFree && reviewingDeal.deliveryTerms) {
                  const m = reviewingDeal.deliveryTerms.match(/\$([0-9.]+)/);
                  delFee = m ? parseFloat(m[1]) : 0;
                }
                const total = agreed + delFee;
                const savings = Math.max(0, list - agreed);
                const savingsPct = list > 0 ? Math.round((savings / list) * 100) : 0;

                return (
                  <div className="deal-invoice-table">
                    <div className="invoice-row">
                      <span>Original Advertised Price</span>
                      <span>${list.toFixed(2)}</span>
                    </div>
                    <div className="invoice-row">
                      <span>Agent Negotiated Discount</span>
                      <span className="invoice-savings-badge">-${savings.toFixed(2)} ({savingsPct}%)</span>
                    </div>
                    <div className="invoice-row">
                      <span>Final Agreed Product Price</span>
                      <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                        ${agreed.toFixed(2)}
                      </span>
                    </div>
                    <div className="invoice-row">
                      <span>Delivery Terms</span>
                      <span>
                        {isFree ? 'Free Delivery ($0.00)' : `Standard Delivery ($${delFee.toFixed(2)})`}
                      </span>
                    </div>
                    <div className="invoice-row total">
                      <span>Total Payable Amount</span>
                      <span className="invoice-value">${total.toFixed(2)}</span>
                    </div>
                  </div>
                );
              })()}

              {/* Verified Autonomous Sign-Off */}
              <div className="deal-security-notice">
                <ShieldCheck size={20} style={{ flexShrink: 0, marginTop: 1, color: '#16a34a' }} />
                <span>
                  <strong>Autonomous deal verified:</strong> Both the Buyer Agent and {reviewingDeal.product?.merchant} Seller Agent have concluded negotiation in Round {reviewingDeal.roundsCount}.
                </span>
              </div>

              {/* PayPal Sandbox Checkout Section */}
              <div className="paypal-checkout-section">
                <div className="paypal-section-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Lock size={16} color="#003087" />
                    <span style={{ fontWeight: 700, color: '#0f172a' }}>PayPal Sandbox Checkout</span>
                  </div>
                  <span className="paypal-badge-sandbox">SANDBOX ENVIRONMENT</span>
                </div>

                {/* State 1: Idle (Not initiated yet) */}
                {paypalState === 'idle' && (
                  <div className="paypal-state-box">
                    <p style={{ fontSize: 13.5, color: '#475569', margin: '0 0 10px 0', lineHeight: 1.5 }}>
                      Approve this deal to initiate a live order with PayPal Sandbox.
                    </p>
                    <button
                      type="button"
                      className="paypal-action-btn primary"
                      onClick={() => handleInitiatePayPal(reviewingDeal)}
                    >
                      <CreditCard size={16} />
                      <span>Approve Deal & Pay with PayPal Sandbox</span>
                    </button>
                  </div>
                )}

                {/* State 2: Creating Order */}
                {paypalState === 'creating' && (
                  <div className="paypal-state-box loading">
                    <RefreshCw size={18} className="search-btn-spinner" />
                    <span>Creating order in PayPal Sandbox REST API...</span>
                  </div>
                )}

                {/* State 3: Order Created in Sandbox */}
                {paypalState === 'created' && reviewingDeal.paypalOrder && (
                  <div className="paypal-order-details-card">
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">PayPal Order ID:</span>
                      <code className="paypal-order-code">{reviewingDeal.paypalOrder.order_id}</code>
                    </div>
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">Status:</span>
                      <span className="paypal-order-status-pill">{reviewingDeal.paypalOrder.status}</span>
                    </div>
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">Total Payable:</span>
                      <strong style={{ color: '#0f172a' }}>
                        ${reviewingDeal.paypalOrder.amount?.toFixed(2)} {reviewingDeal.paypalOrder.currency}
                      </strong>
                    </div>

                    <p className="paypal-order-instruction">
                      Order created on PayPal Sandbox. Authorize payment using your Sandbox account, then click <strong>Verify & Capture</strong>.
                    </p>

                    <div className="paypal-order-actions-row">
                      {reviewingDeal.paypalOrder.approve_url && (
                        <a
                          href={reviewingDeal.paypalOrder.approve_url}
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
                        onClick={() => handleCapturePayPal(reviewingDeal)}
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
                    <span>Verifying authorization with PayPal Sandbox...</span>
                  </div>
                )}

                {/* State 5: Capture Success (Real COMPLETED) */}
                {paypalState === 'captured' && (
                  <div className="paypal-success-card">
                    <div className="paypal-success-header">
                      <CheckCircle2 size={22} color="#16a34a" />
                      <strong style={{ color: '#166534', fontSize: 15 }}>Payment Confirmed & Captured!</strong>
                    </div>
                    {reviewingDeal.paypalCapture?.capture_id && (
                      <div className="paypal-order-meta-row">
                        <span className="paypal-order-label">Capture ID:</span>
                        <code className="paypal-order-code">{reviewingDeal.paypalCapture.capture_id}</code>
                      </div>
                    )}
                    <div className="paypal-order-meta-row">
                      <span className="paypal-order-label">Status:</span>
                      <strong style={{ color: '#166534' }}>COMPLETED</strong>
                    </div>
                    <p style={{ fontSize: 13, color: '#15803d', margin: '6px 0 0 0' }}>
                      Deal finalized and authorized. PayPal Sandbox transaction verified.
                    </p>
                  </div>
                )}

                {/* State 6: Not Yet Approved */}
                {paypalState === 'not_approved' && (
                  <div className="paypal-warning-card">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#b45309', fontWeight: 700 }}>
                      <AlertCircle size={18} />
                      <span>Notice: Order Not Yet Approved in Sandbox</span>
                    </div>
                    <p style={{ fontSize: 13, color: '#78350f', margin: '6px 0 10px 0', lineHeight: 1.5 }}>
                      The PayPal Sandbox API reports this order is not yet approved. Please open the Sandbox authorization window to complete approval, then re-check capture.
                    </p>
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                      {reviewingDeal.paypalOrder?.approve_url && (
                        <a
                          href={reviewingDeal.paypalOrder.approve_url}
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
                        onClick={() => handleCapturePayPal(reviewingDeal)}
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
                      onClick={() => handleInitiatePayPal(reviewingDeal)}
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
                onClick={handleCloseReview}
              >
                <span>Close Deal Inspector</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Transcript Modal Viewer */}
      <TranscriptModal
        negotiation={viewingTranscript}
        isOpen={Boolean(viewingTranscript)}
        onClose={() => setViewingTranscript(null)}
      />
    </div>
  );
}
