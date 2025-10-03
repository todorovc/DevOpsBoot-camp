#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SKIP_TERRAFORM=${SKIP_TERRAFORM:-false}
SKIP_DOCKER=${SKIP_DOCKER:-false}
SKIP_ANSIBLE=${SKIP_ANSIBLE:-false}
AWS_REGION=${AWS_REGION:-us-west-2}
PROJECT_NAME=${PROJECT_NAME:-k8s-demo}
ENVIRONMENT=${ENVIRONMENT:-dev}

# Function to print colored output
print_status() {
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate prerequisites
validate_prerequisites() {
    print_status "Validating prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    if ! command_exists terraform; then missing_tools+=("terraform"); fi
    if ! command_exists ansible; then missing_tools+=("ansible"); fi
    if ! command_exists aws; then missing_tools+=("aws"); fi
    if ! command_exists kubectl; then missing_tools+=("kubectl"); fi
    if ! command_exists docker; then missing_tools+=("docker"); fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install missing tools and try again."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured properly"
        print_error "Run 'aws configure' or set AWS environment variables"
        exit 1
    fi
    
    print_success "Prerequisites validated"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    if [ "$SKIP_TERRAFORM" = "true" ]; then
        print_warning "Skipping Terraform deployment"
        return
    fi
    
    print_status "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Check if terraform.tfvars exists
    if [ ! -f terraform.tfvars ]; then
        print_warning "terraform.tfvars not found. Copying from example..."
        cp terraform.tfvars.example terraform.tfvars
        print_warning "Please edit terraform.tfvars with your configurations"
        print_warning "Press Enter to continue or Ctrl+C to abort..."
        read
    fi
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Clean up plan file
    rm -f tfplan
    
    cd ..
    print_success "Infrastructure deployed successfully"
}

# Function to build and push Docker image
build_and_push_image() {
    if [ "$SKIP_DOCKER" = "true" ]; then
        print_warning "Skipping Docker build"
        return
    fi
    
    print_status "Building Docker image..."
    
    cd app
    
    # Build image
    docker build -t demo-k8s-app:latest .
    
    # Optional: Push to ECR (uncomment if needed)
    # ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    # aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
    # docker tag demo-k8s-app:latest ${ECR_REGISTRY}/demo-k8s-app:latest
    # docker push ${ECR_REGISTRY}/demo-k8s-app:latest
    
    cd ..
    print_success "Docker image built successfully"
}

# Function to deploy application
deploy_application() {
    if [ "$SKIP_ANSIBLE" = "true" ]; then
        print_warning "Skipping Ansible deployment"
        return
    fi
    
    print_status "Deploying application with Ansible..."
    
    cd ansible
    
    # Check if group_vars/all.yml exists
    if [ ! -f group_vars/all.yml ]; then
        print_warning "group_vars/all.yml not found. Copying from example..."
        mkdir -p group_vars
        cp group_vars/all.yml.example group_vars/all.yml
    fi
    
    # Update kubeconfig
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}
    
    # Deploy application
    ansible-playbook playbooks/deploy-app.yml \
        -e cluster_name=${CLUSTER_NAME} \
        -e aws_region=${AWS_REGION}
    
    cd ..
    print_success "Application deployed successfully"
}

# Function to validate deployment
validate_deployment() {
    print_status "Validating deployment..."
    
    # Check if cluster is accessible
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_error "Cannot access Kubernetes cluster"
        return 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace demo-app >/dev/null 2>&1; then
        print_error "Namespace 'demo-app' not found"
        return 1
    fi
    
    # Check if deployment is ready
    if ! kubectl get deployment demo-k8s-app -n demo-app >/dev/null 2>&1; then
        print_error "Deployment 'demo-k8s-app' not found"
        return 1
    fi
    
    # Wait for deployment to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/demo-k8s-app -n demo-app
    
    print_success "Deployment validation completed"
}

# Function to display access instructions
show_access_instructions() {
    print_status "Access Instructions:"
    echo ""
    echo "1. Port-forward to access the application:"
    echo "   kubectl port-forward svc/demo-k8s-app-service 8080:80 -n demo-app"
    echo ""
    echo "2. Open your browser and visit:"
    echo "   http://localhost:8080"
    echo ""
    echo "3. Health check endpoint:"
    echo "   http://localhost:8080/health"
    echo ""
    echo "4. API info endpoint:"
    echo "   http://localhost:8080/api/info"
    echo ""
    echo "5. To check application status:"
    echo "   kubectl get pods -n demo-app"
    echo "   kubectl logs -f deployment/demo-k8s-app -n demo-app"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy Kubernetes application to AWS EKS"
    echo ""
    echo "OPTIONS:"
    echo "  --skip-terraform    Skip Terraform infrastructure deployment"
    echo "  --skip-docker       Skip Docker image build"
    echo "  --skip-ansible      Skip Ansible application deployment"
    echo "  --region REGION     AWS region (default: us-west-2)"
    echo "  --project PROJECT   Project name (default: k8s-demo)"
    echo "  --env ENVIRONMENT   Environment (default: dev)"
    echo "  --help              Show this help message"
    echo ""
    echo "ENVIRONMENT VARIABLES:"
    echo "  SKIP_TERRAFORM      Set to 'true' to skip Terraform"
    echo "  SKIP_DOCKER         Set to 'true' to skip Docker build"
    echo "  SKIP_ANSIBLE        Set to 'true' to skip Ansible"
    echo "  AWS_REGION          AWS region"
    echo "  PROJECT_NAME        Project name"
    echo "  ENVIRONMENT         Environment name"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                                  # Full deployment"
    echo "  $0 --skip-terraform                # Skip infrastructure"
    echo "  $0 --region us-east-1 --env prod   # Different region/env"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-terraform)
            SKIP_TERRAFORM=true
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-ansible)
            SKIP_ANSIBLE=true
            shift
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --project)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Starting Kubernetes deployment..."
    print_status "Configuration:"
    print_status "  AWS Region: ${AWS_REGION}"
    print_status "  Project: ${PROJECT_NAME}"
    print_status "  Environment: ${ENVIRONMENT}"
    print_status "  Skip Terraform: ${SKIP_TERRAFORM}"
    print_status "  Skip Docker: ${SKIP_DOCKER}"
    print_status "  Skip Ansible: ${SKIP_ANSIBLE}"
    echo ""
    
    validate_prerequisites
    deploy_infrastructure
    build_and_push_image
    deploy_application
    validate_deployment
    show_access_instructions
    
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"