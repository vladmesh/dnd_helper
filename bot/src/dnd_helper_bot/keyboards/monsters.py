from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from dnd_helper_bot.utils.i18n import t


async def build_monsters_root_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    t_list = await t("monsters.menu.list", lang)
    t_rand = await t("monsters.menu.random", lang)
    t_search = await t("monsters.menu.search", lang)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t_list, callback_data="monster:list:page:1")],
        [InlineKeyboardButton(t_rand, callback_data="monster:random")],
        [InlineKeyboardButton(t_search, callback_data="monster:search")],
    ])


