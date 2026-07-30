# Production Launch Checklist

## Product and policy

- [ ] Phase 1A scope signed off; Phase 1B/later clearly excluded
- [ ] Terms of service published and version captured on submission
- [ ] Privacy policy published
- [ ] Refund policy approved and matches implementation
- [ ] Prohibited-items policy approved and mapped to moderation reasons
- [ ] Communications/phone consent copy approved
- [ ] Contact/reporting/support paths staffed
- [ ] Community Board inclusion/exclusion communicated

## Brand and content

- [ ] Verified brand source manifest complete
- [ ] Approved logo/font/color assets used
- [ ] Mobile/desktop brand-parity review approved
- [ ] Empty states, help text, emails, and error copy reviewed
- [ ] No test/placeholder content or unverified tokens remain

## Identity and security

- [ ] Staff MFA enforced
- [ ] Staff groups/permissions tested with real role accounts
- [ ] Signup/login/reset/verification rate limits verified
- [ ] Admin URL/access and audit behavior reviewed
- [ ] Security review findings resolved or formally accepted
- [ ] Dependency audit clean at approved severity threshold
- [ ] CSP/cookies/HSTS/host/proxy settings verified
- [ ] PII/log-redaction review complete

## Listings, media, and moderation

- [ ] All launch vertical forms and filters approved
- [ ] Required-field/photo exceptions approved
- [ ] Direct upload, processing, EXIF stripping, and cleanup verified
- [ ] Moderation queue, reasons, escalation, suspend/restore tested
- [ ] Moderator training complete
- [ ] Material-edit and renewal rules tested
- [ ] Expiration and sold/archive behavior tested

## Payments

- [ ] Correct production Stripe account and products/prices mapped
- [ ] Test and live keys/webhook secrets separated
- [ ] Webhook endpoint verified and replay tested
- [ ] Duplicate/out-of-order/async events tested
- [ ] Refund/support/reconciliation workflow rehearsed
- [ ] Finance access and reporting approved
- [ ] Chargeback/dispute owner identified

## Search, SEO, and accessibility

- [ ] State/county default/toggle behavior approved
- [ ] Canonical lowercase routes and redirects tested
- [ ] Visibility matrix passes across browse/detail/sitemap/favorites
- [ ] Query plans tested with representative inventory
- [ ] Sitemap/robots/noindex behavior verified
- [ ] Keyboard and screen-reader critical flows tested
- [ ] Contrast, focus, errors, touch targets, and reduced motion reviewed
- [ ] Performance budget met for key pages

## AWS and operations

- [ ] Production ECS web/worker use approved image digest
- [ ] Explicit migration task completed successfully
- [ ] RDS private/encrypted/backups/PITR/deletion protection verified
- [ ] Restore exercise completed
- [ ] S3 Block Public Access and lifecycle rules verified
- [ ] SES authentication, bounce, complaint, and suppression handling verified
- [ ] Secrets Manager/IAM least privilege reviewed
- [ ] Route 53/ACM and certificate renewal ownership verified
- [ ] CloudWatch dashboards and alert destinations tested
- [ ] Outbox, webhook, expiration, media, and email alerts tested
- [ ] Rollback and incident communication plan rehearsed

## Inventory and rollout

- [ ] State/county/category/product/reference seeds verified
- [ ] Potter/Randall inventory plan complete
- [ ] Representative active inventory approved
- [ ] County-site navigation integration tested independently
- [ ] Analytics events/dashboards validated
- [ ] Launch window and decision owner identified
- [ ] Post-launch monitoring coverage scheduled
- [ ] Rollback/hold criteria documented

## Sign-off

| Area | Owner | Date | Result/notes |
|---|---|---|---|
| Product |  |  |  |
| Legal/policy |  |  |  |
| Engineering |  |  |  |
| Security |  |  |  |
| Operations |  |  |  |
| Moderation/support |  |  |  |
| Finance/payments |  |  |  |
| Brand/content |  |  |  |
