# Product Charter

## Source status

The source document is an initial AI-assisted product conversation from a non-technical stakeholder. It expresses desired outcomes, examples, pricing ideas, and launch priorities. It does not define complete acceptance criteria, legal policy, operational staffing, data retention, security controls, or integration contracts.

Engineering must preserve the stakeholder’s terminology and intent while recording every added assumption as one of:

- **Accepted product decision** — approved and recorded in an ADR or decision log.
- **Provisional engineering default** — selected to unblock design and explicitly open to change.
- **Deferred decision** — not needed for the current milestone.

## Vision

Create a media-company-owned regional classifieds marketplace that outperforms generic free bulletin boards in its markets through structured listings, moderation, seller verification, high-quality presentation, and a trusted CountyPost brand relationship.

## Product principles

1. **Quality over volume.** Empty fields, low-quality photos, spam, and prohibited items are rejected rather than accepted to inflate inventory.
2. **One network marketplace.** Counties filter one shared marketplace; they are not separate applications.
3. **Statewide value on day one.** Statewide results are the default so thin counties inherit broader inventory.
4. **Structured verticals.** Every vertical has fields and filters appropriate to the item being sold or leased.
5. **Trust is a workflow.** Verification, moderation, audit history, clear policies, and support operations are first-class product work.
6. **Independent operations.** Marketplace releases and incidents must not take down CountyPost news sites.
7. **Progressive scope.** Messaging, ratings, SMS, dealers, and advanced search do not enter MVP accidentally.

## Primary users

- Casual private sellers
- Buyers browsing within a county or statewide
- Property owners and brokers
- Farmers and ranchers
- Equipment and vehicle sellers
- Community organizers posting time-limited events
- Moderators, support staff, finance staff, and marketplace administrators

## MVP goals

- A seller can create a verified account, complete a structured listing, upload approved photos, pay when required, submit for moderation, and manage the listing through expiration or sale.
- A moderator can review, approve, reject, request changes, suspend, and audit listings without direct database access.
- A buyer can browse state or county scope, filter by vertical fields, search, sort, open a canonical listing page, and favorite an active listing.
- Finance and support staff can reconcile an order to a listing and a Stripe event without reading application logs.
- Operations can deploy, roll back, monitor, restore, and expire listings using documented procedures.

## Success measures to instrument

No target values are invented here. Product owners must set targets after baseline data exists.

- Listing completion rate
- Payment completion rate
- Moderation approval/rejection/change-request rate
- Median moderation age
- Time from draft creation to active publication
- Search-to-detail and detail-to-contact intent conversion
- Favorite rate
- Renewal rate
- Expiration and sold-close rate
- Refund and chargeback rate
- Spam, duplicate, scam, and prohibited-item report rate
- Email delivery and alert engagement
- County and vertical inventory depth
- Availability, latency, error rate, and background-job lag

## Explicit non-goals for Phase 1A

- Buyer-to-seller payments or escrow
- Stripe Connect or seller payouts
- Native mobile applications
- Radius/geospatial search
- Dealer subscriptions or bulk imports
- Seller ratings
- In-platform messaging
- SMS alerts
- Separate services per county or vertical
- Elasticsearch/OpenSearch
- React single-page application
