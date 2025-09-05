from __future__ import annotations

from typing import Dict

from dnd_helper_bot.repositories.api_client import api_get_one

# Cache structure: { lang: { namespace: { key: text } } }
_cache: Dict[str, Dict[str, Dict[str, str]]] = {}


async def _ensure_namespace(lang: str, namespace: str = "bot") -> Dict[str, str]:
    lang = (lang or "ru").lower()
    ns = namespace or "bot"
    if lang not in _cache:
        _cache[lang] = {}
    if ns not in _cache[lang]:
        data = await api_get_one("/i18n/ui", params={"ns": ns, "lang": lang})
        if not isinstance(data, dict):
            data = {}
        _cache[lang][ns] = {str(k): str(v) for k, v in data.items()}
    return _cache[lang][ns]


async def t(key: str, lang: str, default: str | None = None, namespace: str = "bot") -> str:
    data = await _ensure_namespace(lang, namespace)
    return data.get(key) or (default if default is not None else key)
