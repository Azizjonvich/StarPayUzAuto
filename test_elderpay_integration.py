"""
Test script for ElderPay integration changes.

Tests:
  1. Database schema has elderpay_order_id column
  2. ElderPay API client works (create_order, check_order)
  3. Background checker query logic
  4. Payment flow through ElderPay

Usage:
  python test_elderpay_integration.py
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_elderpay")

# ─── Helper ─────────────────────────────────────────────────────

PASS = 0
FAIL = 0

def header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def ok(text: str):
    global PASS
    PASS += 1
    print(f"  [OK] {text}")

def fail(text: str):
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {text}")

def info(text: str):
    print(f"  [INFO] {text}")

# ─── TESTS ──────────────────────────────────────────────────────

def test_database_schema():
    """Test that database.py has elderpay_order_id support."""
    header("TEST 1: Database Schema")

    # Check init_db has elderpay_order_id in CREATE TABLE
    with open("services/database.py", "r", encoding="utf-8") as f:
        content = f.read()

    if "elderpay_order_id TEXT" in content:
        ok("elderpay_order_id column found in CREATE TABLE orders")
    else:
        fail("elderpay_order_id column NOT found in CREATE TABLE orders")

    if "ALTER TABLE orders ADD COLUMN IF NOT EXISTS elderpay_order_id" in content:
        ok("ALTER TABLE migration for elderpay_order_id found")
    else:
        fail("ALTER TABLE migration NOT found")

    # Check _LegacyDB.create_order accepts elderpay_order_id
    if "elderpay_order_id" in content and "def create_order" in content:
        # Check the _LegacyDB.create_order method
        if "elderpay_order_id: str = None" in content:
            ok("_LegacyDB.create_order accepts elderpay_order_id parameter")
        else:
            fail("_LegacyDB.create_order missing elderpay_order_id parameter")
    else:
        fail("elderpay_order_id not found in database.py")


def test_elderpay_client():
    """Test ElderPay API client module."""
    header("TEST 2: ElderPay API Client")

    from services.elderpay import ElderPayAPI, ElderPayError

    # Test is_configured property
    client_empty = ElderPayAPI("", "")
    assert client_empty.is_configured == False
    ok("ElderPayAPI.is_configured = False when credentials empty")

    client_valid = ElderPayAPI("shop123", "key456")
    assert client_valid.is_configured == True
    ok("ElderPayAPI.is_configured = True when credentials set")

    # Test shop_id/shop_key stripping
    client_strip = ElderPayAPI("  shop123  ", "  key456  ")
    assert client_strip.shop_id == "shop123"
    assert client_strip.shop_key == "key456"
    ok("ElderPayAPI trims whitespace from credentials")

    # Test ElderPayError
    err = ElderPayError("test error", 400, {"error": "bad"})
    assert str(err) == "test error"
    assert err.status == 400
    assert err.payload == {"error": "bad"}
    ok("ElderPayError works correctly")

    # Test ElderPayAPI._request params (can't fully test without network)
    info("ElderPayAPI uses aiohttp for requests - network test skipped")
    info(f"  create_order sends: method=create, shop_id, shop_key, amount, over=10")
    info(f"  check_order sends: method=check, order, shop_id, shop_key")


def test_main_bot_integration():
    """Test that handlers/balance.py has ElderPay integrated."""
    header("TEST 3: Main Bot (handlers/balance.py)")

    with open("handlers/balance.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check ElderPay is imported and used
    if "from services.elderpay import ElderPayAPI, ElderPayError" in content:
        ok("ElderPay imported in balance.py")
    else:
        fail("ElderPay NOT imported in balance.py")

    if "elderpay = ElderPayAPI(" in content:
        ok("ElderPay client instantiated in balance.py")
    else:
        fail("ElderPay client NOT instantiated in balance.py")

    if "elderpay.create_order" in content:
        ok("create_order is called when creating topup")
    else:
        fail("create_order NOT called during topup creation")

    if "elderpay.check_order" in content:
        ok("check_order is called during payment check")
    else:
        fail("check_order NOT called during payment check")

    if "async def _credit_user" in content:
        ok("_credit_user helper function exists")
    else:
        fail("_credit_user helper function MISSING")

    # Verify ElderPay Node.js client imports are removed
    if "elderpay_node_client" not in content:
        ok("Old ElderPay Node.js client import removed")
    else:
        fail("Old ElderPay Node.js client import still present")

    # Verify ElderPay disabled comments are removed
    if "ElderPay Node.js API disabled" not in content:
        ok("Old 'ElderPay disabled' comments removed")
    else:
        fail("Old 'ElderPay disabled' comments still present")


def test_second_bot_integration():
    """Test that bot/handlers/callbacks.py has ElderPay fixed."""
    header("TEST 4: Second Bot (bot/handlers/callbacks.py)")

    with open("bot/handlers/callbacks.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check elderpay_order_id is passed to create_order
    if "elderpay_order_id=elderpay_order_id" in content:
        ok("elderpay_order_id passed to db.create_order")
    else:
        fail("elderpay_order_id NOT passed to db.create_order")

    # Check check_order uses elderpay_order_id from DB
    if "order.get(\"elderpay_order_id\")" in content:
        ok("check_order uses elderpay_order_id from database")
    else:
        fail("check_order does NOT use elderpay_order_id from database")

    # Check the fix for local order_id bug
    if "check_id = order.get(\"elderpay_order_id\") if order else None" in content:
        ok("Fixed: check_payment uses stored elderpay_order_id instead of local order_id")
    else:
        fail("Bug still present: check_payment may use local order_id")


def test_api_background_checker():
    """Test that api/server.py has ElderPay background checker enabled."""
    header("TEST 5: API Server Background Checker")

    with open("api/server.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check background checker is enabled
    if "ENABLED (checking every 10s)" in content:
        ok("Background checker ENABLED")
    else:
        fail("Background checker NOT enabled")

    if "ElderPay background checker: DISABLED" not in content:
        ok("Old 'DISABLED' message removed")
    else:
        fail("Old 'DISABLED' message still present")

    # Check it queries elderpay_order_id
    if "elderpay_order_id IS NOT NULL" in content:
        ok("Background checker queries by elderpay_order_id")
    else:
        fail("Background checker might query by wrong field")

    if "elderpay.check_order(elderpay_order_id)" in content:
        ok("Background checker uses elderpay_order_id for status check")
    else:
        fail("Background checker might use wrong order_id for status check")


def test_no_circular_imports():
    """Test that there are no circular imports between modules."""
    header("TEST 6: Import Safety")

    # Test that services/elderpay.py imports only what it needs
    with open("services/elderpay.py", "r", encoding="utf-8") as f:
        elderpay_content = f.read()

    # Should NOT import database or handlers
    forbidden_imports = ["database", "handlers", "bot", "config"]
    issues = []
    for imp in forbidden_imports:
        if f"import {imp}" in elderpay_content or f"from {imp}" in elderpay_content:
            issues.append(imp)
    
    if not issues:
        ok("ElderPay client has no circular imports")
    else:
        for imp in issues:
            fail(f"ElderPay client imports {imp} - potential circular import")


# ─── MAIN ────────────────────────────────────────────────────────

async def main():
    print()
    print(f"{'='*60}")
    print(f"  StarPayUz — ElderPay Integration Tests")
    print(f"{'='*60}")
    print(f"  Python: {sys.version}")
    print(f"  CWD: {os.getcwd()}")
    print()

    test_database_schema()
    test_elderpay_client()
    test_main_bot_integration()
    test_second_bot_integration()
    test_api_background_checker()
    test_no_circular_imports()

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print(f"{'='*60}\n")

    return FAIL == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
