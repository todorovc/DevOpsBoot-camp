#!/bin/bash

# EKS CI/CD Pipeline Deployment Script
# This script automates the deployment of the entire infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
AWS_REGION="us-west-2"
CLUSTER_NAME="eks-cicd-cluster"
GITHUB_REPO=""
ALERT_EMAIL=""
ENVIRONMENT="dev"

# Helper functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command_exists aws; then
        missing_tools+=("aws-cli")
    fi
    
    if ! command_exists terraform; then
        missing_tools+=("terraform")
    fi
    
    if ! command_exists kubectl; then
        missing_tools+=("kubectl")
    fi
    
    if ! command_exists docker; then
        missing_tools+=("docker")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_info "Please install the missing tools and try again."
        exit 1
    fi
    
    print_success "All prerequisites are installed"
}

# Check AWS credentials
check_aws_credentials() {
    print_info "Checking AWS credentials..."
    
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured or invalid"
        print_info "Please run 'aws configure' to set up your credentials"
        exit 1
    fi
    
    print_success "AWS credentials are configured"
}

# Get user inputs
get_user_inputs() {
    print_info "Collecting configuration..."
    
    # AWS Region
    read -p "AWS Region [$AWS_REGION]: " user_region
    AWS_REGION=${user_region:-$AWS_REGION}
    
    # GitHub Repository
    while [ -z "$GITHUB_REPO" ]; do
        read -p "GitHub Repository (format: owner/repo): " GITHUB_REPO
        if [ -z "$GITHUB_REPO" ]; then
            print_warning "GitHub repository is required"
        fi
    done
    
    # Alert Email
    read -p "Alert Email (optional): " ALERT_EMAIL
    
    # Environment
    read -p "Environment [$ENVIRONMENT]: " user_env
    ENVIRONMENT=${user_env:-$ENVIRONMENT}
    
    print_info "Configuration:"
    echo "  AWS Region: $AWS_REGION"
    echo "  GitHub Repo: $GITHUB_REPO"
    echo "  Alert Email: ${ALERT_EMAIL:-'Not provided'}"
    echo "  Environment: $ENVIRONMENT"
    
    read -p "Continue with this configuration? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "Deployment cancelled"
        exit 0
    fi
}

# Update Terraform variables
update_terraform_variables() {
    print_info "Updating Terraform variables..."
    
    cat > terraform/terraform.tfvars <<EOF
aws_region = "$AWS_REGION"
github_repository = "$GITHUB_REPO"
alert_email = "$ALERT_EMAIL"
environment = "$ENVIRONMENT"
cluster_name = "$CLUSTER_NAME"
EOF
    
    print_success "Terraform variables updated"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_info "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    print_info "Initializing Terraform..."
    terraform init
    
    # Validate configuration
    print_info "Validating Terraform configuration..."
    terraform validate
    
    # Plan deployment
    print_info "Creating Terraform plan..."
    terraform plan -var-file="terraform.tfvars" -out=tfplan
    
    # Apply deployment
    print_info "Applying Terraform configuration..."
    if terraform apply tfplan; then
        print_success "Infrastructure deployed successfully"
    else
        print_error "Failed to deploy infrastructure"
        exit 1
    fi
    
    cd ..
}

# Get Terraform outputs
get_terraform_outputs() {
    print_info "Getting Terraform outputs..."
    
    cd terraform
    
    ECR_URL=$(terraform output -raw ecr_repository_url)
    GITHUB_ROLE_ARN=$(terraform output -raw github_actions_role_arn)
    CLUSTER_ENDPOINT=$(terraform output -raw cluster_endpoint)
    
    cd ..
    
    print_info "Infrastructure outputs:"
    echo "  ECR Repository URL: $ECR_URL"
    echo "  GitHub Actions Role ARN: $GITHUB_ROLE_ARN"
    echo "  EKS Cluster Endpoint: $CLUSTER_ENDPOINT"
}

# Configure kubectl
configure_kubectl() {
    print_info "Configuring kubectl..."
    
    aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME"
    
    if kubectl get nodes >/dev/null 2>&1; then
        print_success "kubectl configured successfully"
        print_info "Cluster nodes:"
        kubectl get nodes
    else
        print_error "Failed to configure kubectl"
        exit 1
    fi
}

# Deploy monitoring
deploy_monitoring() {
    print_info "Setting up monitoring and logging..."
    
    # Apply CloudWatch Container Insights
    envsubst <<< "$(cat k8s/cloudwatch-insights.yaml)" | kubectl apply -f -
    
    print_success "Monitoring configured"
}

# Display next steps
display_next_steps() {
    print_success "Deployment completed successfully!"
    print_info "Next steps:"
    echo
    echo "1. Configure GitHub repository secrets:"
    echo "   - AWS_ROLE_ARN: $GITHUB_ROLE_ARN"
    if [ -n "$ALERT_EMAIL" ]; then
        echo "   - SLACK_WEBHOOK: (Optional) Your Slack webhook URL"
    fi
    echo
    echo "2. Push your code to trigger the CI/CD pipeline:"
    echo "   git add ."
    echo "   git commit -m 'Initial deployment'"
    echo "   git push origin main"
    echo
    echo "3. Monitor your deployment:"
    echo "   - GitHub Actions: https://github.com/$GITHUB_REPO/actions"
    echo "   - AWS Console EKS: https://$AWS_REGION.console.aws.amazon.com/eks/home?region=$AWS_REGION#/clusters"
    echo "   - CloudWatch Dashboard: https://$AWS_REGION.console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:"
    echo
    echo "4. Access your application:"
    echo "   kubectl get service eks-cicd-app-service"
    echo "   # Use the EXTERNAL-IP from the load balancer"
    echo
    print_info "For troubleshooting, check the README.md file"
}

# Main deployment function
main() {
    print_info "Starting EKS CI/CD Pipeline deployment"
    echo
    
    check_prerequisites
    check_aws_credentials
    get_user_inputs
    update_terraform_variables
    deploy_infrastructure
    get_terraform_outputs
    configure_kubectl
    deploy_monitoring
    display_next_steps
}

# Cleanup function
cleanup() {
    print_warning "Deployment interrupted"
    if [ -f terraform/tfplan ]; then
        rm terraform/tfplan
    fi
    exit 1
}

# Trap interrupt signals
trap cleanup INT TERM

# Check if help is requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "EKS CI/CD Pipeline Deployment Script"
    echo
    echo "Usage: $0"
    echo
    echo "This script will:"
    echo "1. Check prerequisites"
    echo "2. Collect configuration"
    echo "3. Deploy AWS infrastructure with Terraform"
    echo "4. Configure kubectl"
    echo "5. Set up monitoring"
    echo
    echo "Prerequisites:"
    echo "- AWS CLI configured with appropriate permissions"
    echo "- Terraform >= 1.0"
    echo "- kubectl"
    echo "- Docker"
    echo
    exit 0
fi

# Run main function
main