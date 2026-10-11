#!/usr/bin/env bash
# ==============================================================================
# AndroidStudio-For-Android Bootstrap / 1-Liner Entrypoint
# Repository: https://github.com/sirvkrm/AndroidStudio-For-Android
# ==============================================================================
set -eo pipefail

SCRIPT_SRC="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SRC")" 2>/dev/null && pwd || echo "$HOME")"

# Ensure python3 is available in Termux
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required for the interactive setup wizard."
    if command -v pkg >/dev/null 2>&1; then
        echo "Installing python via 'pkg install python -y'..."
        pkg install -y python
    fi
fi

# Reattach stdin from /dev/tty if running from a pipe (e.g. curl ... | bash)
run_python() {
    local script="$1"; shift
    if [ ! -t 0 ] && [ -e /dev/tty ]; then
        python3 "$script" "$@" < /dev/tty
    else
        python3 "$script" "$@"
    fi
}

# If setup.py is present locally, run it
if [ -f "$SCRIPT_DIR/setup.py" ]; then
    run_python "$SCRIPT_DIR/setup.py" "$@"
    exit 0
fi

# If piped directly via curl, download setup.py to a temp dir and run
TMP_SETUP="$(mktemp --suffix=.py)"
echo "Downloading interactive setup wizard..."
curl -fsSL https://raw.githubusercontent.com/sirvkrm/AndroidStudio-For-Android/main/setup.py -o "$TMP_SETUP"
trap 'rm -f "$TMP_SETUP"' EXIT
run_python "$TMP_SETUP" "$@"
