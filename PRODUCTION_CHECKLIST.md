# MemoApp Memory Bot - Production Checklist

## 📋 Pre-Deployment Checklist

### ✅ Required Environment Variables

Configure the following environment variables before deployment:

#### **Core Configuration**
```bash
# Application Settings
PORT=5000                           # Application port (required: 5000)
PRODUCTION=true                     # Enable production mode
LOG_LEVEL=INFO                      # Logging level (DEBUG|INFO|WARNING|ERROR)

# Database
DATABASE_URL=postgresql://...       # PostgreSQL connection string (required)
```

#### **WhatsApp Integration**
```bash
# WhatsApp Cloud API
WHATSAPP_ACCESS_TOKEN=              # Meta Business API access token (required)
WHATSAPP_PHONE_NUMBER_ID=           # WhatsApp Business phone number ID (required)
WEBHOOK_VERIFY_TOKEN=               # Webhook verification token (required)
WEBHOOK_SECRET=                     # Webhook signature secret (recommended)
```

#### **Voice Services**
```bash
# Azure Speech Services
AZURE_SPEECH_KEY=                   # Azure Speech API key (required)
AZURE_SPEECH_REGION=                # Azure region (e.g., eastus) (required)

# OpenAI API
OPENAI_API_KEY=                     # OpenAI API key for AI features (required)
```

#### **Security Configuration**
```bash
# Encryption & Security
ENCRYPTION_KEY=                     # 32-byte hex key for data encryption
JWT_SECRET=                         # JWT signing secret for sessions
SESSION_TIMEOUT_MINUTES=30          # Session timeout duration
MAX_LOGIN_ATTEMPTS=5                # Maximum login attempts before lockout
```

#### **Business Features (Optional)**
```bash
# Stripe Payment Processing
STRIPE_API_KEY=                     # Stripe API key for payments
STRIPE_WEBHOOK_SECRET=              # Stripe webhook endpoint secret

# Email Notifications
SMTP_HOST=                          # SMTP server hostname
SMTP_PORT=587                       # SMTP server port
SMTP_USER=                          # SMTP username
SMTP_PASSWORD=                      # SMTP password
```

---

## 🛡️ Security Hardening Steps

### 1. **Network Security**
- [ ] Configure firewall to only allow port 5000
- [ ] Set up HTTPS/TLS termination (nginx/caddy)
- [ ] Implement rate limiting (10 requests/second per IP)
- [ ] Configure CORS appropriately

### 2. **Application Security**
- [ ] Generate strong encryption keys:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] Enable audit logging for all sensitive operations
- [ ] Configure secure session management
- [ ] Implement request signature validation

### 3. **Database Security**
- [ ] Use connection pooling with SSL
- [ ] Create read-only database user for reporting
- [ ] Enable query logging for auditing
- [ ] Regular automated backups

### 4. **File System Security**
- [ ] Set restrictive file permissions:
  ```bash
  chmod 600 memory-system/security/*
  chmod 700 scripts/*.sh
  ```
- [ ] Encrypt sensitive data at rest
- [ ] Configure log rotation

---

## 💾 Backup Procedures

### Automated Backups
Run the backup script regularly via cron:
```bash
# Add to crontab (daily at 2 AM)
0 2 * * * /path/to/app/scripts/backup.sh
```

### Manual Backup
```bash
bash scripts/backup.sh
```

### Backup Contents
- Memory system data (`memory-system/`)
- Audit logs (`data/audit/`)
- Tenant configurations (`data/tenants/`)
- PostgreSQL database dump

### Restore Procedure
```bash
# 1. Stop the application
kill $(cat /tmp/echovault.pid)

# 2. Extract backup
cd /tmp/echovault_backups
tar -xzf echovault_backup_[timestamp].tar.gz

# 3. Restore data
cp -r echovault_backup_[timestamp]/memory_data/* /path/to/app/memory-system/

# 4. Restore database
gunzip -c echovault_backup_[timestamp]/database.sql.gz | psql $DATABASE_URL

# 5. Restart application
bash scripts/deploy.sh
```

