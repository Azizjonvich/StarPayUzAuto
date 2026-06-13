# 💳 Настройка автоматического пополнения баланса

## Как это работает

1. **Пользователь** открывает webapp → "Hisobni to'ldirish"
2. **Выбирает сумму** (от 10,000 до 10,000,000 сум)
3. **Выбирает метод оплаты** (Click / Payme / Uzum)
4. **Нажимает "To'lash"** → создается заказ в базе
5. **Открывается платежная страница** Fragment API
6. **После оплаты** Fragment API отправляет webhook на ваш сервер
7. **Webhook обрабатывается** → баланс автоматически пополняется
8. **Пользователь получает уведомление** в боте

---

## 📋 Необходимые настройки

### 1. Зарегистрируйтесь на Fragment API Uz

1. Перейдите на https://fragment-api.uz
2. Зарегистрируйте аккаунт
3. Создайте магазин (Shop)
4. Получите:
   - **API Key** (например: `29de7688acb19ccc97c7bbb7e9e31d69ef26aeb2`)
   - **Shop ID** (например: `665210`)
   - **Shop Key** (для проверки подписи вебхуков)

### 2. Настройте переменные окружения

В Railway добавьте переменные:

```env
# Fragment API
FRAGMENT_API_KEY=29de7688acb19ccc97c7bbb7e9e31d69ef26aeb2
FRAGMENT_API_URL=https://fragment-api.uz/api
SHOP_ID=665210
SHOP_KEY=ваш_shop_key

# Webhook URL (ваш Railway URL)
WEBHOOK_URL=https://worker-production-679d.up.railway.app/webhook/payment
```

### 3. Настройте webhook в Fragment API

В админ панели Fragment API:

1. Откройте настройки магазина
2. Найдите секцию "Webhooks"
3. Добавьте URL: `https://worker-production-679d.up.railway.app/webhook/payment`
4. Выберите события:
   - ✅ Payment Success
   - ✅ Payment Complete
   - ✅ Payment Paid

---

## 🔧 API Endpoints

### Создание платежа

**POST** `/api/payment/create`

```json
{
  "amount": 50000,
  "method": "click",
  "order_id": "topup_1234567890",
  "telegram_id": 8784918764
}
```

**Response:**
```json
{
  "ok": true,
  "payment_url": "https://fragment-api.uz/pay/12345",
  "order_id": "topup_1234567890"
}
```

### Webhook от Fragment API

**POST** `/webhook/payment`

```json
{
  "shop_id": "665210",
  "order_id": "topup_1234567890",
  "amount": 50000,
  "status": "paid",
  "user_id": 8784918764,
  "signature": "abc123...",
  "payment_method": "click",
  "created_at": "2026-06-10T14:30:00Z"
}
```

**Обработка:**
1. Проверка подписи (`verify_shop_signature`)
2. Проверка дубликата (`record_payment`)
3. Пополнение баланса (`add_balance`)
4. Отправка уведомления в Telegram

---

## 📱 Как пользователь пополняет баланс

### Через webapp:

1. Открыть бота → нажать "Webapp"
2. Перейти в профиль (иконка 👤 внизу)
3. Нажать "💰 Hisobni to'ldirish"
4. Выбрать сумму или ввести свою
5. Выбрать метод оплаты (Click/Payme/Uzum)
6. Нажать "To'lash"
7. Оплатить на открывшейся странице
8. Вернуться в бота → баланс уже пополнен! ✅

### Через бота (альтернативный способ):

```
/start → ✨ Hisobni to'ldirish
```

1. Написать сумму (например: 50000)
2. Получить платежную ссылку
3. Оплатить
4. Нажать "✅ To'lovni tekshirish"

---

## 🔐 Безопасность

### Проверка подписи webhook

```python
def verify_shop_signature(payload: dict, shop_key: str) -> bool:
    received_sign = payload.get("signature")
    data = {k: v for k, v in payload.items() if k != "signature"}
    check_string = "&".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    expected = hmac.new(
        shop_key.encode(), 
        check_string.encode(), 
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, received_sign)
```

