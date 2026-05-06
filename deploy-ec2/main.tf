terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Latest Amazon Linux 2023 AMI (ARM64 for t4g) ─────────────────────────────

data "aws_ami" "al2023_arm" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── Security groups ───────────────────────────────────────────────────────────

resource "aws_security_group" "cloud1" {
  name        = "luminx-cloud1"
  description = "Node A (head) + Tracker"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_ip_cidr]
  }

  ingress {
    description = "Node A /generate API (public)"
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
      description = "Tracker API (public - nodes + frontend poll this)"
    from_port   = 8003
    to_port     = 8003
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "cloud2" {
  name        = "luminx-cloud2"
  description = "Node C (tail)"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.your_ip_cidr]
  }

  ingress {
    description = "Node C /forward_tail (from Node B local + Cloud 1)"
    from_port   = 8004
    to_port     = 8004
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── EC2 instances (t4g.large ARM — CPU only, no GPU) ─────────────────────────

resource "aws_instance" "cloud1" {
  ami                         = data.aws_ami.al2023_arm.id
  instance_type               = var.instance_type
  key_name                    = var.key_pair_name
  vpc_security_group_ids      = [aws_security_group.cloud1.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = 30  # extra space for model weights cache
    volume_type = "gp3"
  }

  user_data = file("${path.module}/user_data.sh")

  tags = { Name = "luminx-cloud1", Project = "luminx", Role = "head+tracker" }
}

resource "aws_instance" "cloud2" {
  ami                         = data.aws_ami.al2023_arm.id
  instance_type               = var.instance_type
  key_name                    = var.key_pair_name
  vpc_security_group_ids      = [aws_security_group.cloud2.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  user_data = file("${path.module}/user_data.sh")

  tags = { Name = "luminx-cloud2", Project = "luminx", Role = "tail" }
}
