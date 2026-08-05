# LST-012 — Listing fulfillment availability

**Status:** Implemented locally  
**Last updated:** 2026-08-04

## Behavior

Every listing workflow exposes three optional, independent seller declarations:
**Available for pickup**, **Delivery available**, and **Shipping available**.
They are stored on the shared `Listing` aggregate, so they apply to offer and
Wanted listings across typed and generic categories. They are not a promise of
carrier service, a checkout/shipping-rate feature, or buyer/seller messaging.

Selected methods render as a safe public listing fact after publication and are
visible to the owner before publication. A material edit follows the existing
listing moderation policy.

## Data and verification

`listings.0021_listing_available_for_pickup_and_more` adds three non-null
boolean fields with `False` defaults; no backfill is needed. Unified, Auto, and
property forms cover the common workflow paths. Regression tests confirm the
fields remain optional and available to those workflows.
