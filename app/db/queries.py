from datetime import date as date_type
from app.db.database import get_pool


async def ensure_user(user_id: int, username: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, username)
            VALUES ($1, $2)
            ON CONFLICT (id) DO NOTHING
        """, user_id, username)


async def get_user_name(user_id: int) -> str | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT name FROM users WHERE id = $1", user_id)
        return row["name"] if row else None


async def set_user_name(user_id: int, name: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET name = $1 WHERE id = $2", name, user_id)


async def save_transaction(user_id: int, amount: float, currency: str,
                           category: str, description: str, original_text: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO transactions (user_id, amount, currency, category, description, original_text)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, user_id, amount, currency, category, description, original_text)


async def get_transactions_by_day(user_id: int, target_date: str):
    pool = await get_pool()
    d = date_type.fromisoformat(target_date)
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT amount, currency, category, description, created_at
            FROM transactions
            WHERE user_id = $1
              AND DATE(created_at AT TIME ZONE 'Asia/Bishkek') = $2
            ORDER BY created_at
        """, user_id, d)


async def get_period_totals(user_id: int, date_from: str, date_to: str) -> dict:
    """Возвращает суммы по категориям за период."""
    pool = await get_pool()
    d_from = date_type.fromisoformat(date_from)
    d_to = date_type.fromisoformat(date_to)
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT category, currency, SUM(amount) as total
            FROM transactions
            WHERE user_id = $1
              AND DATE(created_at AT TIME ZONE 'Asia/Bishkek') BETWEEN $2 AND $3
            GROUP BY category, currency
        """, user_id, d_from, d_to)
    result = {}
    for r in rows:
        key = f"{r['category']} ({r['currency']})"
        result[key] = float(r["total"])
    return result


async def get_transactions_by_period(user_id: int, date_from: str, date_to: str):
    pool = await get_pool()
    d_from = date_type.fromisoformat(date_from)
    d_to = date_type.fromisoformat(date_to)
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT amount, currency, category, description, created_at
            FROM transactions
            WHERE user_id = $1
              AND DATE(created_at AT TIME ZONE 'Asia/Bishkek') BETWEEN $2 AND $3
            ORDER BY created_at
        """, user_id, d_from, d_to)
