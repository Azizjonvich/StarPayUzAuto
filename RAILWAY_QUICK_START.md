# 🚀 Быстрый старт на Railway

## 3 простых шага:

### 1️⃣ Загрузи на GitHub
```bash
# В папке D:\StarPayUzAuto
git init
git add .
git commit -m "Initial commit"

# Создай репозиторий на GitHub.com, потом:
git remote add origin https://github.com/ТВОЙ_USERNAME/StarPayUz.git
git push -u origin main
```

### 2️⃣ Деплой на Railway
1. Открой https://railway.app
2. Войди через GitHub
3. "Start a New Project" → "Deploy from GitHub repo"
4. Выбери репозиторий `StarPayUz`
5. Railway начнет деплой автоматически! 🎉

### 3️⃣ Настрой переменные
В Railway dashboard → Variables → Add All:

```
BOT_TOKEN=твой_новый_токен_бота
FRAGMENT_API_KEY=твой_fragment_api_key
SHOP_ID=твой_shop_id
SHOP_KEY=твой_shop_key
WEBAPP_URL=https://твой-проект.up.railway.app
```

⚠️ **ВАЖНО**: После деплоя Railway даст URL - обнови `WEBAPP_URL` на реальный!

## 🎯 После деплоя:

Railway даст тебе URL типа:
```
https://starpayuz-production-xxxx.up.railway.app
```

1. Скопируй этот URL
2. Обнови `WEBAPP_URL` в Variables
3. Redeploy (Railway сделает автоматически)

## ✅ Проверка:

1. Открой бота в Telegram
2. Отправь `/start`
3. Нажми кнопку с Web App
4. Должна открыться страница! 🎊

## 🔥 Готово!

Твой бот работает 24/7 с Web App! 🚀

---

Полная инструкция: `DEPLOY_RAILWAY.md`
