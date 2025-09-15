# Twilio Integration Features Documentation

## Table of Contents
1. [Overview](#overview)
2. [Voice Call Features](#voice-call-features)
3. [SMS Features](#sms-features)
4. [Test Endpoints](#test-endpoints)
5. [Webhook Architecture](#webhook-architecture)
6. [Security Features](#security-features)
7. [Error Handling](#error-handling)
8. [API Reference](#api-reference)

## Overview

The Memory App's Twilio integration provides comprehensive voice and SMS capabilities for storing and retrieving memories through phone calls and text messages. The integration supports both production and demo modes, allowing testing without real Twilio credentials.

### Key Capabilities
- 📞 **Voice Calls**: AI-powered call handling with recording and transcription
- 📱 **SMS Messaging**: Command-based memory management via text
- 🎤 **Voice Commands**: Natural language processing for voice interactions
- 🔐 **Secure Storage**: Encrypted memory storage with user authentication
- 🧪 **Demo Mode**: Full feature testing without Twilio account

## Voice Call Features

### 1. Incoming Call Handling
When someone calls your Twilio number, the app:
- Identifies the caller via phone number
- Determines whether to answer or send to voicemail
- Greets the caller with a personalized message
- Processes voice commands in real-time

### 2. Voice Commands

| Command | Description | Example Response |
|---------|-------------|------------------|
| "Store a memory" | Initiates memory recording | "Please tell me the memory you'd like to store." |
| "Retrieve memories" | Gets recent memories | "Here are your recent memories: Memory 1001..." |
| "Search for [topic]" | Searches specific memories | "Found 3 memories about birthday..." |
| "Store a secret" | Records encrypted memory | "Your secret has been stored securely." |
| "End call" | Terminates the call | "Thank you for calling. Goodbye!" |

### 3. Call Recording & Transcription
- **Automatic Recording**: Calls are recorded when memory storage is requested
- **Real-time Transcription**: Speech-to-text conversion using Twilio's API
- **Storage**: Transcriptions stored as memories with metadata
- **Privacy**: Recordings encrypted and user-controlled

### 4. Voicemail System
- **Smart Routing**: Calls routed to voicemail when user unavailable
- **Transcription**: Voicemail automatically transcribed and stored
- **Notifications**: User notified of new voicemails
- **Retrieval**: Access voicemails as memories

### Example Voice Call Flow
```xml
<!-- TwiML Response for incoming call -->
<Response>
    <Say voice="alice">Hello! This is your AI assistant. How can I help you today?</Say>
    <Gather input="speech" timeout="5" action="/webhook/twilio/voice-command/SESSION_ID">
        <Say>Please say your command.</Say>
    </Gather>
</Response>
```

## SMS Features

### 1. Supported SMS Commands

| Command | Syntax | Description | Example |
|---------|--------|-------------|---------|
| **MEMORY** | `MEMORY <text>` | Store a new memory | `MEMORY Buy milk tomorrow` |
| **RETRIEVE** | `RETRIEVE` | Get 5 recent memories | `RETRIEVE` |
| **SECRET** | `SECRET <text>` | Store encrypted memory | `SECRET My PIN is 1234` |
| **SEARCH** | `SEARCH <query>` | Search memories | `SEARCH doctor appointment` |
| **DELETE** | `DELETE <number>` | Remove a memory | `DELETE 1001` |
| **HELP** | `HELP` | Show available commands | `HELP` |

### 2. SMS Processing Logic
```python
# Command processing flow
1. Receive SMS → Parse command
2. Validate user → Check permissions
3. Process command → Execute action
4. Store result → Update database
5. Send response → Return SMS
```

### 3. Media Message Support
- **Image Attachments**: Process MMS with images
- **Media Storage**: Save media URLs with memories
- **Thumbnail Generation**: Create previews for stored media
- **Size Limits**: Max 5MB per attachment

### 4. Auto-Response System
- **Smart Replies**: Context-aware responses based on message content
- **Command Suggestions**: Helpful hints for invalid commands
- **Confirmation Messages**: Acknowledge successful operations
- **Error Messages**: Clear feedback for failed operations

## Test Endpoints

### 1. Voice Call Test Endpoint
**URL**: `POST /api/test/twilio/voice`

**Request Body**:
```json
{
    "from": "+15551234567",
    "message": "store memory test call content"
}
```

**Response**:
```json
{
    "status": "success",
    "action": "memory_stored",
    "memory_number": "1001",
    "transcript": "test call content",
    "response": "Memory 1001 stored successfully",
    "twiml_response": "<Response>...</Response>"
}
```

### 2. SMS Test Endpoint
**URL**: `POST /api/test/twilio/sms`

**Request Body**:
```json
{
    "from": "+15551234567",
    "message": "MEMORY Test memory from SMS",
    "media_url": "https://example.com/image.jpg"
}
```

**Response**:
```json
{
    "status": "success",
    "command": "MEMORY",
    "from": "+15551234567",
    "response": "✅ Memory 1001 stored successfully!",
    "twiml_response": "<Response>...</Response>"
}
```

### 3. Status Check Endpoint
**URL**: `GET /api/test/twilio/status`

**Response**:
```json
{
    "status": "success",
    "twilio_config": {
        "demo_mode": true,
        "phone_number": "+15555551234",
        "features": {
            "voice": true,
            "sms": true
        }
    },
    "webhook_urls": {
        "voice": "/webhook/twilio/voice",
        "sms": "/webhook/twilio/sms"
    }
}
```

## Webhook Architecture

### 1. Webhook Flow Diagram
```
Twilio Cloud → Your App
    ↓
[Webhook Request]
    ↓
[Signature Verification]
    ↓
[Request Processing]
    ↓
[Memory App Logic]
    ↓
[TwiML Response]
    ↓
Twilio Cloud → User's Phone
```

### 2. Webhook Endpoints

| Endpoint | Method | Purpose | Authentication |
|----------|--------|---------|----------------|
| `/webhook/twilio/voice` | POST | Handle incoming calls | Twilio signature |
| `/webhook/twilio/voice-command/<session>` | POST | Process voice commands | Session-based |
| `/webhook/twilio/sms` | POST | Handle SMS messages | Twilio signature |
| `/webhook/twilio/voicemail` | POST | Process voicemails | Twilio signature |
| `/webhook/twilio/save-memory/<session>` | POST | Store voice memories | Session-based |

### 3. Webhook Security
- **Signature Verification**: All webhooks validate X-Twilio-Signature
- **HTTPS Required**: Production webhooks must use HTTPS
- **Rate Limiting**: 60 requests/minute, 1000/hour
- **IP Whitelisting**: Optional Twilio IP range filtering

## Security Features

### 1. Authentication & Authorization
- **Phone Number Verification**: User identity via caller ID
- **Session Management**: Unique session IDs for call tracking
- **JWT Tokens**: Secure API authentication
- **Rate Limiting**: Prevent abuse and spam

### 2. Data Encryption
- **Memory Encryption**: AES-256 for sensitive memories
- **Transport Security**: TLS 1.2+ for all communications
- **Recording Storage**: Encrypted audio file storage
- **Database Encryption**: At-rest encryption for all data

### 3. Privacy Controls
- **Consent Management**: Explicit recording consent
- **Data Retention**: Configurable retention policies
- **User Rights**: GDPR-compliant data access/deletion
- **Audit Logging**: Complete activity tracking

## Error Handling

### 1. Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| 11200 | HTTP retrieval failure | Check webhook URL accessibility |
| 11205 | HTTP connection failure | Verify server is running |
| 12100 | Invalid phone number | Validate number format |
| 21211 | Invalid 'To' phone number | Check recipient number |
| 21608 | Phone number not verified | Verify number in Twilio console |

### 2. Error Response Format
```json
{
    "error": {
        "code": "TWILIO_ERROR",
        "message": "Failed to process request",
        "details": {
            "twilio_code": 11200,
            "twilio_message": "HTTP retrieval failure"
        }
    },
    "status": "error"
}
```

### 3. Retry Logic
- **Automatic Retries**: 3 attempts with exponential backoff
- **Fallback Responses**: Default messages on failure
- **Queue System**: Failed operations queued for retry
- **Alert System**: Admin notifications for persistent failures

## API Reference

### Voice Call Webhook Request
```json
{
    "CallSid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "From": "+15551234567",
    "To": "+15559876543",
    "CallStatus": "ringing",
    "Direction": "inbound",
    "CallerName": "John Doe",
    "FromCity": "San Francisco",
    "FromState": "CA",
    "FromCountry": "US"
}
```

### SMS Webhook Request
```json
{
    "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "MessagingServiceSid": "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "From": "+15551234567",
    "To": "+15559876543",
    "Body": "MEMORY Remember this important note",
    "NumMedia": "1",
    "MediaUrl0": "https://api.twilio.com/2010-04-01/Accounts/.../Media/...",
    "MediaContentType0": "image/jpeg"
}
```

### TwiML Response Examples

#### Voice Response
```xml
<Response>
    <Say voice="alice" language="en-US">
        Your memory has been saved successfully.
    </Say>
    <Pause length="1"/>
    <Say>
        Memory number 1001 has been created.
    </Say>
    <Hangup/>
</Response>
```

#### SMS Response
```xml
<Response>
    <Message>
        ✅ Memory 1001 stored successfully!
        📝 "Remember to call mom tomorrow"
        
        Reply RETRIEVE to see recent memories.
    </Message>
</Response>
```

## Testing Guide

### 1. Local Testing with ngrok
```bash
# Install ngrok
npm install -g ngrok

# Start your app
python webhook_server_complete.py

# Expose local server
ngrok http 8080

# Use ngrok URL for Twilio webhooks
# Example: https://abc123.ngrok.io/webhook/twilio/voice
```

### 2. Demo Mode Testing
```bash
# Test voice call
curl -X POST http://localhost:8080/api/test/twilio/voice \
  -H "Content-Type: application/json" \
  -d '{"from": "+15551234567", "message": "store memory test"}'

# Test SMS
curl -X POST http://localhost:8080/api/test/twilio/sms \
  -H "Content-Type: application/json" \
  -d '{"from": "+15551234567", "message": "MEMORY Test memory"}'

# Check status
curl http://localhost:8080/api/test/twilio/status
```

### 3. Production Testing
1. Configure real Twilio credentials in environment
2. Set webhook URLs in Twilio console
3. Call your Twilio number to test voice
4. Send SMS to test messaging
5. Monitor logs for debugging

## Performance Optimization

### 1. Response Times
- **Target**: < 500ms webhook response
- **Database Queries**: Optimized with indexes
- **Caching**: Redis for frequent lookups
- **Async Processing**: Background jobs for heavy tasks

### 2. Scalability
- **Concurrent Calls**: Support 100+ simultaneous calls
- **Message Queue**: RabbitMQ for SMS processing
- **Load Balancing**: Multiple server instances
- **Auto-scaling**: Based on traffic patterns

### 3. Monitoring
- **Metrics**: Response time, error rate, throughput
- **Alerts**: Slack/email for critical issues
- **Dashboards**: Real-time performance monitoring
- **Logging**: Structured logs with correlation IDs

## Troubleshooting

### Common Issues and Solutions

1. **Webhook Not Receiving Calls**
   - Verify webhook URL is publicly accessible
   - Check Twilio phone number configuration
   - Confirm signature validation is working
   - Review server logs for errors

2. **Transcription Not Working**
   - Ensure transcription is enabled in Twilio
   - Check audio quality requirements
   - Verify language settings
   - Monitor transcription callbacks

3. **SMS Commands Not Recognized**
   - Check command spelling and format
   - Verify case sensitivity handling
   - Test with simple commands first
   - Review SMS parsing logic

4. **Memory Storage Failing**
   - Check database connectivity
   - Verify user permissions
   - Monitor storage quotas
   - Review encryption settings

## Best Practices

1. **Security**
   - Always validate Twilio signatures in production
   - Use environment variables for credentials
   - Implement rate limiting
   - Monitor for suspicious activity

2. **User Experience**
   - Keep voice prompts clear and concise
   - Provide helpful error messages
   - Confirm successful operations
   - Offer command help when needed

3. **Development**
   - Use demo mode for development
   - Test with various phone numbers
   - Handle edge cases gracefully
   - Log all interactions for debugging

4. **Deployment**
   - Use HTTPS for webhooks
   - Set up monitoring and alerts
   - Implement graceful error handling
   - Plan for scaling requirements

---

**Need Help?** Check the [Twilio Setup Guide](./TWILIO_SETUP_GUIDE.md) for configuration instructions or test the features using the demo endpoints.