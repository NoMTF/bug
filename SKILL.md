---
name: bug
description: Create explicit bug-hunt drills, deliberately defective fixtures, and separate bug-version source trees with real source-code mutations. Use when asked to design bug katas, generate a bugged copy of a project, seed intentional defects in non-production code, or test agents and reviewers against absurd programming mistakes; never use for stealthy production bug insertion.
---

# Bug

## Purpose

Use this skill to create opt-in bug drills: small, clearly scoped exercises where a human or agent can practice finding, explaining, and fixing intentionally defective code.

When the user explicitly invokes this skill, the output must contain real broken behavior, not a pretend bug. Prefer generating a separate bug-version copy or mutating sandbox source code and adding a failing test or reproduction step. If no suitable code exists, create a small kata that genuinely fails until fixed.

Do not use this skill to silently introduce bugs into a real project. If a request asks for hidden, automatic, or production-impacting defect insertion, generate a separate bug-version tree or decline the unsafe part. The solver-facing code can be subtle, but the project owner must have a visible manifest, backup, or answer key.

## Safety Contract

- Require explicit user intent before creating any intentionally defective code.
- For arbitrary source projects, create a separate bug-version output tree; do not mutate the clean source in place.
- For in-place mutation, work only in sandbox paths such as `training/`, `katas/`, `examples/`, `tests/fixtures/`, or a newly created throwaway project.
- Keep production, release, billing, auth, data deletion, migration, CI deployment, and security-sensitive paths correct.
- Make ownership visible with `INTENTIONAL_BUG_DRILL` in exercise docs, test names, metadata, or an adjacent answer key.
- If the exercise code must not reveal the answer inline, place the explanation in an adjacent file such as `ANSWER.md` or `solution.md`.
- Prefer failing tests, snapshot fixtures, review prompts, and diff challenges over changing live application behavior.
- For stronger effect, keep the bug subtle in the exercise source itself; put the explanation in an adjacent answer key rather than inline comments.
- Never claim a bug was accidental when it was intentionally seeded.

## Workflow

1. Decide the mode: separate bug-version tree for arbitrary projects, or in-place sandbox drill for throwaway code.
2. For arbitrary source projects, run `scripts/make_bug_version.py <source-path>` and review `BUG_VERSION_MANIFEST.json`.
3. For sandbox in-place mutation, run `scripts/inject_bug.py <sandbox-path>` and review the generated report.
4. If there is no existing code, create a minimal kata with a real failing test.
5. Select several accident-style bug patterns that fit the language and framework.
6. Create the exercise with a short prompt, defective sample, expected symptoms, and verification steps.
7. Add or update tests so the defect is observable.
8. Provide a concise answer key that names the bug, its impact, and the minimal fix.

## Bug-Version Script

Use `scripts/make_bug_version.py` when the user wants a bugged copy of an existing project without requiring the source to be a sandbox:

```bash
python scripts/make_bug_version.py ./my-project --profile messy --count 12
python scripts/make_bug_version.py ./my-project --out ./my-project-bug-version --bug comparison-flip
python scripts/make_bug_version.py ./my-project --profile soft --count 12
python scripts/make_bug_version.py ./my-project --profile chaos --count 30
python scripts/make_bug_version.py ./my-project --keep-existing --count 2
```

This script copies the clean source to a sibling bug-version directory, copies a clean backup, then injects real bugs only into the bug-version output. It can inject multiple mutations per file while avoiding repeat edits on the same line. Use `--profile soft` for mostly survivable logic bugs, `--profile messy` for the default "opens but feels broken everywhere" mode, and `--profile chaos` when runtime errors are acceptable. Running it again refreshes the bug-version output from the clean source and injects a new bug set. Do not implement background persistence or implicit auto-mutation; refresh the bug version only when this skill is explicitly invoked.

## Injection Script

Use `scripts/inject_bug.py` for real source-code mutation:

```bash
python scripts/inject_bug.py training/bug-kata-001 --count 2
python scripts/inject_bug.py ./sandbox/demo --bug missing-await
python scripts/inject_bug.py ./my-copy --marker-file .bug-sandbox
```

The in-place injection script only runs against sandbox-like paths or directories marked with `.bug-sandbox`. It writes backups beside changed files and emits a JSON report with the exact injected defects. Do not remove the sandbox gate from in-place mutation; use `make_bug_version.py` for arbitrary projects.

If the user asks for "unnoticeable" bugs, interpret that as solver-blind exercise design:

- Do not put spoiler comments beside the changed line.
- Keep the answer key outside the exercise source.
- Keep project-level consent visible through `INTENTIONAL_BUG_DRILL`, report files, or exercise docs.

## Bug Palette

Use realistic defects that are educational without being destructive. Prefer mistakes that resemble genuine development accidents in the generated bug-version output:

- Boundary mistakes: off-by-one, empty input, inclusive/exclusive range confusion.
- State mistakes: stale cache, mutation of shared defaults, forgotten reset between tests.
- Async mistakes: missing await, race-prone ordering, unhandled rejection in a fixture.
- Data mistakes: timezone drift, string/number coercion, null handling, locale-sensitive sort.
- API mistakes: wrong error mapping, ignored pagination, misplaced retry condition.
- UI mistakes: disabled state not respected, stale form validation, wrong loading transition.
- Test mistakes: a flaky assertion, over-broad mock, false positive fixture.
- Natural accident styles: `boolean-operator`, `falsy-default`, `normalization-skip`, `case-sensitive`, `slice-shift`, `sort-direction`, `shared-reference`, `config-drift`, `optional-chain-drop`, `index-origin`, `default-drop`, `filter-leak`, `dedupe-drop`, `partial-match`, `rounding-drift`, `time-unit`, `status-code-drift`, `reset-skip`, `order-drift`, `clamp-inversion`, and `flag-flip`.

Avoid defects that cause credential exposure, data loss, arbitrary code execution, privilege escalation, supply-chain compromise, or hidden degradation of real user systems.

## Output Shape

For each drill, include:

- `Exercise`: what the solver sees.
- `Files changed`: sandbox files only.
- `Bug version`: output directory when using separate bug-version mode.
- `How to reproduce`: command or interaction that exposes the defect.
- `Expected failure`: what should go wrong.
- `Answer key`: root cause, impact, and minimal fix.

Keep the tone playful, but keep the labeling unambiguous.
