# 🚂 Настройка Telethon на Railway

## ⚠️ Важно: Первая авторизация

Telethon требует **интерактивной** авторизации при первом запуске (ввод кода из SMS).
Railway не поддерживает интерактивный ввод, поэтому нужно:

### Вариант 1: Авторизоваться локально (РЕКОМЕНДУЕТСЯ)

#### Шаг 1: Остановить бот на Railway
1. Зайти на https://railway.app/
2. Открыть проект `StarPayUzAuto`
3. Нажать **"..."** → **"Remove Service"** (временно)

#### Шаг 2: Авторизоваться локально
```bash
python bot.py
```

Telegram отправит код на `+998971051000`
Введите код в терминал:
```
Please enter the code you received: 12345
```

#### Шаг 3: Загрузить session файл на Railway

После успешной авторизации создастся файл `starpayuz_session.session`

**Способ A: Через Git (НЕ РЕКОМЕНДУЕТСЯ - небезопасно)**
```bash
git add starpayuz_session.session
git commit -m "Add Telethon session"
git push
```

**Способ B: Через Railway Volume (РЕКОМЕНДУЕТСЯ)**
1. На Railway создать Volume для хранения сессии
2. Загрузить файл вручную через Railway CLI

**Способ C: Использовать string session (ЛУЧШИЙ)**
Вместо файла использовать строковую сессию:

```python
# services/telethon_client.py
from telethon.sessions import StringSession

# При первом запуске локально:
client = TelegramClient(StringSession(), api_id, api_hash)
await client.start(phone=phone)
print(client.session.save())  # Скопировать эту строку

# Добавить в .env:
# TELETHON_SESSION_STRING=1AРандом...строка...
```

---

### Вариант 2: Использовать готовую сессию

Если у вас уже есть авторизованная сессия Telethon:

1. Конвертировать в string session
2. Добавить в Railway Environment Variables
3. Обновить код для использования StringSession

---

## 📋 Railway Environment Variables

Добавьте эти переменные в Railway:

```env
API_ID=30654977
API_HASH=921be05f47930bd6e60860faa4c6b0d5
PHONE_NUMBER=+998971051000
SESSION_NAME=starpayuz_session
```

**Или с string session:**
```env
API_ID=30654977
API_HASH=921be05f47930bd6e60860faa4c6b0d5
TELETHON_SESSION_STRING=1AРандомная_строка_сессии...
```

---

## 🔧 Обновить код для Railway

### Текущий код:
```python
# bot.py
await init_gift_sender(
    config.API_ID,
    config.API_HASH,
    config.PHONE_NUMBER if config.PHONE_NUMBER else None
)
```

### Для Railway (с string session):
```python
# config.py
TELETHON_SESSION_STRING = os.getenv("TELETHON_SESSION_STRING", "")

# services/telethon_client.py
from telethon.sessions import StringSession

async def init_gift_sender(api_id: int, api_hash: str, session_string: str = ""):
    global gift_sender
    session = StringSession(session_string) if session_string else "starpayuz_session"
    gift_sender = TelethonGiftSender(api_id, api_hash, session)
    await gift_sender.start()
    return gift_sender
```

---

## 🧪 Тестирование

После настройки протестируйте отправку подарка:

1. Пополнить баланс в боте
2. Открыть Gift раздел
3. Выбрать подарок
4. Указать username
5. Нажать "Sotib olish"

Проверьте логи на Railway:
```
INFO - Gift sent to @username: 5170233102089322756
```

---

## ❓ Troubleshooting

### "Telethon client not connected"
→ Сессия не загружена. Проверьте файл/переменную сессии.

### "FloodWait"
→ Слишком много запросов. Подождите указанное время.

### "Phone number is already in use"
→ Аккаунт уже авторизован в другом месте. Завершите другие сессии.

---

## 📚 Полезные ссылки

- **Railway Docs**: https://docs.railway.app/
- **Telethon String Sessions**: https://docs.telethon.dev/en/stable/concepts/sessions.html
- **Railway Volumes**: https://docs.railway.app/guides/volumes
