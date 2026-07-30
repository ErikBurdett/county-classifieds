# ADR 0022: ZIP-county missing-geography handling

**Status:** Accepted  
**Date:** 2026-07-24  
**Decision owners:** Project owner  
**Supersedes:** ADR 0021 only for handling source county FIPS absent from local geography  
**Superseded by:** none

## Context

The accepted ZIP/county crosswalk inputs can include valid county FIPS from
geographies that have not been loaded into the application's local Census
reference data. For example, Harvard Dataverse `one2few_summy` includes USVI
FIPS `78030`, while a local geography import may not include that county.
Rejecting the entire transaction prevents compatible crosswalk rows from being
imported.

## Decision

Continue to reject malformed ZIP/FIPS, schema, and SHA256 checksum failures.
When a syntactically valid source county FIPS is absent from the local `County`
table, skip that row without creating or inferring geography. Count skipped rows
and print both a warning and final summary for operators.

Import all rows whose county FIPS exists locally. Fail before writes if no
source rows are compatible with local geography, protecting against a wrong
source file or geography dataset. Preserve transactional, idempotent, and
dry-run behavior.

## Consequences

- Partial local geography imports can consume compatible portions of valid
  nationwide crosswalks.
- Operators receive explicit visibility into every omitted row count, but not
  a fabricated mapping or county record.
- A source containing only absent FIPS remains a fatal operational mismatch,
  with no crosswalk rows written.

## References

- ADR 0021
- `docs/features/LST-009-universal-generic-listings.md`
