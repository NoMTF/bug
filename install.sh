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

# ── IDE integrations ──────────────────────────────────────────────────────
section "IDE integrations"

# Continue.dev — patch global config with /bug-version and /bug-inject commands
CONTINUE_CFG="$HOME/.continue/config.json"
if [ -f "$CONTINUE_CFG" ]; then
  if grep -q '"bug-version"' "$CONTINUE_CFG" 2>/dev/null; then
    info "Continue.dev: bug commands already present — skipping"
  elif command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
    PY="${PYTHON:-python3}"
    "$PY" - "$CONTINUE_CFG" "$INSTALL_DIR" <<'PYEOF'
import json, sys
cfg_path, install_dir = sys.argv[1], sys.argv[2]
with open(cfg_path, encoding="utf-8") as f:
    cfg = json.load(f)

new_cmds = [
    {
        "name": "bug-version",
        "description": "Copy current project and inject real bugs for a drill",
        "prompt": (
            f"Run in the terminal:\n\npython {install_dir}/scripts/make_bug_version.py "
            ". --profile messy --count 12\n\n"
            "Then read BUG_VERSION_MANIFEST.json and summarise every injected bug."
        ),
    },
    {
        "name": "bug-inject",
        "description": "Inject bugs into a sandbox directory in-place",
        "prompt": (
            f"Run in the terminal:\n\npython {install_dir}/scripts/inject_bug.py "
            "{input} --profile messy --count 3\n\n"
            "Then read BUG_INJECTION_REPORT.json and describe every mutation."
        ),
    },
]

existing = cfg.setdefault("customCommands", [])
names = {c.get("name") for c in existing}
for cmd in new_cmds:
    if cmd["name"] not in names:
        existing.append(cmd)

with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("patched")
PYEOF
    info "Continue.dev: added /bug-version and /bug-inject to $CONTINUE_CFG"
  else
    warn "Continue.dev: Python not found, skipping config patch"
  fi
else
  warn "Continue.dev: $CONTINUE_CFG not found — open Continue.dev once to create it, then re-run the installer"
fi

# Cursor — copy rule to user-level rules directory (macOS/Linux standard path)
CURSOR_RULES_DIR="$HOME/.cursor/rules"
if [ -d "$HOME/.cursor" ] || [ -d "$HOME/Library/Application Support/Cursor" ]; then
  mkdir -p "$CURSOR_RULES_DIR"
  cp "$INSTALL_DIR/.cursor/rules/bug.mdc" "$CURSOR_RULES_DIR/bug.mdc"
  info "Cursor: rule written to $CURSOR_RULES_DIR/bug.mdc"
else
  warn "Cursor: not detected — copy .cursor/rules/bug.mdc from $INSTALL_DIR manually"
fi

# GitHub Copilot — remind user
info "Copilot: copy .github/copilot-instructions.md from $INSTALL_DIR to your project root"

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

  IDE setup:
    Copilot  → copy $INSTALL_DIR/.github/copilot-instructions.md to your project's .github/
    Continue → /bug-version and /bug-inject slash commands added to ~/.continue/config.json
    Cursor   → rule written to ~/.cursor/rules/bug.mdc (alwaysApply: false)

SUMMARY
