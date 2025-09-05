#!/usr/bin/env bash
set -euo pipefail

# Selective test runner based on staged changes
# Rules:
# 1) Only text/docs/json changed -> skip tests
# 2) Only bot/** changed (no api/** or shared_models/**) -> run bot tests only
# 3) Otherwise -> run full test suite (api + bot)

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

CHANGED=$(git diff --name-only --cached || true)

if [[ -z "$CHANGED" ]]; then
  echo "[selective-tests] No staged changes -> skip tests"
  exit 0
fi

# Derive non-text files list
# Text includes: any *.md, *.json, and anything under docs/ or docs/tasks/
NON_TEXT=$(printf '%s\n' "$CHANGED" | grep -Ev '(^docs/|^docs/tasks/|\.md$|\.json$)' || true)

if [[ -z "$NON_TEXT" ]]; then
  echo "[selective-tests] Only text/docs/json changed -> skip tests"
  exit 0
fi

# If any api/ or shared_models/ present among non-text -> FULL
if printf '%s\n' "$NON_TEXT" | grep -Eq '^(api/|shared_models/)'; then
  echo "[selective-tests] API or shared_models changed -> run FULL tests"
  echo "[API] Running tests..."
  cd "$ROOT_DIR/api"
  docker compose -f docker_compose_tests.yml build | cat
  docker compose -f docker_compose_tests.yml run --rm api-tests | cat
  docker compose -f docker_compose_tests.yml down -v | cat

  echo "[BOT] Running tests..."
  cd "$ROOT_DIR/bot"
  docker compose -f docker_compose_tests.yml build | cat
  docker compose -f docker_compose_tests.yml run --rm bot-tests | cat
  docker compose -f docker_compose_tests.yml down -v | cat
  exit 0
fi

# If all non-text under bot/ -> BOT only
if printf '%s\n' "$NON_TEXT" | grep -Eq '^(bot/)'; then
  if ! printf '%s\n' "$NON_TEXT" | grep -Ev '^(bot/)' | grep -q .; then
    echo "[selective-tests] Only bot code changed -> run BOT tests"
    cd "$ROOT_DIR/bot"
    docker compose -f docker_compose_tests.yml build | cat
    docker compose -f docker_compose_tests.yml run --rm bot-tests | cat
    docker compose -f docker_compose_tests.yml down -v | cat
    exit 0
  fi
fi

# Fallback: treat as full
echo "[selective-tests] Mixed changes -> run FULL tests"
echo "[API] Running tests..."
cd "$ROOT_DIR/api"
docker compose -f docker_compose_tests.yml build | cat
docker compose -f docker_compose_tests.yml run --rm api-tests | cat
docker compose -f docker_compose_tests.yml down -v | cat

echo "[BOT] Running tests..."
cd "$ROOT_DIR/bot"
docker compose -f docker_compose_tests.yml build | cat
docker compose -f docker_compose_tests.yml run --rm bot-tests | cat
docker compose -f docker_compose_tests.yml down -v | cat

exit 0


