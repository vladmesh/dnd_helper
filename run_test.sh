#!/usr/bin/env bash
set -euo pipefail

# Run tests for each microservice using its test docker compose file

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)

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

echo "All tests completed successfully."


