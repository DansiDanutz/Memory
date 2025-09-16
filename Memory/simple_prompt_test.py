"""
Simple test to verify API connection
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Test basic API connection
api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")

if api_key:
    print("[OK] API Key found!")
    print(f"Key starts with: {api_key[:20]}...")

    # Try basic import
    try:
        import anthropic
        print("[OK] Anthropic library imported successfully")

        # Try creating client with minimal config
        try:
            # Use the simplest initialization
            os.environ["ANTHROPIC_API_KEY"] = api_key
            client = anthropic.Anthropic()
            print("[OK] Client created successfully!")

            # Test with a simple prompt
            print("\nTesting API with simple prompt...")
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheaper model for testing
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": "Say 'Hello, prompt generator is working!' in 5 words or less."
                }]
            )
            print(f"[OK] API Response: {response.content[0].text}")

        except Exception as e:
            print(f"[ERROR] Error creating client: {e}")
            print("\nTrying alternative approach...")

    except ImportError as e:
        print(f"[ERROR] Error importing anthropic: {e}")
else:
    print("[ERROR] No API key found in .env file")