resource "aws_dynamodb_table" "workouts" {
  # tfsec:ignore:aws-dynamodb-table-customer-key
  name         = "${var.project_name}-workouts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }
}
