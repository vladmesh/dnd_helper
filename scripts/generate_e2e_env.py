#!/usr/bin/env python3
"""Helper for generating .env.e2e from the checked-in example."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = PROJECT_ROOT / ".env.e2e.example"
TARGET_FILE = PROJECT_ROOT / ".env.e2e"
TOKEN_PLACEHOLDER_PATTERN = re.compile(r"^TELEGRAM_BOT_TOKEN=.*$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy .env.e2e.example to .env.e2e and optionally inject a Telegram bot token. "
            "The token can be passed via --token or E2E_TELEGRAM_BOT_TOKEN."
        )
    )
    parser.add_argument(
        "--token",
        dest="token",
        help="Telegram bot token to write into TELEGRAM_BOT_TOKEN. Overrides environment variable.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing .env.e2e file instead of failing.",
    )
    return parser.parse_args()


def load_example() -> str:
    if not EXAMPLE_FILE.exists():
        raise SystemExit(".env.e2e.example is missing; cannot generate .env.e2e")
    return EXAMPLE_FILE.read_text()


def apply_token(contents: str, token: str | None) -> str:
    if not token:
        return contents
    if TOKEN_PLACEHOLDER_PATTERN.search(contents):
        return TOKEN_PLACEHOLDER_PATTERN.sub(f"TELEGRAM_BOT_TOKEN={token}", contents)
    return f"TELEGRAM_BOT_TOKEN={token}\n{contents}"


def write_env(contents: str, force: bool) -> None:
    if TARGET_FILE.exists() and not force:
        raise SystemExit(
            ".env.e2e already exists. Pass --force to overwrite or remove the file manually."
        )
    TARGET_FILE.write_text(contents)


def main() -> None:
    args = parse_args()
    token = args.token or os.environ.get("E2E_TELEGRAM_BOT_TOKEN")
    contents = load_example()
    contents = apply_token(contents, token)
    write_env(contents, force=args.force)
    if token:
        print("Written .env.e2e with TELEGRAM_BOT_TOKEN from provided token.")
    else:
        print("Written .env.e2e using example values (TELEGRAM_BOT_TOKEN left as placeholder).")


if __name__ == "__main__":
    sys.exit(main())
