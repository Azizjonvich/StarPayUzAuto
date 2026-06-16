/**
 * ElderPay API Client
 * 
 * ElderPay — платёжный сервис, который:
 * 1. Принимает запрос на создание заказа → возвращает order_id
 * 2. Сам детектит переводы на карту по номеру заказа
 * 3. По запросу check возвращает статус платежа (paid/pending/cancel)
 * 
 * API: https://elder.uz/api
 * Формат: application/x-www-form-urlencoded
 */
const axios = require('axios');

const API_URL = process.env.ELDERPAY_API_URL || 'https://69fa3b8bc0078.myxvest2.ru/api';
const SHOP_ID = process.env.ELDERPAY_SHOP_ID || process.env.SHOP_ID || '';
const SHOP_KEY = process.env.ELDERPAY_SHOP_KEY || process.env.SHOP_KEY || '';
const CARD_NUMBER = process.env.CARD_NUMBER || '9860 1801 0171 2578';
const CARD_OWNER = process.env.CARD_OWNER || 'Isxakova A.';

/**
 * Create a payment order via ElderPay.
 * 
 * @param {number} amount - Amount in UZS
 * @param {number} [over=10] - Overpayment tolerance percentage
 * @returns {Promise<{success: boolean, order_id?: string, error?: string}>}
 */
async function createOrder(amount, over = 10) {
  console.log(`[ElderPay] Creating order: amount=${amount}, over=${over}`);
  console.log(`[ElderPay] API_URL=${API_URL}, SHOP_ID=${SHOP_ID}`);

  // First attempt
  let result = await _callElderPay({
    method: 'create',
    shop_id: SHOP_ID,
    shop_key: SHOP_KEY,
    amount: amount,
    over: over,
  });

  // Если ошибка — ретраим с увеличенной суммой (до 200 попыток)
  if (result.status === 'error') {
    console.log(`[ElderPay] Initial create failed, starting retry...`);
    let retryAmount = amount + 1;
    let retryResult;

    for (let i = 0; i < 200; i++) {
      retryResult = await _callElderPay({
        method: 'create',
        shop_id: SHOP_ID,
        shop_key: SHOP_KEY,
        amount: retryAmount,
        over: over,
      });

      console.log(`[ElderPay] Retry ${i + 1}: amount=${retryAmount}, status=${retryResult.status}`);

      if (retryResult.status !== 'error') {
        console.log(`[ElderPay] Retry succeeded at attempt ${i + 1}`);
        return {
          success: true,
          order_id: retryResult.order,
          amount: retryAmount,
        };
      }
      retryAmount++;
    }

    console.error(`[ElderPay] All retries failed`);
    return { success: false, error: retryResult?.message || 'ElderPay create failed after retries' };
  }

  // Success on first try
  if (!result.order) {
    console.error(`[ElderPay] No order_id in response:`, JSON.stringify(result));
    return { success: false, error: 'No order_id returned' };
  }

  console.log(`[ElderPay] Order created: ${result.order}, amount=${amount}`);
  return {
    success: true,
    order_id: result.order,
    amount: amount,
  };
}

/**
 * Check payment status via ElderPay.
 * 
 * @param {string} orderId - ElderPay order ID
 * @returns {Promise<{status: string, amount?: number, paid: boolean}>}
 *   status: "paid" | "pending" | "cancel" | "error"
 */
async function checkOrder(orderId) {
  console.log(`[ElderPay] Checking order: ${orderId}`);

  const result = await _callElderPay({
    method: 'check',
    order: orderId,
    shop_id: SHOP_ID,
    shop_key: SHOP_KEY,
  });

  console.log(`[ElderPay] Check response:`, JSON.stringify(result));

  if (!result || result.status === 'error') {
    return { status: 'pending', paid: false };
  }

  // ElderPay returns data.status in result.data
  const orderData = result.data || result;
  const status = orderData.status || 'pending'; // paid | pending | cancel

  return {
    status: status,
    amount: orderData.amount || result.amount || null,
    paid: status === 'paid',
  };
}

/**
 * Low-level call to ElderPay API.
 * All requests are POST with application/x-www-form-urlencoded.
 * 
 * @param {Object} params - URL-encoded params
 * @returns {Promise<Object>} Parsed JSON response
 */
async function _callElderPay(params) {
  try {
    const response = await axios.post(API_URL, new URLSearchParams(params), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      timeout: 10000,
    });
    return response.data;
  } catch (err) {
    // ElderPay may return non-2xx for errors
    return err.response?.data || { status: 'error', message: err.message };
  }
}

module.exports = {
  createOrder,
  checkOrder,
  CARD_NUMBER,
  CARD_OWNER,
};
