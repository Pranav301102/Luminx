output "generate_endpoint" {
  description = "Public URL for the /generate API"
  value       = "http://${aws_lb.node_a.dns_name}/generate"
}

output "alb_dns" {
  description = "ALB DNS name (point your domain's CNAME here)"
  value       = aws_lb.node_a.dns_name
}

output "ecr_urls" {
  description = "ECR repository URLs — use these in your docker push commands"
  value = {
    tracker = aws_ecr_repository.services["tracker"].repository_url
    node_a  = aws_ecr_repository.services["node-a"].repository_url
    node_b  = aws_ecr_repository.services["node-b"].repository_url
  }
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names for each service"
  value = {
    tracker = aws_cloudwatch_log_group.services["tracker"].name
    node_a  = aws_cloudwatch_log_group.services["node-a"].name
    node_b  = aws_cloudwatch_log_group.services["node-b"].name
  }
}
