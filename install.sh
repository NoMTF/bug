#!/usr/bin/env bash
# bug — one-line installer
#
#   curl -fsSL https://raw.githubusercontent.com/NoMTF/bug/main/install.sh | bash
#
# What this does:
#   1. Clones the repo to ~/.bug  (or pulls if it already exists)
#   2. Makes the launchers executable
#   3. Adds ~/.bug/bin to PATH via your shell rc file
#   4. Prints a quick-start summary

set -euo pipefail

REPO="https://github.com/NoMTF/bug.git"
INSTALL_DIR="${BUG_INSTALL_DIR:-$HOME/.bug}"
BIN_DIR="$INSTALL_DIR/bin"

# ── colours ────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"
else
  BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

info()    { printf "${GREEN}✔${RESET}  %s\n" "$*"; }
warn()    { printf "${YELLOW}!${RESET}  %s\n" "$*"; }
die()     { printf "${RED}✖${RESET}  %s\n" "$*" >&2; exit 1; }
section() { printf "\n${BOLD}%s${RESET}\n" "$*"; }

# ── requirements ──────────────────────────────────────────────────────────
section "Checking requirements"

PYTHON=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver="$("$candidate" -c 'import sys; print(sys.version_info[:2])'  2>/dev/null || true)"
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' 2>/dev/null; then
      PYTHON="$candidate"
      info "Python found: $candidate ($ver)"
      break
    else
      warn "Skipping $candidate — version $ver < (3, 8)"
    fi
  fi
done

[ -n "$PYTHON" ] || die "Python 3.8+ is required. Install it from https://python.org and re-run."

if command -v git >/dev/null 2>&1; then
  info "git found: $(git --version)"
else
  die "git is required. Install it and re-run."
fi

# ── clone / update ────────────────────────────────────────────────────────
section "Installing to $INSTALL_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
  info "Existing install found — pulling latest changes"
  git -C "$INSTALL_DIR" pull --ff-only
else
  info "Cloning $REPO"
  git clone --depth=1 "$REPO" "$INSTALL_DIR"
fi

chmod +x "$BIN_DIR/bug.sh" "$BIN_DIR/bug.js" 2>/dev/null || true
info "Launchers marked executable"

# ── PATH wiring ───────────────────────────────────────────────────────────
section "Wiring up PATH"

wire_path() {
  local rc="$1"
  local line='export PATH="$HOME/.bug/bin:$PATH"'
  if [ -f "$rc" ] && grep -qF '.bug/bin' "$rc" 2>/dev/null; then
    info "$rc already contains .bug/bin — skipping"
  else
    printf '\n# bug installer\n%s\n' "$line" >> "$rc"
    info "Added .bug/bin to PATH in $rc"
  fi
}

# create a wrapper called `bug` that calls bug.sh
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/bug" <<'WRAPPER'
#!/usr/bin/env bash
exec "$(dirname "$(realpath "$0" 2>/dev/null || readlink -f "$0" 2>/dev/null || echo "$0")")/bug.sh" "$@"
WRAPPER
chmod +x "$BIN_DIR/bug"
info "Created $BIN_DIR/bug wrapper"

WIRED=0
for rc in "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc" "$HOME/.profile"; do
  if [ -f "$rc" ]; then
    wire_path "$rc"
    WIRED=1
  fi
done
if [ "$WIRED" -eq 0 ]; then
  wire_path "$HOME/.profile"
fi

# ── verify ────────────────────────────────────────────────────────────────
section "Verifying"
export PATH="$BIN_DIR:$PATH"
if bug languages >/dev/null 2>&1; then
  info "bug is working"
else
  warn "Could not run 'bug languages' — try opening a new terminal"
fi

# ── done ──────────────────────────────────────────────────────────────────
printf "\n${BOLD}${GREEN}Installation complete!${RESET}\n\n"
cat <<SUMMARY
  Installed to : $INSTALL_DIR
  Command      : bug

  Restart your terminal (or run: export PATH="\$HOME/.bug/bin:\$PATH")

  Quick start:
    bug bug-version ./my-project --profile messy --count 12
    bug inject      ./examples/multilang-sandbox --bug off-by-one
    bug languages

  Update anytime:
    curl -fsSL https://raw.githubusercontent.com/NoMTF/bug/main/install.sh | bash

SUMMARY
