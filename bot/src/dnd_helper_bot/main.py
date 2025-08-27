import os
import asyncio
import random
from typing import Any, Dict, List

import httpx
import urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


def build_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [["Бросить кубики"], ["Бестиарий", "Заклинания"]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Выберите действие:", reply_markup=build_main_menu())


async def handle_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if text == "Бросить кубики":
        await show_dice_menu(update, context)
    elif text == "Бестиарий":
        await show_bestiarie_menu(update, context)
    elif text == "Заклинания":
        await show_spells_menu(update, context)
    else:
        await update.message.reply_text("Не понимаю команду. Выберите действие:", reply_markup=build_main_menu())


async def show_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("d20", callback_data="dice:d20")],
        [InlineKeyboardButton("d6", callback_data="dice:d6")],
        [InlineKeyboardButton("2d6", callback_data="dice:2d6")],
    ])
    await update.message.reply_text("Бросить кубики:", reply_markup=keyboard)


async def dice_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    kind = query.data.split(":", 1)[1]
    if kind == "d20":
        result = random.randint(1, 20)
        text = f"🎲 d20 → {result}"
    elif kind == "d6":
        result = random.randint(1, 6)
        text = f"🎲 d6 → {result}"
    elif kind == "2d6":
        r1, r2 = random.randint(1, 6), random.randint(1, 6)
        text = f"🎲 2d6 → {r1}+{r2} = {r1 + r2}"
    else:
        text = "Неизвестный бросок"
    await query.edit_message_text(text)


def build_monsters_root_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Список монстров", callback_data="monster:list:page:1")],
        [InlineKeyboardButton("Случайный монстр", callback_data="monster:random")],
        [InlineKeyboardButton("Поиск монстра", callback_data="monster:search")],
    ])


def build_spells_root_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Список заклинаний", callback_data="spell:list:page:1")],
        [InlineKeyboardButton("Случайное заклинание", callback_data="spell:random")],
    ])


async def show_bestiarie_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Бестиарий:", reply_markup=build_monsters_root_keyboard())


async def show_spells_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Заклинания:", reply_markup=build_spells_root_keyboard())


async def api_get(path: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def api_get_one(path: str) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def paginate(items: List[Dict[str, Any]], page: int, page_size: int = 5) -> List[Dict[str, Any]]:
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]


