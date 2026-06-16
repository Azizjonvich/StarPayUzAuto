const { Pool } = require('pg');

let pool = null;

function getPool() {
  if (pool) return pool;
  
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error('DATABASE_URL not set');
  }
  
  pool = new Pool({
    connectionString: databaseUrl,
    ssl: databaseUrl.includes('localhost') ? false : { rejectUnauthorized: false },
    min: 2,
    max: 10,
  });
  
  return pool;
}

async function query(text, params) {
  const client = await getPool().connect();
  try {
    const result = await client.query(text, params);
    return result;
  } finally {
    client.release();
  }
}

async function getPendingOrders() {
  const result = await query(
    `SELECT id, telegram_id, external_id, amount, product_type, status, created_at
     FROM orders
     WHERE product_type = 'topup'
       AND status = 'pending'
     ORDER BY id ASC
     LIMIT 50`
  );
  return result.rows;
}

async function getOrderByExternalId(externalId) {
  const result = await query(
    'SELECT * FROM orders WHERE external_id = $1',
    [externalId]
  );
  return result.rows[0] || null;
}

async function updateOrderStatus(externalId, status) {
  await query(
    'UPDATE orders SET status = $1 WHERE external_id = $2',
    [status, externalId]
  );
}

async function getUser(telegramId) {
  const result = await query(
    'SELECT * FROM users WHERE telegram_id = $1',
    [telegramId]
  );
  return result.rows[0] || null;
}

async function addBalance(telegramId, amount) {
  const result = await query(
    'UPDATE users SET balance = balance + $1 WHERE telegram_id = $2 RETURNING balance',
    [amount, telegramId]
  );
  return result.rows[0] ? result.rows[0].balance : 0;
}

async function recordPayment(shopOrderId, telegramId, amount, status, rawPayload) {
  try {
    await query(
      `INSERT INTO payments (shop_order_id, telegram_id, amount, status, raw_payload)
       VALUES ($1, $2, $3, $4, $5)`,
      [shopOrderId, telegramId, amount, status, rawPayload]
    );
    return true;
  } catch (err) {
    if (err.code === '23505') { // Unique violation
      return false;
    }
    throw err;
  }
}

module.exports = {
  getPool,
  query,
  getPendingOrders,
  getOrderByExternalId,
  updateOrderStatus,
  getUser,
  addBalance,
  recordPayment,
};
