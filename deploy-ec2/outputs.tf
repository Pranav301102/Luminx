output "head_ip" {
  description = "Public IP of the Head instance (Node A + Tracker)"
  value       = aws_instance.head.public_ip
}

output "tail_ip" {
  description = "Public IP of the Tail instance (Node B)"
  value       = aws_instance.tail.public_ip
}

output "frontend_ip" {
  description = "Public IP of the Frontend instance"
  value       = aws_instance.frontend.public_ip
}

output "frontend_url" {
  description = "Public URL of the frontend"
  value       = "http://${aws_instance.frontend.public_ip}"
}

output "generate_endpoint" {
  description = "Direct API endpoint for text generation"
  value       = "http://${aws_instance.head.public_ip}:8001/generate"
}

output "ssh_head" {
  value = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_instance.head.public_ip}"
}

output "ssh_tail" {
  value = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_instance.tail.public_ip}"
}

output "ssh_frontend" {
  value = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_instance.frontend.public_ip}"
}