async def monsters_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    all_monsters = await api_get("/monsters")
    total = len(all_monsters)
    if total == 0:
        await query.edit_message_text("Монстров нет.")
        return
    page_items = paginate(all_monsters, page)
    rows: List[List[InlineKeyboardButton]] = []
    for m in page_items:
        label = f"Подробнее: {m.get('description','')} (#{m.get('id')})"
        rows.append([InlineKeyboardButton(label, callback_data=f"monster:detail:{m['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"monster:list:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton("➡️ Далее", callback_data=f"monster:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    markup = InlineKeyboardMarkup(rows)
    await query.edit_message_text(f"Список монстров (стр. {page})", reply_markup=markup)


async def monster_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # Set flag in user_data to treat next text as search query
    context.user_data["awaiting_monster_query"] = True
    await query.edit_message_text("Введите подстроку для поиска по названию монстра:")


async def handle_search_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # If not awaiting search, delegate to menu handler
    if not context.user_data.get("awaiting_monster_query"):
        await handle_menu_text(update, context)
        return
    context.user_data.pop("awaiting_monster_query", None)
    query_text = (update.message.text or "").strip()
    if not query_text:
        await update.message.reply_text("Пустой запрос. Повторите.", reply_markup=build_main_menu())
        return
    q = urllib.parse.quote(query_text)
    try:
        items = await api_get(f"/monsters/search?q={q}")
    except Exception:
        await update.message.reply_text("Ошибка при запросе к API.")
        return
    if not items:
        await update.message.reply_text("Ничего не найдено.", reply_markup=build_main_menu())
        return
    # Build result list as inline buttons to details
    rows: List[List[InlineKeyboardButton]] = []
    for m in items[:10]:
        title = m.get("title") or m.get("description", "<no title>")
        rows.append([InlineKeyboardButton(title, callback_data=f"monster:detail:{m['id']}")])
    rows.append([InlineKeyboardButton("К бестиарию", callback_data="monster:list:page:1")])
    markup = InlineKeyboardMarkup(rows)
    await update.message.reply_text("Результаты поиска:", reply_markup=markup)

async def monster_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    monster_id = int(query.data.split(":")[-1])
    m = await api_get_one(f"/monsters/{monster_id}")
    text = (
        f"{m.get('description','')}\n"
        f"Danger: {m.get('dangerous_lvl','-')}\n"
        f"HP: {m.get('hp','-')}, AC: {m.get('ac','-')}, Speed: {m.get('speed','-')}"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("К списку", callback_data="monster:list:page:1")]])
    await query.edit_message_text(text, reply_markup=markup)


async def monster_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    all_monsters = await api_get("/monsters")
    if not all_monsters:
        await query.edit_message_text("Монстров нет.")
        return
    m = random.choice(all_monsters)
    text = (
        f"{m.get('description','')}{' (random)' }\n"
        f"Danger: {m.get('dangerous_lvl','-')}\n"
        f"HP: {m.get('hp','-')}, AC: {m.get('ac','-')}, Speed: {m.get('speed','-')}"
    )
    await query.edit_message_text(text)


async def spells_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    all_spells = await api_get("/spells")
    total = len(all_spells)
    if total == 0:
        await query.edit_message_text("Заклинаний нет.")
        return
    page_items = paginate(all_spells, page)
    rows: List[List[InlineKeyboardButton]] = []
    for s in page_items:
        label = f"Подробнее: {s.get('description','')} (#{s.get('id')})"
        rows.append([InlineKeyboardButton(label, callback_data=f"spell:detail:{s['id']}")])
    nav: List[InlineKeyboardButton] = []
    if (page - 1) * 5 > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"spell:list:page:{page-1}"))
    if page * 5 < total:
        nav.append(InlineKeyboardButton("➡️ Далее", callback_data=f"spell:list:page:{page+1}"))
    if nav:
        rows.append(nav)
    markup = InlineKeyboardMarkup(rows)
    await query.edit_message_text(f"Список заклинаний (стр. {page})", reply_markup=markup)


async def spell_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    spell_id = int(query.data.split(":")[-1])
    s = await api_get_one(f"/spells/{spell_id}")
    text = (
        f"{s.get('description','')}\n"
        f"Class: {s.get('caster_class','-')}\n"
        f"Distance: {s.get('distance','-')}, School: {s.get('school','-')}"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("К списку", callback_data="spell:list:page:1")]])
    await query.edit_message_text(text, reply_markup=markup)


async def spell_random(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    all_spells = await api_get("/spells")
    if not all_spells:
        await query.edit_message_text("Заклинаний нет.")
        return
    s = random.choice(all_spells)
    text = (
        f"{s.get('description','')}{' (random)' }\n"
        f"Class: {s.get('caster_class','-')}\n"
        f"Distance: {s.get('distance','-')}, School: {s.get('school','-')}"
    )
    await query.edit_message_text(text)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = ApplicationBuilder().token(token).build()

    # Commands
    application.add_handler(CommandHandler("start", start))

    # Text menu and search input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_text))

    # Dice callbacks
    application.add_handler(CallbackQueryHandler(dice_roll, pattern=r"^dice:(d20|d6|2d6)$"))

    # Monsters callbacks
    application.add_handler(CallbackQueryHandler(monsters_list, pattern=r"^monster:list:page:\d+$"))
    application.add_handler(CallbackQueryHandler(monster_detail, pattern=r"^monster:detail:\d+$"))
    application.add_handler(CallbackQueryHandler(monster_random, pattern=r"^monster:random$"))
    application.add_handler(CallbackQueryHandler(monster_search_prompt, pattern=r"^monster:search$"))

    # Spells callbacks
    application.add_handler(CallbackQueryHandler(spells_list, pattern=r"^spell:list:page:\d+$"))
    application.add_handler(CallbackQueryHandler(spell_detail, pattern=r"^spell:detail:\d+$"))
    application.add_handler(CallbackQueryHandler(spell_random, pattern=r"^spell:random$"))

    application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())


