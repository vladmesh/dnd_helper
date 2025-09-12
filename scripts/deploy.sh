#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# dnd-helper production bootstrap (root-only)
# - Run as root. Asks for target user, grants docker access, prepares volumes,
#   writes .env and docker-compose.yml, pulls images, runs migrations, starts stack.
# -----------------------------------------------------------------------------

require_root() {
  if [ "${EUID}" -ne 0 ]; then
    echo "[x] This script must be run as root (use: sudo -E bash $0)" >&2
    exit 1
  fi
}

ensure_cmd() {
  command -v "$1" >/dev/null 2>&1
}

log() { echo "[+] $*"; }
warn(){ echo "[!] $*" >&2; }
err() { echo "[x] $*" >&2; exit 1; }

require_root

SCRIPT_DIR="$(pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

# -----------------------------------------------------------------------------
# Choose target user (will manage Docker and own files)
# -----------------------------------------------------------------------------
DEFAULT_USER="${SUDO_USER:-$(logname 2>/dev/null || echo "")}"
read -rp "Linux username to own and run the service [${DEFAULT_USER:-required}]: " RUN_AS_USER
RUN_AS_USER="${RUN_AS_USER:-$DEFAULT_USER}"
[ -n "${RUN_AS_USER}" ] || err "Username is required."
id -u "${RUN_AS_USER}" >/dev/null 2>&1 || err "User '${RUN_AS_USER}' does not exist."

# -----------------------------------------------------------------------------
# Create data dirs with correct ownership
# -----------------------------------------------------------------------------
mkdir -p "${SCRIPT_DIR}/data/postgres" \
         "${SCRIPT_DIR}/data/redis" \
         "${SCRIPT_DIR}/data/admin_uploads"
chown -R "${RUN_AS_USER}:${RUN_AS_USER}" "${SCRIPT_DIR}/data"
log "Prepared data dirs: data/postgres, data/redis, data/admin_uploads"

# -----------------------------------------------------------------------------
# Install Docker Engine + Compose plugin if missing
# -----------------------------------------------------------------------------
install_docker_ubuntu() {
  log "Installing Docker Engine + Compose plugin (Ubuntu/Debian)..."
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release
  install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  fi
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(. /etc/os-release; echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable docker
  systemctl start docker
}

if ! ensure_cmd docker; then
  if [ -f /etc/debian_version ] || grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
    install_docker_ubuntu
  else
    warn "Non-Debian/Ubuntu detected. Using Docker convenience script."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker || true
    systemctl start docker || true
  fi
else
  log "Docker is installed: $(docker --version)"
fi

if ! docker compose version >/dev/null 2>&1; then
  warn "Docker Compose plugin missing. Installing (Ubuntu/Debian)..."
  if [ -f /etc/debian_version ] || grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
    install_docker_ubuntu
  else
    err "Compose plugin missing and auto-install unsupported on this distro. Install docker-compose-plugin manually."
  fi
else
  log "docker compose is available: $(docker compose version | head -n1)"
fi

# -----------------------------------------------------------------------------
# Ensure docker group and grant access to target user
# -----------------------------------------------------------------------------
if ! getent group docker >/dev/null 2>&1; then
  groupadd docker
  log "Created group 'docker'"
fi
usermod -aG docker "${RUN_AS_USER}"
log "Added ${RUN_AS_USER} to 'docker' group"

# -----------------------------------------------------------------------------
# Ensure Docker socket access is immediate for the chosen user (no relogin)
# -----------------------------------------------------------------------------
# Wait for docker socket to appear
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if [ -S /var/run/docker.sock ]; then
    break
  fi
  sleep 1
done

if [ ! -S /var/run/docker.sock ]; then
  warn "Docker socket not found yet. Restarting docker service..."
  systemctl restart docker || true
  sleep 2
fi

# Install ACL tool if missing (for Debian/Ubuntu), then grant socket ACL to user
if ! command -v setfacl >/dev/null 2>&1; then
  if [ -f /etc/debian_version ] || grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
    apt-get update -y
    apt-get install -y acl
  else
    warn "'setfacl' not found and auto-install unsupported on this distro; skipping ACL grant."
  fi
fi

if command -v setfacl >/dev/null 2>&1 && [ -S /var/run/docker.sock ]; then
  setfacl -m u:${RUN_AS_USER}:rw /var/run/docker.sock || warn "Failed to set ACL on /var/run/docker.sock for ${RUN_AS_USER}"
  log "Granted immediate access to Docker socket for ${RUN_AS_USER} via ACL"
fi

# -----------------------------------------------------------------------------
# Ask envs, write .env
# -----------------------------------------------------------------------------
echo
echo "Configure environment (.env). Press Enter to accept defaults."

read -rp "GHCR owner (org/user) [required]: " GHCR_OWNER
[ -n "${GHCR_OWNER}" ] || err "GHCR owner is required (e.g., your GitHub org or username)."

read -rp "Images tag [latest]: " IMAGE_TAG
IMAGE_TAG="${IMAGE_TAG:-latest}"

read -rp "API_PORT [8000]: " API_PORT
API_PORT="${API_PORT:-8000}"

read -rp "POSTGRES_DB [dnd_db]: " POSTGRES_DB
POSTGRES_DB="${POSTGRES_DB:-dnd_db}"

read -rp "POSTGRES_USER [dnd_user]: " POSTGRES_USER
POSTGRES_USER="${POSTGRES_USER:-dnd_user}"

read -srp "POSTGRES_PASSWORD [dnd_password]: " POSTGRES_PASSWORD_INPUT
echo
POSTGRES_PASSWORD="${POSTGRES_PASSWORD_INPUT:-dnd_password}"

read -rp "POSTGRES_HOST [postgres]: " POSTGRES_HOST
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"

read -rp "POSTGRES_PORT [5432]: " POSTGRES_PORT
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

read -rp "Enable admin panel? (y/N) [ADMIN_ENABLED]: " ADMIN_ENABLED_ANSWER
case "${ADMIN_ENABLED_ANSWER:-N}" in y|Y) ADMIN_ENABLED=true ;; *) ADMIN_ENABLED=false ;; esac

