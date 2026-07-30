# FND-001–005 — Django Foundation Bootstrap

**Status:** Accepted engineering foundation, subject to DEC-001 identity confirmation before first migration  
**Owner:** Developer  
**Milestone:** M0  
**Risk:** Medium because the custom user model and initial migration are expensive to reverse

## Outcome

A clean repository becomes a runnable, tested, production-shaped Django 5.2 LTS application on Python 3.13 and PostgreSQL, without implementing marketplace product features.

## In scope

- `src/` Django project
- split settings for local, test, build, and production
- custom email-based UUID user model before the first migration
- Django Admin registration for that user
- PostgreSQL Compose service
- liveness and database readiness endpoints
- request IDs and safe baseline logging
- base templates, error pages, static discovery, and neutral semantic design tokens
- `uv`, Ruff, mypy/django-stubs, pytest, coverage, pre-commit
- non-root multi-stage production image
- GitHub Actions quality and container-build jobs

## Non-goals

- public registration/login pages
- seller profiles or phone verification
- state/county records
- listings, media, moderation, billing, search, notifications, or AWS resources
- final CountyPost colors, fonts, logo, or layout

## Acceptance criteria

1. A fresh checkout can generate and commit `uv.lock`, install dependencies, and start PostgreSQL.
2. The first project migration creates the custom user model; no default Django user migration history is established first.
3. Email identity is normalized and protected against case-variant duplicates.
4. Passwords use Argon2 first in normal environments.
5. `/health/live/` does not call external dependencies; `/health/ready/` returns 503 without leaking database errors when the database is unavailable.
6. Production settings fail closed when required values are missing and require HTTPS/security-cookie behavior.
7. Static project assets are discovered locally and collected into the image.
8. The image runs as a non-root user and does not run migrations on ordinary startup.
9. `make check` and the container build pass from the committed lockfile.
10. No product schema, secret, or invented CountyPost brand value is introduced.

## Required review evidence

- generated initial migration and `sqlmigrate` output
- all quality-gate command results
- local home, admin login, liveness, and readiness checks
- production `check --deploy` result
- image build and container health result
- explicit confirmation of the accepted DEC-001 identity choice
