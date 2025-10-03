#!/bin/bash

# EKS CI/CD Pipeline Cleanup Script
# This script safely removes all infrastructure components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Confirm cleanup
confirm_cleanup() {
    print_warning "This will destroy ALL infrastructure components including:"
    echo "  - EKS Cluster and Node Groups"
    echo "  - VPC and all networking components"
    echo "  - ECR Repository (and all images)"
    echo "  - CloudWatch Log Groups"
    echo "  - IAM Roles and Policies"
    echo "  - KMS Keys"
    echo "  - Load Balancers"
    echo
    print_warning "This action cannot be undone!"
    echo
    read -p "Are you absolutely sure you want to continue? (type 'yes' to confirm): " confirm
    if [[ $confirm != "yes" ]]; then
        print_info "Cleanup cancelled"
        exit 0
    fi
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command_exists terraform; then
        print_error "Terraform is not installed"
        exit 1
    fi
    
    if ! command_exists kubectl; then
        print_error "kubectl is not installed"
        exit 1
    fi
    
    if ! command_exists aws; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
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

# Clean up Kubernetes resources
cleanup_kubernetes() {
    print_info "Cleaning up Kubernetes resources..."
    
    # Check if kubectl is configured for our cluster
    if kubectl cluster-info >/dev/null 2>&1; then
        print_info "Found active kubectl context, cleaning up resources..."
        
        # Delete application resources
        if kubectl get deployment eks-cicd-app >/dev/null 2>&1; then
            print_info "Deleting application deployment..."
            kubectl delete deployment eks-cicd-app --ignore-not-found=true
        fi
        
        if kubectl get service eks-cicd-app-service >/dev/null 2>&1; then
            print_info "Deleting load balancer service..."
            kubectl delete service eks-cicd-app-service --ignore-not-found=true
            
            # Wait for load balancer to be deleted
            print_info "Waiting for load balancer to be deleted..."
            sleep 30
        fi
        
        if kubectl get hpa eks-cicd-app-hpa >/dev/null 2>&1; then
            print_info "Deleting horizontal pod autoscaler..."
            kubectl delete hpa eks-cicd-app-hpa --ignore-not-found=true
        fi
        
        # Delete monitoring resources
        if kubectl get namespace amazon-cloudwatch >/dev/null 2>&1; then
            print_info "Deleting CloudWatch monitoring resources..."
            kubectl delete namespace amazon-cloudwatch --ignore-not-found=true
        fi
        
        print_success "Kubernetes resources cleaned up"
    else
        print_warning "No active kubectl context found, skipping Kubernetes cleanup"
    fi
}

# Clean up ECR images
cleanup_ecr_images() {
    print_info "Cleaning up ECR images..."
    
    local ecr_repo_name="eks-cicd-app"
    local aws_region=$(aws configure get region 2>/dev/null || echo "us-west-2")
    
    if aws ecr describe-repositories --repository-names "$ecr_repo_name" --region "$aws_region" >/dev/null 2>&1; then
        print_info "Found ECR repository, deleting all images..."
        
        # Delete all images in the repository
        local image_digests=$(aws ecr list-images --repository-name "$ecr_repo_name" --region "$aws_region" --query 'imageIds[*].imageDigest' --output text 2>/dev/null)
        
        if [ -n "$image_digests" ] && [ "$image_digests" != "None" ]; then
            print_info "Deleting ECR images..."
            aws ecr batch-delete-image --repository-name "$ecr_repo_name" --region "$aws_region" --image-ids imageDigest="$image_digests" >/dev/null 2>&1 || true
        fi
        
        print_success "ECR images cleaned up"
    else
        print_warning "ECR repository not found, skipping image cleanup"
    fi
}

# Run Terraform destroy
terraform_destroy() {
    print_info "Destroying infrastructure with Terraform..."
    
    if [ ! -d "terraform" ]; then
        print_error "Terraform directory not found"
        exit 1
    fi
    
    cd terraform
    
    # Initialize Terraform (in case of state changes)
    print_info "Initializing Terraform..."
    terraform init
    
    # Plan destruction
    print_info "Creating destruction plan..."
    if [ -f "terraform.tfvars" ]; then
        terraform plan -destroy -var-file="terraform.tfvars" -out=destroy.tfplan
    else
        terraform plan -destroy -out=destroy.tfplan
    fi
    
    # Apply destruction
    print_info "Applying destruction plan..."
    if terraform apply destroy.tfplan; then
        print_success "Infrastructure destroyed successfully"
    else
        print_error "Failed to destroy infrastructure"
        print_warning "You may need to manually clean up some resources"
        exit 1
    fi
    
    # Clean up plan file
    rm -f destroy.tfplan
    
    cd ..
}

# Clean up local files
cleanup_local_files() {
    print_info "Cleaning up local files..."
    
    # Remove Terraform state backups
    find terraform -name "*.tfstate.backup" -delete 2>/dev/null || true
    find terraform -name ".terraform" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Remove any temporary files
    rm -f terraform/tfplan 2>/dev/null || true
    rm -f terraform/terraform.tfvars 2>/dev/null || true
    
    print_success "Local files cleaned up"
}

# Verify cleanup
verify_cleanup() {
    print_info "Verifying cleanup..."
    
    local aws_region=$(aws configure get region 2>/dev/null || echo "us-west-2")
    local issues_found=false
    
    # Check for remaining EKS clusters
    if aws eks list-clusters --region "$aws_region" --query 'clusters[?contains(@, `eks-cicd-cluster`)]' --output text 2>/dev/null | grep -q "eks-cicd-cluster"; then
        print_warning "EKS cluster still exists"
        issues_found=true
    fi
    
    # Check for remaining ECR repositories
    if aws ecr describe-repositories --repository-names "eks-cicd-app" --region "$aws_region" >/dev/null 2>&1; then
        print_warning "ECR repository still exists"
        issues_found=true
    fi
    
    # Check for remaining VPCs with our tag
    local vpc_count=$(aws ec2 describe-vpcs --region "$aws_region" --filters "Name=tag:Name,Values=eks-cicd-pipeline-vpc" --query 'length(Vpcs)' --output text 2>/dev/null || echo "0")
    if [ "$vpc_count" != "0" ]; then
        print_warning "VPC still exists"
        issues_found=true
    fi
    
    if [ "$issues_found" = true ]; then
        print_warning "Some resources may still exist. Check the AWS console and clean up manually if needed."
    else
        print_success "Cleanup verification passed"
    fi
}

# Display cleanup summary
display_summary() {
    print_success "Cleanup completed!"
    print_info "Summary of actions performed:"
    echo "  ✓ Kubernetes resources deleted"
    echo "  ✓ ECR images removed"
    echo "  ✓ Infrastructure destroyed via Terraform"
    echo "  ✓ Local files cleaned up"
    echo
    print_info "If you plan to redeploy:"
    echo "  1. Update your configuration in terraform/variables.tf"
    echo "  2. Run ./scripts/deploy.sh to redeploy"
    echo
    print_warning "Note: Some AWS resources may take time to fully delete"
    print_info "Check the AWS console to verify all resources are removed"
}

# Main cleanup function
main() {
    print_info "Starting EKS CI/CD Pipeline cleanup"
    echo
    
    confirm_cleanup
    check_prerequisites
    check_aws_credentials
    cleanup_kubernetes
    cleanup_ecr_images
    terraform_destroy
    cleanup_local_files
    verify_cleanup
    display_summary
}

# Cleanup function for script interruption
cleanup_script() {
    print_warning "Cleanup interrupted"
    if [ -f terraform/destroy.tfplan ]; then
        rm -f terraform/destroy.tfplan
    fi
    print_info "You may need to run this script again to complete the cleanup"
    exit 1
}

# Trap interrupt signals
trap cleanup_script INT TERM

# Check if help is requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "EKS CI/CD Pipeline Cleanup Script"
    echo
    echo "Usage: $0"
    echo
    echo "This script will safely destroy all infrastructure components:"
    echo "1. Delete Kubernetes resources (pods, services, load balancers)"
    echo "2. Remove ECR images"
    echo "3. Destroy AWS infrastructure with Terraform"
    echo "4. Clean up local files"
    echo "5. Verify cleanup completion"
    echo
    echo "Prerequisites:"
    echo "- AWS CLI configured"
    echo "- Terraform"
    echo "- kubectl"
    echo
    echo "WARNING: This action cannot be undone!"
    echo
    exit 0
fi

# Run main function
main