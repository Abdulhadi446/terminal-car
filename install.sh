#!/usr/bin/env bash
# install.sh - install terminal-car and make `car` runnable from any shell
# Usage: ./install.sh [--user|--system|--prefix DIR]

set -euo pipefail

REPO_NAME="terminal-car"
REPO_GIT="https://github.com/Abdulhadi446/terminal-car.git"
USER_LEVEL=1
PREFIX=""

while (( $# > 0 )); do
  case "$1" in
    --system|-s) USER_LEVEL=0;;
    --user|-u) USER_LEVEL=1;;
    --prefix) shift; PREFIX="${1:?--prefix needs a directory}";;
    --help|-h)
      cat <<'HELP'
Usage: ./install.sh [--user|--system|--prefix DIR]

  --user     install under ~/.local (default)
  --system   install under /usr/local (needs root or sudo)
  --prefix   custom install prefix

After installing, run:  car
HELP
      exit 0
      ;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
  shift
done

log() { printf 'install: %s\n' "$*"; }
fail() { printf 'install: error: %s\n' "$*" >&2; exit 1; }

PYTHON_BIN="$(command -v python3 || command -v python || true)"
[[ -z "$PYTHON_BIN" ]] && fail "python 3 is not installed."
if ! "$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
  fail "python 3.8 or newer is required."
fi

SCRIPT_DIR=""
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || true
fi

SOURCE_DIR=""
for candidate in "$SCRIPT_DIR" "$PWD"; do
  if [[ -f "$candidate/play.py" && -d "$candidate/terminal_car" ]]; then
    SOURCE_DIR="$candidate"
    break
  fi
done

TMP_CLONE=""
if [[ -z "$SOURCE_DIR" ]]; then
  log "game files not found next to the installer; downloading from git..."
  TMP_CLONE="$(mktemp -d -t terminal-car-install-XXXXXX)"
  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 "$REPO_GIT" "$TMP_CLONE"
    SOURCE_DIR="$TMP_CLONE"
  else
    fail "git is required to download terminal-car (or clone the repository manually)"
  fi
fi

if [[ -n "$PREFIX" ]]; then
  BASE_DIR="$PREFIX"
  BIN_DIR="$PREFIX/bin"
else
  if (( USER_LEVEL == 0 )); then
    BASE_DIR="/usr/local"
    BIN_DIR="/usr/local/bin"
  else
    BASE_DIR="$HOME/.local"
    BIN_DIR="$HOME/.local/bin"
  fi
fi

mkdir -p "$BIN_DIR"
if [[ ! -w "$BIN_DIR" ]]; then
  fail "cannot write to $BIN_DIR (try sudo ./install.sh --system or --user)"
fi

APP_DIR="$BASE_DIR/share/terminal-car"
mkdir -p "$APP_DIR"

log "copying game files to $APP_DIR..."
cp "$SOURCE_DIR/play.py" "$APP_DIR/play.py"
rm -rf "$APP_DIR/terminal_car"
cp -r "$SOURCE_DIR/terminal_car" "$APP_DIR/terminal_car"

# Create the main executable `car`
log "installing launcher: $BIN_DIR/car"
cat > "$BIN_DIR/car" <<LAUNCHER
#!/bin/sh
exec "$PYTHON_BIN" "$APP_DIR/play.py" "\$@"
LAUNCHER
chmod 0755 "$BIN_DIR/car"

# Symlink `terminal-car` and `terminal-rush` as aliases
ln -sf "$BIN_DIR/car" "$BIN_DIR/terminal-car"
ln -sf "$BIN_DIR/car" "$BIN_DIR/terminal-rush"

# Optional desktop entry (Linux / BSD)
if [[ -d "$HOME/.local" ]]; then
  DESK_DIR="$HOME/.local/share/applications"
  mkdir -p "$DESK_DIR"
  cat > "$DESK_DIR/terminal-car.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Terminal Rush
Comment=Endless retro highway survival in your terminal
Exec=$BIN_DIR/car
Terminal=true
Categories=Game;ArcadeGame;
Keywords=game;arcade;racing;terminal;curses;car;
DESKTOP
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESK_DIR" >/dev/null 2>&1 || true
fi

# PATH assistance for user installs
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
      if [[ -f "$rc" ]]; then
        if ! grep -qF "$BIN_DIR" "$rc"; then
          printf '\n# terminal-car\nexport PATH="%s:$PATH"\n' "$BIN_DIR" >> "$rc"
          log "added $BIN_DIR to $rc (restart your shell)"
        fi
      fi
    done
    ;;
esac

if [[ -n "$TMP_CLONE" && -d "$TMP_CLONE" ]]; then
  rm -rf "$TMP_CLONE"
fi

cat <<EOF

🏎️  Terminal Rush is installed!

Run the game from any directory with:
    car

(You can also use 'terminal-car' or 'terminal-rush')

If your shell doesn't find the command yet, either restart your shell or run:
    export PATH="$BIN_DIR:\$PATH"

EOF
