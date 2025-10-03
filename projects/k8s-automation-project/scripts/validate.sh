#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
AWS_REGION=${AWS_REGION:-us-west-2}
PROJECT_NAME=${PROJECT_NAME:-k8s-demo}
ENVIRONMENT=${ENVIRONMENT:-dev}
NAMESPACE=${NAMESPACE:-demo-app}
APP_NAME=${APP_NAME:-demo-k8s-app}

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
    if ! command_exists aws; then missing_tools+=("aws"); fi
    if ! command_exists kubectl; then missing_tools+=("kubectl"); fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured properly"
        exit 1
    fi
    
    print_success "Prerequisites validated"
}

# Function to check infrastructure
check_infrastructure() {
    print_status "Checking infrastructure..."
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Check if EKS cluster exists
    if aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} >/dev/null 2>&1; then
        print_success "EKS cluster '${CLUSTER_NAME}' exists"
        
        # Get cluster status
        cluster_status=$(aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} --query 'cluster.status' --output text)
        if [ "$cluster_status" = "ACTIVE" ]; then
            print_success "EKS cluster is ACTIVE"
        else
            print_warning "EKS cluster status: $cluster_status"
        fi
    else
        print_error "EKS cluster '${CLUSTER_NAME}' not found"
        return 1
    fi
}

# Function to check kubectl connectivity
check_kubectl_connectivity() {
    print_status "Checking kubectl connectivity..."
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Update kubeconfig
    if aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME} >/dev/null 2>&1; then
        print_success "Updated kubeconfig for cluster '${CLUSTER_NAME}'"
    else
        print_error "Failed to update kubeconfig"
        return 1
    fi
    
    # Test cluster connectivity
    if kubectl cluster-info >/dev/null 2>&1; then
        print_success "Successfully connected to Kubernetes cluster"
    else
        print_error "Cannot connect to Kubernetes cluster"
        return 1
    fi
}

