#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET="${1:-all}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[mike-lxd]${NC} $*"; }
warn()  { echo -e "${YELLOW}[mike-lxd]${NC} $*"; }
error() { echo -e "${RED}[mike-lxd]${NC} $*" >&2; exit 1; }

command -v lxc >/dev/null 2>&1 || error "lxc non trovato."

inject_env() {
  local container="$1" env_file="$2"
  [[ ! -f "$env_file" ]] && { warn "File env non trovato: $env_file (skip)"; return; }
  info "Iniezione variabili da $env_file..."
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    [[ "$line" != *=* ]] && continue
    lxc config set "$container" "environment.${line%%=*}=${line#*=}"
  done < "$env_file"
}

ensure_common_profile() {
  if ! lxc profile show mike-common >/dev/null 2>&1; then
    info "Creazione profilo mike-common..."
    lxc profile create mike-common
    lxc profile edit mike-common < "$SCRIPT_DIR/profiles/common.yaml"
  fi
}

launch_container() {
  local name="$1" service="$2" port="$3" env_suffix="${4:-}"

  info "=== Lancio container: $name ==="

  if lxc info "$name" >/dev/null 2>&1; then
    warn "Container $name già esistente. Fermo e rimuovo..."
    lxc stop "$name" --force 2>/dev/null || true
    lxc delete "$name"
  fi

  if lxc profile show "mike-$service" >/dev/null 2>&1; then
    lxc profile delete "mike-$service"
  fi

  # Crea profilo e imposta config
  lxc profile create "mike-$service"
  lxc profile set "mike-$service" limits.cpu=2
  lxc profile set "mike-$service" limits.memory=2GB
  lxc profile set "mike-$service" user.user-data="$(cat "$SCRIPT_DIR/cloud-init/${service}.yaml")"

  # Aggiungi device via CLI (più affidabile del YAML)
  lxc profile device add "mike-$service" app disk \
    source="$PROJECT_ROOT/$service" \
    path=/app \
    shift=true

  lxc profile device add "mike-$service" "port${port}" proxy \
    listen="tcp:0.0.0.0:${port}" \
    connect="tcp:127.0.0.1:${port}"

  info "Profilo mike-$service creato."

  # Lancia il container
  lxc launch ubuntu:22.04 "$name" \
    --profile mike-common \
    --profile "mike-$service"

  info "Attendo che cloud-init finisca..."
  lxc exec "$name" -- cloud-init status --wait

  # npm install dentro il container (ora /app è montato con permessi corretti)
  info "Eseguo npm install..."
  lxc exec "$name" -- bash -c "cd /app && npm install --legacy-peer-deps"

  # Inietta env vars
  inject_env "$name" "$PROJECT_ROOT/${service}/.env${env_suffix}"

  # Avvia il servizio
  lxc exec "$name" -- systemctl enable "mike-${service}.service"
  lxc exec "$name" -- systemctl start  "mike-${service}.service"

  info "Container $name pronto."
  lxc exec "$name" -- systemctl status "mike-${service}.service" --no-pager || true
}

ensure_common_profile

case "$TARGET" in
  backend)  launch_container "mike-backend"  "backend"  3001 "" ;;
  frontend) launch_container "mike-frontend" "frontend" 3000 ".local" ;;
  all)
    launch_container "mike-backend"  "backend"  3001 ""
    launch_container "mike-frontend" "frontend" 3000 ".local"
    ;;
  *) error "Usa: all | backend | frontend" ;;
esac

echo ""
info "=== Container in esecuzione ==="
lxc list "mike-" --columns "ns4t"
echo ""
info "Backend  → http://localhost:3001"
info "Frontend → http://localhost:3000"
info "Log:   lxc exec mike-backend -- journalctl -fu mike-backend.service"
info "Shell: lxc exec mike-backend -- bash"
