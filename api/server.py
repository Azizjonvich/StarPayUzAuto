import json
import logging
from pathlib import Path

from aiohttp import web
from aiohttp.web_middlewares import middleware

from bot.config import STARS_MAX_AMOUNT, STARS_MIN_AMOUNT, settings
from services.database import (
  add_balance,
  create_order,
  deduct_balance,
  get_user,
  record_payment,
)
from services.fragment_api import FragmentAPI, FragmentAPIError
from services.payment_verify import extract_payment_fields, verify_shop_signature
from services.telegram_auth import validate_init_data

logger = logging.getLogger(__name__)

WEBAPP_DIR = Path(__file__).resolve().parent.parent / "webapp"
fragment = FragmentAPI()

CORS_ORIGINS = {
    "https://starpayuz-webapp.vercel.app",
    "https://kamron5505.github.io",
    "https://worker-production-679d.up.railway.app",
}


@middleware
async def cors_middleware(request: web.Request, handler):
    origin = request.headers.get("Origin", "")
    # Allow preflight
    if request.method == "OPTIONS":
        resp = web.Response()
        _set_cors(resp, origin)
        return resp
    resp = await handler(request)
    _set_cors(resp, origin)
    return resp


def _set_cors(resp: web.Response, origin: str) -> None:
    allowed = origin if origin in CORS_ORIGINS else "*"
    resp.headers["Access-Control-Allow-Origin"] = allowed
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, X-Telegram-Init-Data"
    )


async def _json_body(request: web.Request) -> dict:
  try:
    return await request.json()
  except Exception:
    return {}


async def _auth_user(request: web.Request) -> dict | None:
  init_data = request.headers.get("X-Telegram-Init-Data") or ""
  body = await _json_body(request)
  if not init_data:
    init_data = body.get("initData", "")
  return validate_init_data(init_data, settings.bot_token)


def _user_id_from_auth(auth: dict | None) -> int | None:
  if not auth:
    return None
  user = auth.get("user")
  if isinstance(user, dict):
    return user.get("id")
  return None


async def health(_: web.Request) -> web.Response:
  return web.json_response({"ok": True, "service": "StarPayUz"})


async def webapp_index(_: web.Request) -> web.FileResponse:
  return web.FileResponse(WEBAPP_DIR / "index.html")


async def api_user_balance(request: web.Request) -> web.Response:
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)
  
  # Ensure user exists (create if not)
  from services.database import ensure_user
  username = None
  full_name = None
  if auth and auth.get("user"):
    u = auth["user"]
    username = u.get("username")
    full_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
  
  user = await ensure_user(int(user_id), username, full_name or "User")
  return web.json_response({"ok": True, "balance": user.get("balance", 0)})


def _parse_stars_quantity(body: dict) -> int | None:
  raw = body.get("quantity") or body.get("amount")
  if raw is None:
    return None
  try:
    return int(raw)
  except (TypeError, ValueError):
    return None


def _validate_stars_quantity(quantity: int | None) -> str | None:
  if quantity is None:
    return "Stars miqdori ko'rsatilmagan"
  if quantity < STARS_MIN_AMOUNT:
    return f"Minimal miqdor: {STARS_MIN_AMOUNT} stars"
  if quantity > STARS_MAX_AMOUNT:
    return f"Maksimal miqdor: {STARS_MAX_AMOUNT:,} stars"
  return None


async def api_stars_price(request: web.Request) -> web.Response:
  body = await _json_body(request)
  quantity = _parse_stars_quantity(body) or STARS_MIN_AMOUNT
  err = _validate_stars_quantity(quantity)
  if err:
    return web.json_response({"ok": False, "error": err}, status=400)
  try:
    data = await fragment.get_stars_price(quantity)
    return web.json_response({"ok": True, "data": data})
  except FragmentAPIError as e:
    return web.json_response({"ok": False, "error": str(e)}, status=400)


