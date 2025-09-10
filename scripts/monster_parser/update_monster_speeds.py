#!/usr/bin/env python3
"""
Update monsters' speed fields in seed_data_monsters.json using parsed data.
Mirrors CLI structure and matching strategy of update_monster_translations.py.
"""

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_name(name: str) -> str:
    if not name:
        return ""
    normalized = re.sub(r"\s+", " ", name.strip().lower())
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return normalized


def load_data(seed_in_path: str, parsed_in_path: str) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    try:
        print("📥 Loading seed JSON...")
        with open(seed_in_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)

        print("📥 Loading parsed monsters...")
        with open(parsed_in_path, "r", encoding="utf-8") as f:
            parsed_data = json.load(f)

        monsters = parsed_data.get("monsters", []) if isinstance(parsed_data, dict) else parsed_data
        return original_data, monsters
    except Exception as e:
        print(f"❌ Load error: {e}")
        return None, None


def build_name_by_slug(original_data: Dict[str, Any], lang: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for t in original_data.get("monster_translations", []):
        if t.get("lang") == lang:
            slug = t.get("monster_slug")
            name = t.get("name")
            if slug and name:
                result[slug] = name
    return result


def extract_speeds(speed_str: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Return (walk, fly, climb) speeds in feet when found."""
    if not speed_str:
        return None, None, None

    s = speed_str.lower()
    # normalize diacritics: ё -> е
    s = s.replace("ё", "е")
    # remove parentheticals for simpler matching
    s = re.sub(r"\([^)]*\)", "", s)
    # split by comma/semicolon
    segments = re.split(r"[,;]", s)

    walk: Optional[int] = None
    fly: Optional[int] = None
    climb: Optional[int] = None

    for raw_seg in segments:
        seg = raw_seg.strip()
        if not seg:
            continue

        # fly (ru/en): "летая 50 футов", "полета 50 футов", "fly 60 ft"
        m = re.search(r"\b(?:летая|полета|полет|fly)\s*(\d+)\s*(?:фт|футов|фут|ft)\b", seg)
        if m and fly is None:
            fly = int(m.group(1))
            continue

        # climb (ru/en): "лазая 20 футов", "climb 20 ft"
        m = re.search(r"\b(?:лаза[а-я]*|climb)\s*(\d+)\s*(?:фт|футов|фут|ft)\b", seg)
        if m and climb is None:
            climb = int(m.group(1))
            continue

        # explicit walk or leading number without other keywords -> walk
        if re.search(r"\bwalk\b", seg):
            m = re.search(r"\bwalk\s*(\d+)\s*ft\b", seg)
            if m and walk is None:
                walk = int(m.group(1))
                continue
        else:
            # if segment starts with number and lacks movement keywords, treat as walk
            if not re.search(r"\b(?:fly|climb|swim|burrow|летая|полет|полета|плавая|лаза)\b", seg):
                # ru: "20 футов"; en: "20 ft"
                m = re.match(r"^(\d+)\s*(?:фт|футов|фут|ft)\b", seg)
                if m and walk is None:
                    walk = int(m.group(1))
                    continue

    return walk, fly, climb


def find_parsed_match(seed_monster: Dict[str, Any], parsed_monsters: List[Dict[str, Any]], en_by_slug: Dict[str, str], ru_by_slug: Dict[str, str]) -> Optional[Dict[str, Any]]:
    slug = seed_monster.get("slug")
    seed_en = normalize_name(en_by_slug.get(slug, "")) if slug else ""
    seed_ru = normalize_name(ru_by_slug.get(slug, "")) if slug else ""

    for pm in parsed_monsters:
        pm_ru = normalize_name(pm.get("name", ""))
        pm_en = normalize_name(pm.get("english_name", ""))
        if (seed_ru and pm_ru and seed_ru == pm_ru) or (seed_ru and pm_en and seed_ru == pm_en) or (seed_en and pm_ru and seed_en == pm_ru) or (seed_en and pm_en and seed_en == pm_en):
            return pm
    return None


def update_monster_speeds(original_data: Dict[str, Any], parsed_monsters: List[Dict[str, Any]]) -> int:
    monsters: List[Dict[str, Any]] = original_data.get("monsters", [])
    en_by_slug = build_name_by_slug(original_data, "en")
    ru_by_slug = build_name_by_slug(original_data, "ru")
    updated = 0

    for m in monsters:
        pm = find_parsed_match(m, parsed_monsters, en_by_slug, ru_by_slug)
        if not pm:
            continue

        walk, fly, climb = extract_speeds(pm.get("speed", ""))

        before = (m.get("speed_walk"), m.get("speed_fly"), m.get("speed_climb"), m.get("is_flying"))

        changed = False
        if walk is not None and m.get("speed_walk") != walk:
            m["speed_walk"] = walk
            changed = True
        if fly is not None and m.get("speed_fly") != fly:
            m["speed_fly"] = fly
            changed = True
        if climb is not None and m.get("speed_climb") != climb:
            m["speed_climb"] = climb
            changed = True

        # is_flying: True iff fly parsed (>0). If absent, leave as-is (None/False).
        if fly is not None:
            new_flag = bool(fly and fly > 0)
            if m.get("is_flying") != new_flag:
                m["is_flying"] = new_flag
                changed = True

        after = (m.get("speed_walk"), m.get("speed_fly"), m.get("speed_climb"), m.get("is_flying"))
        if changed:
            updated += 1
            print(f"✅ {m.get('slug')}: {before} -> {after}")

    return updated


def save_updated_data(data: Dict[str, Any], output_path: str) -> bool:
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Save error: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Update monster speeds in seed using parsed data")
    parser.add_argument("--seed-in", default="/app/seed_data_monsters.json", help="Path to input seed JSON")
    parser.add_argument("--seed-out", default="/app/seed_data_monsters_updated.json", help="Path to output updated seed JSON")
    parser.add_argument("--parsed-in", default="/app/scripts/monster_parser/output/parsed_monsters_filtered_final.json", help="Path to parsed monsters JSON")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output, only report")
    args = parser.parse_args()

    original_data, parsed_monsters = load_data(args.seed_in, args.parsed_in)
    if not original_data or not parsed_monsters:
        return

    print(f"📊 Parsed monsters loaded: {len(parsed_monsters)}")
    updated = update_monster_speeds(original_data, parsed_monsters)
    print(f"🎯 Monsters updated: {updated}")

    if updated > 0 and not args.dry_run:
        save_updated_data(original_data, args.seed_out)
    elif args.dry_run:
        print("✅ Dry-run: no files written")


if __name__ == "__main__":
    main()


