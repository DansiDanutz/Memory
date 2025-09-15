# MemoApp WhatsApp Bot - Production Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Meta WhatsApp Setup](#meta-whatsapp-setup)
3. [Server Configuration](#server-configuration)
4. [Application Deployment](#application-deployment)
5. [SSL/HTTPS Configuration](#ssl-https-configuration)
6. [Monitoring Setup](#monitoring-setup)
7. [Backup Procedures](#backup-procedures)
8. [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Accounts
- Meta Business Account with WhatsApp Business API access
- Azure account with Cognitive Services (Speech)
- OpenAI account with API access
- Domain name with SSL certificate
- Server with Ubuntu 20.04+ or similar

### Required Software
```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3.9 python3-pip redis-server nginx certbot ffmpeg postgresql

# Python packages
pip3 install -r requirements.txt
```

### Required Environment Variables
Create `.env` file:
```bash
# WhatsApp Configuration
WHATSAPP_ACCESS_TOKEN=your_meta_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WEBHOOK_VERIFY_TOKEN=your_unique_verify_token_here

# Azure Speech Services
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=eastus

# OpenAI (for classification)
OPENAI_API_KEY=your_openai_api_key

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
APP_ENV=production
LOG_LEVEL=INFO
DEFAULT_TENANT_ID=memoapp
DEFAULT_DEPARTMENT_ID=general

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost/memoapp
```

## Meta WhatsApp Setup

### 1. Create Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click "My Apps" → "Create App"
3. Choose "Business" type
4. Fill in app details:
   - App Name: "MemoApp WhatsApp Bot"
   - App Contact Email: your-email@domain.com
   - Business Account: Select your business

### 2. Add WhatsApp Product

1. In your app dashboard, click "Add Product"
2. Find "WhatsApp" and click "Set Up"
3. Navigate to WhatsApp → Getting Started

### 3. Configure Phone Number

1. Add a phone number or use the test number
2. Verify the phone number via SMS/Voice
3. Copy the Phone Number ID (you'll need this)

Example:
```
Phone Number ID: 115769834587455
```

### 4. Generate Access Token

1. Go to WhatsApp → API Setup
2. Under "Temporary access token", click "Generate"
3. Copy the token (valid for 24 hours for testing)
4. For production, create a System User:
   - Business Settings → Users → System Users
   - Add System User with "Admin" role
   - Generate token with these permissions:
     - whatsapp_business_messaging
     - whatsapp_business_management

### 5. Configure Webhook

1. Go to WhatsApp → Configuration → Webhook
2. Enter your webhook URL:
   ```
   https://yourdomain.com/webhook/whatsapp
   ```
3. Enter Verify Token (must match WEBHOOK_VERIFY_TOKEN in .env)
4. Click "Verify and Save"

5. Subscribe to webhook fields:
   - messages
   - message_status
   - message_template_status_update

### 6. Test the Setup

Send a test message:
```bash
curl -X POST "https://graph.facebook.com/v17.0/${WHATSAPP_PHONE_NUMBER_ID}/messages" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "1234567890",
    "type": "text",
    "text": {"body": "Hello from MemoApp!"}
  }'
```

## Server Configuration

### 1. System Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash memoapp

# Create directories
sudo mkdir -p /opt/memoapp
sudo mkdir -p /var/log/memoapp
sudo mkdir -p /opt/memoapp/data/contacts
sudo mkdir -p /opt/memoapp/backups

# Set permissions
sudo chown -R memoapp:memoapp /opt/memoapp
sudo chown -R memoapp:memoapp /var/log/memoapp
```

### 2. Systemd Service

Create `/etc/systemd/system/memoapp.service`:
```ini
[Unit]
Description=MemoApp WhatsApp Bot
After=network.target redis.service

[Service]
Type=simple
User=memoapp
Group=memoapp
WorkingDirectory=/opt/memoapp
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/memoapp/.env
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:/var/log/memoapp/app.log
StandardError=append:/var/log/memoapp/error.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable memoapp
sudo systemctl start memoapp
sudo systemctl status memoapp
```

## Application Deployment

### 1. Clone Repository

```bash
sudo -u memoapp git clone https://github.com/your-repo/memoapp.git /opt/memoapp
cd /opt/memoapp
```

### 2. Install Dependencies

```bash
sudo -u memoapp python3 -m venv venv
sudo -u memoapp venv/bin/pip install --upgrade pip
sudo -u memoapp venv/bin/pip install -r requirements.txt
```

### 3. Initialize Data Structure

```bash
# Create required directories
sudo -u memoapp mkdir -p data/contacts data/audit data/tenants
sudo -u memoapp mkdir -p app/memory-system/users
sudo -u memoapp mkdir -p backups

# Set up encryption keys
sudo -u memoapp python3 -c "
from cryptography.fernet import Fernet
import os
os.makedirs('data/.keys', exist_ok=True)
with open('data/.keys/master.key', 'wb') as f:
    f.write(Fernet.generate_key())
"

# Secure the keys
sudo chmod 600 /opt/memoapp/data/.keys/master.key
sudo chmod 700 /opt/memoapp/data/.keys
```

### 4. Database Setup (if using PostgreSQL)

```bash
# Create database
sudo -u postgres createdb memoapp
sudo -u postgres createuser memoapp_user

# Set password
sudo -u postgres psql -c "ALTER USER memoapp_user PASSWORD 'secure_password';"

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE memoapp TO memoapp_user;"

# Run migrations (if any)
cd /opt/memoapp
sudo -u memoapp venv/bin/python manage.py migrate
```

## SSL/HTTPS Configuration

### 1. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/memoapp`:
```nginx
upstream memoapp {
    server 127.0.0.1:5000 fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;
    keepalive_timeout 5;

    location / {
        proxy_pass http://memoapp;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_buffering off;
    }

    location /webhook/whatsapp {
        proxy_pass http://memoapp/webhook/whatsapp;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /metrics {
        proxy_pass http://memoapp/metrics;
        allow 10.0.0.0/8;  # Internal monitoring
        deny all;
    }

    access_log /var/log/nginx/memoapp_access.log;
    error_log /var/log/nginx/memoapp_error.log;
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/memoapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2. SSL Certificate with Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal (add to crontab)
0 3 * * * /usr/bin/certbot renew --quiet
```

## Monitoring Setup

### 1. Prometheus Configuration

Create `/etc/prometheus/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'memoapp'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

### 2. Grafana Dashboard

Import dashboard JSON:
```json
{
  "dashboard": {
    "title": "MemoApp WhatsApp Bot",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(errors_total[5m])"
          }
        ]
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, response_time_seconds)"
          }
        ]
      },
      {
        "title": "Active Sessions",
        "targets": [
          {
            "expr": "gauge:active_sessions"
          }
        ]
      }
    ]
  }
}
```

### 3. Log Aggregation

Configure rsyslog to forward logs:
```bash
# /etc/rsyslog.d/50-memoapp.conf
module(load="imfile")

