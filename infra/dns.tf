# DNS Records in Cloudflare

# ACM Validation Record
resource "cloudflare_record" "acm_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id = var.cloudflare_zone_id
  name    = each.value.name
  value   = each.value.record
  type    = each.value.type
  ttl     = 60
  proxied = false
}

# App CNAME Record
resource "cloudflare_record" "app" {
  zone_id         = var.cloudflare_zone_id
  name            = "set" # set.kokoszka.cloud
  value           = aws_cloudfront_distribution.s3_distribution.domain_name
  type            = "CNAME"
  ttl             = 1
  proxied         = true
  allow_overwrite = true
}
