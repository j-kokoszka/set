# Grafana Dashboards for set Application

resource "grafana_dashboard" "application_insights" {
  provider    = grafana.stack
  folder      = grafana_folder.set.id
  config_json = jsonencode({
    "title": "Application Insights",
    "uid": "set-app-insights",
    "tags": ["prod", "observability"],
    "timezone": "browser",
    "schemaVersion": 38,
    "panels": [
      # --- ROW: SUMMARY ---
      {
        "title": "Health Summary",
        "type": "row",
        "gridPos": { "h": 1, "w": 24, "x": 0, "y": 0 },
        "collapsed": false
      },
      {
        "title": "Request Rate",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 0, "y": 1 },
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service_name=\"${var.project_name}-backend\"}[5m]))",
            "legendFormat": "Requests/sec"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps",
            "color": { "mode": "thresholds" },
            "thresholds": { "mode": "absolute", "steps": [{ "color": "green", "value": null }] }
          }
        }
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 6, "y": 1 },
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\", service_name=\"${var.project_name}-backend\"}[5m])) / sum(rate(http_requests_total{service_name=\"${var.project_name}-backend\"}[5m])) * 100",
            "legendFormat": "Error Rate"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "color": { "mode": "thresholds" },
            "thresholds": { 
              "mode": "absolute", 
              "steps": [
                { "color": "green", "value": null },
                { "color": "orange", "value": 1 },
                { "color": "red", "value": 5 }
              ] 
            }
          }
        }
      },
      {
        "title": "Avg Latency (P90)",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 12, "y": 1 },
        "targets": [
          {
            "expr": "histogram_quantile(0.9, sum by (le) (rate(http_request_duration_seconds_bucket{service_name=\"${var.project_name}-backend\"}[5m])))",
            "legendFormat": "P90 Latency"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "color": { "mode": "thresholds" },
            "thresholds": { 
              "mode": "absolute", 
              "steps": [
                { "color": "green", "value": null },
                { "color": "orange", "value": 0.5 },
                { "color": "red", "value": 1.5 }
              ] 
            }
          }
        }
      },
      {
        "title": "Active Users (24h)",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 18, "y": 1 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Cognito",
            "metricName": "SignInSuccesses",
            "statistic": "Sum",
            "period": "86400"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "none",
            "color": { "mode": "thresholds" },
            "thresholds": { "mode": "absolute", "steps": [{ "color": "blue", "value": null }] }
          }
        }
      },

      # --- ROW: API PERFORMANCE ---
      {
        "title": "API & Backend Performance",
        "type": "row",
        "gridPos": { "h": 1, "w": 24, "x": 0, "y": 5 },
        "collapsed": false
      },
      {
        "title": "Traffic Volume (Status Codes)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 6 },
        "targets": [
          {
            "expr": "sum by (status) (rate(http_requests_total{service_name=\"${var.project_name}-backend\"}[5m]))",
            "legendFormat": "{{status}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "custom": { "drawStyle": "bars", "fillOpacity": 30 }
          }
        }
      },
      {
        "title": "Latency Heatmap",
        "type": "heatmap",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 6 },
        "targets": [
          {
            "expr": "sum by (le) (rate(http_request_duration_seconds_bucket{service_name=\"${var.project_name}-backend\"}[5m]))",
            "format": "heatmap"
          }
        ]
      },

      # --- ROW: AWS INFRASTRUCTURE ---
      {
        "title": "Infrastructure Health",
        "type": "row",
        "gridPos": { "h": 1, "w": 24, "x": 0, "y": 14 },
        "collapsed": false
      },
      {
        "title": "Lambda Invocations & Durations",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 8, "x": 0, "y": 15 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Lambda",
            "metricName": "Invocations",
            "dimensions": { "FunctionName": "${var.project_name}-api" },
            "statistic": "Sum",
            "period": "300"
          },
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Lambda",
            "metricName": "Duration",
            "dimensions": { "FunctionName": "${var.project_name}-api" },
            "statistic": "Average",
            "period": "300"
          }
        ]
      },
      {
        "title": "DynamoDB Capacity Consumption",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 8, "x": 8, "y": 15 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/DynamoDB",
            "metricName": "ConsumedReadCapacityUnits",
            "dimensions": { "TableName": "${var.project_name}-workouts" },
            "statistic": "Sum",
            "period": "300"
          },
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/DynamoDB",
            "metricName": "ConsumedWriteCapacityUnits",
            "dimensions": { "TableName": "${var.project_name}-workouts" },
            "statistic": "Sum",
            "period": "300"
          }
        ]
      },
      {
        "title": "CloudFront Distribution Requests",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 8, "x": 16, "y": 15 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/CloudFront",
            "metricName": "Requests",
            "dimensions": { "Region": "Global", "DistributionId": aws_cloudfront_distribution.s3_distribution.id },
            "statistic": "Sum",
            "period": "300"
          }
        ]
      },

      # --- ROW: AI & BUSINESS ---
      {
        "title": "AI & Business Metrics",
        "type": "row",
        "gridPos": { "h": 1, "w": 24, "x": 0, "y": 23 },
        "collapsed": false
      },
      {
        "title": "AI Response Time (Bedrock)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 24 },
        "targets": [
          {
            "expr": "bedrock_invocation_duration_seconds_sum / bedrock_invocation_duration_seconds_count",
            "legendFormat": "Avg Duration"
          }
        ],
        "fieldConfig": {
          "defaults": { "unit": "s" }
        }
      },
      {
        "title": "Workouts Logged (DynamoDB Metrics)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 24 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/DynamoDB",
            "metricName": "SuccessfulRequestLatency",
            "dimensions": { "TableName": "${var.project_name}-workouts", "Operation": "PutItem" },
            "statistic": "SampleCount",
            "period": "3600"
          }
        ],
        "fieldConfig": {
          "defaults": { "unit": "none", "color": { "mode": "palette-classic" } }
        }
      },

      # --- ROW: LOGS & TRACES ---
      {
        "title": "Deep Inspection (Logs & Traces)",
        "type": "row",
        "gridPos": { "h": 1, "w": 24, "x": 0, "y": 32 },
        "collapsed": false
      },
      {
        "title": "Backend Error Logs",
        "type": "logs",
        "gridPos": { "h": 10, "w": 12, "x": 0, "y": 33 },
        "targets": [
          {
            "datasource": "grafanacloud-loki-managed",
            "expr": "{service_name=\"${var.project_name}-backend\"} |= \"error\""
          }
        ]
      },
      {
        "title": "Slowest Traces (Tempo)",
        "type": "logs",
        "gridPos": { "h": 10, "w": 12, "x": 12, "y": 33 },
        "targets": [
          {
            "datasource": "grafanacloud-tempo",
            "queryType": "traceQL",
            "expr": "{service_name=\"${var.project_name}-backend\" && duration > 500ms}"
          }
        ]
      }
    ]
  })
}

