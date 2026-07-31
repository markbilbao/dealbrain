terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Remote state is mandatory for shared apply once bootstrap exists.
  # Bootstrap an S3 bucket + DynamoDB lock table out-of-band, then uncomment:
  #
  # backend "s3" {
  #   bucket         = "dealbrain-terraform-state-REPLACE_ME"
  #   key            = "account/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "dealbrain-terraform-locks"
  #   encrypt        = true
  # }
}
