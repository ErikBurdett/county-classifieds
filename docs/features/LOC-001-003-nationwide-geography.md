# Feature Specification: LOC-001–003 — Nationwide Geography and Canonical Routes

**Status:** Accepted / implementing  
**Owner:** Developer  
**Milestone:** M2  
**Target release:** Unscheduled  
**Last updated:** 2026-07-23  
**Decision authority:** Project owner

> Policy supersession: ADR-0012 supersedes this specification wherever it
> requires `is_network_enabled` for public directory routes. Active status is
> now the sole directory/finder eligibility control; network-enabled status
> remains required for public inventory.

## 1. Outcome

### Problem

The marketplace needs a consistent nationwide state/county reference model
before listings, browse scopes, and canonical marketplace routes can exist.

### Desired outcome

All Census reference states and counties are importable from a versioned source;
staff control which markets are usable; active locations resolve to lowercase
canonical routes.

### Success measures

- An import rerun makes no unintended changes and reports source provenance.
- Invalid or inactive route contexts are not silently resolved as another
  market. An active, network-disabled context remains a valid empty directory.

## 2. Traceability

### Source requirements

- `docs/00-PRODUCT-CHARTER.md`: one marketplace, state/county browse scopes.
- `docs/20-SOURCE-TRACEABILITY.md`: nationwide technical availability with
  controlled promotion/inventory rollout.

### Accepted decisions

- ADR-0010: Nationwide Geography Reference Data
- ADR-0001: Use a Django Modular Monolith
- ADR-0004: Use PostgreSQL 18

### Assumptions

- The Census 2025 National Counties Gazetteer source has the fields needed for
  state FIPS, full county GEOID, USPS abbreviation, and display name.
- `is_active` means reference data is eligible for ordinary selection; 
  `is_network_enabled` controls whether public market routes may resolve.

### Unresolved decisions/blockers

- County seat and timezone metadata are deferred; the selected source does not
  make either a launch requirement.

## 3. Scope

### In scope

- `locations` Django app with normalized `State` and `County` models.
- U.S. Census source artifact, version/checksum manifest, and idempotent import.
- Staff administration of activation flags.
- State/county route resolver and lowercase canonical redirects.

### Non-goals

- Radius search or per-county deployments. Listings, search results, and the
  state-default/county scope UI were intentionally delivered later through the
  public-browse slices and remain outside this geography feature's data-import
  contract.
- Geocoding, exact-address display, county-seat/timezone enrichment, or
  automated Census downloads in web requests.

### Deferred follow-ups

- The implemented SRCH-003 state-default/county scope behavior uses this route
  resolver; future scope changes must preserve the same active-directory and
  network-enabled inventory boundary.
- Annual source refresh process and source-retention policy are operational
  follow-ups after the initial importer is stable.

## 4. Actors and authorization

| Actor | May view | May create/change | Restrictions/audit |
|---|---|---|---|
| Anonymous buyer | Network-enabled route context | None | Unknown or disabled context is not exposed |
| Seller | Network-enabled route context | None | May not alter reference data |
| Administrator | All reference records | Import and activation flags | Django permissions and admin log |
| System command | Source artifact | Idempotent upsert | Explicit command, provenance output |

## 5. User and operator flows

### Primary flow

1. An administrator obtains the documented Census source artifact.
2. The import command validates headers, FIPS/GEOID, and source checksum.
3. The command upserts states and counties and records a source manifest.
4. An administrator controls active directory availability and, separately,
   network inventory eligibility.
5. A buyer opens a lowercase state/county route and receives canonical context.

### Alternate/failure flows

- Invalid archive, header, duplicate FIPS, or inconsistent state relationship:
  abort before partial writes.
- Source checksum does not match a supplied expected checksum: abort.
- Rerun with unchanged artifact: report unchanged counts and succeed.
- Uppercase or alias route: redirect to lowercase canonical route.
- Unknown or inactive location: 404; never fall back to a statewide page.
- Active network-disabled location: render the directory context without
  inventory that requires network eligibility.

## 6. Behavior and business rules

- State FIPS is a two-digit string; county FIPS/GEOID is a five-digit string.
- A county’s first two FIPS digits MUST match its state FIPS.
- State USPS codes and all route slugs MUST be normalized to lowercase where
  applicable; stored FIPS preserves leading zeroes.
- `is_active` and `is_network_enabled` are separate controls. A county
  directory resolves publicly when it and its state are active; listings also
  require network eligibility.
- The importer MUST deactivate only records absent from a new source when they
  have no marketplace references; otherwise it reports the conflict and leaves
  them intact.

### State transitions

| Current state | Event/actor | New state | Preconditions | Side effects |
|---|---|---|---|---|
| inactive | Staff enables directory | active | Parent state active for county | Admin audit log |
| active | Staff disables directory | inactive | No destructive delete | Public route becomes 404 |
| active/network-enabled | Staff disables inventory | active/network-disabled | No destructive delete | Directory remains; inventory is hidden |

## 7. Data design

### Models/fields

| Model | Field/change | Type | Null/default | Privacy | Reason |
|---|---|---|---|---|---|
| State | `fips`, `usps_code`, `name`, `slug` | strings | required | public | Stable route/reference identity |
| State | `is_active`, `is_network_enabled` | booleans | false/false | internal control | Controlled rollout |
| County | `fips`, `state`, `name`, `slug` | strings/FK | required | public | Normalized county identity |
| County | `is_active`, `is_network_enabled` | booleans | false/false | internal control | Controlled rollout |
| ReferenceImport | source/version/checksum/counts | immutable record | required | internal | Provenance and operations |

