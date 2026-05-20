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
    "logs:write",
    "traces:write"
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

# 3. Synthetic Monitoring (Uptime Checks)
# Note: Synthetic Monitoring installation requires a stack
# For simplicity in Free Tier (1 stack), we assume the stack exists or is managed elsewhere.
# If you want to manage the stack itself via Terraform, we can add grafana_cloud_stack.

# 4. Dashboard Folder
# To manage resources INSIDE the stack, we would need a second provider instance 
# pointing to the stack URL. This is best done in a separate phase once the stack is ready.
