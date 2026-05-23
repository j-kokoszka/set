terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.45"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.19"
    }
    grafana = {
      source  = "grafana/grafana"
      version = "~> 4.36"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Grafana Cloud Management
provider "grafana" {
  alias                     = "cloud"
  cloud_access_policy_token = var.grafana_cloud_api_key # This should be a Cloud Access Policy token
}