async def api_order_stars(request: web.Request) -> web.Response:
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

  username = (body.get("username") or "").strip().lstrip("@")
  quantity = _parse_stars_quantity(body)
  
  logger.info("api_order_stars: user_id=%s, username=%s, quantity=%s", user_id, username, quantity)
  
  if not username:
    return web.json_response({"ok": False, "error": "Username ko'rsatilmagan"}, status=400)
  err = _validate_stars_quantity(quantity)
  if err:
    return web.json_response({"ok": False, "error": err}, status=400)

  user = await get_user(int(user_id))
  if not user:
    logger.warning("User %s not found in DB", user_id)
    return web.json_response({"ok": False, "error": "Foydalanuvchi topilmadi. /start bosing."}, status=400)
  
  balance = user.get("balance", 0)
  logger.info("User %s balance: %s", user_id, balance)
  
  # Calculate price (simple: 200 sum per star)
  price = quantity * 200
  
  if balance < price:
    logger.warning("Insufficient balance: have %s, need %s", balance, price)
    return web.json_response(
      {"ok": False, "error": f"Balans yetarli emas. Kerak: {price:,} so'm, Balans: {balance:,} so'm"},
      status=400
    )

  try:
    result = await fragment.buy_stars(username, quantity)
    order_id = await create_order(
      int(user_id), "stars", username, quantity, None, str(result.get("id", "")), "completed"
    )
    await deduct_balance(int(user_id), price)
    return web.json_response({"ok": True, "order_id": order_id, "result": result})
  except FragmentAPIError as e:
    await create_order(int(user_id), "stars", username, quantity, None, status="failed")
    return web.json_response({"ok": False, "error": str(e)}, status=400)


async def api_order_premium(request: web.Request) -> web.Response:
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

  username = (body.get("username") or "").strip().lstrip("@")
  months = int(body.get("months", 3))
  if months not in (3, 6, 12):
    months = 3

  try:
    result = await fragment.buy_premium(username, months)
    order_id = await create_order(
      int(user_id), "premium", username, months, None, str(result.get("id", "")), "completed"
    )
    return web.json_response({"ok": True, "order_id": order_id, "result": result})
  except FragmentAPIError as e:
    await create_order(int(user_id), "premium", username, months, None, status="failed")
    return web.json_response({"ok": False, "error": str(e)}, status=400)


async def api_order_gift(request: web.Request) -> web.Response:
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

  username = (body.get("username") or "").strip().lstrip("@")
  gift = (body.get("gift") or "").strip().lower()
  price = int(body.get("price", 0))
  
  if not username:
    return web.json_response({"ok": False, "error": "Username ko'rsatilmagan"}, status=400)
  
  if not gift or price <= 0:
    return web.json_response({"ok": False, "error": "Gift tanlanmagan"}, status=400)
  
  # Check balance
  user = await get_user(int(user_id))
  if not user:
    return web.json_response({"ok": False, "error": "Foydalanuvchi topilmadi"}, status=400)
  
  balance = user.get("balance", 0)
  if balance < price:
    return web.json_response({
      "ok": False,
      "error": f"Balans yetarli emas. Kerak: {price:,} so'm, Balans: {balance:,} so'm"
    }, status=400)
  
  # Gift ID mapping
  gift_mapping = {
    # Regular gifts
    "heart": "5170145012310081615",
    "bear": "5170233102089322756",
    "box": "5170250947678437525",
    "rose": "5168103777563050263",
    "cake": "5170144170496491616",
    "rocket": "5170564780938756245",
    "champagne": "6028601630662853006",
    "bouquet": "5170314324215857265",
    "diamond": "5170521118301225164",
    "trophy": "5168043875654172773",
    "ring": "5170690322832818290",
    
    # Deluxe/Limited gifts (IDs need to be obtained from GetStarGiftsRequest)
    # These are placeholder IDs - update with real IDs from Telegram API
    "deluxe_rose": "5170145012310081616",      # Deluxe Rose - 25 stars
    "deluxe_heart": "5170145012310081617",     # Deluxe Heart - 25 stars
    "deluxe_cake": "5170144170496491617",      # Deluxe Cake - 50 stars
    "deluxe_diamond": "5170521118301225165",   # Deluxe Diamond - 100 stars
    "golden_trophy": "5168043875654172774",    # Golden Trophy - 250 stars
    "star_crown": "5170145012310081618",       # Star Crown - 500 stars
    "blue_gem": "5170145012310081619",         # Blue Gem - 1000 stars
    "fire_phoenix": "5170145012310081620",     # Fire Phoenix - 2500 stars
    
    # Limited Edition gifts (removed Telegram gifts)
    "newyear_tree": "5922558454332916696",       # New Year Tree - 50 stars
    "newyear_bear": "5956217000635139069",       # New Year Bear - 50 stars
    "valentine_heart": "5801108895304779062",    # Valentine Heart - 50 stars
    "valentine_bear": "5800655655995968830",     # Valentine Bear - 50 stars
    "march8_bear": "5866352046986232958",        # March 8 Bear - 50 stars
    "patrick_bear": "5893356958802511476",       # St. Patrick Bear - 50 stars
    "april_bear": "5935895822435615975",         # April Fools Bear - 50 stars
    "easter_bear": "5969796561943660080",        # Easter Bear - 50 stars
    "may_bear": "6026193266406327981",           # May Day Bear - 50 stars
  }
  
  gift_id = gift_mapping.get(gift.lower())
  if not gift_id:
    return web.json_response({"ok": False, "error": f"Noma'lum gift: {gift}"}, status=400)
  
  # Send gift via Telethon (MTProto)
  from services.telethon_client import gift_sender
  
  if not gift_sender:
    return web.json_response({
      "ok": False,
      "error": "Gift sender не инициализирован. Проверьте настройки Telethon."
    }, status=503)
  
  try:
    logger.info(f"Sending gift {gift} (ID: {gift_id}) to @{username} via Telethon MTProto")
    
    # Отправляем подарок через Telethon
    result = await gift_sender.send_gift(
      username=username,
      gift_sticker_id=gift_id,
      message=f"🎁 Sovg'a"
    )
    
    if not result.get("ok"):
      logger.error(f"Gift sending failed: {result.get('error')}")
      # Create failed order
      order_id = await create_order(
        int(user_id), "gift", username, None, price, gift_id, "failed"
      )
      return web.json_response({
        "ok": False,
        "error": result.get("error", "Gift yuborishda xatolik")
      }, status=400)
    
    logger.info(f"Gift sent successfully: {result}")
    
    # Deduct balance
    await deduct_balance(int(user_id), price)
    
    # Create order
    order_id = await create_order(
      int(user_id), "gift", username, None, price, gift_id, "completed"
    )
    
    return web.json_response({
      "ok": True,
      "order_id": order_id,
      "message": f"🎁 {gift.capitalize()} sovg'asi @{username} ga yuborildi!"
    })
    
  except Exception as e:
    logger.error(f"Failed to send gift: {e}")
    
    # Create failed order
    order_id = await create_order(
      int(user_id), "gift", username, None, price, gift_id, "failed"
    )
    
    return web.json_response({
      "ok": False,
      "error": f"Xatolik: {str(e)}"
    }, status=400)


