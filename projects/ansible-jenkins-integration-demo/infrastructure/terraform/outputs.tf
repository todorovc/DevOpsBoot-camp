output "jenkins_server_ip" {
  description = "Public IP address of Jenkins server"
  value       = digitalocean_droplet.jenkins_server.ipv4_address
}

output "ansible_control_ip" {
  description = "Public IP address of Ansible control node"
  value       = digitalocean_droplet.ansible_control.ipv4_address
}

output "web_server_ip" {
  description = "Public IP address of AWS web server"
  value       = aws_instance.web_server.public_ip
}

output "app_server_ip" {
  description = "Public IP address of AWS application server"
  value       = aws_instance.app_server.public_ip
}

output "web_server_private_ip" {
  description = "Private IP address of AWS web server"
  value       = aws_instance.web_server.private_ip
}

output "app_server_private_ip" {
  description = "Private IP address of AWS application server"
  value       = aws_instance.app_server.private_ip
}

output "jenkins_url" {
  description = "Jenkins server URL"
  value       = "http://${digitalocean_droplet.jenkins_server.ipv4_address}:8080"
}