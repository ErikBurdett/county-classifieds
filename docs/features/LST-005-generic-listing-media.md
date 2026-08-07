# Feature Specification: LST-005 — Generic private listing media

**Status:** Implemented locally; production storage incomplete  
**Milestone:** M4  
**Decision:** DEC-102 accepted 2026-07-23 — there is no universal photo minimum.

## Scope
- Image upload, validation, re-encoding, small rendition, ordering, deletion,
  and owner-only delivery for every editable listing, including typed, generic,
  and In Search Of/Wanted posts. Images remain private while a listing is draft
  or in review; a published listing returns to moderation after an image change.
- The unified Create Listing, Create In Search Of, and Edit Listing forms accept
  one or more optional image files alongside listing fields. The listing is saved
  first, then each selected file is finalized through the same media service as
  the owner image panel; a rejected file leaves the saved draft available for a
  retry and is reported through the normal message system.
- `ListingImage` and bounded, expiring `UploadSession` records. Files are
  accepted only after server-side byte, signature/decoder, format, and dimension
  checks; accepted JPEGs are re-encoded without EXIF/GPS.
- Supplemental `ListingVideo` records for every listing vertical/category. The
  owner-only media panel accepts MP4 and WebM files up to 100 MB after
  server-side container-signature validation. Videos are retained in their
  accepted source format: no FFmpeg processing, transcoding, or poster-image
  generation is performed.
- `ListingMediaPolicy` targets exactly one `ListingKind` or `Category`. Category
  overrides take precedence; no policy means required count zero and a technical
  maximum of 12. Required count is informational until M5 submission.
- DEBUG uses local `MEDIA_ROOT`; production leaves media disabled until a
  reviewed private object-storage adapter is configured.

## Non-goals
- S3 credentials or presigned/direct remote uploads. Public rendering of
  processed media is now provided by the shared public listing selector; this
  spec's private-draft media boundary remains unchanged.
- Video-derived images, automatic transcoding, duration extraction, and video
  requirements. Existing image policy still determines required listing images,
  and images remain the only media shown on listing cards.

## Security and operations
- Every media mutation locks the listing and verifies draft ownership. Other
  sellers receive 404 from private routes. Served files use `private, no-store`
  and `X-Robots-Tag: noindex`.
- Video files are private to their owner and authorized moderators until the
  associated listing is public and that individual video is approved. Public
  video responses resolve through the published-listing selector and serve
  only approved, ready records.
- Run `make cleanup-listing-media` periodically. It expires unused sessions and
  removes old unreferenced staging files; reruns are safe.
- Rollback is a forward fix: disable `LISTING_MEDIA_ENABLED`; private records
  and files remain available for controlled cleanup.

## Moderation review

- Storage readiness is separate from moderation. Newly uploaded images are
  pending until a moderator approves or rejects them.
- Pending and rejected images remain available only to their owner and
  authorized staff. Public cards, detail pages, social metadata, and public
  image delivery use approved images only.
- Videos use the same independent `pending|approved|rejected` moderation
  lifecycle. A moderator must decide every pending image and video before
  recording a listing outcome. Approved videos render only on the public
  listing-detail gallery; image cards and the image minimum remain unchanged.
- A positive listing outcome requires the category image minimum to be approved.
  If the minimum is not met, the listing is returned for changes.
- A material edit preserves approval of unchanged existing images; newly
  uploaded or replaced images are reviewed with the new submission.
- Adding or deleting a video on a published listing is a material edit and
  returns the listing to review. Existing approved videos retain their
  decision; each newly uploaded video begins pending review.
