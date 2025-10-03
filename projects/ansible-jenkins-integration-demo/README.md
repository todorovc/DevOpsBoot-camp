# Ansible Integration in Jenkins - Demo Project

This project demonstrates a complete CI/CD pipeline integration between Jenkins and Ansible, showcasing infrastructure automation and application deployment across multiple cloud providers.

## 🏗️ Architecture Overview

The demo creates the following infrastructure:

- **Jenkins Server** (DigitalOcean): CI/CD orchestration
- **Ansible Control Node** (DigitalOcean): Ansible automation hub  
- **2x EC2 Instances** (AWS): Managed nodes (Web Server + App Server)

## 🛠️ Technologies Used

- **Infrastructure**: Terraform, DigitalOcean, AWS
- **Automation**: Ansible, Jenkins Pipeline
- **Application**: Java 11, Spring Boot, Maven
- **Containerization**: Docker
- **Operating System**: Ubuntu 22.04 LTS
- **Version Control**: Git

## 📁 Project Structure

```
ansible-jenkins-integration-demo/
├── ansible/                          # Ansible configuration and playbooks
│   ├── ansible.cfg                   # Ansible configuration
│   ├── inventory/                    # Inventory files
│   │   ├── hosts                     # Static inventory
│   │   └── aws_ec2.yml              # Dynamic AWS inventory
│   ├── group_vars/                   # Group variables
│   │   ├── all.yml                   # Common variables
│   │   ├── webservers.yml           # Web server variables
│   │   └── appservers.yml           # App server variables
│   └── playbooks/                    # Ansible playbooks
│       ├── site.yml                 # Main infrastructure playbook
│       ├── deploy-app.yml           # Application deployment playbook
│       └── templates/               # Jinja2 templates
├── infrastructure/                   # Infrastructure as Code
│   ├── terraform/                   # Terraform configurations
│   │   ├── main.tf                  # Main Terraform configuration
│   │   ├── variables.tf             # Variable definitions
│   │   ├── outputs.tf               # Output definitions
│   │   └── terraform.tfvars.example # Example variables file
│   └── scripts/                     # Setup and deployment scripts
│       ├── generate-keys.sh         # SSH key generation
│       ├── deploy-infrastructure.sh # Infrastructure deployment
│       ├── jenkins-setup.sh         # Jenkins server setup
│       └── ansible-control-setup.sh # Ansible control node setup
├── jenkins/                         # Jenkins pipeline configuration
│   ├── Jenkinsfile                  # Main pipeline
│   └── test-pipeline.groovy         # Test pipeline
├── sample-app/                      # Demo Java application
│   ├── pom.xml                      # Maven configuration
│   ├── src/main/java/com/example/   # Application source code
│   └── src/test/java/com/example/   # Test code
├── keys/                            # SSH keys (gitignored)
└── docs/                           # Additional documentation
```

## 🚀 Quick Start

### Prerequisites

1. **Required Tools:**
   - Terraform >= 1.0
   - Git
   - SSH client

2. **Cloud Account Setup:**
   - DigitalOcean account with API token
   - AWS account with access keys
   - Sufficient permissions to create VMs, security groups, etc.

### Step 1: Clone and Setup

```bash
git clone <repository-url>
cd ansible-jenkins-integration-demo
```

### Step 2: Generate SSH Keys

```bash
chmod +x infrastructure/scripts/generate-keys.sh
./infrastructure/scripts/generate-keys.sh
```

### Step 3: Configure Terraform Variables

```bash
cp infrastructure/terraform/terraform.tfvars.example infrastructure/terraform/terraform.tfvars
# Edit terraform.tfvars with your actual API tokens and keys
```

### Step 4: Deploy Infrastructure

```bash
chmod +x infrastructure/scripts/deploy-infrastructure.sh
./infrastructure/scripts/deploy-infrastructure.sh plan   # Review the plan
./infrastructure/scripts/deploy-infrastructure.sh apply  # Deploy
```

### Step 5: Configure Jenkins

1. Access Jenkins at the provided URL
2. Get initial admin password:
   ```bash
   ssh -i keys/do_rsa ubuntu@<jenkins-ip> 'sudo cat /var/lib/jenkins/secrets/initialAdminPassword'
   ```
3. Install suggested plugins
4. Add credentials for SSH keys and server IPs

### Step 6: Update Ansible Inventory

Update `ansible/inventory/hosts` with the actual IP addresses from Terraform output.

### Step 7: Run the Pipeline

Create a new Jenkins pipeline job and run the deployment.

## 🔧 Detailed Configuration

### Jenkins Pipeline Configuration

The pipeline performs the following stages:

1. **Checkout**: Clone the source code
2. **Build Application**: Compile and test the Java application
3. **Prepare Ansible Control Node**: Copy SSH keys and setup environment
4. **Copy Configuration**: Transfer Ansible playbooks and configuration
5. **Install Dependencies**: Install Ansible, Python3, and Boto3
6. **Execute Playbooks**: Run infrastructure and application deployment playbooks
7. **Verify Deployment**: Check service status and connectivity

