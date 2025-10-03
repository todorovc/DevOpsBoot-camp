terraform {
  required_version = ">= 1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}

# AWS Provider
provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

# SSH Key for DigitalOcean droplets
resource "digitalocean_ssh_key" "default" {
  name       = "ansible-jenkins-demo-key"
  public_key = file(var.public_key_path)
}

# Jenkins Server on DigitalOcean
resource "digitalocean_droplet" "jenkins_server" {
  image    = "ubuntu-22-04-x64"
  name     = "jenkins-server"
  region   = var.do_region
  size     = "s-2vcpu-4gb"
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]

  tags = ["jenkins", "ci-cd", "demo"]

  user_data = file("${path.module}/../scripts/jenkins-setup.sh")
}

# Ansible Control Node on DigitalOcean
resource "digitalocean_droplet" "ansible_control" {
  image    = "ubuntu-22-04-x64"
  name     = "ansible-control-node"
  region   = var.do_region
  size     = "s-1vcpu-2gb"
  ssh_keys = [digitalocean_ssh_key.default.fingerprint]

  tags = ["ansible", "control-node", "demo"]

  user_data = file("${path.module}/../scripts/ansible-control-setup.sh")
}

# Security Group for AWS EC2 instances
resource "aws_security_group" "managed_nodes_sg" {
  name        = "ansible-managed-nodes-sg"
  description = "Security group for Ansible managed nodes"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ansible-managed-nodes-sg"
  }
}

# Key Pair for AWS EC2 instances
resource "aws_key_pair" "managed_nodes_key" {
  key_name   = "ansible-managed-nodes-key"
  public_key = file(var.aws_public_key_path)
}

# EC2 Instance 1 - Web Server
resource "aws_instance" "web_server" {
  ami                    = var.aws_ami
  instance_type          = "t2.micro"
  key_name              = aws_key_pair.managed_nodes_key.key_name
  vpc_security_group_ids = [aws_security_group.managed_nodes_sg.id]

  tags = {
    Name = "ansible-managed-web-server"
    Type = "web-server"
    Environment = "demo"
  }
}

# EC2 Instance 2 - Application Server
resource "aws_instance" "app_server" {
  ami                    = var.aws_ami
  instance_type          = "t2.micro"
  key_name              = aws_key_pair.managed_nodes_key.key_name
  vpc_security_group_ids = [aws_security_group.managed_nodes_sg.id]

  tags = {
    Name = "ansible-managed-app-server"
    Type = "app-server"
    Environment = "demo"
  }
}

# DigitalOcean Firewall for Jenkins
resource "digitalocean_firewall" "jenkins_firewall" {
  name = "jenkins-firewall"

  droplet_ids = [digitalocean_droplet.jenkins_server.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# DigitalOcean Firewall for Ansible Control Node
resource "digitalocean_firewall" "ansible_firewall" {
  name = "ansible-control-firewall"

  droplet_ids = [digitalocean_droplet.ansible_control.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}