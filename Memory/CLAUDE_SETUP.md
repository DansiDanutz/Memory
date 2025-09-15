# Claude AI Integration Setup

## Overview
Your Memory App now includes Claude AI integration for advanced text processing, analysis, and generation capabilities.

## Configuration

### 1. Environment Variables
Add the following to your `.env` file:

```bash
# Claude AI Configuration
CLAUDE_API_KEY=your_claude_api_key_here
```

### 2. Get Claude API Key
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key and add it to your `.env` file

### 3. Install Dependencies
```bash
cd Memory
pip install -r requirements.txt
```

## Available Endpoints

### Claude Service Status
- **GET** `/claude/status` - Check if Claude service is available
- **GET** `/claude/health` - Health check for Claude AI service

### Message Analysis
- **POST** `/claude/analyze`
  ```json
  {
    "message": "I'm really frustrated with this issue",
    "context": "Customer support conversation"
  }
  ```

### Response Generation
- **POST** `/claude/generate`
  ```json
  {
    "message": "How can I reset my password?",
    "context": "User needs help",
    "tone": "helpful"
  }
  ```

### Conversation Summarization
- **POST** `/claude/summarize`
  ```json
  {
    "messages": [
      {"sender": "User", "content": "I need help with my account"},
      {"sender": "Support", "content": "I can help you with that"}
    ]
  }
  ```

### Memory Extraction
- **POST** `/claude/extract-memory`
  ```json
  {
    "text": "My birthday is on March 15th and I prefer email notifications"
  }
  ```

## Integration Examples

### In Python Code
```python
from app.claude_service import analyze_message, generate_response

# Analyze a message
result = await analyze_message("I'm having trouble logging in")

# Generate a response
response = await generate_response(
    message="How do I change my password?",
    tone="helpful"
)
```

### WhatsApp Integration
The Claude service can be integrated into your WhatsApp webhook to:
- Analyze incoming messages for sentiment and intent
- Generate intelligent responses
- Extract important information for memory storage
- Summarize conversation threads

## Features

### Message Analysis
- Sentiment analysis (positive, negative, neutral)
- Intent detection (question, request, complaint, etc.)
- Key topic extraction
- Urgency level assessment
- Response type suggestions

### Response Generation
- Context-aware responses
- Customizable tone (helpful, professional, casual)
- WhatsApp-optimized length
- Natural language generation

### Conversation Summarization
- Main topics identification
- Key decisions tracking
- Action items extraction
- Overall sentiment analysis

### Memory Extraction
- Important facts identification
- Personal preferences detection
- Date and appointment extraction
- Contact information parsing
- Decision tracking

## Error Handling
- Graceful degradation when Claude API is unavailable
- Detailed error messages and logging
- Service availability checks
- Automatic retry mechanisms

## Security
- API key stored in environment variables
- No sensitive data logged
- Secure API communication
- Rate limiting considerations

## Testing
```bash
# Test Claude service availability
curl http://localhost:8000/claude/status

# Test message analysis
curl -X POST http://localhost:8000/claude/analyze \
  -H "Content-Type: application/json" \
  -d '{"message": "I need help with my account"}'
```

## Troubleshooting

### Claude Service Not Available
1. Check if `CLAUDE_API_KEY` is set in your environment
2. Verify the API key is valid
3. Check network connectivity
4. Review application logs for errors

### API Rate Limits
- Claude API has rate limits
- Implement appropriate delays between requests
- Consider caching responses for repeated queries
- Monitor usage in Anthropic Console

## Next Steps
1. Set up your Claude API key
2. Test the endpoints
3. Integrate Claude analysis into your WhatsApp webhook
4. Customize prompts for your specific use case
5. Implement caching for better performance
