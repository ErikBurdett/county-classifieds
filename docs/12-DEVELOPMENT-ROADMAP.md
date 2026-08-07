# Comprehensive Development Roadmap

## How to use this roadmap

Each milestone is a release-quality vertical slice with an explicit gate. Complete and stabilize a milestone before starting multiple dependent milestones. Suggested slices are intentionally small enough for focused Cursor sessions and reviewable pull requests.

Statuses to use in this file or an issue tracker:

```text
not_started | discovery | ready | in_progress | blocked | review | done
```

## Phase 0 — Product and engineering readiness

### M0-A: Decision baseline

**Objective:** Turn unresolved source material into explicit decisions before schema and workflow choices become expensive.

**Deliverables**

- P0 decisions in `docs/14-OPEN-DECISIONS.md`
- accepted/proposed ADRs
- approved MVP/Phase 1B/later boundary
- legal/policy work owners identified
- verified brand-source access plan
- provider choices or stable adapter boundaries

**Gate**

- No P0 item blocks identity, payments, moderation, or publishing.
- Stakeholders understand that ratings, messaging, SMS, and dealer accounts are not Phase 1A.
- Refund and prohibited-items policies have named owners and delivery dates before those features ship.

### M0-B: Repository and development foundation

**Objective:** Create a reproducible Django project that is safe to evolve.

**Deliverables**

- Python 3.13 and Django 5.2 LTS pinned/locked
- `src/` layout and split settings
- custom user model before first migration
- PostgreSQL Compose service and a network-free local email backend
- health endpoints
- base templates and semantic CSS token structure
- Ruff, mypy/django-stubs, pytest, coverage, pre-commit
- CI pipeline
- Docker image
- developer Makefile/scripts
- dependency update policy

**Acceptance gate**

- Fresh clone bootstrap is documented and succeeds.
- `make check` and `make test` pass.
- CI runs from a clean environment.
- production settings run `check --deploy` without unaccepted failures.
- first migration is reviewed and committed.
- no business feature code is mixed into foundation PRs.

**Suggested PR slices**

1. Project skeleton and settings.
2. Custom user and first migration.
3. Docker/Compose/local email.
4. Quality tooling and CI.
5. Base template, health, logging, and request IDs.

## Phase 1A — Launchable marketplace

### M1: Identity, seller profile, and phone-verification boundary

**Status:** partially implemented — password reset, account status, staff role
groups, security audit events, and moderated public seller profiles are
available locally; DEC-003 phone verification and DEC-101 email-verification
policy remain unresolved.

**Objective:** Establish marketplace identity and seller eligibility without coupling the system irreversibly to one provider.

**Deliverables**

- registration/login/logout/password reset
- email verification policy implementation if approved
- seller profile
- account status and suspension services
- phone-verification adapter, attempts, expiry, and rate limits
- public/private profile field separation
- staff permissions and initial groups
- account/security audit events

**Acceptance gate**

- unverified or suspended sellers cannot submit listings
- enumeration-safe signup/reset/verification behavior
- phone values normalized and private
- provider failure/retry paths tested
- staff access uses explicit permissions
- custom user model is stable before dependent migrations

**Suggested PR slices**

1. Auth pages and account policy.
2. Seller profile and public representation.
3. Phone provider interface and fake/local implementation.
4. Production provider implementation.
5. Staff groups, suspension, and audit.

### M2: Locations, catalog, products, and reference data

**Objective:** Create normalized geography and controlled marketplace taxonomy/pricing.

**Deliverables**

- State and County models with FIPS/slug constraints
- idempotent import command and source manifest
- vertical/category hierarchy
- listing kinds and eligibility rules
- listing and upgrade product models
- environment-specific Stripe price mapping boundary
- admin management with protected historical records

**Acceptance gate**

- county always belongs to state
- routes resolve canonical lowercase slugs
- adding a county requires data/config only
- import reruns safely and reports changes
- inactive categories/products cannot be newly selected
- prices are server-owned and effective-dated

### M3: Listing aggregate, typed details, and draft workflow
**Status:** implemented locally — LST-010 provides unified category-resolved
creation and editing, typed workflow reuse, bounded catalog profiles, broker
attribution, tags/custom facts, and progressive state/county selection. Production
seller eligibility and launch verification remain pending.

**Objective:** Implement structured listing creation without payments or publication yet.

**Deliverables**

- Listing common model
- typed detail tables for the approved launch verticals
- status choices and transition policy skeleton
- status history
- draft create/edit/delete-or-archive behavior
- per-vertical forms and validation
- multi-step flow or clear single-flow architecture
- seller draft dashboard
- terms/policy acceptance version capture

**Acceptance gate**

- no EAV data model
- incompatible detail rows cannot be submitted
- all filterable fields are typed
- seller object authorization is tested
- drafts cannot become active through form tampering
- wanted/community exceptions are explicit, not accidental
- model/query decisions are documented in ADRs

**Suggested vertical sequence**

