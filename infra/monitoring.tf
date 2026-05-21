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
  alias                     = "stack"
  url                       = data.grafana_cloud_stack.main.url
  auth                      = grafana_cloud_stack_service_account_token.manager.key
  cloud_access_policy_token = var.grafana_cloud_api_key
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
