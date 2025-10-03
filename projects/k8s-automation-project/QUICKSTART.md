# 🚀 Quick Start Guide

This guide will help you quickly deploy the Kubernetes demo application to AWS EKS.

## Prerequisites Check

Run this command to verify you have all required tools:
```bash
# Check if tools are installed
terraform --version
ansible --version
aws --version
kubectl version --client
docker --version
```

## 1. Setup AWS Credentials

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"
```

## 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 3. One-Command Deployment

```bash
# Deploy everything
./scripts/deploy.sh
```

This single command will:
- ✅ Deploy EKS infrastructure with Terraform
- ✅ Build the Docker image
- ✅ Deploy the application with Ansible
- ✅ Validate the deployment

## 4. Access Your Application

After deployment completes:

```bash
# Port-forward to access the app
kubectl port-forward svc/demo-k8s-app-service 8080:80 -n demo-app

# Open in browser: http://localhost:8080
```

## 5. Validate Deployment

```bash
# Check everything is working
./scripts/validate.sh
```

## 6. Cleanup

```bash
# Remove everything
./scripts/cleanup.sh
```

## Customization Options

### Skip Steps
```bash
# Skip Terraform (if infrastructure exists)
./scripts/deploy.sh --skip-terraform

# Skip Docker build
./scripts/deploy.sh --skip-docker

# Skip Ansible deployment  
./scripts/deploy.sh --skip-ansible
```

### Different Regions/Environments
```bash
# Deploy to different region
./scripts/deploy.sh --region us-east-1 --env prod
```

### Custom Configuration
```bash
# Edit Terraform variables
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit the file with your preferences

# Edit Ansible variables
mkdir -p ansible/group_vars
cp ansible/group_vars/all.yml.example ansible/group_vars/all.yml
# Edit the file with your preferences
```

## Troubleshooting

### Common Issues

1. **AWS Permissions Error**
   ```bash
   # Check your AWS credentials
   aws sts get-caller-identity
   ```

2. **kubectl Not Working**
   ```bash
   # Update kubeconfig
   aws eks update-kubeconfig --region us-west-2 --name k8s-demo-dev
   ```

3. **Application Not Responding**
   ```bash
   # Check pod status
   kubectl get pods -n demo-app
   kubectl logs -f deployment/demo-k8s-app -n demo-app
   ```

### Getting Help

- Run any script with `--help` for options
- Check the main [README.md](README.md) for detailed documentation
- Validate deployment status: `./scripts/validate.sh`

## What You Get

After successful deployment:

- ✅ **EKS Cluster**: Managed Kubernetes cluster with 2+ worker nodes
- ✅ **VPC**: Custom VPC with public/private subnets across 3 AZs
- ✅ **Python App**: Flask web application with health checks
- ✅ **Load Balancing**: Service and optional ingress with ALB
- ✅ **Security**: Non-root containers, security contexts
- ✅ **Monitoring**: Built-in health and readiness probes

## Next Steps

1. **Add Monitoring**: Install Prometheus/Grafana
2. **CI/CD Pipeline**: Set up automated deployments
3. **Scaling**: Configure HPA and cluster autoscaler
4. **Security**: Add network policies and RBAC
5. **Logging**: Set up centralized logging with ELK/CloudWatch

---

**Time to deploy: ~10-15 minutes** ⏱️

Happy deploying! 🎉