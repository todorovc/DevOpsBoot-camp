#!/bin/bash

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Create app directory
mkdir -p /home/ec2-user/app
chown ec2-user:ec2-user /home/ec2-user/app

# Create docker-compose file
echo "${docker_compose_content}" | base64 --decode > /home/ec2-user/app/docker-compose.yml
chown ec2-user:ec2-user /home/ec2-user/app/docker-compose.yml

# Create deployment script
cat > /home/ec2-user/app/deploy.sh << 'EOF'
#!/bin/bash

# Function to deploy the application
deploy_app() {
    local image_tag=$1
    if [ -z "$image_tag" ]; then
        echo "Usage: deploy_app <image_tag>"
        return 1
    fi
    
    echo "Deploying application with image: $image_tag"
    
    # Update docker-compose.yml with new image tag
    sed -i "s|image: .*|image: $image_tag|" /home/ec2-user/app/docker-compose.yml
    
    # Pull latest image
    docker-compose -f /home/ec2-user/app/docker-compose.yml pull
    
    # Deploy with zero-downtime
    docker-compose -f /home/ec2-user/app/docker-compose.yml up -d
    
    # Clean up old images
    docker image prune -f
    
    echo "Deployment completed successfully!"
}

# If called with argument, deploy
if [ $# -eq 1 ]; then
    deploy_app $1
else
    echo "Deploy script ready. Usage: ./deploy.sh <image_tag>"
fi
EOF

chmod +x /home/ec2-user/app/deploy.sh
chown ec2-user:ec2-user /home/ec2-user/app/deploy.sh

# Install additional tools
yum install -y htop curl wget git

# Create log directory
mkdir -p /var/log/app
chown ec2-user:ec2-user /var/log/app

echo "EC2 instance setup completed!" > /var/log/user-data.log