### Защита от дубликатов

```python
# В базе данных payments.shop_order_id имеет UNIQUE constraint
async def record_payment(...) -> bool:
    try:
        await conn.execute("INSERT INTO payments ...")
        return True  # Первый раз обрабатываем
    except asyncpg.UniqueViolationError:
        return False  # Уже обработан, игнорируем
```

---

## 🧪 Тестирование

### 1. Локальное тестирование (без реального платежа)

Используйте команду admin:

```
/bal 1 +50000
```

Это добавит 50,000 сум на баланс пользователя с StarPayUz ID = 1.

### 2. Тестирование webhook

Используйте curl для имитации webhook:

```bash
curl -X POST https://worker-production-679d.up.railway.app/webhook/payment \
  -H "Content-Type: application/json" \
  -d '{
    "shop_id": "665210",
    "order_id": "test_' $(date +%s) '",
    "amount": 10000,
    "status": "paid",
    "user_id": 8784918764
  }'
```

### 3. Тестирование полного цикла

1. Откройте webapp в браузере с devtools
2. Перейдите на `https://starpayuz-webapp.vercel.app/balance.html`
3. Откройте Network tab
4. Нажмите "To'lash"
5. Проверьте запросы и ответы

---

## 📊 Мониторинг платежей

### Просмотр логов в Railway:

```bash
railway logs
```

Ищите строки:
```
INFO - Payment received: order_id=topup_123, amount=50000
INFO - Balance updated: user_id=8784918764, new_balance=150000
```

### SQL запросы для проверки:

```sql
-- Последние 10 платежей
SELECT * FROM payments 
ORDER BY created_at DESC 
LIMIT 10;

-- Незавершенные заказы
SELECT * FROM orders 
WHERE status = 'pending' 
AND created_at > NOW() - INTERVAL '24 hours';

-- Статистика по пополнениям
SELECT 
  COUNT(*) as total_payments,
  SUM(amount) as total_amount,
  AVG(amount) as avg_amount
FROM payments 
WHERE status = 'paid';
```

---

## ❓ Частые проблемы

### Webhook не приходит

**Причины:**
1. Неправильный URL в настройках Fragment API
2. Сервер Railway не доступен
3. Webhook заблокирован файрволлом

**Решение:**
1. Проверить URL: `https://worker-production-679d.up.railway.app/webhook/payment`
2. Проверить доступность: `curl https://worker-production-679d.up.railway.app/health`
3. Проверить логи Railway

### Баланс не пополняется

**Причины:**
1. Неправильная подпись webhook
2. Дубликат платежа
3. Пользователь не найден в БД

**Решение:**
1. Проверить `SHOP_KEY` в Railway
2. Проверить таблицу `payments` на дубликаты
3. Убедиться что пользователь есть в таблице `users`

### Payment URL не создается

**Причины:**
1. Неправильный `FRAGMENT_API_KEY`
2. Неправильный `SHOP_ID`
3. Fragment API недоступен

**Решение:**
1. Проверить API ключ в Railway
2. Проверить Shop ID
3. Проверить https://fragment-api.uz/status

---

## 📝 Дополнительная информация

### Лимиты

- Минимальная сумма: **10,000 сум**
- Максимальная сумма: **10,000,000 сум**
- Комиссия Fragment API: **уточните у провайдера**

### Поддерживаемые методы оплаты

- ✅ Click
- ✅ Payme  
- ✅ Uzum Bank
- ⏳ Другие методы (скоро)

### Контакты

- Админ: @StarPayUzAdmin
- Канал: @StarPayUz_Channel
- Поддержка Fragment API: https://fragment-api.uz/support

---

## 🎉 Готово!

Теперь пользователи могут автоматически пополнять баланс через Click/Payme/Uzum! 

Вебхуки приходят автоматически, баланс обновляется мгновенно, пользователь получает уведомление в боте.
