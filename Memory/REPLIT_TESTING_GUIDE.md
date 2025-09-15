# Replit Testing Guide - Memory App with Claude Integration

## 🚀 Quick Start in Replit

Since you've already set the Claude API key in Replit Secrets, here's how to test everything:

### 1. Import to Replit
1. Go to [Replit](https://replit.com)
2. Click "Create Repl"
3. Choose "Import from GitHub"
4. Enter: `https://github.com/DansiDanutz/Memory`
5. Click "Import from GitHub"

### 2. Verify Environment
In Replit console, check your setup:
```bash
# Check if Claude API key is set
python -c "import os; print('Claude API Key configured:', bool(os.getenv('CLAUDE_API_KEY')))"

# Check Python version
python --version

# List installed packages
pip list | grep -E "(anthropic|fastapi|uvicorn)"
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Test Claude Integration
Create a quick test in Replit console:
```python
# Test Claude service
import asyncio
import os
from app.claude_service import claude_service

async def test_claude():
    print("🧪 Testing Claude Integration in Replit")
    print("=" * 40)
    
    # Check availability
    available = claude_service.is_available()
    print(f"Claude service available: {available}")
    
    if available:
        # Test message analysis
        result = await claude_service.analyze_message(
            "Hello from Replit! This is a test message.",
            "Replit testing environment"
        )
        
        if 'analysis' in result:
            print("✅ Message analysis working!")
            print(f"Analysis preview: {result['analysis'][:100]}...")
        else:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        
        # Test response generation
        response = await claude_service.generate_response(
            "How do I test my Memory App?",
            "Replit deployment",
            "helpful"
        )
        
        if 'response' in response:
            print("✅ Response generation working!")
            print(f"Response: {response['response']}")
        else:
            print(f"❌ Response failed: {response.get('error', 'Unknown error')}")
    
    print("🎉 Claude integration test completed!")

# Run the test
asyncio.run(test_claude())
```

### 5. Start the Server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 6. Test API Endpoints
Once the server is running, test these endpoints in a new Replit tab:

#### Check Claude Status
```bash
curl https://your-repl-name.your-username.repl.co/claude/status
```

#### Test Message Analysis
```bash
curl -X POST https://your-repl-name.your-username.repl.co/claude/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am excited about this Memory App with Claude integration!",
    "context": "Testing from Replit"
  }'
```

#### Test Response Generation
```bash
curl -X POST https://your-repl-name.your-username.repl.co/claude/generate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How does the Memory App work?",
    "context": "User question",
    "tone": "helpful"
  }'
```

#### Test Memory Extraction
```bash
curl -X POST https://your-repl-name.your-username.repl.co/claude/extract-memory \
  -H "Content-Type: application/json" \
  -d '{
    "text": "My name is John, I live in New York, and my birthday is March 15th. I prefer email notifications."
  }'
```

### 7. Expected Results

#### Successful Claude Status Response:
```json
{
  "success": true,
  "data": {
    "available": true
  },
  "available": true
}
```

#### Successful Analysis Response:
```json
{
  "success": true,
  "data": {
    "analysis": "{\n  \"sentiment\": \"positive\",\n  \"intent\": \"information_sharing\",\n  \"key_topics\": [\"Memory App\", \"Claude integration\", \"excitement\"],\n  \"urgency_level\": \"low\",\n  \"suggested_response_type\": \"acknowledgment_and_information\"\n}",
    "available": true,
    "model": "claude-3-haiku-20240307"
  },
  "available": true
}
```

### 8. Troubleshooting

#### If Claude API key is not found:
1. Go to Replit Secrets tab
2. Verify `CLAUDE_API_KEY` is set correctly
3. Restart your Repl

#### If dependencies are missing:
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

#### If server won't start:
```bash
# Check for port conflicts
netstat -tulpn | grep :8000

# Try different port
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

### 9. Production Deployment

#### Enable Always On (Replit Hacker Plan):
1. Go to your Repl settings
2. Enable "Always On"
3. Your app will stay running 24/7

#### Custom Domain (Optional):
1. In deployment settings
2. Add your custom domain
3. Update webhook URLs accordingly

### 10. Monitoring

#### Check Logs:
```bash
# View application logs
tail -f /tmp/replit.log

# Check Claude API usage
# Visit https://console.anthropic.com/settings/usage
```

#### Health Checks:
```bash
# Main app health
curl https://your-repl-name.your-username.repl.co/health

# Claude service health
curl https://your-repl-name.your-username.repl.co/claude/health
```

## 🎯 Success Indicators

✅ **Claude API Key**: Environment variable is set  
✅ **Dependencies**: All packages installed successfully  
✅ **Server**: FastAPI server starts without errors  
✅ **Claude Status**: `/claude/status` returns `available: true`  
✅ **API Endpoints**: All Claude endpoints respond correctly  
✅ **Integration**: Message analysis and response generation work  

## 🚀 Next Steps

1. **Test WhatsApp Integration**: Set up WhatsApp webhook
2. **Customize Prompts**: Modify Claude prompts for your use case
3. **Add Caching**: Implement Redis caching for better performance
4. **Monitor Usage**: Track Claude API usage and costs
5. **Scale Up**: Enable Always On for production use

Your Memory App with Claude AI integration is now ready for production use in Replit! 🎉
