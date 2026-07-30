# M8 Development Report

**Date:** 2026-07-23  
**Status:** Implementing

## Intended behavior

This implementation keeps public exposure fail-closed for expired, sold,
archived, unreviewed, and materially edited listings. Owner actions and payment
outcomes use audited services; favorite reads never bypass public visibility.

## Changed areas

- `listings.0011`: lifecycle expiration/edit fields, sold/expired/archived
  statuses, favorite table, visibility and favorite indexes/constraints.
- `billing.0002`: immutable order purpose and one-pending-renewal constraint.
- Listing/billing services, selectors, owner routes, dashboard, and public detail
  favorite affordance.

## Security and operations

All mutations are POST/CSRF-protected and owner-scoped or public-selector-scoped.
No external provider, secrets, scheduler, refund path, or background worker was
added. Migrations are additive; rollback should disable routes while retaining
auditable records, then forward-fix.

## Verification

Verified 2026-07-23:

- `make check` passed: 145 tests passed, 5 PostgreSQL-only tests skipped under
  SQLite, and total coverage was 85.09%.
- `make test-e2e` passed: 4 browser smoke tests passed.
- PostgreSQL `sqlmigrate` output for `listings.0011` and `billing.0002` was
  reviewed; both migrations applied successfully to the local PostgreSQL 18
  database.
