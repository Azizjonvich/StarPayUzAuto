import aiosqlite
import asyncio
from datetime import datetime
from typing import Optional, List
import config


class Database:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
    
    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0.0,
                    referrals INTEGER DEFAULT 0,
                    referrer_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_activity TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    product_type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    payment_url TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    transaction_type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[dict]:
        """Get user by Telegram ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_by_sp_id(self, sp_id: int) -> Optional[dict]:
        """Get user by internal StarPayUz ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (sp_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def create_user(self, user_id: int, username: str = None, 
                         first_name: str = None, referrer_id: int = None) -> dict:
        """Create new user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO users (user_id, username, first_name, referrer_id)
                   VALUES (?, ?, ?, ?)""",
                (user_id, username, first_name, referrer_id)
            )
            
            # Update referrer if exists
            if referrer_id:
                await db.execute(
                    """UPDATE users 
                       SET referrals = referrals + 1, balance = balance + 5000
                       WHERE user_id = ?""",
                    (referrer_id,)
                )
            
            await db.commit()
            return await self.get_user(user_id)
    
    async def update_user_activity(self, user_id: int):
        """Update user's last activity"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_activity = ? WHERE user_id = ?",
                (datetime.utcnow().isoformat(), user_id)
            )
            await db.commit()
    
    async def update_balance(self, user_id: int, amount: float, operation: str = 'add'):
        """Update user balance by Telegram ID"""
        async with aiosqlite.connect(self.db_path) as db:
            if operation == 'add':
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (amount, user_id)
                )
            else:  # subtract
                await db.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (amount, user_id)
                )
            await db.commit()

    async def update_balance_by_sp_id(
        self, sp_id: int, amount: float, operation: str = "add"
    ) -> Optional[dict]:
        """Update user balance by internal StarPayUz ID"""
        user = await self.get_user_by_sp_id(sp_id)
        if not user:
            return None
        await self.update_balance(user["user_id"], amount, operation)
        return await self.get_user_by_sp_id(sp_id)
    
    async def create_order(self, order_id: str, user_id: int, product_type: str,
                          amount: int, price: float) -> dict:
        """Create new order"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO orders (order_id, user_id, product_type, amount, price)
                   VALUES (?, ?, ?, ?, ?)""",
                (order_id, user_id, product_type, amount, price)
            )
            await db.commit()
            return await self.get_order(order_id)
    
    async def get_order(self, order_id: str) -> Optional[dict]:
        """Get order by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM orders WHERE order_id = ?", (order_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def update_order(self, order_id: str, **kwargs):
        """Update order fields"""
        async with aiosqlite.connect(self.db_path) as db:
            for key, value in kwargs.items():
                await db.execute(
                    f"UPDATE orders SET {key} = ? WHERE order_id = ?",
                    (value, order_id)
                )
            await db.commit()
    
    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[dict]:
        """Get user's orders"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM orders WHERE user_id = ? 
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_referrals(self, user_id: int) -> List[dict]:
        """Get user's referrals"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE referrer_id = ?", (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


# Global database instance
db = Database()


async def init_db():
    """Initialize database"""
    await db.init_db()
