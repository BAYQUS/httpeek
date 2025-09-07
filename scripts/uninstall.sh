#!/usr/bin/env bash
set -Eeuo pipefail

GREEN="\033[1;32m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; NC="\033[0m"
SUDO="${SUDO:-}"

need() { command -v "$1" >/dev/null 2>&1; }

ensure_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    if need sudo; then SUDO="sudo"; else
      echo -e "${RED}This uninstaller needs sudo.${NC}"; exit 1
    fi
  else SUDO=""; fi
}

ask() { local a; read -r -p "$1 [y/N]: " a || true; [[ "${a:-}" =~ ^[Yy]$ ]]; }

main() {
  ensure_root

  if [[ -e /usr/bin/httpeek ]]; then
    echo "[*] Removing /usr/bin/httpeek"
    $SUDO rm -f /usr/bin/httpeek
  else
    echo "[i] /usr/bin/httpeek not found (skipping)"
  fi

  if [[ -d /usr/share/httpeek ]]; then
    echo "[*] Removing /usr/share/httpeek"
    $SUDO rm -rf /usr/share/httpeek
  else
    echo "[i] /usr/share/httpeek not found (skipping)"
  fi

  if need pipx; then
    if pipx list 2>/dev/null | grep -qi '^package .*httpeek'; then
      if ask "pipx installation detected. Uninstall via pipx too?"; then
        pipx uninstall httpeek || true
      fi
    fi
  fi

  echo -e "${GREEN}[✓] Uninstall complete.${NC}"
}

main "$@"
