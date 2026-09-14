# Default AMI: official AWS public parameter for standard (non-minimal)
# Amazon Linux 2023 x86_64 with the default kernel.
# https://docs.aws.amazon.com/linux/al2023/ug/ec2.html
#
# This cannot resolve al2023-ami-minimal-* images. The previous aws_ami name
# filter `al2023-ami-*-x86_64` could select the latest *minimal* AMI because
# that name also matches the glob.
#
# When var.ami_id is set, this lookup is skipped (explicit override).
# Changing the selector does not replace an existing host: aws_instance.api
# ignores AMI drift. Live replacement is owner-controlled and out-of-band
# after review.
data "aws_ssm_parameter" "al2023" {
  count = var.ami_id == "" ? 1 : 0
  name  = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

locals {
  ami_id = var.ami_id != "" ? var.ami_id : data.aws_ssm_parameter.al2023[0].value
}

resource "aws_instance" "api" {
  ami                         = local.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = var.security_group_ids
  iam_instance_profile        = var.iam_instance_profile_name
  associate_public_ip_address = var.associate_public_ip
  user_data_base64            = var.user_data_base64 != "" ? var.user_data_base64 : null

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gb
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-host"
    Role = "api-compose-host"
  })

  # AMI selector / AWS default-AMI updates must not replace a running host.
  # Production replacement of a bad instance is an explicit owner-controlled
  # out-of-band action after this change is reviewed and merged.
  lifecycle {
    ignore_changes = [ami]
  }
}

resource "aws_lb_target_group_attachment" "api" {
  target_group_arn = var.target_group_arn
  target_id        = aws_instance.api.id
  port             = 8000
}
