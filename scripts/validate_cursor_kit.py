#!/usr/bin/env python3
"""Validate starter-kit structure without third-party dependencies."""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
EXPECTED_DOCS = {
    "START-HERE.md",
    "PROJECT-BLUEPRINT.md",
    "docs/00-PRODUCT-CHARTER.md",
    "docs/01-ARCHITECTURE.md",
    "docs/02-DOMAIN-MODEL.md",
    "docs/03-LISTING-LIFECYCLE.md",
    "docs/07-SECURITY-PRIVACY.md",
    "docs/10-AWS-DEPLOYMENT.md",
    "docs/12-DEVELOPMENT-ROADMAP.md",
    "docs/13-MVP-BACKLOG.md",
    "docs/14-OPEN-DECISIONS.md",
    "docs/19-LAUNCH-CHECKLIST.md",
    "docs/20-SOURCE-TRACEABILITY.md",
    "docs/21-FIRST-BUILD-SEQUENCE.md",
    "docs/22-CURSOR-SKILLS-CATALOG.md",
    "docs/23-TECHNICAL-BASELINE.md",
    "docs/24-CONFIGURATION-CONTRACT.md",
    "docs/features/FND-001-005-foundation-bootstrap.md",
    "KIT-MANIFEST.md",
    "VALIDATION.md",
}


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("missing YAML frontmatter")

    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in match.group("body").splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list:
            data.setdefault(current_list, []).append(line[4:].strip().strip('"'))
            continue
        current_list = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            data[key] = []
            current_list = key
        elif value.lower() in {"true", "false"}:
            data[key] = value.lower() == "true"
        else:
            data[key] = value.strip('"')
    return data


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    for relative in sorted(EXPECTED_DOCS):
        check((ROOT / relative).is_file(), f"missing required document: {relative}", errors)

    skill_root = ROOT / ".cursor" / "skills"
    skills = sorted(skill_root.glob("*/SKILL.md"))
    check(len(skills) >= 12, f"expected at least 12 skills, found {len(skills)}", errors)
    seen_names: set[str] = set()
    for path in skills:
        try:
            frontmatter = parse_frontmatter(path)
        except ValueError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        name = frontmatter.get("name")
        check(name == path.parent.name, f"{path.relative_to(ROOT)}: name must match folder", errors)
        check(
            bool(frontmatter.get("description")),
            f"{path.relative_to(ROOT)}: missing description",
            errors,
        )
        check(name not in seen_names, f"duplicate skill name: {name}", errors)
        check(
            frontmatter.get("disable-model-invocation") is True,
            f"{path.relative_to(ROOT)}: expected manual invocation flag",
            errors,
        )
        if isinstance(name, str):
            check(
                bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)),
                f"invalid skill name: {name}",
                errors,
            )
            seen_names.add(name)

    rule_root = ROOT / ".cursor" / "rules"
    rules = sorted(rule_root.glob("*.mdc"))
    check(len(rules) >= 8, f"expected at least 8 rules, found {len(rules)}", errors)
    for path in rules:
        try:
            frontmatter = parse_frontmatter(path)
        except ValueError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        check(
            bool(frontmatter.get("description")),
            f"{path.relative_to(ROOT)}: missing description",
            errors,
        )
        check(
            "alwaysApply" in frontmatter, f"{path.relative_to(ROOT)}: missing alwaysApply", errors
        )

    try:
        json.loads((ROOT / "brand" / "brand-reference-manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid brand manifest: {exc}")

    try:
        with (ROOT / "scaffold" / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        check(
            project["project"]["requires-python"].startswith(">=3.13"),
            "scaffold must target Python 3.13",
            errors,
        )
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"invalid scaffold pyproject: {exc}")

    for python_file in sorted((ROOT / "scaffold" / "src").rglob("*.py")):
        try:
            ast.parse(python_file.read_text(encoding="utf-8"), filename=str(python_file))
        except (OSError, SyntaxError) as exc:
            errors.append(
                f"scaffold Python syntax failed for {python_file.relative_to(ROOT)}: {exc}"
            )

    dockerfile = (ROOT / "scaffold" / "Dockerfile").read_text(encoding="utf-8")
    check("USER app" in dockerfile, "Dockerfile must run as non-root app user", errors)
    check("manage.py migrate" not in dockerfile, "Dockerfile must not auto-run migrations", errors)
    check(
        "STATICFILES_DIRS"
        in (ROOT / "scaffold" / "src" / "config" / "settings" / "base.py").read_text(
            encoding="utf-8"
        ),
        "scaffold must discover project static assets",
        errors,
    )
    compose = (ROOT / "scaffold" / "compose.yaml").read_text(encoding="utf-8")
    check(
        "postgres-data:/var/lib/postgresql\n" in compose,
        "PostgreSQL 18 volume must target /var/lib/postgresql",
        errors,
    )

    start_here = (ROOT / "START-HERE.md").read_text(encoding="utf-8")
    for name in ("bootstrap-django-marketplace", "plan-marketplace-feature", "review-diff"):
        check(f"/{name}" in start_here, f"START-HERE missing /{name}", errors)

    if errors:
        print("Starter-kit validation FAILED:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Starter-kit validation passed: {len(skills)} skills, {len(rules)} rules, "
        f"{len(EXPECTED_DOCS)} required documents."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
