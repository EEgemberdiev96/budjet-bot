import asyncio
from datetime import date, timedelta
from collections import defaultdict

MONTHS_RU = {
    1: "январь", 2: "февраль", 3: "март", 4: "апрель",
    5: "май", 6: "июнь", 7: "июль", 8: "август",
    9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
}

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from app.db.queries import (ensure_user, save_transaction, get_user_name,
                             get_transactions_by_day, get_transactions_by_period,
                             get_period_totals)
from app.services.gpt_parser import parse_expense
from app.services.transcriber import transcribe_audio
from app.services.analytics import get_analytics
from app.handlers.common import Registration

router = Router()

CURRENCY_SYMBOL = {"KGS": "сом", "USD": "$"}


def build_report(rows, title: str) -> str:
    if not rows:
        return f"{title}\nРасходов нет."

    by_category_kgs = defaultdict(float)
    by_category_usd = defaultdict(float)

    for r in rows:
        if r["currency"] == "KGS":
            by_category_kgs[r["category"]] += float(r["amount"])
        else:
            by_category_usd[r["category"]] += float(r["amount"])

    total_kgs = sum(by_category_kgs.values())
    total_usd = sum(by_category_usd.values())

    lines = [title, ""]

    if by_category_kgs:
        for cat, amt in sorted(by_category_kgs.items(), key=lambda x: -x[1]):
            lines.append(f"• {cat}: {amt:g} сом")
    if by_category_usd:
        for cat, amt in sorted(by_category_usd.items(), key=lambda x: -x[1]):
            lines.append(f"• {cat}: {amt:g} $")

    lines.append("")
    if total_kgs:
        lines.append(f"Итого: {total_kgs:g} сом")
    if total_usd:
        lines.append(f"Итого: {total_usd:g} $")

    return "\n".join(lines)


async def save_and_reply(message: Message, text: str, original_text: str):
    parsed = await parse_expense(text)
    if not parsed:
        await message.answer(f"Не смог распознать расход. Попробуй ещё раз.")
        return

    amount = float(parsed["amount"])
    currency = parsed.get("currency", "KGS")
    category = parsed.get("category", "Другое")
    description = parsed.get("description", "")

    await save_transaction(
        user_id=message.from_user.id,
        amount=amount,
        currency=currency,
        category=category,
        description=description,
        original_text=original_text,
    )

    name = await get_user_name(message.from_user.id)
    name_str = f", {name}" if name else ""
    symbol = CURRENCY_SYMBOL.get(currency, currency)
    await message.answer(
        f"✅ Записал{name_str}: {amount:g} {symbol} — {description}\n"
        f"Категория: {category}"
    )


