# M11: Production infrastructure, CI/CD, and operations

## Problem and scope

The marketplace needs an independently deployable AWS baseline with an explicit
recovery posture, immutable application releases, and operational procedures.
This slice implements the Terraform and CI/CD foundation only. It does not
provision an AWS account, DNS, certificates, SES sending identities, production
secrets, or a live environment.

## Decisions and non-goals

- Accepted recovery target: RTO 4 hours and RPO 24 hours.
- Accepted database posture: encrypted single-AZ RDS PostgreSQL with tested
  automated backups and restore exercises.
- Accepted IaC tool: Terraform (ADR 0017).
- No automatic production deployment, static AWS credentials, secret values,
  SES identities, Route 53 records, ACM validation, or production domains are
  introduced.
- CloudFront is optional. When enabled it reaches only `processed/` media by
  Origin Access Control; S3 remains private.

## Architecture and configuration boundary

```text
GitHub protected environment + OIDC
  -> Terraform remote state / ECR / ECS Fargate
  -> ALB -> web task (immutable digest)
            worker task (same digest)
            operations task (migrate/scheduled commands, same digest)
  -> private RDS PostgreSQL (single AZ)
  -> private S3 media [-> optional CloudFront OAC]
  -> CloudWatch Logs, alarms, dashboard
  -> EventBridge -> operations task
```

Every production task receives configuration through normal environment
variables or ECS Secrets Manager injection. `DJANGO_SECRET_KEY`, `DATABASE_URL`,
and SES SMTP credentials are references to Secrets Manager values. Django
rejects missing host/CSRF, database, storage, and SMTP configuration. Production
media uses private S3 storage with signed URLs; it never uses container-local
storage.

## State and migration impact

There are no Django database migrations. Terraform state is external and must
be encrypted, locked, and separated per environment. The RDS admin password is
RDS-managed. The application database URL is a separate secret reference and
must be rotated/reconciled through the secrets procedure.

## Security and privacy

- RDS has no public IP and permits port 5432 only from ECS tasks.
- S3 blocks all public access, enables versioning/encryption, and expires
  abandoned staging objects.
- Task execution can read only declared secret references. Task roles access
  only media prefixes needed by the application.
- GitHub deployment credentials use short-lived OIDC. The assumed role's
  trust/policy must restrict repository, branch/environment, and the Terraform
  resource set before first use.
- SES sender verification, DKIM/SPF/DMARC, bounce/complaint handling, and
  recipient-safety policy remain an external pre-deploy checklist.

## Observability

The foundation creates ECS log retention, an operations dashboard, unhealthy
target and RDS CPU alarms, and optional delivery to an existing alarm SNS topic.
Before go-live, the operations owner must add/review alarms for target 5xx and
latency, task restarts/CPU/memory, RDS storage/connections, outbox oldest age,
payment webhook failures, and each scheduled command failure. Do not invent
application metric names: wire them after structured log/metric names are
reviewed.

## Rollout and rollback

1. Validate Terraform locally/CI, then create reviewed staging configuration.
2. Apply staging manually through protected GitHub environment approval.
3. Push an immutable image, run one-off migrations, then update web and worker
   to the same digest.
4. Smoke-test readiness, media, email-safe flow, worker, schedules, logs, and
   alarm delivery.
5. Capture the prior digest and migration compatibility statement before
   production promotion.

Rollback uses the previous known-good digest for both services only when the
schema remains compatible. Otherwise stop workers/schedules and make a forward
fix. Restoring RDS is a separate recovery procedure, not an application
rollback.

## Acceptance criteria

- Terraform formatting and offline validation run in CI.
- A protected manual OIDC workflow accepts only an immutable image digest.
- Web, worker, migration, and scheduled command definitions use the same image
  input and secret/configuration boundary.
- No committed identifier, hostname, secret, or cloud credential is required.
- A staging restore exercise and migration/rollback rehearsal complete before
  production use.
