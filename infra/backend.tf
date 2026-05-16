terraform {
  backend "s3" {
    bucket         = "set-terraform-state-prod-77777"
    key            = "terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "set-terraform-locks-prod"
    encrypt        = true
  }
}
