#!/usr/bin/env python3
"""
Website Monitor Script
Monitors website availability, response times, and validates HTTP responses.
"""

import requests
import time
import logging
import argparse
import yaml
import json
import ssl
import socket
from urllib.parse import urlparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class WebsiteMonitor:
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the website monitor with configuration."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            # Default configuration if file doesn't exist
            return {
                'monitoring': {
                    'timeout': 10,
                    'retry_count': 3,
                    'retry_delay': 5,
                    'check_interval': 60
                },
                'alerts': {
                    'response_time_threshold': 5.0
                }
            }
    
    def setup_logging(self):
        """Set up logging configuration."""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        log_file = self.config.get('logging', {}).get('file', 'logs/monitor.log')
        
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
    
    def check_website(self, url: str, expected_status: List[int] = None, 
                     expected_content: str = None) -> Dict:
        """
        Check a single website's health.
        
        Args:
            url: The URL to check
            expected_status: List of acceptable HTTP status codes (default: [200, 301, 302])
            expected_content: Optional content to verify in the response
            
        Returns:
            Dictionary with check results
        """
        if expected_status is None:
            expected_status = [200, 301, 302]
            
        result = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'response_time': None,
            'status_code': None,
            'error': None,
            'ssl_valid': None,
            'content_check': None
        }
        
        start_time = time.time()
        
        try:
            # Configure session with timeout and retries
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Website-Monitor/1.0 (+https://github.com/your-repo)'
            })
            
            # Make the request
            response = session.get(
                url,
                timeout=self.config['monitoring']['timeout'],
                allow_redirects=True,
                verify=True  # Verify SSL certificates
            )
            
            end_time = time.time()
            result['response_time'] = round(end_time - start_time, 3)
            result['status_code'] = response.status_code
            
            # Check status code
            if response.status_code in expected_status:
                result['status'] = 'up'
                self.logger.info(f"✓ {url} is UP (Status: {response.status_code}, "
                               f"Response time: {result['response_time']}s)")
            else:
                result['status'] = 'down'
                result['error'] = f"Unexpected status code: {response.status_code}"
                self.logger.warning(f"✗ {url} returned unexpected status: {response.status_code}")
            
            # Check content if specified
            if expected_content and result['status'] == 'up':
                if expected_content in response.text:
                    result['content_check'] = 'pass'
                    self.logger.info(f"✓ Content check passed for {url}")
                else:
                    result['content_check'] = 'fail'
                    result['status'] = 'degraded'
                    result['error'] = "Expected content not found"
                    self.logger.warning(f"✗ Content check failed for {url}")
            
            # Check SSL certificate
            result['ssl_valid'] = self._check_ssl_certificate(url)
            
            # Check response time threshold
            threshold = self.config['alerts']['response_time_threshold']
            if result['response_time'] > threshold:
                self.logger.warning(f"⚠ {url} response time ({result['response_time']}s) "
                                  f"exceeds threshold ({threshold}s)")
                if result['status'] == 'up':
                    result['status'] = 'slow'
                    
        except requests.exceptions.Timeout:
            result['status'] = 'down'
            result['error'] = 'Request timeout'
            result['response_time'] = self.config['monitoring']['timeout']
            self.logger.error(f"✗ {url} timed out after {result['response_time']}s")
            
        except requests.exceptions.ConnectionError as e:
            result['status'] = 'down'
            result['error'] = f'Connection error: {str(e)}'
            self.logger.error(f"✗ {url} connection failed: {e}")
            
        except requests.exceptions.SSLError as e:
            result['status'] = 'down'
            result['error'] = f'SSL error: {str(e)}'
            result['ssl_valid'] = False
            self.logger.error(f"✗ {url} SSL error: {e}")
            
        except Exception as e:
            result['status'] = 'down'
            result['error'] = f'Unexpected error: {str(e)}'
            self.logger.error(f"✗ {url} unexpected error: {e}")
            
        finally:
            if 'session' in locals():
                session.close()
        
        return result
    
    def _check_ssl_certificate(self, url: str) -> Optional[bool]:
        """Check SSL certificate validity."""
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme != 'https':
                return None  # Not applicable for non-HTTPS URLs
                
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    # Certificate is valid if we reach here without exception
                    return True
                    
        except Exception as e:
            self.logger.warning(f"SSL check failed for {url}: {e}")
            return False
    
    def check_port(self, host: str, port: int, timeout: int = 5) -> Dict:
        """Check if a specific port is accessible."""
        result = {
            'host': host,
            'port': port,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'response_time': None,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result_code = sock.connect_ex((host, port))
            
            end_time = time.time()
            result['response_time'] = round(end_time - start_time, 3)
            
            if result_code == 0:
                result['status'] = 'open'
                self.logger.info(f"✓ Port {port} on {host} is OPEN")
            else:
                result['status'] = 'closed'
                result['error'] = f"Port {port} is closed or filtered"
                self.logger.warning(f"✗ Port {port} on {host} is CLOSED")
                
        except socket.gaierror as e:
            result['status'] = 'error'
            result['error'] = f'DNS resolution failed: {str(e)}'
            self.logger.error(f"✗ DNS resolution failed for {host}: {e}")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f'Connection error: {str(e)}'
            self.logger.error(f"✗ Port check failed for {host}:{port} - {e}")
            
        finally:
            if 'sock' in locals():
                sock.close()
        
        return result
    
    def monitor_websites(self, websites: List[Dict]) -> List[Dict]:
        """Monitor multiple websites."""
        results = []
        
        for site in websites:
            url = site['url']
            expected_status = site.get('expected_status', [200, 301, 302])
            expected_content = site.get('expected_content')
            
            self.logger.info(f"Checking {url}...")
            
            # Retry logic
            for attempt in range(self.config['monitoring']['retry_count']):
                result = self.check_website(url, expected_status, expected_content)
                
                if result['status'] in ['up', 'slow']:
                    break
                    
                if attempt < self.config['monitoring']['retry_count'] - 1:
                    self.logger.info(f"Retrying {url} in {self.config['monitoring']['retry_delay']}s "
                                   f"(attempt {attempt + 1}/{self.config['monitoring']['retry_count']})")
                    time.sleep(self.config['monitoring']['retry_delay'])
            
            results.append(result)
            
            # Check ports if specified
            if 'ports' in site:
                parsed_url = urlparse(url)
                host = parsed_url.hostname
                
                for port in site['ports']:
                    port_result = self.check_port(host, port)
                    results.append(port_result)
        
        return results
    
    def health_check(self) -> bool:
        """Perform a health check of the monitoring system itself."""
        try:
            # Test configuration loading
            if not self.config:
                return False
                
            # Test logging
            self.logger.info("Health check: Monitor system is healthy")
            
            # Test network connectivity (optional)
            test_result = self.check_website("https://httpbin.org/status/200")
            
            return test_result['status'] in ['up', 'slow']
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def save_results(self, results: List[Dict], filename: str = None):
        """Save monitoring results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/monitor_results_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Website Monitor")
    parser.add_argument('--url', help='Single URL to monitor')
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    parser.add_argument('--websites', default='config/websites.yaml', help='Websites configuration file')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--health-check', action='store_true', help='Perform health check')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (continuous monitoring)')
    
    args = parser.parse_args()
    
    monitor = WebsiteMonitor(args.config)
    
    if args.health_check:
        if monitor.health_check():
            print("Health check: OK")
            sys.exit(0)
        else:
            print("Health check: FAILED")
            sys.exit(1)
    
    if args.url:
        # Monitor single URL
        result = monitor.check_website(args.url)
        print(json.dumps(result, indent=2))
        
        if args.output:
            monitor.save_results([result], args.output)
    
    elif os.path.exists(args.websites):
        # Monitor websites from configuration file
        with open(args.websites, 'r') as f:
            websites_config = yaml.safe_load(f)
        
        websites = websites_config.get('websites', [])
        
        if args.daemon:
            # Continuous monitoring
            interval = monitor.config['monitoring']['check_interval']
            monitor.logger.info(f"Starting daemon mode with {interval}s interval")
            
            try:
                while True:
                    results = monitor.monitor_websites(websites)
                    
                    if args.output:
                        monitor.save_results(results, args.output)
                    
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                monitor.logger.info("Monitoring stopped by user")
        else:
            # Single check
            results = monitor.monitor_websites(websites)
            
            if args.output:
                monitor.save_results(results, args.output)
            else:
                print(json.dumps(results, indent=2))
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()