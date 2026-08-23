output "public_ip" {
  description = "Static Public IP Address"
  value       = aws_eip.aidubbing_eip.public_ip
}

output "app_url" {
  description = "App URL — Browser-ல இதை open பண்ணுங்க"
  value       = "http://${aws_eip.aidubbing_eip.public_ip}:8000"
}

output "health_check_url" {
  description = "Health Check Endpoint"
  value       = "http://${aws_eip.aidubbing_eip.public_ip}:8000/health"
}

output "api_docs_url" {
  description = "FastAPI Swagger Docs"
  value       = "http://${aws_eip.aidubbing_eip.public_ip}:8000/docs"
}

output "ssh_command" {
  description = "SSH Command — EC2-ல login ஆக"
  value       = "ssh -i ~/.ssh/aidubbing-key.pem ubuntu@${aws_eip.aidubbing_eip.public_ip}"
}

output "instance_id" {
  description = "EC2 Instance ID"
  value       = aws_instance.aidubbing_ec2.id
}
