from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_main_menu_inline() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Бросить кубики", callback_data="menu:dice")],
        [
            InlineKeyboardButton("Бестиарий", callback_data="menu:monsters"),
            InlineKeyboardButton("Заклинания", callback_data="menu:spells"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

