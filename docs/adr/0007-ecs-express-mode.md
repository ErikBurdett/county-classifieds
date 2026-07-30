# ADR 0007: Deploy the Public Web Service with ECS Express Mode

- Status: Accepted
- Date: 2026-07-22

## Context

The application needs independent, containerized deployment on AWS with HTTPS, load balancing, autoscaling, logs, and straightforward operations. ECS Express Mode provides production-oriented defaults while exposing underlying AWS resources.

## Decision

Build one immutable container image. Deploy the stateless web command through ECS Express Mode. Run worker and one-off migration/scheduled commands from the same image using ECS services/tasks. Use RDS, S3, SES, Secrets Manager, CloudWatch, Route 53, and ACM.

## Consequences

- Lower setup complexity than hand-configuring every ECS component.
- Application remains portable as a standard container.
- Infrastructure must confirm regional and IaC support during implementation.
- Database migrations remain an explicit deployment step.
