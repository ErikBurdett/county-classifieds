# AWS Deployment Architecture

## Objective

Deploy the marketplace independently from CountyPost news sites with the smallest operational surface that still supports safe production practices.

## Recommended topology

```text
Internet
  |
Route 53: market.thecountypost.com
  |
ACM certificate
  |
ECS Express Mode public HTTPS service / ALB
  |
Django web tasks (Fargate)
  |------------------------|
  |                        |
RDS PostgreSQL        S3 media bucket ---> CloudFront (optional/expected for media)
  |
Django worker tasks (same image, different command)

SES               Stripe             Secrets Manager
  ^                  |                      |
  |                  v                      v
Outbox worker <--- webhook route       ECS task injection

EventBridge Scheduler ---> ECS one-off tasks / scheduled management commands
CloudWatch Logs/Metrics/Alarms cover all components
```

## Environments

Use at least:

- local
- staging
- production

Staging uses separate Stripe test-mode configuration, S3 prefixes/buckets, database, secrets, email behavior, and hostname. Production data never copies into lower environments without an approved sanitized process.

## Container image

One image contains application code and static assets. Commands vary by workload:

```text
web:    gunicorn config.wsgi:application
worker: python manage.py process_outbox
job:    python manage.py expire_listings
migrate: python manage.py migrate --noinput
```

Do not run migrations in the ordinary web container entrypoint. Multiple starting tasks can race and a migration failure should not create a restart loop.

## ECS Express Mode

Use Express Mode for the stateless public web service because it provisions sensible Fargate, HTTPS/load-balancing, autoscaling, networking, and monitoring defaults while retaining access to underlying resources.

The worker may be another ECS service using the same image. Scheduled and deployment commands run as one-off tasks. Confirm the selected Express Mode/IaC feature support in the target AWS region during the infrastructure milestone.

## RDS PostgreSQL

Recommended baseline:

- PostgreSQL 18 current supported minor version
- private subnets/security groups
- encrypted storage
- automated backups and point-in-time recovery
- deletion protection in production
- performance insights/monitoring appropriate to the environment
- Multi-AZ decision based on accepted availability requirements
- controlled maintenance/upgrade window

Application connections use TLS and bounded persistent connections. Size the Django worker count against the database connection budget; do not let autoscaling exceed it.

## S3 and media

- Block Public Access enabled.
- Browser uploads use short-lived presigned authorization to a private staging prefix.
- Processor creates sanitized derivatives under a processed prefix.
- Public delivery uses CloudFront with Origin Access Control or another approved controlled pattern.
- Lifecycle rules remove abandoned staging uploads and old private originals according to policy.
- Object keys contain generated IDs, not user-supplied filenames or personal information.

## Static assets

WhiteNoise with manifest/compressed storage is the initial simplest option. Static files are built/collected into the image and receive immutable cache headers. Move static assets to S3/CloudFront only if operational or performance needs justify it.

## Email

SES handles transactional mail. Configure:

- verified sending domain
- SPF, DKIM, and DMARC alignment
- bounce/complaint events
- suppression handling
- environment-safe recipient behavior
- template/version tracking in application code

Marketing and saved-search consent are separate from essential account/payment/moderation mail.

## Secrets

Secrets Manager holds:

- Django secret key
- database credentials or connection secret
- Stripe keys and webhook secrets
- phone provider credentials
- Sentry DSN where treated as secret
- email/provider configuration where needed

Use ECS task roles and secret injection. Do not store production `.env` files in S3, GitHub, container images, or developer machines.

## CI/CD

Recommended flow:

1. pull request runs lint, type, tests, migration check, security audit, and build
2. merge builds one immutable image and pushes to ECR
3. deploy image to staging
4. run one-off migration task
5. run smoke tests
6. require production approval
7. run production migration task
8. update web/worker services to the same image digest
9. run production smoke tests and monitor alarms

Use GitHub Actions OIDC to assume a least-privilege deployment role; avoid static AWS access keys.

## Migration safety

Use expand/contract:

- release A adds nullable/new structures and dual-compatible code
- backfill in bounded restartable jobs
- release B switches reads/writes
- release C removes old structures after verification

Every release identifies whether code rollback remains compatible with the migrated schema.

## Health checks

- `/health/live/`: process is running; no external dependencies
- `/health/ready/`: bounded database readiness and essential configuration

Do not call Stripe/S3/SES from the load balancer health endpoint.

## Observability

- JSON logs to stdout/CloudWatch
- request/correlation IDs
- alarms for 5xx, target health, latency, task restarts, CPU/memory, DB capacity, outbox lag, webhook failures, scheduled-job failures, and email/provider issues
- deployment markers/releases in error monitoring

## Backup and recovery

Document and test:

- RDS point-in-time restore
- S3 versioning/lifecycle recovery policy if enabled
- secret recovery/rotation
- redeployment from an immutable image digest
- DNS/certificate ownership
- target recovery objectives approved by product/operations

A backup is not considered reliable until a restore exercise succeeds.
