#!/usr/bin/env python3
"""Inject real, reversible bugs into sandbox code for bug-hunt drills.

This is not a stealth sabotage tool. It refuses non-sandbox targets, creates
backups, and writes a report so the project owner can see what was changed.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_PATH_MARKERS = {
    "bug-kata",
    "bug_kata",
    "demo",
    "example",
    "examples",
    "fixture",
    "fixtures",
    "kata",
    "katas",
    "playground",
    "sandbox",
    "scratch",
    "temp",
    "tmp",
    "training",
}

DEFAULT_MARKER_FILE = ".bug-sandbox"

JS_LIKE = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
PY_LIKE = {".py"}
GO_LIKE = {".go"}
RUST_LIKE = {".rs"}
JAVA_LIKE = {".java"}
KOTLIN_LIKE = {".kt", ".kts"}
SWIFT_LIKE = {".swift"}
CSHARP_LIKE = {".cs"}
C_LIKE = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"}
RUBY_LIKE = {".rb"}
PHP_LIKE = {".php"}

CSTYLE_LIKE = (
    JS_LIKE | GO_LIKE | RUST_LIKE | JAVA_LIKE | KOTLIN_LIKE
    | SWIFT_LIKE | CSHARP_LIKE | C_LIKE | PHP_LIKE
)
BRACE_LIKE = CSTYLE_LIKE
SCRIPT_LIKE = PY_LIKE | RUBY_LIKE

SUPPORTED_SUFFIXES = (
    JS_LIKE | PY_LIKE | GO_LIKE | RUST_LIKE | JAVA_LIKE | KOTLIN_LIKE
    | SWIFT_LIKE | CSHARP_LIKE | C_LIKE | RUBY_LIKE | PHP_LIKE
)

SKIP_DIRS = {
    ".git",
    ".gradle",
    ".hg",
    ".idea",
    ".svn",
    ".venv",
    "__pycache__",
    "bin",
    "build",
    "cmake-build-debug",
    "cmake-build-release",
    "coverage",
    "dist",
    "node_modules",
    "obj",
    "out",
    "Pods",
    "target",
    "vendor",
}


@dataclass(frozen=True)
class Mutation:
    name: str
    line: int
    before: str
    after: str
    explanation: str


def is_sandbox_path(path: Path, marker_file: str) -> bool:
    resolved = path.resolve()
    lowered_parts = {part.lower() for part in resolved.parts}
    if lowered_parts & ALLOWED_PATH_MARKERS:
        return True
    return (resolved / marker_file).exists()


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name.endswith(".bug-backup"):
            continue
        files.append(path)
    return sorted(files)


def is_ignored_line(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith(("#", "//", "*", "--"))


def has_word(line: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", line) is not None


def mutate_comparison_flip(lines: list[str], suffix: str) -> Mutation | None:
    base_ops = [("<=", "<"), (">=", ">"), ("==", "!="), ("!=", "==")]
    if suffix in JS_LIKE or suffix in PHP_LIKE:
        ops = [("<=", "<"), (">=", ">"), ("===", "!=="), ("!==", "==="), ("==", "!="), ("!=", "==")]
    elif suffix in (PY_LIKE | GO_LIKE | RUST_LIKE | JAVA_LIKE | KOTLIN_LIKE
                    | SWIFT_LIKE | CSHARP_LIKE | C_LIKE | RUBY_LIKE):
        ops = base_ops
    else:
        ops = []
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for old, new in ops:
            if old in line:
                changed = line.replace(old, new, 1)
                return Mutation(
                    name="comparison-flip",
                    line=idx + 1,
                    before=line.rstrip("\n"),
                    after=changed.rstrip("\n"),
                    explanation=f"Changed `{old}` to `{new}`, altering boundary or equality behavior.",
                )
    return None


def mutate_missing_await(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in (JS_LIKE | PY_LIKE | CSHARP_LIKE | RUST_LIKE | SWIFT_LIKE | KOTLIN_LIKE):
        return None
    pattern = re.compile(r"\bawait\s+")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if pattern.search(line):
            changed = pattern.sub("", line, count=1)
            return Mutation(
                name="missing-await",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Removed one `await`, creating async ordering or promise/coroutine handling bugs.",
            )
    return None


def mutate_js_off_by_one(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in (JS_LIKE | JAVA_LIKE | CSHARP_LIKE | KOTLIN_LIKE | SWIFT_LIKE | C_LIKE | PHP_LIKE):
        return None
    # Matches `< something.length` / `< something.size()` / `< something.count` / `< len(x)`
    if suffix in C_LIKE:
        pattern = re.compile(r"(<)\s*([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*\.(?:length|size|count)\(?\)?)")
    else:
        pattern = re.compile(r"(<)\s*([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\.(?:length|size|count|Count|Length|size\(\)))")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if pattern.search(line):
            changed = pattern.sub(r"<= \2", line, count=1)
            return Mutation(
                name="off-by-one",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Changed a length bound from `<` to `<=`, allowing one extra iteration.",
            )
    return None


def mutate_go_off_by_one(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in GO_LIKE:
        return None
    pattern = re.compile(r"(<)\s*(len\([^)\n]+\))")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if pattern.search(line):
            changed = pattern.sub(r"<= \2", line, count=1)
            return Mutation(
                name="off-by-one",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Changed a Go `< len(...)` bound to `<=`, running one iteration past the slice end.",
            )
    return None


def mutate_rust_off_by_one(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in RUST_LIKE:
        return None
    pattern = re.compile(r"\.\.([A-Za-z_][\w]*\.len\(\))")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if pattern.search(line):
            changed = pattern.sub(r"..=\1", line, count=1)
            return Mutation(
                name="off-by-one",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Changed exclusive `..len()` into inclusive `..=len()`, reading past the vector end.",
            )
    return None


def mutate_py_range_shrink(lines: list[str], suffix: str) -> Mutation | None:
    if suffix != ".py":
        return None
    pattern = re.compile(r"range\((len\([^)]+\)|[A-Za-z_][\w.]*)\)")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        value = match.group(1)
        changed = pattern.sub(f"range({value} - 1)", line, count=1)
        return Mutation(
            name="off-by-one",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Reduced a loop range by one, skipping the final item.",
        )
    return None


def mutate_truthy_empty(lines: list[str], suffix: str) -> Mutation | None:
    if suffix != ".py":
        return None
    pattern = re.compile(r"if\s+not\s+([A-Za-z_][\w.]*)\s*:")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        value = match.group(1)
        changed = pattern.sub(f"if {value}:", line, count=1)
        return Mutation(
            name="truthy-empty",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Inverted an empty/null guard so valid and empty inputs take the wrong branch.",
        )
    return None


def mutate_boolean_operator(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in BRACE_LIKE:
        candidates = [("&&", "||"), ("||", "&&")]
    elif suffix in PY_LIKE or suffix in RUBY_LIKE:
        candidates = [(" and ", " or "), (" or ", " and ")]
    else:
        return None

    gate_prefixes = ("if ", "elif ", "elsif ", "return ", "while ", "unless ")
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if is_ignored_line(line):
            continue
        if not (stripped.startswith(gate_prefixes) or "?" in line):
            continue
        for old, new in candidates:
            if old in line:
                changed = line.replace(old, new, 1)
                return Mutation(
                    name="boolean-operator",
                    line=idx + 1,
                    before=line.rstrip("\n"),
                    after=changed.rstrip("\n"),
                    explanation=f"Changed `{old.strip()}` to `{new.strip()}`, making compound logic pass or fail for the wrong cases.",
                )
    return None


def mutate_nullish_to_or(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in (JS_LIKE | CSHARP_LIKE | KOTLIN_LIKE):
        return None
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if "??" not in line:
            continue
        changed = line.replace("??", "||", 1)
        return Mutation(
            name="falsy-default",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Changed nullish fallback to truthy fallback, so valid falsy values like 0, empty string, or false are overwritten.",
        )
    return None


def mutate_trim_removal(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        targets = [".trim()"]
    elif suffix in PY_LIKE:
        targets = [".strip()"]
    elif suffix in RUBY_LIKE:
        targets = [".strip"]
    elif suffix in GO_LIKE:
        # strings.TrimSpace(x) -> x
        for idx, line in enumerate(lines):
            if is_ignored_line(line):
                continue
            m = re.search(r"strings\.TrimSpace\(([^()\n]+)\)", line)
            if not m:
                continue
            changed = line.replace(m.group(0), m.group(1), 1)
            return Mutation(
                name="normalization-skip",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Removed Go `strings.TrimSpace`, so padded input starts mismatching comparisons.",
            )
        return None
    elif suffix in PHP_LIKE:
        for idx, line in enumerate(lines):
            if is_ignored_line(line):
                continue
            m = re.search(r"\btrim\(([^()\n]+)\)", line)
            if not m:
                continue
            changed = line.replace(m.group(0), m.group(1), 1)
            return Mutation(
                name="normalization-skip",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Removed PHP `trim()`, leaving leading/trailing whitespace in user input.",
            )
        return None
    elif suffix in RUST_LIKE:
        targets = [".trim()"]
    elif suffix in (JAVA_LIKE | KOTLIN_LIKE):
        targets = [".trim()", ".strip()"]
    elif suffix in CSHARP_LIKE:
        targets = [".Trim()"]
    elif suffix in SWIFT_LIKE:
        targets = [".trimmingCharacters(in: .whitespaces)", ".trimmingCharacters(in: .whitespacesAndNewlines)"]
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for target in targets:
            if target in line:
                changed = line.replace(target, "", 1)
                return Mutation(
                    name="normalization-skip",
                    line=idx + 1,
                    before=line.rstrip("\n"),
                    after=changed.rstrip("\n"),
                    explanation="Removed whitespace normalization, making values with leading or trailing spaces behave differently.",
                )
    return None


def mutate_case_normalization_removal(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        targets = [".toLowerCase()", ".toUpperCase()"]
    elif suffix in PY_LIKE:
        targets = [".lower()", ".upper()", ".casefold()"]
    elif suffix in RUBY_LIKE:
        targets = [".downcase", ".upcase"]
    elif suffix in RUST_LIKE:
        targets = [".to_lowercase()", ".to_uppercase()", ".to_ascii_lowercase()", ".to_ascii_uppercase()"]
    elif suffix in (JAVA_LIKE | SWIFT_LIKE):
        targets = [".toLowerCase()", ".toUpperCase()", ".lowercased()", ".uppercased()"]
    elif suffix in KOTLIN_LIKE:
        targets = [".lowercase()", ".uppercase()", ".toLowerCase()", ".toUpperCase()"]
    elif suffix in CSHARP_LIKE:
        targets = [".ToLower()", ".ToUpper()", ".ToLowerInvariant()", ".ToUpperInvariant()"]
    elif suffix in GO_LIKE:
        for idx, line in enumerate(lines):
            if is_ignored_line(line):
                continue
            m = re.search(r"strings\.(?:ToLower|ToUpper)\(([^()\n]+)\)", line)
            if not m:
                continue
            changed = line.replace(m.group(0), m.group(1), 1)
            return Mutation(
                name="case-sensitive",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Removed Go `strings.ToLower/ToUpper`, making previously case-insensitive logic case-sensitive.",
            )
        return None
    elif suffix in PHP_LIKE:
        for idx, line in enumerate(lines):
            if is_ignored_line(line):
                continue
            m = re.search(r"\b(?:strtolower|strtoupper|mb_strtolower|mb_strtoupper)\(([^()\n]+)\)", line)
            if not m:
                continue
            changed = line.replace(m.group(0), m.group(1), 1)
            return Mutation(
                name="case-sensitive",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Removed PHP case-folding call, turning formerly case-insensitive logic into case-sensitive.",
            )
        return None
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for target in targets:
            if target in line:
                changed = line.replace(target, "", 1)
                return Mutation(
                    name="case-sensitive",
                    line=idx + 1,
                    before=line.rstrip("\n"),
                    after=changed.rstrip("\n"),
                    explanation="Removed case normalization, turning formerly case-insensitive logic into case-sensitive logic.",
                )
    return None


def mutate_slice_shift(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        pattern = re.compile(r"\.slice\(\s*0\s*,")
        replacement = ".slice(1,"
    elif suffix in PY_LIKE:
        pattern = re.compile(r"\[\s*0\s*:")
        replacement = "[1:"
    elif suffix in RUST_LIKE:
        pattern = re.compile(r"\[\s*0\s*\.\.")
        replacement = "[1.."
    elif suffix in GO_LIKE:
        pattern = re.compile(r"\[\s*0\s*:")
        replacement = "[1:"
    elif suffix in RUBY_LIKE:
        pattern = re.compile(r"\[\s*0\s*,")
        replacement = "[1,"
    elif suffix in PHP_LIKE:
        pattern = re.compile(r"array_slice\(([^,]+),\s*0\s*,")
        replacement = r"array_slice(\1, 1,"
    elif suffix in JAVA_LIKE:
        pattern = re.compile(r"\.substring\(\s*0\s*,")
        replacement = ".substring(1,"
    elif suffix in CSHARP_LIKE:
        pattern = re.compile(r"\.Substring\(\s*0\s*,")
        replacement = ".Substring(1,"
    elif suffix in SWIFT_LIKE:
        pattern = re.compile(r"\.prefix\(")
        replacement = ".dropFirst().prefix("
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if not pattern.search(line):
            continue
        changed = pattern.sub(replacement, line, count=1)
        return Mutation(
            name="slice-shift",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Shifted a slice start from 0 to 1, silently dropping the first item.",
        )
    return None


def mutate_sort_direction(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        patterns = [
            (re.compile(r"(\.sort\(\s*\(\s*)(\w+)(\s*,\s*)(\w+)(\s*\)\s*=>\s*)\2\s*-\s*\4"), r"\1\2\3\4\5\4 - \2"),
            (re.compile(r"(\.sort\(\s*\(\s*)(\w+)(\s*,\s*)(\w+)(\s*\)\s*=>\s*)\2\.localeCompare\(\4\)"), r"\1\2\3\4\5\4.localeCompare(\2)"),
        ]
    elif suffix in PY_LIKE:
        patterns = [
            (re.compile(r"reverse\s*=\s*False"), "reverse=True"),
            (re.compile(r"reverse\s*=\s*True"), "reverse=False"),
        ]
    elif suffix in RUST_LIKE:
        patterns = [
            (re.compile(r"(\.sort_by\(\s*\|(\w+),\s*(\w+)\|\s*)\2\.cmp\(&?\3\)"), r"\1\3.cmp(&\2)"),
        ]
    elif suffix in GO_LIKE:
        patterns = [
            (re.compile(r"(\[\s*[ij]\s*\]\s*)<(\s*\w+\s*\[\s*[ij]\s*\])"), r"\1>\2"),
        ]
    elif suffix in JAVA_LIKE or suffix in CSHARP_LIKE or suffix in KOTLIN_LIKE:
        patterns = [
            (re.compile(r"Comparator\.reverseOrder\(\)"), "Comparator.naturalOrder()"),
            (re.compile(r"Comparator\.naturalOrder\(\)"), "Comparator.reverseOrder()"),
        ]
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for pattern, replacement in patterns:
            if not pattern.search(line):
                continue
            changed = pattern.sub(replacement, line, count=1)
            return Mutation(
                name="sort-direction",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Reversed a sort direction, producing plausible but incorrectly ordered results.",
            )
    return None


def mutate_copy_alias(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        patterns = [
            (re.compile(r"\[\s*\.\.\.([A-Za-z_$][\w$]*)\s*\]"), r"\1"),
            (re.compile(r"Object\.assign\(\s*\{\s*\}\s*,\s*([A-Za-z_$][\w$]*)\s*\)"), r"\1"),
            (re.compile(r"structuredClone\(\s*([A-Za-z_$][\w$]*)\s*\)"), r"\1"),
        ]
    elif suffix in PY_LIKE:
        patterns = [
            (re.compile(r"([A-Za-z_][\w.]*)\.copy\(\)"), r"\1"),
            (re.compile(r"list\(([A-Za-z_][\w.]*)\)"), r"\1"),
            (re.compile(r"dict\(([A-Za-z_][\w.]*)\)"), r"\1"),
            (re.compile(r"copy\.deepcopy\(([^()\n]+)\)"), r"\1"),
        ]
    elif suffix in RUST_LIKE:
        patterns = [
            (re.compile(r"([A-Za-z_][\w]*)\.clone\(\)"), r"\1"),
            (re.compile(r"([A-Za-z_][\w]*)\.to_owned\(\)"), r"\1"),
            (re.compile(r"([A-Za-z_][\w]*)\.to_vec\(\)"), r"\1"),
        ]
    elif suffix in JAVA_LIKE or suffix in KOTLIN_LIKE:
        patterns = [
            (re.compile(r"new ArrayList<>\(\s*([A-Za-z_][\w]*)\s*\)"), r"\1"),
            (re.compile(r"new HashMap<>\(\s*([A-Za-z_][\w]*)\s*\)"), r"\1"),
            (re.compile(r"([A-Za-z_][\w]*)\.toMutableList\(\)"), r"\1"),
        ]
    elif suffix in GO_LIKE:
        patterns = [
            (re.compile(r"append\(\s*\[\][A-Za-z_][\w]*\{\}\s*,\s*([A-Za-z_][\w]*)\.\.\.\s*\)"), r"\1"),
        ]
    elif suffix in RUBY_LIKE:
        patterns = [
            (re.compile(r"([A-Za-z_][\w]*)\.dup\b"), r"\1"),
            (re.compile(r"([A-Za-z_][\w]*)\.clone\b"), r"\1"),
        ]
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for pattern, replacement in patterns:
            if not pattern.search(line):
                continue
            changed = pattern.sub(replacement, line, count=1)
            return Mutation(
                name="shared-reference",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Removed a defensive copy, so later mutation can leak through shared references.",
            )
    return None


def mutate_numeric_knob(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in SUPPORTED_SUFFIXES:
        return None
    knob = r"(timeout|delay|limit|max|retries|retry|pageSize|page_size|batchSize|batch_size)"
    pattern = re.compile(rf"(\b{knob}\b\s*(?::\s*\w+\s*)?=\s*)(\d+)", re.IGNORECASE)
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        value = int(match.group(3))
        if value <= 1:
            continue
        if has_word(match.group(2).lower(), "retry") or has_word(match.group(2).lower(), "retries"):
            new_value = max(0, value - 1)
        else:
            new_value = max(1, value // 2)
        changed = line[: match.start(3)] + str(new_value) + line[match.end(3) :]
        return Mutation(
            name="config-drift",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Tweaked a numeric configuration knob, creating plausible timeout, limit, pagination, or retry regressions.",
        )
    return None


def mutate_js_property_typo(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in JS_LIKE:
        return None
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if ".length" not in line:
            continue
        changed = line.replace(".length", ".lenght", 1)
        return Mutation(
            name="property-typo",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Misspelled a common property name, causing a realistic undefined-value regression.",
        )
    return None


def mutate_py_enumerate_start(lines: list[str], suffix: str) -> Mutation | None:
    if suffix != ".py":
        return None
    pattern = re.compile(r"enumerate\(([^,\n)]+)\)")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if not pattern.search(line):
            continue
        changed = pattern.sub(r"enumerate(\1, 1)", line, count=1)
        return Mutation(
            name="index-origin",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Changed enumerate to start at 1, shifting indexes while leaving the loop structure believable.",
        )
    return None


def mutate_py_get_default(lines: list[str], suffix: str) -> Mutation | None:
    if suffix != ".py":
        return None
    pattern = re.compile(r"\.get\(([^,\n()]+),\s*([^)\n]+)\)")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if not pattern.search(line):
            continue
        changed = pattern.sub(r".get(\1)", line, count=1)
        return Mutation(
            name="default-drop",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Dropped a dictionary default value, letting missing keys turn into None unexpectedly.",
        )
    return None


def mutate_js_optional_chain(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in (JS_LIKE | KOTLIN_LIKE | SWIFT_LIKE | CSHARP_LIKE):
        return None
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if "?." not in line:
            continue
        changed = line.replace("?.", ".", 1)
        return Mutation(
            name="optional-chain-drop",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Removed optional chaining, turning rare nullish inputs into runtime crashes.",
        )
    return None


def mutate_rounding_drift(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        targets = [("Math.floor(", "Math.round("), ("Math.ceil(", "Math.floor(")]
    elif suffix in PY_LIKE:
        targets = [("math.floor(", "round("), ("floor(", "round("), ("math.ceil(", "math.floor(")]
    elif suffix in GO_LIKE:
        targets = [("math.Floor(", "math.Round("), ("math.Ceil(", "math.Floor(")]
    elif suffix in RUST_LIKE:
        targets = [(".floor()", ".round()"), (".ceil()", ".floor()")]
    elif suffix in (JAVA_LIKE | KOTLIN_LIKE):
        targets = [("Math.floor(", "Math.round("), ("Math.ceil(", "Math.floor(")]
    elif suffix in CSHARP_LIKE:
        targets = [("Math.Floor(", "Math.Round("), ("Math.Ceiling(", "Math.Floor(")]
    elif suffix in PHP_LIKE:
        targets = [("floor(", "round("), ("ceil(", "floor(")]
    elif suffix in RUBY_LIKE:
        targets = [(".floor", ".round"), (".ceil", ".floor")]
    elif suffix in SWIFT_LIKE:
        targets = [("floor(", "round("), ("ceil(", "floor(")]
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for old, new in targets:
            if old in line:
                changed = line.replace(old, new, 1)
                return Mutation(
                    name="rounding-drift",
                    line=idx + 1,
                    before=line.rstrip("\n"),
                    after=changed.rstrip("\n"),
                    explanation="Changed rounding behavior, creating subtle count, price, layout, or pagination drift.",
                )
    return None


def mutate_filter_leak(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        pattern = re.compile(r"\.filter\(\s*Boolean\s*\)")
        replacement = ".filter(() => true)"
    elif suffix in PY_LIKE:
        pattern = re.compile(r"filter\(\s*None\s*,\s*([^)]+)\)")
        replacement = r"\1"
    elif suffix in RUBY_LIKE:
        pattern = re.compile(r"\.compact\b")
        replacement = ""
    elif suffix in RUST_LIKE:
        pattern = re.compile(r"\.flatten\(\)")
        replacement = ".map(|x| x.unwrap_or_default())"
    elif suffix in (JAVA_LIKE | KOTLIN_LIKE):
        pattern = re.compile(r"\.filterNotNull\(\)")
        replacement = ""
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if not pattern.search(line):
            continue
        changed = pattern.sub(replacement, line, count=1)
        return Mutation(
            name="filter-leak",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Removed an implicit filtering step, allowing empty, nullish, or invalid values to leak downstream.",
        )
    return None


def mutate_dedupe_drop(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        pattern = re.compile(r"\[\s*\.\.\.new Set\(([^)]+)\)\s*\]")
        replacement = r"\1"
    elif suffix in PY_LIKE:
        pattern = re.compile(r"list\(\s*set\(([^)]+)\)\s*\)")
        replacement = r"\1"
    elif suffix in RUST_LIKE:
        pattern = re.compile(r"([A-Za-z_][\w]*)\.dedup\(\)")
        replacement = ""
    elif suffix in RUBY_LIKE:
        pattern = re.compile(r"\.uniq\b")
        replacement = ""
    elif suffix in (JAVA_LIKE | KOTLIN_LIKE):
        pattern = re.compile(r"\.distinct\(\)")
        replacement = ""
    elif suffix in CSHARP_LIKE:
        pattern = re.compile(r"\.Distinct\(\)")
        replacement = ""
    elif suffix in PHP_LIKE:
        pattern = re.compile(r"array_unique\(([^)]+)\)")
        replacement = r"\1"
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if not pattern.search(line):
            continue
        changed = pattern.sub(replacement, line, count=1)
        return Mutation(
            name="dedupe-drop",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Removed deduplication while preserving the surrounding shape, letting duplicate records leak through.",
        )
    return None


def mutate_partial_match(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        targets = [(".startsWith(", ".includes("), (".endsWith(", ".includes(")]
    elif suffix in PY_LIKE:
        targets = [(".startswith(", ".__contains__("), (".endswith(", ".__contains__(")]
    elif suffix in (JAVA_LIKE | KOTLIN_LIKE):
        targets = [(".startsWith(", ".contains("), (".endsWith(", ".contains(")]
    elif suffix in CSHARP_LIKE:
        targets = [(".StartsWith(", ".Contains("), (".EndsWith(", ".Contains(")]
    elif suffix in GO_LIKE:
        targets = [("strings.HasPrefix(", "strings.Contains("), ("strings.HasSuffix(", "strings.Contains(")]
    elif suffix in RUST_LIKE:
        targets = [(".starts_with(", ".contains("), (".ends_with(", ".contains(")]
    elif suffix in SWIFT_LIKE:
        targets = [(".hasPrefix(", ".contains("), (".hasSuffix(", ".contains(")]
    elif suffix in RUBY_LIKE:
        targets = [(".start_with?(", ".include?("), (".end_with?(", ".include?(")]
    elif suffix in PHP_LIKE:
        targets = [("str_starts_with(", "str_contains("), ("str_ends_with(", "str_contains(")]
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for old, new in targets:
            if old in line:
                changed = line.replace(old, new, 1)
                return Mutation(
                    name="partial-match",
                    line=idx + 1,
                    before=line.rstrip("\n"),
                    after=changed.rstrip("\n"),
                    explanation="Changed prefix/suffix matching into substring matching, making validation too permissive.",
                )
    return None


def mutate_time_unit(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in SUPPORTED_SUFFIXES:
        return None
    patterns = [
        (re.compile(r"(\b(?:timeout|delay|ttl|interval|duration|expiresIn|expires_in)\b[^#\n;]*\*\s*)1000\b", re.IGNORECASE), r"\g<1>100"),
        (re.compile(r"(\b(?:timeout|delay|ttl|interval|duration|expiresIn|expires_in)\b[^#\n;]*/\s*)1000\b", re.IGNORECASE), r"\g<1>100"),
    ]
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        for pattern, replacement in patterns:
            if not pattern.search(line):
                continue
            changed = pattern.sub(replacement, line, count=1)
            return Mutation(
                name="time-unit",
                line=idx + 1,
                before=line.rstrip("\n"),
                after=changed.rstrip("\n"),
                explanation="Changed a time-unit conversion, causing timers, cache TTLs, or delays to be off by a factor.",
            )
    return None


def mutate_status_code(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in SUPPORTED_SUFFIXES:
        return None
    replacements = [("200", "204"), ("201", "200"), ("400", "422"), ("404", "400"), ("500", "503")]
    pattern = re.compile(r"(\bstatus(?:_code)?\b\s*[:=]\s*)(200|201|400|404|500)\b", re.IGNORECASE)
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        current = match.group(2)
        new_value = next(new for old, new in replacements if old == current)
        changed = line[: match.start(2)] + new_value + line[match.end(2) :]
        return Mutation(
            name="status-code-drift",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Changed an HTTP/status code to a nearby plausible value, confusing clients and error handling.",
        )
    return None


def mutate_clear_noop(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in (JS_LIKE | JAVA_LIKE | KOTLIN_LIKE | CSHARP_LIKE | SWIFT_LIKE):
        pattern = re.compile(r"([A-Za-z_$][\w$]*)\.(clear|Clear|removeAll)\(\)")
        replacement = r"\1"
    elif suffix in PY_LIKE:
        pattern = re.compile(r"([A-Za-z_][\w.]*)\.clear\(\)")
        replacement = r"len(\1)"
    elif suffix in RUST_LIKE:
        pattern = re.compile(r"([A-Za-z_][\w]*)\.clear\(\)")
        replacement = r"\1.len()"
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if not pattern.search(line):
            continue
        changed = pattern.sub(replacement, line, count=1)
        return Mutation(
            name="reset-skip",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Turned a reset/clear operation into a harmless read, leaving stale state behind.",
        )
    return None


def mutate_append_order(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        pattern = re.compile(r"\.push\(")
        replacement = ".unshift("
    elif suffix in PY_LIKE:
        pattern = re.compile(r"([A-Za-z_][\w.]*)\.append\(([^)\n]+)\)")
        replacement = r"\1.insert(0, \2)"
    elif suffix in (JAVA_LIKE | KOTLIN_LIKE):
        pattern = re.compile(r"([A-Za-z_][\w.]*)\.add\(([^,)\n]+)\)")
        replacement = r"\1.add(0, \2)"
    elif suffix in CSHARP_LIKE:
        pattern = re.compile(r"([A-Za-z_][\w.]*)\.Add\(([^,)\n]+)\)")
        replacement = r"\1.Insert(0, \2)"
    elif suffix in RUST_LIKE:
        pattern = re.compile(r"([A-Za-z_][\w]*)\.push\(([^)\n]+)\)")
        replacement = r"\1.insert(0, \2)"
    elif suffix in RUBY_LIKE:
        pattern = re.compile(r"([A-Za-z_][\w]*)\.push\(([^)\n]+)\)")
        replacement = r"\1.unshift(\2)"
    elif suffix in GO_LIKE:
        pattern = re.compile(r"(\w+)\s*=\s*append\(\s*\1\s*,\s*([^)\n]+)\)")
        replacement = r"\1 = append([]{}{\2}, \1...)"
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if not pattern.search(line):
            continue
        changed = pattern.sub(replacement, line, count=1)
        return Mutation(
            name="order-drift",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Changed append-at-end behavior into prepend behavior, preserving data while scrambling order.",
        )
    return None


def mutate_min_max_swap(lines: list[str], suffix: str) -> Mutation | None:
    if suffix in JS_LIKE:
        targets = [("Math.min(", "Math.max("), ("Math.max(", "Math.min(")]
    elif suffix in PY_LIKE:
        targets = [("min(", "max("), ("max(", "min(")]
    elif suffix in (JAVA_LIKE | KOTLIN_LIKE):
        targets = [("Math.min(", "Math.max("), ("Math.max(", "Math.min("), (".coerceAtMost(", ".coerceAtLeast(")]
    elif suffix in CSHARP_LIKE:
        targets = [("Math.Min(", "Math.Max("), ("Math.Max(", "Math.Min(")]
    elif suffix in GO_LIKE:
        targets = [("math.Min(", "math.Max("), ("math.Max(", "math.Min(")]
    elif suffix in RUST_LIKE:
        targets = [(".min(", ".max("), (".max(", ".min(")]
    elif suffix in PHP_LIKE:
        targets = [("min(", "max("), ("max(", "min(")]
    elif suffix in RUBY_LIKE:
        targets = [(".min", ".max"), (".max", ".min")]
    elif suffix in SWIFT_LIKE:
        targets = [("min(", "max("), ("max(", "min(")]
    else:
        return None

    prefixes = ("return ", "const ", "let ", "var ", "value", "total", "result", "final ", "val ", "$")
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if is_ignored_line(line) or not stripped.startswith(prefixes):
            continue
        for old, new in targets:
            if old in line:
                changed = line.replace(old, new, 1)
                return Mutation(
                    name="clamp-inversion",
                    line=idx + 1,
                    before=line.rstrip("\n"),
                    after=changed.rstrip("\n"),
                    explanation="Swapped min/max style logic, making clamping, scoring, or bounds calculations drift.",
                )
    return None


def mutate_boolean_literal(lines: list[str], suffix: str) -> Mutation | None:
    flag_words = r"(?:enabled|visible|active|required|debug|cached|selected|checked|disabled|readonly|readOnly|is_[a-z_]+|IsEnabled|HasValue)"
    if suffix in (JS_LIKE | GO_LIKE | RUST_LIKE | JAVA_LIKE | KOTLIN_LIKE
                  | SWIFT_LIKE | CSHARP_LIKE | C_LIKE | PHP_LIKE):
        pattern = re.compile(rf"(\b{flag_words}\b\s*[:=]\s*)(true|false|True|False)\b")
        replacements = {"true": "false", "false": "true", "True": "False", "False": "True"}
    elif suffix in PY_LIKE or suffix in RUBY_LIKE:
        pattern = re.compile(rf"(\b{flag_words}\b\s*=\s*)(True|False|true|false)\b")
        replacements = {"True": "False", "False": "True", "true": "false", "false": "true"}
    else:
        return None

    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        changed = line[: match.start(2)] + replacements[match.group(2)] + line[match.end(2) :]
        return Mutation(
            name="flag-flip",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Flipped a boolean feature/config flag, creating a believable behavior toggle regression.",
        )
    return None


def mutate_go_err_check_flip(lines: list[str], suffix: str) -> Mutation | None:
    """Flip a Go `if err != nil` into `if err == nil` — a classic high-impact regression."""
    if suffix not in GO_LIKE:
        return None
    pattern = re.compile(r"\bif\s+([A-Za-z_][\w]*)\s*(!=|==)\s*nil\b")
    flip = {"!=": "==", "==": "!="}
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        op = match.group(2)
        changed = line[: match.start(2)] + flip[op] + line[match.end(2) :]
        return Mutation(
            name="nil-check-flip",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Flipped a Go nil-check, so errors are swallowed or the success branch never runs.",
        )
    return None


def mutate_rust_unwrap_or_drop(lines: list[str], suffix: str) -> Mutation | None:
    """Replace `.unwrap_or(x)` / `.unwrap_or_default()` with `.unwrap()` — panics on None/Err."""
    if suffix not in RUST_LIKE:
        return None
    pattern = re.compile(r"\.unwrap_or(?:_default)?\([^)\n]*\)")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        changed = line[: match.start()] + ".unwrap()" + line[match.end() :]
        return Mutation(
            name="unwrap-panic",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Replaced safe `unwrap_or(...)` with `unwrap()`, making rare None/Err values panic at runtime.",
        )
    return None


def mutate_java_equals_to_ref(lines: list[str], suffix: str) -> Mutation | None:
    """Convert `a.equals(b)` into `a == b` — classic Java reference-vs-value bug."""
    if suffix not in (JAVA_LIKE | KOTLIN_LIKE):
        return None
    pattern = re.compile(r"([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)\.equals\(([^()\n]+)\)")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        changed = pattern.sub(r"\1 == \2", line, count=1)
        return Mutation(
            name="equals-to-ref",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Replaced `.equals(...)` with `==`, turning value comparison into reference comparison.",
        )
    return None


def mutate_swift_force_unwrap(lines: list[str], suffix: str) -> Mutation | None:
    """Turn `?? default` into `!` — classic Swift force-unwrap regression."""
    if suffix not in SWIFT_LIKE:
        return None
    pattern = re.compile(r"\s*\?\?\s*[^,\n)\]\}]+")
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        match = pattern.search(line)
        if not match:
            continue
        changed = line[: match.start()] + "!" + line[match.end() :]
        return Mutation(
            name="force-unwrap",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Replaced Swift `?? default` with `!`, crashing on nil optionals.",
        )
    return None


def mutate_ruby_safe_nav_drop(lines: list[str], suffix: str) -> Mutation | None:
    if suffix not in RUBY_LIKE:
        return None
    for idx, line in enumerate(lines):
        if is_ignored_line(line):
            continue
        if "&." not in line:
            continue
        changed = line.replace("&.", ".", 1)
        return Mutation(
            name="optional-chain-drop",
            line=idx + 1,
            before=line.rstrip("\n"),
            after=changed.rstrip("\n"),
            explanation="Removed Ruby safe-navigation `&.`, so nil receivers raise NoMethodError.",
        )
    return None


MUTATORS = {
    "boolean-operator": mutate_boolean_operator,
    "equals-to-ref": mutate_java_equals_to_ref,
    "force-unwrap": mutate_swift_force_unwrap,
    "nil-check-flip": mutate_go_err_check_flip,
    "unwrap-panic": mutate_rust_unwrap_or_drop,
    "case-sensitive": mutate_case_normalization_removal,
    "clamp-inversion": mutate_min_max_swap,
    "comparison-flip": mutate_comparison_flip,
    "config-drift": mutate_numeric_knob,
    "default-drop": mutate_py_get_default,
    "dedupe-drop": mutate_dedupe_drop,
    "falsy-default": mutate_nullish_to_or,
    "filter-leak": mutate_filter_leak,
    "flag-flip": mutate_boolean_literal,
    "index-origin": mutate_py_enumerate_start,
    "missing-await": mutate_missing_await,
    "normalization-skip": mutate_trim_removal,
    "off-by-one": lambda lines, suffix: (
        mutate_js_off_by_one(lines, suffix)
        or mutate_py_range_shrink(lines, suffix)
        or mutate_go_off_by_one(lines, suffix)
        or mutate_rust_off_by_one(lines, suffix)
    ),
    "order-drift": mutate_append_order,
    "optional-chain-drop": lambda lines, suffix: (
        mutate_js_optional_chain(lines, suffix)
        or mutate_ruby_safe_nav_drop(lines, suffix)
    ),
    "property-typo": mutate_js_property_typo,
    "partial-match": mutate_partial_match,
    "reset-skip": mutate_clear_noop,
    "rounding-drift": mutate_rounding_drift,
    "shared-reference": mutate_copy_alias,
    "slice-shift": mutate_slice_shift,
    "sort-direction": mutate_sort_direction,
    "status-code-drift": mutate_status_code,
    "time-unit": mutate_time_unit,
    "truthy-empty": mutate_truthy_empty,
}

MUTATOR_PROFILES = {
    "soft": {
        "boolean-operator",
        "case-sensitive",
        "clamp-inversion",
        "comparison-flip",
        "config-drift",
        "dedupe-drop",
        "falsy-default",
        "filter-leak",
        "flag-flip",
        "normalization-skip",
        "order-drift",
        "partial-match",
        "rounding-drift",
        "shared-reference",
        "slice-shift",
        "sort-direction",
        "status-code-drift",
        "time-unit",
    },
    "messy": {
        "boolean-operator",
        "case-sensitive",
        "clamp-inversion",
        "comparison-flip",
        "config-drift",
        "default-drop",
        "dedupe-drop",
        "equals-to-ref",
        "falsy-default",
        "filter-leak",
        "flag-flip",
        "force-unwrap",
        "index-origin",
        "missing-await",
        "nil-check-flip",
        "normalization-skip",
        "off-by-one",
        "order-drift",
        "partial-match",
        "property-typo",
        "reset-skip",
        "rounding-drift",
        "shared-reference",
        "slice-shift",
        "sort-direction",
        "status-code-drift",
        "time-unit",
        "truthy-empty",
        "unwrap-panic",
    },
    "chaos": set(),
}
MUTATOR_PROFILES["chaos"] = set(MUTATORS)


def mutator_names_for(requested_bug: str, profile: str) -> list[str]:
    if requested_bug != "random":
        return [requested_bug]
    return sorted(MUTATOR_PROFILES[profile])


def apply_mutation(
    path: Path,
    requested_bug: str,
    rng: random.Random,
    blocked_lines: set[int] | None = None,
    profile: str = "messy",
) -> Mutation | None:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    if not lines:
        return None

    blocked_lines = blocked_lines or set()
    bug_names = mutator_names_for(requested_bug, profile)
    rng.shuffle(bug_names)
    for bug_name in bug_names:
        mutation = MUTATORS[bug_name](lines, path.suffix.lower())
        if not mutation:
            continue
        if mutation.line in blocked_lines:
            continue
        lines[mutation.line - 1] = mutation.after + ("\n" if lines[mutation.line - 1].endswith("\n") else "")
        changed = "".join(lines)
        if changed == original:
            continue
        backup = path.with_name(path.name + ".bug-backup")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(changed, encoding="utf-8")
        return mutation
    return None


def build_report(root: Path, changes: list[dict[str, object]], seed: int) -> dict[str, object]:
    return {
        "label": "INTENTIONAL_BUG_DRILL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root.resolve()),
        "seed": seed,
        "changes": changes,
        "restore": "Replace each changed file with its .bug-backup copy, or inspect the JSON entries and revert manually.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inject real, reversible bugs into sandbox code for bug-hunt drills."
    )
    parser.add_argument("target", help="Sandbox directory to mutate.")
    parser.add_argument(
        "--bug",
        choices=["random", *sorted(MUTATORS)],
        default="random",
        help="Bug pattern to inject. Default: random.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(MUTATOR_PROFILES),
        default="messy",
        help="Random mutation profile. soft avoids most crash-like changes; messy creates many survivable regressions; chaos uses everything.",
    )
    parser.add_argument("--count", type=int, default=1, help="Number of files to mutate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatability.")
    parser.add_argument(
        "--marker-file",
        default=DEFAULT_MARKER_FILE,
        help="Marker file that opts a directory into sandbox mutation.",
    )
    parser.add_argument(
        "--report",
        default="BUG_INJECTION_REPORT.json",
        help="Report path, relative to the target directory unless absolute.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.target)
    if not root.exists() or not root.is_dir():
        print(f"error: target is not a directory: {root}", file=sys.stderr)
        return 2

    if args.count < 1:
        print("error: --count must be at least 1", file=sys.stderr)
        return 2

    if not is_sandbox_path(root, args.marker_file):
        print(
            "error: refusing non-sandbox target. Use a path containing one of "
            f"{sorted(ALLOWED_PATH_MARKERS)} or create {args.marker_file} in the target directory.",
            file=sys.stderr,
        )
        return 3

    seed = args.seed if args.seed is not None else random.SystemRandom().randint(1, 2**31 - 1)
    rng = random.Random(seed)
    files = iter_source_files(root)
    rng.shuffle(files)

    changes: list[dict[str, object]] = []
    mutated_lines: dict[Path, set[int]] = {}
    max_rounds = max(3, args.count * max(1, len(files)) * 2)
    for _ in range(max_rounds):
        if len(changes) >= args.count:
            break
        made_progress = False
        rng.shuffle(files)
        for path in files:
            if len(changes) >= args.count:
                break
            mutation = apply_mutation(path, args.bug, rng, mutated_lines.get(path), args.profile)
            if not mutation:
                continue
            mutated_lines.setdefault(path, set()).add(mutation.line)
            made_progress = True
            changes.append(
                {
                    "file": str(path.resolve()),
                    "bug": mutation.name,
                    "line": mutation.line,
                    "before": mutation.before,
                    "after": mutation.after,
                    "explanation": mutation.explanation,
                    "backup": str(path.with_name(path.name + ".bug-backup").resolve()),
                }
            )
        if not made_progress:
            break

    if not changes:
        print("error: no injectable patterns found in supported source files.", file=sys.stderr)
        return 4

    report = build_report(root, changes, seed)
    report["profile"] = args.profile
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
