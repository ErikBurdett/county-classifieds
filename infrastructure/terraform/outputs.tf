output "ecr_repository_url" {
  description = "ECR repository URL used to build immutable image digest references."
  value       = aws_ecr_repository.application.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster for the web, worker, migration, and scheduled tasks."
  value       = aws_ecs_cluster.application.name
}

output "operations_task_definition_arn" {
  description = "Task definition for explicit migration and scheduled command runs."
  value       = aws_ecs_task_definition.operations.arn
}

output "load_balancer_dns_name" {
  description = "HTTPS load balancer hostname. DNS records are intentionally not managed by this foundation."
  value       = aws_lb.web.dns_name
}

output "media_bucket_name" {
  description = "Private media bucket name."
  value       = aws_s3_bucket.media.bucket
}

output "rds_endpoint" {
  description = "Private RDS endpoint; do not publish it in DNS, logs, or application configuration outside Secrets Manager."
  value       = aws_db_instance.database.address
  sensitive   = true
}
