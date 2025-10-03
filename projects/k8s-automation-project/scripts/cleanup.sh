#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SKIP_APPLICATION=${SKIP_APPLICATION:-false}
SKIP_TERRAFORM=${SKIP_TERRAFORM:-false}
AWS_REGION=${AWS_REGION:-us-west-2}
PROJECT_NAME=${PROJECT_NAME:-k8s-demo}
ENVIRONMENT=${ENVIRONMENT:-dev}
FORCE=${FORCE:-false}

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

# Function to confirm action
confirm_action() {
    if [ "$FORCE" = "true" ]; then
        return 0
    fi
    
    echo -e "${YELLOW}WARNING: This will destroy resources and may result in data loss!${NC}"
    echo -n "Are you sure you want to continue? (yes/no): "
    read -r response
    case "$response" in
        yes|YES|y|Y) 
            return 0
            ;;
        *)
            print_status "Operation cancelled by user"
            exit 0
            ;;
    esac
}

# Function to cleanup application
cleanup_application() {
    if [ "$SKIP_APPLICATION" = "true" ]; then
        print_warning "Skipping application cleanup"
        return
    fi
    
    print_status "Cleaning up application resources..."
    
    # Update kubeconfig
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    if ! aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME} >/dev/null 2>&1; then
        print_warning "Could not update kubeconfig for cluster ${CLUSTER_NAME}"
        print_warning "Cluster may not exist or be accessible"
        return
    fi
    
    # Check if namespace exists
    if kubectl get namespace demo-app >/dev/null 2>&1; then
        print_status "Deleting namespace 'demo-app'..."
        kubectl delete namespace demo-app --timeout=300s
        print_success "Application resources cleaned up"
    else
        print_warning "Namespace 'demo-app' not found, skipping application cleanup"
    fi
}

# Function to cleanup infrastructure
cleanup_infrastructure() {
    if [ "$SKIP_TERRAFORM" = "true" ]; then
        print_warning "Skipping infrastructure cleanup"
        return
    fi
    
    print_status "Cleaning up infrastructure with Terraform..."
    
    cd terraform
    
    if [ ! -f terraform.tfstate ]; then
        print_warning "No Terraform state file found, skipping infrastructure cleanup"
        cd ..
        return
    fi
    
    # Run terraform destroy
    terraform destroy -auto-approve
    
    cd ..
    print_success "Infrastructure cleaned up successfully"
}

# Function to cleanup Docker images
cleanup_docker_images() {
    print_status "Cleaning up Docker images..."
    
    # Remove demo app images
    if docker images demo-k8s-app -q | grep -q .; then
        print_status "Removing demo-k8s-app Docker images..."
        docker rmi $(docker images demo-k8s-app -q) 2>/dev/null || true
    fi
    
    # Clean up dangling images
    if docker images -f "dangling=true" -q | grep -q .; then
        print_status "Removing dangling Docker images..."
        docker image prune -f
    fi
    
    print_success "Docker cleanup completed"
}

# Function to cleanup kubectl contexts
cleanup_kubectl_contexts() {
    print_status "Cleaning up kubectl contexts..."
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    CONTEXT_NAME="arn:aws:eks:${AWS_REGION}:*:cluster/${CLUSTER_NAME}"
    
    # Get current context
    current_context=$(kubectl config current-context 2>/dev/null || echo "")
    
    # List contexts related to our cluster
    contexts=$(kubectl config get-contexts -o name | grep -i "${CLUSTER_NAME}" || true)
    
    for context in $contexts; do
        if [ "$context" = "$current_context" ]; then
            print_status "Switching away from context: $context"
            kubectl config use-context docker-desktop 2>/dev/null || \
            kubectl config use-context minikube 2>/dev/null || \
            print_warning "Could not switch to alternative context"
        fi
        
        print_status "Deleting kubectl context: $context"
        kubectl config delete-context "$context" 2>/dev/null || true
    done
    
    # Clean up cluster entries
    clusters=$(kubectl config get-clusters | grep -i "${CLUSTER_NAME}" || true)
    for cluster in $clusters; do
        print_status "Deleting kubectl cluster: $cluster"
        kubectl config delete-cluster "$cluster" 2>/dev/null || true
    done
    
    # Clean up user entries
    users=$(kubectl config view -o jsonpath='{.users[*].name}' | tr ' ' '\n' | grep -i "${CLUSTER_NAME}" || true)
    for user in $users; do
        print_status "Deleting kubectl user: $user"
        kubectl config delete-user "$user" 2>/dev/null || true
    done
    
    print_success "Kubectl cleanup completed"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Cleanup Kubernetes deployment from AWS EKS"
    echo ""
    echo "OPTIONS:"
    echo "  --skip-app          Skip application cleanup"
    echo "  --skip-terraform    Skip Terraform infrastructure cleanup"
    echo "  --region REGION     AWS region (default: us-west-2)"
    echo "  --project PROJECT   Project name (default: k8s-demo)"
    echo "  --env ENVIRONMENT   Environment (default: dev)"
    echo "  --force             Skip confirmation prompts"
    echo "  --help              Show this help message"
    echo ""
    echo "ENVIRONMENT VARIABLES:"
    echo "  SKIP_APPLICATION    Set to 'true' to skip application cleanup"
    echo "  SKIP_TERRAFORM      Set to 'true' to skip Terraform cleanup"
    echo "  AWS_REGION          AWS region"
    echo "  PROJECT_NAME        Project name"
    echo "  ENVIRONMENT         Environment name"
    echo "  FORCE              Set to 'true' to skip confirmations"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                          # Full cleanup"
    echo "  $0 --skip-terraform         # Cleanup app only"
    echo "  $0 --force                  # Skip confirmations"
    echo "  $0 --region us-east-1       # Different region"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-app)
            SKIP_APPLICATION=true
            shift
            ;;
        --skip-terraform)
            SKIP_TERRAFORM=true
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
        --force)
            FORCE=true
            shift
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
    print_status "Starting cleanup process..."
    print_status "Configuration:"
    print_status "  AWS Region: ${AWS_REGION}"
    print_status "  Project: ${PROJECT_NAME}"
    print_status "  Environment: ${ENVIRONMENT}"
    print_status "  Skip Application: ${SKIP_APPLICATION}"
    print_status "  Skip Terraform: ${SKIP_TERRAFORM}"
    print_status "  Force: ${FORCE}"
    echo ""
    
    confirm_action
    
    cleanup_application
    cleanup_infrastructure
    cleanup_docker_images
    cleanup_kubectl_contexts
    
    print_success "Cleanup completed successfully!"
    print_status "All resources have been removed."
}

# Run main function
main "$@"