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

variable "log_level" {
  description = "Log level for the application"
  type        = string
  default     = "INFO"
}

variable "google_client_id" {
  description = "Google OAuth 2.0 Client ID"
  type        = string
  sensitive   = false # Usually considered public in OAuth flows
}

variable "google_client_secret" {
  description = "Google OAuth 2.0 Client Secret"
  type        = string
  sensitive   = true
}
