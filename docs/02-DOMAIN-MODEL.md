# Domain Model

## General conventions

- Use UUID primary keys for externally addressable mutable business records.
- Use stable natural identifiers where appropriate for reference data, such as state FIPS and county FIPS.
- Store timestamps in UTC and display in the user’s relevant local timezone.
- Use `created_at` and `updated_at`; add actor and reason fields to status history rather than relying only on timestamps.
- Avoid hard deletion of listings, orders, moderation actions, Stripe events, or audit records.
- Store money as integer minor units plus ISO currency (`amount_minor`, `currency`) unless a documented reason requires decimal arithmetic.
- Add database constraints for invariants that must survive all code paths.
- Do not use a traditional EAV schema.

## Identity and seller data

### `User`

Custom user model created before the first migration.

Recommended fields:

- UUID `id`
- unique normalized email
- optional display name
- account status: active, suspended, closed
- staff flags managed by Django permissions/groups
- last login and standard Django auth fields

Do not use phone number as the primary identifier. Phone numbers change and may be recycled.

### `SellerProfile`

- one-to-one user
- immutable UUID public identifier
- public display name
- member-since derived from creation date
- nullable pointer to one approved public-content revision
- private phone and verification state

### `SellerProfileRevision`

- seller profile, pending/approved/rejected state, reviewer/note/time
- optional avatar plus bio
- optional HTTPS website, Facebook, Instagram, X, LinkedIn, and YouTube links
- only the profile's currently approved revision is public

### `PhoneVerification`

- user
- normalized E.164 phone number
- provider and provider reference
- purpose
- status
- initiated/verified/expires timestamps
- attempt and rate-limit metadata
- consent-version reference where required

Only one verified primary seller phone should be active per account unless policy explicitly allows otherwise.

## Geography

### `State`

- FIPS code
- USPS abbreviation
- name
- lowercase slug
- active flag

### `County`

- county FIPS code
- state foreign key
- county name
- lowercase slug unique within state
- optional county-seat/timezone metadata
- active/network flags

Unique constraint: `(state, slug)`.

Listings always reference both state and county. A database constraint or model validation must ensure the county belongs to the selected state.

## Catalog and pricing

### `Vertical`

A controlled record or code enum for homes, rentals, autos, ag equipment, pasture/cattle, appliances/home, and community.

### `Category`

- vertical
- optional parent category
- name and slug
- display order
- active flag
- listing-kind allowances

### `ListingProduct`

Represents a sellable posting product, not a Stripe object.

- code
- eligible vertical/category rules
- duration days
- amount minor and currency
- active-from/active-until
- free/paid flag
- moderation requirement

### `UpgradeProduct`

Featured placement and future upgrades.

- code
- duration/placement rules
- amount/currency
- active window

Application product records map to Stripe Price IDs by environment. Never hard-code Stripe IDs in business logic.

## Listing aggregate

### `Listing`

Shared fields:

- UUID `id`
- seller
- listing kind: offer, wanted, community event/sale where allowed
- vertical and category
- state, county, city
- title
- description
- price amount/currency plus price mode (`fixed`, `negotiable`, `free`, `contact`, where policy permits)
- status
- moderation state/reason summary
- public slug
- published, expires, sold, archived timestamps
- first-publication, sold, and seller-profile sold-retention timestamps
- independent pickup, delivery, and shipping availability declarations
- draft-completeness and version number
- optional public general-area text
- created/updated timestamps

Constraints and indexes:

- public slug is not the sole identifier; canonical URLs include a stable short form of the UUID.
- status/date indexes support public visibility and expiration scans.
- location/category/status compound indexes support browse queries.
- price indexes are added only for categories where range filtering is meaningful.

### Typed vertical details

Use one-to-one tables. Required filter/sort fields are normal columns.

#### `HomeDetails`

- property type
- beds, baths
- square feet
- year built
- lot size and unit
- address visibility mode
- address/general area
- commercial/investment indicators as approved

#### `RentalDetails`

- rental type
- monthly rent and deposit
- beds, baths
- available date
- pet policy
- lease term
- address visibility mode

#### `AutoDetails`

- vehicle type
- year, make, model, trim
- mileage
- title status
- VIN encrypted or access-restricted and never rendered publicly
- drivetrain/transmission/fuel if approved for filters

