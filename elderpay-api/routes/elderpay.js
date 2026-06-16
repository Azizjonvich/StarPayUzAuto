const express = require('express');
const router = express.Router();
const db = require('../db');
const { sendTelegramNotification } = require('../telegram');
const elderpay = require('../services/elderpayClient');

/**
 * POST /api/elderpay/create
 * Create a payment order via ElderPay API.
 * 
 * Body: { telegram_id, amount }
 * Returns: { success, data: { order_id, card_number, card_owner, amount, expires_in } }
 */
router.post('/create', async (req, res) => {
  try {
    const { telegram_id, amount } = req.body;

    if (!telegram_id || !amount) {
      return res.status(422).json({ success: false, error: 'telegram_id and amount required' });
    }

    const amountInt = parseInt(amount);
    if (amountInt < 1000 || amountInt > 10000000) {
      return res.status(422).json({
        success: false,
        error: 'Amount must be between 1000 and 10000000',
      });
    }

    console.log(`[ElderPay] Creating order: telegram_id=${telegram_id}, amount=${amountInt}`);

    // Create order via ElderPay API
    const elderResult = await elderpay.createOrder(amountInt);

    if (!elderResult.success) {
      console.error(`[ElderPay] Create failed:`, elderResult.error);
      return res.status(400).json({ success: false, error: elderResult.error || 'ElderPay error' });
    }

    const actualAmount = elderResult.amount || amountInt;
    const orderId = elderResult.order_id;

    console.log(`[ElderPay] Order created: ${orderId}, amount=${actualAmount}`);

    // Save order in local DB
    await db.query(
      `INSERT INTO orders (telegram_id, external_id, product_type, amount, status, created_at)
       VALUES ($1, $2, 'topup', $3, 'pending', NOW())`,
      [telegram_id, orderId, actualAmount]
    );

    res.json({
      success: true,
      data: {
        order_id: orderId,
        amount: actualAmount,
        card_number: elderpay.CARD_NUMBER,
        card_owner: elderpay.CARD_OWNER,
        expires_in: 300, // 5 minutes
      },
    });

  } catch (err) {
    console.error('[ElderPay] Create error:', err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * GET /api/elderpay/check/:order_id
 * Check payment status via ElderPay API.
 * If paid — credits user balance automatically.
 */
router.get('/check/:order_id', async (req, res) => {
  try {
    const { order_id } = req.params;

    console.log(`[ElderPay] Check request: order=${order_id}`);

    // Check with ElderPay API
    const elderResult = await elderpay.checkOrder(order_id);

    console.log(`[ElderPay] Check result:`, JSON.stringify(elderResult));

    if (!elderResult.paid) {
      // Not paid yet
      return res.json({
        success: true,
        data: {
          order_id,
          status: elderResult.status || 'pending',
          paid: false,
        },
      });
    }

    // Payment is confirmed as paid by ElderPay
    // Find the order in local DB
    const order = await db.getOrderByExternalId(order_id);

    if (!order) {
      console.log(`[ElderPay] Order ${order_id} not found in local DB`);
      return res.json({
        success: true,
        data: { order_id, status: 'paid', paid: true },
      });
    }

    if (order.status === 'completed') {
      // Already processed
      return res.json({
        success: true,
        data: { order_id, status: 'paid', paid: true, already_credited: true },
      });
    }

    // Credit balance
    const user_id = order.telegram_id;
    const rawAmount = elderResult.amount || Number(order.amount) || 0;
    const amount = Math.round(parseFloat(String(rawAmount)));

    const newBalance = await db.addBalance(user_id, amount);
    await db.updateOrderStatus(order_id, 'completed');

    // Record payment in payments table
    await db.recordPayment(
      order_id,
      user_id,
      amount,
      'paid',
      JSON.stringify({ source: 'elderpay_check', checked_at: new Date().toISOString() })
    );

    // Send Telegram notification
    await sendTelegramNotification(user_id, amount, newBalance);

    console.log(`[ElderPay] Payment confirmed: order=${order_id} user=${user_id} amount=${amount}`);

    res.json({
      success: true,
      data: {
        order_id,
        status: 'paid',
        paid: true,
        amount,
        new_balance: newBalance,
      },
    });

  } catch (err) {
    console.error('[ElderPay] Check error:', err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * GET /api/elderpay/pending
 * Returns all pending payments (for bot recovery on restart)
 */
router.get('/pending', async (req, res) => {
  try {
    const orders = await db.getPendingOrders();
    const payments = orders.map(o => ({
      provider_transaction_id: o.external_id,
      telegram_id: o.telegram_id,
      amount_uzs: o.amount,
      created_at: o.created_at,
    }));

    res.json({ success: true, data: payments });
  } catch (err) {
    console.error('[ElderPay] Pending error:', err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
