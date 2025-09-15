# 🚀 Memory App Production Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Security Hardening](#security-hardening)
5. [Database Setup](#database-setup)
6. [Deployment Process](#deployment-process)
7. [Health Monitoring](#health-monitoring)
8. [Performance Optimization](#performance-optimization)
9. [Backup and Recovery](#backup-and-recovery)
10. [Maintenance](#maintenance)
11. [Troubleshooting](#troubleshooting)
12. [Security Checklist](#security-checklist)

---

## Overview

The Memory App Platform is a comprehensive digital immortality system that requires careful production deployment with proper security, performance, and reliability measures. This guide provides step-by-step instructions for deploying the platform in a production environment.

### Architecture Components
- **Backend Services**: Python/Flask webhook server, memory processing system
- **Frontend**: Node.js web interface
- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis for session management and caching
- **External Services**: OpenAI, Anthropic, Stripe, Twilio, WhatsApp, Telegram
- **Monitoring**: Prometheus metrics, health checks, logging

---

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **CPU**: Minimum 4 cores, recommended 8 cores
- **RAM**: Minimum 8GB, recommended 16GB
- **Storage**: Minimum 50GB SSD, recommended 100GB+
- **Network**: Static IP, open ports 80, 443, 5000, 8080

### Software Requirements
```bash
# Required software versions
- Python 3.9+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- Nginx 1.18+
- Git 2.25+
```

### Access Requirements
- Root or sudo access for system configuration
- Domain name with DNS control
- SSL certificates (Let's Encrypt recommended)
- API keys for all external services

---

## Environment Configuration

### 1. Create Production Environment File

Copy the production template and configure all values:

```bash
cd memory-system
cp .env.production .env
nano .env
```

### 2. Required Environment Variables

#### Core Configuration
```bash
# Application
NODE_ENV=production
ENVIRONMENT=production
APP_NAME="Memory App Platform"
APP_VERSION=1.0.0
APP_URL=https://your-domain.com
API_URL=https://api.your-domain.com

# Security (Generate strong random values)
JWT_SECRET=$(openssl rand -base64 64)
ADMIN_JWT_SECRET=$(openssl rand -base64 64)
MEMORY_MASTER_SECRET=$(openssl rand -base64 32)
SESSION_SECRET=$(openssl rand -base64 32)
```

#### Database Configuration
```bash
# PostgreSQL
DATABASE_URL=postgresql://username:password@host:5432/memory_app?sslmode=require
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10
DATABASE_SSL=true

# Redis
REDIS_URL=redis://username:password@host:6379
REDIS_TLS=true
```

#### External Services
```bash
# OpenAI (Primary AI)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-5

# Anthropic (Fallback AI)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Stripe (Payments)
STRIPE_SECRET_KEY=sk_live_your-stripe-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# Twilio (Voice/SMS)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# WhatsApp
WHATSAPP_ACCESS_TOKEN=your-whatsapp-token
WHATSAPP_WEBHOOK_SECRET=your-webhook-secret

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
```

### 3. Validate Configuration

Run the configuration validator:

```bash
python3 production_secure_config.py
```

---

## Security Hardening

### 1. System Security

#### Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install fail2ban ufw
```

#### Configure Firewall
```bash
# Allow SSH (change port if needed)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application ports (internal only)
sudo ufw allow from 10.0.0.0/8 to any port 5000
sudo ufw allow from 10.0.0.0/8 to any port 8080

# Enable firewall
sudo ufw enable
```

#### Configure Fail2ban
```bash
sudo nano /etc/fail2ban/jail.local
```

Add configuration:
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
```

### 2. Application Security

#### Enable Security Middleware
```python
# In webhook_server_complete.py
from security_middleware import SecurityMiddleware

# Initialize security
security = SecurityMiddleware(app, config={
    'max_request_size': 10485760,  # 10MB
    'rate_limit_window_ms': 60000,
    'rate_limit_max_requests': 100,
    'environment': 'production'
})
```

#### Configure CORS
```python
CORS(app, origins=[
    'https://your-domain.com',
    'https://app.your-domain.com'
], supports_credentials=True)
```

#### Input Validation
All endpoints use the validation decorators from `security_middleware.py`:
```python
@validate_input({
    'email': {'required': True, 'type': str, 'pattern': r'^[\w\.-]+@[\w\.-]+\.\w+$'},
    'password': {'required': True, 'type': str, 'min_length': 8}
})
def login():
    pass
```

### 3. SSL/TLS Configuration

#### Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx
```

#### Generate SSL Certificate
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

#### Configure Nginx SSL
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
}
```

---

## Database Setup

### 1. Install PostgreSQL
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl enable postgresql
```

### 2. Create Database and User
```bash
sudo -u postgres psql

CREATE USER memory_app WITH PASSWORD 'secure_password';
CREATE DATABASE memory_app OWNER memory_app;
GRANT ALL PRIVILEGES ON DATABASE memory_app TO memory_app;

-- Enable required extensions
\c memory_app
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
\q
```

### 3. Configure PostgreSQL for Production
```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```

Key settings:
```conf
# Connection Settings
max_connections = 200
shared_buffers = 256MB

# Performance
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Logging
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000  # Log slow queries > 1s

# SSL
ssl = on
```

### 4. Initialize Database Schema
```bash
cd memory-system
source venv/bin/activate
python3 << EOF
from postgres_db_client import initialize_schema
initialize_schema()
print("Database schema initialized successfully")
EOF
```

---

## Deployment Process

### 1. Clone Repository
```bash
cd /opt
git clone https://github.com/your-org/memory-app.git
cd memory-app
```

### 2. Run Deployment Script
```bash
chmod +x memory-system/deploy_production.sh
./memory-system/deploy_production.sh deploy
```

The script will:
1. Run pre-deployment checks
2. Create backup of current deployment
3. Install dependencies
4. Run database migrations
5. Configure services
6. Start all services
7. Run health checks
8. Perform post-deployment tasks

### 3. Manual Deployment Steps

If preferring manual deployment:

#### Install Python Dependencies
```bash
cd memory-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Install Node Dependencies
```bash
cd ../web-interface
npm ci --production
npm run build
```

#### Start Services
```bash
sudo systemctl start memory-app
sudo systemctl start webhook-server
sudo systemctl start web-interface
sudo systemctl enable memory-app webhook-server web-interface
```

---

## Health Monitoring

### 1. Health Check Endpoints

The platform provides multiple health check endpoints:

- **Main Health**: `GET /health` - Comprehensive health status
- **Liveness**: `GET /health/live` - Service is alive
- **Readiness**: `GET /health/ready` - Ready for traffic
- **Startup**: `GET /health/startup` - Startup complete
- **Metrics**: `GET /metrics` - Prometheus metrics

### 2. Monitoring Setup

#### Prometheus Configuration
```yaml
# /etc/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'memory-app'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

#### Health Check Script
```bash
#!/bin/bash
# /opt/scripts/health_check.sh

response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
if [ $response -eq 200 ]; then
    echo "Health check passed"
    exit 0
else
    echo "Health check failed with status: $response"
    # Send alert
    curl -X POST $ALERT_WEBHOOK_URL -d '{"text":"Memory App health check failed"}'
    exit 1
fi
```

#### Cron Job for Monitoring
```bash
# Add to crontab
*/5 * * * * /opt/scripts/health_check.sh
```

### 3. Logging Configuration

#### Application Logs
```bash
# Create log directory
sudo mkdir -p /var/log/memory-app
sudo chown $USER:$USER /var/log/memory-app

# Configure log rotation
sudo nano /etc/logrotate.d/memory-app
```

```conf
/var/log/memory-app/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    sharedscripts
    postrotate
        systemctl reload memory-app webhook-server web-interface
    endscript
}
```

---

## Performance Optimization

### 1. Enable Caching

The platform uses multi-layer caching:

```python
# Redis caching is automatically enabled if REDIS_URL is set
# Memory caching is used as fallback

from performance_optimization import cache_manager

# Cache usage example
@cache(key_prefix='user_memories', ttl=3600)
def get_user_memories(user_id):
    # Expensive database query
    pass
```

### 2. Database Optimization

#### Create Indexes
```sql
-- Performance indexes
CREATE INDEX idx_memories_user_timestamp ON memories(user_id, timestamp DESC);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_search ON memories USING gin(to_tsvector('english', content));

-- Analyze tables
ANALYZE memories;
ANALYZE users;
```

### 3. Enable Compression

Compression is automatically enabled via middleware:
- Brotli for modern browsers
- Gzip as fallback
- Static files served compressed

### 4. Configure CDN (Optional)

For static assets:
```nginx
location /static {
    alias /opt/memory-app/web-interface/public;
    expires 30d;
    add_header Cache-Control "public, immutable";
    
    # CDN headers
    add_header Access-Control-Allow-Origin "https://cdn.your-domain.com";
}
```

---

## Backup and Recovery

### 1. Automated Backups

#### Database Backup Script
```bash
#!/bin/bash
# /opt/scripts/backup.sh

BACKUP_DIR="/opt/backups/memory-app"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz

# Backup files
tar -czf $BACKUP_DIR/files_$TIMESTAMP.tar.gz /opt/memory-app

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/db_$TIMESTAMP.sql.gz s3://your-backup-bucket/
aws s3 cp $BACKUP_DIR/files_$TIMESTAMP.tar.gz s3://your-backup-bucket/

# Clean old backups (keep 30 days)
find $BACKUP_DIR -type f -mtime +30 -delete
```

#### Schedule Backups
```bash
# Add to crontab
0 3 * * * /opt/scripts/backup.sh
```

### 2. Recovery Procedures

#### Database Recovery
```bash
# Stop services
sudo systemctl stop memory-app webhook-server

# Restore database
gunzip -c /opt/backups/memory-app/db_20250913_030000.sql.gz | psql $DATABASE_URL

# Restart services
sudo systemctl start memory-app webhook-server
```

#### Full System Recovery
```bash
# Use deployment script rollback
./memory-system/deploy_production.sh rollback
```

---

## Maintenance

### 1. Regular Maintenance Tasks

#### Weekly
- Review error logs
- Check disk space
- Verify backup integrity
- Update security patches

#### Monthly
- Analyze database performance
- Review security alerts
- Update dependencies
- Performance tuning

#### Quarterly
- Security audit
- Disaster recovery test
- Capacity planning
- Documentation review

### 2. Update Procedures

#### Application Updates
```bash
# Create backup first
./memory-system/deploy_production.sh backup

# Deploy update
git pull origin main
./memory-system/deploy_production.sh deploy
```

#### Security Updates
```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Python dependencies
cd memory-system
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Node dependencies
cd ../web-interface
npm audit fix
npm update
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Service Won't Start
```bash
# Check logs
journalctl -u memory-app -n 50
tail -f /var/log/memory-app/memory-app-error.log

# Verify environment
python3 production_secure_config.py

# Check permissions
ls -la /opt/memory-app
```

#### 2. Database Connection Issues
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check PostgreSQL status
sudo systemctl status postgresql

# Review connection pool
netstat -an | grep 5432
```

#### 3. High Memory Usage
```bash
# Check memory
free -h
ps aux --sort=-%mem | head

# Clear caches
redis-cli FLUSHDB

# Restart services
sudo systemctl restart memory-app webhook-server
```

#### 4. Slow Performance
```bash
# Check CPU usage
top -b -n 1

# Analyze slow queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10"

# Check disk I/O
iostat -x 1
```

---

## Security Checklist

### Pre-Deployment
- [ ] All environment variables configured
- [ ] Strong passwords generated
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] Fail2ban enabled
- [ ] Security headers configured
- [ ] Input validation enabled
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Admin access restricted

### Post-Deployment
- [ ] Health checks passing
- [ ] Monitoring active
- [ ] Backups scheduled
- [ ] Logs rotating
- [ ] Alerts configured
- [ ] Documentation updated
- [ ] Team trained
- [ ] Incident response plan ready
- [ ] Recovery procedures tested
- [ ] Security scan completed

### Ongoing
- [ ] Regular security updates
- [ ] Log review
- [ ] Access audit
- [ ] Dependency updates
- [ ] Performance monitoring
- [ ] Backup verification
- [ ] Security training
- [ ] Penetration testing (quarterly)
- [ ] Compliance review
- [ ] Documentation updates

---

## Support and Resources

### Documentation
- API Documentation: `/docs/api`
- Architecture Guide: `/docs/architecture`
- Security Guide: `/docs/security`

### Monitoring Dashboards
- Health Status: `https://your-domain.com/health`
- Metrics: `https://your-domain.com/metrics`
- Admin Dashboard: `https://your-domain.com/admin`

### Support Channels
- Emergency: On-call rotation
- Issues: GitHub Issues
- Questions: Team Slack
- Security: security@your-domain.com

### External Resources
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Flask Security Guide](https://flask.palletsprojects.com/en/2.3.x/security/)
- [OWASP Security Checklist](https://owasp.org/www-project-web-security-testing-guide/)

---

## Appendix

### A. Environment Variable Reference

See `.env.production` for complete list with descriptions.

### B. Service Dependencies

```yaml
Dependencies:
  memory-app:
    - postgresql
    - redis (optional)
    
  webhook-server:
    - memory-app
    - postgresql
    
  web-interface:
    - webhook-server
    - nginx
```

### C. Port Reference

| Service | Port | Access |
|---------|------|--------|
| Web Interface | 5000 | Internal |
| Webhook Server | 8080 | Internal |
| PostgreSQL | 5432 | Internal |
| Redis | 6379 | Internal |
| Nginx HTTP | 80 | Public |
| Nginx HTTPS | 443 | Public |

### D. File Structure

```
/opt/memory-app/
├── memory-system/
│   ├── .env
│   ├── venv/
│   ├── *.py
│   └── logs/
├── web-interface/
│   ├── node_modules/
│   ├── public/
│   └── server.js
└── backups/
```

---

**Last Updated**: September 2025
**Version**: 1.0.0
**Author**: Memory App DevOps Team