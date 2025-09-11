import importlib
import types

import pytest
from factories import make_message_update
import dnd_helper_bot.utils.nav as nav


pytestmark = pytest.mark.asyncio


class DummyContext(types.SimpleNamespace):
    pass


async def test_monster_search_uses_scope_param_and_renders_scope_label(monkeypatch):
    # Arrange
    search_mod = importlib.import_module("dnd_helper_bot.handlers.search")

    # User language
    async def ok_api_get_one(*args, **kwargs):
        return {"lang": "en"}

    monkeypatch.setattr(search_mod, "api_get_one", ok_api_get_one)

    # Capture API call
    captured = {}

    async def fake_api_get(path: str, params: dict | None = None):
        captured["path"] = path
        captured["params"] = dict(params or {})
        # Minimal wrapped item
        return [
            {"entity": {"id": 1}, "translation": {"name": "Wolf"}},
        ]

    monkeypatch.setattr(search_mod, "api_get", fake_api_get)

    # i18n stubs
    async def fake_t(key: str, lang: str, default: str | None = None, namespace: str = "bot"):
        mapping = {
            "search.scope.name": "Name",
            "search.scope.name_description": "Name + Description",
            "search.results_title": "Search results:",
            "nav.back": "Back",
            "nav.main": "Main menu",
        }
        return mapping.get(key, key)

    monkeypatch.setattr(search_mod, "t", fake_t)
    # Also stub t in nav module to avoid network calls for i18n
    monkeypatch.setattr(nav, "t", fake_t)

    update = make_message_update(user_lang="en", text="wolf")
    context = DummyContext(user_data={"awaiting_monster_query": True})

    # Act
    await search_mod.handle_search_text(update, context)

    # Assert: API called with default scope and correct path
    assert captured["path"] == "/monsters/search/wrapped"
    assert captured["params"]["q"] == "wolf"
    assert captured["params"]["search_scope"] == "name"

    # And the message shows the scope label in header (prefix), suffix may include page
    assert update.message.last_text.startswith("[Name]\nSearch results:")


