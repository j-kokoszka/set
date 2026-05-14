# Infrastructure Plan: Terraform Migration & Google SSO

## Objective
Migrate the infrastructure-as-code (IaC) from AWS SAM to HashiCorp Terraform. Terraform is the industry standard for managing complex cloud environments and is highly capable of orchestrating the Amazon Cognito + Google SSO integration, as well as the GitHub OIDC deployment pipeline.

## Directory Structure
We will create a new `terraform/` directory at the project root to hold our infrastructure definitions.

```text
terraform/
├── main.tf          # Provider configurations (AWS, optional Google)
├── variables.tf     # Input variables (e.g., Google Client ID/Secret)
├── outputs.tf       # Exported values (e.g., API URL, Cognito Client ID)
├── cognito.tf       # Identity: User Pool, Google SSO Provider, Hosted UI
├── dynamodb.tf      # Database: 'set-workouts' table
├── lambda_api.tf    # Compute: FastAPI backend and API Gateway
└── oidc.tf          # Security: GitHub Actions OIDC Trust
```

## Component Breakdown

### 1. Amazon Cognito & Google SSO (`cognito.tf`)
This is where Terraform shines. We will automate the "click-ops" of setting up SSO:
*   `aws_cognito_user_pool`: The core user database.
*   `aws_cognito_identity_provider`: Links the User Pool to Google. It requires the `google_client_id` and `google_client_secret` (passed as secure variables).
*   `aws_cognito_user_pool_client`: The configuration for our React frontend, specifying that it is allowed to use the Google provider and defining the Callback URLs.
*   `aws_cognito_user_pool_domain`: Sets up the hosted UI URL (e.g., `set-tracker-auth.auth.us-east-1.amazoncognito.com`).

### 2. Secure CI/CD Deployment (`oidc.tf`)
We will replace hardcoded AWS keys with OpenID Connect (OIDC).
*   Terraform will create an `aws_iam_openid_connect_provider` for GitHub.
*   It will create an IAM Role that GitHub Actions can assume. This role will only have permission to deploy the resources defined in our Terraform state.

### 3. Application Infrastructure (`dynamodb.tf` & `lambda_api.tf`)
We will translate the existing `template.yaml` (SAM) resources into their Terraform equivalents:
*   `aws_dynamodb_table` for the single-table design.
*   `aws_lambda_function`, `aws_apigatewayv2_api`, and necessary IAM roles for the FastAPI backend.

## The Google Cloud Side
While Terraform *can* manage Google Cloud resources (using the `google` provider), setting up the initial OAuth Consent Screen and getting the Client ID/Secret in Google Cloud is usually done manually once per project, as it requires domain verification and branding setup.
1. You will manually create the OAuth credentials in Google Cloud.
2. You will store the Client ID and Secret in GitHub Secrets.
3. GitHub Actions will pass those secrets to Terraform during deployment:
   `terraform apply -var="google_client_id=${{ secrets.GOOGLE_CLIENT_ID }}" ...`

## Implementation Steps
1.  **Draft Terraform Files**: Write the `.tf` files defining the infrastructure.
2.  **Update GitHub Actions**: Modify `.github/workflows/ci.yml` (or create a `deploy.yml`) to use `hashicorp/setup-terraform` instead of SAM.
3.  **Clean Up**: Remove the old `template.yaml`.
