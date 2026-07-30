# ADR-0019: Generic listing county distribution

**Status:** Accepted 2026-07-23

Generic listings use the shared `Listing` aggregate with a bounded `GenericListingDetails` one-to-one row. `Listing.county` remains the one canonical primary county and `ListingCountyPlacement` models optional additional public county scope, rather than duplicating listings.

County candidates are selected manually from an offline, versioned HUD USPS ZIP-County Crosswalk import keyed by county FIPS. The application makes no runtime network request and does not treat a candidate as postal-delivery confirmation. Alternate county detail URLs redirect to the primary canonical URL while county browse may surface the selected placement.

For the local demo only, item asking-price mode is independent from a server-owned $10 primary plus $5 additional-county quote. Quote snapshots are durable but generic moderation does not await an unimplemented payment path.
