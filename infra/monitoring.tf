# Grafana Cloud Observability Resources

data "grafana_cloud_stack" "main" {
  provider = grafana.cloud
  slug     = var.grafana_cloud_stack_slug
}

# 1. Access Policy for OTLP Ingestion (Metrics, Logs, Traces)
resource "grafana_cloud_access_policy" "otlp" {
  provider     = grafana.cloud
  region       = var.grafana_cloud_region
  name         = "${var.project_name}-otlp-ingestion"
  display_name = "OTLP Ingestion for ${var.project_name}"

  scopes = [
    "metrics:write",
    "metrics:read",
    "logs:read",
    "logs:write",
    "traces:write",
    "traces:read"
  ]

  realm {
    type       = "stack"
    identifier = data.grafana_cloud_stack.main.id
  }
}

# 2. Token for the OTLP Access Policy
resource "grafana_cloud_access_policy_token" "otlp" {
  provider         = grafana.cloud
  region           = var.grafana_cloud_region
  access_policy_id = grafana_cloud_access_policy.otlp.policy_id
  name             = "${var.project_name}-otlp-token"
  display_name     = "Token for OTLP Ingestion (${var.project_name})"
}

# 3. INTERNAL MANAGEMENT: Create a Service Account INSIDE the stack
resource "grafana_cloud_stack_service_account" "manager" {
  provider   = grafana.cloud
  stack_slug = var.grafana_cloud_stack_slug
  name       = "terraform-stack-manager"
  role       = "Admin"
}

resource "grafana_cloud_stack_service_account_token" "manager" {
  provider           = grafana.cloud
  stack_slug         = var.grafana_cloud_stack_slug
  name               = "terraform-manager-token"
  service_account_id = grafana_cloud_stack_service_account.manager.id
}

# 4. Provider for managing resources INSIDE the stack
provider "grafana" {
  alias = "stack"
  url   = data.grafana_cloud_stack.main.url
  auth  = grafana_cloud_stack_service_account_token.manager.key
}

# 5. Dashboard Folder
resource "grafana_folder" "set" {
  provider = grafana.stack
  title    = "${var.project_name} Application"
}

# 6. Data Sources (Ensure they are discoverable in dashboards)
# In Grafana Cloud, these are usually pre-created, but we reference them here.
resource "grafana_data_source" "prometheus" {
  provider = grafana.stack
  type     = "prometheus"
  name     = "grafanacloud-prom-managed"
  url      = data.grafana_cloud_stack.main.prometheus_url
  
  basic_auth_enabled = true
  basic_auth_username = data.grafana_cloud_stack.main.prometheus_user_id
  secure_json_data_encoded = jsonencode({
    basicAuthPassword = grafana_cloud_access_policy_token.otlp.token
  })
}

resource "grafana_data_source" "loki" {
  provider = grafana.stack
  type     = "loki"
  name     = "grafanacloud-loki-managed"
  url      = data.grafana_cloud_stack.main.logs_url
  
  basic_auth_enabled = true
  basic_auth_username = data.grafana_cloud_stack.main.logs_user_id
  secure_json_data_encoded = jsonencode({
    basicAuthPassword = grafana_cloud_access_policy_token.otlp.token
  })
}

resource "grafana_data_source" "tempo" {
  provider = grafana.stack
  type     = "tempo"
  name     = "grafanacloud-tempo"
  url      = data.grafana_cloud_stack.main.traces_url
  
  basic_auth_enabled = true
  basic_auth_username = data.grafana_cloud_stack.main.traces_user_id
  secure_json_data_encoded = jsonencode({
    basicAuthPassword = grafana_cloud_access_policy_token.otlp.token
  })
}

# 7. CloudWatch Data Source (AWS Integration via AssumeRole)
resource "aws_iam_role" "grafana_monitoring" {
  name = "${var.project_name}-grafana-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          # Grafana Cloud AWS Account ID
          AWS = "arn:aws:iam::${var.grafana_cloud_aws_account_id}:root" 
        }
        Condition = {
          StringEquals = {
            # External ID provided by Grafana Cloud to prevent confused deputy
            "sts:ExternalId": var.grafana_cloud_stack_slug
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "grafana_cloudwatch" {
  role       = aws_iam_role.grafana_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchReadOnlyAccess"
}

resource "grafana_data_source" "cloudwatch" {
  provider = grafana.stack
  type     = "cloudwatch"
  name     = "aws-cloudwatch"

  json_data_encoded = jsonencode({
    defaultRegion = var.aws_region
    authType      = "arn"
    assumeRoleArn = aws_iam_role.grafana_monitoring.arn
    externalId    = var.grafana_cloud_stack_slug
  })
}
