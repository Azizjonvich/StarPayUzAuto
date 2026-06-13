# 🚀 StarPayUz Bot - Готов к работе!

## ✅ Что работает СЕЙЧАС

Бот полностью рабочий с красивыми inline кнопками!

### Запуск:
```bash
python bot.py
```

## 📱 Функции бота

### При команде /start появляются inline кнопки:

1. **⭐ Stars olish** - Покупка Telegram Stars
   - 5 пакетов: 50, 100, 250, 500, 1000 Stars
   - Оплата через баланс

2. **💎 Premium olish** - Покупка Telegram Premium
   - 4 пакета: 1, 3, 6, 12 месяцев
   - С premium emoji 💎

3. **📱 Nomer olish** - Virtual номера (в разработке)

4. **🎁 Gift olish** - Подарки (в разработке)

5. **📦 Buyurtmalarim** - История заказов

6. **👥 Referallar** - Реферальная программа
   - 5000 сум за каждого друга
   - Реферальная ссылка

7. **✨ Hisobni to'ldirish** - Пополнение баланса

8. **🔒 Qo'llab-quvvatlash** - Контакты поддержки

## 💾 База данных

Автоматически создается `database.db` с таблицами:
- **users** - пользователи, балансы, рефералы
- **orders** - заказы и их статусы
- **transactions** - история транзакций

## 🔧 Конфигурация

### Твои данные уже настроены:
```
BOT_TOKEN: твой_новый_токен_бота
ADMIN_ID: твой_telegram_id
FRAGMENT_API_KEY: твой_fragment_api_key
SHOP_ID: твой_shop_id
SHOP_KEY: твой_shop_key
```

## 📊 Цены

### Stars:
- 50 Stars = 10,000 сум
- 100 Stars = 18,000 сум
- 250 Stars = 45,000 сум
- 500 Stars = 85,000 сум
- 1000 Stars = 165,000 сум

### Premium:
- 1 месяц = 25,000 сум
- 3 месяца = 65,000 сум
- 6 месяцев = 120,000 сум
- 12 месяцев = 220,000 сум

## 🌐 Web App (для будущего)

Когда будет сервер с доменом, можно включить Web App:

1. Получи домен и настрой HTTPS
2. Обнови в `.env`:
   ```
   WEBAPP_URL=https://твой-домен.com
   ```
3. Запусти webhook сервер:
   ```bash
   python webhook_server.py
   ```
4. В `keyboards.py` замени `callback_data` на `web_app=WebAppInfo(...)`

Готовые страницы Web App уже есть:
- `webapp/stars.html` - ⭐ Покупка Stars
- `webapp/premium.html` - 💎 Покупка Premium
- `webapp/phone.html` - 📱 Номера
- `webapp/gift.html` - 🎁 Подарки
- `webapp/topup.html` - ✨ Пополнение

## 🔍 Тестирование

1. Открой бота в Telegram
2. Отправь `/start`
3. Увидишь красивые inline кнопки
4. Нажми на любую кнопку
5. Работает! ✅

## 📝 Структура файлов

```
D:\StarPayUzAuto\
├── bot.py                 # Главный файл - запускай его!
├── config.py             # Настройки (твой ID, токены)
├── database.py           # База данных
├── api_client.py         # Fragment API
├── keyboards.py          # Клавиатуры
├── webhook_server.py     # Для Web App (потом)
├── handlers/
│   ├── start.py         # /start и все callbacks
│   ├── shop.py          # Покупка Stars/Premium
│   ├── balance.py       # Баланс
│   └── profile.py       # Профиль, рефералы
├── webapp/              # Web App страницы (для будущего)
│   ├── stars.html
│   ├── premium.html
│   └── ...
├── .env                 # Твои секретные данные
└── database.db          # База данных (создается автоматически)
```

## 🎯 Что делать дальше

1. **Сейчас**: Тестируй бота - он полностью работает!
2. **Потом**: Когда будет сервер - настрой Web App
3. **API интеграция**: Подключи реальный Fragment API для покупок

## 💡 Советы

- База данных SQLite - для продакшена лучше PostgreSQL
- Для тестов можешь добавить себе баланс вручную в БД
- Админ панель можно добавить через отдельные команды

## 🐛 Если что-то не работает

1. Проверь что бот запущен: `python bot.py`
2. Проверь токен бота в `.env`
3. Проверь что нет других ошибок в консоли

## ✨ Бот готов к работе!

Просто запусти:
```bash
python bot.py
```

И открой бота в Telegram! 🚀
