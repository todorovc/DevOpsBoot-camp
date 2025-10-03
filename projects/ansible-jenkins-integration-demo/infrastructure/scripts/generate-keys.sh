#!/bin/bash

# Script to generate SSH keys for the Ansible-Jenkins integration demo
# Usage: ./generate-keys.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
KEYS_DIR="$PROJECT_ROOT/keys"

echo "🔐 Generating SSH keys for Ansible-Jenkins integration demo"
echo "Project root: $PROJECT_ROOT"
echo "Keys directory: $KEYS_DIR"

# Create keys directory if it doesn't exist
mkdir -p "$KEYS_DIR"

# Generate SSH key for DigitalOcean droplets (Jenkins and Ansible Control Node)
if [ ! -f "$KEYS_DIR/do_rsa" ]; then
    echo "Generating SSH key for DigitalOcean droplets..."
    ssh-keygen -t rsa -b 4096 -f "$KEYS_DIR/do_rsa" -N "" -C "ansible-jenkins-demo-do"
    echo "✅ DigitalOcean SSH key generated: $KEYS_DIR/do_rsa"
else
    echo "⚠️  DigitalOcean SSH key already exists: $KEYS_DIR/do_rsa"
fi

# Generate SSH key for AWS EC2 instances
if [ ! -f "$KEYS_DIR/aws_rsa" ]; then
    echo "Generating SSH key for AWS EC2 instances..."
    ssh-keygen -t rsa -b 4096 -f "$KEYS_DIR/aws_rsa" -N "" -C "ansible-jenkins-demo-aws"
    echo "✅ AWS SSH key generated: $KEYS_DIR/aws_rsa"
else
    echo "⚠️  AWS SSH key already exists: $KEYS_DIR/aws_rsa"
fi

# Set proper permissions
chmod 600 "$KEYS_DIR"/*_rsa
chmod 644 "$KEYS_DIR"/*.pub

echo ""
echo "📝 SSH Key Summary:"
echo "==================="
ls -la "$KEYS_DIR"

echo ""
echo "📋 Next Steps:"
echo "=============="
echo "1. Add the public keys to your cloud providers:"
echo "   - DigitalOcean: $(cat $KEYS_DIR/do_rsa.pub)"
echo "   - AWS: $(cat $KEYS_DIR/aws_rsa.pub)"
echo ""
echo "2. Update your terraform.tfvars file with the correct paths"
echo "3. Add the private keys as Jenkins credentials"
echo "4. Run 'terraform plan' to verify your infrastructure"
echo ""
echo "⚠️  SECURITY WARNING:"
echo "Keep these private keys secure and never commit them to version control!"

# Create .gitignore for keys directory
cat > "$KEYS_DIR/.gitignore" << EOF
# Ignore all private keys
*_rsa
*.pem
*.key

# Allow public keys and documentation
!*.pub
!README.md
!.gitignore
EOF

echo "🛡️  Created .gitignore file to protect private keys"