import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { 
  Search, 
  X, 
  SlidersHorizontal, 
  Sparkles, 
  RefreshCw, 
  AlertCircle, 
  Layers, 
  Globe,
  Bot,
  ShieldCheck,
  Zap
} from 'lucide-react';
import ProductCard from './ProductCard';
import AgentActivationModal from './AgentActivationModal';
import { searchProducts } from '../services/api';
import { PRODUCTS as CURATED_PRODUCTS, CATEGORIES } from '../data/products';

export default function DiscoverFeed({
  agentSettings,
  onNegotiationComplete,
  onUpdateDealPayment
}) {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('smartwatch');
  const [activeProductForAgent, setActiveProductForAgent] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const searchInputRef = useRef(null);

  // Channel3 API State
  const [channelProducts, setChannelProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchError, setSearchError] = useState(null);
  const [dataSource, setDataSource] = useState('channel3'); // 'channel3' | 'fallback'

  // Fetch live products from backend Channel3 endpoint
  const performSearch = useCallback(async (queryText) => {
    const term = (queryText || '').trim();
    if (!term) return;

    setIsLoading(true);
    setSearchError(null);

    const result = await searchProducts(term, 20);

    if (result.success && result.data?.products) {
      setChannelProducts(result.data.products);
      setDataSource('channel3');
    } else {
      setSearchError(result.error || 'Failed to retrieve live products from Channel3.');
    }
    setIsLoading(false);
  }, []);

  // Initial load: search for smartwatches asynchronously on mount
  useEffect(() => {
    let ignore = false;

    searchProducts('smartwatch', 20).then((result) => {
      if (!ignore) {
        if (result.success && result.data?.products) {
          setChannelProducts(result.data.products);
          setDataSource('channel3');
        } else {
          setSearchError(result.error || 'Failed to retrieve live products from Channel3.');
        }
        setIsLoading(false);
      }
    });

    return () => {
      ignore = true;
    };
  }, []);

  // Handle manual search form submit
  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    if (searchQuery.trim()) {
      performSearch(searchQuery.trim());
    }
  };

  // Switch to curated fallback products
  const handleUseFallback = () => {
    setDataSource('fallback');
    setSearchError(null);
  };

  // Switch back to live Channel3 search
  const handleUseChannel3 = () => {
    setDataSource('channel3');
    performSearch(searchQuery || 'smartwatch');
  };

  // Active pool of products depending on current data source
  const activePool = dataSource === 'channel3' ? channelProducts : CURATED_PRODUCTS;

  // Filter products based on search term and category
  const filteredProducts = useMemo(() => {
    return activePool.filter((product) => {
      const matchesCategory = 
        selectedCategory === 'All' || 
        (product.category && product.category.toLowerCase().includes(selectedCategory.toLowerCase()));
      
      const query = searchQuery.trim().toLowerCase();
      const matchesSearch = 
        query === '' ||
        (product.name && product.name.toLowerCase().includes(query)) ||
        (product.merchant && product.merchant.toLowerCase().includes(query)) ||
        (product.description && product.description.toLowerCase().includes(query));

      return matchesCategory && matchesSearch;
    });
  }, [activePool, selectedCategory, searchQuery]);

  const handleOpenAgentModal = (product) => {
    setActiveProductForAgent(product);
    setIsModalOpen(true);
  };

  const handleCloseAgentModal = () => {
    setIsModalOpen(false);
  };

  const handleClearFilters = () => {
    setSelectedCategory('All');
    setSearchQuery('smartwatch');
    performSearch('smartwatch');
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    if (searchInputRef.current) {
      searchInputRef.current.focus();
    }
  };

  return (
    <div className="discover-social-wrapper">
      {/* Social Discovery Header */}
      <header className="discover-social-header">
        <div className="social-header-top">
          <div className="social-eyebrow-row">
            <span className="social-eyebrow-pill">
              <Sparkles size={13} className="sparkle-icon" />
              <span>SPONSORED PRODUCT FEED</span>
            </span>
            {dataSource === 'channel3' ? (
              <span className="source-indicator live">
                <Globe size={12} />
                <span>Channel3 Live Retailer Feed</span>
              </span>
            ) : (
              <span className="source-indicator curated">
                <Layers size={12} />
                <span>Curated Demo Feed</span>
              </span>
            )}
          </div>
          <h1 className="social-feed-title">Discover</h1>
          <p className="social-feed-subtitle">
            Explore sponsored retailer offers in your timeline. Tap <strong>Add my Agent</strong> on any post to autonomously negotiate pricing.
          </p>
        </div>

        {/* Search Bar Form (Preserved Task 3 Fix) */}
        <div className="discover-search-wrapper">
          <form onSubmit={handleSearchSubmit} className="discover-search-form" role="search">
            <div className="search-input-box">
              <Search size={19} className="search-icon" aria-hidden="true" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products or retailers (e.g. smartwatch, headphones, sneakers)..."
                className="search-input"
                aria-label="Search real products"
              />
              {searchQuery && (
                <button 
                  type="button" 
                  onClick={handleClearSearch}
                  className="search-clear-btn"
                  aria-label="Clear search query"
                  title="Clear search"
                >
                  <X size={16} />
                </button>
              )}
            </div>
            <button
              type="submit"
              className="search-submit-btn"
              disabled={isLoading || !searchQuery.trim()}
              aria-label="Search products"
            >
              {isLoading ? (
                <>
                  <RefreshCw size={15} className="search-btn-spinner" />
                  <span>Searching...</span>
                </>
              ) : (
                <span>Search</span>
              )}
            </button>
          </form>
        </div>

        {/* Error State Banner */}
        {searchError && (
          <section className="discover-error-banner" role="alert">
            <div className="discover-error-content">
              <AlertCircle size={20} />
              <div>
                <strong>Channel3 Discovery Notice:</strong> {searchError}
              </div>
            </div>
            <div className="discover-error-actions">
              <button 
                type="button" 
                className="discover-retry-btn"
                onClick={() => performSearch(searchQuery || 'smartwatch')}
              >
                <RefreshCw size={13} />
                <span>Retry Search</span>
              </button>
              <button 
                type="button" 
                className="discover-fallback-btn"
                onClick={handleUseFallback}
              >
                <Layers size={13} />
                <span>View Curated Deals</span>
              </button>
            </div>
          </section>
        )}

        {/* Filter Navigation Bar: Category Pills & Source Switcher */}
        <div className="social-filter-navigation">
          <div className="social-categories-scroll" role="tablist" aria-label="Category filters">
            {CATEGORIES.map((cat) => {
              const count = cat === 'All' 
                ? activePool.length 
                : activePool.filter((p) => p.category && p.category.toLowerCase().includes(cat.toLowerCase())).length;
              const isActive = selectedCategory === cat;

              return (
                <button
                  key={cat}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`social-category-pill ${isActive ? 'active' : ''}`}
                  onClick={() => setSelectedCategory(cat)}
                >
                  <span>{cat}</span>
                  <span className="category-counter">{count}</span>
                </button>
              );
            })}
          </div>

          <div className="social-meta-controls">
            <span className="results-count-text">
              <SlidersHorizontal size={13} />
              <span>
                <strong>{filteredProducts.length}</strong> {dataSource === 'channel3' ? 'retailer' : 'curated'} {filteredProducts.length === 1 ? 'post' : 'posts'}
              </span>
            </span>

            {/* Catalog Source Toggle */}
            <div className="social-source-switcher" role="radiogroup" aria-label="Catalog data source">
              <button
                type="button"
                className={`source-switch-pill ${dataSource === 'channel3' ? 'active' : ''}`}
                onClick={handleUseChannel3}
                title="Browse live Channel3 merchant offers"
              >
                Live Channel3
              </button>
              <button
                type="button"
                className={`source-switch-pill ${dataSource === 'fallback' ? 'active' : ''}`}
                onClick={handleUseFallback}
                title="Browse curated sample catalog"
              >
                Curated
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Social Feed Stream & Desktop Agent Sidebar */}
      <div className="discover-layout-grid">
        {/* Central Vertical Social Feed */}
        <main className="social-feed-center-column">
          {isLoading ? (
            /* Search Loading State */
            <div className="feed-loading-card" role="status" aria-live="polite">
              <div className="feed-spinner-ring"></div>
              <h3 className="feed-loading-heading">Loading Sponsored Product Posts...</h3>
              <p className="feed-loading-text">
                Querying real-time merchant offers for "{searchQuery}".
              </p>
            </div>
          ) : filteredProducts.length > 0 ? (
            /* Vertical Stream of Sponsored Posts */
            <div className="social-feed-stream" role="feed" aria-label="Sponsored product feed">
              {filteredProducts.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onAddAgent={handleOpenAgentModal}
                />
              ))}
            </div>
          ) : (
            /* Empty State */
            <div className="feed-empty-card">
              <div className="feed-empty-icon-wrap">
                <Search size={28} />
              </div>
              <h3 className="feed-empty-title">No sponsored posts match your search</h3>
              <p className="feed-empty-text">
                We couldn't find any products matching "{searchQuery}" in {selectedCategory}. Try another keyword or switch back to our curated catalog.
              </p>
              <div className="feed-empty-actions">
                <button
                  type="button"
                  className="feed-empty-btn primary"
                  onClick={handleClearFilters}
                >
                  Search Smartwatches
                </button>
                {dataSource === 'channel3' && (
                  <button
                    type="button"
                    className="feed-empty-btn secondary"
                    onClick={handleUseFallback}
                  >
                    View Curated Deals
                  </button>
                )}
              </div>
            </div>
          )}
        </main>

        {/* Secondary Desktop Sidebar: NEGOZA Agent Status (Desktop >= 1100px only) */}
        <aside className="feed-agent-sidebar" aria-label="NEGOZA Agent Status Panel">
          <div className="sidebar-agent-card">
            <div className="sidebar-agent-header">
              <div className="sidebar-agent-avatar">
                <Bot size={22} />
              </div>
              <div>
                <h3 className="sidebar-agent-name">NEGOZA Buyer Agent</h3>
                <div className="sidebar-agent-status-badge">
                  <span className="status-live-dot"></span>
                  <span>Autonomous Standby</span>
                </div>
              </div>
            </div>

            <p className="sidebar-agent-desc">
              Your AI agent works directly for you. When you find a sponsored post you like, click <strong>Add my Agent</strong> to set your budget ceiling and let the agent negotiate price and terms with the retailer.
            </p>

            <div className="sidebar-specs-list">
              <div className="sidebar-spec-row">
                <span className="spec-label">
                  <Zap size={14} className="spec-icon" />
                  <span>Intelligence</span>
                </span>
                <span className="spec-val">Gemini AI</span>
              </div>
              <div className="sidebar-spec-row">
                <span className="spec-label">
                  <Globe size={14} className="spec-icon" />
                  <span>Discovery</span>
                </span>
                <span className="spec-val">Channel3 Catalog</span>
              </div>
              <div className="sidebar-spec-row">
                <span className="spec-label">
                  <ShieldCheck size={14} className="spec-icon" />
                  <span>Checkout</span>
                </span>
                <span className="spec-val">PayPal Sandbox</span>
              </div>
            </div>

            <div className="sidebar-agent-tip">
              <Sparkles size={14} className="tip-sparkle" />
              <span>
                Tip: Target 10%–20% below list price for optimal agent negotiation success.
              </span>
            </div>
          </div>
        </aside>
      </div>

      {/* Agent Activation Modal Component */}
      <AgentActivationModal
        key={activeProductForAgent?.id || 'none'}
        product={activeProductForAgent}
        isOpen={isModalOpen}
        onClose={handleCloseAgentModal}
        agentSettings={agentSettings}
        onNegotiationComplete={onNegotiationComplete}
        onUpdateDealPayment={onUpdateDealPayment}
      />
    </div>
  );
}
