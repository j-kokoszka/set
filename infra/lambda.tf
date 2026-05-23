# Lambda Function
resource "aws_lambda_function" "api" {
  filename      = "lambda_function_payload.zip" # Placeholder, will be managed by CI/CD
  function_name = "${var.project_name}-api"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 512

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      DYNAMODB_TABLE         = aws_dynamodb_table.workouts.name
      MOCK_AUTH              = "false"
      LOG_LEVEL              = var.log_level
      COGNITO_USER_POOL_ID   = aws_cognito_user_pool.user_pool_v2.id
      COGNITO_APP_CLIENT_ID  = aws_cognito_user_pool_client.client.id
      SET_AWS_REGION         = var.aws_region
      GITHUB_PAT_SECRET_ID   = aws_secretsmanager_secret.github_pat.name
      OTEL_EXPORTER_OTLP_ENDPOINT = "https://otlp-gateway-${var.grafana_cloud_region}.grafana.net"
      OTEL_EXPORTER_OTLP_HEADERS  = "Authorization=Bearer ${grafana_cloud_access_policy_token.otlp.token}"
      OTEL_SERVICE_NAME      = "${var.project_name}-backend"
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# KMS Key for Secret Encryption
resource "aws_kms_key" "secrets" {
  description             = "KMS key for encrypting project secrets"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# Secrets Manager for GITHUB_PAT
resource "aws_secretsmanager_secret" "github_pat" {
  name        = "${var.project_name}-github-pat"
  description = "GitHub Personal Access Token for issue reporting"
  kms_key_id  = aws_kms_key.secrets.arn
  recovery_window_in_days = 0 # For development/demo purposes
}

resource "aws_secretsmanager_secret_version" "github_pat" {
  secret_id     = aws_secretsmanager_secret.github_pat.id
  secret_string = var.github_pat
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for DynamoDB, Secrets Manager, and Logging
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_secrets" {
  name        = "${var.project_name}-lambda-secrets"
  description = "IAM policy for Lambda to access Secrets Manager and KMS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "secretsmanager:GetSecretValue"
        Effect   = "Allow"
        Resource = aws_secretsmanager_secret.github_pat.arn
      },
      {
        Action   = "kms:Decrypt"
        Effect   = "Allow"
        Resource = aws_kms_key.secrets.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_secrets_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_secrets.arn
}

resource "aws_iam_policy" "lambda_dynamodb" {
  name        = "${var.project_name}-lambda-dynamodb"
  description = "IAM policy for Lambda to access DynamoDB"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:BatchWriteItem",
          "dynamodb:DeleteItem",
          "dynamodb:UpdateItem"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.workouts.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_dynamodb.arn
}

resource "aws_iam_policy" "lambda_bedrock" {
  name        = "${var.project_name}-lambda-bedrock"
  description = "IAM policy for Lambda to invoke Bedrock models"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "bedrock:InvokeModel"
        Effect   = "Allow"
        Resource = [
          "arn:aws:bedrock:eu-central-1::foundation-model/amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-west-1::foundation-model/amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-west-3::foundation-model/amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-central-1::foundation-model/amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-west-1::foundation-model/amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-west-3::foundation-model/amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-central-1:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-west-1:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-west-3:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-central-1:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-west-1:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-west-3:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-micro-v1:0" ,
          "arn:aws:bedrock:eu-north-1::foundation-model/amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-north-1::foundation-model/amazon.nova-micro-v1:0",
          "arn:aws:bedrock:eu-north-1:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-lite-v1:0",
          "arn:aws:bedrock:eu-north-1:${data.aws_caller_identity.current.account_id}:inference-profile/eu.amazon.nova-micro-v1:0"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_bedrock_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_bedrock.arn
}

# API Gateway (HTTP API)
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_headers = ["*"]
    allow_methods = ["*"]
    allow_origins = ["*"] # Adjust for production later
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"

  integration_uri    = aws_lambda_function.api.invoke_arn
  integration_method = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
