# 🚀 Запуск StarPayUz бота

## Быстрый старт

### 1. Запуск бота
```bash
python bot.py
```

### 2. Запуск webhook сервера (в отдельном окне)
```bash
python webhook_server.py
```

## ✅ Что готово

### 🤖 Бот
- ✅ Telegram Bot с Web App интерфейсом
- ✅ Красивый дизайн как на скрине
- ✅ Inline кнопки с Web App
- ✅ База данных SQLite
- ✅ Реферальная система

### 🎨 Web App страницы
- ✅ **stars.html** - покупка Stars с красивым дизайном
- ✅ **premium.html** - покупка Premium
- ✅ **phone.html** - Virtual рaqамlar (заглушка)
- ✅ **gift.html** - Gift sovg'alar (заглушка)
- ✅ **topup.html** - Пополнение баланса (заглушка)

### 💎 Функции
- ⭐ Покупка Telegram Stars
- 💎 Покупка Telegram Premium
- 💰 Балансовая система
- 👥 Реферальная программа (5000 сум за друга)
- 📦 История заказов
- 🔒 Поддержка

## 📱 Как использовать

1. Запусти бота: `/start`
2. Увидишь приветственное сообщение с inline кнопками
3. Нажми на любую кнопку (⭐ Stars olish или 💎 Premium olish)
4. Откроется красивый Web App с дизайном как на скрине!

## 🎯 Кнопки в боте

- **⭐ Stars olish** - откр ывает Web App для покупки Stars
- **💎 Premium olish** - открывает Web App для покупки Premium  
- **📱 Nomer olish** - Virtual номера (в разработке)
- **🎁 Gift olish** - Подарки (в разработке)
- **📦 Buyurtmalarim** - История заказов (callback)
- **👥 Referallar** - Реферальная программа (callback)
- **✨ Hisobni to'ldirish** - Пополнение (Web App)
- **🔒 Qo'llab-quvvatlash** - Поддержка (callback)

## ⚙️ Настройка для продакшена

### 1. Обнови .env файл
```env
BOT_TOKEN=твой_новый_токен
WEBAPP_URL=https://твой-домен.com
```

### 2. Настрой webhook сервер
Разверни на VPS с nginx и SSL сертификатом

### 3. Fragment API
API уже настроен с твоими ключами:
- API Key: 9621fbdcb35922779aaf152e94c3a0b53ce9223b
- Shop ID: 665210
- Shop Key: 8TJY3PDQ5C

## 🎨 Дизайн Web App

Дизайн сделан в темной теме (#0f1419) с синими акцентами (#7c8cff):
- Адаптивный под мобильные
- Красивые карточки для пакетов
- Градиентные кнопки
- Tabs для переключения между разделами
- Лидерборд (в Stars)

## 📝 Структура

```
StarPayUzAuto/
├── bot.py              # Главный файл бота
├── config.py           # Конфигурация
├── database.py         # База данных
├── api_client.py       # Fragment API клиент
├── keyboards.py        # Клавиатуры
├── webhook_server.py   # Webhook сервер
├── handlers/
│   ├── start.py       # /start и callbacks
│   ├── shop.py        # Покупки
│   ├── balance.py     # Баланс
│   └── profile.py     # Профиль
├── webapp/
│   ├── stars.html     # Stars Web App ⭐
│   ├── premium.html   # Premium Web App 💎
│   ├── phone.html     # Phone (заглушка)
│   ├── gift.html      # Gift (заглушка)
│   └── topup.html     # Topup (заглушка)
└── database.db        # SQLite база

```

## 🔧 Troubleshooting

### Ошибка: "No module named 'aiogram'"
```bash
pip install aiogram aiohttp aiosqlite python-dotenv cryptography
```

### Web App не открывается
- Проверь что webhook_server.py запущен
- Проверь WEBAPP_URL в config.py
- Для локального тестирования используй ngrok

### База данных
База автоматически создается при первом запуске

## 🌐 Для локального тестирования с Web App

1. Установи ngrok: https://ngrok.com/
2. Запусти webhook сервер: `python webhook_server.py`
3. В другом терминале: `ngrok http 8080`
4. Скопируй URL из ngrok (например: https://abc123.ngrok.io)
5. Обнови WEBAPP_URL в .env или config.py
6. Перезапусти бота

## ✨ Готово!

Бот готов к работе! Открой Telegram и попробуй `/start`

Контакты для поддержки:
- Telegram: @StarPayUz_Admin
- Email: support@starpayuz.com
