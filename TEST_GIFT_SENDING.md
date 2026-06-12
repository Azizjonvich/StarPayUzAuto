# Тестирование отправки подарков

## ✅ Что было исправлено

### Проблема
- `SendStarGiftRequest` не существует в Telethon ❌
- Ошибка: `cannot import name 'SendStarGiftRequest' from 'telethon.tl.functions.payments'`

### Решение
Использован **правильный метод** из официального API Telegram:
```python
InputInvoiceStarGift + GetPaymentFormRequest + SendStarsFormRequest
```

## 🔄 Как работает сейчас

1. **Пользователь выбирает подарок** в webapp (gift.html)
2. **Webapp отправляет запрос** на `/api/order/gift`:
   ```json
   {
     "telegram_id": 8784918764,
     "username": "StarPayUzAdmin",
     "gift": "heart",
     "price": 3000
   }
   ```
3. **Сервер проверяет баланс** пользователя
4. **Telethon отправляет подарок** через 3 шага:
   - Создает `InputInvoiceStarGift` (invoice для подарка)
   - Получает `GetPaymentFormRequest` (форма оплаты)
   - Отправляет `SendStarsFormRequest` (отправка подарка)
5. **Баланс списывается**, order сохраняется как "completed"
6. **Пользователь получает уведомление**: "🎁 Heart sovg'asi @username ga yuborildi!"

## 🧪 Инструкция по тестированию

### Шаг 1: Дождитесь деплоя на Railway
Railway автоматически развернет изменения (займет ~2 минуты).

Проверьте логи Railway:
```
Telethon gift sender initialized
Got receiver peer for @StarPayUzAdmin: ...
Created invoice for gift 5170145012310081615
Got payment form: form_id=...
Star gift sent to @StarPayUzAdmin: 5170145012310081615
```

### Шаг 2: Откройте webapp
1. Зайдите в бот: [@starpayuzauto_bot](https://t.me/starpayuzauto_bot)
2. Нажмите "🎁 Gift olish"
3. Или откройте напрямую: https://starpayuz-webapp.vercel.app/gift.html

### Шаг 3: Купите подарок
1. Выберите любой подарок (например, 💝 Yurak - 3,000 sum)
2. Введите username получателя: `StarPayUzAdmin`
3. Нажмите "Yuborish"

### Шаг 4: Проверьте результат

**Если успешно:**
- ✅ Уведомление: "🎁 Heart sovg'asi @StarPayUzAdmin ga yuborildi!"
- ✅ Баланс уменьшился на 3,000 sum
- ✅ **Получатель получил настоящий Telegram подарок** (не сообщение!)

**Если ошибка:**
Проверьте логи Railway для сообщения об ошибке:
- `STARGIFT_USAGE_LIMITED` - подарок закончился
- `PEER_ID_INVALID` - username не найден
- `BALANCE_TOO_LOW` - недостаточно Stars у бота (не у пользователя!)

## 🔍 Возможные проблемы

### 1. "BALANCE_TOO_LOW"
**Причина**: У вашего Telegram аккаунта (через которого работает Telethon) недостаточно Stars.

**Решение**: Подарки отправляются через ваш личный аккаунт, а не бота. Нужно пополнить Stars на аккаунте +998971051000.

### 2. "InputInvoiceStarGift not found"
**Причина**: Старая версия Telethon.

**Решение**: Обновите Telethon на Railway:
```bash
pip install --upgrade telethon
```

### 3. Подарок не пришел получателю
**Причина**: Возможно, получатель заблокировал подарки или username неверный.

**Решение**: 
- Проверьте, что username существует
- Убедитесь, что получатель не отключил прием подарков в настройках Telegram

## 📊 Мониторинг

### Railway Logs
Ключевые сообщения:
```
INFO - Telethon gift sender initialized
INFO - Got receiver peer for @username: InputPeerUser(...)
INFO - Created invoice for gift 5170145012310081615
INFO - Got payment form: form_id=123456
INFO - Star gift sent to @username: 5170145012310081615, result: ...
```

### Database
Проверьте таблицу `orders`:
```sql
SELECT * FROM orders WHERE order_type = 'gift' ORDER BY created_at DESC LIMIT 5;
```

Статус должен быть `completed`, если подарок отправлен успешно.

## 🎯 Следующие шаги

Если тест успешен:
1. ✅ Отправка подарков работает
2. ✅ Можно использовать в продакшене
3. ✅ Следите за балансом Stars на аккаунте

Если тест провалился:
1. ❌ Проверьте логи Railway
2. ❌ Скопируйте ошибку и отправьте мне
3. ❌ Проверьте, что Telethon session активен

---
**Дата**: 12 июня 2026
**Версия**: 2.0 (исправлено)
**Метод**: `InputInvoiceStarGift` + `SendStarsFormRequest`
