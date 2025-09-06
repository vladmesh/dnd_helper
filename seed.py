#!/usr/bin/env python3
"""
Seed data into the running API using split JSON files:
  - seed_data_enums.json
  - seed_data_spells.json
  - seed_data_monsters.json

This is a thin entrypoint that delegates to the seeding CLI implementation.
"""
from __future__ import annotations

from seeding.cli import main

if __name__ == "__main__":
    raise SystemExit(main())


