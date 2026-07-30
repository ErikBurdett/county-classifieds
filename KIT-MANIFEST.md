# Starter Kit Manifest

## Purpose

This kit is the engineering bridge between the initial non-technical marketplace conversation and a reviewable Django implementation. It supplies project context, decision boundaries, Cursor guidance, a foundation scaffold, and release/operations checklists. It does not pretend unresolved stakeholder policy is settled.

## Included systems

- **Product and traceability:** charter, source matrix, open-decision register, MVP boundary, backlog, definition of done.
- **Architecture:** modular monolith, app boundaries, domain model, lifecycle, routes/search/SEO, diagrams, and ADRs.
- **Operational design:** moderation, billing/expiry, security/privacy, AWS, observability, seeding, launch, and incident/release templates.
- **Cursor:** 10 project rules and 16 manual Agent Skills.
- **Django foundation:** Python/Django/PostgreSQL config, custom email-first UUID user, settings split, health checks, request IDs, tests, Docker, Compose, CI, Dependabot, and quality tools.
- **Brand workflow:** evidence manifest, capture checklist/script, semantic token contract, and parity-review skill without guessed brand values.
- **Reusable templates:** feature spec, ADR, PR, threat model, release, bug, incident, Cursor skill, and Cursor rule.
- **Source:** the original `CountyPost-Marketplace-Spec-v6-FINAL.docx` retained under `source/`.

## Current counts

Counts are validated by `scripts/validate_cursor_kit.py` and may increase as the project evolves:

- 16 manual Cursor skills
- 10 Cursor project rules
- 25 numbered engineering documents, plus ADRs/features
- 9 initial ADRs
- 9 reusable work/review templates
- 4 Mermaid architecture/workflow diagrams
- one installable Django foundation scaffold

## Deliberately not included yet

- accepted answers to stakeholder-owned product/legal decisions
- exact TheCountyPost colors, fonts, logos, or licensed assets
- generated initial migration or `uv.lock` before the identity decision and dependency resolution
- production AWS resource identifiers, secrets, or live Stripe values
- Phase 1B messaging, ratings, SMS, dealer subscriptions, advanced search, or mobile apps
