# MVP Backlog

This is the original issue map. Items are not a statement of current status:
implemented local slices are recorded in their feature specifications,
`dev-report.md`, and `VALIDATION.md`; unresolved launch work remains in
`docs/14-OPEN-DECISIONS.md` and the roadmap.

## Foundation (`FND`)

- **FND-001** Initialize Django 5.2 LTS project with Python 3.13 and `uv`.
- **FND-002** Add split settings and typed environment parsing.
- **FND-003** Create custom user before first migration.
- **FND-004** Add PostgreSQL Compose and local email capture.
- **FND-005** Add structured logging, request IDs, live/readiness endpoints.
- **FND-006** Add Ruff, mypy/django-stubs, pytest, coverage, and pre-commit.
- **FND-007** Add GitHub Actions CI and dependency audit.
- **FND-008** Add Docker image and Makefile developer workflow.
- **FND-009** Add base template and semantic design-token files.

## Accounts (`ACC`)

- **ACC-001** Registration, login, logout, password reset.
- **ACC-002** SellerProfile and public/private representation.
- **ACC-003** Account status and audited suspension service.
- **ACC-004** PhoneVerification model/provider interface.
- **ACC-005** Verification request/check endpoints and rate limits.
- **ACC-006** Staff groups and permission seeding.
- **ACC-007** Admin MFA production requirement.

## Location/catalog (`LOC`, `CAT`)

- **LOC-001** State/County models and constraints.
- **LOC-002** Idempotent FIPS/reference import command.
- **LOC-003** Canonical state/county route resolver.
- **CAT-001** Vertical and category hierarchy.
- **CAT-002** Listing-kind eligibility rules.
- **CAT-003** ListingProduct and UpgradeProduct.
- **CAT-004** Environment-specific Stripe price mapping.

## Listings (`LST`)

- **LST-001** Common Listing model and indexes.
- **LST-002** Status history and transition policy.
- **LST-003** Seller draft create/edit flow.
- **LST-004** HomeDetails and filters contract.
- **LST-005** RentalDetails and filters contract.
- **LST-006** AutoDetails and filters contract.
- **LST-007** AgEquipmentDetails and filters contract.
- **LST-008** LivestockDetails and filters contract.
- **LST-009** PastureDetails and filters contract.
- **LST-010** Unified category-resolved listing creation/editing, including
  bounded generic profiles, broker attribution, seller tags, custom facts, and
  progressive state/county selection. Implemented locally; legacy typed routes
  remain compatibility workflows.
- **LST-011** CommunityDetails if launch scope confirms it.
- **LST-012** Draft completeness/submission validation.
- **LST-013** Seller dashboard by status.
- **LST-014** Material-edit re-moderation.
- **LST-015** Mark sold/archive.
- **LST-016** Renewal eligibility and flow.

## Media (`MED`)

- **MED-001** UploadSession and ListingImage.
- **MED-002** Presigned S3 staging upload.
- **MED-003** Finalization/authorization checks.
- **MED-004** Image validation, metadata stripping, derivatives.
- **MED-005** Image ordering and accessible upload UX.
- **MED-006** Abandoned staging cleanup.

## Moderation (`MOD`)

- **MOD-001** ModerationReason management.
- **MOD-002** Queue selector and filters.
- **MOD-003** Claim/assignment and concurrency handling.
- **MOD-004** Approve service.
- **MOD-005** Request-changes service and seller notice.
- **MOD-006** Reject service and refund-review event.
- **MOD-007** Suspend/restore/escalate.
- **MOD-008** Immutable action/audit history.
- **MOD-009** Queue metrics/dashboard.

## Billing (`BIL`)

- **BIL-001** Order and OrderLine.
- **BIL-002** Server-side product/price selection.
- **BIL-003** Stripe Checkout Session creation.
- **BIL-004** Status-only success/cancel pages.
- **BIL-005** StripeEvent persistence and signature validation.
- **BIL-006** Idempotent completion/failure handlers.
- **BIL-007** Payment-to-moderation transition.
- **BIL-008** FeaturedPlacement entitlement.
- **BIL-009** Refund primitives after policy approval.
- **BIL-010** Reconciliation staff view and replay command.

## Browse/search (`SRCH`)

- **SRCH-001** Shared public visibility selector.
- **SRCH-002** State/county context and scope toggle.
- **SRCH-003** PostgreSQL weighted public text search and state-default/county
  scope. Implemented locally; representative production query-plan evidence is
  still required.
- **SRCH-004** Typed public filter parser/forms per vertical. Implemented
  locally for supported typed presentations; tags, generic profiles, and custom
  facts remain non-filterable.
- **SRCH-005** Vertical/category browse.
- **SRCH-006** Sort and stable pagination.
- **SRCH-007** Featured row.
- **SRCH-008** Listing detail and canonical redirect.
- **SRCH-009** Query/index performance review.
- **SRCH-010** Sitemap, robots, canonical/noindex rules.

## Buyer/seller retention (`RET`)

- **RET-001** Favorite/unfavorite.
- **RET-002** Favorites page with visibility-safe behavior.
- **RET-003** Expiration reminders.
- **RET-004** Renewal confirmation and entitlement history.

## Notifications/operations (`NTF`, `OPS`)

- **OPS-001** OutboxEvent and worker leasing.
- **OPS-002** Idempotent handler registry and failure/replay commands.
- **OPS-003** Expiration batch command.
- **OPS-004** EventBridge schedule definitions.
- **NTF-001** Transactional email adapter and delivery record.
- **NTF-002** Account/verification emails.
- **NTF-003** Moderation outcome emails.
- **NTF-004** Payment/renewal emails.
- **NTF-005** Expiration reminder/expired emails.
- **NTF-006** SES bounce/complaint handling.

## UI/brand/accessibility (`UI`)

- **UI-001** Verified brand manifest and tokens.
- **UI-002** Masthead, sub-brand, navigation, footer.
- **UI-003** Listing cards and featured treatment.
- **UI-004** Filter and scope components.
- **UI-005** Listing form/progress/error system.
- **UI-006** Image gallery.
- **UI-007** Seller dashboard/status components.
- **UI-008** Accessibility audit and remediation.
- **UI-009** Mobile/performance review.

## Infrastructure/launch (`INF`, `LCH`)

- **INF-001** ECR and immutable image build.
- **INF-002** ECS Express Mode staging web service.
- **INF-003** Worker and one-off task definitions.
- **INF-004** RDS PostgreSQL and connection/secrets.
- **INF-005** S3/CloudFront media path.
- **INF-006** SES domain configuration.
- **INF-007** Route 53/ACM custom domain.
- **INF-008** GitHub Actions OIDC deployment.
- **INF-009** CloudWatch dashboards/alarms.
- **INF-010** backup/restore and rollback exercise.
- **LCH-001** Seed categories/products/counties.
- **LCH-002** Policy/legal content loaded and versioned.
- **LCH-003** Staff training and permission validation.
- **LCH-004** End-to-end staging/production smoke suite.
- **LCH-005** Load/security/accessibility sign-off.
- **LCH-006** Inventory seeding and launch checklist.
