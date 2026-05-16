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
  validation_record_fqdns = [for record in cloudflare_record.acm_validation : record.hostname]
}

output "acm_certificate_arn" {
  value = aws_acm_certificate.cert.arn
}

output "dns_validation_record" {
  description = "DNS validation record for ACM. Add this to Cloudflare."
  value = {
    name  = tolist(aws_acm_certificate.cert.domain_validation_options)[0].resource_record_name
    type  = tolist(aws_acm_certificate.cert.domain_validation_options)[0].resource_record_type
    value = tolist(aws_acm_certificate.cert.domain_validation_options)[0].resource_record_value
  }
}
