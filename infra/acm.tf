# SSL Certificate for CloudFront (Must be in us-east-1)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "cert" {
  provider          = aws.us_east_1
  domain_name       = var.custom_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "cert" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in cloudflare_dns_record.acm_validation : record.name]
}

output "acm_certificate_arn" {
  value = aws_acm_certificate.cert.arn
}
