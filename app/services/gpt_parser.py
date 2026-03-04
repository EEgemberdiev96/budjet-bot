import json
from groq import AsyncGroq
from app.config import GROQ_API_KEY

client = AsyncGroq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """Ты — помощник для учёта личных расходов.
Пользователь пишет в свободной форме на русском, кыргызском или английском языке.
Твоя задача — извлечь из текста данные о расходе и вернуть JSON.

Правила:
- amount: число (обязательно)
- currency: "KGS" или "USD" (по умолчанию KGS)
- category: одна из следующих категорий:
  Продукты — магазин, рынок (мясо, овощи, фрукты, молоко и т.д.)
  Кафе и рестораны — обеды, ужины вне дома, доставка готовой еды
  Напитки — кофе, чай, соки, смузи вне дома
  Транспорт — такси, автобус, метро, бензин
  Аренда — квартира, офис
  Здоровье — аптека, врач, анализы
  Одежда — одежда, обувь, аксессуары
  Красота — парикмахер, косметика, маникюр
  Образование — курсы, книги, учёба
  Саморазвитие — тренинги, коучинг, подписки на сервисы
  Спорт — спортзал, инвентарь, секции
  Развлечения — кино, концерты, игры
  Связь — телефон, интернет
  Хозтовары — бытовая химия, инструменты, товары для дома
  Другое — всё что не подходит под остальные категории
- description: краткое описание на русском (1-5 слов)

Если в тексте нет расхода — верни {"error": "no_transaction"}.

Отвечай ТОЛЬКО JSON, без лишнего текста."""


async def parse_expense(text: str) -> dict | None:
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    result = json.loads(response.choices[0].message.content)
    if "error" in result:
        return None
    return result
