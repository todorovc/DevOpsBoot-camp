variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "do_region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc1"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS access key"
  type        = string
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS secret key"
  type        = string
  sensitive   = true
}

variable "aws_ami" {
  description = "AWS AMI ID for EC2 instances (Ubuntu 22.04 LTS)"
  type        = string
  default     = "ami-0c02fb55956c7d316" # Ubuntu 22.04 LTS in us-east-1
}

variable "public_key_path" {
  description = "Path to the public key file for DigitalOcean droplets"
  type        = string
  default     = "../../keys/do_rsa.pub"
}

variable "aws_public_key_path" {
  description = "Path to the public key file for AWS EC2 instances"
  type        = string
  default     = "../../keys/aws_rsa.pub"
}