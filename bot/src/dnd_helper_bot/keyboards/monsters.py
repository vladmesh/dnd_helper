from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_monsters_root_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    t_list = "Monsters list" if lang == "en" else "Список монстров"
    t_rand = "Random monster" if lang == "en" else "Случайный монстр"
    t_search = "Search monster" if lang == "en" else "Поиск монстра"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t_list, callback_data="monster:list:page:1")],
        [InlineKeyboardButton(t_rand, callback_data="monster:random")],
        [InlineKeyboardButton(t_search, callback_data="monster:search")],
    ])


