# Grafana Dashboards for set Application

resource "grafana_dashboard" "service_overview" {
  provider    = grafana.stack
  folder      = grafana_folder.set.id
  config_json = jsonencode({
    "title": "Service Overview",
    "uid": "set-service-overview",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service_name=\"set-backend\"}[5m]))",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "API Latency (P90)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 0 },
        "targets": [
          {
            "expr": "histogram_quantile(0.9, sum by (le) (rate(http_request_duration_seconds_bucket{service_name=\"set-backend\"}[5m])))",
            "legendFormat": "P90 Latency"
          }
        ]
      },
      {
        "title": "AI Model Latency (Bedrock)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 8 },
        "targets": [
          {
            "expr": "sum by (model_id) (rate(bedrock_invocation_duration_seconds_sum[5m]) / rate(bedrock_invocation_duration_seconds_count[5m]))",
            "legendFormat": "{{model_id}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 8 },
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service_name=\"set-backend\", status=~\"5..\"}[5m])) / sum(rate(http_requests_total{service_name=\"set-backend\"}[5m]))",
            "legendFormat": "Error %"
          }
        ]
      }
    ],
    "schemaVersion": 38
  })
}
