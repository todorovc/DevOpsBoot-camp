# CI/CD Pipeline with Terraform Infrastructure Provisioning

This project demonstrates a complete CI/CD pipeline that integrates infrastructure provisioning using Terraform. The pipeline automatically builds a Java Spring Boot application, creates a Docker image, provisions AWS EC2 infrastructure, and deploys the application.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Git Repository│───▶│   Jenkins CI/CD │───▶│   Docker Hub    │───▶│   AWS EC2       │
│                 │    │                 │    │                 │    │                 │
│ - Java App      │    │ - Build         │    │ - Store Images  │    │ - Run App       │
│ - Dockerfile    │    │ - Test          │    │ - Version Tags  │    │ - Auto-scaling  │
│ - Terraform     │    │ - Docker Build  │    │                 │    │ - Load Balancer │
│ - Jenkinsfile   │    │ - Terraform     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Technologies Used

- **Java Spring Boot**: Web application framework
- **Maven**: Build and dependency management
- **Docker**: Containerization
- **Terraform**: Infrastructure as Code
- **Jenkins**: CI/CD automation
- **AWS EC2**: Cloud compute instances
- **Docker Hub**: Container registry
- **Git**: Version control
- **Nginx**: Reverse proxy (optional)

## 📋 Prerequisites

### 1. Tools Required
- Docker and Docker Compose
- Git
- AWS CLI (configured)
- SSH key pair for EC2 access

### 2. Accounts Needed
- AWS Account with appropriate permissions
- Docker Hub account
- Git repository (GitHub/GitLab/etc.)

### 3. AWS Permissions Required
Your AWS user/role needs the following permissions:
- EC2 (create/manage instances, security groups, VPC)
- IAM (create key pairs)
- Route53 (if using custom domains)

## 🛠️ Setup Instructions

### Step 1: Clone and Prepare Repository

```bash
# Clone the repository
git clone <your-repository-url>
cd ci-cd-terraform-demo

# Update configuration files with your details
# Edit the following files:
# - Jenkinsfile (update DOCKER_HUB_REPO)
# - terraform/variables.tf (update defaults if needed)
# - docker-compose/docker-compose.yml (update image name)
```

### Step 2: Generate SSH Key Pair

```bash
# Generate SSH key pair for EC2 access
ssh-keygen -t rsa -b 4096 -f ~/.ssh/ci-cd-terraform-demo-key

# Get the public key content
cat ~/.ssh/ci-cd-terraform-demo-key.pub
```

### Step 3: Set Up Jenkins

```bash
# Navigate to Jenkins directory
cd jenkins

# Build and start Jenkins
docker-compose up -d

# Wait for Jenkins to start (check logs)
docker-compose logs -f

# Get initial admin password
docker exec jenkins-ci-cd cat /var/jenkins_home/secrets/initialAdminPassword
```

### Step 4: Configure Jenkins

1. **Access Jenkins**: Open http://localhost:8080
2. **Login**: Use the initial admin password from Step 3
3. **Install Plugins**: The required plugins are pre-configured
4. **Create Admin User**: Set up your admin credentials

### Step 5: Configure Jenkins Credentials

Add the following credentials in Jenkins (Manage Jenkins → Credentials):

#### Global Credentials:
1. **dockerhub-credentials** (Username/Password)
   - Username: Your Docker Hub username
   - Password: Your Docker Hub password/token

2. **aws-credentials** (AWS Credentials)
   - Access Key ID: Your AWS access key
   - Secret Access Key: Your AWS secret key

3. **ec2-ssh-key** (SSH Username with private key)
   - Username: `ec2-user`
   - Private Key: Content of `~/.ssh/ci-cd-terraform-demo-key`

4. **ec2-public-key** (Secret text)
   - Secret: Content of `~/.ssh/ci-cd-terraform-demo-key.pub`

### Step 6: Create Jenkins Pipeline Job

1. **New Item** → **Pipeline**
2. **Name**: ci-cd-terraform-demo
3. **Pipeline Configuration**:
   - Definition: Pipeline script from SCM
   - SCM: Git
   - Repository URL: Your repository URL
   - Script Path: Jenkinsfile

### Step 7: Update Configuration Files

Before running the pipeline, update these files with your specific details:

#### Jenkinsfile
```groovy
environment {
    DOCKER_HUB_REPO = 'YOUR_DOCKERHUB_USERNAME/ci-cd-demo'
    AWS_DEFAULT_REGION = 'us-west-2' // Change if needed
}
```

