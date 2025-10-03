#!/bin/bash
# Website Monitoring System Deployment Script
# This script helps deploy the monitoring system to a Linode server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CONFIG_FILE="config/config.yaml"
ENV_FILE=".env"
DEPLOY_MODE=""
INSTANCE_ID=""
SSH_KEY=""
REGION="us-east"
INSTANCE_TYPE="g6-nanode-1"

# Print colored output
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

# Display help
show_help() {
    cat << EOF
Website Monitoring System - Deployment Script

USAGE:
    $0 [OPTIONS] COMMAND

COMMANDS:
    setup           Set up local development environment
    create          Create a new Linode server
    deploy          Deploy application to existing server
    list            List existing Linode servers
    destroy         Delete a Linode server
    help            Show this help message

OPTIONS:
    -c, --config FILE       Configuration file (default: config/config.yaml)
    -e, --env FILE          Environment file (default: .env)
    -i, --instance ID       Linode instance ID or label
    -k, --ssh-key FILE      SSH public key file
    -r, --region REGION     Linode region (default: us-east)
    -t, --type TYPE         Instance type (default: g6-nanode-1)
    -h, --help              Show this help message

EXAMPLES:
    # Set up local development environment
    $0 setup

    # Create a new server
    $0 create --region us-west --type g6-standard-1

    # Deploy to existing server
    $0 deploy --instance my-monitor-server

    # List all servers
    $0 list

    # Delete a server
    $0 destroy --instance 12345678

PREREQUISITES:
    - Python 3.8+
    - pip (Python package installer)
    - Linode API token (set LINODE_API_TOKEN environment variable)
    - For SSH deployment: SSH key pair

For more information, see README.md
EOF
}

