# Security and Privacy Baseline

## Security posture

This is a public marketplace handling accounts, phone numbers, payments, user-generated content, staff moderation, and uploads. Security requirements are feature requirements, not a final hardening phase.

## Authentication and accounts

- Custom user model from the first migration.
- Email normalization and unique account policy.
- Strong password validators and Argon2 preferred.
- Email verification policy documented separately from phone verification.
- Rate limit login, password reset, signup, verification, upload authorization, and report endpoints.
- Rotate sessions on login and sensitive account changes.
- Staff/admin accounts require MFA before production launch.
- Staff groups use least privilege; `is_staff` is not sufficient authorization.
- Account suspension invalidates or restricts sessions according to an explicit service.

## Object authorization

Every mutable endpoint verifies both role and object ownership/state. Never rely on hidden form fields, route obscurity, or template visibility.

Examples:

- only the listing owner or authorized staff can edit a draft
- an owner cannot edit a listing into an arbitrary status
- favorites are scoped to the current user
- upload sessions are bound to user and listing
- staff finance data requires separate permissions

## CSRF, XSS, and templates

- Use Django CSRF protection on all state-changing browser requests.
- Keep auto-escaping enabled.
- Never mark user content safe.
- Sanitize or restrict any approved rich text; plain text is preferred for MVP.
- Production does not currently configure a Content Security Policy; before a
  restrictive policy is activated, include
  `frame-src https://www.google.com` while the public listing map iframe is
  enabled, or remove that iframe. Avoid inline scripts.
- Set secure cookie, HSTS, proxy SSL, host, referrer, and frame settings in production.
- Run `manage.py check --deploy` in CI and deployment checks.

## User-generated text

- Bound field lengths at form and database layers.
- Normalize whitespace where appropriate without altering material claims.
- Protect logs and admin pages from control-character/log injection.
- Detect obvious personal contact information only when the product policy requires it; do not overpromise perfect redaction.
- Prohibited content policy and moderator escalation remain human-governed.

## Image uploads

- Prefer presigned S3 uploads to a private staging prefix.
- Server chooses object key, allowed MIME types, maximum bytes, upload count, and expiration.
- Do not trust extension or browser MIME alone.
- Finalization verifies object ownership, size, checksum where available, and decodes with a supported image library.
- Strip metadata, including EXIF/GPS, when producing public derivatives.
- Re-encode public derivatives rather than serving arbitrary original bytes.
- Limit dimensions and decompression risk.
- Keep originals private or delete them according to retention policy.
- Use separate staging and public/processed prefixes and restrictive bucket policies.
- Report processing failures without exposing internal storage details.

## Stripe

- Server owns prices and product eligibility.
- Verify webhook signatures against the exact raw body.
- Store and deduplicate provider event IDs.
- Use idempotency keys for outbound Stripe creation/refund calls.
- Never place secret keys in browser code, repository files, logs, or screenshots.
- Avoid storing card data; use Stripe-hosted surfaces.

## Phone verification and SMS

- Store normalized E.164 numbers.
- Separate verification consent from marketing/alert consent.
- Rate limit by account, phone, IP/device signals, and time window as appropriate.
- Do not reveal whether another account owns a phone number.
- Define re-verification when a number changes or risk is detected.
- Provider credentials live in Secrets Manager.

## Privacy and PII

Classify at least:

- account email and phone
- private address/VIN/serial fields
- IP and device/security logs
- payment references
- moderation notes and reports
- message content in Phase 1B

For each class define:

- collection purpose
- user/staff visibility
- encryption/access expectations
- logging redaction
- retention/deletion schedule
- export/correction process

Public listing location must support general-area display when exact addresses are private.

Public listing detail includes a lazy Google Maps iframe and external Google
Maps fallback links. The iframe sends only the privacy-safe presenter map
query, uses `referrerpolicy="no-referrer"`, and has no API key or map script.
Exact Home/Rental street, unit, and postal data can reach Google only after the
seller explicitly opted into public address display; private addresses,
coordinates, and general-area free text never form map queries.

## Logging

Use structured logs with request/correlation IDs. Never log:

- passwords or one-time codes
- Stripe secrets/signatures
- full webhook payloads by default
- full phone numbers where masking suffices
- private VIN/address fields
- session cookies or authorization headers

Security-relevant events should be distinct from ordinary application errors.

## Database and infrastructure

- RDS is private, encrypted, backed up, and not reachable from the public internet.
- Least-privilege task roles; avoid long-lived AWS keys in CI by using OIDC.
- Separate environments/accounts or strong environment boundaries.
- S3 Block Public Access remains enabled; CloudFront/OAC or controlled asset access provides delivery.
- Secrets rotate through AWS-managed mechanisms and deployment procedures.
- Enable deletion protection and point-in-time recovery for production.
- Restore tests are scheduled, not assumed.

## Abuse and availability

- Bound expensive searches and page sizes.
- Rate limit account and content-creation actions.
- Add bot/WAF controls based on observed abuse.
- Avoid synchronous fan-out email or image processing in requests.
- Use timeouts and retries with jitter for external services.
- Circuit-break or degrade non-critical integrations rather than blocking all browsing.

## Security review triggers

Run `/security-review` for:

- authentication/account changes
- new public endpoints or permissions
- uploads/media changes
- Stripe/payment/refund changes
- admin/staff tools
- contact/messaging/reporting
- new PII fields
- infrastructure/network changes
- dependency major upgrades
