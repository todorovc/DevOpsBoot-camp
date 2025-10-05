# Automated Kubernetes Deployment Project

This project demonstrates automated Kubernetes deployment using **Terraform** for infrastructure provisioning and **Ansible** for application deployment on AWS EKS.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Terraform     │───▶│   AWS EKS       │───▶│   Python App    │
│   (Infrastructure)   │   (Kubernetes)   │    │   (Containerized) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │    Ansible      │
                       │   (Deployment)  │
                       └─────────────────┘
```

## 🚀 Technologies Used

- **Terraform**: Infrastructure as Code (IaC)
- **Ansible**: Configuration Management & Application Deployment
- **AWS EKS**: Managed Kubernetes Service
- **Python Flask**: Demo Web Application
- **Docker**: Containerization
- **Kubernetes**: Container Orchestration

## 📋 Prerequisites

### Required Tools
- [Terraform](https://terraform.io/downloads.html) >= 1.0
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/index.html) >= 2.9
- [AWS CLI](https://aws.amazon.com/cli/) >= 2.0
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) >= 1.28
- [Docker](https://docs.docker.com/get-docker/) >= 20.0
- [Python](https://python.org) >= 3.8

### AWS Configuration
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="eu-west-1"
```

### Python Dependencies
```bash
# Install Python dependencies for Ansible
pip install -r requirements.txt
```

## 📁 Project Structure

```
k8s-automation-project/
├── terraform/                 # Infrastructure as Code
│   ├── main.tf                # Main Terraform configuration
│   ├── variables.tf           # Input variables
│   ├── outputs.tf             # Output values
│   ├── terraform.tfvars.example # Example variables file
│   └── modules/               # Terraform modules
│       ├── vpc/               # VPC module
│       ├── eks/               # EKS cluster module
│       └── security-groups/   # Security groups module
├── ansible/                   # Configuration Management
│   ├── playbooks/             # Ansible playbooks
│   │   └── deploy-app.yml     # Main deployment playbook
│   ├── roles/                 # Ansible roles
│   │   └── app-deploy/        # Application deployment role
│   ├── inventory.ini          # Ansible inventory
│   ├── ansible.cfg            # Ansible configuration
│   └── group_vars/            # Group variables
├── app/                       # Application code
│   ├── src/                   # Python Flask application
│   │   ├── app.py             # Main application
│   │   └── requirements.txt   # Python dependencies
│   ├── Dockerfile             # Container definition
│   └── k8s-manifests/         # Kubernetes manifests
├── scripts/                   # Automation scripts
├── docs/                      # Documentation
├── requirements.txt           # Project dependencies
└── README.md                  # This file
```

## 🛠️ Setup Instructions

### 1. Clone the Project
```bash
git clone <repository-url>
cd k8s-automation-project
```

### 2. Configure Terraform
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your configurations
```

### 3. Configure Ansible
```bash
cd ../ansible
mkdir -p group_vars
cp group_vars/all.yml.example group_vars/all.yml
# Edit group_vars/all.yml with your configurations
```

## 🚀 Deployment Guide

### Step 1: Deploy Infrastructure with Terraform

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

This will create:
- VPC with public and private subnets
- Internet Gateway and NAT Gateways
- Security Groups
- EKS Cluster with managed node group
- IAM roles and policies

### Step 2: Build and Push Docker Image

```bash
# Navigate to app directory
cd ../app

# Build Docker image
docker build -t demo-k8s-app:latest .

# Tag and push to your container registry (ECR, DockerHub, etc.)
# Example for ECR:
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.eu-west-1.amazonaws.com
docker tag demo-k8s-app:latest <account-id>.dkr.ecr.eu-west-1.amazonaws.com/demo-k8s-app:latest
docker push <account-id>.dkr.ecr.eu-west-1.amazonaws.com/demo-k8s-app:latest
```

### Step 3: Deploy Application with Ansible

```bash
# Navigate to ansible directory
cd ../ansible

# Update kubeconfig
aws eks update-kubeconfig --region eu-west-1 --name k8s-demo-dev

# Deploy the application
ansible-playbook playbooks/deploy-app.yml

# Or with custom variables
ansible-playbook playbooks/deploy-app.yml -e cluster_name=your-cluster-name -e app_replicas=5
```

## 🔍 Verification

### Check Infrastructure
```bash
# Verify Terraform deployment
terraform output

# Check EKS cluster
aws eks describe-cluster --name k8s-demo-dev --region eu-west-1
```

### Check Application
```bash
# Check cluster connection
kubectl cluster-info

# Check namespace
kubectl get namespaces

# Check deployment
kubectl get deployments -n demo-app

# Check pods
kubectl get pods -n demo-app

# Check service
kubectl get svc -n demo-app

# Check ingress (if ALB controller is installed)
kubectl get ingress -n demo-app
```

### Access the Application
```bash
# Port forward to access locally
kubectl port-forward svc/demo-k8s-app-service 8080:80 -n demo-app

# Visit http://localhost:8080 in your browser
```

## 📊 Monitoring and Troubleshooting

### View Logs
```bash
# View pod logs
kubectl logs -f deployment/demo-k8s-app -n demo-app

# View previous pod logs
kubectl logs --previous <pod-name> -n demo-app
```

### Debug Issues
```bash
# Describe resources
kubectl describe deployment demo-k8s-app -n demo-app
kubectl describe pod <pod-name> -n demo-app

# Check events
kubectl get events -n demo-app --sort-by=.metadata.creationTimestamp
```

## 🧹 Cleanup

### Remove Application
```bash
# Delete Kubernetes resources
kubectl delete namespace demo-app

# Or use Ansible
ansible-playbook playbooks/deploy-app.yml -e state=absent
```

### Destroy Infrastructure
```bash
cd terraform
terraform destroy
```

## 🔧 Customization

### Terraform Variables
Edit `terraform/terraform.tfvars`:
- `aws_region`: AWS region for deployment
- `cluster_version`: Kubernetes version
- `node_instance_types`: EC2 instance types for worker nodes
- `desired_capacity`, `min_capacity`, `max_capacity`: Auto Scaling configuration

### Ansible Variables
Edit `ansible/group_vars/all.yml`:
- `app_replicas`: Number of application replicas
- `docker_image`: Container image to deploy
- `enable_ingress`: Enable/disable ingress creation

## 📈 Advanced Features

### Auto Scaling
The EKS cluster includes:
- Horizontal Pod Autoscaler (HPA) ready configuration
- Cluster Autoscaler support
- Configurable node group scaling

### Security
- Non-root container execution
- Security contexts and capabilities dropping
- Network policies ready
- RBAC integration

### High Availability
- Multi-AZ deployment
- Load balancer integration
- Health checks and probes
- Rolling updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions or issues:
1. Check the troubleshooting section
2. Review AWS EKS documentation
3. Check Terraform and Ansible documentation
4. Create an issue in the repository

## 📚 Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)
- [Ansible Kubernetes Collection](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

**Happy Deploying! 🚀**
