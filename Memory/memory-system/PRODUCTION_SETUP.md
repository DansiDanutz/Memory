# Production Setup Guide - Digital Immortality Platform

## Quick Start

Your Digital Immortality Platform is ready for production deployment with WhatsApp Cloud API integration!

## 🚀 Production Deployment Steps

### 1. WhatsApp Business Setup
1. Go to [Meta for Developers](https://developers.facebook.com)
2. Create a new WhatsApp Business App
3. Get your credentials:
   - **Access Token**: System User Access Token
   - **Phone Number ID**: WhatsApp Business Phone Number ID
   - **Webhook Verify Token**: Create a custom token (e.g., `your-secret-verify-token-2025`)

### 2. Configure Environment Variables
Set these in your Replit Secrets:
```
META_ACCESS_TOKEN=your_meta_access_token
WA_PHONE_NUMBER_ID=your_phone_number_id
META_VERIFY_TOKEN=your_webhook_verify_token
```

### 3. Configure Webhook in Meta
1. In Meta Developer Console, go to WhatsApp > Configuration
2. Set Webhook URL: `https://your-replit-domain.repl.co/api/whatsapp/webhook`
3. Set Verify Token: Same as META_VERIFY_TOKEN
4. Subscribe to webhook fields: `messages`, `messaging_postbacks`

### 4. Deploy to Production
The system is configured for autoscale deployment. Click "Deploy" in Replit to publish.

## 📱 WhatsApp Commands

### Text Commands
- `enroll: <passphrase>` - Set your voice passphrase
- `verify: <passphrase>` - Unlock secret memories (10 min)
- `search: <query>` - Search your memories

### Voice Note Commands
- Send any voice note for automatic transcription
- Say passphrase to verify
- Ask questions to search memories

## 🔐 Security Levels

1. **General** - Everyday conversations (always accessible)
2. **Chronological** - Events and appointments (always accessible)
3. **Confidential** - Personal information (always accessible)
4. **Secret** - Sensitive data (requires verification)
5. **Ultra-Secret** - Critical information (requires verification)

## 📂 Data Storage

Memories are stored in: `data/contacts/<phone_number>/memories/`
- `general.md` - General conversations
- `chronological.md` - Time-based events
- `confidential.md` - Personal information
- `secret.md` - Protected sensitive data
- `ultra_secret.md` - Highest security data

## 🔧 Testing

### Test in Demo Mode
The system runs in demo mode when WhatsApp credentials aren't set:
```bash
python memory-system/test_whatsapp_integration.py
```

### Test Voice Processing
```bash
python memory-system/test_voice_processing.py
```

## 📊 Monitoring

- Health Check: `GET /api/health`
- WhatsApp Status: `GET /api/whatsapp/status`
- Admin Dashboard: `/admin` (username: admin, password: check logs)

## 🚨 Troubleshooting

### Webhook Not Receiving Messages
1. Check webhook verification passed in Meta console
2. Verify all environment variables are set
3. Check webhook URL is publicly accessible

### Voice Notes Not Processing
1. Ensure OPENAI_API_KEY is set
2. Check audio format compatibility (OGG/Opus)
3. Verify META_ACCESS_TOKEN for media download

### Search Not Working
1. Check memories are stored in correct directories
2. Verify security level classifications
3. Test passphrase verification for secret content

## 📱 Support

For issues or questions:
- Check logs: `/api/admin/logs`
- Health status: `/api/health`
- WhatsApp status: `/api/whatsapp/status`

Your Digital Immortality Platform is ready to preserve and manage memories with enterprise-grade security!