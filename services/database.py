"""Database layer with PostgreSQL support via asyncpg"""
import asyncio
import os
from typing import Any

import asyncpg

# Read DATABASE_URL from env
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Connection pool (created on init_db)
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not DATABASE_URL or not DATABASE_URL.startswith("postgres"):
            raise RuntimeError("DATABASE_URL not set or invalid")
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def init_db() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                sp_id SERIAL UNIQUE,
                username TEXT,
                full_name TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                referrals INTEGER NOT NULL DEFAULT 0,
                referred_by BIGINT,
                language TEXT NOT NULL DEFAULT 'uz',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                product_type TEXT NOT NULL,
                target_username TEXT,
                quantity INTEGER,
                amount INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                external_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                shop_order_id TEXT UNIQUE,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                raw_payload TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


async def ensure_user(
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    referred_by: int | None = None,
) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1", telegram_id
        )
        if row:
            return dict(row)
        
        # Insert with sp_id generated automatically by SERIAL
        await conn.execute(
            """
            INSERT INTO users (telegram_id, username, full_name, referred_by)
            VALUES ($1, $2, $3, $4)
            """,
            telegram_id, username, full_name, referred_by,
        )
        if referred_by:
            await conn.execute(
                "UPDATE users SET referrals = referrals + 1 WHERE telegram_id = $1",
                referred_by,
            )
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1", telegram_id
        )
        return dict(row) if row else {}


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1", telegram_id
        )
        return dict(row) if row else None


async def get_user_by_sp_id(sp_id: int) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE sp_id = $1", sp_id)
        return dict(row) if row else None


async def update_balance_by_sp_id(
    sp_id: int, amount: int, operation: str = "add"
) -> dict[str, Any] | None:
    user = await get_user_by_sp_id(sp_id)
    if not user:
        return None
    if operation == "add":
        await add_balance(user["telegram_id"], amount)
    else:
        ok = await deduct_balance(user["telegram_id"], amount)
        if not ok:
            return None
    return await get_user_by_sp_id(sp_id)


async def add_balance(telegram_id: int, amount: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE users SET balance = balance + $1 WHERE telegram_id = $2 RETURNING balance",
            amount, telegram_id,
        )
        return row["balance"] if row else 0


async def deduct_balance(telegram_id: int, amount: int) -> bool:
    user = await get_user(telegram_id)
    if not user or user["balance"] < amount:
        return False
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE users SET balance = balance - $1 WHERE telegram_id = $2 AND balance >= $1",
            amount, telegram_id,
        )
        return result != "UPDATE 0"


async def set_language(telegram_id: int, lang: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET language = $1 WHERE telegram_id = $2", lang, telegram_id
        )


async def create_order(
    telegram_id: int,
    product_type: str,
    target_username: str,
    quantity: int | None,
    amount: int | None,
    external_id: str | None = None,
    status: str = "pending",
) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO orders (telegram_id, product_type, target_username, quantity, amount, status, external_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            telegram_id, product_type, target_username, quantity, amount, status, external_id,
        )
        return row["id"] if row else 0


async def get_user_orders(telegram_id: int, limit: int = 10) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM orders WHERE telegram_id = $1
            ORDER BY id DESC LIMIT $2
            """,
            telegram_id, limit,
        )
        return [dict(r) for r in rows]


async def record_payment(
    shop_order_id: str,
    telegram_id: int | None,
    amount: int,
    status: str,
    raw_payload: str,
) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO payments (shop_order_id, telegram_id, amount, status, raw_payload)
                VALUES ($1, $2, $3, $4, $5)
                """,
                shop_order_id, telegram_id, amount, status, raw_payload,
            )
            return True
        except asyncpg.UniqueViolationError:
            return False


# Legacy API compatibility layer for handlers that use "from services.database import db"
class _LegacyDB:
    """Compatibility wrapper to match old database.py API"""
    
    async def init_db(self):
        await init_db()
    
    async def get_user(self, user_id: int):
        return await get_user(user_id)
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None, referrer_id: int = None):
        user = await ensure_user(user_id, username, first_name or "", referred_by=referrer_id)
        return user
    
    async def update_balance(self, user_id: int, amount: int, operation: str = "add"):
        if operation == "add":
            await add_balance(user_id, amount)
        else:
            await deduct_balance(user_id, amount)
    
    async def get_user_by_sp_id(self, sp_id: int):
        return await get_user_by_sp_id(sp_id)
    
    async def update_balance_by_sp_id(self, sp_id: int, amount: int, operation: str = "add"):
        return await update_balance_by_sp_id(sp_id, amount, operation)
    
    async def update_user_activity(self, user_id: int):
        # Not needed in new schema - can be a no-op
        pass
    
    async def create_order(self, order_id: str, user_id: int, product_type: str, amount: int, price: int):
        return await create_order(user_id, product_type, "", amount, price, order_id, "pending")
    
    async def update_order(self, order_id: str, **kwargs):
        # Not implemented in services/database - orders are immutable after creation
        pass
    
    async def get_user_orders(self, user_id: int, limit: int = 10):
        return await get_user_orders(user_id, limit)
    
    async def get_referrals(self, user_id: int):
        # Return users referred by this user
        user = await get_user(user_id)
        if not user:
            return []
        # Simple: return empty list for now (referrals count is in user.referrals)
        return []


db = _LegacyDB()