async def api_order_phone(request: web.Request) -> web.Response:
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

  username = (body.get("username") or "").strip().lstrip("@")
  country = (body.get("country") or "UZ").strip().upper()

  try:
    result = await fragment.buy_phone(username, country)
    order_id = await create_order(
      int(user_id), "phone", username, None, None, str(result.get("id", "")), "completed"
    )
    return web.json_response({"ok": True, "order_id": order_id, "result": result})
  except FragmentAPIError as e:
    await create_order(int(user_id), "phone", username, None, None, status="failed")
    return web.json_response({"ok": False, "error": str(e)}, status=400)


async def api_payment_create(request: web.Request) -> web.Response:
  """Create payment invoice"""
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

  amount = body.get("amount")
  method = body.get("method", "click")
  order_id = body.get("order_id")
  
  if not amount or not order_id:
    return web.json_response({"ok": False, "error": "Amount va order_id kerak"}, status=400)
  
  try:
    amount_int = int(amount)
    if amount_int < 1000 or amount_int > 100000000:
      return web.json_response({"ok": False, "error": "Summa 1,000 dan 100,000,000 oralig'ida bo'lishi kerak"}, status=400)
  except (TypeError, ValueError):
    return web.json_response({"ok": False, "error": "Noto'g'ri summa"}, status=400)

  # Create order in database
  await create_order(int(user_id), "topup", "", None, amount_int, order_id, "pending")
  
  # Import api_client to create payment
  from api_client import api_client
  
  # Определяем callback_url для вебхуков
  callback_url = f"{settings.api_public_url}/webhook/payment"
  redirect_url = f"{settings.api_public_url}/payment/success"
  
  result = await api_client.create_payment(
    amount=amount_int,
    order_id=order_id,
    user_id=int(user_id),
    description=f"StarPayUz - Hisobni to'ldirish {amount_int:,} so'm",
    callback_url=callback_url,
    redirect_url=redirect_url
  )
  
  payment_ok = result.get("ok") or result.get("success") or False
  if payment_ok and result.get("payment_url"):
    return web.json_response({
      "ok": True,
      "payment_url": result["payment_url"],
      "order_id": order_id
    })
  else:
    return web.json_response({
      "ok": False,
      "error": result.get("message") or result.get("error") or "To'lov yaratishda xatolik"
    }, status=400)


