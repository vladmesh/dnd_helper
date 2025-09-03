#!/usr/bin/env python3
"""
Seed data into the running API from a single file seed_data.json.

What this script does:
  - Seeds monsters and spells through public API endpoints (includes RU/EN translations when present).
  - Upserts enum translations and UI (bot) translations directly into DB inside the API container.

Usage examples:
  python3 seed.py --monsters --limit 10
  python3 seed.py --spells --dry-run
  python3 seed.py --all  # monsters, spells, enums, ui

Notes:
  - Monsters/Spells seeding is done via HTTP requests to the API exposed on localhost.
  - Enum/UI translations are upserted by running a tiny Python snippet inside the API container
    (no local DB deps). Data is piped as JSON via stdin.
  - Source format is a single JSON with blocks: monsters, spells, monster_translations,
    spell_translations, enum_translations, optional ui_translations.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def run_curl(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def curl_get_json(base_url: str, path: str) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    result = run_curl(["curl", "-sS", url])
    if result.returncode != 0:
        print(f"GET {url} failed: {result.stderr}", file=sys.stderr)
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        print(f"GET {url} invalid JSON: {exc}\nBody: {result.stdout}", file=sys.stderr)
        raise SystemExit(1) from exc


def curl_post_json(base_url: str, path: str, payload: Dict[str, Any]) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload, ensure_ascii=False)
    result = run_curl([
        "curl",
        "-sS",
        "-H",
        "Content-Type: application/json",
        "-X",
        "POST",
        "-d",
        data,
        url,
    ])
    if result.returncode != 0:
        print(f"POST {url} failed: {result.stderr}", file=sys.stderr)
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        print(f"POST {url} invalid JSON: {exc}\nBody: {result.stdout}", file=sys.stderr)
        raise SystemExit(1) from exc


# ---------------------- Enum/UI translations (container) ----------------------


def _default_ui_pairs() -> List[Tuple[str, str, str]]:
    """Fallback UI translations if seed_data.json has no ui_translations block."""
    return [
        ("menu.main.title", "ru", "Главное меню"),
        ("menu.main.title", "en", "Main menu"),
        ("menu.bestiary.title", "ru", "Бестиарий"),
        ("menu.bestiary.title", "en", "Bestiary"),
        ("menu.spells.title", "ru", "Заклинания"),
        ("menu.spells.title", "en", "Spells"),
        ("menu.settings.title", "ru", "Настройки"),
        ("menu.settings.title", "en", "Settings"),
        ("dice.menu.title", "ru", "Бросить кубики"),
        ("dice.menu.title", "en", "Roll dice"),
        ("dice.custom.button", "ru", "Произвольный бросок"),
        ("dice.custom.button", "en", "Custom roll"),
        ("dice.custom.prompt.count", "ru", "Сколько кубиков бросить? (1-100)"),
        ("dice.custom.prompt.count", "en", "How many dice to roll? (1-100)"),
        ("dice.custom.prompt.faces", "ru", "Номинал кубика? (2,3,4,6,8,10,12,20,100)"),
        ("dice.custom.prompt.faces", "en", "Die faces? (2,3,4,6,8,10,12,20,100)"),
        ("dice.custom.error.range", "ru", "Количество должно быть от 1 до 100"),
        ("dice.custom.error.range", "en", "Count must be between 1 and 100"),
        ("dice.custom.error.allowed", "ru", "Разрешены только: 2,3,4,6,8,10,12,20,100"),
        ("dice.custom.error.allowed", "en", "Allowed only: 2,3,4,6,8,10,12,20,100"),
        ("monsters.search.prompt", "ru", "Введите подстроку для поиска по названию монстра:"),
        ("monsters.search.prompt", "en", "Enter substring to search monster by name:"),
        ("spells.search.prompt", "ru", "Введите подстроку для поиска по названию заклинания:"),
        ("spells.search.prompt", "en", "Enter substring to search spell by name:"),
        ("list.empty.monsters", "ru", "Монстров нет."),
        ("list.empty.monsters", "en", "No monsters."),
        ("list.empty.spells", "ru", "Заклинаний нет."),
        ("list.empty.spells", "en", "No spells."),
        ("nav.back", "ru", "⬅️ Назад"),
        ("nav.back", "en", "⬅️ Back"),
        ("nav.next", "ru", "➡️ Далее"),
        ("nav.next", "en", "➡️ Next"),
        ("nav.main", "ru", "К главному меню"),
        ("nav.main", "en", "Main menu"),
    ]


def upsert_enum_and_ui_translations_in_container(enum_rows: List[Dict[str, Any]], ui_rows: List[Dict[str, Any]]) -> None:
    """Execute upserts inside the API container using project dependencies there."""
    payload = json.dumps({"enum": enum_rows, "ui": ui_rows}, ensure_ascii=False)
    inline = (
        "import sys,json;\n"
        "from sqlmodel import Session;\n"
        "from sqlalchemy.dialects.postgresql import insert as pg_insert;\n"
        "from dnd_helper_api.db import engine;\n"
        "from shared_models.enum_translation import EnumTranslation;\n"
        "from shared_models.ui_translation import UiTranslation;\n"
        "data=json.load(sys.stdin); enum=data.get('enum') or []; ui=data.get('ui') or [];\n"
        "from contextlib import nullcontext as _nc;\n"
        "with Session(engine) as session:\n"
        "    if enum:\n"
        "        t=EnumTranslation.__table__;\n"
        "        s=pg_insert(t).values(enum);\n"
        "        s=s.on_conflict_do_update(index_elements=[t.c.enum_type,t.c.enum_value,t.c.lang], set_={'label': s.excluded.label, 'description': s.excluded.description, 'synonyms': s.excluded.synonyms});\n"
        "        session.exec(s);\n"
        "    if ui:\n"
        "        t=UiTranslation.__table__;\n"
        "        s=pg_insert(t).values(ui);\n"
        "        s=s.on_conflict_do_update(index_elements=[t.c.namespace,t.c.key,t.c.lang], set_={'text': s.excluded.text});\n"
        "        session.exec(s);\n"
        "    session.commit()\n"
    )
    proc = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-T",
            "api",
            "python",
            "-c",
            inline,
        ],
        input=payload,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)


# ---------------------------- Seed JSON helpers ----------------------------


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _index_translations(
    items: List[Dict[str, Any]], key_slug: str
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Index translations by (slug, lang)."""
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for it in items or []:
        slug = str(it.get(key_slug) or "").strip()
        lang = str(it.get("lang") or "").strip().lower()
        if not slug or lang not in {"ru", "en"}:
            continue
        index[(slug, lang)] = it
    return index


