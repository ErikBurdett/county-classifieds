# Project Blueprint

## Product statement

TheCountyPost Market is a premium regional classifieds marketplace owned by a media organization. It favors structured data, pre-publication moderation, verified sellers, and clear vertical experiences over unstructured posting volume.

It is one independently deployed application at `market.thecountypost.com` with one shared listings database. Counties are filters and routes, not separate deployments or data silos.

## Initial verticals

- Homes
- Rentals
- Autos
- Agricultural equipment
- Pasture and cattle
- Appliances and home goods
- Community Board, visually and operationally separated from paid marketplace inventory

## MVP release boundary

### Phase 1A

- State/county route resolution and scope toggle
- Marketplace account and seller profile
- Phone verification
- Structured listing creation for approved verticals
- Listing photos
- Paid listing checkout and featured upgrade
- Pre-publication moderation and audit history
- Browse, filters, sorting, and PostgreSQL search
- Seller dashboard and favorites
- Expiration, renewal, and transactional email
- Community Board if confirmed as a launch requirement
- Production deployment, backups, observability, and operational runbooks

### Phase 1B

- Saved searches and email alerts
- Weekly county digest
- Wanted/ISO listing type
- User reporting/blocking
- In-platform messaging and anti-contact-sharing controls
- More advanced moderation tools

### Later

- SMS alerts
- Seller ratings
- Dealer subscriptions and storefronts
- Bulk inventory feeds
- Radius search
- Dedicated search service
- Native mobile applications
- Vertical brand spinoffs

## Architecture summary

```text
Browser
  |
Route 53 + ACM
  |
Application Load Balancer / ECS Express Mode
  |---------------------------|
Django web service       Django worker service
  |                           |
  |------ Amazon RDS PostgreSQL
  |------ Amazon S3 listing media
  |------ Amazon SES email
  |------ Stripe Checkout/webhooks
  |------ Secrets Manager
  |------ CloudWatch logs/alarms

EventBridge Scheduler ---> one-off ECS tasks / scheduled commands
```

## Application structure

```text
src/
  config/                 # settings, root URLs, WSGI/ASGI
  apps/
    core/                 # health, common types, shared utilities
    accounts/             # custom user, seller profile, verification boundary
    locations/            # states, counties, location lookup
    catalog/              # verticals, categories, pricing products
    listings/             # listing aggregate and typed details
    media/                # upload sessions, images, processing state
    moderation/           # queue, actions, reasons, policy enforcement
    billing/              # orders, line items, Stripe events, refunds
    favorites/            # saved listing relation
    notifications/        # email templates, delivery records
    operations/           # outbox, scheduled jobs, admin utilities
  templates/
  static/
  tests/
```

Phase 1B apps are added only when their milestones begin: `saved_searches`, `messaging`, `reports`, and later `ratings` or `dealers`.

## Core coding shape

- Models enforce durable invariants and database constraints.
- Services perform state changes inside explicit transactions.
- Selectors contain reusable read/query logic.
- Forms validate user-entered data and permissions.
- Views are thin coordinators.
- Templates contain presentation logic only.
- Admin actions call the same domain services as public/internal views.
- Side effects are recorded to an outbox inside the business transaction and processed by a worker.
- Signals are avoided for core business workflows because they hide control flow.

## Data principles

- UUIDs for externally exposed records.
- Integer/FIPS identifiers may be retained for stable reference data.
- Money is stored in minor units plus a three-letter currency code.
- All mutable business records have `created_at` and `updated_at` in UTC.
- Listings are never hard-deleted during normal operations.
- Status transitions create immutable history entries.
- Stripe webhook events are stored by provider event ID and processed idempotently.
- Filtered/sorted vertical attributes are normal typed columns, not EAV rows.
- JSONB is limited to non-critical metadata that is not a primary filter or invariant.

## Frontend principles

- Server-rendered first.
- Semantic HTML and accessible native controls.
- Progressive enhancement for filters, upload progress, and admin efficiency.
- Shareable URL state for search and filtering.
- Design tokens are the only place approved brand values are encoded.
- No React SPA unless an ADR demonstrates a concrete need.

## Deployment principles

- One immutable image promotes through environments.
- Database migrations run as an explicit one-off deployment step, not on every container start.
- Web and worker use the same image with different commands.
- Static assets can be served with WhiteNoise initially; user media is never stored on the container filesystem.
- Secrets enter through AWS-managed secret injection.
- Rollback procedures account for database compatibility using expand/contract migrations.
