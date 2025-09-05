from telegram import InlineKeyboardButton

from dnd_helper_bot.utils.i18n import t


async def build_nav_row(lang: str, back_callback: str, main_callback: str = "menu:main") -> list[InlineKeyboardButton]:
    """Build a standardized navigation row [Back, Main].

    Labels are resolved via i18n; absence of keys should be treated as an error.
    """
    back_label = await t("nav.back", lang)
    main_label = await t("nav.main", lang)
    return [
        InlineKeyboardButton(back_label, callback_data=back_callback),
        InlineKeyboardButton(main_label, callback_data=main_callback),
    ]


