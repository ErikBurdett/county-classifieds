---
name: design-domain-model
description: Design or revise a Django/PostgreSQL domain model for a marketplace capability before migrations are generated.
argument-hint: "<domain capability or model area>"
disable-model-invocation: true
---

# Design Domain Model

Use for listings, typed vertical details, moderation, orders, media, favorites, saved searches, notifications, reports, or future capabilities.

## Read and inspect

- `docs/02-DOMAIN-MODEL.md`
- `docs/03-LISTING-LIFECYCLE.md`
- relevant ADRs and feature spec
- existing models, constraints, indexes, migrations, services, and query paths

## Model the domain

For each proposed entity define:

- purpose and owner app
- identity/public identifier
- fields and data types
- required/optional semantics
- relationships and deletion behavior
- lifecycle/state and actor permissions
- invariants and where enforced
- privacy classification and public exposure
- audit/retention needs
- expected query/filter/sort patterns
- indexes/constraints
- concurrency behavior
- migration/backfill implications

## Marketplace-specific constraints

- Common listing data belongs on `Listing`; frequently filtered vertical data belongs in explicit typed one-to-one detail tables.
- Do not use EAV. Use JSONB only for non-core extension metadata.
- Money is integer minor units plus currency.
- Use UUID public IDs.
- State/county are validated reference data.
- Status changes go through the lifecycle service and generate history.
- Keep private VIN, verification, payment, moderation, and abuse data out of public read models.

## Evaluate alternatives

Compare at least the credible alternatives and document tradeoffs in an ADR when the choice is structural. Include expected SQL/query examples for the highest-value paths.

## Output

- proposed model diagram/table
- invariants and constraints
- index plan
- service/selectors affected
- migration sequence
- privacy/audit notes
- open questions
- recommendation

Do not generate migrations unless explicitly asked in a follow-up.