### Ansible Playbook Details

#### Infrastructure Playbook (`site.yml`)
- **Common Configuration**: Updates packages, creates users, configures SSH
- **Web Server Setup**: Installs and configures Nginx as reverse proxy
- **Application Server Setup**: Installs Java, Docker, and prepares app environment
- **Security Configuration**: Configures firewall rules and SSH hardening

#### Application Deployment (`deploy-app.yml`)
- **Zero-downtime Deployment**: Stops service, backs up current version, deploys new version
- **Health Checks**: Verifies application startup and API endpoints
- **Rollback Capability**: Maintains backup versions for quick rollback

### Infrastructure Components

#### Jenkins Server Features:
- Pre-installed Java 11, Maven, Docker, Git
- Jenkins with security plugins
- SSH agent for remote connections
- Automated initial setup

#### Ansible Control Node Features:
- Python3, Ansible, Boto3 for AWS integration
- Pre-configured Ansible settings
- Secure SSH key management
- Jenkins integration scripts

#### Managed Nodes (EC2):
- Ubuntu 22.04 LTS
- Security groups for web traffic (80, 8080) and SSH (22)
- Automatic tagging for Ansible discovery
- EBS-optimized instances

## 📊 Pipeline Parameters

The Jenkins pipeline supports several parameters:

- **DEPLOY_ENVIRONMENT**: Choose between `infrastructure`, `application`, or `full-deployment`
- **SKIP_TESTS**: Boolean to skip Maven tests
- **PLAYBOOK_TAGS**: Comma-separated list of Ansible tags to run

## 🔒 Security Considerations

### SSH Key Management
- Private keys are automatically generated and protected
- Keys are never committed to version control
- Proper file permissions (600) are enforced

### Network Security
- Firewalls configured on all instances
- SSH access limited to key-based authentication
- Root login disabled on all servers

### Jenkins Security
- Credentials stored securely in Jenkins credential store
- SSH agent used for secure key handling
- Temporary files cleaned up after pipeline execution

## 🧪 Testing

### Local Testing
```bash
cd sample-app
mvn test                    # Run unit tests
mvn spring-boot:run        # Run application locally
```

### Pipeline Testing
Use the test pipeline (`jenkins/test-pipeline.groovy`) to verify:
- Connection to Ansible Control Node
- Ansible inventory configuration
- SSH connectivity

## 🐛 Troubleshooting

### Common Issues

1. **SSH Connection Failures**
   - Verify SSH keys are properly generated
   - Check security group rules allow SSH (port 22)
   - Ensure private keys have correct permissions (600)

2. **Terraform Apply Failures**
   - Verify API tokens are correct and have proper permissions
   - Check if resource limits are exceeded
   - Ensure SSH keys exist before applying

3. **Ansible Playbook Failures**
   - Check inventory file has correct IP addresses
   - Verify SSH connectivity to managed nodes
   - Ensure Ansible is properly installed on control node

4. **Jenkins Pipeline Failures**
   - Verify Jenkins credentials are configured correctly
   - Check Ansible Control Node is accessible
   - Ensure all required plugins are installed

### Debug Commands

```bash
# Test Terraform configuration
cd infrastructure/terraform
terraform validate
terraform plan

# Test Ansible connectivity
cd ansible
ansible all -m ping -i inventory/hosts

# Test application locally
cd sample-app
mvn clean test
java -jar target/demo-app-1.0.0.jar
curl http://localhost:8080/health
```

## 📈 Monitoring and Logging

### Application Monitoring
- Health check endpoint: `http://<server>:8080/health`
- Metrics endpoint: `http://<server>:8080/actuator/metrics`
- Application logs: `/var/log/demo-app/demo-app.log`

### System Monitoring
- Service status: `systemctl status demo-app`
- System resources: `htop`, `df -h`, `free -m`
- Network connectivity: `netstat -tulpn`

## 🔄 Maintenance

### Regular Tasks
1. Update AMI IDs for different regions
2. Rotate SSH keys periodically
3. Update application dependencies
4. Review and update security groups

### Backup Strategy
- Application backups are automatically created during deployments
- Infrastructure is fully reproducible via Terraform
- Consider backing up Jenkins configuration and job definitions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test thoroughly
4. Update documentation as needed
5. Submit a pull request

## 📜 License

This project is for educational purposes. See LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs from Jenkins pipeline
3. Check cloud provider status pages
4. Open an issue with detailed error messages and logs

---

**⚠️ Important Notes:**
- This is a demo project intended for learning purposes
- Production deployments should include additional security measures
- Monitor cloud costs as resources will incur charges
- Always destroy resources when no longer needed using `./deploy-infrastructure.sh destroy`