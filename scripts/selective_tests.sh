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

is_text_file() {
  local f="$1"
  [[ "$f" =~ \.md$ ]] || [[ "$f" == docs/* ]] || [[ "$f" == docs/tasks/* ]] || [[ "$f" =~ \.json$ ]]
}

is_bot_file() {
  local f="$1"
  [[ "$f" == bot/* ]]
}

is_api_or_shared_file() {
  local f="$1"
  [[ "$f" == api/* ]] || [[ "$f" == shared_models/* ]]
}

all_text=true
any_api_or_shared=false
all_under_bot=true

while IFS= read -r file; do
  # Empty lines guard
  [[ -z "$file" ]] && continue

  if ! is_text_file "$file"; then
    all_text=false
  fi

  if is_api_or_shared_file "$file"; then
    any_api_or_shared=true
  fi

  if ! is_bot_file "$file"; then
    all_under_bot=false
  fi
done <<< "$CHANGED"

if [[ "$all_text" == true ]]; then
  echo "[selective-tests] Only text/docs/json changed -> skip tests"
  exit 0
fi

if [[ "$any_api_or_shared" == true ]]; then
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

if [[ "$all_under_bot" == true ]]; then
  echo "[selective-tests] Only bot code changed -> run BOT tests"
  cd "$ROOT_DIR/bot"
  docker compose -f docker_compose_tests.yml build | cat
  docker compose -f docker_compose_tests.yml run --rm bot-tests | cat
  docker compose -f docker_compose_tests.yml down -v | cat
  exit 0
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


