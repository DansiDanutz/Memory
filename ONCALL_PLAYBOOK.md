# MemoApp WhatsApp Bot - On-Call Playbook

## Emergency Contacts

- **Primary On-Call**: [Phone/Slack]
- **Secondary On-Call**: [Phone/Slack]
- **Engineering Lead**: [Phone/Slack]
- **Meta Support**: [Meta Developer Support](https://developers.facebook.com/support/)
- **Azure Support**: [Azure Support Portal](https://azure.microsoft.com/support/)

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

1. Check SSL certificate is valid and not expired
1. Ensure firewall allows incoming HTTPS traffic
1. Verify webhook URL is exact (no trailing slash)
1. Re-subscribe webhook in Meta dashboard

[... Rest of content restored ...]

Remember: Stay calm, communicate clearly, and document everything!
