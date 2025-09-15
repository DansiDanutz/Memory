# MemoApp WhatsApp Bot - On-Call Playbook

## Emergency Contacts
- **Primary On-Call**: [Phone/Slack]
- **Secondary On-Call**: [Phone/Slack]
- **Engineering Lead**: [Phone/Slack]
- **Meta Support**: https://developers.facebook.com/support/
- **Azure Support**: https://azure.microsoft.com/support/

## Quick Health Checks

```bash
# Service status
curl -s http://localhost:5000/health | jq .

# Metrics check
curl -s http://localhost:5000/metrics | grep -E "whatsapp_messages_total|errors_total"

# Redis health
redis-cli ping

# Recent logs
tail -100 /var/log/memoapp/app.log | grep ERROR

# Webhook status in Meta Dashboard
# https://developers.facebook.com/apps/YOUR_APP_ID/webhooks/
```

## Common Issues and Solutions

### 1. Webhook Not Receiving Messages

**Symptoms:**
- No incoming messages in logs
- WhatsApp messages not triggering bot responses
- `/webhook/whatsapp` endpoint not being called

**Diagnosis:**
```bash
# Check webhook registration
curl -X GET "https://graph.facebook.com/v17.0/${WHATSAPP_PHONE_NUMBER_ID}/subscribed_apps" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}"

# Test webhook manually
curl -X POST http://localhost:5000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"test","type":"text","text":{"body":"test"}}]}}]}]}'

# Check SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

**Solutions:**
1. Re-verify webhook in Meta dashboard:
   ```bash
   curl "https://yourdomain.com/webhook/whatsapp?hub.mode=subscribe&hub.verify_token=${WEBHOOK_VERIFY_TOKEN}&hub.challenge=test"
   ```
2. Check SSL certificate is valid and not expired
3. Ensure firewall allows incoming HTTPS traffic
4. Verify webhook URL is exact (no trailing slash)
5. Re-subscribe webhook in Meta dashboard

### 2. Media Download Failures

**Symptoms:**
- Voice notes not being transcribed
- "Failed to download media" errors
- Empty audio responses

**Diagnosis:**
```bash
# Check media download manually
curl -X GET "https://graph.facebook.com/v17.0/MEDIA_ID" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}"

# Check disk space
df -h /tmp