def _collect_monster_translations_for_slug(
    tr_index: Dict[Tuple[str, str], Dict[str, Any]], slug: str
) -> Optional[Dict[str, Dict[str, Any]]]:
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


def _collect_spell_translations_for_slug(
    tr_index: Dict[Tuple[str, str], Dict[str, Any]], slug: str
) -> Optional[Dict[str, Dict[str, Any]]]:
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


def build_ui_rows_from_seed(seed: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        # Fallback to default set
        rows = [{"namespace": "bot", "key": k, "lang": lang, "text": text} for k, lang, text in _default_ui_pairs()]
    return rows


# --------------------------------- CLI/main --------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Seed data (monsters, spells, enums, ui) from seed JSON")
    parser.add_argument("--api-base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--monsters", action="store_true", help="Import monsters")
    parser.add_argument("--spells", action="store_true", help="Import spells")
    parser.add_argument("--enums", action="store_true", help="Upsert enum translations")
    parser.add_argument("--ui", action="store_true", help="Upsert UI translations")
    parser.add_argument("--all", action="store_true", help="Do everything (monsters, spells, enums, ui)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of imported items per type")
    parser.add_argument("--dry-run", action="store_true", help="Do not POST, just show summary and samples")

    args = parser.parse_args(argv)

    if args.all:
        args.monsters = True
        args.spells = True
        args.enums = True
        args.ui = True
    if not any([args.monsters, args.spells, args.enums, args.ui]):
        # Default: seed everything via safe order
        args.monsters = True
        args.spells = True
        args.enums = True
        args.ui = True

    # API connectivity check (only needed if we touch monsters/spells)
    if args.monsters or args.spells:
        try:
            _ = curl_get_json(args.api_base_url, "/health")
        except SystemExit:
            print("API is not reachable at", args.api_base_url, file=sys.stderr)
            return 1

    # Load seed JSON once (fixed path next to this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    seed_path = os.path.join(script_dir, "seed_data.json")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed = json.load(f)

    if args.monsters:
        monster_payloads = build_monster_payloads_from_seed(seed, limit=args.limit)
        print(f"Monsters prepared: {len(monster_payloads)}")
        if args.dry_run:
            for sample in monster_payloads[: min(3, len(monster_payloads))]:
                body = json.dumps(sample, ensure_ascii=False)
                print(body[:500] + ("..." if len(body) > 500 else ""))
        else:
            existing = curl_get_json(args.api_base_url, "/monsters") or []
            if existing:
                print(f"Monsters already present: {len(existing)}. Skipping import.")
            else:
                for idx, p in enumerate(monster_payloads, 1):
                    created = curl_post_json(args.api_base_url, "/monsters", p)
                    print(f"[{idx}/{len(monster_payloads)}] Created monster id={created.get('id')} name={created.get('name')}")

    if args.spells:
        spell_payloads = build_spell_payloads_from_seed(seed, limit=args.limit)
        print(f"Spells prepared: {len(spell_payloads)}")
        if args.dry_run:
            for sample in spell_payloads[: min(3, len(spell_payloads))]:
                body = json.dumps(sample, ensure_ascii=False)
                print(body[:500] + ("..." if len(body) > 500 else ""))
        else:
            existing = curl_get_json(args.api_base_url, "/spells") or []
            if existing:
                print(f"Spells already present: {len(existing)}. Skipping import.")
            else:
                for idx, p in enumerate(spell_payloads, 1):
                    created = curl_post_json(args.api_base_url, "/spells", p)
                    print(f"[{idx}/{len(spell_payloads)}] Created spell id={created.get('id')} name={created.get('name')}")

    # Enums/UI upserts (always direct DB via container)
    if args.enums or args.ui:
        enum_rows = build_enum_rows_from_seed(seed) if args.enums else []
        ui_rows = build_ui_rows_from_seed(seed) if args.ui else []
        print(f"Enum translations: {len(enum_rows)} | UI translations: {len(ui_rows)}")
        if not args.dry_run:
            upsert_enum_and_ui_translations_in_container(enum_rows, ui_rows)
        else:
            print("[dry-run] Skipping enum/ui upsert")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


