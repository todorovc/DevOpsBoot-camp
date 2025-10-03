#!/bin/bash

# Update system
apt-get update

# Install Java 11 (required for Jenkins)
apt-get install -y openjdk-11-jdk

# Add Jenkins repository key
wget -q -O - https://pkg.jenkins.io/debian/jenkins.io.key | apt-key add -

# Add Jenkins repository
echo "deb https://pkg.jenkins.io/debian binary/" >> /etc/apt/sources.list.d/jenkins.list

# Update package list and install Jenkins
apt-get update
apt-get install -y jenkins

# Start and enable Jenkins
systemctl start jenkins
systemctl enable jenkins

# Install Docker
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Add jenkins user to docker group
usermod -aG docker jenkins

# Install Git
apt-get install -y git

# Install Maven
apt-get install -y maven

# Install additional packages
apt-get install -y curl wget unzip

# Create Jenkins user home directory if it doesn't exist
mkdir -p /var/lib/jenkins/.ssh
chown jenkins:jenkins /var/lib/jenkins/.ssh
chmod 700 /var/lib/jenkins/.ssh

# Restart Jenkins to apply group changes
systemctl restart jenkins

# Wait for Jenkins to start
sleep 30

# Output initial admin password location
echo "Jenkins initial admin password can be found at: /var/lib/jenkins/secrets/initialAdminPassword"

# Create a script to display the initial password
cat > /home/ubuntu/get-jenkins-password.sh << 'EOF'
#!/bin/bash
echo "Jenkins Initial Admin Password:"
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
EOF

chmod +x /home/ubuntu/get-jenkins-password.sh