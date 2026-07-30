# Configuration Contract

## Principles

- Configuration enters through environment variables or AWS-managed secret injection.
- Production must fail closed when a required setting is missing.
- Secrets never live in Git, images, task definitions in plaintext, logs, screenshots, or support tickets.
- Staging and production use separate databases, buckets/prefixes, Stripe modes/secrets, email configuration, and hostnames.
- A setting is not added until its owner, sensitivity, default behavior, and validation are documented.

## Foundation variables

| Variable | Local | Production | Sensitive | Purpose |
|---|---:|---:|---:|---|
| `DJANGO_SETTINGS_MODULE` | default/local | required by process | No | Select settings module |
| `DJANGO_SECRET_KEY` | safe local value | Required | Yes | Django cryptographic signing |
| `DJANGO_ALLOWED_HOSTS` | localhost values | Required | No | Host-header allowlist |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | localhost origin | Required | No | Trusted HTTPS origins |
| `DATABASE_URL` | local PostgreSQL | Required | Yes | Database connection |
| `DATABASE_SSL_REQUIRE` | `false` | normally `true` | No | Enforce database TLS |
| `DJANGO_LOG_LEVEL` | `INFO` | configured | No | Application log level |
| `AWS_REGION` | blank | Required | No | AWS service region |
| `AWS_STORAGE_BUCKET_NAME` | blank | Required | No | Private marketplace media bucket |
| `EMAIL_HOST` | blank | Required | No | SES SMTP endpoint |
| `EMAIL_PORT` | `587` | Configured | No | SMTP port |
| `EMAIL_HOST_USER` | blank | Required | Yes | SES SMTP username injected from Secrets Manager |
| `EMAIL_HOST_PASSWORD` | blank | Required | Yes | SES SMTP password injected from Secrets Manager |
| `EMAIL_TIMEOUT` | `10` | Configured | No | SMTP timeout seconds |
| `SES_FROM_EMAIL` | blank | Required | No | Verified sender identity |
| `STRIPE_SECRET_KEY` | blank | Required at M6 | Yes | Server-side Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | blank | Required at M6 | Yes | Webhook signature verification |

## Production storage and task injection

- Production uses `storages.backends.s3.S3Storage` for listing media with
  signed/private access; local and test use their own storage backends.
- `LISTING_MEDIA_ENABLED` is enabled only in production after both the bucket
  and task role configuration are present.
- `DJANGO_SECRET_KEY`, `DATABASE_URL`, `EMAIL_HOST_USER`, and
  `EMAIL_HOST_PASSWORD` are ECS Secrets Manager injection values. They must not
  be supplied from a task-definition literal, image, `.env` file, or GitHub
  secret value.
- `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` are required
  non-empty production lists, not merely optional variables.

## Variables added by later milestones

Document these before implementation rather than inventing names ad hoc:

- phone-verification provider credentials, sender/service IDs, rate-limit policy version
- S3 staging/processed prefixes, CloudFront domain, upload size/count limits
- Stripe product/price mapping by environment
- outbox worker batch/lease/retry settings
- EventBridge schedule identifiers
- error-monitoring DSN/environment/release
- analytics identifiers and consent mode
- feature flags with owner, default, removal date, and environment values

## Validation and startup

- Base/local settings may provide safe development defaults.
- Production settings use explicit `required()` validation for essential values.
- `python src/manage.py check --deploy --settings=config.settings.production` is a CI/release gate with placeholder non-secret values.
- Readiness checks test bounded essential dependencies only; they must not expose secret values or private failure details.
- The container entrypoint does not run migrations. A release task receives the same configuration and image digest as the web/worker tasks.
