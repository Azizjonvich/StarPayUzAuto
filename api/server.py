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
  gift_id = (body.get("gift_id") or "default").strip()

  try:
    result = await fragment.buy_gift(username, gift_id)
    order_id = await create_order(
      int(user_id), "gift", username, None, None, str(result.get("id", "")), "completed"
    )
    return web.json_response({"ok": True, "order_id": order_id, "result": result})
  except FragmentAPIError as e:
    await create_order(int(user_id), "gift", username, None, None, status="failed")
    return web.json_response({"ok": False, "error": str(e)}, status=400)


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
    if amount_int < 10000 or amount_int > 10000000:
      return web.json_response({"ok": False, "error": "Summa 10,000 dan 10,000,000 oralig'ida bo'lishi kerak"}, status=400)
  except (TypeError, ValueError):
    return web.json_response({"ok": False, "error": "Noto'g'ri summa"}, status=400)

  # Create order in database
  await create_order(int(user_id), "topup", "", amount_int, amount_int, order_id, "pending")
  
  # Import api_client to create payment
  from api_client import api_client
  
  result = await api_client.create_payment(
    amount=amount_int,
    order_id=order_id,
    user_id=int(user_id),
    description=f"StarPayUz - Hisobni to'ldirish {amount_int:,} so'm"
  )
  
  if result.get("ok") and result.get("payment_url"):
    return web.json_response({
      "ok": True,
      "payment_url": result["payment_url"],
      "order_id": order_id
    })
  else:
    return web.json_response({
      "ok": False,
      "error": result.get("message", "To'lov yaratishda xatolik")
    }, status=400)


async def payment_webhook(request: web.Request) -> web.Response:
  try:
    payload = await request.json()
  except Exception:
    return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

  shop_id = str(payload.get("shop_id", ""))
  if settings.shop_id and shop_id and shop_id != str(settings.shop_id):
    return web.json_response({"ok": False, "error": "Invalid shop_id"}, status=403)

  if settings.shop_key and not verify_shop_signature(payload, settings.shop_key):
    logger.warning("Payment webhook signature mismatch — check SHOP_KEY / payload format")

  status = str(payload.get("status", "paid")).lower()
  if status not in ("paid", "success", "completed", "1", "true"):
    return web.json_response({"ok": True, "message": "ignored status"})

  order_id, amount, user_id = extract_payment_fields(payload)
  if not order_id or not amount:
    return web.json_response({"ok": False, "error": "Missing order_id or amount"}, status=400)

  inserted = await record_payment(
    order_id,
    user_id,
    amount,
    "paid",
    json.dumps(payload, ensure_ascii=False),
  )
  if not inserted:
    return web.json_response({"ok": True, "message": "already processed"})

  if user_id:
    new_balance = await add_balance(user_id, amount)
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    if settings.bot_token:
      bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
      )
      try:
        await bot.send_message(
          user_id,
          f"✅ Hisob to'ldirildi: <b>{amount:,}</b> so'm\n"
          f"💰 Yangi balans: <b>{new_balance:,}</b> so'm",
        )
      except Exception as e:
        logger.warning("Could not notify user %s: %s", user_id, e)
      finally:
        await bot.session.close()

  return web.json_response({"ok": True})


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
    if amount_int < 10000 or amount_int > 10000000:
      return web.json_response({"ok": False, "error": "Summa noto'g'ri"}, status=400)
  except (TypeError, ValueError):
    return web.json_response({"ok": False, "error": "Noto'g'ri summa"}, status=400)

  # Create order in database
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


async def on_startup(app: web.Application) -> None:
  from services.database import init_db

  await init_db()
  logger.info("API server ready — webapp at /app/")


def create_app() -> web.Application:
  app = web.Application(middlewares=[cors_middleware])
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
