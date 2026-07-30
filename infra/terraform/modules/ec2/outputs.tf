output "instance_id" {
  description = "EC2 instance ID."
  value       = aws_instance.api.id
}

output "private_ip" {
  description = "Private IP of the API host."
  value       = aws_instance.api.private_ip
}

output "public_ip" {
  description = "Public IP if associated; otherwise null."
  value       = aws_instance.api.public_ip
}
