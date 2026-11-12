import { useState, useEffect } from 'react';
import { 
  X, 
  Bot, 
  Sparkles, 
  DollarSign, 
  ArrowRight, 
  Info, 
  ChevronDown, 
  ChevronUp, 
  Zap
} from 'lucide-react';
import { startNegotiation } from '../services/api';
import NegotiationWorkspace from './NegotiationWorkspace';

export default function AgentActivationModal({ 
  product, 
  isOpen, 
  onClose,
  agentSettings,
  onNegotiationComplete,
  onUpdateDealPayment
}) {
  const discountPct = Number(agentSettings?.targetDiscountPercent) || 15;
  const initialTarget = product ? Math.round(product.advertisedPrice * (1 - discountPct / 100)) : 0;
  const initialMax = product 
    ? (agentSettings?.maxSpendLimit ? Math.min(product.advertisedPrice, Number(agentSettings.maxSpendLimit)) : product.advertisedPrice)
    : 0;

  const [targetBudget, setTargetBudget] = useState(initialTarget);
  const [maxBudget, setMaxBudget] = useState(initialMax);
  const [deliveryPreference, setDeliveryPreference] = useState(agentSettings?.deliveryPreference || 'Free standard delivery');
  const [customRequirements, setCustomRequirements] = useState(agentSettings?.additionalRequirements || '');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Negotiation Engine State
  const [isNegotiationActive, setIsNegotiationActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [negotiationData, setNegotiationData] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Handle ESC key press
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isLoading) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, isLoading]);

  // Lock background body scroll while modal is open
  useEffect(() => {
    if (!isOpen) return;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen]);

  if (!isOpen || !product) return null;

  const numericTarget = Number(targetBudget) || 0;
  const numericMax = Number(maxBudget) || product.advertisedPrice;
  const targetSavings = Math.max(0, product.advertisedPrice - numericTarget);

  const handleQuickBudget = (percent) => {
    const calculated = Math.round(product.advertisedPrice * (1 - percent / 100));
    setTargetBudget(calculated);
  };

  const handleStartNegotiation = async (e) => {
    e.preventDefault();
    if (numericTarget <= 0) return;

    setIsNegotiationActive(true);
    setIsLoading(true);
    setErrorMessage(null);
    setNegotiationData(null);

    const requirementsList = [];
    if (customRequirements.trim()) {
      requirementsList.push(customRequirements.trim());
    }

    const payload = {
      product_id: String(product.id),
      product_name: product.name,
      merchant_name: product.merchant,
      advertised_price: Number(product.advertisedPrice),
      target_price: numericTarget,
      max_price: numericMax >= numericTarget ? numericMax : product.advertisedPrice,
      delivery_preference: deliveryPreference || 'Free standard delivery',
      requirements: requirementsList,
      max_rounds: 5
    };

    const result = await startNegotiation(payload);

    if (result.success && result.data) {
      setNegotiationData(result.data);

      if (onNegotiationComplete) {
        const finalPrice = result.data.final_agreed_price != null ? Number(result.data.final_agreed_price) : null;
        const isFree = (result.data.delivery_terms || '').toLowerCase().includes('free');
        let deliveryFee = 0;
        if (!isFree && result.data.delivery_terms) {
          const match = result.data.delivery_terms.match(/\$([0-9.]+)/);
          deliveryFee = match ? parseFloat(match[1]) : 0;
        }
        const total = finalPrice != null ? finalPrice + deliveryFee : null;

        onNegotiationComplete({
          id: result.data.negotiation_id || `neg-${Date.now()}`,
          negotiation_id: result.data.negotiation_id,
          product: {
            id: product.id,
            name: product.name,
            merchant: product.merchant,
            advertisedPrice: Number(product.advertisedPrice),
            originalPrice: Number(product.originalPrice || product.advertisedPrice),
            image: product.image,
            merchantUrl: product.merchantUrl || ''
          },
          status: result.data.status,
          finalAgreedPrice: finalPrice,
          deliveryTerms: result.data.delivery_terms || 'Free standard delivery',
          deliveryFee,
          totalPayable: total,
          roundsCount: result.data.rounds_completed || 1,
          transcript: result.data.transcript || [],
          summary: result.data.summary || '',
          paymentStatus: 'unpaid',
          paypalOrder: null,
          paypalCapture: null,
          createdAt: new Date().toISOString()
        });
      }
    } else {
      setErrorMessage(result.error || 'Failed to complete agent negotiation. Please verify backend connection.');
    }

    setIsLoading(false);
  };

  const handleResetForm = () => {
    setIsNegotiationActive(false);
    setNegotiationData(null);
    setErrorMessage(null);
  };

  return (
    <div 
      className="modal-backdrop" 
      onClick={!isLoading ? onClose : undefined}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div 
        className={`modal-window ${isNegotiationActive ? 'negotiation-expanded' : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-avatar-badge">
              <Bot size={22} className="modal-bot-icon" />
            </div>
            <div>
              <h2 id="modal-title" className="modal-title">
                {isNegotiationActive ? 'Agent Negotiation Protocol' : 'Activate Buyer Agent'}
              </h2>
              <span className="modal-subtitle">
                {isNegotiationActive ? 'Live Autonomous Offer Exchange' : 'Autonomous Commerce Negotiation'}
              </span>
            </div>
          </div>
          <button 
            type="button" 
            className="modal-close-btn" 
            onClick={onClose}
            aria-label="Close modal"
            disabled={isLoading}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className={`modal-body ${isNegotiationActive ? 'modal-body-negotiation' : ''}`}>
          {/* View Mode 1: Initial Budget Setup Form */}
          {!isNegotiationActive ? (
            <>
              {/* Product Summary Card */}
              <div className="modal-product-summary">
                <img 
                  src={product.image} 
                  alt={product.name} 
                  className="modal-product-img" 
                />
                <div className="modal-product-details">
                  <span className="modal-product-merchant">{product.merchant}</span>
                  <h3 className="modal-product-name">{product.name}</h3>
                  <div className="modal-price-comparison">
                    <span className="modal-current-price">
                      Advertised: <strong>${product.advertisedPrice}</strong>
                    </span>
                    {product.originalPrice > product.advertisedPrice && (
                      <span className="modal-orig-price">
                        Orig. ${product.originalPrice}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <form onSubmit={handleStartNegotiation} className="modal-form">
                {/* Ready Message Banner */}
                <div className="agent-ready-banner">
                  <div className="banner-icon-col">
                    <Sparkles size={18} className="banner-sparkle" />
                  </div>
                  <div className="banner-text-col">
                    <h4 className="banner-headline">Configure Your Buyer Agent</h4>
                    <p className="banner-body">
                      Specify your target budget. Your AI buyer agent will immediately initiate autonomous negotiations with {product.merchant}’s seller agent to secure the best deal.
                    </p>
                  </div>
                </div>

                {/* Target Budget Input */}
                <div className="budget-input-group">
                  <div className="budget-label-row">
                    <label htmlFor="budget-input" className="budget-label">
                      Target Purchase Budget
                    </label>
                    <span className="budget-hint">
                      Desired price to negotiate towards
                    </span>
                  </div>

                  <div className="input-with-adornment">
                    <span className="adornment-icon">
                      <DollarSign size={18} />
                    </span>
                    <input
                      id="budget-input"
                      type="number"
                      min="1"
                      max={product.advertisedPrice}
                      value={targetBudget}
                      onChange={(e) => setTargetBudget(e.target.value)}
                      className="budget-input"
                      placeholder="Enter target price"
                      required
                    />
                  </div>

                  {/* Quick Selection Shortcuts */}
                  <div className="quick-budget-pills">
                    <span className="quick-pills-label">Quick targets:</span>
                    <button 
                      type="button" 
                      className="quick-pill" 
                      onClick={() => handleQuickBudget(10)}
                    >
                      10% off (${Math.round(product.advertisedPrice * 0.90)})
                    </button>
                    <button 
                      type="button" 
                      className="quick-pill" 
                      onClick={() => handleQuickBudget(15)}
                    >
                      15% off (${Math.round(product.advertisedPrice * 0.85)})
                    </button>
                    <button 
                      type="button" 
                      className="quick-pill" 
                      onClick={() => handleQuickBudget(20)}
                    >
                      20% off (${Math.round(product.advertisedPrice * 0.80)})
                    </button>
                  </div>

                  {/* Savings Projection */}
                  {targetSavings > 0 && (
                    <div className="savings-projection">
                      <Info size={14} className="savings-info-icon" />
                      <span>
                        Targeting <strong>${targetSavings}</strong> in savings below list price.
                      </span>
                    </div>
                  )}
                </div>

                {/* Advanced Strategy Options (Collapsible) */}
                <div>
                  <button
                    type="button"
                    className="additional-prefs-toggle"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                  >
                    {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    <span>{showAdvanced ? 'Hide strategy preferences' : 'Customize ceiling & preferences (optional)'}</span>
                  </button>

                  {showAdvanced && (
                    <div className="additional-prefs-panel">
                      <div>
                        <label className="budget-label" style={{ fontSize: 13 }}>
                          Maximum Acceptable Ceiling Price ($)
                        </label>
                        <input
                          type="number"
                          min={numericTarget}
                          max={product.advertisedPrice}
                          value={maxBudget}
                          onChange={(e) => setMaxBudget(e.target.value)}
                          className="pref-input-field"
                          placeholder={`Max acceptable ceiling (e.g. $${product.advertisedPrice})`}
                        />
                      </div>
                      <div>
                        <label className="budget-label" style={{ fontSize: 13 }}>
                          Delivery Preference
                        </label>
                        <input
                          type="text"
                          value={deliveryPreference}
                          onChange={(e) => setDeliveryPreference(e.target.value)}
                          className="pref-input-field"
                          placeholder="e.g. Free standard delivery, Express shipping"
                        />
                      </div>
                      <div>
                        <label className="budget-label" style={{ fontSize: 13 }}>
                          Specific Requirements (optional)
                        </label>
                        <input
                          type="text"
                          value={customRequirements}
                          onChange={(e) => setCustomRequirements(e.target.value)}
                          className="pref-input-field"
                          placeholder="e.g. Include 1-year warranty, Original retail box"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Modal Form Actions */}
                <div className="modal-actions">
                  <button
                    type="button"
                    className="modal-cancel-btn"
                    onClick={onClose}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="modal-start-btn"
                  >
                    <Zap size={17} />
                    <span>Start Negotiation</span>
                    <ArrowRight size={15} />
                  </button>
                </div>
              </form>
            </>
          ) : (
            /* View Mode 2: Live Negotiation Workspace */
            <NegotiationWorkspace
              product={product}
              targetBudget={numericTarget}
              maxBudget={numericMax}
              negotiationData={negotiationData}
              isLoading={isLoading}
              errorMessage={errorMessage}
              onReset={handleResetForm}
              onClose={onClose}
              onUpdateDealPayment={onUpdateDealPayment}
            />
          )}
        </div>
      </div>
    </div>
  );
}
