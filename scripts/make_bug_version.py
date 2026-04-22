#!/usr/bin/env python3
"""Create and refresh a separate bugged version of a source tree.

The clean source is never modified. This script copies the source tree, stores a
clean backup copy, then injects real bugs into the bug-version output.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from inject_bug import MUTATORS, MUTATOR_PROFILES, SKIP_DIRS, SUPPORTED_SUFFIXES, apply_mutation


MANIFEST_NAME = "BUG_VERSION_MANIFEST.json"
GENERATOR_ID = "bug.make_bug_version"
EXTRA_SKIP_DIRS = {
    ".bug-backups",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".turbo",
    ".vite",
    ".vscode",
}
EXTRA_SKIP_FILES = {
    "BUG_INJECTION_REPORT.json",
    "BUG_VERSION_MANIFEST.json",
}


def resolve(path: Path) -> Path:
    return path.expanduser().resolve()


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def default_output(source: Path) -> Path:
    return source.parent / f"{source.name}-bug-version"


def default_backup(source: Path) -> Path:
    return source.parent / f"{source.name}-clean-backup"


def validate_paths(source: Path, output: Path, backup: Path) -> None:
    if not source.exists() or not source.is_dir():
        raise ValueError(f"source is not a directory: {source}")
    if output == source:
        raise ValueError("output must be different from source")
    if backup == source:
        raise ValueError("backup must be different from source")
    if output == backup:
        raise ValueError("output and backup must be different directories")
    if is_relative_to(output, source):
        raise ValueError("output cannot be inside source; choose a sibling directory")
    if is_relative_to(backup, source):
        raise ValueError("backup cannot be inside source; choose a sibling directory")


def was_generated(path: Path) -> bool:
    manifest = path / MANIFEST_NAME
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return data.get("generated_by") == GENERATOR_ID


def replace_generated_dir(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_dir():
        raise ValueError(f"refusing to replace non-directory path: {path}")
    if not was_generated(path):
        raise ValueError(
            f"refusing to replace {path}; it is missing a {MANIFEST_NAME} created by this script"
        )
    shutil.rmtree(path)


def ignore_names(_: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in SKIP_DIRS or name in EXTRA_SKIP_DIRS or name in EXTRA_SKIP_FILES:
            ignored.add(name)
            continue
        if name.endswith(".bug-backup"):
            ignored.add(name)
            continue
        suffix = Path(name).suffix.lower()
        if suffix in {".pyc", ".pyo", ".log", ".tmp"}:
            ignored.add(name)
    return ignored


def copy_tree(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=ignore_names)


def iter_mutable_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if any(part in SKIP_DIRS or part in EXTRA_SKIP_DIRS for part in path.parts):
            continue
        if path.name.endswith(".bug-backup"):
            continue
        files.append(path)
    return sorted(files)


def inject_into_output(
    output: Path,
    bug: str,
    count: int,
    seed: int,
    profile: str,
) -> list[dict[str, object]]:
    rng = random.Random(seed)
    files = iter_mutable_files(output)
    rng.shuffle(files)

    changes: list[dict[str, object]] = []
    mutated_lines: dict[Path, set[int]] = {}
    max_rounds = max(3, count * max(1, len(files)) * 2)
    for _ in range(max_rounds):
        if len(changes) >= count:
            break
        made_progress = False
        rng.shuffle(files)
        for path in files:
            if len(changes) >= count:
                break
            mutation = apply_mutation(path, bug, rng, mutated_lines.get(path), profile)
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
    return changes


def write_manifest(
    source: Path,
    output: Path,
    backup: Path,
    seed: int,
    bug: str,
    count: int,
    profile: str,
    changes: list[dict[str, object]],
) -> dict[str, object]:
    manifest = {
        "label": "INTENTIONAL_BUG_VERSION",
        "generated_by": GENERATOR_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "output": str(output),
        "clean_backup": str(backup),
        "seed": seed,
        "profile": profile,
        "requested_bug": bug,
        "requested_count": count,
        "changes": changes,
        "refresh": "Run make_bug_version.py again to rebuild this output from the clean source and inject a new bug set.",
        "restore": "Use the source directory or clean_backup directory; the bug-version output is disposable.",
    }
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (output / MANIFEST_NAME).write_text(text, encoding="utf-8")
    (backup / MANIFEST_NAME).write_text(text, encoding="utf-8")
    return manifest


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a separate bug-version copy from a clean source tree."
    )
    parser.add_argument("source", help="Clean source directory to copy.")
    parser.add_argument(
        "--out",
        default=None,
        help="Bug-version output directory. Default: sibling named <source>-bug-version.",
    )
    parser.add_argument(
        "--backup",
        default=None,
        help="Clean backup directory. Default: sibling named <source>-clean-backup.",
    )
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
    parser.add_argument("--count", type=int, default=3, help="Number of files to mutate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatability.")
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Mutate the existing bug-version output instead of rebuilding from source.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    source = resolve(Path(args.source))
    output = resolve(Path(args.out)) if args.out else resolve(default_output(source))
    backup = resolve(Path(args.backup)) if args.backup else resolve(default_backup(source))

    try:
        validate_paths(source, output, backup)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.count < 1:
        print("error: --count must be at least 1", file=sys.stderr)
        return 2

    seed = args.seed if args.seed is not None else random.SystemRandom().randint(1, 2**31 - 1)

    try:
        if args.keep_existing:
            if not output.exists() or not was_generated(output):
                raise ValueError("--keep-existing requires an existing generated bug-version output")
        else:
            replace_generated_dir(output)
            replace_generated_dir(backup)
            copy_tree(source, output)
            copy_tree(source, backup)

        changes = inject_into_output(output, args.bug, args.count, seed, args.profile)
        if not changes:
            raise ValueError("no injectable patterns found in copied source files")

        manifest = write_manifest(
            source,
            output,
            backup,
            seed,
            args.bug,
            args.count,
            args.profile,
            changes,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
