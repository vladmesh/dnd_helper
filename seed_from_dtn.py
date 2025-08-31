#!/usr/bin/env python3
"""
Import monsters and spells from .dtn files via local HTTP API (curl to localhost:8000).

Usage examples:
  python3 seed_from_dtn.py --monsters --limit 10
  python3 seed_from_dtn.py --monsters --dry-run
  python3 seed_from_dtn.py --spells --dry-run

Notes:
  - This script does NOT modify containers. It calls the API exposed on localhost.
  - It parses Russian .dtn datasets and maps to our API schema.
  - Spells dataset lacks required caster_class; spell import will be skipped with a report.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


RE_CELLS = re.compile(r"(\d+)\s*клет")


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


# ---------------------------- Monsters mapping ----------------------------


@dataclass
class MonsterSourceRow:
    raw: Dict[str, Any]

    @property
    def name_raw(self) -> str:
        return str(self.raw.get("name", "")).strip()

    @property
    def name_ru_en(self) -> Tuple[str, Optional[str]]:
        # Example: "Ааракокра (Aarakocra)" -> ("Ааракокра", "Aarakocra")
        text = self.name_raw
        if "(" in text and ")" in text:
            ru = text.split("(", 1)[0].strip()
            en = text.split("(", 1)[1].rsplit(")", 1)[0].strip()
            return ru, en or None
        return text, None

    @property
    def description_html(self) -> str:
        return str(self.raw.get("fiction", "")).strip()

    @property
    def description_plain(self) -> str:
        # Strip simple HTML tags
        text = self.description_html
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    @property
    def ac(self) -> Optional[int]:
        ac_raw = str(self.raw.get("ac", "")).strip()
        m = re.search(r"(\d+)", ac_raw)
        return int(m.group(1)) if m else None

    @property
    def hp(self) -> Optional[int]:
        hp_raw = str(self.raw.get("hp", "")).strip()
        m = re.search(r"(\d+)", hp_raw)
        return int(m.group(1)) if m else None

    @property
    def hit_dice(self) -> Optional[str]:
        hp_raw = str(self.raw.get("hp", "")).strip()
        m = re.search(r"\(([^)]+)\)", hp_raw)
        return m.group(1) if m else None

    @property
    def cr_str(self) -> Optional[str]:
        value = self.raw.get("cr")
        return str(value).strip() if value is not None else None

    @property
    def cr(self) -> Optional[float]:
        if not self.cr_str:
            return None
        s = self.cr_str
        # Handle fractions like 1/4, 1/2, 2/3; and integers
        if "/" in s:
            try:
                num, den = s.split("/", 1)
                return float(num) / float(den)
            except Exception:
                return None
        try:
            return float(s)
        except Exception:
            return None

    @property
    def xp(self) -> Optional[int]:
        return None  # Will be filled using exp table by caller if provided

    @property
    def size_code(self) -> Optional[str]:
        return str(self.raw.get("size", "")).strip() or None

    @property
    def type_text(self) -> Optional[str]:
        # Prefer base type (sType) if present
        base = self.raw.get("sType")
        if base:
            return str(base).strip()
        t = self.raw.get("type")
        return str(t).strip() if t else None

    @property
    def alignment(self) -> Optional[str]:
        a = self.raw.get("alignment")
        return str(a).strip() if a else None

    @property
    def abilities(self) -> Dict[str, int]:
        def to_int(key: str) -> Optional[int]:
            v = self.raw.get(key)
            try:
                return int(str(v)) if v is not None else None
            except Exception:
                return None

        result: Dict[str, int] = {}
        for key_src, key_dst in [
            ("str", "str"),
            ("dex", "dex"),
            ("con", "con"),
            ("int", "int"),
            ("wis", "wis"),
            ("cha", "cha"),
        ]:
            val = to_int(key_src)
            if val is not None:
                result[key_dst] = val
        return result

    @property
    def skills_str(self) -> Optional[str]:
        v = self.raw.get("skill")
        return str(v).strip() if v else None

    @property
    def passive_perception(self) -> Optional[int]:
        v = self.raw.get("passive")
        try:
            return int(str(v)) if v is not None else None
        except Exception:
            return None

    @property
    def languages_list(self) -> Optional[List[str]]:
        v = self.raw.get("languages")
        if not v:
            return None
        parts = [p.strip() for p in str(v).split(",")]
        parts = [p for p in parts if p]
        return parts or None

    @property
    def speed_str(self) -> str:
        return str(self.raw.get("speed", "")).strip()

    @property
    def senses_str(self) -> Optional[str]:
        v = self.raw.get("senses")
        return str(v).strip() if v else None

    @property
    def traits_list(self) -> List[Dict[str, Any]]:
        v = self.raw.get("trait")
        if not v:
            return []
        if isinstance(v, list):
            items = v
        elif isinstance(v, dict):
            items = [v]
        else:
            return []
        result: List[Dict[str, Any]] = []
        for it in items:
            name = str(it.get("name", "")).strip()
            text = str(it.get("text", "")).strip()
            if name or text:
                result.append({"name": name, "text": text})
        return result

    @property
    def actions_list(self) -> List[Dict[str, Any]]:
        v = self.raw.get("action")
        if not v or not isinstance(v, list):
            return []
        result: List[Dict[str, Any]] = []
        for it in v:
            name = str(it.get("name", "")).strip()
            text = str(it.get("text", "")).strip()
            if name or text:
                result.append({"name": name, "text": text})
        return result

    @property
    def subtypes(self) -> Optional[List[str]]:
        v = self.raw.get("aSubtypes")
        if isinstance(v, list):
            cleaned = [str(x).strip() for x in v if str(x).strip()]
            return cleaned or None
        return None

    @property
    def environment(self) -> Optional[str]:
        v = self.raw.get("biom")
        return str(v).strip() if v else None

    @property
    def source_key(self) -> Optional[str]:
        v = self.raw.get("source")
        return str(v).strip() if v else None


def parse_cells_to_feet(text: str) -> Optional[int]:
    m = RE_CELLS.search(text)
    if not m:
        return None
    try:
        return int(m.group(1)) * 5
    except Exception:
        return None


def extract_speeds(speed_text: str) -> Dict[str, Optional[int]]:
    # Russian keywords to movement modes; fallback: first number = walk
    text = speed_text.lower()
    speeds: Dict[str, Optional[int]] = {
        "walk": None,
        "fly": None,
        "swim": None,
        "climb": None,
        "burrow": None,
    }

    # Find all numbers with context slices
    matches = list(RE_CELLS.finditer(text))
    if not matches:
        return speeds

    # Heuristics by surrounding words
    for m in matches:
        val_feet = int(m.group(1)) * 5
        start = max(0, m.start() - 20)
        ctx = text[start:m.start()]
        if any(k in ctx for k in ["лет", "полет", "лёта", "fly"]):
            speeds["fly"] = val_feet
        elif any(k in ctx for k in ["плав", "swim"]):
            speeds["swim"] = val_feet
        elif any(k in ctx for k in ["лаз", "climb"]):
            speeds["climb"] = val_feet
        elif any(k in ctx for k in ["копан", "burrow"]):
            speeds["burrow"] = val_feet
        else:
            # assume walk for plain segment
            if speeds["walk"] is None:
                speeds["walk"] = val_feet

    # Ensure at least walk is filled using first match
    if speeds["walk"] is None and matches:
        speeds["walk"] = int(matches[0].group(1)) * 5
    return speeds


def extract_senses(senses_text: Optional[str]) -> Dict[str, int]:
    if not senses_text:
        return {}
    text = senses_text.lower()
    result: Dict[str, int] = {}

    def set_from(keyword: str, key: str) -> None:
        if keyword in text:
            # Grab nearest number before/after keyword
            m = re.search(rf"{re.escape(keyword)}[^\d]*(\d+)", text)
            if not m:
                m = re.search(rf"(\d+)[^\d]*{re.escape(keyword)}", text)
            if m:
                result[key] = int(m.group(1)) * 5

    set_from("темнозрение", "darkvision")
    set_from("слепозрение", "blindsight")
    set_from("истинное зрение", "truesight")
    set_from("виброчувств", "tremorsense")
    return result


def normalize_size(size_value: Optional[str]) -> Optional[str]:
    if not size_value:
        return None
    s = str(size_value).strip()
    mapping = {
        "T": "tiny",
        "S": "small",
        "M": "medium",
        "L": "large",
        "H": "huge",
        "G": "gargantuan",
    }
    if s in mapping:
        return mapping[s]
    # Accept english words
    s_lower = s.lower()
    if s_lower in {"tiny", "small", "medium", "large", "huge", "gargantuan"}:
        return s_lower
    return None


def normalize_type(type_value: Optional[str]) -> Optional[str]:
    if not type_value:
        return None
    t = str(type_value).lower().strip()
    # Keep only base token before parenthesis or comma
    t = t.split("(", 1)[0].split(",", 1)[0].strip()
    # English fast path
    allowed = {
        "aberration",
        "beast",
        "celestial",
        "construct",
        "dragon",
        "elemental",
        "fey",
        "fiend",
        "giant",
        "humanoid",
        "monstrosity",
        "ooze",
        "plant",
        "undead",
    }
    if t in allowed:
        return t
    # Russian common mappings
    ru_map = {
        "аберрация": "aberration",
        "зверь": "beast",
        "небожитель": "celestial",
        "конструкт": "construct",
        "голем": "construct",
        "дракон": "dragon",
        "элементаль": "elemental",
        "фея": "fey",
        "исчадие": "fiend",
        "демон": "fiend",
        "дьявол": "fiend",
        "гигант": "giant",
        "гуманоид": "humanoid",
        "чудовище": "monstrosity",
        "слизь": "ooze",
        "растение": "plant",
        "нежить": "undead",
    }
    # Also handle leading base word before space
    base_token = t.split(" ", 1)[0]
    if base_token in ru_map:
        return ru_map[base_token]
    if t in ru_map:
        return ru_map[t]
    return None


def map_cr_to_danger(cr: Optional[float]) -> str:
    # Simple heuristic mapping CR -> DangerLevel
    if cr is None:
        return "moderate"
    if cr < 0.25:
        return "trivial"
    if cr <= 1:
        return "low"
    if cr <= 4:
        return "moderate"
    if cr <= 10:
        return "high"
    return "deadly"


def build_monster_payloads(monsters_json: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    data_list: List[Dict[str, Any]] = monsters_json.get("dataList", [])
    # XP lookup table if present
    expa: Dict[str, str] = monsters_json.get("expaList", {})

    payloads: List[Dict[str, Any]] = []
    for raw in data_list[: limit or len(data_list)]:
        row = MonsterSourceRow(raw)
        name_ru, name_en = row.name_ru_en
        speeds = extract_speeds(row.speed_str)
        senses = extract_senses(row.senses_str)
        cr_val = row.cr

        # XP: expaList values may contain ranges like "0 - 10"; parse first integer if present
        xp_val: Optional[int] = None
        if row.cr_str in expa:
            xp_raw = expa.get(row.cr_str, "")
            if isinstance(xp_raw, str):
                m_xp = re.search(r"(\d+)", xp_raw)
                if m_xp:
                    try:
                        xp_val = int(m_xp.group(1))
                    except Exception:
                        xp_val = None
            else:
                try:
                    xp_val = int(xp_raw)  # if numeric
                except Exception:
                    xp_val = None

        payload: Dict[str, Any] = {
            "name": name_ru or row.name_raw or "",
            "description": row.description_plain or (row.type_text or "").capitalize(),
            "dangerous_lvl": map_cr_to_danger(cr_val),
            "hp": row.hp or 1,
            "ac": row.ac or 10,
            # Optional fields
            "type": normalize_type(row.type_text),
            "size": normalize_size(row.size_code),
            "alignment": row.alignment,
            "hit_dice": row.hit_dice,
            "cr": cr_val,
            "xp": xp_val,
            "abilities": row.abilities or None,
            "skills": None,  # free-form string -> skip structured mapping
            "senses": senses or None,
            "languages": row.languages_list,
            "traits": row.traits_list or None,
            "actions": row.actions_list or None,
            "reactions": None,
            "legendary_actions": None,
            "spellcasting": None,
            "tags": None,
            # Localization & meta
            "name_ru": name_ru or None,
            "name_en": name_en or None,
            "source": row.source_key,
            # Taxonomy
            "subtypes": row.subtypes,
            "environments": [row.environment] if row.environment else None,
            # Derived speeds
            "speed_walk": speeds.get("walk"),
            "speed_fly": speeds.get("fly"),
            "speed_swim": speeds.get("swim"),
            "speed_climb": speeds.get("climb"),
            "speed_burrow": speeds.get("burrow"),
        }

        payloads.append(payload)

    return payloads


# ------------------------------ Spells mapping -----------------------------


@dataclass
class SpellSourceRow:
    en: Dict[str, Any]
    ru: Dict[str, Any]

    @property
    def name_ru(self) -> str:
        return str(self.ru.get("name", "")).strip()

    @property
    def name_en(self) -> str:
        return str(self.en.get("name", "")).strip()

    @property
    def description_ru(self) -> str:
        return str(self.ru.get("text", "")).strip()

    @property
    def level(self) -> Optional[int]:
        val = self.ru.get("level") or self.en.get("level")
        try:
            return int(str(val)) if val is not None else None
        except Exception:
            return None

    @property
    def school(self) -> Optional[str]:
        s = (self.en.get("school") or self.ru.get("school") or "").strip()
        mapping = {
            "abjuration": "abjuration",
            "ограждение": "abjuration",
            "conjuration": "conjuration",
            "призыв": "conjuration",
            "divination": "divination",
            "прорицание": "divination",
            "enchantment": "enchantment",
            "очарование": "enchantment",
            "evocation": "evocation",
            "проявление": "evocation",
            "illusion": "illusion",
            "иллюзия": "illusion",
            "necromancy": "necromancy",
            "некромантия": "necromancy",
            "transmutation": "transmutation",
            "преобразование": "transmutation",
        }
        return mapping.get(s.lower())

    @property
    def casting_time(self) -> Optional[str]:
        return (self.en.get("castingTime") or self.ru.get("castingTime") or "").strip() or None

    @property
    def range(self) -> Optional[str]:
        return (self.en.get("range") or self.ru.get("range") or "").strip() or None

    @property
    def duration(self) -> Optional[str]:
        return (self.en.get("duration") or self.ru.get("duration") or "").strip() or None

    @property
    def components_dict(self) -> Dict[str, Any]:
        comp = (self.en.get("components") or self.ru.get("components") or "").lower()
        comps = {k.strip() for k in comp.replace(".", "").split(",")}
        has_v = "v" in comps or "в" in comps
        has_s = "s" in comps or "с" in comps
        has_m = "m" in comps or "m" in comps
        materials = (self.en.get("materials") or self.ru.get("materials") or "").strip()
        return {"v": has_v, "s": has_s, "m": has_m, "material_desc": materials}


def build_spell_payloads(spells_json: Dict[str, Any], limit: Optional[int] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
    # The dataset appears to be a list with {"en": {...}, "ru": {...}} objects under some top-level array
    data_entries: List[Dict[str, Any]] = []
    # Attempt to locate an array by scanning JSON values
    if isinstance(spells_json, dict):
        for v in spells_json.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and ("en" in v[0] and "ru" in v[0]):
                data_entries = v
                break
    elif isinstance(spells_json, list):
        data_entries = spells_json

    payloads: List[Dict[str, Any]] = []
    issues: List[str] = []

    for entry in data_entries[: limit or len(data_entries)]:
        en = entry.get("en", {})
        ru = entry.get("ru", {})
        row = SpellSourceRow(en=en, ru=ru)

        # Dataset may lack explicit caster list; default single class wizard
        caster_class: str = "wizard"

        # Use enriched DTN fields when available
        classes_en = en.get("classes")
        classes_ru = ru.get("classes")
        classes_list: Optional[List[str]] = None
        if isinstance(classes_en, list) and classes_en:
            classes_list = [str(x).strip().lower() for x in classes_en if str(x).strip()]
        elif isinstance(classes_ru, list) and classes_ru:
            classes_list = [str(x).strip().lower() for x in classes_ru if str(x).strip()]
        else:
            classes_list = [caster_class]

        ritual_val: Optional[bool] = None
        if isinstance(en.get("ritual"), bool):
            ritual_val = bool(en.get("ritual"))
        elif isinstance(ru.get("ritual"), bool):
            ritual_val = bool(ru.get("ritual"))

        # Derive concentration → is_concentration
        conc_flag: Optional[bool] = None
        if isinstance(en.get("concentration"), bool):
            conc_flag = bool(en.get("concentration"))
        elif isinstance(ru.get("concentration"), bool):
            conc_flag = bool(ru.get("concentration"))
        else:
            # Fallback from duration text
            dur_en = (en.get("duration") or "")
            dur_ru = (ru.get("duration") or "")
            if isinstance(dur_en, str) and re.search(r"\bConcentration\b", dur_en, flags=re.IGNORECASE):
                conc_flag = True
            elif isinstance(dur_ru, str) and re.search(r"конц", dur_ru, flags=re.IGNORECASE):
                conc_flag = True

        school = row.school

        payload: Dict[str, Any] = {
            "name": row.name_ru or row.name_en,
            "description": row.description_ru or row.name_en,
            # Prefer multi-class list when provided
            "classes": classes_list,
            "school": school,
            "level": row.level,
            "ritual": ritual_val,
            "casting_time": row.casting_time,
            "range": row.range,
            "duration": row.duration,
            "is_concentration": conc_flag,
            "components": row.components_dict,
            "name_ru": row.name_ru,
            "name_en": row.name_en,
        }
        payloads.append(payload)

    return payloads, issues


# --------------------------------- CLI/main --------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Import monsters and spells from .dtn via API")
    parser.add_argument("--api-base-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--monsters", action="store_true", help="Import monsters")
    parser.add_argument("--spells", action="store_true", help="Import spells")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of imported items per type")
    parser.add_argument("--dry-run", action="store_true", help="Do not POST, just show summary and samples")
    parser.add_argument("--monsters-file", default="DnD5e_monsters_BD.dtn")
    parser.add_argument("--spells-file", default="DnD5e_spells_BD.dtn")

    args = parser.parse_args(argv)

    # If neither specified, default to monsters only (since spells cannot be imported fully)
    if not args.monsters and not args.spells:
        args.monsters = True

    # API connectivity check
    try:
        _ = curl_get_json(args.api_base_url, "/health")
    except SystemExit:
        print("API is not reachable at", args.api_base_url, file=sys.stderr)
        return 1

    if args.monsters:
        with open(args.monsters_file, "r", encoding="utf-8-sig") as f:
            monsters_json = json.load(f)
        monster_payloads = build_monster_payloads(monsters_json, limit=args.limit)
        print(f"Monsters prepared: {len(monster_payloads)}")
        if args.dry_run:
            for sample in monster_payloads[: min(3, len(monster_payloads))]:
                print(json.dumps(sample, ensure_ascii=False)[:500] + ("..." if len(json.dumps(sample, ensure_ascii=False)) > 500 else ""))
        else:
            existing = curl_get_json(args.api_base_url, "/monsters") or []
            if existing:
                print(f"Monsters already present: {len(existing)}. Skipping import.")
            else:
                for idx, p in enumerate(monster_payloads, 1):
                    created = curl_post_json(args.api_base_url, "/monsters", p)
                    print(f"[{idx}/{len(monster_payloads)}] Created monster id={created.get('id')} name={created.get('name')}")

    if args.spells:
        with open(args.spells_file, "r", encoding="utf-8-sig") as f:
            spells_json = json.load(f)
        spell_payloads, issues = build_spell_payloads(spells_json, limit=args.limit)
        print(f"Spells prepared: {len(spell_payloads)}; Skipped due to issues: {len(issues)}")
        for issue in issues[:10]:
            print(f"WARN: {issue}")
        if not args.dry_run and spell_payloads:
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


