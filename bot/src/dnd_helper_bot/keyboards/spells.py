from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_spells_root_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    t_list = "Spells list" if lang == "en" else "Список заклинаний"
    t_rand = "Random spell" if lang == "en" else "Случайное заклинание"
    t_search = "Search spell" if lang == "en" else "Поиск заклинания"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t_list, callback_data="spell:list:page:1")],
        [InlineKeyboardButton(t_rand, callback_data="spell:random")],
        [InlineKeyboardButton(t_search, callback_data="spell:search")],
    ])


