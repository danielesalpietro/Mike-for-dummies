#!/usr/bin/env bash
# Equivalente di: docker compose down

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[mike-lxd]${NC} $*"; }
warn() { echo -e "${YELLOW}[mike-lxd]${NC} $*"; }

for c in mike-backend mike-frontend; do
  if lxc info "$c" >/dev/null 2>&1; then
    info "Fermo e rimuovo: $c"
    lxc stop "$c" --force 2>/dev/null || true
    lxc delete "$c"
  else
    warn "Container $c non trovato, skip."
  fi
done

for p in mike-backend mike-frontend mike-common; do
  if lxc profile show "$p" >/dev/null 2>&1; then
    info "Rimuovo profilo: $p"
    lxc profile delete "$p"
  fi
done

info "Teardown completato."