#### docker-compose/docker-compose.yml
```yaml
services:
  app:
    image: YOUR_DOCKERHUB_USERNAME/ci-cd-demo:latest
```

#### terraform/variables.tf
```hcl
variable "docker_image" {
  default = "YOUR_DOCKERHUB_USERNAME/ci-cd-demo:latest"
}
```

## 🚦 Running the Pipeline

### Manual Trigger
1. Go to Jenkins dashboard
2. Click on your pipeline job
3. Click "Build Now"

### Automatic Triggers (Optional)
Configure webhook in your Git repository to trigger builds on code changes.

## 📁 Project Structure

```
ci-cd-terraform-demo/
├── java-app/                    # Spring Boot application
│   ├── src/main/java/          # Java source code
│   ├── pom.xml                 # Maven configuration
│   └── Dockerfile              # App container configuration
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                 # Main Terraform configuration
│   ├── variables.tf            # Variable definitions
│   ├── outputs.tf              # Output definitions
│   └── user_data.sh            # EC2 initialization script
├── jenkins/                    # Jenkins setup
│   ├── Dockerfile              # Custom Jenkins image
│   ├── docker-compose.yml      # Jenkins container setup
│   └── plugins.txt             # Required Jenkins plugins
├── docker-compose/             # Application deployment
│   ├── docker-compose.yml      # Production deployment config
│   └── nginx.conf              # Reverse proxy configuration
├── scripts/                    # Utility scripts
├── Jenkinsfile                 # CI/CD pipeline definition
└── README.md                   # This file
```

## 🔄 Pipeline Stages

The CI/CD pipeline consists of the following stages:

1. **Checkout**: Clone the repository
2. **Build Maven Application**: Compile, test, and package the Java app
3. **Build Docker Image**: Create Docker image from JAR file
4. **Push Docker Image**: Push image to Docker Hub
5. **Provision Infrastructure**: Use Terraform to create AWS resources
6. **Wait for Instance Ready**: Ensure EC2 instance is accessible
7. **Deploy Application**: Deploy the Docker container to EC2
8. **Health Check**: Verify application is running correctly

## 🌐 Accessing the Application

After successful deployment, you can access:

- **Application**: http://\<EC2_PUBLIC_IP>:8080
- **Health Check**: http://\<EC2_PUBLIC_IP>:8080/health
- **Version Info**: http://\<EC2_PUBLIC_IP>:8080/version
- **Nginx Proxy**: http://\<EC2_PUBLIC_IP> (if enabled)

## 📊 Monitoring and Logging

### Application Logs
```bash
# SSH into the EC2 instance
ssh -i ~/.ssh/ci-cd-terraform-demo-key ec2-user@<EC2_PUBLIC_IP>

# View application logs
docker-compose -f /home/ec2-user/app/docker-compose.yml logs -f app
```

### Infrastructure Monitoring
- Monitor AWS resources through AWS Console
- Use CloudWatch for metrics and alerts
- Check Terraform state: `terraform show`

## 🧹 Cleanup

### Destroy AWS Resources
```bash
cd terraform
terraform destroy -auto-approve
```

### Stop Jenkins
```bash
cd jenkins
docker-compose down -v
```

## 🔧 Troubleshooting

### Common Issues

1. **Terraform Permission Errors**
   - Ensure AWS credentials have necessary permissions
   - Check IAM policies for EC2, VPC, and EIP operations

2. **Docker Build Failures**
   - Verify Dockerfile syntax
   - Check Maven build logs for Java compilation errors

3. **SSH Connection Issues**
   - Ensure security group allows SSH (port 22)
   - Verify SSH key pair is correctly configured
   - Check EC2 instance public IP and status

4. **Application Not Accessible**
   - Verify security group allows HTTP (ports 80, 8080)
   - Check Docker container logs
   - Ensure user data script completed successfully

### Debug Commands
```bash
# Check Jenkins logs
docker-compose -f jenkins/docker-compose.yml logs jenkins

# Verify Terraform state
cd terraform && terraform show

# Test SSH connectivity
ssh -i ~/.ssh/ci-cd-terraform-demo-key ec2-user@<EC2_IP>

# Check EC2 user data logs
sudo tail -f /var/log/cloud-init-output.log
```

## 📚 Additional Resources

- [Spring Boot Documentation](https://spring.io/projects/spring-boot)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This is a demo project for learning purposes. For production use, implement additional security measures, monitoring, and error handling.