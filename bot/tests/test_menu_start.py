import asyncio
import types
import importlib

import pytest

from factories import make_message_update


pytestmark = pytest.mark.asyncio


class DummyContext(types.SimpleNamespace):
    pass


async def test_start_prompts_language_when_user_not_found(monkeypatch):
    # Arrange: make API call raise to simulate missing user
    async def fail_api_get_one(*args, **kwargs):
        raise RuntimeError("not found")

    start_mod = importlib.import_module("dnd_helper_bot.handlers.menu.start")
    monkeypatch.setattr(start_mod, "api_get_one", fail_api_get_one)

    # Mock i18n translation to return recognizable key
    async def fake_t(key: str, lang: str):
        return f"__{key}__[{lang}]"

    monkeypatch.setattr(start_mod, "t", fake_t)

    # Mock keyboard builder to return sentinel object
    async def fake_keyboard(include_back: bool, lang: str):
        return {"kb": "language", "include_back": include_back, "lang": lang}

    monkeypatch.setattr(start_mod, "_build_language_keyboard", fake_keyboard)

    update = make_message_update(user_lang="en")
    context = DummyContext()

    # Act
    await start_mod.start(update, context)

    # Assert: message contains i18n prompt and keyboard was passed
    assert update.message.last_text == "__settings.choose_language_prompt__[en]"
    assert update.message.last_kwargs.get("reply_markup") == {
        "kb": "language",
        "include_back": False,
        "lang": "en",
    }


