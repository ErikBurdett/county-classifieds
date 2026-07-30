# ADR 0017: Terraform for production infrastructure foundation

- Status: Accepted
- Date: 2026-07-23

## Context

M11 needs reviewable, repeatable AWS infrastructure while preserving the
accepted 4-hour RTO, 24-hour RPO, and single-AZ RDS decision. The prior
deployment guidance identified AWS services but did not select one IaC tool or
define a safe source-of-configuration boundary.

## Decision

Use Terraform for AWS infrastructure. The committed configuration is
variable-driven and uses no external Terraform modules. Remote-state details,
AWS account values, certificate/domain values, secret values, SES identities,
and deployment role ARNs are supplied outside Git through reviewed
environment-specific configuration.

The baseline creates a private, encrypted, single-AZ PostgreSQL instance with
automated backups and configurable deletion protection; private versioned S3
media; ECR; Fargate web/worker/operations task definitions from one immutable
image digest; CloudWatch logs/baseline alarms; EventBridge commands; and
least-privilege task roles. GitHub Actions receives AWS credentials only with
OIDC in a manually dispatched protected-environment workflow.

ECS Express Mode remains the desired web-service operating model from ADR 0007.
This foundation uses standard Fargate task/service resources because their
Terraform support is explicit. Before an Express Mode transition, verify
regional feature and Terraform support and supersede this decision if the
resource model changes.

## Consequences

- Terraform apply is intentionally blocked until a reviewer supplies an
  approved backend, VPC/subnets, ACM certificate, secret references, alarm
  owner/topic, and SES/domain configuration.
- Secrets are injected into ECS from Secrets Manager references; no secret
  plaintext appears in Terraform state inputs, task definitions, image layers,
  or GitHub Actions.
- Single-AZ RDS and one NAT gateway reduce cost but are an availability risk
  accepted only for the current 4-hour RTO. A restored database may require
  promotion/traffic changes during recovery.
- RDS automated backups and a tested restore exercise are required to meet the
  24-hour RPO; backup existence alone is not evidence of recoverability.
- Terraform is validated in CI, but no production deployment is automatic.