@router.message(F.text & ~F.text.startswith("/") & F.text.not_in(["📅 День", "📊 Неделя", "📊 Месяц"]))
async def handle_expense(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == Registration.waiting_for_name.state:
        return

    await ensure_user(message.from_user.id, message.from_user.username)
    await save_and_reply(message, message.text, message.text)


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    await ensure_user(message.from_user.id, message.from_user.username)

    file = await bot.get_file(message.voice.file_id)
    audio_bytes = await bot.download_file(file.file_path)
    text = await transcribe_audio(audio_bytes.read(), "audio.ogg")

    parsed = await parse_expense(text)
    if not parsed:
        await message.answer(f"🎤 Распознал: «{text}»\nНе смог найти расход.")
        return

    amount = float(parsed["amount"])
    currency = parsed.get("currency", "KGS")
    category = parsed.get("category", "Другое")
    description = parsed.get("description", "")

    await save_transaction(
        user_id=message.from_user.id,
        amount=amount,
        currency=currency,
        category=category,
        description=description,
        original_text=text,
    )

    name = await get_user_name(message.from_user.id)
    name_str = f", {name}" if name else ""
    symbol = CURRENCY_SYMBOL.get(currency, currency)
    await message.answer(
        f"🎤 Распознал: «{text}»\n"
        f"✅ Записал{name_str}: {amount:g} {symbol} — {description}\n"
        f"Категория: {category}"
    )


async def show_day(message: Message, target_date: str):
    rows = await get_transactions_by_day(message.from_user.id, target_date)
    d = date.fromisoformat(target_date)

    if not rows:
        name = await get_user_name(message.from_user.id)
        name_str = f", {name}" if name else ""
        await message.answer(f"За {d.strftime('%d.%m.%Y')} расходов нет{name_str}.")
        return

    total_kgs = sum(r["amount"] for r in rows if r["currency"] == "KGS")
    total_usd = sum(r["amount"] for r in rows if r["currency"] == "USD")

    lines = [f"📅 Расходы за {d.strftime('%d.%m.%Y')}:\n"]
    for r in rows:
        symbol = CURRENCY_SYMBOL.get(r["currency"], r["currency"])
        lines.append(f"• {r['amount']:g} {symbol} — {r['description']} [{r['category']}]")

    if total_kgs:
        lines.append(f"\nИтого: {total_kgs:g} сом")
    if total_usd:
        lines.append(f"Итого: {total_usd:g} $")

    month_ago = d - timedelta(days=30)
    current_totals, prev_totals = await asyncio.gather(
        get_period_totals(message.from_user.id, target_date, target_date),
        get_period_totals(message.from_user.id, month_ago.isoformat(), (d - timedelta(days=1)).isoformat()),
    )
    insight = await get_analytics(current_totals, prev_totals, "день")
    if insight:
        lines.append(f"\n💡 {insight}")

    await message.answer("\n".join(lines))


@router.message(F.text == "📅 День")
async def btn_day(message: Message):
    await show_day(message, date.today().isoformat())


@router.message(Command("day"))
async def cmd_day(message: Message):
    args = message.text.split()
    target_date = args[1] if len(args) >= 2 else date.today().isoformat()
    try:
        date.fromisoformat(target_date)
    except ValueError:
        await message.answer("Неверный формат даты. Используй: /day YYYY-MM-DD")
        return
    await show_day(message, target_date)


@router.message(F.text == "📊 Неделя")
@router.message(Command("week"))
async def cmd_week(message: Message):
    today = date.today()
    week_ago = today - timedelta(days=6)
    prev_end = week_ago - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)

    rows, current_totals, prev_totals = await asyncio.gather(
        get_transactions_by_period(message.from_user.id, week_ago.isoformat(), today.isoformat()),
        get_period_totals(message.from_user.id, week_ago.isoformat(), today.isoformat()),
        get_period_totals(message.from_user.id, prev_start.isoformat(), prev_end.isoformat()),
    )

    title = f"📊 Расходы за неделю ({week_ago.strftime('%d.%m.%Y')} — {today.strftime('%d.%m.%Y')}):"
    report = build_report(rows, title)
    insight = await get_analytics(current_totals, prev_totals, "неделя")
    if insight:
        report += f"\n\n💡 {insight}"
    await message.answer(report)


@router.message(F.text == "📊 Месяц")
@router.message(Command("month"))
async def cmd_month(message: Message):
    today = date.today()
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    rows, current_totals, prev_totals = await asyncio.gather(
        get_transactions_by_period(message.from_user.id, month_start.isoformat(), today.isoformat()),
        get_period_totals(message.from_user.id, month_start.isoformat(), today.isoformat()),
        get_period_totals(message.from_user.id, prev_month_start.isoformat(), prev_month_end.isoformat()),
    )

    title = f"📊 Расходы за {MONTHS_RU[today.month]} {today.year}:"
    report = build_report(rows, title)
    insight = await get_analytics(current_totals, prev_totals, f"{MONTHS_RU[today.month]} {today.year}")
    if insight:
        report += f"\n\n💡 {insight}"
    await message.answer(report)
