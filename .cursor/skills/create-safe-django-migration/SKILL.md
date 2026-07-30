---
name: create-safe-django-migration
description: Design, generate, inspect, and verify a production-safe Django migration for PostgreSQL.
argument-hint: "<model/schema change or accepted feature spec>"
disable-model-invocation: true
---

# Create Safe Django Migration

## Inspect first

1. Read the accepted spec/ADR and current model/migration history.
2. Estimate whether the affected table is empty, small, or potentially large; do not assume production cardinality.
3. Identify compatibility requirements between old/new application tasks during rolling deployment.
4. State lock, rewrite, backfill, index, constraint, and rollback risks.

## Plan the sequence

Use expand/migrate/contract where needed:

1. additive/nullable schema
2. dual-read/write only if justified
3. bounded and restartable data backfill
4. behavior switch
5. constraint validation/default tightening
6. later destructive cleanup

Do not combine these merely to reduce migration count.

## Generate and review

- Generate the migration with Django.
- Read every operation.
- Inspect SQL with `sqlmigrate` or the appropriate PostgreSQL tooling.
- For data migrations use historical models, deterministic batches, and explicit atomicity.
- Add/validate constraints and indexes with production locking in mind.
- Never modify a migration already applied outside the branch.

## Test

- migrate from a clean database
- migrate from the prior schema with representative rows
- verify data transformation and constraints
- test reverse migration when supported; otherwise document why not
- run `makemigrations --check --dry-run`
- run affected domain/integration tests

## Output

- migration path(s) and dependency order
- SQL/locking summary
- backfill/restart behavior
- deploy ordering
- rollback or forward-fix plan
- commands and results
- explicit production operator notes
