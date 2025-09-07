#!/usr/bin/env bash
set -Eeuo pipefail

GREEN="\033[1;32m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; BLUE="\033[1;34m"; NC="\033[0m"
SUDO="${SUDO:-}"

banner() {
cat <<'BANNER'
██╗  ██╗████████╗████████╗██████╗ ███████╗███████╗██╗  ██╗
██║  ██║╚══██╔══╝╚══██╔══╝██╔══██╗██╔════╝██╔════╝██║ ██╔╝
███████║   ██║      ██║   ██████╔╝█████╗  █████╗  █████╔╝ 
██╔══██║   ██║      ██║   ██╔═══╝ ██╔══╝  ██╔══╝  ██╔═██╗ 
██║  ██║   ██║      ██║   ██║     ███████╗███████╗██║  ██╗
╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
Pentest-grade HTTP recon with Rich TUI, TLS info & CF signals
BANNER
}

need() { command -v "$1" >/dev/null 2>&1; }

ensure_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    if need sudo; then SUDO="sudo"; else
      echo -e "${RED}This installer needs sudo.${NC}"; exit 1
    fi
  else SUDO=""; fi
}

ask() {
  local q="$1" ans; read -r -p "$q [y/N]: " ans || true
  [[ "${ans:-}" =~ ^[Yy]$ ]]
}

pkgmgr() {
  if need apt-get; then echo apt; return; fi
  if need dnf; then echo dnf; return; fi
  if need pacman; then echo pacman; return; fi
  echo unknown
}

pkgi() {
  local m="$1"; shift
  case "$m" in
    apt)    $SUDO apt-get update -y; $SUDO apt-get install -y "$@";;
    dnf)    $SUDO dnf install -y "$@";;
    pacman) $SUDO pacman -Sy --noconfirm "$@";;
    *)      echo -e "${YELLOW}Please install: $*${NC}";;
  esac
}

main() {
  banner
  echo -e "${BLUE}This will install ${GREEN}httpeek${BLUE} system-wide.${NC}"
  echo -e "Target dir: ${YELLOW}/usr/share/httpeek${NC}   Wrapper: ${YELLOW}/usr/bin/httpeek${NC}"
  echo

  if ! ask "Proceed?"; then echo "Aborted."; exit 0; fi
  ensure_root

  # Find repo root (this script lives in repo_root/scripts/)
  local SRC
  SRC="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

  # Support both layouts:
  #  A) repo_root/httpeek.py + repo_root/includes
  #  B) repo_root/httpeek/httpeek.py + repo_root/httpeek/includes
  local ENTRY_PATH="" INCLUDES_PATH=""
  if [[ -f "$SRC/httpeek.py" ]]; then
    ENTRY_PATH="httpeek.py"
    [[ -d "$SRC/includes" ]] && INCLUDES_PATH="includes"
  elif [[ -f "$SRC/httpeek/httpeek.py" ]]; then
    ENTRY_PATH="httpeek/httpeek.py"
    [[ -d "$SRC/httpeek/includes" ]] && INCLUDES_PATH="httpeek/includes"
  fi

  if [[ -z "$ENTRY_PATH" ]]; then
    echo -e "${RED}Cannot find httpeek entry point.${NC}"
    echo -e "Expected one of:"
    echo -e "  - ${YELLOW}$SRC/httpeek.py${NC}"
    echo -e "  - ${YELLOW}$SRC/httpeek/httpeek.py${NC}"
    exit 1
  fi
  if [[ -z "$INCLUDES_PATH" ]]; then
    echo -e "${YELLOW}Warning:${NC} includes/ directory not found next to entry. Continuing anyway."
  fi

  # deps for venv/pip
  local M; M="$(pkgmgr)"
  case "$M" in
    apt)    pkgi apt python3-venv python3-pip ;;
    dnf)    pkgi dnf python3-virtualenv python3-pip ;;
    pacman) pkgi pacman python-virtualenv python-pip ;;
    *)      echo -e "${YELLOW}Ensure python3-venv and pip are installed.${NC}";;
  esac

  echo -e "${BLUE}[*] Staging to /usr/share/httpeek${NC}"
  $SUDO rm -rf /usr/share/httpeek
  $SUDO mkdir -p /usr/share/httpeek
  $SUDO cp -a "$SRC"/. /usr/share/httpeek/

  echo -e "${BLUE}[*] Creating venv${NC}"
  $SUDO python3 -m venv /usr/share/httpeek/.venv

  echo -e "${BLUE}[*] Installing dependencies into venv${NC}"
  $SUDO bash -c 'set -Eeuo pipefail
    source /usr/share/httpeek/.venv/bin/activate
    python -m pip install -U pip setuptools wheel
    if [ -f /usr/share/httpeek/requirements.txt ]; then
      python -m pip install -r /usr/share/httpeek/requirements.txt
    else
      # minimal fallbacks; adjust if needed
      python -m pip install "httpx>=0.24.1" "beautifulsoup4>=4.12.3" "rich>=13.7.1" "dnspython>=2.4.2"
    fi
  '

  echo -e "${BLUE}[*] Writing wrapper /usr/bin/httpeek${NC}"
  cat <<'WRAP' | $SUDO tee /usr/bin/httpeek >/dev/null
#!/usr/bin/env bash
# Run httpeek from its dedicated venv, supporting two repo layouts.
set -Eeuo pipefail

ROOT="/usr/share/httpeek"
PY="$ROOT/.venv/bin/python"

if [[ -f "$ROOT/httpeek.py" ]]; then
  exec "$PY" "$ROOT/httpeek.py" "$@"
elif [[ -f "$ROOT/httpeek/httpeek.py" ]]; then
  exec "$PY" "$ROOT/httpeek/httpeek.py" "$@"
elif [[ -d "$ROOT/httpeek" && -f "$ROOT/httpeek/__init__.py" ]]; then
  # Fallback to module execution if packaged layout is present
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  exec "$PY" -m httpeek "$@"
else
  echo "Cannot locate httpeek entry point under $ROOT" >&2
  exit 1
fi
WRAP
  $SUDO chmod +x /usr/bin/httpeek

  echo -e "${GREEN}[+] Installed: /usr/bin/httpeek${NC}"
  echo -e "${BLUE}Test:${NC} httpeek --help || true"
  /usr/bin/httpeek --help || true
}

main "$@"
