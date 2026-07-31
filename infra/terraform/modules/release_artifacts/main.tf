# Staging-only release-artifacts bucket (Sprint 25b.3).
# Holds integrity-checked deploy bundles and append-only deploy evidence.
# Never stores Terraform state or secrets.

data "aws_caller_identity" "current" {}

locals {
  account_id  = data.aws_caller_identity.current.account_id
  bucket_name = "${var.name_prefix}-release-artifacts-${local.account_id}"
}

resource "aws_s3_bucket" "artifacts" {
  bucket = local.bucket_name

  tags = merge(var.tags, {
    Name        = local.bucket_name
    Environment = var.environment
    Role        = "release-artifacts"
    Project     = "dealbrain"
    ManagedBy   = "terraform"
    Sprint      = "25b.3"
  })
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  dynamic "rule" {
    for_each = var.object_retention_days > 0 ? [var.object_retention_days] : []
    content {
      id     = "expire-objects"
      status = "Enabled"

      filter {}

      expiration {
        days = rule.value
      }

      noncurrent_version_expiration {
        noncurrent_days = rule.value
      }
    }
  }
}

# Deny accidental use as Terraform remote state.
resource "aws_s3_bucket_policy" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.artifacts.arn,
          "${aws_s3_bucket.artifacts.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}
