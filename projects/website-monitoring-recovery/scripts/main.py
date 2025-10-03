#!/usr/bin/env python3
"""
Main Orchestration Script
Coordinates website monitoring, email notifications, and auto-recovery actions.
"""

import sys
import os
import time
import json
import yaml
import logging
import argparse
import schedule
import signal
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from monitor import WebsiteMonitor
from emailer import EmailNotifier
from recovery import RecoveryManager

class MonitoringOrchestrator:
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the monitoring orchestrator."""
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize components
        self.monitor = WebsiteMonitor(config_path)
        self.emailer = EmailNotifier(config_path)
        self.recovery = RecoveryManager(config_path)
        
        # Orchestration settings
        self.orchestration_settings = self.config.get('orchestration', {})
        self.check_interval = self.orchestration_settings.get('check_interval', 300)  # 5 minutes default
        self.enable_recovery = self.orchestration_settings.get('enable_recovery', True)
        self.enable_notifications = self.orchestration_settings.get('enable_notifications', True)
        
        # State tracking
        self.previous_results = {}
        self.failure_counts = {}
        self.last_notification_times = {}
        self.running = False
        
        # Graceful shutdown handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return {
                'orchestration': {
                    'check_interval': 300,
                    'enable_recovery': True,
                    'enable_notifications': True,
                    'max_failures_before_recovery': 3,
                    'notification_cooldown': 1800  # 30 minutes
                },
                'logging': {
                    'level': 'INFO',
                    'file': 'logs/main.log'
                }
            }
    
    def setup_logging(self):
        """Set up logging configuration."""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        log_file = self.config.get('logging', {}).get('file', 'logs/main.log')
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def load_websites_config(self) -> List[Dict]:
        """Load websites configuration from file."""
        websites_config_path = self.config.get('websites_config', 'config/websites.yaml')
        
        try:
            with open(websites_config_path, 'r') as f:
                websites_config = yaml.safe_load(f)
            
            websites = websites_config.get('websites', [])
            self.logger.info(f"Loaded {len(websites)} websites from configuration")
            return websites
        
        except FileNotFoundError:
            self.logger.error(f"Websites configuration file not found: {websites_config_path}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading websites configuration: {e}")
            return []
    
    def update_failure_tracking(self, results: List[Dict]):
        """Update failure count tracking for websites."""
        for result in results:
            url = result.get('url')
            if not url:
                continue
            
            status = result.get('status')
            
            # Initialize tracking if needed
            if url not in self.failure_counts:
                self.failure_counts[url] = 0
            
            # Update failure count
            if status == 'down':
                self.failure_counts[url] += 1
            elif status in ['up', 'slow']:
                # Reset on successful check
                if self.failure_counts[url] > 0:
                    self.logger.info(f"Resetting failure count for {url} (now {status})")
                self.failure_counts[url] = 0
            
            self.logger.debug(f"Failure count for {url}: {self.failure_counts[url]}")
    
    def detect_state_changes(self, current_results: List[Dict]) -> List[Dict]:
        """Detect state changes from previous monitoring results."""
        state_changes = []
        
        for result in current_results:
            url = result.get('url')
            current_status = result.get('status')
            
            if url in self.previous_results:
                previous_status = self.previous_results[url].get('status')
                
                if previous_status != current_status:
                    change = {
                        'url': url,
                        'previous_status': previous_status,
                        'current_status': current_status,
                        'timestamp': datetime.now().isoformat(),
                        'result': result
                    }
                    
                    state_changes.append(change)
                    self.logger.info(f"State change detected for {url}: {previous_status} → {current_status}")
                
                # Add previous status to result for email notifications
                result['previous_status'] = previous_status
        
        # Update previous results
        self.previous_results = {result.get('url'): result for result in current_results if result.get('url')}
        
        return state_changes
    
    def should_send_notification(self, results: List[Dict]) -> bool:
        """Determine if a notification should be sent."""
        if not self.enable_notifications:
            return False
        
        # Check for down sites
        down_sites = [r for r in results if r.get('status') == 'down']
        if down_sites:
            return True
        
        # Check for recovered sites
        recovered_sites = [r for r in results if r.get('status') == 'up' and 
                          r.get('previous_status') in ['down', 'slow', 'degraded']]
        if recovered_sites:
            return True
        
        # Check for degraded sites
        degraded_sites = [r for r in results if r.get('status') in ['slow', 'degraded']]
        if degraded_sites:
            return True
        
        return False
    
    def should_attempt_recovery(self, results: List[Dict]) -> bool:
        """Determine if recovery should be attempted."""
        if not self.enable_recovery:
            return False
        
        max_failures = self.orchestration_settings.get('max_failures_before_recovery', 3)
        
        # Check if any site has exceeded failure threshold
        for result in results:
            url = result.get('url')
            if result.get('status') == 'down' and self.failure_counts.get(url, 0) >= max_failures:
                return True
        
        return False
    
    def perform_monitoring_cycle(self) -> Dict:
        """Perform a complete monitoring cycle."""
        cycle_start = datetime.now()
        self.logger.info("Starting monitoring cycle")
        
        cycle_results = {
            'timestamp': cycle_start.isoformat(),
            'monitoring_results': [],
            'state_changes': [],
            'notifications_sent': False,
            'recovery_attempted': False,
            'recovery_results': None,
            'errors': []
        }
        
        try:
            # Load websites configuration
            websites = self.load_websites_config()
            if not websites:
                error_msg = "No websites configured for monitoring"
                self.logger.error(error_msg)
                cycle_results['errors'].append(error_msg)
                return cycle_results
            
            # Perform monitoring
            self.logger.info(f"Monitoring {len(websites)} websites")
            monitoring_results = self.monitor.monitor_websites(websites)
            cycle_results['monitoring_results'] = monitoring_results
            
            # Update failure tracking
            self.update_failure_tracking(monitoring_results)
            
            # Detect state changes
            state_changes = self.detect_state_changes(monitoring_results)
            cycle_results['state_changes'] = state_changes
            
            # Summary logging
            status_counts = {}
            for result in monitoring_results:
                status = result.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            self.logger.info(f"Monitoring results: {dict(status_counts)}")
            
            # Send notifications if needed
            if self.should_send_notification(monitoring_results):
                try:
                    success = self.emailer.send_monitoring_alert(monitoring_results)
                    cycle_results['notifications_sent'] = success
                    
                    if success:
                        self.logger.info("Notification sent successfully")
                    else:
                        error_msg = "Failed to send notification"
                        self.logger.error(error_msg)
                        cycle_results['errors'].append(error_msg)
                
                except Exception as e:
                    error_msg = f"Error sending notification: {e}"
                    self.logger.error(error_msg)
                    cycle_results['errors'].append(error_msg)
            
            # Attempt recovery if needed
            if self.should_attempt_recovery(monitoring_results):
                try:
                    self.logger.info("Attempting recovery actions")
                    recovery_results = self.recovery.recover_from_monitoring_results(monitoring_results)
                    cycle_results['recovery_attempted'] = True
                    cycle_results['recovery_results'] = recovery_results
                    
                    if recovery_results.get('enabled'):
                        successful = recovery_results.get('successful_actions', 0)
                        failed = recovery_results.get('failed_actions', 0)
                        self.logger.info(f"Recovery completed: {successful} successful, {failed} failed")
                    else:
                        self.logger.info("Recovery is disabled")
                
                except Exception as e:
                    error_msg = f"Error during recovery: {e}"
                    self.logger.error(error_msg)
                    cycle_results['errors'].append(error_msg)
            
        except Exception as e:
            error_msg = f"Error during monitoring cycle: {e}"
            self.logger.error(error_msg)
            cycle_results['errors'].append(error_msg)
        
        cycle_end = datetime.now()
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        
        self.logger.info(f"Monitoring cycle completed in {cycle_duration:.2f}s")
        cycle_results['duration_seconds'] = cycle_duration
        
        return cycle_results
    
    def save_cycle_results(self, results: Dict, filename: str = None):
        """Save cycle results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/cycle_results_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.debug(f"Cycle results saved to {filename}")
    
    def run_single_cycle(self):
        """Run a single monitoring cycle."""
        results = self.perform_monitoring_cycle()
        
        # Save results if configured
        if self.orchestration_settings.get('save_results', False):
            self.save_cycle_results(results)
        
        return results
    
    def run_daemon(self):
        """Run the monitoring system as a daemon."""
        self.logger.info("Starting monitoring daemon")
        self.logger.info(f"Check interval: {self.check_interval} seconds")
        self.running = True
        
        # Schedule the monitoring job
        schedule.every(self.check_interval).seconds.do(self.run_single_cycle)
        
        try:
            # Run initial check
            self.run_single_cycle()
            
            # Main daemon loop
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        except KeyboardInterrupt:
            self.logger.info("Monitoring daemon interrupted by user")
        
        except Exception as e:
            self.logger.error(f"Monitoring daemon error: {e}")
            raise
        
        finally:
            self.running = False
            self.logger.info("Monitoring daemon stopped")
    
    def run_scheduled_daemon(self):
        """Run with human-readable schedule."""
        self.logger.info("Starting scheduled monitoring daemon")
        self.running = True
        
        # Get schedule from config
        schedule_config = self.orchestration_settings.get('schedule', '*/5 * * * *')  # Every 5 minutes
        
        # For simplicity, use interval-based scheduling
        # In production, you might want to use a proper cron-like scheduler
        interval_minutes = self.orchestration_settings.get('interval_minutes', 5)
        
        schedule.every(interval_minutes).minutes.do(self.run_single_cycle)
        
        try:
            # Run initial check
            self.run_single_cycle()
            
            # Main loop
            while self.running:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
        
        except KeyboardInterrupt:
            self.logger.info("Scheduled monitoring daemon interrupted by user")
        
        finally:
            self.running = False
            self.logger.info("Scheduled monitoring daemon stopped")


