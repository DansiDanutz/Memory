# 🎙️ Voice Authentication Setup Guide

## Overview

The Voice Authentication System provides biometric voice-based authentication for the Memory App, enabling secure access to memories through voice verification. This system uses advanced speaker recognition technology to verify user identity.

## Features

### Core Capabilities
- **Voice Enrollment**: Register voice profiles with 3 sample recordings
- **Voice Verification**: Authenticate users through voice biometrics
- **Multi-Factor Authentication**: Challenge questions for medium confidence
- **Session Management**: Secure sessions with expiration and activity tracking
- **Access Control**: Different memory access levels based on authentication confidence
- **Profile Management**: Support multiple voice profiles per user
- **Audit Logging**: Complete authentication attempt history

### Security Features
- **Confidence Thresholds**:
  - High (≥0.85): Full access to all memories
  - Medium (0.70-0.85): Challenge required for sensitive data
  - Low (0.55-0.70): Limited access to family memories only
  - Failed (<0.55): Access denied

- **Rate Limiting**: 3 attempts per minute per user
- **Session Timeout**: 30-minute default expiration
- **Encrypted Storage**: Voice embeddings encrypted with Fernet
- **Audit Trail**: All authentication attempts logged

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client Application                    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Voice Auth API Endpoints                    │
│  /api/voice-auth/enroll, /api/voice-auth/verify, etc.  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│           Voice Authentication Service                   │
│  • Enrollment Management                                 │
│  • Voice Verification                                    │
│  • Challenge System                                      │
│  • Session Management                                    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Data Storage                           │
│  • Voice Profiles (encrypted embeddings)                │
│  • Authentication Sessions                               │
│  • Audit Logs                                           │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints

### Enrollment Endpoints

#### Start Enrollment
```http
POST /api/voice-auth/enroll/start
Content-Type: application/json

{
  "user_id": "user123",
  "display_name": "John Doe"
}

Response:
{
  "success": true,
  "enrollment_id": "enroll_abc123def456",
  "status": "initialized",
  "required_samples": 3,
  "instructions": "Please provide 3 voice samples...",
  "expires_at": "2025-09-13T11:00:00Z"
}
```

#### Submit Voice Sample
```http
POST /api/voice-auth/enroll/sample
Content-Type: multipart/form-data

enrollment_id: enroll_abc123def456
audio: [binary audio file]
device_hint: iPhone

Response:
{
  "success": true,
  "status": "collecting",
  "samples_collected": 1,
  "samples_remaining": 2,
  "message": "Sample 1 recorded. Please provide 2 more sample(s)."
}
```

### Verification Endpoints

#### Verify Voice
```http
POST /api/voice-auth/verify
Content-Type: multipart/form-data

user_id: user123
audio: [binary audio file]

Response (High Confidence):
{
  "success": true,
  "session_id": "session_xyz789",
  "confidence_score": 0.92,
  "authentication_level": "high",
  "access_level": "full",
  "message": "Voice authenticated successfully",
  "authorized_categories": ["all"]
}

Response (Medium Confidence):
{
  "success": false,
  "session_id": "session_xyz789",
  "confidence_score": 0.75,
  "authentication_level": "medium",
  "challenge_required": true,
  "challenge_token": "token_abc123",
  "message": "Additional verification required"
}
```

#### Get Challenge Question
```http
GET /api/voice-auth/challenge?session_id=session_xyz789

Response:
{
  "success": true,
  "challenge_token": "token_abc123",
  "question": "What year were you born?",
  "question_type": "year",
  "attempts_remaining": 3
}
```

#### Answer Challenge
```http
POST /api/voice-auth/challenge/answer
Content-Type: application/json

{
  "session_id": "session_xyz789",
  "challenge_token": "token_abc123",
  "answer": "1990"
}

Response:
{
  "success": true,
  "message": "Challenge completed successfully",
  "access_level": "full",
  "authorized_categories": ["all"]
}
```

### Session & Access Endpoints

#### Check Session Status
```http
GET /api/voice-auth/status?session_id=session_xyz789

Response:
{
  "success": true,
  "session_id": "session_xyz789",
  "user_id": "user123",
  "status": "authenticated",
  "authentication_level": "high",
  "access_level": "full",
  "authorized_categories": [],
  "created_at": "2025-09-13T10:00:00Z",
  "expires_at": "2025-09-13T10:30:00Z",
  "challenge_required": false
}
```

