const express = require('express');
const router = express.Router();
const db = require('../db');
const { sendTelegramNotification } = require('../telegram');

/**
 * Verify shop_id in webhook payload matches expected SHOP_ID.
 * Не блокируем — только логируем несоответствие.
 */
function checkShopId(payload) {
  const shopId = String(payload.shop_id || '').trim();
  const expected = String(process.env.SHOP_ID || '').trim();
  if (expected && shopId && shopId !== expected) {
    console.warn(`[Webhook] shop_id mismatch: got='${shopId}' expected='${expected}'`);
  }
}

/**
 * POST /webhook/payment
 * Universal payment webhook called by payment systems.
 * 
 * Supported formats:
 *   - Generic: { order_id, amount, user_id, status: "paid" }
 *   - Payme:   { order_id, amount, customer_id, status: "paid" }
 *   - Simple:  { merchant_trans_id, amount, user_id }
 */
router.post('/webhook/payment', async (req, res) => {
  try {
    const payload = req.body;
    console.log('[Webhook] Received:', JSON.stringify(payload).substring(0, 300));

    // Проверка shop_id (не блокируем)
    checkShopId(payload);

    // Check if this is a successful payment
    const rawStatus = String(payload.status || '').toLowerCase();
    const isPaid = ['paid', 'success', 'completed', '1', 'true'].includes(rawStatus);

    if (!isPaid) {
      console.log('[Webhook] Ignored — status not success:', rawStatus);
      return res.json({ ok: true, message: 'ignored' });
    }

    // Extract payment fields
    let order_id = payload.order_id || payload.merchant_trans_id || null;
    let amount = payload.amount || payload.sum || payload.total || null;
    let user_id = payload.user_id || payload.telegram_id || payload.customer_id || null;

    // Parse amount (may be string "50000.00")
    if (amount !== null) {
      amount = Math.round(parseFloat(String(amount)));
    }

    if (!order_id || amount === null || isNaN(amount) || amount <= 0) {
      console.log('[Webhook] Missing/invalid fields:', { order_id, amount });
      return res.status(400).json({ ok: false, error: 'Invalid order_id or amount' });
    }

    // Resolve user from order if not provided
    let resolvedUserId = user_id ? parseInt(user_id) : null;
    if (!resolvedUserId) {
      const order = await db.getOrderByExternalId(order_id);
      if (order) {
        resolvedUserId = order.telegram_id;
      }
    }

    if (!resolvedUserId) {
      console.log(`[Webhook] No user for order ${order_id} — recording without credit`);
      await db.recordPayment(order_id, null, amount, 'paid',
        JSON.stringify({ source: 'webhook', no_user: true, payload }));
      return res.json({ ok: true, message: 'recorded without user' });
    }

    // Record payment (prevents duplicates)
    const inserted = await db.recordPayment(order_id, resolvedUserId, amount, 'paid',
      JSON.stringify({ source: 'webhook', payload }));

    if (!inserted) {
      console.log(`[Webhook] Payment ${order_id} already processed`);
      return res.json({ ok: true, message: 'already processed' });
    }

    // Credit balance
    const newBalance = await db.addBalance(resolvedUserId, amount);
    await db.updateOrderStatus(order_id, 'completed');

    // Send Telegram notification
    await sendTelegramNotification(resolvedUserId, amount, newBalance);

    console.log(`[Webhook] Success: order=${order_id} user=${resolvedUserId} amount=${amount}`);
    res.json({ ok: true, message: 'Payment processed' });

  } catch (err) {
    console.error('[Webhook] Error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

/**
 * GET /webhook/payment
 * Health check endpoint (payment systems verify URL with GET)
 */
router.get('/webhook/payment', (req, res) => {
  res.json({ ok: true, service: 'StarPayUz', message: 'Webhook active' });
});

/**
 * POST /webhook/click
 * Click UZ specific webhook handler.
 * Click sends: action=0 (prepare) then action=1 (complete)
 */
router.post('/webhook/click', async (req, res) => {
  try {
    const payload = req.body;
    const action = parseInt(payload.action) || 0;
    const orderId = payload.merchant_trans_id || '';
    const clickTransId = payload.click_trans_id || '';
    
    console.log(`[Click] Received action=${action} order=${orderId} click_trans_id=${clickTransId}`);

    if (action === 0) {
      // PREPARE: verify order exists and amount matches
      const order = await db.getOrderByExternalId(orderId);
      
      if (!order) {
        console.log(`[Click] Order not found: ${orderId}`);
        return res.json({
          click_trans_id: clickTransId,
          merchant_trans_id: orderId,
          error: -1,
          error_note: 'Order not found'
        });
      }
      
      // Check amount matches
      const clickAmount = Math.round(parseFloat(String(payload.amount || '0')));
      if (order.amount !== null && clickAmount !== order.amount) {
        console.log(`[Click] Amount mismatch: expected=${order.amount} got=${clickAmount}`);
        return res.json({
          click_trans_id: clickTransId,
          merchant_trans_id: orderId,
          click_paydoc_id: payload.click_paydoc_id || null,
          error: -2,
          error_note: 'Insufficient amount'
        });
      }

      return res.json({
        click_trans_id: clickTransId,
        merchant_trans_id: orderId,
        click_paydoc_id: payload.click_paydoc_id || null,
        error: 0,
        error_note: 'Success'
      });
    }

    if (action === 1) {
      // COMPLETE: process payment
      const error = parseInt(payload.error) || -1;
      
      if (error !== 0) {
        console.log(`[Click] Payment failed: error=${error}`);
        return res.json({
          click_trans_id: clickTransId,
          merchant_trans_id: orderId,
          click_paydoc_id: payload.click_paydoc_id || null,
          error: error,
          error_note: 'Payment failed'
        });
      }

      const amount = Math.round(parseFloat(String(payload.amount || '0')));
      const order = await db.getOrderByExternalId(orderId);

      if (!order) {
        return res.json({
          click_trans_id: clickTransId,
          merchant_trans_id: orderId,
          click_paydoc_id: payload.click_paydoc_id || null,
          error: -1,
          error_note: 'Order not found'
        });
      }

      // Validate amount in complete too
      if (order.amount !== null && amount !== order.amount) {
        console.log(`[Click] Complete amount mismatch: expected=${order.amount} got=${amount}`);
        return res.json({
          click_trans_id: clickTransId,
          merchant_trans_id: orderId,
          click_paydoc_id: payload.click_paydoc_id || null,
          error: -2,
          error_note: 'Amount mismatch'
        });
      }

      const userId = order.telegram_id;

      // Record payment
      const inserted = await db.recordPayment(orderId, userId, amount, 'paid',
        JSON.stringify({ source: 'click', click_paydoc_id: payload.click_paydoc_id, payload }));

      if (inserted) {
        const newBalance = await db.addBalance(userId, amount);
        await db.updateOrderStatus(orderId, 'completed');
        await sendTelegramNotification(userId, amount, newBalance);
        console.log(`[Click] Payment processed: order=${orderId} amount=${amount} doc_id=${payload.click_paydoc_id}`);
      }

      return res.json({
        click_trans_id: clickTransId,
        merchant_trans_id: orderId,
        click_paydoc_id: payload.click_paydoc_id || null,
        error: 0,
        error_note: 'Success'
      });
    }

    // Invalid action
    res.json({
      click_trans_id: clickTransId,
      merchant_trans_id: orderId,
      error: -1,
      error_note: 'Invalid action'
    });

  } catch (err) {
    console.error('[Click] Error:', err.message);
    res.json({
      click_trans_id: req.body?.click_trans_id || '',
      merchant_trans_id: req.body?.merchant_trans_id || '',
      error: -1,
      error_note: 'Internal error'
    });
  }
});

module.exports = router;
