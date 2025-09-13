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


def run_capture(command: list[str]) -> tuple[int, str, str]:
    """Run a command and capture (rc, stdout, stderr)."""
    p = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr


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
    time.sleep(7)
    # --- Seed enums and UI translations via universal bundle ingest ---
    project_root = os.path.dirname(os.path.abspath(__file__))
    bundle_dir = os.path.join(project_root, "data", "seed_bundle")
    manifest_path = os.path.join(bundle_dir, "manifest.json")
    bundle_zip = os.path.join(bundle_dir, "bundle.zip")
    if not os.path.exists(manifest_path):
        raise SystemExit("seed bundle manifest.json not found: " + manifest_path)
    # Create/refresh zip archive deterministically
    import zipfile
    with zipfile.ZipFile(bundle_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in ("manifest.json", "enum_translations.en.jsonl", "enum_translations.ru.jsonl", "ui_translations.jsonl"):
            path = os.path.join(bundle_dir, name)
            if os.path.exists(path):
                zf.write(path, arcname=name)
    # Load ADMIN_TOKEN from .env
    env_path = os.path.join(project_root, ".env")
    admin_token = os.environ.get("ADMIN_TOKEN", "")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("ADMIN_TOKEN=") and not admin_token:
                        admin_token = line.split("=", 1)[1]
                        break
        except Exception:
            pass
    if not admin_token:
        raise SystemExit("ADMIN_TOKEN is required in environment or .env for admin ingest")
    # Use curl in a container to POST bundle and poll job status; parse JSON in Python
    rc, out, err = run_capture([
        "docker", "run", "--rm",
        "--network", "dnd_helper_default",
        "-v", f"{bundle_dir}:/bundle:ro",
        "curlimages/curl:8.10.1",
        "-sS",
        "-H", f"Authorization: Bearer {admin_token}",
        "-F", "file=@/bundle/bundle.zip",
        "http://api:8000/admin-api/ingest/bundle",
    ])
    if rc != 0:
        sys.stderr.write(err)
        raise SystemExit(rc)
    try:
        import json as _json
        job_id = _json.loads(out).get("id")
    except Exception:
        sys.stderr.write("Failed to parse ingest response: " + out + "\n")
        raise SystemExit(1)
    if not job_id:
        sys.stderr.write("Ingest response missing id: " + out + "\n")
        raise SystemExit(1)
    # Poll job status up to 60s
    for _ in range(60):
        rc, out, err = run_capture([
            "docker", "run", "--rm",
            "--network", "dnd_helper_default",
            "curlimages/curl:8.10.1",
            "-sS",
            "-H", f"Authorization: Bearer {admin_token}",
            f"http://api:8000/admin-api/ingest/jobs/{job_id}",
        ])
        if rc != 0:
            sys.stderr.write(err)
            raise SystemExit(rc)
        try:
            data = _json.loads(out)
            status = str(data.get("status") or "")
        except Exception:
            sys.stderr.write("Failed to parse job status: " + out + "\n")
            raise SystemExit(1)
        if status == "succeeded":
            break
        if status == "failed":
            sys.stderr.write("Ingest job failed: " + out + "\n")
            raise SystemExit(2)
        time.sleep(1)
    else:
        sys.stderr.write("Ingest job did not complete within timeout\n")
        raise SystemExit(3)


def cmd_parce_core(args: argparse.Namespace) -> None:
    """Run server-filtered core parsing inside parser image with correct UID/GID."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    server_url = 'https://dnd.su/bestiary/?search=&source=102%7C101%7C103%7C158%7C111%7C109'
    output_dir = os.path.join(project_root, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Build image to ensure it's available
    run_command([
        "docker", "build",
        "-f", os.path.join(project_root, "scripts/monster_parser/Dockerfile"),
        "-t", "dnd_helper/monster_parser:latest",
        project_root,
    ])

    # Run parsing with host UID/GID so output is writable/deletable (force server-filtered mode)
    run_command([
        "docker", "run", "--rm",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{project_root}:/app",
        "-w", "/app/scripts/monster_parser",
        "dnd_helper/monster_parser:latest",
        "python3", "filtered_mass_parser.py",
        "--server-filtered-url", server_url,
        "--output-dir", "/app/" + args.output_dir,
        "--final-file-name", args.final_file_name,
        "--batch-size", str(args.batch_size),
    ] + (["--test-limit", str(args.test_limit)] if args.test_limit and args.test_limit > 0 else []))

    # Then update seed_data_monsters.json -> seed_data_monsters_updated.json
    run_command([
        "docker", "run", "--rm",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{project_root}:/app",
        "-w", "/app/scripts/monster_parser",
        "dnd_helper/monster_parser:latest",
        "python3", "update_monster_translations.py",
        "--seed-in", "/app/seed_data_monsters.json",
        "--seed-out", "/app/seed_data_monsters_updated.json",
        "--parsed-in", f"/app/{args.output_dir}/" + args.final_file_name,
    ])


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


def cmd_format(_: argparse.Namespace) -> None:
    """Format codebase using Ruff (import sorting + formatter)."""
    base = [
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
    ]
    # 1) Apply all available auto-fixes from configured lint rules
    run_command(base + ["check", "--fix", "."])
    # 2) Apply Ruff formatter (Black-compatible)
    run_command(base + ["format", "."])


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

    fmt = subparsers.add_parser(
        "format",
        help="Format code using Ruff (imports + formatter)",
    )
    fmt.set_defaults(func=cmd_format)

    # Parser: fetch Core monsters via server-filtered URL into output files
    parse_core = subparsers.add_parser(
        "parce_core",
        help="Fetch Core monsters from dnd.su (server-filtered) into scripts/monster_parser/output",
    )
    parse_core.add_argument(
        "--test-limit",
        type=int,
        default=0,
        help="Limit number of monsters to parse (0 = all)",
    )
    parse_core.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Batch size for parsing",
    )
    parse_core.add_argument(
        "--output-dir",
        default="scripts/monster_parser/output",
        help="Output directory for parser results (relative to project root)",
    )
    parse_core.add_argument(
        "--final-file-name",
        default="parsed_monsters_filtered_final.json",
        help="Final aggregated JSON filename",
    )
    parse_core.set_defaults(func=cmd_parce_core)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