#### Validate Memory Access
```http
POST /api/voice-auth/validate-access
Content-Type: application/json

{
  "session_id": "session_xyz789",
  "memory_category": "super_secret"
}

Response:
{
  "success": true,
  "access_granted": true,
  "reason": "Full access granted",
  "access_level": "full",
  "session_expires_at": "2025-09-13T10:30:00Z"
}
```

### Profile Management

#### List Voice Profiles
```http
GET /api/voice-auth/profiles?user_id=user123

Response:
{
  "success": true,
  "profiles": [
    {
      "profile_id": "profile_abc123",
      "display_name": "John Doe",
      "created_at": "2025-09-13T09:00:00Z",
      "updated_at": "2025-09-13T09:00:00Z",
      "is_primary": true,
      "is_active": true,
      "enrollment_samples": 3,
      "confidence_threshold": 0.85,
      "device_hints": ["iPhone", "MacBook Pro"]
    }
  ],
  "count": 1
}
```

#### Delete Voice Profile
```http
DELETE /api/voice-auth/profiles/profile_abc123?user_id=user123

Response:
{
  "success": true,
  "message": "Voice profile \"John Doe\" deleted successfully"
}
```

### Monitoring & Testing

#### Get Authentication Logs
```http
GET /api/voice-auth/logs?user_id=user123&limit=10

Response:
{
  "success": true,
  "logs": [
    {
      "attempt_id": "attempt_xyz",
      "user_id": "user123",
      "timestamp": "2025-09-13T10:00:00Z",
      "confidence_score": 0.92,
      "authentication_level": "high",
      "success": true,
      "failure_reason": null,
      "ip_address": "192.168.1.1",
      "device_info": "Mozilla/5.0...",
      "challenge_required": false,
      "challenge_passed": false
    }
  ],
  "count": 1
}
```

#### Get Statistics
```http
GET /api/voice-auth/stats

Response:
{
  "success": true,
  "statistics": {
    "total_profiles": 42,
    "total_users": 35,
    "active_sessions": 5,
    "total_attempts": 156,
    "successful_attempts": 134,
    "success_rate": "85.90%",
    "demo_mode": true
  }
}
```

## Enrollment Flow

### Step 1: Initialize Enrollment
```javascript
const response = await fetch('/api/voice-auth/enroll/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user123',
    display_name: 'John Doe'
  })
});
const { enrollment_id } = await response.json();
```

### Step 2: Collect Voice Samples
```javascript
// Record 3 voice samples (3-5 seconds each)
for (let i = 0; i < 3; i++) {
  const audioBlob = await recordAudio(); // Your recording function
  
  const formData = new FormData();
  formData.append('enrollment_id', enrollment_id);
  formData.append('audio', audioBlob, 'sample.wav');
  formData.append('device_hint', navigator.userAgent);
  
  const response = await fetch('/api/voice-auth/enroll/sample', {
    method: 'POST',
    body: formData
  });
  
  const result = await response.json();
  console.log(`Sample ${i+1}/3 submitted`);
}
```

### Step 3: Profile Created
Once all samples are submitted, the voice profile is automatically created and activated.

## Verification Flow

### Step 1: Submit Voice for Verification
```javascript
const audioBlob = await recordAudio(); // Record voice

const formData = new FormData();
formData.append('user_id', 'user123');
formData.append('audio', audioBlob, 'verify.wav');

const response = await fetch('/api/voice-auth/verify', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

### Step 2: Handle Response Based on Confidence

#### High Confidence (≥0.85)
```javascript
if (result.success) {
  // User authenticated with high confidence
  sessionStorage.setItem('auth_session', result.session_id);
  sessionStorage.setItem('access_level', result.access_level);
  // Grant full access
}
```

#### Medium Confidence (0.70-0.85)
```javascript
if (result.challenge_required) {
  // Get challenge question
  const challengeResponse = await fetch(
    `/api/voice-auth/challenge?session_id=${result.session_id}`
  );
  const challenge = await challengeResponse.json();
  
  // Present question to user and get answer
  const answer = prompt(challenge.question);
  
  // Submit answer
  const answerResponse = await fetch('/api/voice-auth/challenge/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: result.session_id,
      challenge_token: challenge.challenge_token,
      answer: answer
    })
  });
  
  const answerResult = await answerResponse.json();
  if (answerResult.success) {
    // Challenge passed, grant access
  }
}
```

#### Low Confidence or Failed
```javascript
if (!result.success && !result.challenge_required) {
  // Authentication failed
  alert('Voice not recognized. Please try again or use alternative authentication.');
}
```

## Memory Access Integration

### Check Access Before Retrieving Memory
```javascript
async function retrieveMemory(sessionId, memoryCategory) {
  // Validate access first
  const accessResponse = await fetch('/api/voice-auth/validate-access', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      memory_category: memoryCategory
    })
  });
  
  const access = await accessResponse.json();
  
  if (access.access_granted) {
    // Retrieve memory
    return await fetchMemory(memoryCategory);
  } else {
    // Handle access denied
    console.log(`Access denied: ${access.reason}`);
    return null;
  }
}
```

## Testing

### Quick Test Endpoint
```bash
# Test enrollment
curl -X POST http://localhost:8080/api/voice-auth/demo/quick-test \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "action": "enroll"}'

