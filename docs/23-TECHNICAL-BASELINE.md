# Technical Baseline and Update Policy

**Baseline reviewed:** July 22, 2026

This document records why the starter chooses its versions and where to verify them before a deliberate upgrade. The lockfile—not these ranges—is the exact dependency set used by a build.

## Chosen baseline

| Area | Baseline | Reason |
|---|---|---|
| Python | 3.13 | Mature supported runtime for the chosen Django LTS; narrower than an unbounded “latest Python” policy |
| Django | 5.2 LTS, latest 5.2 patch | Long support runway and lower framework churn during marketplace launch |
| PostgreSQL | 18, current supported minor | Current major supported by Django/RDS; typed relational and search workload fits the product |
| Dependency manager | `uv` 0.11.x | Reproducible lock/sync workflow and one tool for Python/runtime/dependencies |
| Cursor configuration | `.cursor/rules/*.mdc` plus `.cursor/skills/*/SKILL.md` | Compact persistent constraints plus manually invoked procedural workflows |
| AWS web runtime | ECS Express Mode/Fargate | One-container deployment with managed load balancing, HTTPS, networking, scaling, and monitoring defaults |

## First-party references

- Django downloads and support table: https://www.djangoproject.com/download/
- Django 5.2 release notes and compatibility: https://docs.djangoproject.com/en/5.2/releases/5.2/
- Django database support: https://docs.djangoproject.com/en/5.2/ref/databases/
- Cursor project rules: https://cursor.com/docs/rules
- Cursor Agent Skills: https://cursor.com/docs/skills
- ECS Express Mode: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-overview.html
- Official PostgreSQL container image: https://hub.docker.com/_/postgres
- RDS PostgreSQL release calendar: https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-release-calendar.html

## Version policy

- Commit `uv.lock` and install CI/production from it with `--frozen`.
- Permit patch updates through automated dependency pull requests after CI, migration, and smoke-test review.
- Handle Django/Python/PostgreSQL minor or major changes in dedicated pull requests; do not mix them with product work.
- Read Django security releases promptly and update to the latest patch in the 5.2 line unless an evidenced blocker exists.
- Rebuild and redeploy the immutable image for dependency updates; do not patch running containers.
- Test PostgreSQL major upgrades through snapshot restore/clone and application regression before production.
- Re-check Cursor rule/skill schema before changing frontmatter conventions.
- Record a new ADR when changing framework series, database major, rendering architecture, task system, search engine, or deployment platform.

## Pre-bootstrap verification

Before creating `uv.lock`, verify that the selected package index can resolve every range in `scaffold/pyproject.toml`. Review the resolved lockfile for unexpected framework majors or duplicate database drivers, then commit it in the foundation pull request.