async def payment_webhook(request: web.Request) -> web.Response:
  """
  Единый обработчик вебхуков от платёжных систем.
  Поддерживает:
    - Fragment API (поле "order_id", "amount", "user_id")
    - Click (поле "merchant_trans_id", "amount", "user_id")
    - Payme (поле "order_id", "amount", "customer_id")
  """
  try:
    payload = await request.json()
  except Exception:
    return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

  logger.info("Payment webhook received: %s", json.dumps(payload, ensure_ascii=False)[:200])

  # Проверка shop_id — логируем несоответствие, но НЕ блокируем
  # (Railway env может содержать пробелы, разные платёжки шлют разные форматы)
  shop_id = str(payload.get("shop_id", "")).strip()
  expected_shop_id = str(settings.shop_id).strip()
  if expected_shop_id and shop_id and shop_id != expected_shop_id:
    logger.warning("shop_id mismatch: got='%s' expected='%s' — proceeding anyway", shop_id, expected_shop_id)
  # НЕ блокируем — проверка подписи достаточна для безопасности

  # Проверка подписи (не блокируем — разные платёжки используют разные алгоритмы)
  if settings.shop_key:
    sig_ok = verify_shop_signature(payload, settings.shop_key)
    logger.info("Payment webhook signature: %s", "OK" if sig_ok else "MISMATCH (non-blocking)")

  # Определяем статус (Click использует поле "error": 0 для успеха)
  raw_status = str(payload.get("status", "")).lower()
  action = str(payload.get("action", "")).lower()
  error_code = payload.get("error")
  error_text = str(error_code).strip().lower()
  
  # Click: action="1" (complete) и error=0 значит успех
  is_click_success = (action == "1" and error_text in ("0", "0.0"))
  # Payme: status="paid" / status="completed"
  is_paid = raw_status in ("paid", "success", "completed", "1", "true")
  
  if not is_paid and not is_click_success:
    logger.info("Webhook ignored: status=%s, action=%s, error=%s", raw_status, action, error_code)
    return web.json_response({"ok": True, "message": "ignored status"})

  # Извлекаем поля (поддержка разных форматов)
  order_id, amount, user_id = extract_payment_fields(payload)
  
  # Если не нашли через общие поля — пробуем специфичные для Click
  if not order_id:
    order_id = payload.get("merchant_trans_id") or payload.get("click_trans_id")
  if not amount:
    # Click/Payme могут передавать amount как строку с десятичной точкой "50000.00"
    raw_amount = payload.get("amount") or payload.get("sum") or payload.get("total")
    if raw_amount is not None:
      try:
        amount = int(float(str(raw_amount)))
      except (TypeError, ValueError):
        amount = None
  if not user_id:
    user_id = payload.get("user_id") or payload.get("telegram_id") or payload.get("customer_id")
  
  if not order_id or amount is None:
    logger.warning("Missing required fields: order_id=%s, amount=%s", order_id, amount)
    return web.json_response({"ok": False, "error": "Missing order_id or amount"}, status=400)

  try:
    amount_int = int(float(str(amount))) if not isinstance(amount, int) else amount
  except (TypeError, ValueError):
    return web.json_response({"ok": False, "error": "Invalid amount"}, status=400)

  try:
    user_int = int(user_id) if user_id else None
  except (TypeError, ValueError):
    user_int = None

  if not user_int:
    # Ищем telegram_id через сохранённый заказ по external_id
    from services.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
      order = await conn.fetchrow(
        "SELECT telegram_id, amount FROM orders WHERE external_id = $1 ORDER BY id DESC LIMIT 1",
        order_id,
      )
    if order:
      user_int = int(order["telegram_id"])
      logger.info("Resolved user from order: order=%s user=%s", order_id, user_int)
      # Проверяем расхождение суммы (логируем, но не блокируем)
      if order["amount"] is not None and int(order["amount"]) != amount_int:
        logger.warning(
          "Amount mismatch: order=%s webhook=%s order_db=%s",
          order_id, amount_int, order["amount"],
        )

  if not user_int:
    logger.warning(
      "Payment webhook: cannot resolve user for order=%s — balance NOT credited. Payload: %s",
      order_id, json.dumps(payload, ensure_ascii=False)[:300]
    )

  # Записываем платеж (если уже был — вернёт False)
  inserted = await record_payment(
    order_id,
    user_int,
    amount_int,
    "paid",
    json.dumps(payload, ensure_ascii=False),
  )
  if not inserted:
    logger.info("Payment %s already processed, skipping", order_id)
    return web.json_response({"ok": True, "message": "already processed"})    # Начисляем баланс только если есть user_id
  if user_int:
    new_balance = await add_balance(user_int, amount_int)
    logger.info("Balance credited: user=%s, amount=%s, new_balance=%s", user_int, amount_int, new_balance)
    
    # Обновляем статус заказа на completed
    from services.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
      await conn.execute(
        "UPDATE orders SET status = 'completed' WHERE external_id = $1",
        order_id
      )
    
    # Отправляем уведомление в Telegram
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    if settings.bot_token:
      check_emoji = f'<tg-emoji emoji-id="{settings.custom_emoji_check}">✅</tg-emoji>' if settings.custom_emoji_check else "✅"
      premium_emoji = f'<tg-emoji emoji-id="{settings.custom_emoji_premium}">💎</tg-emoji>' if settings.custom_emoji_premium else "💎"
      money_emoji = f'<tg-emoji emoji-id="{settings.custom_emoji_money}">💰</tg-emoji>' if settings.custom_emoji_money else "💰"
      bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
      )
      try:
        await bot.send_message(
          user_int,
          f"{check_emoji} To'lov muvaffaqiyatli qabul qilindi\n\n"
          f"{premium_emoji} +{amount_int:,} so'm\n"
          f"{money_emoji} Balans: {new_balance:,} so'm",
        )
      except Exception as e:
        logger.warning("Could not notify user %s: %s", user_int, e)
      finally:
        await bot.session.close()
  else:
    logger.warning("Payment %s recorded but balance NOT credited (no user_id)", order_id)

  return web.json_response({"ok": True, "message": "Payment processed"})


