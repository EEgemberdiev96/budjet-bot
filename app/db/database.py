import asyncpg
from app.config import DATABASE_URL

_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, ssl='require', statement_cache_size=0)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                name TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                amount NUMERIC(12, 2) NOT NULL,
                currency TEXT NOT NULL DEFAULT 'KGS',
                category TEXT,
                description TEXT,
                original_text TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
