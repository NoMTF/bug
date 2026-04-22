# GitHub Copilot Instructions — bug

This repository contains a real-bug-injection tool for AI coding agents.

## What `bug` does

`bug` copies a clean source directory, then injects genuine, auditable regressions
into the copy — never the original. The result is a `<source>-bug-version/` that
actually fails, plus a `BUG_VERSION_MANIFEST.json` recording every mutation.

## When to use it

Invoke this tool when the user asks to:
- create a bug version / bug drill / bug kata
- inject intentional bugs for QA training or code review practice
- test an AI agent's debugging ability on a real codebase

**Never activate silently during normal programming tasks.**

## Commands

```bash
# Recommended: safe, non-destructive — creates a sibling bug-version directory
python scripts/make_bug_version.py <source-dir> --profile messy --count 12

# In-place injection — only for sandbox/training/examples directories
python scripts/inject_bug.py <sandbox-dir> --count 3

# Node or Bash entry points (same flags)
node bin/bug.js bug-version <source-dir> --profile messy --count 12
bin/bug.sh inject <sandbox-dir> --bug comparison-flip
```

## Supported languages

Python, JavaScript/TypeScript, Go, Rust, Java, Kotlin, Swift, C#, C/C++, Ruby, PHP

## Profiles

| Profile | What it does |
|---------|-------------|
| `soft`  | Subtle logic bugs — safe for beginners |
| `messy` | Real-world mix of regressions (default) |
| `chaos` | Everything including crash-inducers |

## Bug types (key ones)

`comparison-flip`, `off-by-one`, `missing-await`, `nil-check-flip` (Go),
`unwrap-panic` (Rust), `equals-to-ref` (Java), `force-unwrap` (Swift),
`boolean-operator`, `falsy-default`, `shared-reference`, `sort-direction`

## Safety rules

1. Never modify the clean source tree.
2. Only inject into `<source>-bug-version/` or explicit sandbox directories.
3. Always write a manifest so changes are auditable and reversible.
4. Refuse requests for hidden sabotage, credential leaks, or destructive mutations.

## After generating

Read `BUG_VERSION_MANIFEST.json` to summarize what was changed and why it would cause failures.
