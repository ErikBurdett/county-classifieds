# M11 Operations Runbook

## Ownership checklist

Before a live deployment, record a named primary and backup owner for:

- AWS account and Terraform state/lock access.
- GitHub protected environments and OIDC deployment-role policy.
- DNS and ACM certificate renewal.
- RDS backups/restores and database credential rotation.
- SES identity, DKIM/SPF/DMARC, bounce/complaint handling, and sender access.
- CloudWatch dashboard, alarm SNS topic, 24-hour alarm acknowledgement, and
  escalation path.
- Application release/migration authority and post-deploy smoke testing.

Do not proceed while an owner or escalation path is absent.

## Deploy an immutable digest

1. CI must pass for the commit. Build and scan one ECR image, obtain its digest,
   and record the prior production digest.
2. Select the protected GitHub Environment and manually dispatch
   `Manual infrastructure deployment` with the region, approved OIDC role ARN,
   and `repository@sha256:...` digest. Start with `apply=false`; review the
   Terraform plan. A protected-environment approval is required before an
   apply.
3. Run the migration as a one-off ECS operations task using the candidate
   digest and exactly the web/worker production configuration:

   ```text
   python /app/src/manage.py migrate --noinput
   ```

   Wait for exit status zero and inspect only safe logs. Never run this command
   from a web task startup or in parallel with another migration task.
4. Update web and worker to the same digest. Verify `/health/ready/`, ALB target
   health, worker processing, expected EventBridge task exits, CloudWatch logs,
   and alarm delivery.
5. Record deployment time, digest, migration result, smoke-test result, and
   dashboard/alarm review in the release record.

Docker promotion is digest-based: build once, scan/test that digest, then pass
the exact `ECR repository@sha256` reference through staging and production.
Never rebuild or promote a mutable tag.

## Rollback and forward fix

1. Stop the release if readiness, target health, or safety checks fail.
2. If migrations are backward compatible, redeploy both web and worker using
   the recorded prior digest and observe health/alarms.
3. If the candidate migration is not compatible with older code, do not blindly
   roll back application code. Stop the worker and schedules if needed, preserve
   evidence, and issue a tested forward fix.
4. Do not delete production resources or Terraform state during incident
   recovery. Escalate to the named infrastructure/database owner.

## RDS backup and restore

The accepted targets are RTO 4 hours and RPO 24 hours. Automated backups are
retained for at least one day (the baseline defaults to seven). This is not a
guarantee until a restore is tested.

Quarterly, and before first production traffic:

1. Select a point-in-time within the last 24 hours and restore to a new,
   isolated RDS instance/subnet/security group. Never overwrite the source.
2. Restrict access to the database owner; do not expose data publicly or copy
   it to lower environments.
3. Measure restore start, available time, schema check, and a bounded
   application-readiness check. Record whether total elapsed time is under four
   hours and whether data loss is under 24 hours.
4. Delete the isolated restore using the approved data-handling procedure and
   record evidence, gaps, and remediation owner.

For an actual recovery, restore to a replacement, update the `DATABASE_URL`
secret through the approved change process, run compatibility checks/migrations
only when reviewed, redeploy the known-good digest, and validate before
directing traffic.

## Secrets rotation

1. Create a new secret version or replacement secret in Secrets Manager.
2. Test it in staging with the same task definition/configuration model.
3. Update the protected environment's ARN reference only if the ARN changed;
   never paste a secret value into Terraform, GitHub, a ticket, or logs.
4. Force a controlled new deployment so ECS injects the new value. Verify
   readiness and the affected integration.
5. Retire the old version only after the rollback window and owner approval.

Rotate Django signing material only with an explicit session/token invalidation
plan. Coordinate database credential rotation with the application
`DATABASE_URL` secret and RDS-managed admin credential; an uncoordinated change
causes an outage.

## Monitoring and alarms

At each deploy, check:

- ALB healthy target count, 5xx/latency, ECS desired-versus-running tasks, and
  task CPU/memory/restarts.
- RDS CPU, storage, freeable memory, connections, backup status, and logs.
- Outbox pending/failed count and oldest age from `inspect_outbox`.
- Payment webhook failures when payment integration is enabled.
- EventBridge invocation/task exits for expiry and reminder commands.
- SES sending/bounce/complaint indicators after SES is configured.

The alarm owner acknowledges each alarm, records the affected digest and time,
and either resolves or escalates according to the ownership checklist. An alarm
without a destination and owner is not accepted as operational coverage.

## Staff management console

`/manage/` is the staff landing page for operational summaries and links into
existing workflows. It is not a replacement for Django admin or domain
services: it has no direct mutation controls and never displays payment details,
outbox payloads, or private moderation notes.

Grant staff only the permissions needed for their work. A staff account without
the relevant permission can sign in but will not see the affected operational
link:

- `listings.moderate_listing` for the moderation queue.
- `billing.view_order` for billing reconciliation and the filtered order queue.
- Target model `view` permissions for policy, catalog, geography, and outbox
  Django admin links.

The local `seed_demo_staff` command is DEBUG-only and must not be included in
production deployment tasks. Production staff access, including the unresolved
MFA decision (DEC-111), remains subject to the normal access-review process.