# Check if required commands exist
check_dependencies() {
    print_info "Checking dependencies..."
    
    local deps=("python3" "pip")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_info "Please install the missing dependencies and try again"
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Set up Python virtual environment
setup_venv() {
    print_info "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Created virtual environment"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        print_info "Installing Python packages..."
        pip install -r requirements.txt
        print_success "Python packages installed"
    else
        print_warning "requirements.txt not found, skipping package installation"
    fi
}

# Set up configuration files
setup_config() {
    print_info "Setting up configuration files..."
    
    # Create config directory if it doesn't exist
    mkdir -p config logs
    
    # Create sample configuration files if they don't exist
    if [ ! -f "config/config.yaml" ]; then
        cat > config/config.yaml << 'EOF'
# Website Monitoring Configuration
monitoring:
  timeout: 10
  retry_count: 3
  retry_delay: 5
  check_interval: 300  # 5 minutes

alerts:
  response_time_threshold: 5.0
  send_on_recovery: true
  send_on_degraded: true

email:
  smtp_server: smtp.gmail.com
  smtp_port: 587
  use_tls: true
  # username and password should be set via environment variables

recovery:
  enabled: true
  max_attempts: 3
  delay_seconds: 30
  actions:
    - restart_nginx
    - restart_container
    - reboot_server

orchestration:
  check_interval: 300
  enable_recovery: true
  enable_notifications: true
  max_failures_before_recovery: 3

linode:
  region: us-east
  type: g6-nanode-1
  image: linode/ubuntu20.04
  tags:
    - monitoring
    - website-monitor

logging:
  level: INFO
  file: logs/main.log

websites_config: config/websites.yaml
EOF
        print_success "Created config/config.yaml"
    fi
    
    if [ ! -f "config/websites.yaml" ]; then
        cat > config/websites.yaml << 'EOF'
# Websites to Monitor
websites:
  - url: https://httpbin.org/status/200
    expected_status: [200]
    expected_content: null
    ports: [80, 443]
    
  - url: https://example.com
    expected_status: [200, 301, 302]
    expected_content: "Example Domain"
    
  - url: https://www.google.com
    expected_status: [200]
EOF
        print_success "Created config/websites.yaml"
    fi
    
    if [ ! -f ".env.example" ]; then
        cat > .env.example << 'EOF'
# Environment Variables Template
# Copy this file to .env and fill in your values

# Email Configuration
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
FROM_EMAIL=monitoring@yourdomain.com
TO_EMAILS=admin@yourdomain.com,alerts@yourdomain.com

# SMTP Configuration (optional, defaults to Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Linode Configuration
LINODE_API_TOKEN=your-linode-api-token

# Optional: Database Configuration
# DATABASE_URL=postgresql://user:pass@localhost/monitoring
EOF
        print_success "Created .env.example"
    fi
    
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning "Created .env from template - please edit it with your credentials"
    fi
}

# Setup local development environment
setup_local() {
    print_info "Setting up local development environment..."
    
    check_dependencies
    setup_venv
    setup_config
    
    print_success "Local environment setup complete!"
    print_info "Next steps:"
    echo "  1. Edit .env with your credentials"
    echo "  2. Edit config/websites.yaml with websites to monitor"
    echo "  3. Test the system: python scripts/main.py --single --dry-run"
}

# Create a new Linode instance
create_server() {
    print_info "Creating new Linode server..."
    
    source venv/bin/activate 2>/dev/null || true
    
    local args=""
    
    if [ -n "$SSH_KEY" ]; then
        args="$args --ssh-key $SSH_KEY"
    fi
    
    if [ -n "$REGION" ]; then
        args="$args --region $REGION"
    fi
    
    if [ -n "$INSTANCE_TYPE" ]; then
        args="$args --type $INSTANCE_TYPE"
    fi
    
    python scripts/linode_setup.py --create $args --config "$CONFIG_FILE"
}

# Deploy application to server
deploy_app() {
    if [ -z "$INSTANCE_ID" ]; then
        print_error "Instance ID or label is required for deployment"
        print_info "Use: $0 deploy --instance <id-or-label>"
        exit 1
    fi
    
    print_info "Deploying application to server: $INSTANCE_ID"
    
    source venv/bin/activate 2>/dev/null || true
    
    local args="--deploy $INSTANCE_ID --config $CONFIG_FILE"
    
    if [ -f "$ENV_FILE" ]; then
        args="$args --env-file $ENV_FILE"
    fi
    
    python scripts/linode_setup.py $args
}

# List Linode instances
list_servers() {
    print_info "Listing Linode servers..."
    
    source venv/bin/activate 2>/dev/null || true
    
    python scripts/linode_setup.py --list --config "$CONFIG_FILE"
}

# Delete a Linode instance
destroy_server() {
    if [ -z "$INSTANCE_ID" ]; then
        print_error "Instance ID or label is required"
        print_info "Use: $0 destroy --instance <id-or-label>"
        exit 1
    fi
    
    print_warning "This will permanently delete the server: $INSTANCE_ID"
    read -p "Are you sure? [y/N]: " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source venv/bin/activate 2>/dev/null || true
        python scripts/linode_setup.py --delete "$INSTANCE_ID" --config "$CONFIG_FILE"
    else
        print_info "Deletion cancelled"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -i|--instance)
            INSTANCE_ID="$2"
            shift 2
            ;;
        -k|--ssh-key)
            SSH_KEY="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -t|--type)
            INSTANCE_TYPE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        setup|create|deploy|list|destroy|help)
            if [ -z "$DEPLOY_MODE" ]; then
                DEPLOY_MODE="$1"
            else
                print_error "Multiple commands specified"
                exit 1
            fi
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if command was provided
if [ -z "$DEPLOY_MODE" ]; then
    print_error "No command specified"
    show_help
    exit 1
fi

# Execute the command
case "$DEPLOY_MODE" in
    setup)
        setup_local
        ;;
    create)
        create_server
        ;;
    deploy)
        deploy_app
        ;;
    list)
        list_servers
        ;;
    destroy)
        destroy_server
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $DEPLOY_MODE"
        show_help
        exit 1
        ;;
esac