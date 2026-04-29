terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and configure after creating the S3 bucket + DynamoDB table
  # backend "s3" {
  #   bucket         = "luminx-tfstate"
  #   key            = "sprint1/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "luminx-tfstate-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "luminx"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
