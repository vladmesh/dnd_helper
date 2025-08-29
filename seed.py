#!/usr/bin/env python3
"""
Simple seeding script that populates API via curl to localhost:8000.

Usage:
  python3 seed.py

Environment:
  API_BASE_URL (optional) - defaults to http://localhost:8000
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def run_curl(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def curl_get_json(path: str) -> Any:
    url = f"{API_BASE_URL}{path}"
    result = run_curl(["curl", "-sS", url])
    if result.returncode != 0:
        print(f"GET {url} failed: {result.stderr}", file=sys.stderr)
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        print(f"GET {url} invalid JSON: {exc}\nBody: {result.stdout}", file=sys.stderr)
        raise SystemExit(1)


def curl_post_json(path: str, payload: Dict[str, Any]) -> Any:
    url = f"{API_BASE_URL}{path}"
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
        raise SystemExit(1)


def seed_monsters() -> None:
    existing = curl_get_json("/monsters") or []
    if existing:
        print(f"Monsters already present: {len(existing)}. Skipping.")
        return

    monsters: List[Dict[str, Any]] = [
        {
            "title": "Goblin",
            "description": "Small, sneaky humanoid.",
            "dangerous_lvl": "low",
            "hp": 7,
            "ac": 15,
            "speed": 30,
        },
        {
            "title": "Orc",
            "description": "Brutal warrior.",
            "dangerous_lvl": "moderate",
            "hp": 15,
            "ac": 13,
            "speed": 30,
        },
        {
            "title": "Troll",
            "description": "Regenerating giant.",
            "dangerous_lvl": "high",
            "hp": 84,
            "ac": 15,
            "speed": 30,
        },
        {
            "title": "Young Red Dragon",
            "description": "Fearsome dragon wyrmling.",
            "dangerous_lvl": "deadly",
            "hp": 178,
            "ac": 18,
            "speed": 40,
        },
    ]

    for item in monsters:
        created = curl_post_json("/monsters", item)
        print(f"Created monster id={created.get('id')} description={created.get('description')}")


def seed_spells() -> None:
    existing = curl_get_json("/spells") or []
    if existing:
        print(f"Spells already present: {len(existing)}. Skipping.")
        return

    spells: List[Dict[str, Any]] = [
        {
            "title": "Fire Bolt",
            "description": "Fire Bolt — a mote of fire that deals damage.",
            "caster_class": "wizard",
            "distance": 120,
            "school": "evocation",
        },
        {
            "title": "Cure Wounds",
            "description": "Cure Wounds — touch to restore hit points.",
            "caster_class": "cleric",
            "distance": 5,
            "school": "evocation",
        },
        {
            "title": "Mage Hand",
            "description": "Mage Hand — spectral hand to manipulate objects.",
            "caster_class": "sorcerer",
            "distance": 30,
            "school": "conjuration",
        },
        {
            "title": "Fireball",
            "description": "Fireball — explosive fire dealing area damage.",
            "caster_class": "wizard",
            "distance": 150,
            "school": "evocation",
        },
    ]

    for item in spells:
        created = curl_post_json("/spells", item)
        print(f"Created spell id={created.get('id')} description={created.get('description')}")


def main() -> int:
    print(f"Seeding via API_BASE_URL={API_BASE_URL}")
    seed_monsters()
    seed_spells()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


