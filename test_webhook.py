"""
Test script for payment webhook and related endpoints.
Tests:
  1. Health check
  2. Balance check (real user from DB)
  3. Create topup order
  4. Simulate webhook payment → balance credited
  5. Check payment status
  6. Verify balance increased
  7. Get available gifts
"""

import asyncio
import json
import time
import aiohttp

API_BASE = "https://worker-production-679d.up.railway.app"
TEST_USER_ID = 8784918764  # Admin user ID from .env

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ️  {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠️  {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{CYAN}{'─'*50}{RESET}\n{BOLD}  {msg}{RESET}\n{BOLD}{CYAN}{'─'*50}{RESET}")


async def run_tests():
    async with aiohttp.ClientSession() as session:

        # ─── 1. Health Check ───────────────────────────────────
        header("TEST 1: Health Check")
        try:
            async with session.get(f"{API_BASE}/health") as r:
                data = await r.json()
                if data.get("ok"):
                    ok(f"Server online: {data}")
                else:
                    fail(f"Bad response: {data}")
        except Exception as e:
            fail(f"Cannot reach server: {e}")
            print(f"\n{RED}⛔ Server is down. Stop.{RESET}")
            return

        # ─── 2. Balance Check ──────────────────────────────────
        header("TEST 2: Balance Check")
        balance_before = 0
        try:
            async with session.post(
                f"{API_BASE}/api/user/balance",
                json={"telegram_id": TEST_USER_ID},
            ) as r:
                data = await r.json()
                if data.get("ok"):
                    balance_before = data["balance"]
                    ok(f"Balance: {balance_before:,} so'm")
                else:
                    warn(f"Balance error: {data}")
        except Exception as e:
            fail(f"Request error: {e}")

        # ─── 3. Create Topup Order ─────────────────────────────
        header("TEST 3: Create Topup Order")
        order_id = f"test_topup_{int(time.time())}_{TEST_USER_ID}"
        test_amount = 5000  # 5,000 so'm
        try:
            async with session.post(
                f"{API_BASE}/api/order/topup",
                json={
                    "telegram_id": TEST_USER_ID,
                    "order_id": order_id,
                    "amount": test_amount,
                },
            ) as r:
                data = await r.json()
                if data.get("ok"):
                    ok(f"Order created: {order_id}")
                    info(f"Amount: {test_amount:,} so'm")
                else:
                    warn(f"Order creation: {data}")
                    # Продолжаем — может минимум другой, создадим вручную
        except Exception as e:
            fail(f"Request error: {e}")

        # ─── 4. Simulate Payment Webhook ───────────────────────
        header("TEST 4: Simulate Payment Webhook (main route)")
        webhook_payload = {
            "order_id": order_id,
            "amount": test_amount,
            "user_id": TEST_USER_ID,
            "status": "paid",
            # shop_id НЕ передаём — реальный webhook от платёжки его тоже может не слать
        }
        info(f"Sending to /webhook/payment")
        info(f"Payload: {json.dumps(webhook_payload, ensure_ascii=False)}")
        try:
            async with session.post(
                f"{API_BASE}/webhook/payment",
                json=webhook_payload,
            ) as r:
                data = await r.json()
                info(f"Response ({r.status}): {data}")
                if data.get("ok"):
                    ok("Webhook accepted!")
                else:
                    fail(f"Webhook failed: {data}")
        except Exception as e:
            fail(f"Request error: {e}")

        # Небольшая пауза чтобы БД успела обновиться
        await asyncio.sleep(1)

        # ─── 5. Check Payment Status ───────────────────────────
        header("TEST 5: Check Payment Status in DB")
        try:
            async with session.post(
                f"{API_BASE}/api/payment/check",
                json={
                    "telegram_id": TEST_USER_ID,
                    "order_id": order_id,
                },
            ) as r:
                data = await r.json()
                info(f"Response: {data}")
                if data.get("ok") and data.get("paid"):
                    ok(f"Payment marked as PAID in DB! Amount: {data.get('amount'):,} so'm")
                else:
                    fail(f"Payment NOT found in DB: {data}")
        except Exception as e:
            fail(f"Request error: {e}")

        # ─── 6. Verify Balance Increased ──────────────────────
        header("TEST 6: Verify Balance Increased")
        try:
            async with session.post(
                f"{API_BASE}/api/user/balance",
                json={"telegram_id": TEST_USER_ID},
            ) as r:
                data = await r.json()
                if data.get("ok"):
                    balance_after = data["balance"]
                    diff = balance_after - balance_before
                    info(f"Balance before: {balance_before:,} so'm")
                    info(f"Balance after:  {balance_after:,} so'm")
                    info(f"Difference:     {diff:+,} so'm")
                    if diff == test_amount:
                        ok(f"Balance correctly increased by {test_amount:,} so'm ✨")
                    elif diff > 0:
                        warn(f"Balance increased but by different amount: {diff:,} (expected {test_amount:,})")
                    else:
                        fail(f"Balance did NOT increase! Check webhook processing.")
                else:
                    fail(f"Balance error: {data}")
        except Exception as e:
            fail(f"Request error: {e}")

        # ─── 7. Test Duplicate Webhook (should be ignored) ─────
        header("TEST 7: Duplicate Webhook (should be ignored)")
        try:
            async with session.post(
                f"{API_BASE}/webhook/payment",
                json=webhook_payload,
            ) as r:
                data = await r.json()
                if data.get("message") == "already processed":
                    ok("Duplicate correctly ignored!")
                else:
                    warn(f"Unexpected response: {data}")
        except Exception as e:
            fail(f"Request error: {e}")

        # ─── 8. Get Available Gifts ────────────────────────────
        header("TEST 8: Get Available Gifts from Telegram")
        try:
            async with session.get(f"{API_BASE}/api/gifts/available") as r:
                data = await r.json()
                if data.get("ok"):
                    gifts = data.get("gifts", [])
                    ok(f"Got {len(gifts)} gifts from Telegram")
                    print()
                    for g in gifts[:10]:  # Показываем первые 10
                        limited = " [LIMITED]" if g.get("limited") else ""
                        avail = f" ({g.get('availability_remains')}/{g.get('availability_total')} left)" if g.get("availability_total") else ""
                        print(f"    {'⭐' if not g.get('limited') else '💎'} ID: {g['id']}  Stars: {g.get('stars', '?')}{limited}{avail}")
                    if len(gifts) > 10:
                        info(f"... and {len(gifts)-10} more")
                else:
                    warn(f"Gifts error: {data.get('error')}")
        except Exception as e:
            fail(f"Request error: {e}")

        # ─── 9. Alt Webhook Route ──────────────────────────────
        header("TEST 9: Alt Webhook Route (/api/webhook/payment)")
        order_id2 = f"test_topup_{int(time.time())}_alt"
        # Сначала создадим заказ
        try:
            async with session.post(
                f"{API_BASE}/api/order/topup",
                json={"telegram_id": TEST_USER_ID, "order_id": order_id2, "amount": 3000},
            ) as r:
                pass  # игнорируем ответ

            async with session.post(
                f"{API_BASE}/api/webhook/payment",
                json={
                    "order_id": order_id2,
                    "amount": 3000,
                    "user_id": TEST_USER_ID,
                    "status": "paid",
                },
            ) as r:
                data = await r.json()
                if data.get("ok"):
                    ok(f"Alt route works: {data}")
                else:
                    warn(f"Alt route response: {data}")
        except Exception as e:
            fail(f"Request error: {e}")

        # ─── Summary ───────────────────────────────────────────
        print(f"\n{BOLD}{GREEN}{'='*50}{RESET}")
        print(f"{BOLD}{GREEN}  TESTS COMPLETE{RESET}")
        print(f"{BOLD}{GREEN}{'='*50}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
