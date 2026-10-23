output "vpc_id" {
  description = "VPC ID."
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "VPC CIDR block."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs (ALB / optional public EC2)."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs (RDS / private app hosts)."
  value       = aws_subnet.private[*].id
}

output "nat_gateway_ids" {
  description = "NAT gateway IDs (empty when disabled)."
  value       = aws_nat_gateway.this[*].id
}

output "flow_logs_bucket_name" {
  description = "Dedicated S3 bucket for this VPC's REJECT flow logs."
  value       = aws_s3_bucket.flow_logs.bucket
}
