from telegram import ReplyKeyboardMarkup


def build_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [["Бросить кубики"], ["Бестиарий", "Заклинания"]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


