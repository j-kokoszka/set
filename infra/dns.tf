# DNS Records in Cloudflare

# ACM Validation Record
resource "cloudflare_dns_record" "acm_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name    = dvo.resource_record_name
      content = dvo.resource_record_value
      type    = dvo.resource_record_type
    }
  }

  zone_id = var.cloudflare_zone_id
  name    = each.value.name
  content = each.value.content
  type    = each.value.type
  ttl     = 60
  proxied = false
}

# App CNAME Record
resource "cloudflare_dns_record" "app" {
  zone_id = var.cloudflare_zone_id
  name    = "set" # set.kokoszka.cloud
  content = aws_cloudfront_distribution.s3_distribution.domain_name
  type    = "CNAME"
  ttl     = 1
  proxied = true
}
