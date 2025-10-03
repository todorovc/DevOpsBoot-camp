#!/bin/bash

# Script to deploy the complete infrastructure for Ansible-Jenkins integration demo
# Usage: ./deploy-infrastructure.sh [plan|apply|destroy]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"

ACTION="${1:-plan}"

echo "🚀 Ansible-Jenkins Integration Demo Infrastructure Deployment"
echo "Project root: $PROJECT_ROOT"
echo "Terraform directory: $TERRAFORM_DIR"
echo "Action: $ACTION"
echo ""

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform is not installed. Please install Terraform first."
    echo "   Visit: https://www.terraform.io/downloads.html"
    exit 1
fi

# Check if terraform.tfvars exists
if [ ! -f "$TERRAFORM_DIR/terraform.tfvars" ]; then
    echo "❌ terraform.tfvars file not found!"
    echo "   Please create $TERRAFORM_DIR/terraform.tfvars with your configuration."
    echo "   See terraform.tfvars.example for reference."
    exit 1
fi

# Check if SSH keys exist
KEYS_DIR="$PROJECT_ROOT/keys"
if [ ! -f "$KEYS_DIR/do_rsa.pub" ] || [ ! -f "$KEYS_DIR/aws_rsa.pub" ]; then
    echo "❌ SSH keys not found!"
    echo "   Please run ./generate-keys.sh first to generate SSH keys."
    exit 1
fi

cd "$TERRAFORM_DIR"

echo "🔧 Initializing Terraform..."
terraform init

case $ACTION in
    "plan")
        echo "📋 Planning infrastructure deployment..."
        terraform plan
        echo ""
        echo "✅ Terraform plan completed successfully!"
        echo "   Review the plan above and run './deploy-infrastructure.sh apply' to deploy."
        ;;
    
    "apply")
        echo "🚀 Applying infrastructure deployment..."
        terraform apply -auto-approve
        
        echo ""
        echo "✅ Infrastructure deployed successfully!"
        echo ""
        echo "📋 Deployment Summary:"
        echo "====================="
        terraform output
        
        echo ""
        echo "📝 Next Steps:"
        echo "=============="
        echo "1. Wait 5-10 minutes for servers to fully initialize"
        echo "2. Access Jenkins at the URL shown above"
        echo "3. Get the Jenkins initial admin password:"
        echo "   ssh -i ../keys/do_rsa ubuntu@\$(terraform output -raw jenkins_server_ip) 'sudo cat /var/lib/jenkins/secrets/initialAdminPassword'"
        echo "4. Configure Jenkins with the required plugins and credentials"
        echo "5. Update the Ansible inventory with the EC2 IP addresses"
        echo "6. Test the connection with the Jenkins pipeline"
        ;;
    
    "destroy")
        echo "🗑️  Destroying infrastructure..."
        echo "⚠️  This will permanently delete all resources!"
        read -p "Are you sure you want to continue? (yes/no): " -r
        if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            terraform destroy -auto-approve
            echo "✅ Infrastructure destroyed successfully!"
        else
            echo "❌ Destruction cancelled."
            exit 1
        fi
        ;;
    
    *)
        echo "❌ Invalid action: $ACTION"
        echo "   Usage: $0 [plan|apply|destroy]"
        exit 1
        ;;
esac