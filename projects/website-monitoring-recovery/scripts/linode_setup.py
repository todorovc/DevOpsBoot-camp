#!/usr/bin/env python3
"""
Linode Setup Script
Creates and configures a Linode server for the website monitoring system.
"""

import os
import sys
import time
import json
import yaml
import logging
import argparse
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from linode_api4 import LinodeClient, Instance, Region, Type, Image, StackScript

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class LinodeDeployment:
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the Linode deployment manager."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize Linode client
        api_token = os.getenv('LINODE_API_TOKEN') or self.config.get('linode', {}).get('api_token')
        if not api_token:
            raise ValueError("Linode API token is required. Set LINODE_API_TOKEN environment variable.")
        
        self.client = LinodeClient(api_token)
        self.deployment_config = self.config.get('linode', {})
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return {
                'linode': {
                    'region': 'us-east',
                    'type': 'g6-nanode-1',
                    'image': 'linode/ubuntu20.04',
                    'root_password': None,
                    'authorized_keys': [],
                    'tags': ['monitoring', 'website-monitor'],
                    'private_ip': True
                },
                'logging': {
                    'level': 'INFO',
                    'file': 'logs/linode.log'
                }
            }
    
    def setup_logging(self):
        """Set up logging configuration."""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        log_file = self.config.get('logging', {}).get('file', 'logs/linode.log')
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def list_regions(self) -> List[Region]:
        """List available Linode regions."""
        try:
            regions = self.client.regions()
            self.logger.info(f"Found {len(regions)} available regions")
            return regions
        except Exception as e:
            self.logger.error(f"Error listing regions: {e}")
            return []
    
    def list_types(self) -> List[Type]:
        """List available Linode instance types."""
        try:
            types = self.client.linode.types()
            self.logger.info(f"Found {len(types)} available instance types")
            return types
        except Exception as e:
            self.logger.error(f"Error listing instance types: {e}")
            return []
    
    def list_images(self) -> List[Image]:
        """List available Linode images."""
        try:
            images = self.client.images()
            self.logger.info(f"Found {len(images)} available images")
            return images
        except Exception as e:
            self.logger.error(f"Error listing images: {e}")
            return []
    
    def generate_root_password(self) -> str:
        """Generate a secure root password."""
        import secrets
        import string
        
        # Generate a 16-character password with letters, digits, and symbols
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for i in range(16))
        
        return password
    
    def create_startup_script(self) -> str:
        """Create a startup script for server initialization."""
        script = """#!/bin/bash
# Website Monitoring Server Setup Script
set -e

# Update system
apt-get update && apt-get upgrade -y

# Install essential packages
apt-get install -y curl wget git vim htop unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Install Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Install Python and pip
apt-get install -y python3 python3-pip python3-venv

# Create monitoring user
useradd -m -s /bin/bash -G docker monitoring
mkdir -p /home/monitoring/.ssh
chmod 700 /home/monitoring/.ssh

# Set up firewall
ufw allow ssh
ufw allow 80
ufw allow 443
ufw --force enable

# Create directories
mkdir -p /opt/website-monitor
mkdir -p /var/log/website-monitor
chown -R monitoring:monitoring /opt/website-monitor /var/log/website-monitor

# Create systemd service file
cat > /etc/systemd/system/website-monitor.service << 'EOF'
[Unit]
Description=Website Monitoring Service
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=monitoring
WorkingDirectory=/opt/website-monitor
ExecStart=/usr/local/bin/docker-compose up
ExecStop=/usr/local/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable the service (but don't start it yet)
systemctl daemon-reload
systemctl enable website-monitor

# Log completion
echo "$(date): Server setup completed" >> /var/log/setup.log
"""
        return script
    
    def create_instance(self, 
                       label: str = None, 
                       root_password: str = None,
                       authorized_keys: List[str] = None,
                       startup_script: str = None) -> Optional[Instance]:
        """Create a new Linode instance."""
        try:
            # Get configuration values
            region = self.deployment_config.get('region', 'us-east')
            instance_type = self.deployment_config.get('type', 'g6-nanode-1')
            image = self.deployment_config.get('image', 'linode/ubuntu20.04')
            tags = self.deployment_config.get('tags', ['monitoring'])
            private_ip = self.deployment_config.get('private_ip', True)
            
            # Generate defaults if not provided
            if not label:
                timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                label = f"website-monitor-{timestamp}"
            
            if not root_password:
                root_password = root_password or self.generate_root_password()
                self.logger.info(f"Generated root password (save this securely): {root_password}")
            
            if not authorized_keys:
                authorized_keys = self.deployment_config.get('authorized_keys', [])
            
            if not startup_script:
                startup_script = self.create_startup_script()
            
            self.logger.info(f"Creating Linode instance: {label}")
            self.logger.info(f"Region: {region}, Type: {instance_type}, Image: {image}")
            
            # Create the instance
            instance = self.client.linode.instances.create(
                ltype=instance_type,
                region=region,
                image=image,
                label=label,
                root_pass=root_password,
                authorized_keys=authorized_keys,
                private_ip=private_ip,
                tags=tags,
                stackscript_data={} if startup_script else None,
                booted=True
            )
            
            self.logger.info(f"Instance created with ID: {instance.id}")
            self.logger.info(f"Instance label: {instance.label}")
            
            # Wait for the instance to be running
            self.logger.info("Waiting for instance to boot...")
            instance.wait_for_status('running', timeout=300)
            
            # Get instance details
            instance = self.client.load(Instance, instance.id)
            self.logger.info(f"Instance is running!")
            self.logger.info(f"Public IP: {instance.ipv4[0] if instance.ipv4 else 'None'}")
            if instance.ipv4 and len(instance.ipv4) > 1:
                self.logger.info(f"Private IP: {instance.ipv4[1]}")
            
            # Execute startup script if provided
            if startup_script:
                self.logger.info("Executing startup script...")
                time.sleep(30)  # Wait for SSH to be available
                success = self.execute_startup_script(instance, startup_script, root_password)
                if success:
                    self.logger.info("Startup script executed successfully")
                else:
                    self.logger.warning("Startup script execution failed")
            
            return instance
        
        except Exception as e:
            self.logger.error(f"Error creating instance: {e}")
            return None
    
    def execute_startup_script(self, instance: Instance, script: str, root_password: str) -> bool:
        """Execute startup script on the instance via SSH."""
        try:
            import paramiko
            
            # Create temporary script file
            script_path = f"/tmp/startup_script_{instance.id}.sh"
            with open(script_path, 'w') as f:
                f.write(script)
            
            # Connect via SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try to connect (may need to retry as SSH starts up)
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    ssh.connect(
                        hostname=instance.ipv4[0],
                        username='root',
                        password=root_password,
                        timeout=30
                    )
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.info(f"SSH connection attempt {attempt + 1} failed, retrying in 30s...")
                        time.sleep(30)
                    else:
                        raise e
            
            # Upload and execute script
            sftp = ssh.open_sftp()
            sftp.put(script_path, '/tmp/startup.sh')
            sftp.chmod('/tmp/startup.sh', 0o755)
            sftp.close()
            
            # Execute the script
            stdin, stdout, stderr = ssh.exec_command('bash /tmp/startup.sh')
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                self.logger.info("Startup script completed successfully")
                output = stdout.read().decode()
                if output:
                    self.logger.debug(f"Script output: {output}")
            else:
                error = stderr.read().decode()
                self.logger.error(f"Startup script failed with exit status {exit_status}: {error}")
            
            ssh.close()
            
            # Clean up temporary file
            os.remove(script_path)
            
            return exit_status == 0
        
        except Exception as e:
            self.logger.error(f"Error executing startup script: {e}")
            return False
    
    def deploy_application(self, instance: Instance, 
                          app_path: str = None, 
                          env_vars: Dict[str, str] = None) -> bool:
        """Deploy the monitoring application to the instance."""
        try:
            if not app_path:
                app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            self.logger.info(f"Deploying application from {app_path} to {instance.label}")
            
            # Create deployment archive
            import tempfile
            import tarfile
            
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
                archive_path = tmp_file.name
            
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(app_path, arcname='website-monitor')
            
            # Upload via SCP
            import paramiko
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=instance.ipv4[0],
                username='root',
                password=self.deployment_config.get('root_password'),
                timeout=30
            )
            
            # Upload archive
            sftp = ssh.open_sftp()
            sftp.put(archive_path, '/tmp/website-monitor.tar.gz')
            sftp.close()
            
            # Extract and setup
            commands = [
                'cd /opt',
                'tar -xzf /tmp/website-monitor.tar.gz',
                'chown -R monitoring:monitoring website-monitor',
                'cd website-monitor',
                'python3 -m pip install -r requirements.txt'
            ]
            
            for cmd in commands:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    error = stderr.read().decode()
                    self.logger.error(f"Command failed '{cmd}': {error}")
                    return False
            
            # Set up environment variables
            if env_vars:
                env_content = '\n'.join([f"{k}={v}" for k, v in env_vars.items()])
                stdin, stdout, stderr = ssh.exec_command(f'echo "{env_content}" > /opt/website-monitor/.env')
                stdout.channel.recv_exit_status()
            
            # Start the service
            stdin, stdout, stderr = ssh.exec_command('systemctl start website-monitor')
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                self.logger.info("Application deployed and started successfully")
            else:
                error = stderr.read().decode()
                self.logger.error(f"Failed to start application: {error}")
            
            ssh.close()
            os.remove(archive_path)
            
            return exit_status == 0
        
        except Exception as e:
            self.logger.error(f"Error deploying application: {e}")
            return False
    
    def list_instances(self) -> List[Instance]:
        """List all Linode instances."""
        try:
            instances = self.client.linode.instances()
            return instances
        except Exception as e:
            self.logger.error(f"Error listing instances: {e}")
            return []
    
    def get_instance(self, instance_id: int = None, label: str = None) -> Optional[Instance]:
        """Get a specific instance by ID or label."""
        try:
            if instance_id:
                return self.client.load(Instance, instance_id)
            elif label:
                instances = self.list_instances()
                for instance in instances:
                    if instance.label == label:
                        return instance
                return None
            else:
                raise ValueError("Either instance_id or label must be provided")
        except Exception as e:
            self.logger.error(f"Error getting instance: {e}")
            return None
    
    def delete_instance(self, instance: Instance) -> bool:
        """Delete a Linode instance."""
        try:
            self.logger.warning(f"Deleting instance: {instance.label} (ID: {instance.id})")
            instance.delete()
            self.logger.info("Instance deleted successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting instance: {e}")
            return False
    
    def save_deployment_info(self, instance: Instance, filename: str = None):
        """Save deployment information to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/deployment_{timestamp}.json"
        
        deployment_info = {
            'timestamp': datetime.now().isoformat(),
            'instance': {
                'id': instance.id,
                'label': instance.label,
                'type': str(instance.type),
                'region': str(instance.region),
                'image': str(instance.image),
                'ipv4': instance.ipv4,
                'status': instance.status,
                'tags': instance.tags
            },
            'config': self.deployment_config
        }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        self.logger.info(f"Deployment info saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Linode Deployment Manager")
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    
    # Actions
    parser.add_argument('--create', action='store_true', help='Create a new instance')
    parser.add_argument('--list', action='store_true', help='List all instances')
    parser.add_argument('--list-regions', action='store_true', help='List available regions')
    parser.add_argument('--list-types', action='store_true', help='List available instance types')
    parser.add_argument('--list-images', action='store_true', help='List available images')
    parser.add_argument('--delete', help='Delete instance by ID or label')
    parser.add_argument('--deploy', help='Deploy application to instance (by ID or label)')
    
    # Instance options
    parser.add_argument('--label', help='Instance label')
    parser.add_argument('--region', help='Instance region')
    parser.add_argument('--type', help='Instance type')
    parser.add_argument('--image', help='Instance image')
    parser.add_argument('--password', help='Root password')
    parser.add_argument('--ssh-key', action='append', help='SSH public key (can be specified multiple times)')
    
    # Application deployment options
    parser.add_argument('--app-path', help='Path to application directory')
    parser.add_argument('--env-file', help='Environment file to load')
    
    args = parser.parse_args()
    
    try:
        deployment = LinodeDeployment(args.config)
        
        if args.list_regions:
            regions = deployment.list_regions()
            print("\nAvailable Regions:")
            for region in regions:
                print(f"  {region.id}: {region.label}")
        
        elif args.list_types:
            types = deployment.list_types()
            print("\nAvailable Instance Types:")
            for instance_type in types:
                print(f"  {instance_type.id}: {instance_type.label} - {instance_type.memory}MB RAM, "
                      f"{instance_type.vcpus} vCPUs, ${instance_type.price.monthly}/month")
        
        elif args.list_images:
            images = deployment.list_images()
            print("\nAvailable Images:")
            for image in images[:20]:  # Show first 20
                print(f"  {image.id}: {image.label}")
        
        elif args.list:
            instances = deployment.list_instances()
            print(f"\nFound {len(instances)} instances:")
            for instance in instances:
                status_emoji = "🟢" if instance.status == "running" else "🔴" if instance.status == "offline" else "🟡"
                print(f"  {status_emoji} {instance.label} (ID: {instance.id})")
                print(f"    Status: {instance.status}")
                print(f"    Type: {instance.type}")
                print(f"    Region: {instance.region}")
                if instance.ipv4:
                    print(f"    IP: {instance.ipv4[0]}")
                print()
        
        elif args.create:
            # Override config with command line arguments
            create_config = {}
            if args.region:
                create_config['region'] = args.region
            if args.type:
                create_config['type'] = args.type
            if args.image:
                create_config['image'] = args.image
            
            deployment.deployment_config.update(create_config)
            
            # Create instance
            instance = deployment.create_instance(
                label=args.label,
                root_password=args.password,
                authorized_keys=args.ssh_key
            )
            
            if instance:
                print(f"✅ Instance created successfully!")
                print(f"   Label: {instance.label}")
                print(f"   ID: {instance.id}")
                print(f"   IP: {instance.ipv4[0] if instance.ipv4 else 'None'}")
                
                deployment.save_deployment_info(instance)
            else:
                print("❌ Failed to create instance")
                sys.exit(1)
        
        elif args.delete:
            # Get instance
            if args.delete.isdigit():
                instance = deployment.get_instance(instance_id=int(args.delete))
            else:
                instance = deployment.get_instance(label=args.delete)
            
            if instance:
                # Confirm deletion
                response = input(f"Are you sure you want to delete '{instance.label}' (ID: {instance.id})? [y/N]: ")
                if response.lower() == 'y':
                    success = deployment.delete_instance(instance)
                    if success:
                        print("✅ Instance deleted successfully")
                    else:
                        print("❌ Failed to delete instance")
                        sys.exit(1)
                else:
                    print("Deletion cancelled")
            else:
                print(f"❌ Instance not found: {args.delete}")
                sys.exit(1)
        
        elif args.deploy:
            # Get instance
            if args.deploy.isdigit():
                instance = deployment.get_instance(instance_id=int(args.deploy))
            else:
                instance = deployment.get_instance(label=args.deploy)
            
            if instance:
                # Load environment variables if specified
                env_vars = {}
                if args.env_file and os.path.exists(args.env_file):
                    with open(args.env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                env_vars[key] = value
                
                success = deployment.deploy_application(
                    instance=instance,
                    app_path=args.app_path,
                    env_vars=env_vars
                )
                
                if success:
                    print("✅ Application deployed successfully")
                else:
                    print("❌ Failed to deploy application")
                    sys.exit(1)
            else:
                print(f"❌ Instance not found: {args.deploy}")
                sys.exit(1)
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()