#!/usr/bin/env bash
# Build spkup.app from this checkout and install it.
#
# Usage:  scripts/build-macos.sh
# Env:    SPKUP_INSTALL_DIR  install folder (default /Applications; use ~/Applications without admin)
#         PYTHON             interpreter used to create .venv (default python3.12)
set -euo pipefail
cd "$(dirname "$0")/.."

install_dir="${SPKUP_INSTALL_DIR:-/Applications}"
app="$install_dir/spkup.app"

if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then
  echo "error: this script builds the Apple Silicon (arm64) app only" >&2
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "==> Creating .venv"
  "${PYTHON:-python3.12}" -m venv .venv
fi
py=.venv/bin/python

echo "==> Installing build dependencies"
"$py" -m pip install --quiet --upgrade pip
"$py" -m pip install --quiet -e ".[build]"

echo "==> Building spkup.app"
rm -rf build dist
"$py" -m PyInstaller --clean --noconfirm --log-level WARN spkup-macos.spec
file dist/spkup.app/Contents/MacOS/spkup | grep -q arm64 || {
  echo "error: dist/spkup.app is not an arm64 build" >&2
  exit 1
}

if pgrep -xq spkup; then
  echo "==> Quitting the running spkup"
  osascript -e 'quit app "spkup"' >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do pgrep -xq spkup || break; sleep 0.25; done
  if pgrep -xq spkup; then
    echo "error: spkup is still running; quit it from the menu bar and run again" >&2
    exit 1
  fi
fi

echo "==> Installing to $app"
mkdir -p "$install_dir"
rm -rf "$app"
ditto dist/spkup.app "$app"

version=$(PYTHONPATH=src "$py" -c 'from spkup import __version__; print(__version__)')
cat <<MSG

spkup $version installed at $app
Open it with:  open "$app"

Each local build gets a new ad-hoc code signature, so macOS may treat it as a new
app. If the hotkey stops working, toggle spkup off and on under System Settings
-> Privacy & Security -> Input Monitoring.
MSG
