#!/usr/bin/env python3
"""
Email Notification Script
Sends email alerts when websites are down or experiencing issues.
"""

import smtplib
import ssl
import logging
import argparse
import yaml
import json
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EmailNotifier:
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the email notifier with configuration."""
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Email configuration from environment variables or config
        self.smtp_server = os.getenv('SMTP_SERVER') or self.config.get('email', {}).get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT') or self.config.get('email', {}).get('smtp_port', 587))
        self.email_user = os.getenv('EMAIL_USER') or self.config.get('email', {}).get('username')
        self.email_password = os.getenv('EMAIL_PASSWORD') or self.config.get('email', {}).get('password')
        self.from_email = os.getenv('FROM_EMAIL') or self.email_user
        
        # Recipient configuration
        self.to_emails = []
        if os.getenv('TO_EMAILS'):
            self.to_emails = [email.strip() for email in os.getenv('TO_EMAILS').split(',')]
        elif self.config.get('email', {}).get('recipients'):
            self.to_emails = self.config['email']['recipients']
        
        # Alert settings
        self.alert_settings = self.config.get('alerts', {})
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return {
                'email': {
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'use_tls': True
                },
                'alerts': {
                    'send_on_recovery': True,
                    'send_on_degraded': True,
                    'cooldown_minutes': 30
                }
            }
    
    def setup_logging(self):
        """Set up logging configuration."""
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        log_file = self.config.get('logging', {}).get('file', 'logs/emailer.log')
        
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
    
    def validate_configuration(self) -> bool:
        """Validate email configuration."""
        if not self.email_user:
            self.logger.error("Email username not configured")
            return False
        
        if not self.email_password:
            self.logger.error("Email password not configured")
            return False
        
        if not self.to_emails:
            self.logger.error("No recipient emails configured")
            return False
        
        return True
    
    def send_email(self, subject: str, body: str, html_body: str = None, 
                  attachments: List[str] = None, priority: str = "normal") -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            attachments: List of file paths to attach (optional)
            priority: Email priority (low, normal, high)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.validate_configuration():
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = subject
            
            # Set priority
            if priority.lower() == 'high':
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            elif priority.lower() == 'low':
                msg['X-Priority'] = '5'
                msg['X-MSMail-Priority'] = 'Low'
            
            # Add timestamp
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Add body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        msg.attach(part)
            
            # Send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.config.get('email', {}).get('use_tls', True):
                    server.starttls(context=context)
                
                server.login(self.email_user, self.email_password)
                text = msg.as_string()
                server.sendmail(self.from_email, self.to_emails, text)
            
            self.logger.info(f"Email sent successfully to {', '.join(self.to_emails)}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def create_alert_email(self, monitoring_results: List[Dict]) -> tuple:
        """
        Create alert email content from monitoring results.
        
        Returns:
            Tuple of (subject, plain_text_body, html_body, priority)
        """
        down_sites = [result for result in monitoring_results if result.get('status') == 'down']
        degraded_sites = [result for result in monitoring_results if result.get('status') in ['slow', 'degraded']]
        recovered_sites = [result for result in monitoring_results if result.get('status') == 'up' and 
                          result.get('previous_status') in ['down', 'slow', 'degraded']]
        
        # Determine alert level and subject
        if down_sites:
            alert_level = "🔴 CRITICAL"
            priority = "high"
        elif degraded_sites:
            alert_level = "🟡 WARNING"
            priority = "normal"
        elif recovered_sites:
            alert_level = "🟢 RECOVERY"
            priority = "normal"
        else:
            alert_level = "ℹ️ INFO"
            priority = "low"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"{alert_level} - Website Monitoring Alert - {timestamp}"
        
        # Create plain text body
        plain_body = f"""Website Monitoring Alert
========================

