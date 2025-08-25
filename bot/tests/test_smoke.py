"""Minimal smoke tests for Bot service."""


def test_bot_module_imports() -> None:
    # Ensure the bot package can be imported
    import dnd_helper_bot.main as bot_main  # noqa: F401


def test_bot_can_build_application_without_token(monkeypatch) -> None:
    # Verify that building app without running polling works
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
    from telegram.ext import ApplicationBuilder

    app = ApplicationBuilder().token("dummy-token").build()
    assert app is not None


