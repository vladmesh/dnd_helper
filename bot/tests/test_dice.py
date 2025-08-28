import os


def test_roll_dice_helper_ranges() -> None:
    # Import from handlers to keep it simple and consistent with project style
    from dnd_helper_bot.handlers.dice import roll_dice

    rolls = roll_dice(5, 6)
    assert len(rolls) == 5
    assert all(1 <= r <= 6 for r in rolls)


def test_bot_module_imports_for_dice() -> None:
    # Ensure main module still importable
    os.environ["TELEGRAM_BOT_TOKEN"] = "dummy-token"
    import dnd_helper_bot.main as bot_main  # noqa: F401


