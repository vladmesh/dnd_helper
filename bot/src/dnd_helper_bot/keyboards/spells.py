from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_spells_root_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Список заклинаний", callback_data="spell:list:page:1")],
        [InlineKeyboardButton("Случайное заклинание", callback_data="spell:random")],
        [InlineKeyboardButton("Поиск заклинания", callback_data="spell:search")],
    ])


