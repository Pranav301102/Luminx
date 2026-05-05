variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type. Free-tier eligible options: t3.small (2GB), t3.micro (1GB), c7i-flex.large (4GB), m7i-flex.large (8GB)"
  type        = string
  default     = "t3.small"
}

variable "key_pair_name" {
  description = "Name of your existing EC2 key pair (for SSH access)"
  type        = string
}

variable "your_ip_cidr" {
  description = "Your public IP in CIDR notation (e.g. 1.2.3.4/32). Restricts SSH and API access to your IP only."
  type        = string
  default     = "0.0.0.0/0"
}
