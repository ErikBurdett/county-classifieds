---
name: prepare-aws-deployment
description: Design or implement a reviewable AWS deployment slice for the Django marketplace using the approved ECS/RDS/S3 architecture.
argument-hint: "<environment or infrastructure slice>"
disable-model-invocation: true
---

# Prepare AWS Deployment

## Read first

- `docs/10-AWS-DEPLOYMENT.md`
- `docs/11-OBSERVABILITY-RUNBOOK.md`
- `docs/19-LAUNCH-CHECKLIST.md`
- ADRs for deployment, database, media, and background work
- current Dockerfile, CI, settings, IaC, and account/environment conventions

## Architecture baseline

- ECS Express Mode web service
- same immutable image for web, worker, and scheduled management commands
- private RDS PostgreSQL
- S3 staging/processed media
- SES transactional email
- Secrets Manager
- CloudWatch logs/metrics/alarms
- Route 53 and ACM for `market.thecountypost.com`
- EventBridge for schedules

Do not invent real account IDs, domains, VPCs, ARNs, secrets, or budgets.

## Procedure

1. Define environment, owner, region, naming/tagging, and change boundary.
2. Produce/update IaC; avoid click-only configuration except documented bootstrap prerequisites.
3. Apply least privilege and private networking.
4. Configure production settings, secure headers/cookies, trusted origins/hosts, database pooling/connection limits, health checks, shutdown, logging, and secret injection.
5. Build, scan, and run the image locally.
6. Define migration as a one-off release task and deployment order.
7. Add alarms/dashboard/runbook and cost-impact notes.
8. Produce rollback/forward-fix and backup/restore validation steps.
9. Validate in a non-production environment before production.

## Output

- architecture/change summary
- IaC files and parameters
- IAM/network/security decisions
- deployment/migration sequence
- smoke tests and commands/results
- observability and cost notes
- rollback/recovery plan
- manual prerequisites and unresolved account information
