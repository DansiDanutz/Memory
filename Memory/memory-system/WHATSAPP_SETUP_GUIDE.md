# WhatsApp Business API Setup Guide for Memory App

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [WhatsApp Business API Access](#whatsapp-business-api-access)
4. [Configuration Steps](#configuration-steps)
5. [Webhook Setup](#webhook-setup)
6. [Environment Variables](#environment-variables)
7. [Testing in Demo Mode](#testing-in-demo-mode)
8. [Production Deployment](#production-deployment)
9. [Cost Information](#cost-information)
10. [Troubleshooting](#troubleshooting)

## Overview

The Memory App integrates with WhatsApp Business API to provide voice-activated memory storage, AI-powered call handling, and daily summaries through WhatsApp messaging. This guide covers the complete setup process from demo mode to production deployment.

### Key Features
- 🎤 Voice note transcription and memory storage
- 📱 Text message commands for memory management
- 🔐 Voice authentication for secure access
- 📊 Daily memory summaries
- 👥 Contact profile management
- 🔒 Secret memory handling with encryption

## Prerequisites

### Required Accounts
1. **Facebook Business Account**
   - Visit [business.facebook.com](https://business.facebook.com)
   - Create or use existing business account
   - Must have admin access

2. **WhatsApp Business Phone Number**
   - Dedicated phone number (not used with regular WhatsApp)
   - Can be landline or mobile
   - Must be able to receive SMS/calls for verification

3. **Meta Developer Account**
   - Visit [developers.facebook.com](https://developers.facebook.com)
   - Link to your Facebook Business Account
   - Create new app or use existing

### Technical Requirements
- HTTPS endpoint for webhooks (production)
- SSL certificate (production)
- Python 3.8+ with required packages
- PostgreSQL database (optional but recommended)

## WhatsApp Business API Access

### Step 1: Create Meta App
1. Go to [Meta for Developers](https://developers.facebook.com)
2. Click "My Apps" → "Create App"
3. Choose "Business" type
4. Select "WhatsApp" as product
5. Name your app (e.g., "Memory App WhatsApp")

### Step 2: Configure WhatsApp Business
1. In your app dashboard, click "WhatsApp" → "Getting Started"
2. Add a phone number:
   - Click "Add phone number"
   - Enter your business phone number
   - Verify via SMS or voice call
3. Create WhatsApp Business Profile:
   - Business name: Your Memory App service name
   - Category: Technology/Software
   - Description: AI-powered memory storage and retrieval

### Step 3: Generate Access Tokens
1. Go to "WhatsApp" → "Configuration"
2. Generate permanent access token:
   ```
   System User → Generate Token → Select permissions:
   - whatsapp_business_messaging
   - whatsapp_business_management
   ```
3. Copy and save the access token securely

### Step 4: Get Phone Number ID
1. In WhatsApp Configuration
2. Find your phone number
3. Copy the Phone Number ID (numeric string)
4. Also copy the WhatsApp Business Account ID

## Configuration Steps

### 1. Clone and Setup Repository
```bash
# Clone the Memory App repository
git clone <your-repo-url>
cd memory-system

# Install Python dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 2. Configure Environment Variables
Edit `.env` file with your WhatsApp credentials:

```bash
# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_BUSINESS_ID=your_business_account_id_here
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token_here
WHATSAPP_WEBHOOK_SECRET=your_webhook_secret_here

# Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com
JWT_SECRET=your_jwt_secret_for_websocket

# Optional: Database Configuration
DATABASE_URL=postgresql://user:password@localhost/memoryapp
```

### 3. Test Configuration
Run the configuration validator:
```bash
python3 -c "from communication_config import communication_config; print(communication_config.validate_configuration())"
```

## Webhook Setup

### 1. Configure Webhook URL
In Meta App Dashboard:
1. Go to "WhatsApp" → "Configuration" → "Webhook"
2. Click "Edit"
3. Enter webhook URL: `https://your-domain.com/webhook/whatsapp`
4. Enter Verify Token: (same as WHATSAPP_VERIFY_TOKEN in .env)
5. Click "Verify and Save"

### 2. Subscribe to Webhook Events
Select the following webhook fields:
- `messages` - Incoming messages
- `message_status` - Delivery status updates
- `message_template_status_update` - Template updates

### 3. Webhook Verification
The webhook will be verified automatically when you save. The server handles verification at:
```python
@app.route('/webhook/whatsapp', methods=['GET'])
def whatsapp_webhook_verify():
    # Handles Meta's verification challenge
```

### 4. Test Webhook
Send a test message from WhatsApp to your business number:
```bash
curl -X POST http://localhost:8080/api/test/whatsapp/status
```

## Environment Variables

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `WHATSAPP_ACCESS_TOKEN` | Permanent access token from Meta | `EAABcd123...` |
| `WHATSAPP_PHONE_NUMBER_ID` | Your WhatsApp phone number ID | `123456789012345` |
| `WHATSAPP_BUSINESS_ID` | WhatsApp Business Account ID | `987654321098765` |
| `WHATSAPP_VERIFY_TOKEN` | Custom token for webhook verification | `my-secure-verify-token` |
| `WHATSAPP_WEBHOOK_SECRET` | Secret for webhook signature validation | `my-webhook-secret` |

### Optional Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_BASE_URL` | Your server's base URL | `http://localhost:8080` |
| `DATABASE_URL` | PostgreSQL connection string | Local SQLite |
| `OPENAI_API_KEY` | For AI features | Required for AI |
| `STRIPE_SECRET_KEY` | For premium features | Required for payments |

## Testing in Demo Mode

### 1. Start in Demo Mode
When environment variables are not set, the app runs in demo mode:
```bash
# Start webhook server
cd memory-system
python3 webhook_server_complete.py
```

### 2. Test Endpoints Available
Demo mode provides test endpoints for development:

#### Send Test Message
```bash
curl -X POST http://localhost:8080/api/test/whatsapp/message \
  -H "Content-Type: application/json" \
  -d '{
    "from": "+1234567890",
    "message": "/enroll John Doe",
    "type": "text"
  }'
```

#### Send Test Voice Note
```bash
curl -X POST http://localhost:8080/api/test/whatsapp/voice \
  -H "Content-Type: application/json" \
  -d '{
    "from": "+1234567890",
    "audio_data": "base64_encoded_audio_here"
  }'
```

#### Check Status
```bash
curl http://localhost:8080/api/test/whatsapp/status
```

### 3. Demo Mode Features
- No real WhatsApp API calls
- Simulated responses
- Full command testing
- Local memory storage
- Console logging for debugging

## Production Deployment

### 1. SSL Certificate Setup
WhatsApp requires HTTPS for webhooks:
```bash
# Using Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

### 2. Production Server Setup
```bash
# Install production server
pip install gunicorn

# Create systemd service
sudo nano /etc/systemd/system/memory-webhook.service
```

Service configuration:
```ini
[Unit]
Description=Memory App WhatsApp Webhook Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/memory-system
Environment="PATH=/usr/bin"
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:8080 webhook_server_complete:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Start Production Service
```bash
sudo systemctl enable memory-webhook
sudo systemctl start memory-webhook
sudo systemctl status memory-webhook
```

### 4. Configure Nginx Reverse Proxy
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location /webhook/whatsapp {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Cost Information

### WhatsApp Business API Pricing

#### Monthly Costs
1. **WhatsApp Business Platform Fee**: Free for first 1,000 conversations/month
2. **Conversation Pricing** (after free tier):
   - User-initiated: $0.00-$0.08 per conversation
   - Business-initiated: $0.03-$0.15 per conversation
   - Prices vary by country

#### Conversation Types
- **User-Initiated**: 24-hour window after user messages
- **Business-Initiated**: Using message templates (requires approval)
- **Service Conversations**: Customer support (user-initiated)
- **Marketing/Utility**: Business-initiated categories

#### Cost Optimization Tips
1. Batch messages within 24-hour window
2. Use user-initiated conversations when possible
3. Implement rate limiting
4. Cache frequent responses
5. Use message templates efficiently

### Additional Costs
- **Hosting**: $5-50/month depending on provider
- **SSL Certificate**: Free with Let's Encrypt
- **Database**: $0-25/month for PostgreSQL
- **OpenAI API**: Usage-based for AI features

## Troubleshooting

### Common Issues and Solutions

#### 1. Webhook Verification Fails
**Problem**: Meta can't verify webhook endpoint
**Solutions**:
- Ensure HTTPS is working: `curl https://your-domain.com/webhook/whatsapp`
- Check verify token matches in both .env and Meta dashboard
- Verify GET endpoint returns challenge parameter
- Check server logs: `tail -f /var/log/memory-webhook.log`

#### 2. Messages Not Received
**Problem**: WhatsApp messages don't trigger webhook
**Solutions**:
- Verify webhook subscriptions in Meta dashboard
- Check webhook URL is correct and HTTPS
- Ensure phone number is verified and active
- Test with curl to webhook endpoint directly

#### 3. Authentication Errors
**Problem**: 403 or 401 errors from WhatsApp API
**Solutions**:
- Regenerate access token in Meta dashboard
- Verify token has required permissions
- Check token hasn't expired (permanent tokens don't expire)
- Ensure phone number ID is correct

#### 4. Voice Notes Not Processing
**Problem**: Voice messages fail to transcribe
**Solutions**:
- Check OpenAI API key is set
- Verify audio format compatibility (ogg, mp3, wav)
- Check file size limits (25MB max)
- Review transcription logs for errors

#### 5. Database Connection Issues
**Problem**: Memories not persisting
**Solutions**:
- Verify DATABASE_URL is correct
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Test connection: `psql $DATABASE_URL`
- Review database logs

### Debug Commands

```bash
# Check webhook server status
curl http://localhost:8080/health

# View server logs
journalctl -u memory-webhook -f

# Test WhatsApp configuration
python3 test_all_communications.py

# Validate environment
python3 -c "from communication_config import communication_config; print(communication_config.get_active_services())"

# Send test webhook
curl -X POST http://localhost:8080/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"1234567890","text":{"body":"test"}}]}}]}]}'
```

### Support Resources

1. **Meta WhatsApp Business Documentation**
   - [Official Docs](https://developers.facebook.com/docs/whatsapp)
   - [API Reference](https://developers.facebook.com/docs/whatsapp/cloud-api)

2. **Memory App Support**
   - GitHub Issues: [your-repo/issues]
   - Documentation: [your-docs-url]
   - Community: [your-community-url]

3. **Rate Limits**
   - 80 messages/second per phone number
   - 500,000 messages/day per phone number
   - 1,000 QR codes/day

## Migration from Demo to Production

### Step 1: Backup Demo Data
```bash
# Export demo memories
python3 migrate_memories.py --export --output demo_backup.json
```

### Step 2: Update Configuration
1. Set production environment variables
2. Update webhook URL in Meta dashboard
3. Configure SSL certificate
4. Set up production database

### Step 3: Import Data
```bash
# Import to production database
python3 migrate_memories.py --import --input demo_backup.json
```

### Step 4: Verify Production
```bash
# Run production tests
python3 test_complete_platform.py --production
```

### Step 5: Monitor
- Set up logging aggregation
- Configure error alerts
- Monitor webhook response times
- Track message delivery rates

## Security Best Practices

1. **Token Security**
   - Never commit tokens to git
   - Use environment variables
   - Rotate tokens periodically
   - Use webhook signatures

2. **Data Protection**
   - Encrypt sensitive memories
   - Use HTTPS everywhere
   - Implement rate limiting
   - Validate all inputs

3. **Access Control**
   - Voice authentication for sensitive data
   - User verification challenges
   - Session management
   - Audit logging

4. **Compliance**
   - Follow WhatsApp Business Policy
   - Implement data retention policies
   - Provide user data export
   - Handle opt-outs properly

---

## Quick Start Checklist

- [ ] Create Meta Developer account
- [ ] Set up WhatsApp Business app
- [ ] Get phone number verified
- [ ] Generate access tokens
- [ ] Configure environment variables
- [ ] Test in demo mode
- [ ] Set up HTTPS (production)
- [ ] Configure webhooks
- [ ] Test message flow
- [ ] Deploy to production

For additional help, refer to the [WHATSAPP_FEATURES.md](WHATSAPP_FEATURES.md) for detailed command documentation.