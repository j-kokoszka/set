# Grafana Dashboards for set Application

resource "grafana_dashboard" "service_overview" {
  provider    = grafana.stack
  folder      = grafana_folder.set.id
  config_json = jsonencode({
    "title": "Service Overview",
    "uid": "set-service-overview",
    "panels": [
      {
        "title": "API Request Rate (Prometheus)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service_name=\"set-backend\"}[5m])) OR sum(rate(calls_total{service_name=\"set-backend\"}[5m]))",
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
            "expr": "histogram_quantile(0.9, sum by (le) (rate(http_request_duration_seconds_bucket{service_name=\"set-backend\"}[5m])) OR sum by (le) (rate(duration_bucket{service_name=\"set-backend\"}[5m])))",
            "legendFormat": "P90 Latency"
          }
        ]
      },
      {
        "title": "Lambda Invocations (CloudWatch)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 8 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Lambda",
            "metricName": "Invocations",
            "dimensions": { "FunctionName": "${var.project_name}-api" },
            "statistic": "Sum",
            "period": "300"
          }
        ]
      },
      {
        "title": "Lambda Errors (CloudWatch)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 8 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Lambda",
            "metricName": "Errors",
            "dimensions": { "FunctionName": "${var.project_name}-api" },
            "statistic": "Sum",
            "period": "300"
          }
        ]
      },
      {
        "title": "AI Model Latency (Bedrock)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 16 },
        "targets": [
          {
            "expr": "sum by (model_id) (rate(bedrock_invocation_duration_seconds_sum[5m]) / rate(bedrock_invocation_duration_seconds_count[5m]))",
            "legendFormat": "{{model_id}}"
          }
        ]
      },
      {
        "title": "Backend Logs (Loki)",
        "type": "logs",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 16 },
        "targets": [
          {
            "datasource": "grafanacloud-loki-managed",
            "expr": "{service_name=\"set-backend\"}"
          }
        ]
      },
      {
        "title": "Live Trace Search (Tempo)",
        "type": "logs",
        "gridPos": { "h": 8, "w": 24, "x": 0, "y": 24 },
        "targets": [
          {
            "datasource": "grafanacloud-tempo",
            "queryType": "traceQL",
            "expr": "{service_name=\"set-backend\"}"
          }
        ]
      }
    ],
    "schemaVersion": 38
  })
}
