# EKS CI/CD Pipeline

A complete CI/CD pipeline implementation using Amazon EKS (Elastic Kubernetes Service) and AWS ECR (Elastic Container Registry) with GitHub Actions.

## 🚀 Features

- **Containerized Application**: Node.js application with Docker
- **Infrastructure as Code**: Terraform for AWS resource management
- **Kubernetes Orchestration**: EKS cluster with auto-scaling
- **CI/CD Pipeline**: GitHub Actions for automated testing and deployment
- **Container Registry**: AWS ECR for secure container image storage
- **Monitoring & Logging**: CloudWatch integration with alerts
- **Security**: IAM roles with least privilege, vulnerability scanning
- **High Availability**: Multi-AZ deployment with load balancing

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub        │    │   AWS ECR        │    │   EKS Cluster   │
│   Repository    │───▶│   Container      │───▶│   Application   │
│   (CI/CD)       │    │   Registry       │    │   Deployment    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐                        ┌─────────────────┐
│   GitHub        │                        │   CloudWatch    │
│   Actions       │                        │   Monitoring    │
│   Runner        │                        │   & Logging     │
└─────────────────┘                        └─────────────────┘
```

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0
- kubectl
- Docker
- Node.js >= 18
- GitHub account with repository

## 🔧 Quick Start

### 1. Clone and Setup

```bash
git clone <your-repository-url>
cd eks-cicd-pipeline
```

### 2. Configure Variables

Update `terraform/variables.tf` with your specific values:

```hcl
variable "aws_region" {
  default = "us-west-2"  # Change to your preferred region
}

variable "github_repository" {
  default = "your-username/eks-cicd-pipeline"  # Update with your GitHub repo
}

variable "alert_email" {
  default = "your-email@example.com"  # Your email for alerts
}
```

### 3. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 4. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `AWS_ROLE_ARN`: The ARN of the GitHub Actions IAM role (from Terraform output)
- `SLACK_WEBHOOK`: (Optional) Slack webhook URL for notifications

### 5. Deploy Application

Push to the `main` branch to trigger the CI/CD pipeline:

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

## 📁 Project Structure

```
eks-cicd-pipeline/
├── app/                      # Node.js application
│   ├── server.js            # Main application
│   ├── package.json         # Dependencies
│   └── server.test.js       # Tests
├── terraform/               # Infrastructure as Code
│   ├── ecr.tf              # ECR repository configuration
│   ├── eks.tf              # EKS cluster configuration
│   ├── vpc.tf              # VPC and networking
│   ├── monitoring.tf       # CloudWatch monitoring
│   ├── variables.tf        # Terraform variables
│   └── outputs.tf          # Terraform outputs
├── k8s/                    # Kubernetes manifests
│   ├── deployment.yaml     # Application deployment
│   ├── service.yaml        # Load balancer service
│   ├── hpa.yaml           # Horizontal Pod Autoscaler
│   └── cloudwatch-insights.yaml # Monitoring setup
├── .github/workflows/      # CI/CD pipelines
│   ├── ci.yml             # Continuous Integration
│   └── cd.yml             # Continuous Deployment
├── scripts/               # Utility scripts
├── docs/                 # Additional documentation
└── README.md            # This file
```

## 🔄 CI/CD Pipeline

### Continuous Integration (CI)

Triggered on: Push to `main`/`develop`, Pull Requests to `main`

Steps:
1. **Code Checkout**: Gets the latest code
2. **Dependency Installation**: Installs Node.js dependencies
3. **Linting**: Runs ESLint for code quality
4. **Testing**: Executes unit tests with Jest
5. **Security Scan**: Vulnerability scanning with Trivy
6. **Docker Build**: Builds and tests Docker image

### Continuous Deployment (CD)

Triggered on: Push to `main` branch

Steps:
1. **AWS Authentication**: Uses OIDC for secure access
2. **ECR Login**: Authenticates with container registry
3. **Docker Build & Push**: Builds and pushes image to ECR
4. **EKS Deploy**: Updates Kubernetes deployment
5. **Health Check**: Verifies deployment success
6. **Notifications**: Sends Slack notifications (optional)

## 📊 Monitoring & Logging

### CloudWatch Integration

- **Metrics**: CPU, Memory, Network, Custom application metrics
- **Logs**: Application logs, EKS cluster logs
- **Alarms**: Automated alerts for high resource usage, pod restarts
- **Dashboard**: Visual monitoring dashboard

### Available Endpoints

- `/health` - Health check endpoint
- `/metrics` - Application metrics
- `/` - Main application endpoint

## 🔒 Security Features

- **IAM Roles**: Least privilege access with role-based permissions
- **OIDC Integration**: Secure GitHub Actions authentication
- **Container Security**: Non-root user, read-only filesystem
- **Network Security**: Private subnets, security groups
- **Image Scanning**: Automatic vulnerability detection
- **Secrets Management**: AWS Systems Manager integration

## 📈 Scaling

### Horizontal Pod Autoscaler (HPA)

- **Min Replicas**: 3
- **Max Replicas**: 10
- **CPU Threshold**: 70%
- **Memory Threshold**: 80%

### Cluster Autoscaler

- **Node Groups**: Auto-scaling based on demand
- **Instance Types**: t3.medium (configurable)
- **Min Nodes**: 1
- **Max Nodes**: 4

## 🛠️ Maintenance

### Updating the Application

1. Make changes to `app/` directory
2. Update tests in `app/server.test.js`
3. Commit and push to trigger CI/CD

### Infrastructure Updates

1. Modify Terraform files in `terraform/`
2. Run `terraform plan` and `terraform apply`
3. Update Kubernetes manifests if needed

### Monitoring Health

1. Check CloudWatch Dashboard
2. Review EKS cluster status
3. Monitor application logs

## 🚨 Troubleshooting

### Common Issues

1. **Pipeline Failures**
   - Check GitHub Actions logs
   - Verify AWS permissions
   - Ensure secrets are configured

2. **Deployment Issues**
   - Check kubectl logs: `kubectl logs deployment/eks-cicd-app`
   - Verify image exists in ECR
   - Check resource limits

3. **Access Issues**
   - Update kubeconfig: `aws eks update-kubeconfig --region us-west-2 --name eks-cicd-cluster`
   - Verify IAM permissions

### Useful Commands

```bash
# Check cluster status
kubectl get nodes

# View application pods
kubectl get pods -l app=eks-cicd-app

# Check service status
kubectl get services

# View logs
kubectl logs -l app=eks-cicd-app --tail=100

# Port forward for local testing
kubectl port-forward service/eks-cicd-app-internal 3000:3000
```

## 📚 Documentation

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if needed
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Resources

- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Container Security](https://kubernetes.io/docs/concepts/security/)
- [Monitoring Kubernetes](https://kubernetes.io/docs/tasks/debug-application-cluster/)

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review GitHub Actions logs
3. Check AWS CloudWatch logs
4. Create an issue in this repository