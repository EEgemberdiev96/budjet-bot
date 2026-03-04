from groq import AsyncGroq
from app.config import GROQ_API_KEY

client = AsyncGroq(api_key=GROQ_API_KEY)


async def get_analytics(current: dict, previous: dict, period_label: str) -> str:
    if not current:
        return ""

    current_total = sum(v for k, v in current.items() if "KGS" in k)
    previous_total = sum(v for k, v in previous.items() if "KGS" in k)

    current_str = "\n".join(f"  {k}: {v:g}" for k, v in sorted(current.items()))
    previous_str = "\n".join(f"  {k}: {v:g}" for k, v in sorted(previous.items())) if previous else "нет данных"

    prompt = f"""Проанализируй расходы пользователя и дай краткий вывод на русском (2-3 предложения максимум).

Текущий период ({period_label}):
{current_str}
Итого KGS: {current_total:g}

Предыдущий период:
{previous_str}
Итого KGS: {previous_total:g}

Напиши:
- Как изменились расходы (если есть данные для сравнения)
- Какая категория самая затратная
- Один короткий совет

Пиши коротко и по делу, без приветствий."""

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()
