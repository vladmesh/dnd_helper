from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from dnd_helper_bot.utils.i18n import t


async def build_spells_root_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    t_list = await t("spells.menu.list", lang)
    t_rand = await t("spells.menu.random", lang)
    t_search = await t("spells.menu.search", lang)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t_list, callback_data="spell:list:page:1")],
        [InlineKeyboardButton(t_rand, callback_data="spell:random")],
        [InlineKeyboardButton(t_search, callback_data="spell:search")],
    ])


