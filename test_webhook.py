"""Test webhook for automatic balance top-up"""
import asyncio
import aiohttp
import json
import hashlib
import hmac

# Configuration
RAILWAY_URL = "https://worker-production-679d.up.railway.app"
SHOP_ID = "304216"
SHOP_KEY = "5QLEKZ625U"
TEST_USER_ID = 8784918764  # Your Telegram ID
TEST_AMOUNT = 50000  # 50,000 sum


def generate_signature(payload: dict, shop_key: str) -> str:
    """Generate HMAC signature for payment webhook"""
    # Remove signature field if exists
    data = {k: v for k, v in payload.items() if k not in ("sign", "signature", "hash")}
    # Sort and create string
    check_string = "&".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    # Generate HMAC-SHA256
    signature = hmac.new(
        shop_key.encode(),
        check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


async def test_payment_webhook():
    """Send test payment webhook to check if bot receives payment automatically"""
    
    # Create test payment payload
    import time
    order_id = f"test_{int(time.time())}"
    
    payload = {
        "shop_id": SHOP_ID,
        "order_id": order_id,
        "amount": TEST_AMOUNT,
        "status": "paid",
        "user_id": TEST_USER_ID,
        "payment_method": "test",
        "created_at": "2026-06-10T15:00:00Z"
    }
    
    # Generate signature
    signature = generate_signature(payload, SHOP_KEY)
    payload["signature"] = signature
    
    print("=" * 60)
    print("🧪 TESTING AUTOMATIC PAYMENT WEBHOOK")
    print("=" * 60)
    print(f"📍 URL: {RAILWAY_URL}/webhook/payment")
    print(f"👤 User ID: {TEST_USER_ID}")
    print(f"💰 Amount: {TEST_AMOUNT:,} so'm")
    print(f"🔑 Order ID: {order_id}")
    print(f"🔒 Signature: {signature[:20]}...")
    print("=" * 60)
    print()
    
    # Send webhook
    try:
        async with aiohttp.ClientSession() as session:
            print("📤 Sending webhook to Railway server...")
            async with session.post(
                f"{RAILWAY_URL}/webhook/payment",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                status = response.status
                try:
                    result = await response.json()
                except:
                    result = {"text": await response.text()}
                
                print()
                print("=" * 60)
                print("📥 RESPONSE FROM SERVER")
                print("=" * 60)
                print(f"Status: {status}")
                print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print("=" * 60)
                print()
                
                if status == 200 and result.get("ok"):
                    print("✅ SUCCESS! Webhook processed successfully!")
                    print()
                    print("🎉 Check your Telegram - you should receive:")
                    print(f"   ✅ Hisob to'ldirildi: {TEST_AMOUNT:,} so'm")
                    print(f"   💰 Yangi balans: [your_new_balance] so'm")
                    print()
                    print("💡 If you received the message - AUTOMATIC PAYMENTS WORK! 🚀")
                else:
                    print("⚠️  Webhook was received but not processed correctly")
                    print("Check Railway logs for details")
                
    except asyncio.TimeoutError:
        print("❌ ERROR: Request timed out")
        print("Check if Railway server is running")
    except aiohttp.ClientConnectorError as e:
        print(f"❌ ERROR: Cannot connect to server: {e}")
        print("Check Railway URL and network connection")
    except Exception as e:
        print(f"❌ ERROR: {e}")


async def check_health():
    """Check if Railway server is running"""
    print("🔍 Checking if Railway server is running...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RAILWAY_URL}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                result = await response.json()
                if result.get("ok"):
                    print(f"✅ Server is running: {result.get('service')}")
                    return True
    except Exception as e:
        print(f"❌ Server is not accessible: {e}")
        return False
    return False


async def main():
    print()
    print("🤖 StarPayUz - Automatic Payment Test")
    print()
    
    # Check server health
    if not await check_health():
        print()
        print("⚠️  Cannot reach Railway server. Please check:")
        print("   1. Railway deployment is running")
        print("   2. URL is correct: https://worker-production-679d.up.railway.app")
        return
    
    print()
    input("Press ENTER to send test payment webhook...")
    print()
    
    await test_payment_webhook()
    
    print()
    print("=" * 60)
    print("📝 NEXT STEPS")
    print("=" * 60)
    print()
    print("1. Check your Telegram bot - did you receive payment notification?")
    print("2. Check Railway logs: railway logs")
    print("3. Check PostgreSQL database - did balance increase?")
    print()
    print("If everything works - your automatic payment system is READY! 🎉")
    print()


if __name__ == "__main__":
    asyncio.run(main())
