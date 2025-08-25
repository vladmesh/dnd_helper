#!/usr/bin/env python3
"""
Management script for developer operations.

Commands:
  - restart: stop, rebuild and start docker compose services (detached)
"""

import argparse
import subprocess
import sys


def run_command(command: list[str]) -> None:
    """Run a shell command and raise on failure."""
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def cmd_restart(_: argparse.Namespace) -> None:
    """Restart docker compose services: down -> build -> up -d."""
    run_command(["docker", "compose", "down"]) 
    run_command(["docker", "compose", "build"]) 
    run_command(["docker", "compose", "up", "-d"]) 


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project management utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    restart = subparsers.add_parser(
        "restart",
        help="Stop, rebuild and start docker compose services",
    )
    restart.set_defaults(func=cmd_restart)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


