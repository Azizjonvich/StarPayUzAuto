"""
Скрипт для генерации Telethon string session
Запустите локально один раз для авторизации
"""

import asyncio
import sys
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "")

# Proxy settings (optional, for countries where Telegram is blocked)
TELEGRAM_PROXY_TYPE = os.getenv("TELEGRAM_PROXY_TYPE", "")  # socks5 or http
TELEGRAM_PROXY_ADDR = os.getenv("TELEGRAM_PROXY_ADDR", "")
TELEGRAM_PROXY_PORT = int(os.getenv("TELEGRAM_PROXY_PORT", "0"))
TELEGRAM_PROXY_USER = os.getenv("TELEGRAM_PROXY_USER", "")
TELEGRAM_PROXY_PASS = os.getenv("TELEGRAM_PROXY_PASS", "")


def get_proxy():
    """Create proxy tuple for Telethon if configured."""
    if TELEGRAM_PROXY_TYPE and TELEGRAM_PROXY_ADDR and TELEGRAM_PROXY_PORT:
        if TELEGRAM_PROXY_USER and TELEGRAM_PROXY_PASS:
            return (TELEGRAM_PROXY_TYPE, TELEGRAM_PROXY_ADDR, TELEGRAM_PROXY_PORT, TELEGRAM_PROXY_USER, TELEGRAM_PROXY_PASS)
        return (TELEGRAM_PROXY_TYPE, TELEGRAM_PROXY_ADDR, TELEGRAM_PROXY_PORT)
    return None


def create_client():
    """Create TelegramClient with optional proxy."""
    proxy = get_proxy()
    if proxy:
        print(f"   🌐 Используется прокси: {TELEGRAM_PROXY_TYPE}://{TELEGRAM_PROXY_ADDR}:{TELEGRAM_PROXY_PORT}")
        return TelegramClient(StringSession(), API_ID, API_HASH, proxy=proxy)
    return TelegramClient(StringSession(), API_ID, API_HASH)


