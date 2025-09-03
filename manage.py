#!/usr/bin/env python3
"""
Management script for developer operations.

Commands:
  - restart: stop, rebuild and start docker compose services (detached)
"""

import argparse
import os
import subprocess
import sys
import time


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


def cmd_ultimate_restart(_: argparse.Namespace) -> None:
    """Full reset: down -v, build --no-cache, up -d, apply migrations."""
    # Stop and remove containers, networks, and volumes
    run_command(["docker", "compose", "down", "-v"]) 
    # Rebuild all services without cache
    run_command(["docker", "compose", "build"]) 
    # Start services
    run_command(["docker", "compose", "up", "-d"]) 
    # Apply migrations inside API container
    run_command([
        "docker", "compose", "exec", "--user",
        f"{os.getuid()}:{os.getgid()}", "-T", "api",
        "alembic", "upgrade", "head",
    ])
    # Wait a bit for API to be fully ready before seeding via REST
    time.sleep(5)
    # Seed data via REST (host script calling localhost:8000) for monsters and spells
    project_root = os.path.dirname(os.path.abspath(__file__))
    seed_path = os.path.join(project_root, "seed.py")
    run_command(["python3", seed_path, "--monsters", "--spells"])


def cmd_makemigration(args: argparse.Namespace) -> None:
    """Create a new Alembic migration with autogenerate inside the API container.

    Files are synced to host via bind mounts.
    """
    # Run alembic revision inside running API container
    run_command([
        "docker", "compose", "exec", "--user",
        f"{os.getuid()}:{os.getgid()}", "-T", "api",
        "alembic", "revision", "--autogenerate", "-m", args.message,
    ])


def cmd_upgrade(_: argparse.Namespace) -> None:
    """Apply Alembic migrations up to head inside the API container."""
    run_command([
        "docker", "compose", "exec", "--user",
        f"{os.getuid()}:{os.getgid()}", "-T", "api",
        "alembic", "upgrade", "head",
    ])


def cmd_lint(args: argparse.Namespace) -> None:
    """Run Ruff linter inside dedicated container (ruff service)."""
    command = [
        "docker",
        "run",
        "--rm",
        "-u",
        f"{os.getuid()}:{os.getgid()}",
        "-v",
        f"{os.getcwd()}:/io",
        "-w",
        "/io",
        "ghcr.io/astral-sh/ruff:latest",
        "check",
    ]
    if getattr(args, "fix", False):
        command.append("--fix")
    command.append(".")
    run_command(command)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project management utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    restart = subparsers.add_parser(
        "restart",
        help="Stop, rebuild and start docker compose services",
    )
    restart.set_defaults(func=cmd_restart)

    ultimate_restart = subparsers.add_parser(
        "ultimate_restart",
        help="Full reset: down -v, build --no-cache, up -d, apply migrations",
    )
    ultimate_restart.set_defaults(func=cmd_ultimate_restart)

    makemigration = subparsers.add_parser(
        "makemigration",
        help="Create a new Alembic migration with autogenerate (API service)",
    )
    makemigration.add_argument("-m", "--message", required=True, help="Migration message")
    makemigration.set_defaults(func=cmd_makemigration)

    upgrade = subparsers.add_parser(
        "upgrade",
        help="Apply Alembic migrations up to head (API service)",
    )
    upgrade.set_defaults(func=cmd_upgrade)

    lint = subparsers.add_parser(
        "lint",
        help="Run Ruff linter (containerized)",
    )
    lint.add_argument(
        "--fix",
        action="store_true",
        help="Apply automatic fixes where possible",
    )
    lint.set_defaults(func=cmd_lint)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


