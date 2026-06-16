/**
 * Signature Utility — генерация и проверка HMAC-SHA256 подписей
 * для вебхуков платёжных систем (Shop ID / Shop Key).
 *
 * ─── КАК ЭТО РАБОТАЕТ ──────────────────────────────────────────────────
 *
 * 1. Платежная система после успешной оплаты отправляет POST-запрос
 *    на ваш webhook endpoint с телом JSON.
 *
 * 2. В теле запроса присутствуют:
 *    - данные платежа: order_id, amount, user_id, shop_id и т.д.
 *    - поле sign (или signature / hash) — HMAC-SHA256 подпись
 *
 * 3. Алгоритм проверки подписи:
 *    a) Извлекаем все поля, КРОМЕ sign / signature / hash
 *    b) Сортируем ключи по алфавиту
 *    c) Собираем строку: key1=value1&key2=value2&...
 *    d) Вычисляем HMAC-SHA256 от этой строки, используя SHOP_KEY
 *    e) Сравниваем результат с полем sign (case-insensitive)
 *
 * 4. Если подпись верна И статус платежа = "paid":
 *    - Считаем платёж успешным
 *    - Начисляем баланс пользователю
 *    - Обновляем базу данных
 *
 * 5. ВАЖНО:
 *    - Webhook вызывается ТОЛЬКО платёжной системой автоматически
 *    - Пользователь и бот НЕ вызывают этот endpoint
 *    - SHOP_KEY должен оставаться секретным (только на сервере)
 *    - Всегда используйте timingSafeEqual для сравнения подписей
 *
 * ─── ПРИМЕР ИСПОЛЬЗОВАНИЯ ─────────────────────────────────────────────
 *
 *   const crypto = require('crypto');
 *   const { generateSign, verifySignature } = require('./utils/signature');
 *
 *   // Генерация подписи (для тестирования / отладки)
 *   const payload = {
 *     order_id: 'topup_abc123',
 *     amount: 50000,
 *     user_id: 123456789,
 *     shop_id: '665210',
 *   };
 *   const sign = generateSign(payload, 'your-shop-key');
 *
 *   // Проверка подписи (в webhook handler)
 *   const payloadWithSign = { ...payload, sign };
 *   const isValid = verifySignature(payloadWithSign, 'your-shop-key');
 *   // → true
 *
 * ─── ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ─────────────────────────────────────────────
 *
 *   SHOP_ID  — идентификатор магазина (shop_id), опционально
 *   SHOP_KEY — секретный ключ для HMAC-SHA256 (обязателен)
 */

const crypto = require('crypto');

/**
 * Поля, которые исключаются из подписи.
 * Платёжные системы могут называть поле подписи по-разному.
 */
const SIGNATURE_FIELDS = new Set(['sign', 'signature', 'hash']);

/**
 * Проверить, является ли значение простым (строкой или числом).
 * Массивы и объекты не участвуют в подписи напрямую.
 * @param {*} value
 * @returns {boolean}
 */
function isPrimitive(value) {
  return value === null || value === undefined || typeof value !== 'object';
}

/**
 * Генерирует HMAC-SHA256 подпись для переданного payload.
 *
 * @param {Object} payload - тело запроса (БЕЗ поля sign)
 * @param {string} shopKey - секретный ключ магазина (SHOP_KEY)
 * @returns {string} - hex-строка HMAC-SHA256 подписи
 *
 * @example
 *   const sign = generateSign({ order_id: '123', amount: 50000 }, SHOP_KEY);
 */
function generateSign(payload, shopKey) {
  if (!payload || typeof payload !== 'object') {
    throw new TypeError('payload must be a non-null object');
  }
  if (!shopKey || typeof shopKey !== 'string') {
    throw new TypeError('shopKey must be a non-empty string');
  }

  // 1. Берём все поля, кроме sign/signature/hash
  // 2. Оставляем только примитивные значения (строки, числа, булевы)
  const data = {};
  for (const [key, value] of Object.entries(payload)) {
    if (!SIGNATURE_FIELDS.has(key) && isPrimitive(value)) {
      data[key] = value;
    }
  }

  // 3. Сортируем ключи по алфавиту
  // 4. Собираем строку: key1=value1&key2=value2
  const checkString = Object.keys(data)
    .sort()
    .map((k) => `${k}=${data[k]}`)
    .join('&');

  // 5. Вычисляем HMAC-SHA256
  return crypto
    .createHmac('sha256', shopKey)
    .update(checkString, 'utf8')
    .digest('hex');
}

/**
 * Проверяет HMAC-SHA256 подпись в webhook payload.
 *
 * @param {Object} payload - тело webhook-запроса (с полем sign/signature/hash)
 * @param {string} shopKey - секретный ключ магазина (SHOP_KEY)
 * @returns {boolean} - true, если подпись верна
 *
 * @example
 *   const isValid = verifySignature(req.body, process.env.SHOP_KEY);
 *   if (!isValid) return res.status(403).json({ error: 'Invalid signature' });
 */
function verifySignature(payload, shopKey) {
  if (!payload || typeof payload !== 'object') {
    return false;
  }
  if (!shopKey || typeof shopKey !== 'string') {
    return false;
  }

  // Извлекаем поле подписи (поддерживаем разные названия)
  const sign = payload.sign || payload.signature || payload.hash;
  if (!sign) {
    return false;
  }

  // Генерируем ожидаемую подпись
  const expected = generateSign(payload, shopKey);

  // Сравниваем через timingSafeEqual — защита от timing-атак
  const expectedBuf = Buffer.from(expected.toLowerCase(), 'utf8');
  const signBuf = Buffer.from(String(sign).toLowerCase(), 'utf8');

  if (expectedBuf.length !== signBuf.length) {
    return false;
  }

  return crypto.timingSafeEqual(expectedBuf, signBuf);
}

/**
 * Проверяет, что shop_id в payload соответствует ожидаемому.
 * Это дополнительная проверка (не блокирующая) — только логируем несоответствие.
 *
 * @param {Object} payload - тело webhook-запроса
 * @param {string} expectedShopId - ожидаемый SHOP_ID из переменных окружения
 * @returns {boolean} - true, если shop_id совпадает или не указан
 */
function checkShopId(payload, expectedShopId) {
  if (!expectedShopId) {
    return true; // SHOP_ID не настроен — пропускаем проверку
  }

  const actualShopId = String(payload.shop_id || '').trim();
  if (!actualShopId) {
    return true; // В запросе нет shop_id — пропускаем
  }

  const match = actualShopId === String(expectedShopId).trim();
  if (!match) {
    console.warn(`[Signature] shop_id mismatch: got='${actualShopId}' expected='${expectedShopId}'`);
  }
  return match;
}

module.exports = {
  generateSign,
  verifySignature,
  checkShopId,
  SIGNATURE_FIELDS,
};