# Check file permissions
ls -la /tmp/whatsapp_media/
```

**Solutions:**
1. Clear temp directory:
   ```bash
   rm -rf /tmp/whatsapp_media/*
   ```
2. Refresh WhatsApp access token if expired
3. Increase disk space if needed
4. Check network connectivity to Meta CDN:
   ```bash
   curl -I https://cdn.fbsbx.com/
   ```
5. Verify ffmpeg is installed:
   ```bash
   ffmpeg -version
   ```

### 3. Redis Connection Issues

**Symptoms:**
- "Redis connection refused" errors
- Session verification failing
- Slow response times

**Diagnosis:**
```bash
# Check Redis status
systemctl status redis
redis-cli ping

# Check connections
redis-cli CLIENT LIST | wc -l

# Check memory usage
redis-cli INFO memory

# Test connection from app
python -c "import redis; r=redis.from_url('${REDIS_URL}'); print(r.ping())"
```

**Solutions:**
1. Restart Redis:
   ```bash
   systemctl restart redis
   ```
2. Clear Redis cache if full:
   ```bash
   redis-cli FLUSHDB
   ```
3. Increase max connections:
   ```bash
   echo "maxclients 10000" >> /etc/redis/redis.conf
   systemctl restart redis
   ```
4. Check for memory issues:
   ```bash
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```

### 4. Encryption/Decryption Errors

**Symptoms:**
- "Failed to decrypt memory" errors
- Corrupted memory files
- SECRET/ULTRA_SECRET categories inaccessible

**Diagnosis:**
```bash
# Check encryption keys exist
ls -la data/.keys/

# Verify key permissions
stat data/.keys/master.key

# Test encryption module
python -c "from app.security.encryption import EncryptionManager; e=EncryptionManager(); print('OK')"

# Check for corrupted files
find data/contacts -name "*.md" -exec file {} \; | grep -v "text"
```

**Solutions:**
1. Regenerate encryption keys (CAUTION: Will make old encrypted data unreadable):
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())" > data/.keys/master.key
   ```
2. Restore from backup if keys are lost
3. Fix file permissions:
   ```bash
   chmod 600 data/.keys/master.key
   chmod 700 data/.keys/
   ```
4. Remove corrupted files after backing up

### 5. High Memory Usage

**Symptoms:**
- OOM (Out of Memory) errors
- Slow response times
- Application crashes

**Diagnosis:**
```bash
# Check memory usage
free -h
ps aux | grep python | head -5

# Check for memory leaks
cat /proc/$(pgrep -f "uvicorn app.main")/status | grep VmRSS

# Monitor over time
while true; do ps aux | grep python | head -1; sleep 5; done
```

**Solutions:**
1. Restart application:
   ```bash
   systemctl restart memoapp
   ```
2. Clear old session data:
   ```bash
   redis-cli --scan --pattern "session:*" | xargs redis-cli DEL
   ```
3. Archive old memories:
   ```bash
   find data/contacts -name "*.md" -mtime +90 -exec gzip {} \;
   ```
4. Increase memory limit or add swap:
   ```bash
   fallocate -l 2G /swapfile
   chmod 600 /swapfile
   mkswap /swapfile
   swapon /swapfile
   ```

### 6. Azure Speech Service Errors

**Symptoms:**
- Voice transcription failing
- Text-to-speech not working
- "Azure authentication failed" errors

**Diagnosis:**
```bash
# Test Azure credentials
curl -X POST "https://${AZURE_SPEECH_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US" \
  -H "Ocp-Apim-Subscription-Key: ${AZURE_SPEECH_KEY}" \
  -H "Content-Type: audio/wav" \
  --data-binary @test.wav

# Check quota
curl -X GET "https://management.azure.com/subscriptions/{subscription-id}/providers/Microsoft.CognitiveServices/locations/${AZURE_SPEECH_REGION}/usages" \
  -H "Authorization: Bearer {token}"
```

**Solutions:**
1. Verify API key is valid and not expired
2. Check Azure service status: https://status.azure.com/
3. Switch to backup region if primary is down:
   ```bash
   export AZURE_SPEECH_REGION=westus2
   systemctl restart memoapp
   ```
4. Implement fallback to OpenAI Whisper if Azure fails

### 7. Classification Service Issues

**Symptoms:**
- All messages going to GENERAL category
- OpenAI API errors
- Slow message processing

**Diagnosis:**
```bash
# Test OpenAI API
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"test"}],"max_tokens":10}'

# Check rate limits
curl https://api.openai.com/v1/usage/daily \
  -H "Authorization: Bearer ${OPENAI_API_KEY}"
```

**Solutions:**
1. Implement exponential backoff for rate limits
2. Use fallback to keyword-based classification
3. Cache classification results in Redis
4. Reduce API calls by batching messages

## Log Analysis

### Key Log Patterns

```bash
# Find errors in last hour
grep -E "ERROR|CRITICAL" /var/log/memoapp/app.log | tail -100

# Track specific user issues
grep "phone_number" /var/log/memoapp/app.log

# Webhook processing times
grep "Webhook processed" /var/log/memoapp/app.log | awk '{print $NF}' | sort -n | tail -10

# Failed operations
grep -E "Failed|Error|Exception" /var/log/memoapp/app.log | cut -d' ' -f4- | sort | uniq -c | sort -rn

# Security events
grep -E "AUTH|DENIED|BLOCKED" /var/log/memoapp/audit.log
```

### Useful Debug Commands

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
systemctl restart memoapp

# Trace specific request
curl -H "X-Request-ID: debug-123" http://localhost:5000/webhook/whatsapp
grep "debug-123" /var/log/memoapp/app.log

# Monitor real-time
tail -f /var/log/memoapp/app.log | grep --line-buffered ERROR
```

## Performance Troubleshooting

### Slow Response Times

```bash
# Check response times
grep "response_time" /var/log/memoapp/metrics.log | awk '{print $2}' | sort -n | tail -20

# Profile slow endpoints
python -m cProfile -o profile.stats app/main.py
python -m pstats profile.stats

# Check database queries (if using DB)
tail -f /var/log/postgresql/postgresql.log | grep -E "duration: [0-9]{4,}"

# Network latency to Meta
ping -c 10 graph.facebook.com
traceroute graph.facebook.com
```

### High Error Rates

```bash
# Error rate calculation
total=$(grep "request" /var/log/memoapp/app.log | wc -l)
errors=$(grep "ERROR" /var/log/memoapp/app.log | wc -l)
echo "Error rate: $(( errors * 100 / total ))%"

# Error distribution
grep ERROR /var/log/memoapp/app.log | cut -d' ' -f5- | sort | uniq -c | sort -rn | head -10

# Recent error spike
for i in {60..0}; do
  echo "$(date -d "$i minutes ago" '+%H:%M'): $(grep "$(date -d "$i minutes ago" '+%Y-%m-%d %H:%M')" /var/log/memoapp/app.log | grep -c ERROR)"
done
```

## Escalation Procedures

### Severity Levels

**SEV-1 (Critical)**: Complete service outage
- No messages being processed
- Data loss occurring
- Security breach detected
- **Response**: Page primary and secondary on-call immediately
- **Target**: Respond within 15 minutes

**SEV-2 (High)**: Major functionality impaired
- > 50% of messages failing
- Voice features completely down
- Authentication broken
- **Response**: Page primary on-call
- **Target**: Respond within 30 minutes

**SEV-3 (Medium)**: Partial degradation
- Specific commands failing
- Slow response times (>5s)
- Non-critical features down
- **Response**: Notify on-call via Slack
- **Target**: Respond within 2 hours

**SEV-4 (Low)**: Minor issues
- Cosmetic problems
- Non-blocking errors in logs
- **Response**: Create ticket for next business day
- **Target**: Respond within 24 hours

### Escalation Chain

1. **L1 - On-Call Engineer** (0-30 minutes)
   - Perform initial diagnosis
   - Apply standard fixes
   - Collect diagnostics

2. **L2 - Senior Engineer** (30-60 minutes)
   - Deep technical investigation
   - Code-level debugging
   - Complex fixes

3. **L3 - Engineering Lead** (60+ minutes)
   - Architecture decisions
   - External vendor issues
   - Major incidents

4. **L4 - CTO/VP Engineering** (2+ hours)
   - Customer communication
   - Security incidents
   - Data loss scenarios

### Communication Templates

**Initial Response:**
```
We are aware of an issue affecting [service/feature].
Impact: [description]
Status: Investigating
Next update: In 30 minutes
```

**Update:**
```
Update on [service/feature] issue:
Root cause: [if known]
Current status: [Investigating/Mitigating/Monitoring]
ETA for resolution: [time]
Workaround: [if available]
```

**Resolution:**
```
The issue with [service/feature] has been resolved.
Root cause: [description]
Duration: [start time - end time]
Impact: [number of users/messages affected]
Follow-up: Post-mortem scheduled for [date]
```

## Recovery Procedures

### Full Service Recovery

```bash
# 1. Stop services
systemctl stop memoapp

# 2. Clear problematic state
redis-cli FLUSHDB
rm -rf /tmp/whatsapp_media/*

# 3. Restore from backup if needed
cd /opt/memoapp
tar -xzf backups/latest.tar.gz

# 4. Verify configuration
python -c "from app.main import app; print('Config OK')"

# 5. Start services
systemctl start redis
systemctl start memoapp

# 6. Verify health
curl http://localhost:5000/health

# 7. Send test message
curl -X POST http://localhost:5000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"test","type":"text","text":{"body":"/help"}}]}}]}]}'
```

### Data Recovery

```bash
# From backup
tar -xzf backups/backup_20250115.tar.gz -C /opt/memoapp/data/

# From Redis backup
redis-cli --rdb /var/lib/redis/dump.rdb

# Verify data integrity
find data/contacts -name "*.md" -exec head -1 {} \; | grep -c "^#"
```

## Monitoring Alerts

### Alert Configurations

```yaml
# Prometheus alerts
groups:
  - name: memoapp
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.01
        for: 5m
        annotations:
          summary: "Error rate above 1%"
          
      - alert: SlowResponse
        expr: histogram_quantile(0.95, response_time_seconds) > 2
        for: 10m
        annotations:
          summary: "95th percentile response time > 2s"
          
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        annotations:
          summary: "Redis is down"
          
      - alert: DiskSpaceLow
        expr: disk_free_percent < 20
        for: 5m
        annotations:
          summary: "Disk space below 20%"
```

## Post-Incident

### Post-Mortem Template

```markdown
# Incident Post-Mortem: [Title]

**Date**: [YYYY-MM-DD]
**Duration**: [HH:MM]
**Severity**: [SEV-1/2/3/4]
**Author**: [Name]

## Summary
[Brief description of what happened]

## Impact
- Users affected: [number]
- Messages lost/delayed: [number]
- Revenue impact: [$amount]

## Timeline
- HH:MM - [Event]
- HH:MM - [Event]
- HH:MM - [Resolution]

## Root Cause
[Detailed explanation]

## Contributing Factors
1. [Factor 1]
2. [Factor 2]

## What Went Well
- [Positive aspect]

## What Went Wrong
- [Issue]

## Action Items
- [ ] [Owner] - [Action] - [Due date]
- [ ] [Owner] - [Action] - [Due date]

## Lessons Learned
[Key takeaways]
```

Remember: Stay calm, communicate clearly, and document everything!