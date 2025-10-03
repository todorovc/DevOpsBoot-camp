#!/bin/bash

# Online Shop Microservices Deployment Script for Linode LKE
# This script deploys the complete microservices application to Linode Kubernetes Engine

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="online-shop"
ENVIRONMENT="${1:-production}"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi
    
    # Check if helm is installed (optional)
    if command -v helm &> /dev/null; then
        print_info "Helm is available for additional deployments"
    else
        print_warning "Helm is not installed. Some optional features may not be available."
    fi
    
    print_status "Prerequisites check completed ✅"
}

# Function to create namespace and basic resources
create_namespace() {
    print_header "Creating Namespace and Basic Resources"
    
    print_info "Creating namespace: $NAMESPACE"
    kubectl apply -f k8s-manifests/base/namespace.yaml
    
    print_info "Creating ConfigMaps"
    kubectl apply -f k8s-manifests/base/configmap.yaml
    
    print_info "Creating Secrets"
    print_warning "Using default secrets. Please update them for production!"
    kubectl apply -f k8s-manifests/base/secrets.yaml
    
    print_status "Basic resources created ✅"
}

# Function to setup RBAC
setup_rbac() {
    print_header "Setting up RBAC"
    
    print_info "Creating service accounts and RBAC policies"
    kubectl apply -f k8s-manifests/security/rbac.yaml
    
    print_status "RBAC setup completed ✅"
}

# Function to deploy infrastructure (databases, cache)
deploy_infrastructure() {
    print_header "Deploying Infrastructure"
    
    print_info "Deploying Redis"
    kubectl apply -f infrastructure/redis/redis-deployment.yaml
    
    print_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n $NAMESPACE
    
    print_status "Infrastructure deployed ✅"
}

# Function to deploy microservices
deploy_microservices() {
    print_header "Deploying Microservices"
    
    print_info "Deploying Frontend Service"
    kubectl apply -f k8s-manifests/base/frontend-deployment.yaml
    
    # Wait for frontend to be ready before deploying other services
    print_info "Waiting for Frontend to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/frontend -n $NAMESPACE
    
    # Deploy other microservices (if they exist)
    if [ -f "k8s-manifests/base/user-service-deployment.yaml" ]; then
        print_info "Deploying User Service"
        kubectl apply -f k8s-manifests/base/user-service-deployment.yaml
        kubectl wait --for=condition=available --timeout=300s deployment/user-service -n $NAMESPACE
    fi
    
    if [ -f "k8s-manifests/base/product-service-deployment.yaml" ]; then
        print_info "Deploying Product Service"
        kubectl apply -f k8s-manifests/base/product-service-deployment.yaml
        kubectl wait --for=condition=available --timeout=300s deployment/product-service -n $NAMESPACE
    fi
    
    if [ -f "k8s-manifests/base/order-service-deployment.yaml" ]; then
        print_info "Deploying Order Service"
        kubectl apply -f k8s-manifests/base/order-service-deployment.yaml
        kubectl wait --for=condition=available --timeout=300s deployment/order-service -n $NAMESPACE
    fi
    
    if [ -f "k8s-manifests/base/payment-service-deployment.yaml" ]; then
        print_info "Deploying Payment Service"
        kubectl apply -f k8s-manifests/base/payment-service-deployment.yaml
        kubectl wait --for=condition=available --timeout=300s deployment/payment-service -n $NAMESPACE
    fi
    
    print_status "Microservices deployed ✅"
}

# Function to setup network policies
setup_network_policies() {
    print_header "Setting up Network Policies"
    
    print_info "Applying network policies for security"
    kubectl apply -f k8s-manifests/security/network-policies.yaml
    
    print_status "Network policies applied ✅"
}

# Function to setup ingress
setup_ingress() {
    print_header "Setting up Ingress"
    
    # Check if nginx ingress controller is installed
    if kubectl get deployment -n ingress-nginx nginx-ingress-controller &> /dev/null; then
        print_info "Nginx Ingress Controller found"
    else
        print_warning "Nginx Ingress Controller not found. Installing..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
        
        print_info "Waiting for Ingress Controller to be ready..."
        kubectl wait --namespace ingress-nginx \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/component=controller \
            --timeout=300s
    fi
    
    print_info "Creating Ingress rules"
    if [ "$ENVIRONMENT" = "development" ]; then
        kubectl apply -f k8s-manifests/base/ingress.yaml
        print_info "Applied development ingress configuration"
    else
        kubectl apply -f k8s-manifests/base/ingress.yaml
        print_info "Applied production ingress configuration"
    fi
    
    print_status "Ingress setup completed ✅"
}

