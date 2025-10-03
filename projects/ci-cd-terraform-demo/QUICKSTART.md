# 🚀 Quick Start Guide

Get your CI/CD pipeline with Terraform up and running in 10 minutes!

## Prerequisites ✅

- Docker & Docker Compose installed
- AWS account with access keys
- Docker Hub account
- Git installed

## 1. Setup Project (2 minutes)

```bash
# Navigate to project directory
cd ci-cd-terraform-demo

# Run the setup script
./scripts/setup.sh
```

This script will:
- Generate SSH keys for EC2 access
- Update configuration files with your details
- Create terraform.tfvars file
- Initialize Git repository (optional)

## 2. Start Jenkins (3 minutes)

```bash
# Start Jenkins
cd jenkins
docker-compose up -d

# Get admin password
docker exec jenkins-ci-cd cat /var/jenkins_home/secrets/initialAdminPassword
```

Access Jenkins at http://localhost:8080 and complete the setup wizard.

## 3. Configure Jenkins Credentials (3 minutes)

Go to **Manage Jenkins → Credentials → Global** and add:

1. **dockerhub-credentials** (Username/Password)
2. **aws-credentials** (AWS Credentials) 
3. **ec2-ssh-key** (SSH private key from ~/.ssh/ci-cd-terraform-demo-key)
4. **ec2-public-key** (SSH public key content as secret text)

## 4. Create Pipeline Job (1 minute)

1. **New Item → Pipeline**
2. **Name**: ci-cd-terraform-demo
3. **Pipeline**: Script from SCM
4. **SCM**: Git
5. **Repository URL**: Your Git repository URL
6. **Script Path**: Jenkinsfile

## 5. Deploy! (1 minute)

Click **"Build Now"** and watch your application deploy automatically!

## 📍 What Gets Created

- ☁️ AWS VPC with public subnet
- 🖥️ EC2 instance with Docker & Docker Compose
- 🔐 Security groups for SSH and HTTP access
- 🌐 Elastic IP for stable access
- 🐳 Docker containers running your application

## 🌐 Access Your Application

After successful deployment:

- **Main App**: http://\<EC2_IP>:8080
- **Health Check**: http://\<EC2_IP>:8080/health
- **Version Info**: http://\<EC2_IP>:8080/version

## 🧹 Cleanup

```bash
# Destroy AWS resources
cd terraform
terraform destroy -auto-approve

# Stop Jenkins
cd ../jenkins
docker-compose down -v
```

## 🚨 Troubleshooting

**Common Issues:**

1. **Permission Denied**: Ensure AWS credentials have EC2/VPC permissions
2. **SSH Issues**: Check security groups allow port 22
3. **Build Fails**: Verify Docker Hub credentials and repository name

**Need Help?** Check the full [README.md](README.md) for detailed instructions.

---

**🎉 Congratulations!** You now have a complete CI/CD pipeline that provisions infrastructure and deploys applications automatically!