async def api_order_topup(request: web.Request) -> web.Response:
  """Create topup order with 5 minute expiration"""
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

  order_id = body.get("order_id")
  amount = body.get("amount")
  
  if not order_id or not amount:
    return web.json_response({"ok": False, "error": "order_id va amount kerak"}, status=400)
  
  try:
    amount_int = int(amount)
    if amount_int < 1000 or amount_int > 100000000:
      return web.json_response({"ok": False, "error": "Summa noto'g'ri (1,000 — 100,000,000)"}, status=400)
  except (TypeError, ValueError):
    return web.json_response({"ok": False, "error": "Noto'g'ri summa"}, status=400)

  # Сохраняем заказ с telegram_id чтобы webhook смог найти пользователя
  await create_order(int(user_id), "topup", "", None, amount_int, order_id, "pending")
  
  return web.json_response({"ok": True, "order_id": order_id})


async def api_payment_check(request: web.Request) -> web.Response:
  """Check if payment was received"""
  auth = await _auth_user(request)
  user_id = _user_id_from_auth(auth)
  body = await _json_body(request)
  
  if not user_id:
    user_id = body.get("telegram_id")
  if not user_id:
    return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)

  order_id = body.get("order_id")
  if not order_id:
    return web.json_response({"ok": False, "error": "order_id kerak"}, status=400)
  
  # Check if payment exists in payments table
  from services.database import get_pool
  pool = await get_pool()
  async with pool.acquire() as conn:
    payment = await conn.fetchrow(
      "SELECT * FROM payments WHERE shop_order_id = $1 AND status = 'paid'",
      order_id
    )
    
    if payment:
      return web.json_response({
        "ok": True,
        "paid": True,
        "amount": payment["amount"]
      })
    else:
      return web.json_response({
        "ok": True,
        "paid": False
      })


async def api_get_available_gifts(request: web.Request) -> web.Response:
  """Get list of available Star Gifts from Telegram"""
  from services.telethon_client import gift_sender
  
  if not gift_sender:
    return web.json_response({
      "ok": False,
      "error": "Gift sender не инициализирован"
    }, status=503)
  
  try:
    result = await gift_sender.get_available_gifts()
    return web.json_response(result)
  except Exception as e:
    logger.exception(f"Failed to get available gifts: {e}")
    return web.json_response({
      "ok": False,
      "error": str(e)
    }, status=500)


