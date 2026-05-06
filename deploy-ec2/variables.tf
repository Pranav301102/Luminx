variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type for inference nodes. t4g.large = ARM Graviton2, 2 vCPU, 8 GB RAM, CPU-only (~$0.067/hr)."
  type        = string
  default     = "t4g.large"
}

variable "key_pair_name" {
  description = "Name of your existing EC2 key pair (for SSH access)"
  type        = string
}

variable "your_ip_cidr" {
  description = "Your public IP in CIDR notation (e.g. 1.2.3.4/32). Restricts SSH access to your IP only."
  type        = string
  default     = "0.0.0.0/0"
}

variable "cloudfront_price_class" {
  description = "CloudFront price class. PriceClass_100 = US/EU only (cheapest). PriceClass_All = global."
  type        = string
  default     = "PriceClass_100"
}