1. shared listing and one representative vertical
2. autos
3. homes and rentals — private draft slice implemented
4. ag equipment — private draft slice implemented
5. livestock and pasture — private draft slice implemented
6. appliances/home — private draft slice implemented
7. community board if in launch scope

Each vertical uses `/build-listing-vertical` and includes field/filter documentation before code.

### M4: Listing media and direct S3 upload

**Objective:** Add secure listing media with image processing and moderated supplemental video.

**Deliverables**

- UploadSession and ListingImage
- presigned staging upload endpoint
- finalization service
- image validation/re-encoding/metadata stripping
- responsive derivatives and ordering
- local-development storage behavior
- cleanup of abandoned staging objects
- upload progress/error UX
- optional MP4/WebM supplemental uploads (100 MB maximum) with private serving,
  separate moderation, and approved-only public detail playback; no transcoding
  or generated posters

**Acceptance gate**

- user cannot upload to another seller’s listing
- count/size/type/dimension limits are server-controlled
- corrupt or dangerous files never become public
- public pages use processed derivatives
- EXIF/GPS is removed
- failures/retries are observable and idempotent
- required image policy is listing-kind specific

### M5: Submission and moderation
**Status:** in_progress — baseline no-payment submission, review, audit, and policy-v1 controls are implemented; queue metrics, restoration, and notifications remain deferred.

**Objective:** Establish the trusted pre-publication path.

**Deliverables**

- submission-completeness service
- moderation-first review, followed by publication or an optional payment link
- moderation queue, claim/assignment, and stale-action handling
- reason-code management
- approve/request changes/reject/escalate/suspend/restore services
- seller-visible moderation notices
- immutable action/audit history
- moderation metrics

**Acceptance gate**

- every state change calls a service and writes history
- admin cannot bypass transition validation with ordinary field edits
- concurrent reviews cannot both succeed
- internal notes never render publicly
- rejected/change-requested listings remain hidden
- reason codes and escalation rules are operationally usable

### M6: Stripe Checkout, orders, webhooks, and featured entitlements

**Objective:** Collect listing fees safely and transition paid listings only from durable payment truth.

**Deliverables**

- Order, OrderLine, StripeEvent, FeaturedPlacement
- server-side pricing/eligibility
- Checkout Session creation
- success/cancel status pages
- signed webhook endpoint
- idempotent event handlers and replay command
- approved-listing payment-to-publication transition
- staff reconciliation view
- refund-support primitives according to approved policy

**Acceptance gate**

- browser success route cannot mark paid
- duplicate/out-of-order events are safe
- amount/currency/product mismatches fail safely and alert
- Stripe event IDs are unique
- featured placement starts according to approved entitlement policy
- test/live configuration cannot cross
- all payment behavior has integration tests

### M7: Public browse, search, filters, routes, and listing detail

**Status:** implemented locally — state/county directories, shared public
visibility, multi-vertical demo browse/detail/media, canonical SEO foundations,
SRCH-003 PostgreSQL full-text/state-default county scope, and SRCH-004 typed
filters are implemented. County browse also has a bounded local-demo
county-internal-point nearby rail (DEC-114), not genuine radius search.
Production seller eligibility/payments, featured ranking policy, production
inventory policy, and representative production query-plan evidence remain deferred.

**Objective:** Deliver the buyer-facing marketplace experience.

**Deliverables**

- state/county route context
- state-default/county scope toggle
- vertical/category browse
- typed filter parsers/forms
- PostgreSQL text search
- sort/pagination
- active featured row
- listing detail and seller summary
- canonical URLs and redirects
- empty states and inventory counts
- shared public-visibility selector

**Acceptance gate**

- all public surfaces share visibility rules
- scope/filter/sort state is shareable
- no arbitrary ORM path injection
- inactive/expired/suspended inventory is excluded even if scheduler lags
- representative query plans and query counts are recorded
- mobile and keyboard use pass review

### M8: Seller management, favorites, sold/archive, and renewal

**Status:** in_progress — lifecycle schema, visibility safety, owner actions,
favorites, and the local renewal boundary are implemented; production billing and
M9 expiration scheduling remain deferred.

**Objective:** Complete essential post-publication self-service and buyer retention.

**Deliverables**

- seller dashboard by status
- listing detail actions
- mark sold/archive
- material-edit re-moderation flow
- favorites
- renewal order flow
- listing and payment history summaries
- support links

**Acceptance gate**

- owner-only actions enforced server-side
- material edits cannot remain public unreviewed
- duplicate renewal cannot grant duplicate entitlement
- favorites cannot reveal private/unpublished listing data
- sold/archive behavior matches policy and sitemap/search handling

### M9: Expiration, notifications, and background worker
**Status:** in_progress — PostgreSQL outbox, lifecycle notifications, reminder
scheduling, explicit worker commands, and local Django email delivery are
implemented; SES/EventBridge deployment remains M11 work.

**Objective:** Make time-based and external side effects reliable.

**Deliverables**

- transactional outbox model/worker
- idempotent handlers
- expiration command
- reminder scheduling
- transactional email templates
- delivery attempt records
- SES integration and local mail capture
- failed-event operations UI/commands
- EventBridge schedule definitions

