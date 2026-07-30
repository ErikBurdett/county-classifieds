# Feature Specification: LST-005 — Generic private listing media

**Status:** Implemented locally; production storage incomplete  
**Milestone:** M4  
**Decision:** DEC-102 accepted 2026-07-23 — there is no universal photo minimum.

## Scope
- Private draft image upload, validation, re-encoding, small rendition, ordering,
  deletion, and owner-only delivery for every existing typed draft.
- `ListingImage` and bounded, expiring `UploadSession` records. Files are
  accepted only after server-side byte, signature/decoder, format, and dimension
  checks; accepted JPEGs are re-encoded without EXIF/GPS.
- `ListingMediaPolicy` targets exactly one `ListingKind` or `Category`. Category
  overrides take precedence; no policy means required count zero and a technical
  maximum of 12. Required count is informational until M5 submission.
- DEBUG uses local `MEDIA_ROOT`; production leaves media disabled until a
  reviewed private object-storage adapter is configured.

## Non-goals
- S3 credentials or presigned/direct remote uploads. Public rendering of
  processed media is now provided by the shared public listing selector; this
  spec's private-draft media boundary remains unchanged.

## Security and operations
- Every media mutation locks the listing and verifies draft ownership. Other
  sellers receive 404 from private routes. Served files use `private, no-store`
  and `X-Robots-Tag: noindex`.
- Run `make cleanup-listing-media` periodically. It expires unused sessions and
  removes old unreferenced staging files; reruns are safe.
- Rollback is a forward fix: disable `LISTING_MEDIA_ENABLED`; private records
  and files remain available for controlled cleanup.