resource "grafana_dashboard" "user_activity" {
  provider    = grafana.stack
  folder      = grafana_folder.set.id
  config_json = jsonencode({
    "title": "User Activity & Engagement",
    "uid": "set-user-activity",
    "tags": ["prod", "business"],
    "timezone": "browser",
    "schemaVersion": 38,
    "panels": [
      {
        "title": "Daily Growth (Cognito Signups)",
        "type": "stat",
        "gridPos": { "h": 6, "w": 12, "x": 0, "y": 0 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Cognito",
            "metricName": "SignUpSuccesses",
            "statistic": "Sum",
            "period": "86400"
          }
        ],
        "fieldConfig": {
          "defaults": { "color": { "mode": "thresholds" }, "mappings": [], "thresholds": { "mode": "absolute", "steps": [{ "color": "green", "value": null }] } }
        }
      },
      {
        "title": "Active Sessions (SignIn Trends)",
        "type": "timeseries",
        "gridPos": { "h": 6, "w": 12, "x": 12, "y": 0 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Cognito",
            "metricName": "SignInSuccesses",
            "statistic": "Sum",
            "period": "3600"
          }
        ]
      },
      {
        "title": "Workout Logging Frequency",
        "type": "bargauge",
        "gridPos": { "h": 8, "w": 24, "x": 0, "y": 6 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/DynamoDB",
            "metricName": "SuccessfulRequestLatency",
            "dimensions": { "TableName": "${var.project_name}-workouts", "Operation": "PutItem" },
            "statistic": "SampleCount",
            "period": "86400"
          }
        ],
        "fieldConfig": {
          "defaults": { "unit": "none", "color": { "mode": "palette-classic" } }
        }
      }
    ]
  })
}

resource "grafana_dashboard" "security_overview" {
  provider    = grafana.stack
  folder      = grafana_folder.set.id
  config_json = jsonencode({
    "title": "Security Overview",
    "uid": "set-security-overview",
    "tags": ["prod", "security"],
    "timezone": "browser",
    "schemaVersion": 38,
    "panels": [
      {
        "title": "WAF Blocked Requests",
        "type": "stat",
        "gridPos": { "h": 6, "w": 12, "x": 0, "y": 0 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/WAFV2",
            "metricName": "BlockedRequests",
            "dimensions": { "Region": "Global", "WebACL": "${var.project_name}-waf-acl" },
            "statistic": "Sum",
            "period": "3600"
          }
        ],
        "fieldConfig": {
          "defaults": { "color": { "mode": "thresholds" }, "thresholds": { "mode": "absolute", "steps": [{ "color": "red", "value": 0 }] } }
        }
      },
      {
        "title": "Auth Failures (Cognito)",
        "type": "stat",
        "gridPos": { "h": 6, "w": 12, "x": 12, "y": 0 },
        "targets": [
          {
            "datasource": "aws-cloudwatch",
            "namespace": "AWS/Cognito",
            "metricName": "SignInFailures",
            "statistic": "Sum",
            "period": "3600"
          }
        ]
      }
    ]
  })
}
