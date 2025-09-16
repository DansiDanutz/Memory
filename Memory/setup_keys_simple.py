"""Simple API Key Setup Script for Windows"""

import os
import re
from pathlib import Path

def update_env_file():
    """Update .env file with Claude API key"""
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print("ERROR: .env file not found!")
        return False
    
    # Read current .env content
    with open(env_path, 'r') as f:
        content = f.read()
    
    print("\n" + "="*50)
    print("API KEY CONFIGURATION")
    print("="*50)
    
    # Get Claude API key
    print("\nEnter your Claude API key (starts with sk-ant-...)")
    claude_key = input("Claude API Key: ").strip()
    
    if claude_key:
        # Replace the Claude API key
        pattern = r'CLAUDE_API_KEY=.*'
        replacement = f'CLAUDE_API_KEY={claude_key}'
        
        if 'CLAUDE_API_KEY=' in content:
            content = re.sub(pattern, replacement, content)
            print("\nSUCCESS: Claude API key updated!")
        else:
            # Add it if not found
            content += f"\nCLAUDE_API_KEY={claude_key}\n"
            print("\nSUCCESS: Claude API key added!")
        
        # Write updated content
        with open(env_path, 'w') as f:
            f.write(content)
        
        print("\nConfiguration saved to .env file")
        print("\nTo start the server, run:")
        print("python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload")
        return True
    else:
        print("\nNo key entered. No changes made.")
        return False

if __name__ == "__main__":
    try:
        success = update_env_file()
        if success:
            print("\nSetup completed successfully!")
    except Exception as e:
        print(f"\nError: {e}")
    
    input("\nPress Enter to exit...")