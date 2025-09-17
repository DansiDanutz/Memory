#!/usr/bin/env python3
"""
Generate Fernet Encryption Key for MemoApp
Generates a secure encryption key for production use
"""

import os
import sys
import base64
from cryptography.fernet import Fernet
from pathlib import Path

def generate_key():
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key()

def save_to_env_file(key: bytes, env_file: str = ".env"):
    """Save key to .env file"""
    key_str = key.decode('utf-8')
    
    # Check if .env exists
    env_path = Path(env_file)
    lines = []
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    
    # Update or add ENCRYPTION_MASTER_KEY
    key_found = False
    for i, line in enumerate(lines):
        if line.startswith('ENCRYPTION_MASTER_KEY='):
            lines[i] = f'ENCRYPTION_MASTER_KEY={key_str}\n'
            key_found = True
            break
    
    if not key_found:
        lines.append(f'ENCRYPTION_MASTER_KEY={key_str}\n')
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Key saved to {env_file}")

def main():
    """Main function"""
    print("🔐 MemoApp Encryption Key Generator")
    print("=" * 40)
    
    # Generate new key
    key = generate_key()
    key_str = key.decode('utf-8')
    
    print(f"\n📌 Generated Encryption Key:")
    print(f"   {key_str}")
    
    print("\n📝 Usage Options:")
    print("1. Set as environment variable:")
    print(f"   export ENCRYPTION_MASTER_KEY={key_str}")
    
    print("\n2. Add to .env file:")
    print(f"   ENCRYPTION_MASTER_KEY={key_str}")
    
    print("\n3. Add to Docker Compose:")
    print(f"   environment:")
    print(f"     - ENCRYPTION_MASTER_KEY={key_str}")
    
    # Ask if user wants to save to .env
    save_choice = input("\n💾 Save to .env file? (y/n): ").lower().strip()
    
    if save_choice == 'y':
        env_file = input("Enter .env file path (default: .env): ").strip() or ".env"
        save_to_env_file(key, env_file)
        print(f"\n⚠️  Important: Add {env_file} to .gitignore to prevent committing secrets!")
        
        # Check if .gitignore exists and update it
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                gitignore_content = f.read()
            
            if env_file not in gitignore_content:
                with open(gitignore_path, 'a') as f:
                    f.write(f"\n# Environment files\n{env_file}\n.env.*\n")
                print(f"✅ Added {env_file} to .gitignore")
    
    print("\n🔒 Security Recommendations:")
    print("   • Use different keys for development and production")
    print("   • Store production keys in secure secret management systems")
    print("   • Rotate keys periodically")
    print("   • Never commit keys to version control")
    
    print("\n✨ Key generation complete!")

if __name__ == "__main__":
    main()