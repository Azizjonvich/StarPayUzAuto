/**
 * Payment Poller — фоновый опрос ElderPay
 * 
 * Каждые 15 секунд проверяет все pending-заказы через ElderPay API.
 * Если ElderPay обнаружил перевод (status = "paid") — автоматически:
 *   - начисляет баланс пользователю
 *   - обновляет статус заказа
 *   - отправляет Telegram-уведомление
 * 
 * Пользователю НЕ НУЖНО нажимать "To'lovni tekshirish" — всё происходит само.
 */
const db = require('../db');
const elderpay = require('./elderpayClient');
const { sendTelegramNotification } = require('../telegram');

const POLL_INTERVAL_MS = 15000; // 15 секунд

let intervalHandle = null;
let isProcessing = false;

/**
 * Start the payment poller.
 * Called once when the server starts.
 */
function start() {
  if (intervalHandle) {
    console.log('[Poller] Already running');
    return;
  }

  console.log(`[Poller] Starting — checking ElderPay every ${POLL_INTERVAL_MS / 1000}s`);
  intervalHandle = setInterval(pollPendingOrders, POLL_INTERVAL_MS);

  // Run first check immediately
  setImmediate(pollPendingOrders);
}

/**
 * Stop the payment poller.
 */
function stop() {
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = null;
    console.log('[Poller] Stopped');
  }
}

/**
 * Poll all pending orders from the local DB.
 * For each order, check with ElderPay API.
 * If paid — credit balance, update status, send notification.
 */
async function pollPendingOrders() {
  // Prevent overlapping runs if a poll cycle takes longer than the interval
  if (isProcessing) {
    return;
  }

  isProcessing = true;

  try {
    const orders = await db.getPendingOrders();

    if (orders.length === 0) {
      return; // Nothing to check
    }

    console.log(`[Poller] Checking ${orders.length} pending order(s)...`);

    for (const order of orders) {
      try {
        await processOrder(order);
      } catch (err) {
        console.error(`[Poller] Error processing order ${order.external_id}:`, err.message);
      }
    }
  } catch (err) {
    console.error('[Poller] Error fetching pending orders:', err.message);
  } finally {
    isProcessing = false;
  }
}

/**
 * Check a single order with ElderPay and process if paid.
 */
async function processOrder(order) {
  const externalId = order.external_id;

  if (!externalId) {
    console.log(`[Poller] Order ${order.id} has no external_id, skipping`);
    return;
  }

  // Check with ElderPay
  const result = await elderpay.checkOrder(externalId);

  if (!result.paid) {
    return; // Not paid yet — skip
  }

  console.log(`[Poller] ╔═══════════════════════════════════════`);
  console.log(`[Poller] ║  PAYMENT DETECTED!`);
  console.log(`[Poller] ║  Order:     ${externalId}`);
  console.log(`[Poller] ║  User:      ${order.telegram_id}`);
  console.log(`[Poller] ║  Amount:    ${result.amount || order.amount} so'm`);
  console.log(`[Poller] ╚═══════════════════════════════════════`);

  const rawAmount = result.amount || Number(order.amount) || 0;
  const amount = Math.round(parseFloat(String(rawAmount)));
  const telegramId = order.telegram_id;

  // Credit balance
  const newBalance = await db.addBalance(telegramId, amount);

  // Update order status
  await db.updateOrderStatus(externalId, 'completed');

  // Record payment
  await db.recordPayment(
    externalId,
    telegramId,
    amount,
    'paid',
    JSON.stringify({
      source: 'elderpay_poller',
      polled_at: new Date().toISOString(),
    })
  );

  // Send Telegram notification to user
  await sendTelegramNotification(telegramId, amount, newBalance);

  console.log(`[Poller] ✅ Auto-credited: user=${telegramId}, amount=${amount}, new_balance=${newBalance}`);
}

module.exports = { start, stop };
