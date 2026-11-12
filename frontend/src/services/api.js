import axios from 'axios';

// Base URL for the FastAPI backend service
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Reusable Axios HTTP client pre-configured with the backend base URL,
 * timeout boundaries, and standard request headers.
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000, // 45 seconds to support multi-round AI agent negotiation
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Checks the operational health of the NEGOZA FastAPI backend service.
 * Calls: GET /api/health
 *
 * @returns {Promise<{ isHealthy: boolean, data?: object }>}
 */
export const checkBackendHealth = async () => {
  try {
    const response = await apiClient.get('/api/health');
    if (response.status === 200 && response.data?.status === 'healthy') {
      return {
        isHealthy: true,
        data: response.data,
      };
    }
    return { isHealthy: false };
  } catch (error) {
    return {
      isHealthy: false,
      error: error.code === 'ECONNABORTED' ? 'Connection timed out' : 'Backend unavailable',
    };
  }
};

/**
 * Submits user targets and product parameters to the NEGOZA Buyer Agent
 * to formulate an autonomous negotiation plan via Gemini.
 * Calls: POST /api/agents/buyer/prepare
 *
 * @param {Object} payload
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export const prepareBuyerAgentPlan = async (payload) => {
  try {
    const response = await apiClient.post('/api/agents/buyer/prepare', payload);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      (error.code === 'ECONNABORTED'
        ? 'Request timed out while preparing negotiation plan.'
        : 'Failed to communicate with Buyer Agent service.');
    return {
      success: false,
      error: typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage),
    };
  }
};

/**
 * Initiates an autonomous agent-to-agent negotiation loop between the Buyer Agent
 * and the Seller Agent via the FastAPI backend.
 * Calls: POST /api/negotiation/start
 *
 * @param {Object} payload
 * @param {string} payload.product_id
 * @param {string} payload.product_name
 * @param {string} [payload.merchant_id]
 * @param {string} [payload.merchant_name]
 * @param {number} payload.advertised_price
 * @param {number} payload.target_price
 * @param {number} [payload.max_price]
 * @param {string} [payload.delivery_preference]
 * @param {string[]} [payload.requirements]
 * @param {number} [payload.max_rounds]
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export const startNegotiation = async (payload) => {
  try {
    const response = await apiClient.post('/api/negotiation/start', payload);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      (error.code === 'ECONNABORTED'
        ? 'Negotiation request timed out. The agents took longer than expected to converge.'
        : 'Failed to communicate with negotiation engine.');
    return {
      success: false,
      error: typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage),
    };
  }
};

/**
 * Searches real-world products and merchant offers via Channel3 through the backend.
 * Calls: GET /api/products/search?q={query}&limit={limit}
 *
 * @param {string} query
 * @param {number} [limit=20]
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export const searchProducts = async (query, limit = 20) => {
  try {
    const response = await apiClient.get('/api/products/search', {
      params: {
        q: query,
        limit,
      },
    });
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      (error.code === 'ECONNABORTED'
        ? 'Product search request timed out.'
        : 'Failed to retrieve products from discovery service.');
    return {
      success: false,
      error: typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage),
    };
  }
};

/**
 * Initiates an order in PayPal Sandbox for an approved negotiated deal.
 * Calls: POST /api/payments/paypal/orders/create
 *
 * @param {Object} payload
 * @param {string} payload.negotiation_id
 * @param {string} payload.product_name
 * @param {number} payload.amount
 * @param {string} [payload.currency='USD']
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export const createPayPalOrder = async (payload) => {
  try {
    const response = await apiClient.post('/api/payments/paypal/orders/create', payload);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      (error.code === 'ECONNABORTED'
        ? 'PayPal order creation timed out.'
        : 'Failed to initiate PayPal Sandbox checkout.');
    return {
      success: false,
      error: typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage),
    };
  }
};

/**
 * Captures an authorized PayPal Sandbox order.
 * Calls: POST /api/payments/paypal/orders/{orderId}/capture
 *
 * @param {string} orderId
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export const capturePayPalOrder = async (orderId) => {
  try {
    const response = await apiClient.post(`/api/payments/paypal/orders/${orderId}/capture`);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    const errorMessage =
      error.response?.data?.detail ||
      (error.code === 'ECONNABORTED'
        ? 'PayPal capture request timed out.'
        : 'Failed to capture PayPal Sandbox payment.');
    return {
      success: false,
      error: typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage),
    };
  }
};

export default apiClient;
