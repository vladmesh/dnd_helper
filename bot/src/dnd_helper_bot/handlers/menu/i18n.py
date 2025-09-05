from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from dnd_helper_bot.utils.i18n import t


async def _build_main_menu_inline_i18n(lang: str) -> InlineKeyboardMarkup:
    dice = await t("dice.menu.title", lang, default=("Roll dice" if lang == "en" else "Бросить кубики"))
    best = await t("menu.bestiary.title", lang, default=("Bestiary" if lang == "en" else "Бестиарий"))
    spells = await t("menu.spells.title", lang, default=("Spells" if lang == "en" else "Заклинания"))
    settings = await t("menu.settings.title", lang, default=("Settings" if lang == "en" else "Настройки"))
    rows = [
        [InlineKeyboardButton(dice, callback_data="menu:dice")],
        [InlineKeyboardButton(best, callback_data="menu:monsters"), InlineKeyboardButton(spells, callback_data="menu:spells")],
        [InlineKeyboardButton(settings, callback_data="menu:settings")],
    ]
    return InlineKeyboardMarkup(rows)


