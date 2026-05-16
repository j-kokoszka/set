variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "set"
}

variable "custom_domain" {
  description = "Custom domain name for the application"
  type        = string
  default     = "set.kokoszka.cloud"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "cloudflare_api_token" {
  description = "Cloudflare API Token"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for kokoszka.cloud"
  type        = string
  default     = "dbd91891fabf248c5845c99f7479e865"
}
