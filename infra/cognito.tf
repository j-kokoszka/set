# Temporarily removed while fixing user pool recreation
# resource "aws_cognito_user_pool" "user_pool" {
#   name = "${var.project_name}-user-pool-v2"
#
#   alias_attributes         = ["email"]
#   auto_verified_attributes = ["email"]
#
#   password_policy {
#     minimum_length    = 8
#     require_lowercase = true
#     require_numbers   = true
#     require_symbols   = true
#     require_uppercase = true
#   }
#
#   verification_message_template {
#     default_email_option = "CONFIRM_WITH_CODE"
#     email_message        = "Your verification code is {####}"
#     email_subject        = "Verify your email for ${var.project_name}"
#   }
#
#   schema {
#     attribute_data_type = "String"
#     name                = "email"
#     required            = true
#     mutable             = true
#   }
#
#   schema {
#     attribute_data_type = "String"
#     name                = "name"
#     required            = false
#     mutable             = true
#   }
#
#   lifecycle {
#     create_before_destroy = true
#   }
# }

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-auth-${var.environment}"
  # user_pool_id = aws_cognito_user_pool.user_pool.id
  user_pool_id = "eu-central-1_PZtslFTJS"
}

resource "aws_cognito_identity_provider" "google" {
  # user_pool_id  = aws_cognito_user_pool.user_pool.id
  user_pool_id  = "eu-central-1_PZtslFTJS"
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    authorize_scopes = "email openid profile"
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    attributes_url                = "https://people.googleapis.com/v1/people/me?personFields="
    attributes_url_add_attributes = "true"
    authorize_url                 = "https://accounts.google.com/o/oauth2/v2/auth"
    oidc_issuer                   = "https://accounts.google.com"
    token_request_method          = "POST"
    token_url                     = "https://www.googleapis.com/oauth2/v4/token"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
    name     = "name"
  }
}

resource "aws_cognito_user_pool_client" "client" {
  name = "${var.project_name}-client"

  # user_pool_id = aws_cognito_user_pool.user_pool.id
  user_pool_id  = "eu-central-1_PZtslFTJS"

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  callback_urls                        = ["https://${var.custom_domain}", "http://localhost:5173"]
  logout_urls                          = ["https://${var.custom_domain}", "http://localhost:5173"]
  
  supported_identity_providers = ["COGNITO", "Google"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]

  generate_secret = false

  # Ensure IdP is fully recognized before creating client that depends on it
  depends_on = [aws_cognito_identity_provider.google]
}
