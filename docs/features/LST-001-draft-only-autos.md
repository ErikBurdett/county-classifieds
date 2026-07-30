# Feature Specification: LST-001 — Draft-only Automobile Listings

**Status:** Implemented locally; later lifecycle/public-demo work supersedes
the original draft-only boundary  
**Owner:** Project owner  
**Milestone:** M1–M3 foundation slice  
**Last updated:** 2026-07-23  
**Authorization:** User-authorized implementation

> Historical scope note: this foundation slice excluded public listing routes.
> Later M5–M10 work provides controlled public browse/detail/media; seller
> eligibility and production payment remain incomplete.

## Outcome

Authenticated sellers can create, edit, and inspect their own private
automobile drafts. This slice establishes the account profile, reference
location, catalog, shared listing, and typed automobile-detail foundations
without making any listing public.

## Scope
- Self-service `/register/` creates a normalized email-based user and required
  seller profile, then signs the seller in and redirects to the dashboard.
- `SellerProfile` with a display name, optional phone, and explicit
  unverified/verified state. No phone provider or verification flow is added.
- State and county reference records with FIPS, USPS code, lowercase slug,
  active, and network-enabled controls.
- Catalog verticals and categories.
- A shared draft-only `Listing` with integer `price_minor` and ISO `currency`,
  plus typed one-to-one `AutoDetails`.
- Authenticated dashboard, seller-profile, automobile create/edit/detail
  pages, Django admin, named URLs, and an idempotent local seed command.

## Non-goals

- Public listing/browse/detail pages, publication, search, SEO routes, uploads,
  payment, moderation, submission, messaging, ratings, and notifications.
- Phone provider integration, phone verification UI, external Census download,
  or a nationwide geography importer.
- VIN public rendering. VIN is restricted to its owner through the private
  draft form and to authorized Django admin users.

## Actors and permissions

| Actor | Permission |
|---|---|
| Authenticated seller | Create a seller profile and create/read/update only their own drafts |
| Non-owner authenticated user | Receives 404 for another seller's private draft |
| Anonymous user | Redirected to sign-in for private workflow URLs |
| Django staff | Admin access according to standard Django permissions |

## Behavior and data rules
- Registration requires a unique normalized email, a unique normalized display
  name, and a valid confirmed password. It creates the user and seller profile
  in one transaction; no email or phone verification is performed in this
  slice.
- All listings created by this slice have the sole allowed status, `draft`.
- Listing changes occur through transactional domain services, never signals.
- A listing category must belong to its vertical and its county must belong to
  its state; PostgreSQL triggers enforce these cross-table invariants.
- County FIPS must start with the referenced state's FIPS. Category parents
  must belong to the same vertical. PostgreSQL triggers enforce both.
- An `AutoDetails` row is one-to-one with a listing and can only reference the
  `autos` vertical. Service and database checks also enforce non-negative
  prices/mileage, ISO currency, and a verified phone requiring a phone value.
- Active vertical/category/state/county records are required by the drafting
  service. Network-enabled flags exist for future public routes and have no
  public routing behavior in this slice.
- A draft detail template never includes the VIN.

## Security and privacy
- Registration and logout are CSRF-protected POST flows. Registration does not
  honor a `next` parameter and always redirects to the seller dashboard.
- Owner-scoped selector filters are used for every draft read/edit, returning
  404 rather than leaking the draft's existence.
- Browser mutations use Django CSRF middleware and authenticated POSTs.
- VIN is not selected into any public route (none exist) and is not rendered on
  the owner detail page. No public selector is introduced.
- Phone verification remains explicitly unverified unless staff updates its
  state; no provider, code, or phone logging is introduced.

## Errors and observability

- Invalid form values return the private form with an error summary and
  field-level errors; mismatched references are rejected before any draft is
  saved.
- Non-owner draft reads and edits are intentionally indistinguishable from a
  missing draft (404).
- The seed command writes only bounded reference-record success output. This
  slice adds no external calls, background jobs, metrics, or sensitive logging.

## Migration and rollout

New additive migrations create the accounts profile, locations, catalog, and
listings tables. Existing `accounts.0001_initial` is unchanged. PostgreSQL-only
triggers are installed in follow-up migrations; SQLite retains model/form and
service validation for fast local tests.

The completed self-service registration flow adds no schema migration.

Deploy the schema before running the development-only seed. Rollback is a
forward fix: disable reference/catalog records and keep drafts private; do not
delete seller or listing records.

## Operations and local usage

With local development settings and migrated database:

```bash
make compose-up
make migrate
make seed-texas-autos
```

`seed_texas_autos` refuses to run unless `DEBUG` is enabled. It upserts Texas
(`48`/`TX`), Potter (`48375`) and Randall (`48381`) counties, and Autos
categories. Re-running it is safe.

## Tests and acceptance criteria

- Model/database tests cover price, seller phone, FIPS/category/location,
  one-to-one AutoDetails, and draft-only state constraints.
- Service tests cover transactional creation/update and invalid cross-model
  data.
- Request tests cover authentication, owner access, 404 for non-owners, form
  errors, dashboard visibility, and VIN omission.
- Registration request tests cover rendering, successful account/profile/session
  creation, duplicate email/display-name validation, invalid password handling,
  and ignored untrusted `next` redirects.
- Migration checks and PostgreSQL `sqlmigrate` output are reviewed before
  deployment.

Acceptance for this historical draft slice is met when an authenticated seller
can create, edit, and view only their own seeded-location automobile draft.
