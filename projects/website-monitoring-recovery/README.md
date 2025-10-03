# Website Monitoring and Recovery System

A comprehensive Python-based website monitoring system that automatically detects downtime, sends notifications, and performs recovery actions on Linode cloud infrastructure.

## 🚀 Features

- **Website Health Monitoring**: Continuously monitors website availability and response times
- **Email Notifications**: Sends instant alerts when websites go down
- **Automatic Recovery**: Automatically restarts applications and servers when issues are detected
- **Docker Support**: Fully containerized for easy deployment
- **Linode Integration**: Designed for deployment on Linode cloud servers
- **Configurable**: Easy to configure monitoring intervals, email settings, and recovery actions

## 🛠 Technologies Used

- **Python 3.9+**: Core programming language
- **Docker**: Containerization
- **Linode API**: Cloud server management
- **SMTP**: Email notifications
- **Linux**: Target deployment environment

## 📁 Project Structure

```
website-monitoring-recovery/
├── scripts/
│   ├── monitor.py              # Website monitoring script
│   ├── emailer.py             # Email notification handler
│   ├── recovery.py            # Auto-recovery operations
│   ├── main.py                # Main orchestration script
│   └── linode_setup.py        # Linode server setup
├── config/
│   ├── config.yaml            # Main configuration file
│   ├── .env.example           # Environment variables template
│   └── websites.yaml          # Websites to monitor
├── logs/                      # Log files directory
├── Dockerfile                 # Docker image definition
├── docker-compose.yml         # Docker compose configuration
├── requirements.txt           # Python dependencies
├── deploy.sh                  # Deployment script
└── README.md                  # This file
```

## ⚙️ Setup Instructions

### 1. Local Development Setup

```bash
# Clone or create the project
cd website-monitoring-recovery

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp config/.env.example .env

# Edit configuration files
nano config/config.yaml
nano .env
```

### 2. Configuration

Edit `config/config.yaml` to configure:
- Monitoring intervals
- Email settings
- Recovery actions
- Linode API settings

Edit `.env` with your credentials:
- Email credentials
- Linode API token
- Other sensitive information

### 3. Docker Deployment

```bash
# Build the Docker image
docker build -t website-monitor .

# Run with docker-compose
docker-compose up -d
```

### 4. Linode Cloud Deployment

```bash
# Run the deployment script
chmod +x deploy.sh
./deploy.sh
```

## 🔧 Usage

### Running Locally
```bash
python scripts/main.py
```

### Running in Docker
```bash
docker-compose up
```

### Manual Monitoring
```bash
python scripts/monitor.py --url https://example.com
```

### Testing Email Notifications
```bash
python scripts/emailer.py --test
```

## 📊 Monitoring Features

- **HTTP Status Code Validation**: Checks for 200, 301, 302 responses
- **Response Time Monitoring**: Tracks website performance
- **Content Validation**: Optionally checks for specific content
- **SSL Certificate Monitoring**: Validates SSL certificates
- **Port Availability**: Checks if specific ports are accessible

## 🔄 Recovery Actions

- **Service Restart**: Automatically restarts failed services
- **Container Restart**: Restarts Docker containers
- **Server Reboot**: Reboots the entire server if needed
- **Load Balancer Update**: Updates load balancer configurations
- **Custom Scripts**: Execute custom recovery scripts

## 📧 Notification Methods

- **Email Alerts**: SMTP-based email notifications
- **Log Files**: Detailed logging for troubleshooting
- **Status Dashboard**: Optional web dashboard (future feature)

## 🚨 Alert Levels

- **INFO**: Service recovered, routine checks
- **WARNING**: Degraded performance detected
- **ERROR**: Service unavailable
- **CRITICAL**: Multiple failures, recovery actions triggered

## 🔐 Security Considerations

- Store sensitive credentials in environment variables
- Use application-specific passwords for email
- Limit Linode API token permissions
- Regular security updates for dependencies

## 📈 Scaling

- Multiple website monitoring
- Distributed monitoring across regions
- Load balancing monitoring
- Database monitoring capabilities

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the logs in the `logs/` directory
2. Review configuration files
3. Test individual components
4. Create an issue with detailed information

## 🔄 Version History

- **v1.0.0**: Initial release with basic monitoring and recovery
- **v1.1.0**: Added Linode integration and Docker support
- **v1.2.0**: Enhanced email notifications and logging

---

**Note**: This system is designed for educational and demonstration purposes. For production use, consider additional security hardening and monitoring features.