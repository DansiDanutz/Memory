# MemoApp WhatsApp Bot - Release Checklist

## Pre-Release Verification

### Environment Variables
- [ ] **WHATSAPP_ACCESS_TOKEN** - Verify valid Meta access token
- [ ] **WHATSAPP_PHONE_NUMBER_ID** - Confirm correct phone number ID
- [ ] **WEBHOOK_VERIFY_TOKEN** - Set unique verification token
- [ ] **AZURE_SPEECH_KEY** - Validate Azure STT/TTS API key
- [ ] **AZURE_SPEECH_REGION** - Confirm correct Azure region (e.g., eastus)
- [ ] **REDIS_URL** - Test Redis connection (default: redis://localhost:6379)
- [ ] **OPENAI_API_KEY** - Verify OpenAI API key for classification
- [ ] **DEFAULT_TENANT_ID** - Set default tenant (default: memoapp)
- [ ] **DEFAULT_DEPARTMENT_ID** - Set default department (default: general)

### API Key Validation
```bash
# Test WhatsApp API
curl -X GET "https://graph.facebook.com/v17.0/${WHATSAPP_PHONE_NUMBER_ID}" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}"

# Test Azure Speech
curl -X POST "https://${AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1" \
  -H "Ocp-Apim-Subscription-Key: ${AZURE_SPEECH_KEY}" \
  -H "Content-Type: application/ssml+xml" \
  -H "X-Microsoft-OutputFormat: audio-16khz-128kbitrate-mono-mp3" \
  --data-raw '<speak version="1.0" xml:lang="en-US"><voice name="en-US-JennyNeural">Test</voice></speak>'

# Test Redis
redis-cli -u "${REDIS_URL}" ping

# Test OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer ${OPENAI_API_KEY}"
```

### WhatsApp Webhook Configuration
- [ ] Webhook URL configured: `https://YOUR_DOMAIN/webhook/whatsapp`
- [ ] Webhook verified with correct token
- [ ] Webhook subscriptions enabled for:
  - [ ] messages
  - [ ] message_status
  - [ ] message_template_status_update
- [ ] Webhook callback URL is HTTPS with valid SSL certificate

### Infrastructure Checks
- [ ] Redis server running and accessible
- [ ] PostgreSQL database initialized (if using database features)
- [ ] Data directories created:
  ```bash
  mkdir -p data/contacts data/audit data/tenants
  mkdir -p app/memory-system/users
  mkdir -p backups
  ```
- [ ] Permissions set correctly:
  ```bash
  chmod 755 scripts/dev_run.sh
  chmod 700 data/contacts  # Sensitive data
  ```

## Pre-Deployment Testing

### Health Checks
```bash
# Test health endpoint
curl http://localhost:5000/health

# Test metrics endpoint
curl http://localhost:5000/metrics

# Test admin status
curl http://localhost:5000/admin/status

# Test webhook verification
curl "http://localhost:5000/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=${WEBHOOK_VERIFY_TOKEN}&hub.challenge=test"
```

### Smoke Tests

#### 1. Basic Message Flow
```bash
# Send test message via API
curl -X POST http://localhost:5000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "1234567890",
            "type": "text",
            "text": {"body": "/help"}
          }]
        }
      }]
    }]
  }'
```

#### 2. Voice Message Test
- [ ] Send voice note to bot
- [ ] Verify transcription occurs
- [ ] Check memory storage in correct category
- [ ] Confirm audio response sent back

#### 3. Command Tests
Test each command manually:
- [ ] `/help` - Shows command list
- [ ] `/search test` - Searches memories
- [ ] `/recent 5` - Shows recent memories
- [ ] `/stats` - Displays statistics
- [ ] `/category GENERAL` - Lists category
- [ ] `/voice` - Shows enrollment guide
- [ ] `/login` - Authentication prompt
- [ ] `/logout` - Ends session
- [ ] `/profile` - Shows user profile
- [ ] `/whoami` - Shows tenant/role
- [ ] `/settings` - Views settings
- [ ] `/clear` - Clears session
- [ ] `/export` - Exports memories
- [ ] `/backup` - Creates backup
- [ ] `/restore` - Shows restore options
- [ ] `/delete <id>` - Deletes memory
- [ ] `/audit` - Admin audit logs

#### 4. Security Tests
- [ ] Verify SECRET/ULTRA_SECRET categories require authentication
- [ ] Test passphrase enrollment: `enroll: my test passphrase is unique`
- [ ] Test passphrase verification: `verify: my test passphrase is unique`
- [ ] Confirm 10-minute session timeout works
- [ ] Check encryption for sensitive categories

## Deployment Process

### 1. Code Preparation
```bash
# Clean test artifacts
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete
find . -type f -name ".DS_Store" -delete
rm -rf test_results/
rm -rf attached_assets/__MACOSX/

# Verify requirements
pip install -r requirements.txt --dry-run

# Run tests
pytest tests/ -v

# Check for hardcoded secrets
grep -r "sk-" . --exclude-dir=.git --exclude-dir=venv
grep -r "Bearer " . --exclude-dir=.git --exclude-dir=venv
```

### 2. Docker Build (if containerized)
```bash
# Build image
docker build -t memoapp-whatsapp:latest .

# Test container locally
docker run -p 5000:5000 \
  --env-file .env \
  memoapp-whatsapp:latest

# Tag for registry
docker tag memoapp-whatsapp:latest registry.example.com/memoapp-whatsapp:v1.0.0
```

### 3. Deploy to Production
```bash
# For Replit
git add .
git commit -m "Release v1.0.0"
git push origin main

# For standard deployment
rsync -avz --exclude='.git' --exclude='venv' . user@server:/opt/memoapp/
ssh user@server "cd /opt/memoapp && pip install -r requirements.txt"
ssh user@server "systemctl restart memoapp"
```

## Post-Deployment Verification

### 1. Service Health
- [ ] Application running: `systemctl status memoapp`
- [ ] Logs showing no errors: `tail -f /var/log/memoapp/app.log`
- [ ] CPU/Memory usage normal: Check `/admin/status`
- [ ] Redis connections active: `redis-cli CLIENT LIST`

### 2. Webhook Verification
- [ ] Send test message from real WhatsApp number
- [ ] Verify webhook receives and processes message
- [ ] Check response delivered to sender
- [ ] Monitor webhook latency in Meta dashboard

### 3. Monitoring Setup
- [ ] Prometheus scraping `/metrics` endpoint
- [ ] Grafana dashboards showing:
  - [ ] Request rate
  - [ ] Response times
  - [ ] Error rate
  - [ ] Memory usage by category
  - [ ] Active sessions
- [ ] Alerts configured for:
  - [ ] High error rate (>1%)
  - [ ] Slow response time (>2s)
  - [ ] Redis connection failures
  - [ ] Disk space usage (>80%)

### 4. Backup Verification
- [ ] Automated backups running
- [ ] Test restore procedure with sample data
- [ ] Verify data integrity after restore

## Rollback Plan

### Quick Rollback (< 5 minutes)
```bash
# Revert to previous version
git checkout v0.9.0
systemctl restart memoapp

# Or with Docker
docker stop memoapp
docker run -d --name memoapp \
  --env-file .env \
  -p 5000:5000 \
  registry.example.com/memoapp-whatsapp:v0.9.0
```

### Data Rollback
```bash
# Restore from backup
cd /opt/memoapp
tar -xzf backups/backup_20250115_120000.tar.gz
systemctl restart memoapp
```

## Sign-off

- [ ] **Product Owner**: Features working as expected
- [ ] **Security**: No vulnerabilities found
- [ ] **Operations**: Monitoring and alerts configured
- [ ] **QA**: All tests passed
- [ ] **Release Manager**: Approved for production

**Release Version**: _______________
**Release Date**: _______________
**Released By**: _______________
**Rollback Point**: _______________

## Notes
- Always deploy during low-traffic hours
- Keep Meta webhook dashboard open during deployment
- Have rollback script ready before starting
- Notify on-call team before and after deployment
- Update status page if customer-facing