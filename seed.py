#!/usr/bin/env python3
"""
Seed data into the running API from a single file seed_data.json.

This is a thin entrypoint that delegates to the seeding CLI implementation.
"""
from __future__ import annotations

from seeding.cli import main

if __name__ == "__main__":
    raise SystemExit(main())


