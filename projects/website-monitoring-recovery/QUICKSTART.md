# Quick Start Guide

Get your website monitoring system up and running in minutes!

## 🚀 Quick Setup (5 minutes)

### 1. Set up the project locally
```bash
# Navigate to the project directory
cd website-monitoring-recovery

# Set up the environment
./deploy.sh setup
```

### 2. Configure your credentials
```bash
# Edit the environment file with your credentials
cp config/.env.example .env
nano .env
```

**Minimum required settings:**
```bash
# Email settings (use Gmail for quick setup)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password
TO_EMAILS=your-alerts@email.com

# Optional: Linode API token (only needed for cloud deployment)
LINODE_API_TOKEN=your-linode-token
```

### 3. Configure websites to monitor
```bash
# Edit the websites configuration
nano config/websites.yaml
```

**Simple example:**
```yaml
websites:
  - url: https://your-website.com
    expected_status: [200]
    
  - url: https://your-api.com/health
    expected_status: [200]
    expected_content: "OK"
```

### 4. Test the system
```bash
# Activate the Python environment
source venv/bin/activate

# Run a single monitoring check (dry run)
python scripts/main.py --single --dry-run

# Run a real monitoring check
python scripts/main.py --single
```

### 5. Start continuous monitoring
```bash
# Run as daemon (continuous monitoring)
python scripts/main.py --daemon
```

## 📧 Gmail Setup (2 minutes)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. **Use the app password** in your `.env` file (not your regular password)

## ☁️ Linode Deployment (Optional)

### 1. Get Linode API Token
- Go to [Linode Cloud Manager](https://cloud.linode.com/profile/tokens)
- Create a Personal Access Token with full permissions
- Add it to your `.env` file

### 2. Create and deploy to server
```bash
# Create a new Linode server
./deploy.sh create --region us-east --type g6-nanode-1

# Deploy your application to the server
./deploy.sh deploy --instance your-server-id
```

## 🐳 Docker Deployment (Alternative)

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your credentials

# Start with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f website-monitor
```

## 🔧 Basic Usage

### Monitor a single website
```bash
python scripts/monitor.py --url https://example.com
```

### Send a test email
```bash
python scripts/emailer.py --test
```

### Test recovery actions (dry run)
```bash
python scripts/recovery.py --action restart_nginx --dry-run
```

### Check system health
```bash
python scripts/monitor.py --health-check
```

## 📊 Understanding the Output

### Monitoring Results
```json
{
  "url": "https://example.com",
  "status": "up",           // up, down, slow, degraded
  "response_time": 1.234,   // seconds
  "status_code": 200,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Status Meanings
- **up**: Website is working normally
- **down**: Website is not accessible
- **slow**: Website responds but exceeds time threshold
- **degraded**: Website accessible but has issues (content, SSL, etc.)

## 🚨 What Happens When a Site Goes Down?

1. **Detection**: System detects website is down
2. **Retry**: Automatically retries 3 times (configurable)
3. **Alert**: Sends email notification
4. **Recovery**: After 3 failures, attempts recovery actions:
   - Restart web server (Nginx/Apache)
   - Restart application containers
   - Reboot server (last resort)
5. **Notification**: Sends recovery status email

## 📁 Key Files

- `config/config.yaml` - Main configuration
- `config/websites.yaml` - Websites to monitor
- `.env` - Your credentials (never commit to git!)
- `logs/` - All system logs
- `scripts/main.py` - Main monitoring script

## 🆘 Troubleshooting

### "No module named 'requests'"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Email authentication failed"
- Make sure you're using an app-specific password, not your regular Gmail password
- Enable 2-Factor Authentication first

### "Permission denied" on deploy.sh
```bash
chmod +x deploy.sh
```

### Check logs for errors
```bash
tail -f logs/main.log
```

## 🔄 Common Commands

```bash
# Set up everything from scratch
./deploy.sh setup

# Run single check
python scripts/main.py --single

# Run continuous monitoring
python scripts/main.py --daemon

# Test email notifications
python scripts/emailer.py --test

# Create Linode server
./deploy.sh create

# List Linode servers
./deploy.sh list

# Deploy to existing server
./deploy.sh deploy --instance server-name

# Stop monitoring (Ctrl+C or)
pkill -f "python scripts/main.py"
```

## 🎯 Next Steps

1. **Customize monitoring**: Edit `config/websites.yaml` with your sites
2. **Set up recovery actions**: Configure what happens when sites go down
3. **Deploy to cloud**: Use Linode for production monitoring
4. **Add more websites**: The system can monitor unlimited sites
5. **Set up alerts**: Configure email notifications for your team

---

**Need help?** Check the full `README.md` or examine the logs in the `logs/` directory.