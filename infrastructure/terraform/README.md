# Terraform production foundation

This is an AWS foundation for one environment. It intentionally does not create
DNS records, ACM certificates, SES identities, an alarm SNS topic, GitHub
secrets, or Secrets Manager values. Those items need verified ownership and
environment-specific approval before they can be managed.

## Prerequisites and state

Use Terraform `>=1.9,<2.0` and AWS provider `~>5.0`. The backend is deliberately
not committed: initialize it with a reviewed backend configuration so bucket,
key, DynamoDB lock table, and AWS account remain environment owned.

```bash
terraform -chdir=infrastructure/terraform init \
  -backend-config="bucket=<state-bucket>" \
  -backend-config="key=marketplace/production/terraform.tfstate" \
  -backend-config="region=<aws-region>" \
  -backend-config="dynamodb_table=<state-lock-table>" \
  -backend-config="encrypt=true"
```

The remote-state bucket, lock table, and deployment role must exist before
initialization. Do not put their account IDs, credentials, or state values in
this repository.

## Configuration

Copy the comments from `environments/production/terraform.tfvars.example` into
an ignored `terraform.tfvars`, replace every placeholder through an approved
secret/configuration process, and review the plan. `task_secret_arns` contains
only Secrets Manager references. `task_environment` contains only non-secret
values. Production task injection must provide:

- `DJANGO_SECRET_KEY`, `DATABASE_URL`, `EMAIL_HOST_USER`, and
  `EMAIL_HOST_PASSWORD` from Secrets Manager references.
- Django host/CSRF values, AWS region/bucket, SES SMTP host/user, and verified
  sender address as non-secret environment values.

The RDS admin password is generated and held by RDS/Secrets Manager. The
application uses a separate `DATABASE_URL` secret reference; create and rotate
it according to the database credential procedure before deployment.

Set either `vpc_id`, `private_subnet_ids`, and `public_subnet_ids` for a
reviewed existing VPC, or leave `vpc_id` null and supply exactly two
`availability_zones` to create the lean VPC. The managed VPC uses one NAT
gateway to match the accepted single-AZ recovery posture; assess a multi-AZ NAT
layout if the availability target changes.

`image_digest` must be the immutable ECR digest form
`<repository-url>@sha256:<digest>`. Web, worker, migration, and scheduled
commands use this exact input. Tags must not be used for promotion.

## Safe validation

```bash
make terraform-fmt
make terraform-validate
```

These targets report a clear missing-tool message and do not change the normal
quality gate. `terraform validate` does not access AWS. Run `terraform plan`
only with approved remote state, AWS identity, secrets references, and an
environment configuration reviewed by the infrastructure owner.

## What this foundation creates

- ECR with immutable tags and scan-on-push.
- A VPC option, private ECS/RDS network path, HTTPS ALB, and restrictive task
  and database security groups.
- Fargate web and worker services plus an operations task definition.
- Single-AZ encrypted PostgreSQL with automated backups, maintenance window,
  and configurable deletion protection.
- Private versioned/encrypted S3 media storage with lifecycle cleanup.
- Optional CloudFront OAC for `processed/` objects only.
- ECS task execution/task roles, CloudWatch logs, baseline availability/database
  alarms, dashboard, and EventBridge commands.

Alarm delivery is disabled until `alarm_sns_topic_arn` points to a reviewed
existing topic. CloudWatch needs application metric/log filters for outbox age,
webhook failure, and scheduled task failure; their names and owners are
documented in the operations runbook rather than guessed here.

## Deliberate release task

Do not migrate in the web container or ECS service startup. After the digest is
available and before changing services, run one one-off ECS task from the
`operations_task_definition_arn` output with:

```text
python /app/src/manage.py migrate --noinput
```

Wait for exit status zero, inspect migration logs, then update web and worker to
the same image digest. See `docs/29-M11-OPERATIONS-RUNBOOK.md` for the complete
sequence, rollback constraints, restore procedure, and required release checks.
