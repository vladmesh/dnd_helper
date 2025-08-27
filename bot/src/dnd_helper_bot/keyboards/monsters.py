from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_monsters_root_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Список монстров", callback_data="monster:list:page:1")],
        [InlineKeyboardButton("Случайный монстр", callback_data="monster:random")],
        [InlineKeyboardButton("Поиск монстра", callback_data="monster:search")],
    ])