### Invariants and constraints

- Unique state FIPS, USPS code, and slug.
- Unique county FIPS and `(state, slug)`.
- Database check or service validation for county FIPS/state FIPS prefix.
- A `County` must reference exactly one `State`.

### Query and index plan

- Unique indexes support route resolution by state slug and `(state, county
  slug)`.
- Admin/import lookups use unique FIPS indexes.
- No speculative search index is introduced.

### Migration/backfill

- Add the `locations` app and reference tables in one initial migration.
- Run the import command as a separate, repeatable post-migration operation.
- No existing marketplace records reference locations, so no backfill exists.

### Retention/deletion

Reference records are deactivated rather than deleted once referenced by
marketplace records. Source artifacts and import manifests follow the approved
operational retention policy when defined.

## 8. Application design

### Domain services/transitions

- `import_census_geography(...)` validates and upserts all data in a
  transaction.
- `set_location_network_status(...)` authorizes staff activation changes.

### Selectors/read models

- `get_network_state_by_slug(...)`
- `get_network_county_by_slugs(...)`

### Forms/validation/policies

- Management-command argument validation for source path, expected checksum,
  and dry-run mode.
- Staff admin validates that county activation cannot bypass state status.

### Views/URLs/templates/admin

- Add reusable state/county route resolver, not public browse pages.
- Resolve `/tx/` and `/tx/potter/` only; views return placeholder context until
  browse/search is implemented.
- Django Admin exposes searchable, filterable reference records and prevents
  ordinary destructive deletion.

### Background/outbox/schedules

None. Imports are deliberate operator commands, not request or scheduled work.

### Third-party integration

The initial command consumes a locally provided Census artifact. It performs no
network download and does not call external services.

## 9. URL, search, and SEO impact

- Canonical paths: `/<state>/` and `/<state>/<county>/`.
- Redirect uppercase/alias forms to lowercase canonical paths.
- State/county context only; statewide/county listing scope parameters arrive
  with SRCH-002.
- Placeholder location routes are `noindex` until useful browse content exists.

## 10. Security, privacy, and abuse cases

| Threat/abuse | Control | Test/evidence |
|---|---|---|
| Untrusted source file | Local explicit path, archive/header/checksum validation | Invalid artifact tests |
| Unauthorized location change | Admin-only permissions | Permission tests |
| Route enumeration leak | Public data only, true 404 for disabled records | Route tests |
| Partial import | Validation before write and transaction | Failure rollback test |
| Sensitive log data | Log source metadata/counts only | Log review |

## 11. Accessibility and responsive behavior

- Route placeholder provides a semantic heading and no color-only status.
- Canonical redirects retain accessible page titles.
- No interaction is introduced beyond existing navigation.

## 12. Notifications and copy

No email or user-facing policy copy is introduced.

## 13. Observability and operations

- Log import source version, checksum, counts, unchanged/upserted/deactivated
  totals, and safe validation failures.
- Admin import result exposes the same bounded counts.
- Update the local data-seeding documentation with exact command syntax.

## 14. Test plan

| Layer | Scenario | Expected result |
|---|---|---|
| Model/constraint | Duplicate FIPS and duplicate state/county slug | Database rejects invalid records |
| Service | County FIPS mismatches state | Import fails atomically |
| Command | Rerun same artifact | No duplicate rows; unchanged counts reported |
| Command | Invalid checksum/header | No rows written |
| Selector | Disabled state/county | No public context returned |
| Request/template | Uppercase route | Lowercase canonical redirect |
| Request/template | Unknown or disabled route | 404 |
| Browser/manual | Placeholder route | Heading and noindex metadata render |

## 15. Rollout and rollback

### Deployment order

1. Deploy additive schema and importer.
2. Import all Census reference data with all records disabled.
3. Enable the launch market records through staff administration.
4. Deploy route resolver and verify route behavior.

### Feature flag/gradual release

`is_network_enabled` is the gradual rollout control; it has no hidden
application behavior.

### Data compatibility

No listing schema exists. Future listing migrations must rely on this reference
data but cannot assume every record is network-enabled.

### Rollback/forward-fix

Disable public routes through activation flags. Do not delete referenced
records; correct import issues with a new artifact or command run.

### Post-deploy verification

- Confirm source checksum and import counts.
- Verify an enabled state/county resolves canonically.
- Verify disabled and unknown routes 404.

## 16. Acceptance criteria

- [ ] A versioned Census source imports all expected states and counties.
- [ ] The command is idempotent and rejects malformed/inconsistent input
  without partial writes.
- [ ] County/state FIPS and slug invariants are enforced by the database.
- [ ] Public directory resolution requires active parent and child records;
  public inventory additionally requires network eligibility.
- [ ] Canonical redirects, unknown/inactive routes, and active
  network-disabled directories are tested.
- [ ] Import provenance and local operational instructions are documented.

## 17. Implementation slices

| Slice | Outcome | Expected files/apps | Migration | Depends on |
|---|---|---|---|---|
| A | State/County schema, constraints, admin | `apps/locations` | initial | ADR-0010 |
| B | Source manifest and idempotent importer | `locations` command/services/tests | additive if manifest model | A |
| C | Route resolver/canonical redirects | `locations` selectors/views/urls/tests | none | A, B |

## 18. Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| Product | Project owner | Geography source accepted; implementation spec review pending | 2026-07-23 |
| Engineering | Developer | Drafted | 2026-07-23 |
| Operations/moderation | | Pending | |
