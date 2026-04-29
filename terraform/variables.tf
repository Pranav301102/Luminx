variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "Application name used as a prefix for resource names"
  type        = string
  default     = "luminx"
}

# ── Networking ───────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of AZs to deploy into (must be >= 2 for ALB)"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDRs for public subnets (one per AZ, used by ALB)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDRs for private subnets (one per AZ, used by ECS tasks)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

# ── ECS / Container settings ─────────────────────────────────────────────────

variable "model_name" {
  description = "HuggingFace model name loaded by Node A and Node B"
  type        = string
  default     = "sshleifer/tiny-gpt2"
}

variable "split_layer" {
  description = "Default transformer layer index at which to split head/tail"
  type        = number
  default     = 2
}

variable "enable_dynamic_split" {
  description = "Allow tracker to override split_layer at runtime"
  type        = bool
  default     = true
}

variable "heartbeat_timeout_sec" {
  description = "Seconds before tracker marks a node stale"
  type        = number
  default     = 30
}

# CPU and memory for each ECS task (Fargate units: 1 vCPU = 1024)
variable "tracker_cpu" {
  type    = number
  default = 256
}

variable "tracker_memory" {
  type    = number
  default = 512
}

variable "node_cpu" {
  description = "CPU units for Node A and Node B (model inference; increase for real models)"
  type        = number
  default     = 1024
}

variable "node_memory" {
  description = "Memory (MiB) for Node A and Node B"
  type        = number
  default     = 2048
}