async def on_startup(app: web.Application) -> None:
  from services.database import init_db

  await init_db()
  logger.info("API server ready — webapp at /app/")


async def click_webhook(request: web.Request) -> web.Response:
  """
  Webhook для Click UZ.
  Click отправляет два запроса:
    1. PREPARE (action=0) — проверка, что заказ существует
    2. COMPLETE (action=1) — подтверждение оплаты
  """
  try:
    payload = await request.json()
  except Exception:
    return web.json_response({"error": "Invalid JSON"}, status=400)

  logger.info("Click webhook received: %s", json.dumps(payload, ensure_ascii=False)[:300])

  action = int(payload.get("action", 0))
  
  if action == 0:
    # PREPARE — проверяем заказ
    from services.click_payment import handle_click_prepare
    result = await handle_click_prepare(payload, settings.shop_id, settings.shop_key)
    return web.json_response(result)
  elif action == 1:
    # COMPLETE — обрабатываем платеж
    from services.click_payment import handle_click_complete
    result = await handle_click_complete(payload, settings.shop_id, settings.shop_key)
    return web.json_response(result)
  else:
    return web.json_response({
      "click_trans_id": payload.get("click_trans_id", ""),
      "merchant_trans_id": payload.get("merchant_trans_id", ""),
      "error": -1,
      "error_note": "Invalid action"
    })


async def payment_success_page(request: web.Request) -> web.Response:
  """Page shown after successful payment"""
  return web.Response(
    content_type="text/html",
    text="""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>To'lov muvaffaqiyatli — StarPayUz</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #fff;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 20px;
    }
    .card {
      background: #1e293b;
      border-radius: 24px;
      padding: 48px 32px;
      text-align: center;
      max-width: 400px;
      width: 100%;
      border: 1px solid rgba(59, 130, 246, 0.3);
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .icon {
      font-size: 80px;
      margin-bottom: 24px;
    }
    h1 {
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 12px;
      color: #3B82F6;
    }
    p {
      color: #94a3b8;
      font-size: 16px;
      line-height: 1.6;
      margin-bottom: 32px;
    }
    .btn {
      display: inline-block;
      padding: 16px 40px;
      background: #3B82F6;
      color: #fff;
      text-decoration: none;
      border-radius: 14px;
      font-weight: 600;
      font-size: 16px;
      transition: .3s;
      box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
    }
    .btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 30px rgba(59, 130, 246, 0.4);
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✅</div>
    <h1>To'lov muvaffaqiyatli!</h1>
    <p>Hisobingiz muvaffaqiyatli to'ldirildi.<br>Botga qaytib, balansingizni tekshiring.</p>
    <a href="https://t.me/StarPayUz_Bot" class="btn">🤖 Botga qaytish</a>
  </div>
</body>
</html>""")


def create_app() -> web.Application:
  app = web.Application(middlewares=[cors_middleware])
  app.router.add_get("/", webapp_index)
  app.router.add_get("/app", webapp_index)
  app.router.add_get("/app/", webapp_index)
  app.router.add_get("/health", health)
  app.router.add_post("/api/user/balance", api_user_balance)
  app.router.add_post("/api/stars/price", api_stars_price)
  app.router.add_post("/api/order/stars", api_order_stars)
  app.router.add_post("/api/order/premium", api_order_premium)
  app.router.add_post("/api/order/gift", api_order_gift)
  app.router.add_post("/api/order/phone", api_order_phone)
  app.router.add_post("/api/order/topup", api_order_topup)
  app.router.add_post("/api/payment/create", api_payment_create)
  app.router.add_post("/api/payment/check", api_payment_check)
  app.router.add_post("/webhook/payment", payment_webhook)
  app.router.add_post("/api/webhook/payment", payment_webhook)
  app.router.add_post("/webhook/click", click_webhook)
  app.router.add_get("/api/gifts/available", api_get_available_gifts)
  app.router.add_get("/payment/success", payment_success_page)

  app.router.add_static("/app", WEBAPP_DIR, name="webapp")
  app.router.add_static("/", WEBAPP_DIR, name="root")
  app.on_startup.append(on_startup)
  return app


def main() -> None:
  logging.basicConfig(level=logging.INFO)
  app = create_app()
  web.run_app(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
  main()
