import os
import asyncio
from app.claude_service import claude_service

async def test_claude():
    print("Testing Claude API integration...")
    print("="*50)
    
    # Check if API key is set
    api_key = os.getenv('CLAUDE_API_KEY')
    if api_key:
        print("[OK] CLAUDE_API_KEY is set in environment")
    else:
        print("[ERROR] CLAUDE_API_KEY not found in environment")
        print("   Please add it to Replit Secrets")
    
    # Check if service is available
    available = claude_service.is_available()
    print(f"\nClaude service available: {available}")
    
    if available:
        # Test message analysis
        print("\n" + "="*50)
        print("Testing message analysis...")
        result = await claude_service.analyze_message(
            "Hello, I'm testing Claude integration in Replit!",
            "Testing environment"
        )
        
        if 'error' in result:
            print(f"[ERROR] Error: {result['error']}")
        else:
            print("[OK] Analysis successful!")
            print(f"   Model used: {result.get('model', 'unknown')}")
            
        # Test response generation
        print("\n" + "="*50)
        print("Testing response generation...")
        response = await claude_service.generate_response(
            "What's the weather like today?",
            tone="helpful"
        )
        
        if 'error' in response:
            print(f"[ERROR] Error: {response['error']}")
        else:
            print("[OK] Response generation successful!")
            print(f"   Generated: {response.get('response', '')[:100]}...")
    else:
        print("\n[WARNING] Claude service not available")
        print("To enable Claude integration:")
        print("1. Go to https://console.anthropic.com/")
        print("2. Create an API key")
        print("3. In Replit, click the Secrets tab")
        print("4. Add CLAUDE_API_KEY with your key value")

if __name__ == "__main__":
    asyncio.run(test_claude())