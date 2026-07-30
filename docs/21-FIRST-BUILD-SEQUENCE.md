# First Build Sequence in Cursor

This is the recommended path from “documentation kit” to the first structured listing draft. It deliberately avoids asking one agent session to build the product end-to-end.

## Before PR 1

- Copy this kit into a new repository.
- Commit it unchanged as the planning baseline.
- Resolve or explicitly accept provisional defaults for DEC-001, DEC-002, DEC-003, and DEC-008.
- Keep Cursor terminal/file permissions on **Ask** until the foundation is stable.

## PR 1 — Foundation skeleton and custom user

**Outcome:** A runnable Django application with the custom user model established before any migration history.

Invoke:

```text
/bootstrap-django-marketplace
Limit this change to FND-001, FND-002, FND-003, FND-005 health endpoints, and the smallest Docker/Compose files needed to verify PostgreSQL. Do not implement auth pages or product models.
```

Review hot spots:

- custom user migration is the first project migration
- production settings fail closed
- no automatic migrations in container startup
- no guessed brand values
- `/health/live/` and `/health/ready/` behavior

## PR 2 — Quality tooling and CI

**Outcome:** Every future PR has a reproducible quality gate.

```text
/plan-marketplace-feature FND-006/FND-007: add Ruff, mypy with django-stubs, pytest, coverage, pre-commit, migration drift check, dependency audit, and CI. Planning only.
```

After accepting the spec:

```text
/implement-django-feature docs/features/FND-006-007-quality-and-ci.md
```

Gate: a clean checkout installs from `uv.lock` and CI passes.

## PR 3 — Shared shell, design tokens, request IDs, and error pages

**Outcome:** A safe, accessible server-rendered shell ready for real brand evidence.

```text
/plan-marketplace-feature FND-009 and remaining FND-005. Include base template, semantic token contract, skip link, error pages, request IDs, and safe logging. Do not invent CountyPost colors or fonts.
```

Run `/brand-parity-review` only after evidence is entered in the brand manifest.

## PR 4 — Authentication pages and account policy

**Outcome:** Registration/login/logout/password reset with enumeration-safe behavior.

```text
/plan-marketplace-feature ACC-001 and DEC-101. Treat marketplace identity according to ADR-0008. No seller profile or phone provider in this slice.
```

Require negative tests for account enumeration, open redirects, CSRF, throttling boundaries, and suspended users.

## PR 5 — Seller profile, account status, and permissions

**Outcome:** Explicit public/private seller representation and audited suspension.

```text
/plan-marketplace-feature ACC-002, ACC-003, and ACC-006. Include staff groups/permissions and audit events. Do not add ratings.
```

## PR 6 — Phone verification boundary

**Outcome:** Provider-neutral verification state and a fake/local adapter; production provider can follow separately.

```text
/plan-marketplace-feature ACC-004 and ACC-005. Include E.164 normalization, purpose, expiry, attempts, resend/rate limits, enumeration-safe responses, and consent-version capture. Do not choose a provider unless DEC-003 is accepted.
```

## PR 7 — State/county reference data and canonical routing

**Outcome:** Validated geography and route resolution without listing models.

```text
/plan-marketplace-feature LOC-001, LOC-002, and LOC-003. Include FIPS provenance, idempotent import, state/county relationship constraints, lowercase canonical redirects, and network-active flags.
```

## PR 8 — Catalog, categories, listing kinds, and products

**Outcome:** Controlled taxonomy and server-owned price definitions.

```text
/design-domain-model CAT-001 through CAT-004. Compare database-backed catalog records versus code enums, preserve history, and keep listing fields out of catalog metadata.
```

Then create an accepted feature spec and implement in slices. Do not configure live Stripe Price IDs in source control.

## PR 9 — Listing aggregate and lifecycle foundation

**Outcome:** Draft-only common listing model, status history, and transition service skeleton.

```text
/design-domain-model LST-001, LST-002, and LST-003. Include UUID public identity, location/category relations, price modes, versioning, indexes, seller ownership, archive behavior, and the complete allowed transition graph. Do not implement payment or publication.
```

Use `/create-safe-django-migration` before committing the schema.

## PR 10 — First typed vertical

Use Autos as a representative structured vertical only if stakeholders approve its field contract; otherwise choose the vertical with the clearest accepted requirements.

```text
/build-listing-vertical Autos using docs/features/LST-006-autos.md. Implement typed details, draft form, validation, admin presentation, filter contract, and tests. VIN must remain private. Do not add public browse yet.
```

## Next sequence

Continue from the roadmap:

1. remaining typed verticals
2. secure media upload/processing
3. submission completeness and moderation
4. orders/Stripe webhooks
5. public routes/browse/search
6. seller actions/favorites/renewal
7. outbox/expiration/notifications
8. brand/accessibility/SEO hardening
9. repeatable AWS staging/production
10. controlled launch readiness

At every step use `/plan-marketplace-feature`, then `/implement-django-feature`, `/test-marketplace-feature`, and `/review-diff` in separate, focused contexts.