# Test verification
curl -X POST http://localhost:8080/api/voice-auth/demo/quick-test \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "action": "verify"}'
```

### Generate Demo Audio Sample
```bash
curl -O http://localhost:8080/api/voice-auth/demo/generate-sample?text=Hello%20World
```

### Run Complete Test Suite
```bash
cd memory-system
python test_voice_authentication.py
```

## Production Requirements

### Speaker Recognition Models
For production deployment, replace the demo embedding extraction with real speaker recognition models:

1. **ECAPA-TDNN** (Recommended)
   - State-of-the-art speaker verification
   - Available via SpeechBrain or Hugging Face
   - Excellent accuracy and speed

2. **X-Vector**
   - Mature and widely tested
   - Good balance of accuracy and efficiency
   - Available in Kaldi and PyTorch implementations

3. **Resemblyzer**
   - Python library for speaker diarization
   - Easy integration
   - Good for quick prototyping

### Audio Requirements
- **Sample Rate**: 16kHz minimum (recommended: 16-48kHz)
- **Duration**: 3-5 seconds per sample
- **Format**: WAV, MP3, or raw PCM
- **Quality**: Clear speech without excessive background noise

### Security Best Practices

1. **Voice Sample Collection**
   - Collect samples in different environments
   - Use anti-spoofing detection
   - Verify liveness (e.g., random phrase repetition)

2. **Storage Security**
   - Encrypt all voice embeddings
   - Rotate encryption keys regularly
   - Store embeddings separately from user data

3. **Authentication Flow**
   - Implement progressive authentication
   - Use multi-factor for sensitive operations
   - Log all authentication attempts

4. **Privacy Compliance**
   - Obtain explicit consent for biometric data
   - Comply with GDPR/CCPA requirements
   - Provide data deletion options

## Troubleshooting

### Common Issues

#### Low Confidence Scores
- **Cause**: Poor audio quality or background noise
- **Solution**: Ensure clear audio recording, minimize background noise

#### Enrollment Failures
- **Cause**: Inconsistent voice samples
- **Solution**: Record samples in similar conditions, speak naturally

#### Session Expiration
- **Cause**: Session timeout after 30 minutes
- **Solution**: Re-authenticate or extend session timeout

#### Rate Limiting
- **Cause**: Too many attempts in short period
- **Solution**: Wait 60 seconds before retrying

### Debug Mode
Enable detailed logging:
```python
# In voice_authentication_service.py
logging.basicConfig(level=logging.DEBUG)
```

## API Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (missing parameters) |
| 401 | Authentication failed |
| 403 | Rate limit exceeded |
| 404 | Resource not found |
| 500 | Internal server error |

## Configuration

### Environment Variables
```bash
# Master encryption key (auto-generated if not set)
VOICE_AUTH_MASTER_KEY=your-secret-key

# Confidence thresholds
VOICE_AUTH_THRESHOLD_HIGH=0.85
VOICE_AUTH_THRESHOLD_MEDIUM=0.70
VOICE_AUTH_THRESHOLD_LOW=0.55

# Session settings
VOICE_AUTH_SESSION_TIMEOUT=1800  # 30 minutes
VOICE_AUTH_MAX_ATTEMPTS=3

# Rate limiting
VOICE_AUTH_RATE_LIMIT_WINDOW=60  # seconds
VOICE_AUTH_RATE_LIMIT_MAX=3      # attempts
```

## Support & Resources

- **Documentation**: This guide
- **Test Suite**: `test_voice_authentication.py`
- **Demo Endpoint**: `/api/voice-auth/demo/quick-test`
- **Health Check**: `/api/voice-auth/health`
- **Statistics**: `/api/voice-auth/stats`

## License

This voice authentication system is part of the Memory App and follows the same licensing terms.