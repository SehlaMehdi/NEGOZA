import { Sparkles, Bot, Star, ExternalLink, Tag } from 'lucide-react';

export default function ProductCard({ product, onAddAgent }) {
  const {
    name,
    merchant,
    category,
    originalPrice,
    advertisedPrice,
    rating,
    reviewsCount,
    image,
    description,
    productUrl,
    product_url,
    brand,
  } = product;

  const resolvedUrl = productUrl || product_url;
  const safeAdvertised = Number(advertisedPrice || 0);

  // Strictly authentic pricing: only show original price and discount if original > advertised
  const safeOriginal = originalPrice ? Number(originalPrice) : null;
  const hasAuthenticDiscount = safeOriginal !== null && safeOriginal > safeAdvertised;
  const discountAmount = hasAuthenticDiscount ? safeOriginal - safeAdvertised : 0;
  const discountPercent = hasAuthenticDiscount && safeOriginal > 0 
    ? Math.round((discountAmount / safeOriginal) * 100) 
    : 0;

  // Clean merchant initials for avatar
  const merchantInitial = (merchant || 'M').charAt(0).toUpperCase();

  // Distinguish whether product came from live Channel3 catalog or curated fallback
  const isCuratedFallback = typeof product.id === 'string' && product.id.startsWith('prod-');

  return (
    <article className="social-post-card" aria-label={`Sponsored product post: ${name}`}>
      {/* 1. Post Header: Merchant Identity & Sponsored Tag */}
      <div className="post-header">
        <div className="post-merchant-profile">
          <div className="merchant-avatar" aria-hidden="true">
            {merchantInitial}
          </div>
          <div className="merchant-meta">
            <div className="merchant-name-line">
              <span className="post-merchant-name">{merchant}</span>
              {brand && brand.toLowerCase() !== merchant.toLowerCase() && (
                <span className="post-brand-tag">by {brand}</span>
              )}
            </div>
            <div className="post-subline">
              <span className="post-sponsored-pill">
                <Sparkles size={11} className="sponsored-sparkle-icon" />
                <span>Sponsored</span>
              </span>
              <span className="post-meta-dot">&bull;</span>
              <span className="post-source-label">
                {isCuratedFallback ? 'Curated Post' : 'Retailer Offer'}
              </span>
            </div>
          </div>
        </div>

        {/* External Store Link (if authentic URL is available) */}
        {resolvedUrl && (
          <a
            href={resolvedUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="post-store-link"
            title={`Visit ${merchant} store for ${name}`}
          >
            <span>Visit Store</span>
            <ExternalLink size={13} />
          </a>
        )}
      </div>

      {/* 2. Post Media: High-Impact Product Imagery */}
      <div className="post-media-container">
        <img 
          src={image || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'} 
          alt={name} 
          className="post-product-image" 
          loading="lazy"
          onError={(e) => {
            e.target.onerror = null;
            e.target.src = 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80';
          }}
        />

        {/* Authentic Discount Overlay (ONLY when verified original price is greater than advertised price) */}
        {hasAuthenticDiscount && (
          <div className="post-discount-badge" aria-label={`Save $${discountAmount.toFixed(0)} (${discountPercent}% off)`}>
            <span>Save ${discountAmount.toFixed(0)}</span>
            <span className="post-discount-pct">({discountPercent}% off)</span>
          </div>
        )}
      </div>

      {/* 3. Post Content: Title, Description & Authentic Specifications */}
      <div className="post-content-body">
        {/* Category & Authentic Rating Row */}
        <div className="post-tags-row">
          {category && (
            <span className="post-category-tag">
              <Tag size={12} className="tag-icon" />
              <span>{category}</span>
            </span>
          )}
          {rating != null && (
            <span className="post-rating-tag" title={`Customer Rating: ${rating.toFixed(1)}`}>
              <Star size={13} className="star-icon" fill="currentColor" />
              <span>{rating.toFixed(1)}</span>
              {reviewsCount != null && (
                <span className="reviews-count">({reviewsCount})</span>
              )}
            </span>
          )}
        </div>

        {/* Product Title */}
        <h2 className="post-product-title" title={name}>
          {name}
        </h2>

        {/* Product Narrative Description */}
        {description && (
          <p className="post-product-description">
            {description}
          </p>
        )}

        {/* 4. Pricing & Primary CTA Action Bar */}
        <div className="post-action-bar">
          <div className="post-price-block">
            <span className="post-price-label">Advertised Price</span>
            <div className="post-price-values">
              <span className="post-current-price">${safeAdvertised.toFixed(2)}</span>
              {hasAuthenticDiscount && (
                <span className="post-original-price">${safeOriginal.toFixed(2)}</span>
              )}
            </div>
          </div>

          <button
            type="button"
            className="post-add-agent-btn"
            onClick={() => onAddAgent(product)}
            aria-label={`Add my Agent to negotiate deal for ${name}`}
          >
            <div className="post-agent-btn-main">
              <Bot size={18} className="post-btn-bot-icon" />
              <span className="post-btn-label">Add my Agent</span>
            </div>
            <span className="post-btn-badge">Negotiate Deal</span>
          </button>
        </div>
      </div>
    </article>
  );
}
