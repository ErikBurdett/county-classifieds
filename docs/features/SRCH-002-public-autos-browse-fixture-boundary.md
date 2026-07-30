# Feature Specification: SRCH-002 — Public Browse and Demo Inventory Boundary

**Status:** Implemented locally; production scope incomplete  
**Milestone:** M7 public-browse foundation  
**Last updated:** 2026-07-23

## Outcome

Buyers can browse public listings on the home page and enabled state/county
routes and open public listing detail/media pages. The local nationwide seed
uses eight implemented typed presentations. This is controlled demo inventory,
not a production seller-posting, payment, or launch-inventory workflow.

## Scope

- Published listings are visible only when their listing, state, county, vertical,
  and category are active; state and county must also be network enabled.
- Home links enabled states and shows recent public Autos.
- State and county routes provide implemented typed GET filters and allowlisted
  sorting.
- A reusable public market finder resolves enabled state-only or state/county
  selections to canonical routes. Its request/response county choices are
  limited to the selected state; mismatched input is rejected without a route
  redirect.
- Public home and browse pages use the verified CountyPost visual tokens:
  responsive square state/county and listing card grids, a blue masthead, and
  semantic no-JavaScript navigation.
- DEBUG-only commands create the bounded four-market Autos fixture and separate
  nationwide multi-vertical demo inventory.

## Non-goals

No production provider integration, full-text/PostgreSQL search, pagination,
messaging, ratings, or private seller contact fields are added. VIN, seller
email, internal moderation data, and private addresses remain private.

## Lifecycle and security

`draft -> published` is available solely through a transactional staff/demo
service. It locks the listing and detail row and rejects incomplete Autos,
non-draft lifecycle states, inactive catalog records, and inactive or
network-disabled locations. Draft forms and services operate only on drafts;
their fields cannot set public status.

## Query and SEO boundary

Public selectors centralize visibility. Price inputs are non-negative whole USD
units converted to integer cents. Sort choices are newest, price ascending,
price descending, mileage ascending, and year descending. Canonical URLs omit
filter query strings; home and enabled directory routes are indexable.

## Migration and rollback

The additive lifecycle migration adds `published_at`, permits `draft` and
`published`, and adds browse indexes. Existing records remain drafts. Roll back
by disabling network location flags; use a forward migration to correct
published data rather than deleting inventory.

## Tests

Cover publication validation, visibility exclusions, route canonicalization,
state-only and county finder redirects, mismatched finder county rejection,
all filters/sorts, VIN omission, responsive no-JavaScript markup, deterministic
seed reruns, and e2e state/county finder navigation.
