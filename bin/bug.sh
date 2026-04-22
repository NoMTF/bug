#!/usr/bin/env bash
# bug — POSIX shell entry point for the bug-version generator.
#
# Forwards sub-commands to the Python scripts. Useful as a single, portable
# CLI on Linux, macOS, WSL, and Git-Bash (Windows) without needing Node.js.
#
# Usage:
#   bug bug-version <source> [flags]
#   bug inject      <sandbox> [flags]
#   bug languages
#   bug help

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
if command -v readlink >/dev/null 2>&1; then
  RESOLVED="$(readlink -f "$SCRIPT_PATH" 2>/dev/null || true)"
  [ -n "$RESOLVED" ] && SCRIPT_PATH="$RESOLVED"
fi
BIN_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd)"
ROOT="$(cd -- "$BIN_DIR/.." && pwd)"
SCRIPTS="$ROOT/scripts"

print_usage() {
  cat <<'USAGE'
Usage: bug <command> [options]

Commands:
  bug-version <source> [flags]   Create <source>-bug-version and -clean-backup
  inject      <sandbox> [flags]  Mutate a sandbox directory in place
  languages                      Print supported file extensions
  help                           Show this message

Flags are forwarded to the underlying Python script. Use --help for more.

Examples:
  bug bug-version ./my-app --profile messy --count 12
  bug inject ./examples/js-kata --bug off-by-one
USAGE
}

print_languages() {
  cat <<'LANGS'
Supported source file extensions:
  .py
  .js .jsx .ts .tsx .mjs .cjs
  .go
  .rs
  .java
  .kt .kts
  .swift
  .cs
  .c .cc .cpp .cxx .h .hpp .hxx
  .rb
  .php
LANGS
}

resolve_python() {
  if [ -n "${BUG_PYTHON:-}" ]; then
    echo "$BUG_PYTHON"
    return 0
  fi
  for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if [ "$#" -eq 0 ]; then
  print_usage
  exit 0
fi

case "$1" in
  help|-h|--help)
    print_usage
    exit 0
    ;;
  languages|--languages)
    print_languages
    exit 0
    ;;
  bug-version|make)
    SCRIPT="$SCRIPTS/make_bug_version.py"
    ;;
  inject|sandbox)
    SCRIPT="$SCRIPTS/inject_bug.py"
    ;;
  *)
    printf 'error: unknown command "%s"\n\n' "$1" >&2
    print_usage
    exit 2
    ;;
esac

shift

if ! PYTHON="$(resolve_python)"; then
  echo "error: no Python interpreter found. Install Python 3.8+ or set BUG_PYTHON." >&2
  exit 1
fi

if [ ! -f "$SCRIPT" ]; then
  echo "error: missing script $SCRIPT" >&2
  exit 1
fi

exec "$PYTHON" "$SCRIPT" "$@"
