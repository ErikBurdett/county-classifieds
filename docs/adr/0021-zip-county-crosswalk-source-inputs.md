# ADR 0021: ZIP-county crosswalk source inputs

**Status:** Accepted  
**Date:** 2026-07-24  
**Decision owners:** Project owner  
**Supersedes:** ADR-0019 only for its HUD-only source statement  
**Superseded by:** none

## Context

Generic listing county validation needs a locally imported, versioned ZIP-to-
county reference. ADR-0019 identified the HUD USPS ZIP-County Crosswalk, but
the public Harvard Dataverse `one2few_summy` release is also a suitable
operator-provided artifact and can map one ZIP to multiple counties.

## Decision

Continue to import ZIP/county references only through the explicit offline
management command, with SHA256 verification, county-FIPS validation,
transactional/idempotent writes, and no runtime network lookup. Accept only:

- the documented HUD comma-delimited `ZIP,COUNTY` schema, including its ratio
  columns; or
- the tab-delimited lower-case `one2few_summy` schema from Harvard Dataverse
  DOI `10.7910/DVN/0U2TCB`.

Every import requires operator-supplied `--source-name` and `--source-url`,
which are stored unchanged as provenance. A Harvard Dataverse import is not
recorded or presented as a primary HUD artifact.

## Consequences

- Operators may use the Harvard release published 2024-08-12, a HUD-derived
  ZIP-county crosswalk covering 2010–2023 and licensed CC BY-SA 4.0.
- One ZIP may retain multiple same-state county candidates; a candidate remains
  a lookup reference rather than postal-delivery confirmation.
- Files with any other delimiter/header schema, malformed rows, mismatched
  checksums, or unknown county FIPS are rejected without a partial import.

## References

- ADR-0019
- `docs/features/LST-009-universal-generic-listings.md`
- https://doi.org/10.7910/DVN/0U2TCB
