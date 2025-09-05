from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _index_translations(items: List[Dict[str, Any]], key_slug: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for it in items or []:
        slug = str(it.get(key_slug) or "").strip()
        lang = str(it.get("lang") or "").strip().lower()
        if not slug or lang not in {"ru", "en"}:
            continue
        index[(slug, lang)] = it
    return index


def _collect_monster_translations_for_slug(tr_index: Dict[Tuple[str, str], Dict[str, Any]], slug: str) -> Optional[Dict[str, Dict[str, Any]]]:
    result: Dict[str, Dict[str, Any]] = {}
    for lang in ("ru", "en"):
        row = tr_index.get((slug, lang))
        if not row:
            continue
        data: Dict[str, Any] = {}
        for key in ("name", "description", "traits", "actions", "reactions", "legendary_actions", "spellcasting"):
            if key in row and row[key] is not None:
                data[key] = row[key]
        if data:
            result[lang] = data
    return result or None


def _collect_spell_translations_for_slug(tr_index: Dict[Tuple[str, str], Dict[str, Any]], slug: str) -> Optional[Dict[str, Dict[str, Any]]]:
    result: Dict[str, Dict[str, Any]] = {}
    for lang in ("ru", "en"):
        row = tr_index.get((slug, lang))
        if not row:
            continue
        data: Dict[str, Any] = {}
        for key in ("name", "description"):
            if key in row and row[key] is not None:
                data[key] = row[key]
        if data:
            result[lang] = data
    return result or None


def build_monster_payloads_from_seed(seed: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = seed.get("monsters", []) or []
    tr_index = _index_translations(seed.get("monster_translations", []) or [], key_slug="monster_slug")
    result: List[Dict[str, Any]] = []
    for raw in rows[: limit or len(rows)]:
        payload = dict(raw)
        slug = payload.get("slug") or _slugify(str(payload.get("name") or payload.get("name_en") or ""))
        if slug:
            payload["slug"] = slug
            translations = _collect_monster_translations_for_slug(tr_index, slug)
            if translations:
                payload["translations"] = translations
        result.append(payload)
    return result


def build_spell_payloads_from_seed(seed: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = seed.get("spells", []) or []
    tr_index = _index_translations(seed.get("spell_translations", []) or [], key_slug="spell_slug")
    result: List[Dict[str, Any]] = []
    for raw in rows[: limit or len(rows)]:
        payload = dict(raw)
        slug = payload.get("slug") or _slugify(str(payload.get("name") or payload.get("name_en") or ""))
        if slug:
            payload["slug"] = slug
            translations = _collect_spell_translations_for_slug(tr_index, slug)
            if translations:
                payload["translations"] = translations
        result.append(payload)
    return result


def build_enum_rows_from_seed(seed: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for r in seed.get("enum_translations", []) or []:
        enum_type = str(r.get("enum_type") or "").strip()
        enum_value = str(r.get("enum_value") or "").strip()
        lang = str(r.get("lang") or "").strip().lower()
        label = r.get("label")
        if not (enum_type and enum_value and lang in {"ru", "en"} and isinstance(label, str)):
            continue
        row: Dict[str, Any] = {
            "enum_type": enum_type,
            "enum_value": enum_value,
            "lang": lang,
            "label": label,
        }
        if "description" in r:
            row["description"] = r.get("description")
        if "synonyms" in r:
            row["synonyms"] = r.get("synonyms")
        rows.append(row)
    return rows


def build_ui_rows_from_seed(seed: Dict[str, Any], default_ui_pairs: List[Tuple[str, str, str]]) -> List[Dict[str, Any]]:
    pairs = seed.get("ui_translations")
    rows: List[Dict[str, str]] = []
    if isinstance(pairs, list):
        for it in pairs:
            key = str(it.get("key") or "").strip()
            lang = str(it.get("lang") or "").strip().lower()
            text = it.get("text")
            ns = str(it.get("namespace") or "bot").strip() or "bot"
            if key and lang in {"ru", "en"} and isinstance(text, str):
                rows.append({"namespace": ns, "key": key, "lang": lang, "text": text})
    else:
        rows = [{"namespace": "bot", "key": k, "lang": lang, "text": text} for k, lang, text in default_ui_pairs]
    return rows