---

## 📊 Monitoring Recommendations

### 1. **Health Monitoring**
Set up monitoring for these endpoints:
- `GET /` - Main health check
- `GET /metrics` - Prometheus metrics
- `GET /webhook` - WhatsApp webhook status

### 2. **Metrics to Track**
- **Application Metrics**
  - Request rate and response times
  - Error rate (4xx, 5xx responses)
  - Active sessions count
  - Memory storage growth

- **System Metrics**
  - CPU usage (alert if >80%)
  - Memory usage (alert if >90%)
  - Disk space (alert if >85%)
  - Database connections

### 3. **Log Monitoring**
Configure log aggregation for:
- Application logs (`logs/app.log`)
- Audit logs (`data/audit/*.jsonl`)
- Error logs (filter by ERROR level)

### 4. **Alerting Rules**
Set up alerts for:
- [ ] Application down/unresponsive
- [ ] Database connection failures
- [ ] High error rate (>5% of requests)
- [ ] Disk space low (<15% free)
- [ ] Suspicious security events

---

## 🚀 Deployment Instructions

### Initial Deployment

1. **Clone the repository**
   ```bash
   git clone [repository-url]
   cd echovault-memory-bot
   ```

2. **Set environment variables**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your values
   source .env
   ```

3. **Run deployment script**
   ```bash
   bash scripts/deploy.sh
   ```

### Update Deployment

1. **Create backup**
   ```bash
   bash scripts/backup.sh
   ```

2. **Pull latest changes**
   ```bash
   git pull origin main
   ```

3. **Deploy update**
   ```bash
   bash scripts/deploy.sh
   ```

### Rollback Procedure

1. **Stop current version**
   ```bash
   kill $(cat /tmp/echovault.pid)
   ```

2. **Restore from backup**
   ```bash
   bash scripts/rollback.sh [backup-timestamp]
   ```

3. **Or checkout previous version**
   ```bash
   git checkout [previous-version-tag]
   bash scripts/deploy.sh
   ```

---

## ✅ Production Readiness Checklist

### Before Going Live
- [ ] All environment variables configured
- [ ] Database migrations completed
- [ ] SSL/TLS configured
- [ ] Firewall rules in place
- [ ] Backup automation configured
- [ ] Monitoring and alerting set up
- [ ] Load testing completed
- [ ] Security scan performed
- [ ] Documentation reviewed

### Post-Deployment
- [ ] Verify all endpoints responding
- [ ] Test WhatsApp integration
- [ ] Confirm audit logging working
- [ ] Check backup creation
- [ ] Monitor error logs
- [ ] Verify session management
- [ ] Test voice authentication
- [ ] Confirm tenant isolation

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks
- **Daily**: Check error logs and metrics
- **Weekly**: Review audit logs for anomalies
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Performance review and optimization

### Troubleshooting

#### Application won't start
```bash
# Check logs
tail -f logs/app.log

# Verify environment variables
env | grep WHATSAPP

# Test database connection
python3 -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"
```

#### High memory usage
```bash
# Check memory usage
ps aux | grep python

# Restart application
bash scripts/restart.sh
```

#### WhatsApp webhook failing
```bash
# Test webhook verification
curl "http://localhost:5000/webhook?hub.mode=subscribe&hub.verify_token=$WEBHOOK_VERIFY_TOKEN&hub.challenge=test"

# Check webhook logs
grep webhook logs/app.log
```

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-10 | Initial production release |

---

## 📄 License & Compliance

- Ensure compliance with WhatsApp Business API terms
- Follow data protection regulations (GDPR, CCPA)
- Maintain audit logs for compliance reporting
- Regular security assessments

---

**Last Updated**: January 10, 2024  
**Status**: Production Ready ✅