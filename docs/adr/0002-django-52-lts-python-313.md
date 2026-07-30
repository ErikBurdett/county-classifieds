# ADR 0002: Use Django 5.2 LTS on Python 3.13

- Status: Accepted
- Date: 2026-07-22

## Context

Django 6.0 is current, but Django 5.2 is an LTS release with extended support through April 2028. The application is beginning before Django 6.2 LTS and values a long support window and third-party package stability.

Python 3.14 is current, but Python 3.13 offers mature ecosystem support and remains modern and supported.

## Decision

- Pin to the latest Django 5.2 patch (`>=5.2.16,<5.3` at project start).
- Pin the project to Python 3.13.
- Apply patch/security updates promptly through reviewed dependency-only PRs.
- Reassess upgrade to Django 6.2 LTS after its stable release and ecosystem validation.

## Consequences

- Longer stable support window than Django 6.0.
- Some newer framework features are deferred.
- Upgrade planning is explicit rather than accidental.
