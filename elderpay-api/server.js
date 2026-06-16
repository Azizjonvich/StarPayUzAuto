const express = require('express');
const cors = require('cors');
require('dotenv').config();

const paymentRoutes = require('./routes/payments');
const webhookRoutes = require('./routes/webhooks');
const elderpayRoutes = require('./routes/elderpay');
const paymentPoller = require('./services/paymentPoller');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Logging
app.use((req, res, next) => {
  const ts = new Date().toISOString();
  console.log(`[${ts}] ${req.method} ${req.path}`);
  next();
});

// Root — status page
app.get('/', (req, res) => {
  res.json({
    ok: true,
    service: 'StarPayUz Payment Server',
    version: '2.1.0',
    endpoints: {
      health: 'GET /health',
      elderpay_create: 'POST /api/elderpay/create',
      elderpay_check: 'GET /api/elderpay/check/:order_id',
      elderpay_pending: 'GET /api/elderpay/pending',
      payment_check: 'POST /api/payment/check',
      payment_confirm: 'POST /api/payment/confirm',
      payment_pending: 'GET /api/payment/pending',
      payment_webhook: 'POST /payment/webhook',
      click_webhook: 'POST /webhook/click',
      admin_orders: 'GET /admin/orders',
    },
    timestamp: new Date().toISOString(),
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    ok: true,
    service: 'StarPayUz Payment Server',
    uptime: process.uptime(),
    db_connected: !!db.getPool(),
    timestamp: new Date().toISOString(),
  });
});

// Payment routes
app.use('/api/payment', paymentRoutes);

// ElderPay routes — автоматическое создание и проверка платежей
app.use('/api/elderpay', elderpayRoutes);

// Webhook routes — для приёма уведомлений от платёжных систем
app.use('/', webhookRoutes);

// Admin routes (simple listing)
app.get('/admin/orders', async (req, res) => {
  try {
    const orders = await db.getPendingOrders();
    let html = '<html><head><meta charset="utf-8"><title>Pending Orders</title>';
    html += '<style>body{font-family:sans-serif;max-width:800px;margin:20px auto;padding:0 20px}';
    html += 'table{width:100%;border-collapse:collapse}th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #ddd}';
    html += '.pending{color:orange}.completed{color:green}.cancel{color:red}';
    html += '</style></head><body>';
    html += '<h1>Pending Orders</h1>';
    html += `<p>Total: ${orders.length}</p>`;
    html += '<table><tr><th>ID</th><th>Order ID</th><th>User</th><th>Amount</th><th>Status</th><th>Created</th></tr>';
    
    for (const o of orders) {
      const user = await db.getUser(o.telegram_id);
      html += `<tr>
        <td>${o.id}</td>
        <td><code>${o.external_id}</code></td>
        <td>@${user?.username || o.telegram_id}</td>
        <td>${Number(o.amount).toLocaleString()} so'm</td>
        <td class="${o.status}">${o.status}</td>
        <td>${new Date(o.created_at).toLocaleString()}</td>
      </tr>`;
    }
    
    html += '</table></body></html>';
    res.send(html);
  } catch (err) {
    res.status(500).send('Error: ' + err.message);
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ ok: false, error: 'Not found', path: req.path });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(err.status || 500).json({
    ok: false,
    error: err.message || 'Internal server error',
  });
});

// Start server
async function start() {
  // Test database connection
  try {
    const pool = db.getPool();
    const client = await pool.connect();
    await client.query('SELECT 1');
    client.release();
    console.log('[DB] Connected to PostgreSQL');
  } catch (err) {
    console.error('[DB] Connection failed:', err.message);
  }

  // Start background poller for automatic payment detection
  paymentPoller.start();

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[Server] StarPayUz Payment Server running on port ${PORT}`);
    console.log(`[Server] Pending orders: GET /admin/orders`);
    console.log(`[Server] Confirm payment: POST /api/payment/confirm`);
    console.log(`[Server] ElderPay create: POST /api/elderpay/create`);
    console.log(`[Server] ElderPay check: GET /api/elderpay/check/:order_id`);
    console.log(`[Server] Payment Webhook: POST /payment/webhook (ваша платёжная система)`);
    console.log(`[Server] Webhook: POST /webhook/payment (совместимость)`);
    console.log(`[Server] ✅ Auto-poller ACTIVE — платежи ElderPay проверяются каждые 15 секунд`);
  });
}

start();

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down...');
  process.exit(0);
});