ADMIN_TOKEN=""
if [ "${ADMIN_ENABLED}" = "true" ]; then
  read -srp "ADMIN_TOKEN [required when admin enabled]: " ADMIN_TOKEN
  echo
  [ -n "${ADMIN_TOKEN}" ] || err "ADMIN_TOKEN is required when admin is enabled."
fi

read -rp "TELEGRAM_BOT_TOKEN [empty to skip starting bot]: " TELEGRAM_BOT_TOKEN

read -rp "LOG_LEVEL [INFO]: " LOG_LEVEL
LOG_LEVEL="${LOG_LEVEL:-INFO}"
read -rp "LOG_JSON (true/false) [true]: " LOG_JSON
LOG_JSON="${LOG_JSON:-true}"

ts="$(date +%Y%m%d_%H%M%S)"
[ -f "${ENV_FILE}" ] && cp -f "${ENV_FILE}" "${ENV_FILE}.bak.${ts}" && log "Backed up .env -> .env.bak.${ts}"
[ -f "${COMPOSE_FILE}" ] && cp -f "${COMPOSE_FILE}" "${COMPOSE_FILE}.bak.${ts}" && log "Backed up compose -> docker-compose.yml.bak.${ts}"

cat > "${ENV_FILE}" <<EOF
# --- dnd-helper production .env ---
API_PORT=${API_PORT}

POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_HOST=${POSTGRES_HOST}
POSTGRES_PORT=${POSTGRES_PORT}

ADMIN_ENABLED=${ADMIN_ENABLED}
ADMIN_TOKEN=${ADMIN_TOKEN}

TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}

LOG_LEVEL=${LOG_LEVEL}
LOG_JSON=${LOG_JSON}
EOF
chown "${RUN_AS_USER}:${RUN_AS_USER}" "${ENV_FILE}"
log "Wrote ${ENV_FILE}"

# -----------------------------------------------------------------------------
# Generate production docker-compose.yml
# - Uses GHCR images; only API exposed; bot/redis/postgres are internal
# - Runs Alembic migrations inside API container before starting app
# -----------------------------------------------------------------------------
cat > "${COMPOSE_FILE}" <<EOF
services:
  postgres:
    image: postgres:16-alpine
    container_name: dnd_postgres
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - POSTGRES_DB=\${POSTGRES_DB}
      - POSTGRES_USER=\${POSTGRES_USER}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: dnd_redis
    restart: unless-stopped
    volumes:
      - ./data/redis:/data

  api:
    image: ghcr.io/${GHCR_OWNER}/dnd-helper-api:${IMAGE_TAG}
    container_name: dnd_api
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app/src
      - LOG_LEVEL=\${LOG_LEVEL}
      - LOG_JSON=\${LOG_JSON}
      - LOG_SERVICE_NAME=api
    depends_on:
      - postgres
      - redis
    ports:
      - "\${API_PORT:-8000}:8000"
    command: sh -lc "alembic upgrade head && python -m dnd_helper_api.main"
    volumes:
      - ./data/admin_uploads:/data/admin_uploads

  bot:
    image: ghcr.io/${GHCR_OWNER}/dnd-helper-bot:${IMAGE_TAG}
    container_name: dnd_bot
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app/src
      - LOG_LEVEL=\${LOG_LEVEL}
      - LOG_JSON=\${LOG_JSON}
      - LOG_SERVICE_NAME=bot
    depends_on:
      - redis
      - postgres
    command: python -m dnd_helper_bot.main
EOF
chown "${RUN_AS_USER}:${RUN_AS_USER}" "${COMPOSE_FILE}"
log "Wrote ${COMPOSE_FILE}"

# -----------------------------------------------------------------------------
# Pull and start stack as target user in docker group (no relogin required)
# -----------------------------------------------------------------------------
# Some systems may lack 'sg'; if so, fallback to root (warn).
if command -v sg >/dev/null 2>&1; then
  log "Pulling images as ${RUN_AS_USER}..."
  sg docker -c "sudo -u '${RUN_AS_USER}' -E bash -lc 'cd \"${SCRIPT_DIR}\" && docker compose pull'"
  log "Starting services as ${RUN_AS_USER}..."
  sg docker -c "sudo -u '${RUN_AS_USER}' -E bash -lc 'cd \"${SCRIPT_DIR}\" && docker compose up -d'"
else
  warn "'sg' not found. Running docker commands as root (temporary). User '${RUN_AS_USER}' is in docker group for future sessions."
  docker compose pull
  docker compose up -d
fi

# Wait per policy before health checks
sleep 7

if curl -fsS "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
  log "API is healthy at http://localhost:${API_PORT}"
else
  warn "API health check failed. Inspect logs: docker compose logs --no-color | cat"
fi

log "Done. Owner user: ${RUN_AS_USER}"
log "Data dirs: ./data/postgres, ./data/redis, ./data/admin_uploads"