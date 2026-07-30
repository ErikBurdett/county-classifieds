# TheCountyPost Market

This is an active Django marketplace implementation with accompanying product,
operations, and Cursor workflow documentation. It remains a local/demo
foundation, not a production launch.

## Current implementation snapshot

- Nationwide local Census 2025 reference data: 52 state-equivalents and 3,222
  counties, with separate active-directory and public-network controls.
- 19 verticals / 229 categories; eight typed local demo presentations and
  25,776 synthetic nationwide demo listings.
- Private typed drafts, generic media, moderation/lifecycle, local deterministic
  billing/refunds, outbox operations, public browse/detail/media, M10 SEO/UI
  foundations, M11 Terraform/runbooks, and M12 staff console/policy foundations.
- No production Stripe, SES, AWS, DNS, ACM, legal approval, staging rehearsal,
  or staff-launch sign-off. See `dev-report.md`.

## Documentation and development resources

- A product charter that explicitly distinguishes stakeholder requirements from engineering decisions.
- A modular-monolith architecture for Django and PostgreSQL.
- A detailed domain model for listings, vertical-specific details, moderation, billing, media, favorites, notifications, and future features.
- A listing state machine and payment/moderation workflows.
- A milestone-based development roadmap with acceptance gates.
- Project-level Cursor rules for persistent standards.
- Manual Cursor Agent Skills for repeatable implementation, review, migration, security, Stripe, branding, and deployment workflows.
- Templates for feature specifications, ADRs, pull requests, threat models, incidents, and release reviews.
- A source-traceability matrix and an exact first-build/first-PR sequence.
- Starter configuration templates for `uv`, Docker, Docker Compose, GitHub Actions, and split Django settings.
- A validation report that distinguishes structural checks completed here from the local/CI gates that still must run.

## Baseline engineering decisions

| Area | Decision |
|---|---|
| Application | One Django modular monolith; no microservices for MVP |
| Runtime | Python 3.13 |
| Framework | Django 5.2 LTS, latest 5.2 patch |
| Database | PostgreSQL 18 locally and on Amazon RDS |
| Frontend | Django templates, semantic HTML, progressive enhancement; no SPA |
| Admin/operations | Django Admin with explicit marketplace roles and audit records |
| Search | PostgreSQL full-text search, trigram support, typed indexes |
| Static assets | WhiteNoise initially |
| Listing media | Direct-to-S3 upload with a private staging prefix and processed public assets |
| Payments | Stripe Checkout plus verified, idempotent webhooks; no Stripe Connect |
| Background work | Transactional outbox plus a separate worker process; EventBridge for schedules |
| Deployment | One container image on ECS Express Mode; separate web and worker commands |
| Infrastructure | RDS, S3, SES, Secrets Manager, CloudWatch, Route 53, ACM; IaC before production |

## Product framing

The source material is an initial AI-assisted conversation from a non-technical stakeholder. It is useful for intent and scope, but it is not an implementation specification. The project therefore treats product decisions as explicit records and never silently fills gaps.

The central product promise is a structured, moderated, trusted regional marketplace rather than a free-form bulletin board. The application is independent at `market.thecountypost.com`, while one shared database supports every county and every listing carries required state and county data.

## Brand status

Exact colors, typefaces, spacing, logo assets, and component styling are intentionally **not guessed**. The public `thecountypost.com` domain was not resolvable from the research environment on July 22, 2026. See `docs/08-BRAND-UI-SYSTEM.md` and `brand/brand-reference-manifest.json` for the required capture process. All UI must use semantic design tokens so verified brand values can be applied centrally.

## Start here

1. Read `dev-report.md`, `docs/12-DEVELOPMENT-ROADMAP.md`, and
   `docs/14-OPEN-DECISIONS.md`.
2. Use `docs/17-LOCAL-DEVELOPMENT.md` and `docs/18-DATA-SEEDING.md` for local
   commands and fixture boundaries.
3. Use `/plan-marketplace-feature` before non-trivial work and `/review-diff`
   before a pull request.

## Important working rule

Do not ask Cursor to “build the whole marketplace.” Give it one accepted feature specification, one milestone slice, and one testable outcome at a time.