**Acceptance gate**

- business transaction and event creation are atomic
- worker crash/retry cannot duplicate outcomes
- oldest outbox age is measurable and alerted
- expiration is idempotent and public visibility is safe before the job runs
- production email domain/authentication and bounce handling are configured

### M10: Brand parity, responsive UX, accessibility, and SEO

**Objective:** Bring all public and account workflows to an approved CountyPost-quality presentation.

**Deliverables**

- verified brand manifest and tokens
- masthead/sub-brand/footer
- documented components
- responsive cards, filters, forms, gallery, dashboard
- WCAG 2.2 AA review and fixes
- metadata/canonicals/sitemaps/robots
- user-initiated external map/directions privacy boundary and progressive
  enhancement for bounded public search controls
- performance/image review
- browser compatibility checklist

**Acceptance gate**

- no unverified placeholder brand values remain
- reference-versus-build evidence is approved
- keyboard and screen-reader critical flows work
- no color-only statuses
- indexed URL strategy is intentional
- core pages meet agreed performance budget on representative devices

### M11: Production infrastructure, CI/CD, and operations
**Status:** in_progress — Terraform foundation, fail-closed production storage
configuration, CI validation, manual OIDC workflow, and runbooks are
implemented; a reviewed staging account/configuration, SES/DNS/ACM setup,
restore exercise, and release rehearsal remain required.

**Objective:** Create reproducible, observable, recoverable AWS environments.

**Deliverables**

- ECR, ECS Express Mode web service, worker service/task definitions
- RDS PostgreSQL
- S3/CloudFront media path
- SES
- Route 53/ACM
- Secrets Manager and task IAM
- CloudWatch dashboards/alarms
- GitHub Actions OIDC deployment
- explicit migration task
- staging and production configuration
- backup/restore and rollback runbooks

**Acceptance gate**

- staging deployment is fully repeatable
- production secrets are not in GitHub or images
- migration/rollback procedure is release-tested
- RDS restore exercise succeeds
- web and worker deploy the same image digest
- alarms and ownership are verified
- news sites are operationally independent

### M12: Launch readiness and controlled rollout
**Status:** in_progress — local refund/consent foundations and rehearsal artifacts
are implemented; legal approval, production providers, staging rehearsal, and
staff training remain launch blockers.


**Objective:** Validate the whole system, staff, inventory, policy, and support path before public promotion.

**Deliverables**

- seeded reference/category/product data
- representative approved inventory
- moderator/support/finance training
- terms, privacy, refund, prohibited-items, reporting, and consent content
- full regression and load test
- security review and remediation
- analytics events/dashboards
- smoke-test checklist
- launch/rollback communication plan
- post-launch monitoring schedule

**Acceptance gate**

- no unresolved launch-blocking P0/P1 decision
- end-to-end flows pass in production configuration/test mode as applicable
- staff can resolve common support/moderation/payment cases
- recovery, rollback, webhook replay, and data repair are rehearsed
- inventory and empty states are acceptable in launch counties/state scope
- launch owner signs the checklist in `docs/19-LAUNCH-CHECKLIST.md`

## Phase 1B — Retention, communication, and reporting

### M13: Saved searches and email alerts

- normalized/versioned search criteria
- stored state/county scope
- matching job/cursor
- deduplicated AlertDelivery
- preferences/unsubscribe/suppression
- digest versus immediate policy

### M14: Weekly county digest

- county-specific content selection
- publication schedule/timezone
- inventory thresholds and fallback content
- email-team integration contract
- delivery analytics

### M15: Wanted/ISO listings

- per-vertical field exceptions
- price/photo policy
- search/filter treatment
- abuse controls
- expiration/pricing decision

### M16: Reporting, blocking, and moderation case management
**Status:** in_progress — public listing report intake and staff triage are
implemented locally under DEC-109; retention, blocking, evidence, and
notification policy remain deferred.

- in-product reports
- assignment/status/escalation
- user blocking where relevant
- evidence and notification policy

### M17: In-platform messaging

Do not begin until product/legal decisions cover contact sharing, spam, blocking, reporting, attachments, retention, staff access, notifications, deletion, and safety. Build messaging as its own domain module over listing/user IDs.

## Later roadmap

### Ratings

Requires an eligible-interaction/completion signal, appeal/removal policy, anti-retaliation controls, and moderation.

### Dealers/brokers

Requires plan catalog, subscription billing, limits, staff accounts, storefronts, inventory import, reporting, compliance, and support operations.

### Advanced search/radius

Requires location precision/privacy decisions, geospatial model, UX, and measured PostgreSQL limitations before OpenSearch or PostGIS expansion.

## Release train guidance

A milestone may ship behind a feature flag when:

- schema is backward compatible
- hidden code does not change public/payment behavior unexpectedly
- the flag has owner, default, environment values, and removal date
- tests cover both states while the flag exists

Do not accumulate permanent flags or use flags to bypass policy decisions.
