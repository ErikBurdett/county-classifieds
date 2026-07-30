---
name: bootstrap-django-marketplace
description: Bootstrap the approved Django marketplace foundation in a new or documentation-only repository. Use once before feature implementation.
argument-hint: "[optional constraints]"
disable-model-invocation: true
---

# Bootstrap Django Marketplace

Create only the application foundation. Do **not** implement listings, payments, moderation, search, messaging, or other product features in this change.

## Read first

- `START-HERE.md`
- `PROJECT-BLUEPRINT.md`
- `docs/01-ARCHITECTURE.md`
- `docs/07-SECURITY-PRIVACY.md`
- `docs/09-TEST-STRATEGY.md`
- `docs/10-AWS-DEPLOYMENT.md`
- `docs/14-OPEN-DECISIONS.md`
- accepted ADRs in `docs/adr/`
- `scaffold/README.md` and all scaffold templates

## Preconditions

1. Inspect the repository and Git status.
2. Confirm no application foundation already exists. If it does, switch to a gap analysis; do not overwrite it.
3. Surface unresolved P0 choices that would make the foundation irreversible, especially the user model/identity decision.
4. State the file plan, dependency plan, and initial migration plan before editing.

## Build

Create a `src/`-layout Django project using Python 3.13, the latest permitted Django 5.2 LTS patch, `uv`, and PostgreSQL.

Required foundation:

- split settings: `base`, `local`, `test`, `production`
- custom user model defined before first migration
- modular app packages matching `docs/01-ARCHITECTURE.md`
- `/health/live/` and `/health/ready/`
- base URL configuration, templates, error pages, static structure, and semantic design tokens
- secure environment parsing with required production values
- PostgreSQL-backed local Compose environment
- one non-root production Docker image
- Ruff, mypy/django-stubs, pytest/pytest-django, coverage, pre-commit
- CI that installs from the lockfile and runs the full quality gate
- Make targets documented in `scaffold/Makefile`
- minimal admin registration for the custom user only
- no sample secrets and no guessed brand values

## Verify

Run the actual equivalents of:

```bash
make bootstrap
make format-check
make lint
make typecheck
make django-check
make migration-check
make test
make build
```

Start the local stack and verify the home page, liveness, readiness, admin login route, static asset loading, and database connection.

## Deliver

Report:

- files created/changed
- dependencies and exact locked versions
- migration names and reviewed SQL summary
- commands run with results
- local startup instructions
- unresolved issues or decisions
- explicit confirmation that no product feature was implemented
