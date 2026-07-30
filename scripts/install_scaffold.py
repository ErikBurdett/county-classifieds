#!/usr/bin/env python3
"""Install the reviewed Django foundation scaffold into the repository root.

Run from the starter-kit repository root. Existing non-identical files are never
silently overwritten. Review the resulting diff before generating migrations.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

COPY_ITEMS = (
    ".python-version",
    ".env.example",
    ".dockerignore",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "Dockerfile",
    "compose.yaml",
    "Makefile",
    ".github",
    "src",
)


def copy_item(source: Path, destination: Path, *, dry_run: bool) -> list[str]:
    conflicts: list[str] = []
    if source.is_dir():
        for child in source.rglob("*"):
            if child.is_dir():
                continue
            relative = child.relative_to(source)
            target = destination / relative
            conflicts.extend(copy_file(child, target, dry_run=dry_run))
        return conflicts
    return copy_file(source, destination, dry_run=dry_run)


def copy_file(source: Path, destination: Path, *, dry_run: bool) -> list[str]:
    if destination.exists():
        if destination.is_file() and filecmp.cmp(source, destination, shallow=False):
            print(f"unchanged  {destination}")
            return []
        print(f"CONFLICT   {destination}")
        return [str(destination)]

    print(f"create     {destination}")
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="show changes without copying")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = Path.cwd().resolve()
    scaffold = repository / "scaffold"
    if not scaffold.is_dir() or not (repository / "START-HERE.md").is_file():
        print("Run this script from the starter-kit repository root.", file=sys.stderr)
        return 2

    conflicts: list[str] = []
    for item in COPY_ITEMS:
        source = scaffold / item
        if not source.exists():
            print(f"Missing scaffold item: {source}", file=sys.stderr)
            return 2
        destination = repository / item
        conflicts.extend(copy_item(source, destination, dry_run=args.dry_run))

    if conflicts:
        print(
            "\nNo conflicting files were overwritten. Resolve these paths first:", file=sys.stderr
        )
        for conflict in conflicts:
            print(f"- {conflict}", file=sys.stderr)
        return 1

    verb = "Would install" if args.dry_run else "Installed"
    print(
        f"\n{verb} the foundation scaffold. Next: run `uv lock`, review the diff, and invoke the bootstrap quality gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
