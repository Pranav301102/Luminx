output "cloud1_ip" {
  description = "Public IP of Cloud 1 (Node A + Tracker)"
  value       = aws_instance.cloud1.public_ip
}

output "cloud2_ip" {
  description = "Public IP of Cloud 2 (Node C)"
  value       = aws_instance.cloud2.public_ip
}

output "generate_endpoint" {
  description = "Text generation API endpoint"
  value       = "http://${aws_instance.cloud1.public_ip}:8001/generate"
}

output "tracker_endpoint" {
  description = "Tracker API endpoint"
  value       = "http://${aws_instance.cloud1.public_ip}:8003/assignment"
}

output "cloudfront_url" {
  description = "CloudFront URL serving the React frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "frontend_bucket" {
  description = "S3 bucket name for frontend static files"
  value       = aws_s3_bucket.frontend.bucket
}

output "cloudfront_id" {
  description = "CloudFront distribution ID (needed for cache invalidation)"
  value       = aws_cloudfront_distribution.frontend.id
}

output "ssh_cloud1" {
  value = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_instance.cloud1.public_ip}"
}

output "ssh_cloud2" {
  value = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_instance.cloud2.public_ip}"
}