Alert Level: {alert_level}
Timestamp: {timestamp}
"""
        
        if down_sites:
            plain_body += "\nWebsites DOWN:\n"
            for site in down_sites:
                plain_body += f"❌ {site['url']} - {site.get('error', 'Unknown error')}\n"
        
        if degraded_sites:
            plain_body += "\nWebsites with ISSUES:\n"
            for site in degraded_sites:
                plain_body += f"⚠️ {site['url']} - Status: {site['status']}"
                if site.get('response_time'):
                    plain_body += f" (Response time: {site['response_time']}s)"
                plain_body += "\n"
        
        if recovered_sites:
            plain_body += "\nRecovered Websites:\n"
            for site in recovered_sites:
                plain_body += f"✅ {site['url']} - Back online\n"
        
        plain_body += f"\n\nMonitoring System: Website Monitor v1.0\nGenerated at: {timestamp}"
        
        # Create HTML body
        alert_class = "critical" if down_sites else "warning" if degraded_sites else "recovery" if recovered_sites else "info"
        
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .alert-critical {{ color: #d32f2f; }}
        .alert-warning {{ color: #f57c00; }}
        .alert-recovery {{ color: #388e3c; }}
        .alert-info {{ color: #1976d2; }}
        .site-list {{ margin: 15px 0; }}
        .site-item {{ padding: 8px; margin: 5px 0; border-left: 4px solid #ccc; }}
        .site-down {{ border-left-color: #d32f2f; background-color: #ffebee; }}
        .site-degraded {{ border-left-color: #f57c00; background-color: #fff8e1; }}
        .site-recovered {{ border-left-color: #388e3c; background-color: #e8f5e8; }}
        .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ccc; 
                  font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>Website Monitoring Alert</h2>
        <p><strong>Alert Level:</strong> <span class="alert-{alert_class}">{alert_level}</span></p>
        <p><strong>Timestamp:</strong> {timestamp}</p>
    </div>
"""
        
        if down_sites:
            html_body += '<div class="site-list"><h3>🔴 Websites DOWN:</h3>'
            for site in down_sites:
                html_body += f'<div class="site-item site-down"><strong>{site["url"]}</strong><br>'
                html_body += f'<small>Error: {site.get("error", "Unknown error")}</small></div>'
            html_body += '</div>'
        
        if degraded_sites:
            html_body += '<div class="site-list"><h3>🟡 Websites with ISSUES:</h3>'
            for site in degraded_sites:
                html_body += f'<div class="site-item site-degraded"><strong>{site["url"]}</strong><br>'
                html_body += f'<small>Status: {site["status"]}'
                if site.get('response_time'):
                    html_body += f' (Response time: {site["response_time"]}s)'
                html_body += '</small></div>'
            html_body += '</div>'
        
        if recovered_sites:
            html_body += '<div class="site-list"><h3>🟢 Recovered Websites:</h3>'
            for site in recovered_sites:
                html_body += f'<div class="site-item site-recovered"><strong>{site["url"]}</strong><br>'
                html_body += '<small>Back online</small></div>'
            html_body += '</div>'
        
        html_body += f"""    <div class="footer">
        <p><strong>Monitoring System:</strong> Website Monitor v1.0</p>
        <p><strong>Generated at:</strong> {timestamp}</p>
    </div>
</body>
</html>"""
        
        return subject, plain_body, html_body, priority
    
    def should_send_alert(self, monitoring_results: List[Dict]) -> bool:
        """Determine if an alert should be sent based on results and settings."""
        has_down = any(result.get('status') == 'down' for result in monitoring_results)
        has_degraded = any(result.get('status') in ['slow', 'degraded'] for result in monitoring_results)
        has_recovered = any(result.get('status') == 'up' and 
                           result.get('previous_status') in ['down', 'slow', 'degraded'] 
                           for result in monitoring_results)
        
        # Always send for down sites
        if has_down:
            return True
        
        # Send for degraded sites if configured
        if has_degraded and self.alert_settings.get('send_on_degraded', True):
            return True
        
        # Send for recovered sites if configured
        if has_recovered and self.alert_settings.get('send_on_recovery', True):
            return True
        
        return False
    
    def send_monitoring_alert(self, monitoring_results: List[Dict], 
                            attachments: List[str] = None) -> bool:
        """Send a monitoring alert email."""
        if not self.should_send_alert(monitoring_results):
            self.logger.info("No alert needed based on current results")
            return True
        
        try:
            subject, plain_body, html_body, priority = self.create_alert_email(monitoring_results)
            
            success = self.send_email(
                subject=subject,
                body=plain_body,
                html_body=html_body,
                attachments=attachments,
                priority=priority
            )
            
            if success:
                self.logger.info(f"Monitoring alert sent successfully with priority: {priority}")
            else:
                self.logger.error("Failed to send monitoring alert")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error creating monitoring alert: {e}")
            return False
    
    def send_test_email(self) -> bool:
        """Send a test email to verify configuration."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        subject = f"🧪 Website Monitor - Test Email - {timestamp}"
        body = f"""This is a test email from the Website Monitoring System.

If you receive this email, the email configuration is working correctly.

Configuration Details:
- SMTP Server: {self.smtp_server}:{self.smtp_port}
- From Email: {self.from_email}
- To Emails: {', '.join(self.to_emails)}
- Timestamp: {timestamp}

Website Monitoring System v1.0"""
        
        html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; margin: 20px;">
    <h2>🧪 Website Monitor Test Email</h2>
    <p>This is a test email from the Website Monitoring System.</p>
    <p>If you receive this email, the email configuration is working correctly.</p>
    
    <h3>Configuration Details:</h3>
    <ul>
        <li><strong>SMTP Server:</strong> {self.smtp_server}:{self.smtp_port}</li>
        <li><strong>From Email:</strong> {self.from_email}</li>
        <li><strong>To Emails:</strong> {', '.join(self.to_emails)}</li>
        <li><strong>Timestamp:</strong> {timestamp}</li>
    </ul>
    
    <p><em>Website Monitoring System v1.0</em></p>
</body>
</html>"""
        
        return self.send_email(
            subject=subject,
            body=body,
            html_body=html_body,
            priority="normal"
        )


def main():
    parser = argparse.ArgumentParser(description="Email Notification System")
    parser.add_argument('--test', action='store_true', help='Send test email')
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    parser.add_argument('--results', help='JSON file with monitoring results to send alert for')
    parser.add_argument('--subject', help='Custom email subject')
    parser.add_argument('--body', help='Custom email body')
    parser.add_argument('--recipient', action='append', help='Additional recipient email')
    
    args = parser.parse_args()
    
    emailer = EmailNotifier(args.config)
    
    # Add additional recipients if specified
    if args.recipient:
        emailer.to_emails.extend(args.recipient)
    
    if args.test:
        success = emailer.send_test_email()
        if success:
            print("✅ Test email sent successfully!")
        else:
            print("❌ Failed to send test email")
            sys.exit(1)
    
    elif args.results:
        try:
            with open(args.results, 'r') as f:
                results = json.load(f)
            
            success = emailer.send_monitoring_alert(results)
            if success:
                print("✅ Monitoring alert sent successfully!")
            else:
                print("❌ Failed to send monitoring alert")
                sys.exit(1)
        
        except Exception as e:
            print(f"❌ Error reading results file: {e}")
            sys.exit(1)
    
    elif args.subject and args.body:
        success = emailer.send_email(
            subject=args.subject,
            body=args.body
        )
        if success:
            print("✅ Custom email sent successfully!")
        else:
            print("❌ Failed to send custom email")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()