# Function to verify deployment
verify_deployment() {
    print_header "Verifying Deployment"
    
    print_info "Checking pod status"
    kubectl get pods -n $NAMESPACE
    
    print_info "Checking service status"
    kubectl get services -n $NAMESPACE
    
    print_info "Checking ingress status"
    kubectl get ingress -n $NAMESPACE
    
    # Check if all deployments are ready
    print_info "Verifying all deployments are ready..."
    
    deployments=$(kubectl get deployments -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')
    for deployment in $deployments; do
        if kubectl wait --for=condition=available --timeout=60s deployment/$deployment -n $NAMESPACE; then
            print_status "$deployment is ready ✅"
        else
            print_error "$deployment is not ready ❌"
        fi
    done
    
    # Get external IP
    print_info "Getting external access information..."
    kubectl get ingress -n $NAMESPACE -o wide
    
    print_status "Deployment verification completed ✅"
}

# Function to show deployment information
show_deployment_info() {
    print_header "Deployment Information"
    
    echo -e "${GREEN}Deployment completed successfully! 🎉${NC}"
    echo ""
    echo "📋 Summary:"
    echo "  - Environment: $ENVIRONMENT"
    echo "  - Namespace: $NAMESPACE"
    echo "  - Cluster: $(kubectl config current-context)"
    echo ""
    
    # Get ingress IP
    INGRESS_IP=$(kubectl get ingress online-shop-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending...")
    
    echo "🌐 Access URLs:"
    if [ "$INGRESS_IP" != "Pending..." ] && [ -n "$INGRESS_IP" ]; then
        echo "  - Frontend: http://$INGRESS_IP"
        echo "  - API: http://$INGRESS_IP/api"
    else
        echo "  - External IP is still being assigned..."
        echo "  - Run 'kubectl get ingress -n $NAMESPACE' to check status"
    fi
    echo ""
    
    echo "🔧 Useful Commands:"
    echo "  - View pods: kubectl get pods -n $NAMESPACE"
    echo "  - View services: kubectl get svc -n $NAMESPACE"
    echo "  - View logs: kubectl logs -f deployment/frontend -n $NAMESPACE"
    echo "  - Scale deployment: kubectl scale deployment frontend --replicas=5 -n $NAMESPACE"
    echo ""
    
    echo "📊 Monitoring:"
    echo "  - Metrics are exposed on /metrics endpoints"
    echo "  - Health checks available on /health endpoints"
    echo "  - Ready checks available on /ready endpoints"
}

# Function to cleanup deployment
cleanup_deployment() {
    print_header "Cleaning up Deployment"
    
    print_warning "This will delete all resources in namespace $NAMESPACE"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deleting namespace $NAMESPACE and all resources..."
        kubectl delete namespace $NAMESPACE
        print_status "Cleanup completed ✅"
    else
        print_info "Cleanup cancelled"
    fi
}

# Main function
main() {
    print_header "Online Shop Microservices Deployment"
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Kubeconfig: $KUBECONFIG_PATH"
    echo ""
    
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            create_namespace
            setup_rbac
            deploy_infrastructure
            deploy_microservices
            setup_network_policies
            setup_ingress
            verify_deployment
            show_deployment_info
            ;;
        "cleanup")
            cleanup_deployment
            ;;
        "verify")
            verify_deployment
            ;;
        "info")
            show_deployment_info
            ;;
        *)
            echo "Usage: $0 [deploy|cleanup|verify|info] [environment]"
            echo ""
            echo "Commands:"
            echo "  deploy    - Deploy the complete application (default)"
            echo "  cleanup   - Remove all deployed resources"
            echo "  verify    - Verify deployment status"
            echo "  info      - Show deployment information"
            echo ""
            echo "Environments:"
            echo "  development  - Deploy with development settings"
            echo "  staging      - Deploy with staging settings"
            echo "  production   - Deploy with production settings (default)"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"