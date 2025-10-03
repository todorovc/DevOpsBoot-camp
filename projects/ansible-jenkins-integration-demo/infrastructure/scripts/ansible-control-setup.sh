#!/bin/bash

# Update system
apt-get update

# Install Python3 and pip
apt-get install -y python3 python3-pip python3-venv

# Install Ansible
pip3 install ansible

# Install Boto3 for AWS integration
pip3 install boto3 botocore

# Install additional Python packages
pip3 install requests paramiko

# Install Git
apt-get install -y git curl wget unzip

# Create ansible user (Jenkins will use this)
useradd -m -s /bin/bash ansible
mkdir -p /home/ansible/.ssh
chown ansible:ansible /home/ansible/.ssh
chmod 700 /home/ansible/.ssh

# Create ansible working directory
mkdir -p /opt/ansible/{playbooks,inventory,keys}
chown -R ansible:ansible /opt/ansible

# Create a directory for Jenkins to copy files
mkdir -p /tmp/jenkins-ansible
chmod 777 /tmp/jenkins-ansible

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws/

# Create Ansible configuration directory
mkdir -p /etc/ansible
chown ansible:ansible /etc/ansible

# Create a basic ansible.cfg
cat > /etc/ansible/ansible.cfg << 'EOF'
[defaults]
inventory = /opt/ansible/inventory/hosts
host_key_checking = False
remote_user = ubuntu
private_key_file = /opt/ansible/keys/aws_rsa
timeout = 30
gathering = smart
fact_caching = memory

[inventory]
enable_plugins = aws_ec2

[ssh_connection]
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes
EOF

# Set ownership
chown ansible:ansible /etc/ansible/ansible.cfg

# Create a script for Jenkins to execute playbooks
cat > /opt/ansible/run-playbook.sh << 'EOF'
#!/bin/bash

# Script for Jenkins to execute Ansible playbooks
# Usage: ./run-playbook.sh <playbook_name>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <playbook_name>"
    exit 1
fi

PLAYBOOK=$1
PLAYBOOK_PATH="/opt/ansible/playbooks/${PLAYBOOK}"

if [ ! -f "$PLAYBOOK_PATH" ]; then
    echo "Playbook $PLAYBOOK_PATH not found!"
    exit 1
fi

echo "Executing playbook: $PLAYBOOK_PATH"
cd /opt/ansible
ansible-playbook "$PLAYBOOK_PATH" -i inventory/hosts -v
EOF

chmod +x /opt/ansible/run-playbook.sh
chown ansible:ansible /opt/ansible/run-playbook.sh

echo "Ansible control node setup complete"