#### `AgEquipmentDetails`

- equipment type
- make, model, year
- powered flag and hours
- condition
- serial number only if policy permits and with restricted visibility

#### `LivestockDetails`

- species
- breed
- class
- head count
- age/weight range
- sale unit and price interpretation
- health/testing metadata only when product/legal policy defines it

#### `PastureDetails`

- acreage
- water
- fencing
- lease term
- livestock/use restrictions
- availability dates

#### `HomeGoodsDetails`

- item type
- brand
- age
- condition
- working status

#### `CommunityDetails`

- event type
- start/end timestamps
- public location
- recurrence prohibited in MVP unless explicitly implemented

A listing must have exactly one compatible detail row. Enforce compatibility through services and validation; add database-level protections where practical.

## Media

### `UploadSession`

- user/listing
- allowed content type and maximum bytes
- staging object key/prefix
- expiry
- finalized status

### `ListingImage`

- listing
- source/staging and processed S3 keys
- sort position
- content type, bytes, width, height
- checksum
- processing status
- moderation status
- created timestamp

Constraints:

- unique `(listing, sort_position)`
- maximum image count enforced transactionally
- only processed and approved images appear publicly

## Lifecycle and moderation

### `ListingStatusHistory`

- listing
- from/to status
- actor user or system identity
- reason code and optional note
- correlation/request ID
- created timestamp

Immutable after creation.

### `ModerationAction`

- listing
- optional listing version/revision
- action: approve, reject, request changes, suspend, restore, note, escalate
- moderator
- reason code
- internal note
- seller-visible explanation
- created timestamp

### `ModerationReason`

Controlled reason codes with seller-visible copy, internal guidance, severity, and active flag.

## Billing

### `Order`

- purchaser/seller
- listing
- status: draft, checkout_created, paid, failed, cancelled, refunded, partially_refunded
- amount/currency totals
- Stripe customer/session/payment references
- paid/refunded timestamps
- idempotency key

### `OrderLine`

- order
- product code and immutable description snapshot
- quantity
- unit/total amount
- product configuration snapshot

### `StripeEvent`

- unique provider event ID
- event type
- livemode
- received timestamp
- payload or secure payload reference according to retention policy
- processing status, attempts, error
- processed timestamp

### `FeaturedPlacement`

- listing
- source order line
- placement type
- starts/ends timestamps
- status

Do not represent “featured” only as a boolean on `Listing`; the paid entitlement has its own lifecycle.

## Buyer retention

### `Favorite`

- user
- listing
- created timestamp

Unique `(user, listing)`.

### Phase 1B: `SavedSearch`

Store normalized query criteria, scope, location, notification preference, and last-run cursor. Validate criteria against a versioned schema; do not store arbitrary executable query expressions.

### Phase 1B: `AlertDelivery`

Track saved search, matched listing, channel, status, provider ID, attempts, timestamps, and suppression reason. Unique constraints prevent duplicate alerts for the same match/channel.

## Future communication and trust

### Phase 1B: `Conversation` and `Message`

Conversations are tied to a listing and participants. Messages require abuse/reporting, retention, redaction policy, notification, and moderator-access decisions before implementation.

### Later: `SellerRating`

Do not create until an eligible completed-interaction workflow is defined. A rating without a transaction/interaction eligibility rule is easy to manipulate.

### `Report`

A report may be needed in Phase 1A or 1B depending on launch policy.

- reporter or anonymous session as allowed
- target listing/user/message
- reason
- description
- status and assignment
- resolution/audit history

## Operations

### `OutboxEvent`

- UUID
- event type and schema version
- aggregate type/ID
- JSON payload containing IDs and immutable facts, not sensitive full objects
- status
- available/leased/completed timestamps
- lease owner
- attempts and last error
- deduplication key where required

### `AuditEvent`

For sensitive staff and support actions not fully represented by domain history.

- actor
- action
- target type/ID
- before/after summary with sensitive-field redaction
- request/correlation ID
- timestamp

## Data deletion and retention

Account closure should deactivate identity and remove or anonymize unnecessary profile data without destroying financial, moderation, fraud-prevention, or legal records that must be retained. Exact periods require legal/product approval and belong in a retention schedule, not ad hoc model methods.