def main():
    parser = argparse.ArgumentParser(description="Website Monitoring Orchestrator")
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (continuous monitoring)')
    parser.add_argument('--scheduled', action='store_true', help='Run with human-readable schedule')
    parser.add_argument('--single', action='store_true', help='Run single monitoring cycle')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--no-recovery', action='store_true', help='Disable recovery actions')
    parser.add_argument('--no-notifications', action='store_true', help='Disable email notifications')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = MonitoringOrchestrator(args.config)
    
    # Override settings based on arguments
    if args.no_recovery:
        orchestrator.enable_recovery = False
        orchestrator.logger.info("Recovery disabled by command line argument")
    
    if args.no_notifications:
        orchestrator.enable_notifications = False
        orchestrator.logger.info("Notifications disabled by command line argument")
    
    if args.dry_run:
        orchestrator.logger.info("DRY RUN MODE - No actual recovery actions or notifications will be sent")
        orchestrator.enable_recovery = False
        orchestrator.enable_notifications = False
    
    try:
        if args.single:
            # Run single monitoring cycle
            results = orchestrator.run_single_cycle()
            
            if args.output:
                orchestrator.save_cycle_results(results, args.output)
            else:
                print(json.dumps(results, indent=2))
        
        elif args.scheduled:
            # Run with human-readable schedule
            orchestrator.run_scheduled_daemon()
        
        elif args.daemon:
            # Run as continuous daemon
            orchestrator.run_daemon()
        
        else:
            # Default to single cycle
            results = orchestrator.run_single_cycle()
            print(json.dumps(results, indent=2))
    
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")
        sys.exit(0)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()