import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "starpay.db"


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                sp_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                referrals INTEGER NOT NULL DEFAULT 0,
                referred_by INTEGER,
                language TEXT NOT NULL DEFAULT 'uz',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                product_type TEXT NOT NULL,
                target_username TEXT,
                quantity INTEGER,
                amount INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                external_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                shop_order_id TEXT UNIQUE,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                raw_payload TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        try:
            await db.execute("ALTER TABLE users ADD COLUMN sp_id INTEGER UNIQUE")
        except aiosqlite.OperationalError:
            pass
        await db.commit()


async def _next_sp_id(db: aiosqlite.Connection) -> int:
    cur = await db.execute("SELECT COALESCE(MAX(sp_id), 0) + 1 FROM users")
    row = await cur.fetchone()
    return row[0] if row else 1


async def ensure_user(
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    referred_by: int | None = None,
) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        if row:
            user = dict(row)
            if user.get("sp_id") is None:
                sp_id = await _next_sp_id(db)
                await db.execute(
                    "UPDATE users SET sp_id = ? WHERE telegram_id = ?",
                    (sp_id, telegram_id),
                )
                await db.commit()
                user["sp_id"] = sp_id
            return user
        sp_id = await _next_sp_id(db)
        await db.execute(
            """
            INSERT INTO users (telegram_id, sp_id, username, full_name, referred_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, sp_id, username, full_name, referred_by),
        )
        if referred_by:
            await db.execute(
                "UPDATE users SET referrals = referrals + 1 WHERE telegram_id = ?",
                (referred_by,),
            )
        await db.commit()
        cur = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        return dict(row)


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_user_by_sp_id(sp_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE sp_id = ?", (sp_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def update_balance_by_sp_id(
    sp_id: int, amount: int, operation: str = "add"
) -> dict | None:
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
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )
        await db.commit()
        cur = await db.execute(
            "SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def deduct_balance(telegram_id: int, amount: int) -> bool:
    user = await get_user(telegram_id)
    if not user or user["balance"] < amount:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE telegram_id = ? AND balance >= ?",
            (amount, telegram_id, amount),
        )
        await db.commit()
        return db.total_changes > 0


async def set_language(telegram_id: int, lang: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET language = ? WHERE telegram_id = ?",
            (lang, telegram_id),
        )
        await db.commit()


async def create_order(
    telegram_id: int,
    product_type: str,
    target_username: str,
    quantity: int | None,
    amount: int | None,
    external_id: str | None = None,
    status: str = "pending",
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO orders (telegram_id, product_type, target_username, quantity, amount, status, external_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                product_type,
                target_username,
                quantity,
                amount,
                status,
                external_id,
            ),
        )
        await db.commit()
        return cur.lastrowid or 0


async def get_user_orders(telegram_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT * FROM orders WHERE telegram_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (telegram_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def record_payment(
    shop_order_id: str,
    telegram_id: int | None,
    amount: int,
    status: str,
    raw_payload: str,
) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """
                INSERT INTO payments (shop_order_id, telegram_id, amount, status, raw_payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (shop_order_id, telegram_id, amount, status, raw_payload),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False
