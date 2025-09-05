from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from dnd_helper_bot.utils.i18n import t


async def _build_main_menu_inline_i18n(lang: str) -> InlineKeyboardMarkup:
    dice = "Roll dice" if lang == "en" else "Бросить кубики"
    best = await t("menu.main.bestiary", lang, default=("Bestiary" if lang == "en" else "Бестиарий"))
    spells = "Spells" if lang == "en" else "Заклинания"
    settings = "Settings" if lang == "en" else "Настройки"
    rows = [
        [InlineKeyboardButton(dice, callback_data="menu:dice")],
        [InlineKeyboardButton(best, callback_data="menu:monsters"), InlineKeyboardButton(spells, callback_data="menu:spells")],
        [InlineKeyboardButton(settings, callback_data="menu:settings")],
    ]
    return InlineKeyboardMarkup(rows)


