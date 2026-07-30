variable "aws_region" {
  description = "AWS region for this environment."
  type        = string
}

variable "environment" {
  description = "Short environment name, such as staging or production."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}

variable "name_prefix" {
  description = "Resource name prefix; must be unique within the AWS account and region."
  type        = string
}

variable "media_bucket_name" {
  description = "Globally unique private S3 media bucket name. This value is non-secret task configuration."
  type        = string
}

variable "image_digest" {
  description = "Immutable ECR image reference, for example repository-url@sha256:... ."
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "Existing VPC ID. Leave null to create a dedicated VPC."
  type        = string
  default     = null
}

variable "private_subnet_ids" {
  description = "Existing private subnet IDs. Required when vpc_id is provided."
  type        = list(string)
  default     = []
}

variable "public_subnet_ids" {
  description = "Existing public subnet IDs for the public HTTPS load balancer. Required when vpc_id is provided."
  type        = list(string)
  default     = []
}

variable "vpc_cidr" {
  description = "CIDR for a Terraform-managed VPC."
  type        = string
  default     = "10.32.0.0/16"
}

variable "availability_zones" {
  description = "Exactly two availability zones for a Terraform-managed VPC."
  type        = list(string)
  default     = []
}

variable "database_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "marketplace"
}

variable "database_master_username" {
  description = "RDS master username. The password is managed by RDS, never supplied to Terraform."
  type        = string
  default     = "marketplace_admin"
  sensitive   = true
}

variable "database_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "database_backup_retention_days" {
  description = "Automated RDS backup retention in days; must meet the 24-hour RPO."
  type        = number
  default     = 7

  validation {
    condition     = var.database_backup_retention_days >= 1
    error_message = "Keep at least one day of automated backups for the accepted RPO."
  }
}

variable "database_deletion_protection" {
  description = "Protect the RDS instance from deletion."
  type        = bool
  default     = true
}

variable "database_maintenance_window" {
  description = "UTC RDS maintenance window."
  type        = string
  default     = "sun:06:00-sun:07:00"
}

variable "database_backup_window" {
  description = "UTC RDS backup window."
  type        = string
  default     = "04:00-05:00"
}

variable "task_secret_arns" {
  description = "Secrets Manager secret ARNs by Django environment variable name. Values are references only."
  type        = map(string)
  sensitive   = true

  validation {
    condition = alltrue([
      for name in ["DJANGO_SECRET_KEY", "DATABASE_URL", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"] :
      contains(keys(var.task_secret_arns), name)
    ])
    error_message = "task_secret_arns must reference Django, database, and SES SMTP secrets."
  }
}

variable "task_environment" {
  description = "Non-secret Django environment variables shared by web, worker, migration, and scheduled tasks."
  type        = map(string)

  validation {
    condition = alltrue([
      for name in [
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "AWS_REGION",
        "AWS_STORAGE_BUCKET_NAME",
        "EMAIL_HOST",
        "SES_FROM_EMAIL",
      ] : contains(keys(var.task_environment), name)
    ])
    error_message = "task_environment is missing required production configuration keys."
  }
}

variable "web_desired_count" {
  description = "Desired web task count."
  type        = number
  default     = 2
}

variable "web_acm_certificate_arn" {
  description = "Existing regional ACM certificate ARN for the public HTTPS listener; Terraform does not create DNS validation records."
  type        = string
  default     = null
}

variable "worker_desired_count" {
  description = "Desired outbox worker count."
  type        = number
  default     = 1
}

variable "enable_cloudfront" {
  description = "Create CloudFront private media delivery with origin access control."
  type        = bool
  default     = false
}

variable "cloudfront_aliases" {
  description = "Verified media delivery aliases. Requires cloudfront_acm_certificate_arn when non-empty."
  type        = list(string)
  default     = []
}

variable "cloudfront_acm_certificate_arn" {
  description = "Existing us-east-1 ACM certificate ARN for CloudFront aliases; not managed here."
  type        = string
  default     = null
}

variable "alarm_sns_topic_arn" {
  description = "Existing SNS topic ARN for alarm notifications; no topic or ownership policy is created here."
  type        = string
  default     = null
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}
