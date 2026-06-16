const express = require('express');
const router = express.Router();
const db = require('../db');
const { sendTelegramNotification } = require('../telegram');

/**
 * GET /api/payment/pending
 * Get all pending topup orders (for admin to review)
 */
router.get('/pending', async (req, res) => {
  try {
    const orders = await db.getPendingOrders();
    
    // Enrich with user info
    const enriched = [];
    for (const order of orders) {
      const user = await db.getUser(order.telegram_id);
      enriched.push({
        id: order.id,
        order_id: order.external_id,
        user_id: order.telegram_id,
        username: user ? user.username : null,
        amount: order.amount,
        status: order.status,
        created_at: order.created_at,
      });
    }

    res.json({
      ok: true,
      count: enriched.length,
      orders: enriched,
    });
  } catch (err) {
    console.error('[Payments] Get pending error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

/**
 * POST /api/payment/confirm
 * Confirm a payment — admin calls this after seeing money on card
 * Body: { order_id: "topup_abc123", admin_secret: "..." }
 */
router.post('/confirm', async (req, res) => {
  try {
    const { order_id, admin_secret } = req.body;

    if (!order_id) {
      return res.status(400).json({ ok: false, error: 'order_id required' });
    }

    // Verify admin secret
    const expectedSecret = process.env.ADMIN_SECRET;
    if (expectedSecret && admin_secret !== expectedSecret) {
      return res.status(403).json({ ok: false, error: 'Invalid admin secret' });
    }

    // Find order
    const order = await db.getOrderByExternalId(order_id);
    if (!order) {
      return res.status(404).json({ ok: false, error: 'Order not found' });
    }

    if (order.status !== 'pending') {
      return res.json({
        ok: true,
        message: `Order already ${order.status}`,
        status: order.status,
      });
    }

    const user_id = order.telegram_id;
    const amount = order.amount;

    // Credit balance
    const newBalance = await db.addBalance(user_id, amount);

    // Update order status
    await db.updateOrderStatus(order_id, 'completed');

    // Record payment
    await db.recordPayment(
      order_id,
      user_id,
      amount,
      'paid',
      JSON.stringify({ source: 'admin_confirm', confirmed_at: new Date().toISOString() })
    );

    // Send Telegram notification
    await sendTelegramNotification(
      user_id,
      amount,
      newBalance
    );

    console.log(`[Payments] Confirmed: order=${order_id} user=${user_id} amount=${amount} new_balance=${newBalance}`);

    res.json({
      ok: true,
      message: 'Payment confirmed and balance credited',
      user_id,
      amount,
      new_balance: newBalance,
    });

  } catch (err) {
    console.error('[Payments] Confirm error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

/**
 * POST /api/payment/check
 * Check if payment was processed (used by bot)
 * Body: { order_id: "topup_abc123" }
 */
router.post('/check', async (req, res) => {
  try {
    const { order_id } = req.body;

    if (!order_id) {
      return res.status(400).json({ ok: false, error: 'order_id required' });
    }

    const order = await db.getOrderByExternalId(order_id);

    if (!order) {
      return res.json({ ok: true, paid: false, error: 'Order not found' });
    }

    if (order.status === 'completed') {
      return res.json({ ok: true, paid: true, amount: order.amount });
    }

    // Also check payments table
    const result = await db.query(
      "SELECT * FROM payments WHERE shop_order_id = $1 AND status = 'paid'",
      [order_id]
    );

    if (result.rows.length > 0) {
      return res.json({ ok: true, paid: true, amount: result.rows[0].amount });
    }

    res.json({ ok: true, paid: false });

  } catch (err) {
    console.error('[Payments] Check error:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

module.exports = router;
