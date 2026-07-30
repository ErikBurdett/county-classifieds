---
name: build-listing-vertical
description: Add one structured marketplace vertical end-to-end using typed detail data, forms, filters, moderation, and tests.
argument-hint: "<vertical name and accepted spec path>"
disable-model-invocation: true
---

# Build Listing Vertical

Implement a single approved vertical at a time. Do not create a generic EAV framework.

## Required discovery

Read the feature spec, `docs/02-DOMAIN-MODEL.md`, listing lifecycle, URL/search design, moderation rules, and the existing vertical registry/pattern. Confirm approved required fields and subcategories; do not infer missing stakeholder policy.

## Vertical slice

Implement, as applicable:

- stable vertical/category identifiers and display metadata
- explicit typed one-to-one detail model
- database constraints and useful indexes
- create/edit form step(s) with server-side validation
- detail rendering through a structured presentation adapter
- typed browse filter form and selector additions
- admin/moderation field presentation
- seeded reference values where approved
- schema, service, form, selector, template, and integration tests

## Guardrails

- Shared fields remain on `Listing`; do not duplicate price/location/title/status.
- Frequently queried fields use typed columns, not JSON.
- Required fields can vary by listing type. Do not force marketplace-photo/price rules onto Community Board or Wanted listings without an accepted rule.
- Do not expose private fields such as VIN.
- All public queries use public visibility policy.
- Editing an active listing follows the approved material-change/re-moderation policy.
- Keep the category registry explicit; avoid metaprogramming that makes migrations and forms opaque.

## Verify

Test draft save, validation errors, payment/moderation transition eligibility, active detail rendering, filters/ranges/sorting, permissions, invalid vertical combinations, and query behavior.

## Output

Summarize the vertical contract, schema/migration, forms/filters, public/admin rendering, tests, and any remaining policy gaps.
