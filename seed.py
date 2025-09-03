#!/usr/bin/env python3
"""
Seed monsters and spells into API from a single seed file (seed_data.json).

Usage examples:
  python3 seed.py --monsters --limit 10
  python3 seed.py --spells --dry-run

Notes:
  - This script calls the API exposed on localhost (curl based), no containers are modified.
  - Source format is a single JSON with blocks: monsters, spells, monster_translations,
    spell_translations, enum_translations.
  - Translations are attached to create requests via the "translations" field (ru/en) when available.
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


# --------------------------------- CLI/main --------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Seed monsters and spells from seed JSON via API")
    parser.add_argument("--api-base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--monsters", action="store_true", help="Import monsters")
    parser.add_argument("--spells", action="store_true", help="Import spells")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of imported items per type")
    parser.add_argument("--dry-run", action="store_true", help="Do not POST, just show summary and samples")

    args = parser.parse_args(argv)

    if not args.monsters and not args.spells:
        args.monsters = True

    # API connectivity check
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


