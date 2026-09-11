# Production logging baseline (Early Access Phase 1).
# Durable application logs: CloudWatch Logs (not container stdout only).
# ALB access logs: encrypted S3 bucket with ELB delivery policy.
# Alerts/paging are NOT created here (EXT-16 / EXT-24 remain later phases).

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  # Regional ELB account IDs for classic PutObject access-log delivery.
  # us-east-1 is the frozen DealBrain region.
  elb_account_ids = {
    "us-east-1" = "127311923021"
  }
  elb_account_id    = lookup(local.elb_account_ids, var.aws_region, "127311923021")
  alb_logs_bucket   = "${var.name_prefix}-alb-logs-${local.account_id}"
  api_log_group     = "/dealbrain/${var.environment}/api"
  host_log_group    = "/dealbrain/${var.environment}/host"
  migrate_log_group = "/dealbrain/${var.environment}/migrate"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = local.api_log_group
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name        = local.api_log_group
    Environment = var.environment
    Role        = "application-logs"
    Project     = "dealbrain"
    ManagedBy   = "terraform"
  })
}

resource "aws_cloudwatch_log_group" "host" {
  name              = local.host_log_group
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name        = local.host_log_group
    Environment = var.environment
    Role        = "host-logs"
    Project     = "dealbrain"
    ManagedBy   = "terraform"
  })
}

resource "aws_cloudwatch_log_group" "migrate" {
  name              = local.migrate_log_group
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name        = local.migrate_log_group
    Environment = var.environment
    Role        = "migrate-logs"
    Project     = "dealbrain"
    ManagedBy   = "terraform"
  })
}

resource "aws_s3_bucket" "alb_logs" {
  bucket = local.alb_logs_bucket

  tags = merge(var.tags, {
    Name        = local.alb_logs_bucket
    Environment = var.environment
    Role        = "alb-access-logs"
    Project     = "dealbrain"
    ManagedBy   = "terraform"
  })
}

resource "aws_s3_bucket_public_access_block" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_ownership_controls" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "expire-alb-access-logs"
    status = "Enabled"

    filter {}

    expiration {
      days = var.log_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.log_retention_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.alb_logs.arn,
          "${aws_s3_bucket.alb_logs.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowELBLogDeliveryPut"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.elb_account_id}:root"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/alb/AWSLogs/${local.account_id}/*"
      },
      {
        Sid    = "AllowELBLogDeliveryAclCheck"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.elb_account_id}:root"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.alb_logs.arn
      },
      {
        Sid    = "AllowLogDeliveryServicePut"
        Effect = "Allow"
        Principal = {
          Service = "logdelivery.elasticloadbalancing.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/alb/AWSLogs/${local.account_id}/*"
      },
    ]
  })
}
