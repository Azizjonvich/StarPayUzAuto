# StarPayUz ElderPay API

Node.js API сервер для интеграции с ElderPay платежной системой.

## Endpoints

### `POST /api/elderpay/create`
Создать заказ на оплату

**Request:**
```json
{
  "amount": 10000,
  "user_id": "123456789",
  "local_order_id": "topup_abc123"
}
```

**Response:**
```json
{
  "ok": true,
  "order_id": "EP123456789",
  "local_order_id": "topup_abc123",
  "card_number": "9860180101712578",
  "amount": 10000,
  "status": "pending"
}
```

### `GET /api/elderpay/check/:order_id`
Проверить статус заказа

**Response:**
```json
{
  "ok": true,
  "order_id": "EP123456789",
  "status": "paid",
  "data": {...}
}
```

### `GET /api/elderpay/pending`
Получить список всех pending заказов

**Response:**
```json
{
  "ok": true,
  "count": 5,
  "orders": [...]
}
```

### `GET /health`
Health check endpoint

## Environment Variables

```env
ELDERPAY_SHOP_ID=665210
ELDERPAY_SHOP_KEY=8TJY3PDQ5C
ELDERPAY_API_URL=https://elder.uz/api
PORT=3000
CARD_NUMBER=9860180101712578
```

## Installation

```bash
cd elderpay-api
npm install
npm start
```

## Development

```bash
npm run dev
```

## Deploy to Railway

1. Push to GitHub
2. Create new project in Railway
3. Connect GitHub repo
4. Set root directory to `elderpay-api`
5. Add environment variables
6. Deploy

## Usage from Python

```python
import aiohttp

async def create_elderpay_order(amount: int, user_id: int, order_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://your-api.railway.app/api/elderpay/create",
            json={
                "amount": amount,
                "user_id": str(user_id),
                "local_order_id": order_id
            }
        ) as resp:
            return await resp.json()

async def check_elderpay_order(order_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://your-api.railway.app/api/elderpay/check/{order_id}"
        ) as resp:
            return await resp.json()
```
