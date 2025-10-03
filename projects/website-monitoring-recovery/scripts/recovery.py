#!/usr/bin/env python3
"""
Auto-Recovery Script
Automatically restarts applications and servers when issues are detected.
"""

import subprocess
import logging
import argparse
import yaml
import json
import os
import sys
import time
import docker
import psutil
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from linode_api4 import LinodeClient, Instance

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class RecoveryManager:
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the recovery manager with configuration."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            self.logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
        
        # Initialize Linode client
        linode_token = os.getenv('LINODE_API_TOKEN') or self.config.get('linode', {}).get('api_token')
        if linode_token:
            try:
                self.linode_client = LinodeClient(linode_token)
            except Exception as e:
                self.logger.warning(f"Linode client not available: {e}")
                self.linode_client = None
        else:
            self.linode_client = None
        
        # Recovery settings
        self.recovery_settings = self.config.get('recovery', {})
        self.max_recovery_attempts = self.recovery_settings.get('max_attempts', 3)
        self.recovery_delay = self.recovery_settings.get('delay_seconds', 30)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return {
                'recovery': {
                    'enabled': True,
                    'max_attempts': 3,
                    'delay_seconds': 30,
                    'actions': ['restart_service', 'restart_container', 'reboot_server']
                },
                'logging': {
                    'level': 'INFO',
                    'file': 'logs/recovery.log'
                }
            }
    
    def setup_logging(self):
        """Set up logging configuration."""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        log_file = self.config.get('logging', {}).get('file', 'logs/recovery.log')
        
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
    
    def execute_command(self, command: str, timeout: int = 60) -> Tuple[bool, str, str]:
        """
        Execute a shell command safely.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
        
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            self.logger.info(f"Executing command: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            success = result.returncode == 0
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if success:
                self.logger.info(f"Command executed successfully: {command}")
                if stdout:
                    self.logger.debug(f"Command output: {stdout}")
            else:
                self.logger.error(f"Command failed with return code {result.returncode}: {command}")
                if stderr:
                    self.logger.error(f"Command error: {stderr}")
            
            return success, stdout, stderr
        
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout}s: {command}")
            return False, "", f"Command timed out after {timeout}s"
        
        except Exception as e:
            self.logger.error(f"Error executing command '{command}': {e}")
            return False, "", str(e)
    
    def restart_systemd_service(self, service_name: str) -> bool:
        """Restart a systemd service."""
        try:
            self.logger.info(f"Restarting systemd service: {service_name}")
            
            # Check service status first
            success, stdout, stderr = self.execute_command(f"systemctl is-active {service_name}")
            
            # Stop the service
            success, _, _ = self.execute_command(f"sudo systemctl stop {service_name}")
            if not success:
                self.logger.warning(f"Failed to stop service {service_name}, continuing anyway")
            
            # Wait a moment
            time.sleep(2)
            
            # Start the service
            success, _, _ = self.execute_command(f"sudo systemctl start {service_name}")
            if not success:
                self.logger.error(f"Failed to start service {service_name}")
                return False
            
            # Check if service is running
            time.sleep(5)
            success, stdout, _ = self.execute_command(f"systemctl is-active {service_name}")
            
            if success and "active" in stdout:
                self.logger.info(f"Successfully restarted service: {service_name}")
                return True
            else:
                self.logger.error(f"Service {service_name} is not active after restart")
                return False
        
        except Exception as e:
            self.logger.error(f"Error restarting service {service_name}: {e}")
            return False
    
    def restart_docker_container(self, container_name: str) -> bool:
        """Restart a Docker container."""
        if not self.docker_client:
            self.logger.error("Docker client not available")
            return False
        
        try:
            self.logger.info(f"Restarting Docker container: {container_name}")
            
            # Find the container
            try:
                container = self.docker_client.containers.get(container_name)
            except docker.errors.NotFound:
                self.logger.error(f"Container {container_name} not found")
                return False
            
            # Stop the container
            container.stop(timeout=30)
            self.logger.info(f"Stopped container: {container_name}")
            
            # Wait a moment
            time.sleep(2)
            
            # Start the container
            container.start()
            self.logger.info(f"Started container: {container_name}")
            
            # Wait and check if container is running
            time.sleep(5)
            container.reload()
            
            if container.status == 'running':
                self.logger.info(f"Successfully restarted container: {container_name}")
                return True
            else:
                self.logger.error(f"Container {container_name} status: {container.status}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error restarting container {container_name}: {e}")
            return False
    
    def restart_process_by_name(self, process_name: str) -> bool:
        """Restart a process by name."""
        try:
            self.logger.info(f"Restarting process: {process_name}")
            
            # Find processes by name
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        processes.append(proc)
                    elif proc.info['cmdline'] and any(process_name.lower() in arg.lower() for arg in proc.info['cmdline']):
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not processes:
                self.logger.warning(f"No processes found matching: {process_name}")
                return False
            
            # Terminate processes
            for proc in processes:
                try:
                    self.logger.info(f"Terminating process PID {proc.pid}: {proc.info['name']}")
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    self.logger.warning(f"Could not terminate PID {proc.pid}: {e}")
            
            # Wait for processes to terminate
            time.sleep(5)
            
            # Force kill if still running
            for proc in processes:
                try:
                    if proc.is_running():
                        self.logger.info(f"Force killing process PID {proc.pid}")
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            self.logger.info(f"Process restart completed for: {process_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error restarting process {process_name}: {e}")
            return False
    
    def restart_nginx(self) -> bool:
        """Restart Nginx web server."""
        self.logger.info("Restarting Nginx")
        
        # Try systemd first
        if self.execute_command("which systemctl")[0]:
            return self.restart_systemd_service("nginx")
        
        # Try service command
        elif self.execute_command("which service")[0]:
            success, _, _ = self.execute_command("sudo service nginx restart")
            return success
        
        # Try direct nginx command
        else:
            success, _, _ = self.execute_command("sudo nginx -s reload")
            return success
    
    def restart_apache(self) -> bool:
        """Restart Apache web server."""
        self.logger.info("Restarting Apache")
        
        # Try systemd first (common service names)
        for service_name in ['apache2', 'httpd']:
            if self.execute_command(f"systemctl list-unit-files | grep {service_name}")[0]:
                return self.restart_systemd_service(service_name)
        
        # Try service command
        for service_name in ['apache2', 'httpd']:
            success, _, _ = self.execute_command(f"sudo service {service_name} restart")
            if success:
                return True
        
        return False
    
    def reboot_server(self) -> bool:
        """Reboot the server."""
        try:
            self.logger.warning("Initiating server reboot")
            
            # Schedule reboot in 1 minute to allow logging
            success, _, _ = self.execute_command("sudo shutdown -r +1 'Automated recovery reboot'")
            
            if success:
                self.logger.info("Server reboot scheduled in 1 minute")
                return True
            else:
                self.logger.error("Failed to schedule server reboot")
                return False
        
        except Exception as e:
            self.logger.error(f"Error rebooting server: {e}")
            return False
    
    def reboot_linode_instance(self, instance_id: int = None) -> bool:
        """Reboot a Linode instance."""
        if not self.linode_client:
            self.logger.error("Linode client not available")
            return False
        
        try:
            if not instance_id:
                # Get instance ID from metadata or config
                instance_id = self.config.get('linode', {}).get('instance_id')
                
                # Try to get from Linode metadata
                if not instance_id:
                    success, stdout, _ = self.execute_command("curl -s http://169.254.169.254/v1/instance/id")
                    if success and stdout.isdigit():
                        instance_id = int(stdout)
            
            if not instance_id:
                self.logger.error("Could not determine Linode instance ID")
                return False
            
            self.logger.info(f"Rebooting Linode instance: {instance_id}")
            
            instance = self.linode_client.load(Instance, instance_id)
            instance.reboot()
            
            self.logger.info(f"Linode instance {instance_id} reboot initiated")
            return True
        
        except Exception as e:
            self.logger.error(f"Error rebooting Linode instance: {e}")
            return False
    
    def perform_recovery_action(self, action_type: str, target: str = None) -> bool:
        """
        Perform a specific recovery action.
        
        Args:
            action_type: Type of recovery action
            target: Target for the action (service name, container name, etc.)
        
        Returns:
            True if action was successful
        """
        self.logger.info(f"Performing recovery action: {action_type} (target: {target})")
        
        try:
            if action_type == 'restart_service' and target:
                return self.restart_systemd_service(target)
            
            elif action_type == 'restart_container' and target:
                return self.restart_docker_container(target)
            
            elif action_type == 'restart_process' and target:
                return self.restart_process_by_name(target)
            
            elif action_type == 'restart_nginx':
                return self.restart_nginx()
            
            elif action_type == 'restart_apache':
                return self.restart_apache()
            
            elif action_type == 'reboot_server':
                return self.reboot_server()
            
            elif action_type == 'reboot_linode':
                return self.reboot_linode_instance()
            
            elif action_type == 'custom_script' and target:
                success, _, _ = self.execute_command(target)
                return success
            
            else:
                self.logger.error(f"Unknown recovery action: {action_type}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error performing recovery action {action_type}: {e}")
            return False
    
    def recover_from_monitoring_results(self, monitoring_results: List[Dict]) -> Dict:
        """
        Perform recovery actions based on monitoring results.
        
        Args:
            monitoring_results: List of monitoring results
        
        Returns:
            Dictionary with recovery results
        """
        if not self.recovery_settings.get('enabled', True):
            self.logger.info("Recovery is disabled in configuration")
            return {'enabled': False}
        
        recovery_results = {
            'enabled': True,
            'timestamp': datetime.now().isoformat(),
            'actions_performed': [],
            'successful_actions': 0,
            'failed_actions': 0
        }
        
        # Find sites that need recovery
        down_sites = [result for result in monitoring_results if result.get('status') == 'down']
        
        if not down_sites:
            self.logger.info("No down sites found, no recovery needed")
            return recovery_results
        
        self.logger.info(f"Found {len(down_sites)} down sites, initiating recovery")
        
        # Get recovery actions from config
        recovery_actions = self.recovery_settings.get('actions', [])
        
        for site in down_sites:
            url = site.get('url', 'unknown')
            self.logger.info(f"Attempting recovery for: {url}")
            
            # Try each recovery action
            for action_config in recovery_actions:
                if isinstance(action_config, str):
                    action_type = action_config
                    target = None
                elif isinstance(action_config, dict):
                    action_type = action_config.get('type')
                    target = action_config.get('target')
                else:
                    self.logger.warning(f"Invalid action configuration: {action_config}")
                    continue
                
                action_result = {
                    'action_type': action_type,
                    'target': target,
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'success': False,
                    'error': None
                }
                
                try:
                    # Perform the action
                    success = self.perform_recovery_action(action_type, target)
                    action_result['success'] = success
                    
                    if success:
                        recovery_results['successful_actions'] += 1
                        self.logger.info(f"Recovery action successful: {action_type} for {url}")
                        
                        # Wait before next action
                        if self.recovery_delay > 0:
                            time.sleep(self.recovery_delay)
                    else:
                        recovery_results['failed_actions'] += 1
                        self.logger.error(f"Recovery action failed: {action_type} for {url}")
                
                except Exception as e:
                    action_result['error'] = str(e)
                    recovery_results['failed_actions'] += 1
                    self.logger.error(f"Error during recovery action {action_type} for {url}: {e}")
                
                recovery_results['actions_performed'].append(action_result)
        
        self.logger.info(f"Recovery completed: {recovery_results['successful_actions']} successful, "
                        f"{recovery_results['failed_actions']} failed")
        
        return recovery_results
    
    def save_recovery_results(self, results: Dict, filename: str = None):
        """Save recovery results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/recovery_results_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Recovery results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Auto-Recovery System")
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    parser.add_argument('--results', help='JSON file with monitoring results to recover from')
    parser.add_argument('--action', help='Single recovery action to perform')
    parser.add_argument('--target', help='Target for the recovery action')
    parser.add_argument('--output', help='Output file for recovery results')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    recovery = RecoveryManager(args.config)
    
    if args.dry_run:
        recovery.logger.info("DRY RUN MODE - No actions will be performed")
    
    if args.action:
        # Perform single recovery action
        if args.dry_run:
            recovery.logger.info(f"Would perform action: {args.action} (target: {args.target})")
        else:
            success = recovery.perform_recovery_action(args.action, args.target)
            if success:
                print(f"✅ Recovery action '{args.action}' completed successfully")
            else:
                print(f"❌ Recovery action '{args.action}' failed")
                sys.exit(1)
    
    elif args.results:
        # Perform recovery based on monitoring results
        try:
            with open(args.results, 'r') as f:
                results = json.load(f)
            
            if args.dry_run:
                down_sites = [result for result in results if result.get('status') == 'down']
                recovery.logger.info(f"Would attempt recovery for {len(down_sites)} down sites")
                for site in down_sites:
                    recovery.logger.info(f"Would recover: {site.get('url', 'unknown')}")
            else:
                recovery_results = recovery.recover_from_monitoring_results(results)
                
                if args.output:
                    recovery.save_recovery_results(recovery_results, args.output)
                else:
                    print(json.dumps(recovery_results, indent=2))
                
                if recovery_results['failed_actions'] > 0:
                    print(f"⚠️ Recovery completed with {recovery_results['failed_actions']} failures")
                else:
                    print("✅ Recovery completed successfully")
        
        except Exception as e:
            print(f"❌ Error reading results file: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()