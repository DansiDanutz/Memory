# 🤖 Telegram Bot Setup Guide for Memory App

## Table of Contents
1. [Quick Start](#quick-start)
2. [Creating Your Telegram Bot](#creating-your-telegram-bot)
3. [Bot Configuration](#bot-configuration)
4. [Webhook Setup](#webhook-setup)
5. [Features Overview](#features-overview)
6. [Commands Reference](#commands-reference)
7. [Advanced Features](#advanced-features)
8. [Testing in Demo Mode](#testing-in-demo-mode)
9. [Production Deployment](#production-deployment)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- Telegram account
- Python 3.8+ installed
- Memory App webhook server running
- Access to environment variables

### Quick Setup (5 minutes)
```bash
# 1. Create bot with BotFather on Telegram
# 2. Get your bot token
# 3. Set environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_BOT_USERNAME="YourBotUsername"
export TELEGRAM_WEBHOOK_URL="https://your-domain.com/webhook/telegram"

# 4. Run the webhook server
python webhook_server_complete.py
```

---

## Creating Your Telegram Bot

### Step 1: Open BotFather
1. Open Telegram app (mobile or desktop)
2. Search for `@BotFather` (official bot creation bot)
3. Start a conversation: Click "START" or send `/start`

### Step 2: Create New Bot
1. Send `/newbot` to BotFather
2. Choose a name for your bot (e.g., "Memory Assistant")
   - This is the display name users will see
3. Choose a username (e.g., "MemoryApp_Bot")
   - Must end with "bot" or "_bot"
   - Must be unique across Telegram
4. BotFather will provide your bot token:
   ```
   Done! Congratulations on your new bot...
   Use this token to access the HTTP API:
   6000000000:AAHdqTcvCH1vGWJxfSeofSAs_A5XldME8Ys
   ```

### Step 3: Configure Bot Settings
Send these commands to BotFather:

```
/setdescription - Set bot description
/setabouttext - Set about text
/setuserpic - Upload bot profile picture
/setcommands - Set command menu
/setprivacy - Configure privacy settings
```

#### Recommended Command Menu
Send `/setcommands` to BotFather, then paste:
```
help - Show all available commands
enroll - Start voice enrollment
status - Check account status
store - Store a new memory
memories - List recent memories
search - Search your memories
summary - Get daily summary
contact - Manage contacts
secret - Create secret memory
settings - Configure preferences
upgrade - View premium plans
```

#### Privacy Settings
Send `/setprivacy` and choose:
- **Disable** - Bot can read all messages (recommended for memory storage)
- **Enable** - Bot only sees commands starting with /

---

## Bot Configuration

### Environment Variables
Create a `.env` file or set these environment variables:

```bash
# Required
TELEGRAM_BOT_TOKEN="6000000000:AAHdqTcvCH1vGWJxfSeofSAs_A5XldME8Ys"
TELEGRAM_BOT_USERNAME="YourMemoryBot"

# Optional (with defaults)
TELEGRAM_WEBHOOK_URL="https://your-domain.com/webhook/telegram"
TELEGRAM_API_URL="https://api.telegram.org"

# For development/testing
TELEGRAM_DEMO_MODE="false"  # Set to "true" for demo mode
```

### Configuration File
The bot uses `communication_config.py`:

```python
self.telegram = {
    'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN'),
    'bot_username': os.environ.get('TELEGRAM_BOT_USERNAME'),
    'webhook_url': os.environ.get('TELEGRAM_WEBHOOK_URL'),
    'api_url': 'https://api.telegram.org',
    'demo_mode': not bool(os.environ.get('TELEGRAM_BOT_TOKEN'))
}
```

---

## Webhook Setup

### Option 1: Automatic Webhook (Recommended)
The Memory App automatically sets the webhook when started:

```python
# Automatic webhook registration on startup
async def register_telegram_webhook():
    token = communication_config.telegram['bot_token']
    webhook_url = f"{communication_config.webhook['base_url']}/webhook/telegram/{token}"
    
    response = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={'url': webhook_url}
    )
    return response.json()
```

### Option 2: Manual Webhook Setup
Use curl or HTTP client:

```bash
# Set webhook
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/webhook/telegram/<YOUR_BOT_TOKEN>"}'

# Check webhook status
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# Remove webhook (for polling mode)
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

### Webhook URL Format
```
https://your-domain.com/webhook/telegram/<BOT_TOKEN>
```
- The token in URL provides additional security
- Must be HTTPS with valid SSL certificate
- Port must be 443, 80, 88, or 8443

---

## Features Overview

### 🎤 Voice Features
- **Voice Message Processing**: Send voice notes for automatic transcription
- **Voice-Activated Memory Retrieval**: Say "Memory Number 1234" to retrieve
- **Voice Enrollment**: Secure voice authentication
- **Voice Cloning** (Premium): Create AI voice avatar

### 💬 Text Features
- **Memory Storage**: Store conversations and memories
- **Smart Search**: Natural language memory search
- **Categories**: Organize memories by type
- **Daily Summaries**: Automated daily memory reviews

### 📱 Media Support
- **Photos**: Store images with descriptions
- **Documents**: Save important documents
- **Voice Notes**: Automatic transcription and storage
- **Location**: Save location-based memories

### 👥 Social Features
- **Contact Profiles**: Build detailed contact memories
- **Group Chat Support**: Works in group conversations
- **Memory Sharing**: Share memories with contacts
- **Mutual Connections**: Track relationship networks

### 🔒 Security Features
- **Secret Memories**: Encrypted private memories
- **Voice Authentication**: Biometric security
- **Access Control**: Granular permissions
- **Memory Inheritance**: Legacy planning

---

## Commands Reference

### Basic Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot | `/start` |
| `/help` | Show all commands | `/help` |
| `/status` | Check account status | `/status` |

### Memory Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/store [content]` | Store new memory | `/store Meeting with John about project` |
| `/memory [number]` | Retrieve specific memory | `/memory 1234` |
| `/memories` | List recent memories | `/memories` |
| `/search [query]` | Search memories | `/search birthday party` |
| `/edit [number] [content]` | Edit memory | `/edit 1234 Updated content` |
| `/delete [number]` | Delete memory | `/delete 1234` |

### Voice Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/enroll [name]` | Start voice enrollment | `/enroll John Doe` |
| `/verify` | Verify voice identity | `/verify` |
| (Voice message) | Auto-transcribe & store | Send voice note |

### Contact Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/contact [name]` | View/create contact | `/contact Jane Smith` |
| `/contacts` | List all contacts | `/contacts` |
| `/relationship [name] [type]` | Set relationship | `/relationship Jane wife` |

### Secret Memory Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/secret` | Create secret memory | `/secret` then follow prompts |
| `/secrets` | List secret memories | `/secrets` |
| `/unlock [id]` | Unlock secret memory | `/unlock secret_123` |

### Premium Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/upgrade` | View premium plans | `/upgrade` |
| `/avatar` | Configure AI avatar | `/avatar` |
| `/analytics` | View memory analytics | `/analytics` |

---

## Advanced Features

### Inline Keyboards
The bot uses inline keyboards for better UX:

```python
# Example inline keyboard
keyboard = {
    'inline_keyboard': [
        [
            {'text': '📋 Full Content', 'callback_data': 'full_1234'},
            {'text': '✏️ Edit', 'callback_data': 'edit_1234'}
        ],
        [
            {'text': '🗑️ Delete', 'callback_data': 'delete_1234'},
            {'text': '🔄 Related', 'callback_data': 'related_1234'}
        ]
    ]
}
```

### Multi-Step Flows
The bot maintains conversation state for complex operations:

1. **Voice Enrollment Flow**
   - `/enroll` → Name input → 3 voice samples → Confirmation

2. **Secret Memory Flow**
   - `/secret` → Title input → Content input → Category → Encryption

3. **Contact Creation Flow**
   - `/contact` → Name → Relationship → Details → Photo (optional)

### Group Chat Support
The bot works in groups with these features:
- Responds only when mentioned: `@YourBot command`
- Tracks group conversations
- Respects privacy settings
- Admin-only commands available

### Scheduled Messages
Set reminders and scheduled summaries:
```
/schedule daily 09:00 - Daily summary at 9 AM
/schedule weekly monday 10:00 - Weekly review
/reminder 2024-12-25 "Christmas shopping"
```

---

## Testing in Demo Mode

### Enable Demo Mode
```bash
# Don't set TELEGRAM_BOT_TOKEN or set explicitly
export TELEGRAM_DEMO_MODE="true"
```

### Test Endpoints
Use these endpoints to simulate Telegram interactions:

#### 1. Test Message
```bash
curl -X POST http://localhost:8080/api/test/telegram/message \
  -H "Content-Type: application/json" \
  -d '{
    "from": "123456789",
    "username": "testuser",
    "message": "/help",
    "chat_type": "private"
  }'
```

#### 2. Test Voice Message
```bash
curl -X POST http://localhost:8080/api/test/telegram/voice \
  -H "Content-Type: application/json" \
  -d '{
    "from": "123456789",
    "duration": 5,
    "transcript": "Store memory about meeting"
  }'
```

#### 3. Test Callback Query
```bash
curl -X POST http://localhost:8080/api/test/telegram/callback \
  -H "Content-Type: application/json" \
  -d '{
    "from": "123456789",
    "data": "full_1234"
  }'
```

#### 4. Check Status
```bash
curl http://localhost:8080/api/test/telegram/status
```

#### 5. Simulate Complete Flow
```bash
curl -X POST http://localhost:8080/api/test/telegram/simulate-flow \
  -H "Content-Type: application/json" \
  -d '{
    "flow": "enrollment",
    "user_id": "123456789"
  }'
```

---

## Production Deployment

### SSL Certificate Requirements
Telegram requires valid SSL certificates:
- Must be from trusted CA (Let's Encrypt works)
- No self-signed certificates
- Domain must match certificate

### Recommended Setup
1. **Use a reverse proxy** (nginx/Apache)
   ```nginx
   location /webhook/telegram/ {
       proxy_pass http://localhost:8080;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

2. **Set production environment**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_production_token"
   export WEBHOOK_BASE_URL="https://your-domain.com"
   export TELEGRAM_DEMO_MODE="false"
   ```

3. **Enable monitoring**
   - Set up health checks
   - Monitor webhook delivery
   - Track API rate limits

### Rate Limits
Telegram API limits:
- **Messages**: 30 messages/second to different users
- **Bulk messages**: 20 messages/minute to same chat
- **File uploads**: 50 MB for documents, 10 MB for photos
- **Inline queries**: 30 queries/second

---

## Troubleshooting

### Common Issues

#### Bot Not Responding
1. Check webhook status:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```
2. Verify SSL certificate
3. Check server logs
4. Ensure bot privacy settings allow message reading

#### Webhook Not Receiving Updates
1. Verify URL is accessible:
   ```bash
   curl https://your-domain.com/webhook/telegram/<TOKEN>
   ```
2. Check SSL certificate validity
3. Ensure correct port (443, 80, 88, or 8443)
4. Remove and re-set webhook

#### Voice Messages Not Working
1. Check OpenAI API key is set
2. Verify audio file format support
3. Check file size limits (20 MB)
4. Review transcription logs

#### Commands Not Showing in Menu
1. Update commands with BotFather
2. Restart Telegram app
3. Clear app cache
4. Verify command format

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Check Endpoint
```bash
curl http://localhost:8080/api/health
```

### Contact Support
- **Documentation**: [Memory App Docs](https://memory-app.docs)
- **GitHub Issues**: [Report Bug](https://github.com/memory-app/issues)
- **Telegram Group**: [@MemoryAppSupport](https://t.me/MemoryAppSupport)

---

## API Reference

### Telegram Bot API Methods Used
- `setWebhook` - Register webhook URL
- `getWebhookInfo` - Check webhook status
- `sendMessage` - Send text messages
- `sendPhoto` - Send images
- `sendDocument` - Send files
- `sendVoice` - Send voice messages
- `editMessageText` - Edit sent messages
- `answerCallbackQuery` - Respond to inline buttons
- `getFile` - Download sent files
- `setMyCommands` - Set bot commands menu

### Webhook Payload Structure
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456789,
      "username": "user",
      "first_name": "John"
    },
    "chat": {
      "id": 123456789,
      "type": "private"
    },
    "date": 1234567890,
    "text": "/start"
  }
}
```

---

## Best Practices

1. **Security**
   - Never expose bot token in code
   - Validate webhook signatures
   - Use environment variables
   - Implement rate limiting

2. **User Experience**
   - Use inline keyboards for actions
   - Provide clear command feedback
   - Handle errors gracefully
   - Support command shortcuts

3. **Performance**
   - Process webhooks asynchronously
   - Cache frequently accessed data
   - Batch API requests when possible
   - Monitor response times

4. **Maintenance**
   - Log all interactions
   - Monitor error rates
   - Keep commands updated
   - Regular backup of data

---

## Next Steps

1. ✅ Create your bot with BotFather
2. ✅ Set environment variables
3. ✅ Start webhook server
4. ✅ Test basic commands
5. ✅ Configure advanced features
6. ✅ Deploy to production

🎉 **Congratulations!** Your Telegram bot is ready for the Memory App!