input(type="imfile"
      File="/var/log/memoapp/app.log"
      Tag="memoapp"
      StateFile="memoapp-state"
      Severity="info"
      Facility="local0")

*.* @@logserver.example.com:514
```

## Backup Procedures

### 1. Automated Daily Backups

Create `/opt/memoapp/scripts/backup.sh`:
```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/memoapp/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz"

# Create backup
cd /opt/memoapp
tar -czf "${BACKUP_FILE}" \
  --exclude='backups' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  data/ app/memory-system/

# Keep only last 30 days
find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +30 -delete

# Upload to S3 (optional)
# aws s3 cp "${BACKUP_FILE}" s3://your-bucket/memoapp-backups/

echo "Backup completed: ${BACKUP_FILE}"
```

Add to crontab:
```bash
0 2 * * * /opt/memoapp/scripts/backup.sh >> /var/log/memoapp/backup.log 2>&1
```

### 2. Redis Backup

```bash
# Configure Redis persistence
echo "save 900 1" >> /etc/redis/redis.conf
echo "save 300 10" >> /etc/redis/redis.conf
echo "save 60 10000" >> /etc/redis/redis.conf
echo "appendonly yes" >> /etc/redis/redis.conf

sudo systemctl restart redis
```

### 3. Database Backup (if using)

```bash
#!/bin/bash
# /opt/memoapp/scripts/db_backup.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump memoapp > "/opt/memoapp/backups/db_${TIMESTAMP}.sql"
gzip "/opt/memoapp/backups/db_${TIMESTAMP}.sql"
```

## Rollback Procedures

### 1. Quick Rollback (Application)

```bash
#!/bin/bash
# /opt/memoapp/scripts/rollback.sh

