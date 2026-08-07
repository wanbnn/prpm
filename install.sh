#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/wanbnn/prpm"
DEFAULT_REF="main"
PACKAGE="prpm"

usage() {
    cat <<EOF
Usage: ./install.sh [options]

Install PRPM, the package manager for the PyReact ecosystem.

Options:
  --dev           Install the development version from GitHub (\$DEFAULT_REF)
  --ref REF       Install a specific git ref (branch, tag, or commit). Implies --dev.
  --user          Install into the user site instead of the active environment
  --upgrade       Upgrade an existing installation to the requested version
  --no-verify     Skip the post-install verification step
  -h, --help      Show this help and exit

Examples:
  ./install.sh
  ./install.sh --dev
  ./install.sh --ref v0.3.0
  ./install.sh --user --upgrade
EOF
}

color_red()   { printf '\033[31m%s\033[0m\n' "$*"; }
color_green() { printf '\033[32m%s\033[0m\n' "$*"; }
color_blue()  { printf '\033[34m%s\033[0m\n' "$*"; }
color_bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

info()  { color_blue  ":: $*"; }
ok()    { color_green "OK $*"; }
fail()  { color_red   "!! $*"; }
title() { color_bold  "==> $*"; }

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        fail "Required command not found: $1"
        exit 1
    fi
}

python_version_ok() {
    "$1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1
}

pick_python() {
    local candidates=("python3" "python")
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1 && python_version_ok "$cmd"; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

DEV=0
USER=0
UPGRADE=0
VERIFY=1
REF=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            DEV=1
            shift
            ;;
        --ref)
            [[ $# -ge 2 ]] || { fail "--ref requires a value"; exit 1; }
            REF="$2"
            DEV=1
            shift 2
            ;;
        --user)
            USER=1
            shift
            ;;
        --upgrade)
            UPGRADE=1
            shift
            ;;
        --no-verify)
            VERIFY=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

title "PRPM installer"

require_command pip

if ! PYTHON_BIN="$(pick_python)"; then
    fail "Python 3.9 or newer is required but was not found."
    exit 1
fi

info "Using Python: $($PYTHON_BIN --version) ($PYTHON_BIN)"

PIP_ARGS=()
if [[ "$USER" -eq 1 ]]; then
    PIP_ARGS+=(--user)
fi
if [[ "$UPGRADE" -eq 1 ]]; then
    PIP_ARGS+=(--upgrade)
fi

if [[ "$DEV" -eq 1 ]]; then
    target="${REF:-$DEFAULT_REF}"
    target="${target#refs/heads/}"
    info "Installing development version from $REPO @ $target"
    PIP_ARGS+=("$REPO@$target")
else
    if [[ -n "$REF" ]]; then
        info "Installing from PyPI with constraint $REF"
        PIP_ARGS+=("$PACKAGE==$REF")
    else
        info "Installing $PACKAGE from PyPI"
        PIP_ARGS+=("$PACKAGE")
    fi
fi

if ! "$PYTHON_BIN" -m pip install "${PIP_ARGS[@]}"; then
    fail "pip install failed."
    exit 1
fi

ok "$PACKAGE installed."

if [[ "$VERIFY" -eq 1 ]]; then
    if ! command -v prpm >/dev/null 2>&1; then
        if [[ "$USER" -eq 1 ]]; then
            fail "prpm not found on PATH. Add ~/.local/bin to your PATH and re-run."
        else
            fail "prpm not found on PATH. Check the install location reported by pip."
        fi
        exit 1
    fi

    info "Verifying installation..."
    if prpm --version; then
        ok "PRPM is ready. Run 'prpm --help' to get started."
    else
        fail "prpm was installed but failed to run."
        exit 1
    fi
else
    info "Skipping verification (--no-verify)."
fi
