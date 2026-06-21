#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.e2e.yml"
ENV_FILE=".env.e2e"

cat >"${ENV_FILE}" <<'ENV'
POSTGRES_DB=dnd_helper_e2e
POSTGRES_USER=dnd_helper
POSTGRES_PASSWORD=dnd_helper
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
LOG_JSON=false
LOG_SERVICE_NAME=api
ADMIN_ENABLED=false
ENV

cleanup() {
  docker compose -f "${COMPOSE_FILE}" down -v >/dev/null 2>&1 || true
}

trap cleanup EXIT

docker compose -f "${COMPOSE_FILE}" up -d --build

wait_for_service() {
  local service="$1"
  local timeout="${2:-120}"
  local start_time
  start_time=$(date +%s)

  while true; do
    local container_id
    container_id=$(docker compose -f "${COMPOSE_FILE}" ps -q "$service")
    if [[ -n "${container_id}" ]]; then
      local health
      health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container_id}")
      if [[ "${health}" == "healthy" ]]; then
        echo "${service} is ready (healthy)."
        break
      fi
    fi

    if (( $(date +%s) - start_time > timeout )); then
      echo "Timed out waiting for ${service} to become healthy" >&2
      docker compose -f "${COMPOSE_FILE}" logs "${service}" || true
      exit 1
    fi

    sleep 2
  done
}

wait_for_service postgres 120
wait_for_service redis 120
wait_for_service api 180

docker compose -f "${COMPOSE_FILE}" run --rm e2e-tests