# Function to check application deployment
check_application() {
    print_status "Checking application deployment..."
    
    # Check namespace
    if kubectl get namespace ${NAMESPACE} >/dev/null 2>&1; then
        print_success "Namespace '${NAMESPACE}' exists"
    else
        print_error "Namespace '${NAMESPACE}' not found"
        return 1
    fi
    
    # Check deployment
    if kubectl get deployment ${APP_NAME} -n ${NAMESPACE} >/dev/null 2>&1; then
        print_success "Deployment '${APP_NAME}' exists"
        
        # Check deployment status
        ready_replicas=$(kubectl get deployment ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
        desired_replicas=$(kubectl get deployment ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.replicas}')
        
        if [ "$ready_replicas" = "$desired_replicas" ] && [ "$ready_replicas" != "0" ]; then
            print_success "Deployment is ready: ${ready_replicas}/${desired_replicas} replicas"
        else
            print_warning "Deployment not fully ready: ${ready_replicas}/${desired_replicas} replicas"
        fi
    else
        print_error "Deployment '${APP_NAME}' not found"
        return 1
    fi
    
    # Check service
    if kubectl get service ${APP_NAME}-service -n ${NAMESPACE} >/dev/null 2>&1; then
        print_success "Service '${APP_NAME}-service' exists"
    else
        print_error "Service '${APP_NAME}-service' not found"
        return 1
    fi
}

# Function to check pods status
check_pods() {
    print_status "Checking pods status..."
    
    pods=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [ -z "$pods" ]; then
        print_error "No pods found for app '${APP_NAME}'"
        return 1
    fi
    
    local all_running=true
    for pod in $pods; do
        status=$(kubectl get pod $pod -n ${NAMESPACE} -o jsonpath='{.status.phase}')
        if [ "$status" = "Running" ]; then
            print_success "Pod '$pod' is Running"
        else
            print_warning "Pod '$pod' status: $status"
            all_running=false
        fi
    done
    
    if [ "$all_running" = "true" ]; then
        print_success "All pods are running"
    else
        print_warning "Some pods are not in Running state"
    fi
}

# Function to test application connectivity
test_application() {
    print_status "Testing application connectivity..."
    
    # Port-forward to test connectivity
    print_status "Starting port-forward for testing..."
    kubectl port-forward svc/${APP_NAME}-service 8080:80 -n ${NAMESPACE} >/dev/null 2>&1 &
    port_forward_pid=$!
    
    # Wait a moment for port-forward to establish
    sleep 3
    
    # Test health endpoint
    if command_exists curl; then
        if curl -s http://localhost:8080/health >/dev/null 2>&1; then
            print_success "Application health endpoint is responding"
        else
            print_warning "Application health endpoint not responding"
        fi
        
        if curl -s http://localhost:8080/api/info >/dev/null 2>&1; then
            print_success "Application API endpoint is responding"
        else
            print_warning "Application API endpoint not responding"
        fi
    else
        print_warning "curl not available, skipping connectivity test"
    fi
    
    # Cleanup port-forward
    kill $port_forward_pid 2>/dev/null || true
}

# Function to check ingress (if applicable)
check_ingress() {
    print_status "Checking ingress configuration..."
    
    if kubectl get ingress ${APP_NAME}-ingress -n ${NAMESPACE} >/dev/null 2>&1; then
        print_success "Ingress '${APP_NAME}-ingress' exists"
        
        # Check if ingress has address
        address=$(kubectl get ingress ${APP_NAME}-ingress -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
        if [ -n "$address" ]; then
            print_success "Ingress has external address: $address"
        else
            print_warning "Ingress does not have external address yet"
        fi
    else
        print_warning "Ingress '${APP_NAME}-ingress' not found (may not be configured)"
    fi
    
    # Check if AWS Load Balancer Controller is installed
    if kubectl get deployment aws-load-balancer-controller -n kube-system >/dev/null 2>&1; then
        print_success "AWS Load Balancer Controller is installed"
    else
        print_warning "AWS Load Balancer Controller not found"
        print_warning "Ingress may not work without ALB controller"
    fi
}

# Function to show resource status
show_resource_status() {
    print_status "Resource Status Summary:"
    echo ""
    
    echo "=== EKS Cluster ==="
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    aws eks describe-cluster --name ${CLUSTER_NAME} --region ${AWS_REGION} --query 'cluster.{Name:name,Status:status,Version:version,Endpoint:endpoint}' --output table 2>/dev/null || echo "Cluster not found"
    
    echo ""
    echo "=== Nodes ==="
    kubectl get nodes -o wide 2>/dev/null || echo "Cannot get nodes"
    
    echo ""
    echo "=== Namespaces ==="
    kubectl get namespaces | grep -E "(NAME|${NAMESPACE})" || echo "Namespace not found"
    
    echo ""
    echo "=== Deployments ==="
    kubectl get deployments -n ${NAMESPACE} -o wide 2>/dev/null || echo "No deployments found"
    
    echo ""
    echo "=== Pods ==="
    kubectl get pods -n ${NAMESPACE} -o wide 2>/dev/null || echo "No pods found"
    
    echo ""
    echo "=== Services ==="
    kubectl get services -n ${NAMESPACE} -o wide 2>/dev/null || echo "No services found"
    
    echo ""
    echo "=== Ingress ==="
    kubectl get ingress -n ${NAMESPACE} -o wide 2>/dev/null || echo "No ingress found"
}

# Function to show access instructions
show_access_instructions() {
    print_status "Access Instructions:"
    echo ""
    echo "To access your application:"
    echo "1. Port-forward: kubectl port-forward svc/${APP_NAME}-service 8080:80 -n ${NAMESPACE}"
    echo "2. Visit: http://localhost:8080"
    echo "3. Health check: http://localhost:8080/health"
    echo "4. API info: http://localhost:8080/api/info"
    echo ""
    
    # Check for external access
    address=$(kubectl get ingress ${APP_NAME}-ingress -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ -n "$address" ]; then
        echo "External access (if ALB is ready):"
        echo "Visit: http://$address"
    else
        echo "External access not yet available (ALB may still be provisioning)"
    fi
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Validate Kubernetes deployment on AWS EKS"
    echo ""
    echo "OPTIONS:"
    echo "  --region REGION     AWS region (default: us-west-2)"
    echo "  --project PROJECT   Project name (default: k8s-demo)"
    echo "  --env ENVIRONMENT   Environment (default: dev)"
    echo "  --namespace NS      Kubernetes namespace (default: demo-app)"
    echo "  --app-name NAME     Application name (default: demo-k8s-app)"
    echo "  --help              Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                                    # Validate with defaults"
    echo "  $0 --region us-east-1 --env prod     # Different region/env"
    echo "  $0 --namespace my-app --app-name myapp # Different app"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --app-name)
            APP_NAME="$2"
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
    print_status "Starting deployment validation..."
    print_status "Configuration:"
    print_status "  AWS Region: ${AWS_REGION}"
    print_status "  Project: ${PROJECT_NAME}"
    print_status "  Environment: ${ENVIRONMENT}"
    print_status "  Namespace: ${NAMESPACE}"
    print_status "  App Name: ${APP_NAME}"
    echo ""
    
    validate_prerequisites
    
    if check_infrastructure && check_kubectl_connectivity; then
        check_application
        check_pods
        test_application
        check_ingress
        show_resource_status
        show_access_instructions
        print_success "Deployment validation completed!"
    else
        print_error "Infrastructure validation failed"
        exit 1
    fi
}

# Run main function
main "$@"