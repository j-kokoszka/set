# Synthetic Monitoring for set Application

# 1. Initialize Synthetic Monitoring (Checks if already installed)
# In many Free Tier accounts, this must be enabled in the UI first.
resource "grafana_synthetic_monitoring_installation" "main" {
  provider      = grafana.stack
  stack_id      = data.grafana_cloud_stack.main.id
  metrics_publisher_key = grafana_cloud_access_policy_token.otlp.token
}

# 2. Probe Data Source (Wait for installation)
data "grafana_synthetic_monitoring_probes" "main" {
  provider = grafana.stack
  depends_on = [grafana_synthetic_monitoring_installation.main]
}

# 3. HTTP Check: Frontend Availability
resource "grafana_synthetic_monitoring_check" "frontend" {
  provider      = grafana.stack
  job           = "${var.project_name}-frontend-uptime"
  target        = "https://${var.custom_domain}"
  enabled       = true
  probes        = [for p in data.grafana_synthetic_monitoring_probes.main.probes : p.id if p.region == "eu-central"]
  
  settings {
    http {
      method = "GET"
      fail_if_not_ssl = true
    }
  }
}

# 4. HTTP Check: Backend Health
resource "grafana_synthetic_monitoring_check" "backend" {
  provider      = grafana.stack
  job           = "${var.project_name}-backend-uptime"
  target        = "${aws_apigatewayv2_api.http_api.api_endpoint}/health"
  enabled       = true
  probes        = [for p in data.grafana_synthetic_monitoring_probes.main.probes : p.id if p.region == "eu-central"]
  
  settings {
    http {
      method = "GET"
    }
  }
}