if [ -z "$1" ]; then
    echo "Usage: ./rollback.sh <version>"
    exit 1
fi

VERSION=$1

# Stop service
sudo systemctl stop memoapp

# Checkout previous version
cd /opt/memoapp
git fetch --tags
git checkout "v${VERSION}"

# Reinstall dependencies if needed
venv/bin/pip install -r requirements.txt

# Start service
sudo systemctl start memoapp

# Verify
sleep 5
curl -f http://localhost:5000/health || exit 1
echo "Rollback to v${VERSION} complete"
```

### 2. Data Rollback

```bash
#!/bin/bash
# /opt/memoapp/scripts/restore_data.sh

if [ -z "$1" ]; then
    echo "Usage: ./restore_data.sh <backup_file>"
    exit 1
fi

BACKUP_FILE=$1

# Stop service
sudo systemctl stop memoapp

# Backup current data
mv /opt/memoapp/data /opt/memoapp/data.rollback

# Restore from backup
cd /opt/memoapp
tar -xzf "${BACKUP_FILE}"

# Start service
sudo systemctl start memoapp

echo "Data restored from ${BACKUP_FILE}"
```

### 3. Database Rollback

```bash
#!/bin/bash
# Restore database from backup

BACKUP_FILE=$1

# Stop application
sudo systemctl stop memoapp

# Restore database
gunzip < "${BACKUP_FILE}" | psql memoapp

# Start application
sudo systemctl start memoapp
```

## Production Checklist

- [ ] Domain configured with SSL certificate
- [ ] WhatsApp webhook verified and subscribed
- [ ] Environment variables set in .env file
- [ ] Redis configured with persistence
- [ ] Firewall rules configured (ports 80, 443 open)
- [ ] Monitoring configured (Prometheus/Grafana)
- [ ] Backup scripts scheduled in cron
- [ ] Log rotation configured
- [ ] Health checks passing
- [ ] Test message sent and received successfully

## Troubleshooting

### Webhook Not Receiving Messages
```bash
# Check webhook status
curl -X GET "https://graph.facebook.com/v17.0/${WHATSAPP_PHONE_NUMBER_ID}/subscribed_apps" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}"

# Re-verify webhook
curl "https://yourdomain.com/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=${WEBHOOK_VERIFY_TOKEN}&hub.challenge=test"
```

### Service Won't Start
```bash
# Check logs
sudo journalctl -u memoapp -n 100

# Test configuration
cd /opt/memoapp
venv/bin/python -c "from app.main import app; print('OK')"

# Check permissions
ls -la /opt/memoapp/data/
ls -la /var/log/memoapp/
```

### High Memory Usage
```bash
# Restart service
sudo systemctl restart memoapp

# Clear Redis cache
redis-cli FLUSHDB

# Check for memory leaks
sudo -u memoapp venv/bin/python -m memory_profiler app/main.py
```

## Support

For issues or questions:
- Check logs: `/var/log/memoapp/app.log`
- Monitor metrics: `https://yourdomain.com/metrics`
- Review Meta webhook dashboard: https://developers.facebook.com/apps/YOUR_APP_ID/webhooks/
- Contact: support@memoapp.com