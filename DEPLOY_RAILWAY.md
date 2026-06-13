# 🚂 Деплой на Railway.app

## Почему Railway?

✅ Бесплатный план ($5 кредита в месяц)
✅ Автоматический HTTPS
✅ Легкий деплой из GitHub
✅ Автоматический домен (.railway.app)
✅ Поддержка нескольких сервисов (bot + webhook)

## 📋 Пошаговая инструкция

### 1. Создай GitHub репозиторий

```bash
cd D:\StarPayUzAuto
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/твой-username/StarPayUz.git
git push -u origin main
```

### 2. Зарегистрируйся на Railway

1. Открой https://railway.app
2. Нажми "Start a New Project"
3. Выбери "Deploy from GitHub repo"
4. Авторизуйся через GitHub
5. Выбери репозиторий StarPayUz

### 3. Настрой переменные окружения

В Railway dashboard:
1. Открой свой проект
2. Нажми на "Variables"
3. Добавь все переменные из `.env`:

```
BOT_TOKEN=8270083145:AAHnNn4VhkjaIkO4Eopa5DqPWXTFpnYHgHo
FRAGMENT_API_KEY=9621fbdcb35922779aaf152e94c3a0b53ce9223b
FRAGMENT_API_URL=https://fragment-api.uz/api
SHOP_ID=665210
SHOP_KEY=8TJY3PDQ5C
DATABASE_URL=sqlite:///database.db
WEBAPP_URL=https://твой-проект.railway.app
```

⚠️ **ВАЖНО**: `WEBAPP_URL` замени на реальный URL который даст Railway!

### 4. Получи домен

После деплоя Railway даст тебе URL типа:
```
https://starpayuz-production-xxxx.up.railway.app
```

1. Скопируй этот URL
2. Обнови переменную `WEBAPP_URL` в Railway
3. Redeploy проект

### 5. Включи Web App в боте

Теперь нужно обновить код чтобы использовать Web App:

В файле `keyboards.py` замени функцию `get_webapp_main_keyboard()`:

```python
def get_webapp_main_keyboard() -> InlineKeyboardMarkup:
    """Main Web App keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Row 1: Stars and Premium with Web App
    builder.row(
        InlineKeyboardButton(
            text="⭐ Stars olish",
            web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/webapp/stars.html")
        ),
        InlineKeyboardButton(
            text="💎 Premium olish",
            web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/webapp/premium.html")
        )
    )
    
    # Row 2: Phone and Gift
    builder.row(
        InlineKeyboardButton(
            text="📱 Nomer olish",
            web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/webapp/phone.html")
        ),
        InlineKeyboardButton(
            text="🎁 Gift olish",
            web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/webapp/gift.html")
        )
    )
    
    # Row 3: Orders (full width)
    builder.row(
        InlineKeyboardButton(
            text="📦 Buyurtmalarim",
            callback_data="my_orders"
        )
    )
    
    # Row 4: Referrals and Balance
    builder.row(
        InlineKeyboardButton(
            text="👥 Referallar",
            callback_data="referrals"
        ),
        InlineKeyboardButton(
            text="✨ Hisobni to'ldirish",
            web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/webapp/topup.html")
        )
    )
    
    # Row 5: Support
    builder.row(
        InlineKeyboardButton(
            text="🔒 Qo'llab-quvvatlash",
            callback_data="support"
        )
    )
    
    return builder.as_markup()
```

Сделай commit и push:
```bash
git add .
git commit -m "Enable Web App"
git push
```

Railway автоматически передеплоит! 🚀

### 6. Настрой базу данных (опционально)

Railway предлагает PostgreSQL бесплатно:

1. В проекте нажми "+ New"
2. Выбери "Database" → "PostgreSQL"
3. Railway создаст БД и даст `DATABASE_URL`
4. Обнови переменную `DATABASE_URL` в настройках

⚠️ Потребуется изменить код для PostgreSQL (или оставь SQLite)

## 🎯 Структура на Railway

Railway запустит два процесса:
- **Bot** (bot.py) - Telegram бот
- **Web** (webhook_server.py) - Webhook сервер для Web App

## 📊 Мониторинг

В Railway dashboard можешь:
- Смотреть логи
- Мониторить использование ресурсов
- Перезапускать сервисы
- Смотреть метрики

## 🔍 Проверка

После деплоя:
1. Открой бота в Telegram
2. Отправь `/start`
3. Нажми на кнопку Web App
4. Должна открыться красивая страница! ✨

## 💰 Стоимость

Railway дает $5 бесплатно в месяц:
- ~500 часов работы
- Достаточно для небольшого бота
- Можешь добавить карту для большего

## 🐛 Troubleshooting

### Бот не запускается
Проверь логи в Railway → смотри ошибки

### Web App не открывается
- Проверь что `WEBAPP_URL` правильный
- Проверь что webhook_server.py запущен
- Смотри логи web сервиса

### База данных
SQLite файл сохраняется в Railway - данные останутся после redeploy

## 🔄 Обновление

Для обновления бота:
```bash
git add .
git commit -m "Update"
git push
```

Railway автоматически передеплоит! 🎉

## 📁 Файлы для Railway

Уже созданы:
- ✅ `Procfile` - команды запуска
- ✅ `nixpacks.toml` - конфигурация сборки
- ✅ `runtime.txt` - версия Python
- ✅ `requirements.txt` - зависимости
- ✅ `.gitignore` - игнорируемые файлы

## 🎊 Готово!

После деплоя у тебя будет:
- 🤖 Работающий бот 24/7
- 🌐 Web App с красивым интерфейсом
- 🔒 HTTPS автоматически
- 📊 Мониторинг и логи
- 🚀 Автодеплой при push

Все готово для Railway! 🚂
