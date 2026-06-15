const axios = require('axios');
const qs = require('querystring');

const ELDERPAY_API_URL = process.env.ELDERPAY_API_URL || 'https://elder.uz/api';
const SHOP_ID = process.env.ELDERPAY_SHOP_ID;
const SHOP_KEY = process.env.ELDERPAY_SHOP_KEY;
const CARD_NUMBER = process.env.CARD_NUMBER || '9860180101712578';

// In-memory storage for pending orders (в продакшене лучше использовать Redis/DB)
const pendingOrders = new Map();

/**
 * Create payment order in ElderPay
 * POST /api/elderpay/create
 * Body: { amount: 10000, user_id: "123456789", local_order_id: "topup_abc123" }
 */
async function createOrder(req, res) {
  try {
    const { amount, user_id, local_order_id } = req.body;

    if (!amount || amount < 1000) {
      return res.status(400).json({
        ok: false,
        error: 'Invalid amount. Minimum: 1000 UZS'
      });
    }

    if (!SHOP_ID || !SHOP_KEY) {
      return res.status(500).json({
        ok: false,
        error: 'ElderPay credentials not configured'
      });
    }

    // Prepare request data (URL-encoded)
    const params = {
      method: 'create',
      shop_id: SHOP_ID,
      shop_key: SHOP_KEY,
      amount: parseInt(amount),
      over: 10  // Overdraft allowance
    };

    console.log(`[ElderPay] Creating order: amount=${amount} user_id=${user_id} local_order_id=${local_order_id}`);

    // Send request to ElderPay
    const response = await axios.post(
      ELDERPAY_API_URL,
      qs.stringify(params),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        timeout: 30000
      }
    );

    const data = response.data;
    console.log('[ElderPay] Response:', JSON.stringify(data).substring(0, 200));

    // Extract order ID
    let elderPayOrderId = null;
    if (data.order) {
      elderPayOrderId = data.order;
    } else if (data.data && data.data.order) {
      elderPayOrderId = data.data.order;
    }

    if (!elderPayOrderId) {
      console.error('[ElderPay] Order ID not found in response:', data);
      return res.status(500).json({
        ok: false,
        error: 'ElderPay did not return order ID',
        raw_response: data
      });
    }

    // Store in pending orders
    pendingOrders.set(elderPayOrderId, {
      elderpay_order_id: elderPayOrderId,
      local_order_id: local_order_id || elderPayOrderId,
      user_id: user_id,
      amount: parseInt(amount),
      status: 'pending',
      created_at: new Date().toISOString()
    });

    console.log(`[ElderPay] Order created successfully: ${elderPayOrderId}`);

    return res.json({
      ok: true,
      order_id: elderPayOrderId,
      local_order_id: local_order_id,
      card_number: CARD_NUMBER,
      amount: parseInt(amount),
      status: 'pending',
      message: 'Order created successfully'
    });

  } catch (error) {
    console.error('[ElderPay] Create error:', error.message);
    
    if (error.response) {
      console.error('[ElderPay] Response error:', error.response.data);
      return res.status(error.response.status).json({
        ok: false,
        error: error.response.data.message || error.response.data.error || 'ElderPay API error',
        details: error.response.data
      });
    }

    return res.status(500).json({
      ok: false,
      error: error.message || 'Failed to create order'
    });
  }
}

/**
 * Check order status in ElderPay
 * GET /api/elderpay/check/:order_id
 */
async function checkOrder(req, res) {
  try {
    const { order_id } = req.params;

    if (!order_id) {
      return res.status(400).json({
        ok: false,
        error: 'Order ID required'
      });
    }

    if (!SHOP_ID || !SHOP_KEY) {
      return res.status(500).json({
        ok: false,
        error: 'ElderPay credentials not configured'
      });
    }

    // Prepare request data
    const params = {
      method: 'check',
      order: order_id,
      shop_id: SHOP_ID,
      shop_key: SHOP_KEY
    };

    console.log(`[ElderPay] Checking order: ${order_id}`);

    // Send request to ElderPay
    const response = await axios.post(
      ELDERPAY_API_URL,
      qs.stringify(params),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        timeout: 30000
      }
    );

    const data = response.data;
    console.log('[ElderPay] Check response:', JSON.stringify(data).substring(0, 200));

    // Extract status
    let status = 'pending';
    if (data.data && data.data.status) {
      status = data.data.status.toLowerCase().trim();
    } else if (data.status) {
      status = data.status.toLowerCase().trim();
    }

    // Update pending orders
    const orderInfo = pendingOrders.get(order_id);
    if (orderInfo) {
      orderInfo.status = status;
      orderInfo.checked_at = new Date().toISOString();
      
      // Remove from pending if completed or cancelled
      if (status === 'paid' || status === 'cancel') {
        pendingOrders.delete(order_id);
      }
    }

    return res.json({
      ok: true,
      order_id: order_id,
      status: status,
      data: data.data || data,
      order_info: orderInfo
    });

  } catch (error) {
    console.error('[ElderPay] Check error:', error.message);
    
    if (error.response) {
      console.error('[ElderPay] Response error:', error.response.data);
      return res.status(error.response.status).json({
        ok: false,
        error: error.response.data.message || error.response.data.error || 'ElderPay API error',
        details: error.response.data
      });
    }

    return res.status(500).json({
      ok: false,
      error: error.message || 'Failed to check order'
    });
  }
}

/**
 * Get all pending orders
 * GET /api/elderpay/pending
 */
async function getPendingOrders(req, res) {
  try {
    const pending = Array.from(pendingOrders.values());
    
    return res.json({
      ok: true,
      count: pending.length,
      orders: pending
    });
  } catch (error) {
    console.error('[ElderPay] Get pending error:', error.message);
    return res.status(500).json({
      ok: false,
      error: error.message
    });
  }
}

module.exports = {
  createOrder,
  checkOrder,
  getPendingOrders
};
