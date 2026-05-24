output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.s3_distribution.domain_name
}

output "s3_bucket_name" {
  description = "S3 bucket name for frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.s3_distribution.id
}

output "cognito_user_pool_id" {
  description = "The ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.user_pool_v3.id
}

output "cognito_app_client_id" {
  description = "The ID of the Cognito App Client"
  value       = aws_cognito_user_pool_client.client.id
}

output "cognito_domain" {
  description = "The domain of the Cognito Hosted UI"
  value       = "${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "grafana_otlp_endpoint" {
  value = "https://otlp-gateway-${var.grafana_cloud_region}.grafana.net"
}

output "grafana_otlp_token" {
  value     = grafana_cloud_access_policy_token.otlp.token
  sensitive = true
}

