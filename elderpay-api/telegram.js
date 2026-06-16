const axios = require('axios');

/**
 * Send Telegram notification about successful payment.
 */
async function sendTelegramNotification(userId, amount, newBalance) {
  const botToken = process.env.BOT_TOKEN;
  if (!botToken) {
    console.warn('[Telegram] BOT_TOKEN not set — cannot send notification');
    return;
  }

  const checkEmoji = process.env.CUSTOM_EMOJI_CHECK || '✅';
  const premiumEmoji = process.env.CUSTOM_EMOJI_PREMIUM || '💎';
  const moneyEmoji = process.env.CUSTOM_EMOJI_MONEY || '💰';

  const text = `${checkEmoji} <b>To'lov muvaffaqiyatli qabul qilindi</b>\n\n`
    + `${premiumEmoji} +${Number(amount).toLocaleString()} so'm\n`
    + `${moneyEmoji} Balans: ${Number(newBalance).toLocaleString()} so'm`;

  try {
    await axios.post(
      `https://api.telegram.org/bot${botToken}/sendMessage`,
      {
        chat_id: userId,
        text: text,
        parse_mode: 'HTML',
      },
      { timeout: 10000 }
    );
    console.log(`[Telegram] Notification sent to user ${userId}`);
  } catch (err) {
    console.error(`[Telegram] Failed to notify user ${userId}:`, err.message);
  }
}

/**
 * Send notification to admins about a new pending order.
 */
async function notifyAdmins(userId, username, orderId, amount) {
  const botToken = process.env.BOT_TOKEN;
  if (!botToken) return;

  const adminIds = (process.env.ADMIN_IDS || '').split(',').filter(Boolean);

  const text = `<b>💳 Yangi to'lov so'rovi</b>\n\n`
    + `👤 Foydalanuvchi: @${username || userId} (<code>${userId}</code>)\n`
    + `💰 Summa: ${Number(amount).toLocaleString()} so'm\n`
    + `🆔 Buyurtma: <code>${orderId}</code>\n\n`
    + `<b>Tasdiqlash uchun:</b>\n`
    + `Node.js server: POST /api/payment/confirm\n`
    + `Body: {"order_id": "${orderId}", "admin_secret": "..."}`;

  for (const adminId of adminIds) {
    try {
      await axios.post(
        `https://api.telegram.org/bot${botToken}/sendMessage`,
        {
          chat_id: adminId.trim(),
          text: text,
          parse_mode: 'HTML',
        },
        { timeout: 10000 }
      );
    } catch (err) {
      console.error(`[Telegram] Failed to notify admin ${adminId}:`, err.message);
    }
  }
}

module.exports = { sendTelegramNotification, notifyAdmins };
