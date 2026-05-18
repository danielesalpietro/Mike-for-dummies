#!/usr/bin/env bash
# Equivalente di: docker compose up --build
# Uso: ./lxd/launch.sh [all|backend|frontend]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET="${1:-all}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[mike-lxd]${NC} $*"; }
warn()  { echo -e "${YELLOW}[mike-lxd]${NC} $*"; }
error() { echo -e "${RED}[mike-lxd]${NC} $*" >&2; exit 1; }

command -v lxc >/dev/null 2>&1 || error "lxc non trovato. Installa LXD: snap install lxd && lxd init"

inject_env() {
  local container="$1" env_file="$2"
  [[ ! -f "$env_file" ]] && { warn "File env non trovato: $env_file (skip)"; return; }
  info "Iniezione variabili da $env_file in $container..."
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    [[ "$line" != *=* ]] && continue
    lxc config set "$container" "environment.${line%%=*}=${line#*=}"
  done < "$env_file"
}

create_profile() {
  local name="$1"
  local file="$SCRIPT_DIR/profiles/${name#mike-}.yaml"
  lxc profile show "$name" >/dev/null 2>&1 && { warn "Profilo $name già esistente, aggiorno..."; lxc profile delete "$name"; }
  local content; content=$(sed "s|SOURCE_PATH|${PROJECT_ROOT}|g" "$file")
  lxc profile create "$name"
  echo "$content" | lxc profile edit "$name"
  info "Profilo $name creato."
}

ensure_common_profile() {
  if ! lxc profile show mike-common >/dev/null 2>&1; then
    info "Creazione profilo mike-common..."
    lxc profile create mike-common
    lxc profile edit mike-common < "$SCRIPT_DIR/profiles/common.yaml"
  fi
}

launch_container() {
  local name="$1" service="$2" env_suffix="${3:-}"
  info "=== Lancio container: $name ==="
  if lxc info "$name" >/dev/null 2>&1; then
    warn "Container $name già esistente. Fermo e rimuovo..."
    lxc stop "$name" --force 2>/dev/null || true
    lxc delete "$name"
  fi
  create_profile "mike-$service"
  lxc profile set "mike-$service" user.user-data="$(cat "$SCRIPT_DIR/cloud-init/${service}.yaml")"
  lxc launch ubuntu:22.04 "$name" --profile mike-common --profile "mike-$service"
  info "Attendo che cloud-init finisca..."
  lxc exec "$name" -- cloud-init status --wait || warn "cloud-init warning su $name"
  inject_env "$name" "$PROJECT_ROOT/${service}/.env${env_suffix}"
  info "Container $name pronto."
  lxc exec "$name" -- systemctl status "mike-${service}.service" --no-pager || true
}

ensure_common_profile

case "$TARGET" in
  backend)  launch_container "mike-backend"  "backend"  "" ;;
  frontend) launch_container "mike-frontend" "frontend" ".local" ;;
  all)
    launch_container "mike-backend"  "backend"  ""
    launch_container "mike-frontend" "frontend" ".local"
    ;;
  *) error "Usa: all | backend | frontend" ;;
esac

echo ""
info "=== Container in esecuzione ==="
lxc list "mike-" --columns "ns4t"
echo ""
info "Backend  → http://localhost:3001"
info "Frontend → http://localhost:3000"
echo ""
info "Log:   lxc exec mike-backend -- journalctl -fu mike-backend.service"
info "Shell: lxc exec mike-backend -- bash"
