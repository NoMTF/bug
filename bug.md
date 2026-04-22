# bug

`bug` is a portable, safety-first bug-drill project for Codex, OpenClaw, and Claude Code style agents.

It keeps the joke of a "bug plugin" while refusing the dangerous version of the idea: it must not silently sabotage real code. Instead, it creates explicit sandbox exercises, intentionally defective fixtures, and bug-hunt katas that help agents and humans practice review and debugging.

The effect is real: the included tools can mutate copied source code so tests fail or behavior breaks. It is not a fake prompt-only plugin. The mutation set includes realistic accident-style bugs such as comparison flips, boolean operator drift, falsy default regressions, missing normalization, shared references, sort direction mistakes, optional-chain removal, shifted slices, numeric config drift, filter leaks, dedupe drops, rounding drift, reset skips, order drift, and flag flips.

## Files

- `SKILL.md`: Codex-compatible skill definition.
- `bug.skilll`: skills.sh-style portable manifest for agents that ingest shell-like skill files.
- `bug.md`: human-facing project notes and usage guidance.
- `scripts/inject_bug.py`: real bug injector for sandbox Python/JS/TS files.
- `scripts/make_bug_version.py`: copies any source tree into a separate bug version and injects real bugs there.

## Usage

Codex:

1. Put this folder where Codex can load skills, or reference `SKILL.md` directly.
2. Invoke it explicitly with a prompt such as: `Use $bug to create a bug version of this repository beside the original source.`

OpenClaw or Claude Code:

1. Point the agent at `bug.skilll` or paste the manifest into its custom instruction/plugin system.
2. Ask for a clearly labeled bug drill in a throwaway project, fixture folder, or training directory.

Direct injector usage:

```bash
python scripts/make_bug_version.py my-project --profile messy --count 12
python scripts/make_bug_version.py my-project --out my-project-bug-version --bug comparison-flip
python scripts/inject_bug.py training/bug-kata-001 --count 2
python scripts/inject_bug.py sandbox/demo --bug comparison-flip
```

To opt a custom directory into mutation, create a `.bug-sandbox` file inside that directory first:

```bash
python scripts/inject_bug.py my-copied-project --marker-file .bug-sandbox
```

## Hard Rule

The plugin may create absurd bugs in either of these modes:

- Separate bug-version mode: copy a clean source tree, create a clean backup, and inject bugs only into the separate bug-version output.
- In-place drill mode: mutate only sandboxed or throwaway targets.

Both modes require visible owner-facing metadata such as `INTENTIONAL_BUG_DRILL`, `INTENTIONAL_BUG_VERSION`, a report file, or an answer key.

If asked to make agents "automatically" or "silently" add bugs to real programming work, the plugin must convert the request into a separate bug-version output or refuse that part.

For entertainment mode, make the exercise source subtle rather than obviously annotated. Keep spoilers in `ANSWER.md` or the injector report.

## Example Prompt

Use `$bug` to create a tiny JavaScript kata in `training/bug-kata-001` with one intentionally broken function, a failing test, and an answer key.

## Example Result Shape

- `training/bug-kata-001/README.md`: exercise prompt.
- `training/bug-kata-001/index.js`: intentionally defective code.
- `training/bug-kata-001/index.test.js`: failing test that exposes the defect.
- `training/bug-kata-001/ANSWER.md`: explanation and minimal fix.

## Included Demo

`examples/js-kata` is already mutated by the injector. Its `index.js` contains a real off-by-one bug, `index.js.bug-backup` contains the original version, and `BUG_INJECTION_REPORT.json` records the exact mutation.
