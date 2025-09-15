# Twilio Integration Setup Guide for Memory App

## Overview
The Memory App supports full Twilio integration for voice calls and SMS messaging. This guide will help you set up your own Twilio account and configure it to work with the Memory App.

## Features Supported

### 📞 Voice Call Features
- **Incoming Call Handling**: AI-powered voice assistant answers calls
- **Call Recording**: Records and transcribes important conversations
- **Voice Commands**: Store memories using voice commands during calls
- **Voicemail Transcription**: Automatically transcribes and stores voicemails
- **Smart Call Routing**: Decides whether to answer or send to voicemail

### 📱 SMS Features
- **Memory Storage**: Store memories via SMS
- **Command Processing**: Support for MEMORY, RETRIEVE, SECRET commands
- **Media Support**: Process images and media attachments
- **Auto-Response**: Intelligent SMS responses based on content

## Prerequisites

1. **Twilio Account**: Sign up at [https://www.twilio.com](https://www.twilio.com)
2. **Phone Number**: Purchase a Twilio phone number with Voice and SMS capabilities
3. **Webhook URL**: Your app must be accessible from the internet (use ngrok for local testing)

## Step 1: Create a Twilio Account

1. Go to [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up for a free trial account (includes $15 credit)
3. Verify your email and phone number
4. Complete the onboarding process

## Step 2: Get Your Twilio Credentials

1. Navigate to the [Twilio Console](https://console.twilio.com)
2. Find your credentials on the dashboard:
   - **Account SID**: Starts with `AC` (e.g., `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
   - **Auth Token**: Click to reveal (keep this secret!)
3. Save these credentials securely

## Step 3: Purchase a Phone Number

1. In the Twilio Console, go to **Phone Numbers** → **Manage** → **Buy a Number**
2. Choose a number with:
   - ✅ Voice capability
   - ✅ SMS capability
   - ✅ MMS capability (optional, for media messages)
3. Purchase the number (costs ~$1/month)
4. Note your phone number (e.g., `+15551234567`)

## Step 4: Configure Environment Variables

Add these variables to your `.env` file:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567

# Webhook Configuration (your app's public URL)
WEBHOOK_BASE_URL=https://your-app-domain.com
```

**For Replit Users:**
1. Go to the Secrets tab (lock icon)
2. Add each variable as a secret
3. The app will automatically use these values

## Step 5: Configure Webhook URLs in Twilio

### Voice Webhooks

1. Go to **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on your phone number
3. In the **Voice & Fax** section:
   - **A call comes in**: 
     - Webhook: `https://your-app-domain.com/webhook/twilio/voice`
     - HTTP Method: `POST`
   - **Primary handler fails**:
     - Leave empty or set a fallback URL

### SMS Webhooks

1. In the same phone number configuration
2. In the **Messaging** section:
   - **A message comes in**:
     - Webhook: `https://your-app-domain.com/webhook/twilio/sms`
     - HTTP Method: `POST`

## Step 6: Testing Your Setup

### Test Voice Calls
1. Call your Twilio phone number
2. You should hear: "Hello! This is your AI assistant. How can I help you today?"
3. Say "Store a memory" to test memory storage
4. Say "Retrieve memories" to get recent memories

### Test SMS
1. Send an SMS to your Twilio phone number:
   - Text `MEMORY This is a test memory` to store
   - Text `RETRIEVE` to get recent memories
   - Text `HELP` for available commands

### Demo Mode Testing (No Twilio Account)
You can test the integration without a Twilio account using demo endpoints:

```bash
# Test voice call
curl -X POST http://localhost:8080/api/test/twilio/voice \
  -H "Content-Type: application/json" \
  -d '{"from": "+15551234567", "message": "Test call"}'

# Test SMS
curl -X POST http://localhost:8080/api/test/twilio/sms \
  -H "Content-Type: application/json" \
  -d '{"from": "+15551234567", "message": "MEMORY Test memory from SMS"}'
```

## Step 7: Production Deployment

### Security Best Practices

1. **Webhook Validation**: The app validates all Twilio webhooks using signature verification
2. **Rate Limiting**: Configured to prevent abuse (60 calls/min, 1000/hour)
3. **Auth Token Security**: Never commit your Auth Token to version control
4. **HTTPS Required**: Always use HTTPS for webhook URLs in production

### Monitoring

1. **Twilio Console**: Monitor usage and logs at https://console.twilio.com
2. **Error Logs**: Check `/webhook/twilio/errors` endpoint for issues
3. **Debug Mode**: Set `TWILIO_DEBUG=true` for verbose logging

## Webhook Payload Examples

### Incoming Call Webhook
```json
{
  "CallSid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "From": "+15551234567",
  "To": "+15559876543",
  "CallStatus": "ringing",
  "Direction": "inbound",
  "CallerName": "John Doe"
}
```

### SMS Webhook
```json
{
  "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "From": "+15551234567",
  "To": "+15559876543",
  "Body": "MEMORY Remember to call mom",
  "NumMedia": "0"
}
```

## Supported SMS Commands

| Command | Description | Example |
|---------|-------------|---------|
| `MEMORY <text>` | Store a new memory | `MEMORY Buy groceries tomorrow` |
| `RETRIEVE` | Get recent memories | `RETRIEVE` |
| `SECRET <text>` | Store a secret memory | `SECRET My password is xyz` |
| `SEARCH <query>` | Search memories | `SEARCH birthday` |
| `DELETE <number>` | Delete a memory | `DELETE 1001` |
| `HELP` | Show available commands | `HELP` |

## Voice Call Commands

During a call, you can say:
- **"Store a memory"**: Record a new memory
- **"Retrieve memories"**: Hear recent memories
- **"Search for [topic]"**: Search specific memories
- **"Store a secret"**: Record a secret memory
- **"End call"**: Hang up

## Troubleshooting

### Common Issues

1. **"Webhook Error - 11200"**
   - Your webhook URL is not accessible
   - Solution: Check your domain and firewall settings

2. **"Invalid Signature"**
   - Webhook validation failing
   - Solution: Verify your Auth Token is correct

3. **"No Response from Webhook"**
   - Server timeout or error
   - Solution: Check server logs, ensure response within 15 seconds

4. **Demo Mode Active**
   - Missing or invalid credentials
   - Solution: Check all environment variables are set correctly

### Testing with ngrok (Local Development)

1. Install ngrok: `npm install -g ngrok`
2. Start your app: `npm start`
3. Expose locally: `ngrok http 8080`
4. Use the ngrok URL for webhooks: `https://xxxxx.ngrok.io/webhook/twilio/voice`

## Cost Estimates

- **Phone Number**: ~$1/month
- **Incoming Calls**: ~$0.0085/minute
- **Outgoing Calls**: ~$0.014/minute
- **SMS**: ~$0.0075/message
- **Transcription**: ~$0.05/minute
- **Recording Storage**: ~$0.0005/minute/month

**Free Trial**: Includes $15 credit (enough for ~1000 SMS or ~1000 minutes of calls)

## API Rate Limits

- **Default**: 60 requests/minute, 1000 requests/hour
- **Concurrent Calls**: 10 simultaneous calls
- **SMS Queue**: 100 messages/second

## Support Resources

- **Twilio Documentation**: https://www.twilio.com/docs
- **Status Page**: https://status.twilio.com
- **Support**: https://support.twilio.com
- **Community Forum**: https://www.twilio.com/community

## Next Steps

1. ✅ Test voice calls and SMS in demo mode
2. ✅ Set up Twilio account and credentials
3. ✅ Configure webhooks
4. ✅ Test with real phone calls and SMS
5. ✅ Monitor usage and optimize costs
6. ✅ Scale as needed

---

**Need Help?** The app runs in demo mode by default, so you can test all features without a Twilio account. When you're ready, add your credentials and go live!