from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_main_menu_inline(lang: str = "ru") -> InlineKeyboardMarkup:
    dice = "Roll dice" if lang == "en" else "Бросить кубики"
    best = "Bestiary" if lang == "en" else "Бестиарий"
    spells = "Spells" if lang == "en" else "Заклинания"
    settings = "Settings" if lang == "en" else "Настройки"
    rows = [
        [InlineKeyboardButton(dice, callback_data="menu:dice")],
        [
            InlineKeyboardButton(best, callback_data="menu:monsters"),
            InlineKeyboardButton(spells, callback_data="menu:spells"),
        ],
        [InlineKeyboardButton(settings, callback_data="menu:settings")],
    ]
    return InlineKeyboardMarkup(rows)