async def main():
    print("=" * 60)
    print("   🤖 Telethon String Session Generator")
    print("=" * 60)
    print()

    if not API_ID or not API_HASH or API_ID == 0:
        print("❌ Ошибка: API_ID и API_HASH не настроены в .env")
        print("   Зайдите на https://my.telegram.org, создайте приложение и укажите API_ID/API_HASH")
        return

    if not PHONE_NUMBER:
        print("❌ Ошибка: PHONE_NUMBER не указан в .env")
        print('   Пример: PHONE_NUMBER=+998901234567')
        return

    print(f"🔑 API_ID: {API_ID}")
    print(f"🔑 API_HASH: {API_HASH[:10]}...")
    print(f"📞 Phone: {PHONE_NUMBER}")
    print()

    # Проверка версии telethon
    try:
        import telethon
        print(f"📦 Telethon version: {telethon.__version__}")
    except:
        pass

    # Создаём клиент (с прокси из .env, если указан)
    client = create_client()

    try:
        # Пытаемся подключиться, с возможностью настройки прокси
        for attempt in range(3):
            try:
                print(f"🔄 Попытка {attempt + 1}/3: Подключение к Telegram...")
                await client.connect()
                if await client.is_user_authorized():
                    print("✅ Уже авторизован!")
                    break
                print("✅ Подключение установлено!")
                break
            except (ConnectionError, OSError, errors.TimedOutError) as e:
                if attempt == 2:
                    raise e
                print(f"   ⚠️  Ошибка: {type(e).__name__}")
                await client.disconnect()
                
                if attempt == 0:
                    print()
                    print("🔍 Не удалось подключиться к Telegram.")
                    print("   • В Узбекистане Telegram заблокирован — нужен VPN или прокси")
                    print()
                    wants_proxy = input("✏️  Хотите настроить SOCKS5/HTTP прокси? (y/n): ").strip().lower()
                    if wants_proxy != 'y':
                        print("❌ Отменено. Включите VPN и запустите скрипт снова.")
                        return
                    
                    # Interactive proxy setup
                    print()
                    print("--- Настройка прокси ---")
                    print("📌 Где взять прокси:")
                    print("   • Купите SOCKS5 прокси (например, на proxy6.net)")
                    print("   • Используйте бесплатные прокси из списков в Telegram")
                    print()
                    proxy_type = input("Тип прокси (socks5/http): ").strip().lower()
                    proxy_addr = input("Адрес прокси (IP): ").strip()
                    proxy_port_str = input("Порт прокси: ").strip()
                    try:
                        proxy_port = int(proxy_port_str)
                    except ValueError:
                        print("❌ Неверный порт")
                        return
                    
                    use_auth = input("Требуется логин/пароль? (y/n): ").strip().lower()
                    if use_auth == 'y':
                        proxy_user = input("Логин: ").strip()
                        proxy_pass = input("Пароль: ").strip()
                        proxy = (proxy_type, proxy_addr, proxy_port, proxy_user, proxy_pass)
                    else:
                        proxy = (proxy_type, proxy_addr, proxy_port)
                    
                    print(f"\n🔄 Создаю новое подключение через прокси...")
                    client = TelegramClient(StringSession(), API_ID, API_HASH, proxy=proxy)
                    
                    # Запоминаем прокси в .env
                    save_to_env = input("\n✏️  Сохранить прокси в .env для будущих запусков? (y/n): ").strip().lower()
                    if save_to_env == 'y':
                        with open(".env", "a") as f:
                            f.write(f"\n# Proxy (added by generate_session.py)\n")
                            f.write(f"TELEGRAM_PROXY_TYPE={proxy_type}\n")
                            f.write(f"TELEGRAM_PROXY_ADDR={proxy_addr}\n")
                            f.write(f"TELEGRAM_PROXY_PORT={proxy_port}\n")
                            if use_auth == 'y':
                                f.write(f"TELEGRAM_PROXY_USER={proxy_user}\n")
                                f.write(f"TELEGRAM_PROXY_PASS={proxy_pass}\n")
                        print("✅ Прокси сохранён в .env!")
                else:
                    print("   🔄 Повторная попытка...")
        
        # Проверка авторизации
        if await client.is_user_authorized():
            print("⚠️  Этот аккаунт уже авторизован!")
            me = await client.get_me()
            name = me.first_name or ""
            if me.last_name:
                name += " " + me.last_name
            username = f"@{me.username}" if me.username else "без username"
            print(f"   👤 Текущий пользователь: {name} ({username})")
        else:
            print()
            print("📤 Отправка кода подтверждения на номер", PHONE_NUMBER)
            print("   ⏳ Ожидание... (до 30 секунд)")
            print()
            
            try:
                # Явно отправляем запрос кода
                sent = await client.send_code_request(PHONE_NUMBER)
                print(f"✅ Код отправлен!")
                print(f"   📱 Способ: {sent.type if hasattr(sent, 'type') else 'SMS/Telegram'}")
                if hasattr(sent, 'phone_code_hash'):
                    print(f"   🆔 Code hash: {sent.phone_code_hash[:10]}...")
                print()
                
                # Запрашиваем ввод кода
                code = input("✏️  Введите код, который пришёл в Telegram: ").strip()
                
                if not code:
                    print("❌ Код не введён")
                    return
                
                print()
                print("🔄 Проверка кода...")
                
                try:
                    await client.sign_in(phone=PHONE_NUMBER, code=code)
                    print("✅ Код принят!")
                except errors.SessionPasswordNeededError:
                    print("🔐 Требуется пароль двухфакторной аутентификации (2FA)")
                    password = input("✏️  Введите ваш пароль Telegram: ")
                    await client.sign_in(password=password)
                    print("✅ Пароль принят!")
                    
            except errors.PhoneNumberInvalidError:
                print()
                print("❌ ОШИБКА: Номер телефона недействителен!")
                print("   Проверьте PHONE_NUMBER в .env")
                print("   Формат: +998XXXXXXXXX (Узбекистан)")
                await client.disconnect()
                return
            except errors.PhoneCodeInvalidError:
                print()
                print("❌ ОШИБКА: Неверный код! Попробуйте ещё раз.")
                await client.disconnect()
                return
            except errors.PhoneCodeExpiredError:
                print()
                print("❌ ОШИБКА: Код истёк! Запустите скрипт заново.")
                await client.disconnect()
                return
            except errors.FloodWaitError as e:
                print()
                print(f"❌ ОШИБКА: Слишком много запросов!")
                print(f"   Подождите {e.seconds} секунд и попробуйте снова.")
                await client.disconnect()
                return
            except errors.PhoneNumberFloodError:
                print()
                print("❌ ОШИБКА: Номер временно заблокирован из-за подозрительной активности.")
                print("   Попробуйте через несколько часов.")
                await client.disconnect()
                return
                
        print()
        print("✅ Успешная авторизация!")
        me = await client.get_me()
        print(f"   👤 Аккаунт: {me.first_name or ''} {me.last_name or ''} (@{me.username or 'нет username'})")
        
        print()
        print("=" * 60)
        print("📝 Ваша STRING SESSION (скопируйте в Railway):")
        print("=" * 60)
        session_str = client.session.save()
        print(session_str)
        print("=" * 60)
        print()
        print("Добавьте в Railway Environment Variables:")
        print("  TELETHON_SESSION_STRING=<скопированная_строка_выше>")
        print()
        print("⚠️  НЕ ПУБЛИКУЙТЕ ЭТУ СТРОКУ В GIT!")
        
        # Сохраняем в файл на всякий случай
        with open("session_string.txt", "w") as f:
            f.write(session_str)
        print("📁 Также сохранено в файл session_string.txt")
        
    except errors.ApiIdInvalidError:
        print()
        print("❌ ОШИБКА: API_ID или API_HASH недействительны!")
        print("   Зайдите на https://my.telegram.org и проверьте данные вашего приложения.")
    except errors.TimedOutError:
        print()
        print("❌ ОШИБКА: Таймаут соединения с Telegram.")
        print("   В Узбекистане Telegram заблокирован — используйте VPN или прокси.")
    except ConnectionError as e:
        print()
        print(f"❌ ОШИБКА: Не удалось подключиться к Telegram: {e}")
        print("   Проверьте интернет или используйте VPN/Proxy.")
    except KeyboardInterrupt:
        print()
        print("\n👋 Завершено пользователем.")
    except Exception as e:
        print()
        print(f"❌ НЕИЗВЕСТНАЯ ОШИБКА: {type(e).__name__}: {e}")
        print("   Пожалуйста, отправьте этот текст разработчику.")
    finally:
        await client.disconnect()
        print()
        print("👋 Соединение закрыто")


if __name__ == "__main__":
    asyncio.run(main())
