"""
Automated API Key Setup Script
This script will help you add your API keys to the .env file
"""

import os
import re
from pathlib import Path
import getpass

def update_env_file():
    """Update .env file with API keys"""

    env_path = Path(".env")

    if not env_path.exists():
        print("❌ .env file not found!")
        print("Creating from template...")
        template_path = Path(".env.example")
        if template_path.exists():
            import shutil
            shutil.copy(template_path, env_path)
        else:
            print("❌ No template found. Creating basic .env file...")
            with open(env_path, 'w') as f:
                f.write("# Environment Configuration\n")

    # Read current .env content
    with open(env_path, 'r') as f:
        content = f.read()

    print("\n" + "="*50)
    print("🔧 API KEY CONFIGURATION WIZARD")
    print("="*50)
    print("\nLeave blank to skip any key\n")

    # Define keys to update
    keys_to_update = {
        'CLAUDE_API_KEY': {
            'prompt': '🤖 Claude API Key (sk-ant-...)',
            'current': re.search(r'CLAUDE_API_KEY=(.+)', content),
            'default': 'your_claude_api_key_here'
        },
        'AZURE_SPEECH_KEY': {
            'prompt': '🎤 Azure Speech Key',
            'current': re.search(r'AZURE_SPEECH_KEY=(.+)', content),
            'default': 'your_azure_speech_key_here'
        },
        'META_ACCESS_TOKEN': {
            'prompt': '📱 WhatsApp/Meta Access Token',
            'current': re.search(r'META_ACCESS_TOKEN=(.+)', content),
            'default': 'your_meta_access_token_here'
        },
        'OPENAI_API_KEY': {
            'prompt': '🧠 OpenAI API Key (optional)',
            'current': re.search(r'OPENAI_API_KEY=(.+)', content),
            'default': 'your_openai_api_key_here'
        }
    }

    updates_made = False

    for key_name, key_info in keys_to_update.items():
        current_value = key_info['current'].group(1) if key_info['current'] else None

        # Show current status
        if current_value and current_value != key_info['default']:
            print(f"\n✅ {key_name} is already set (starts with {current_value[:10]}...)")
            update = input("   Do you want to update it? (y/N): ").lower()
            if update != 'y':
                continue
        elif current_value == key_info['default']:
            print(f"\n⚠️  {key_name} is not configured")
        else:
            print(f"\n❌ {key_name} not found in .env")

        # Get new value
        if 'API_KEY' in key_name or 'TOKEN' in key_name:
            # Use getpass for sensitive input
            new_value = getpass.getpass(f"   Enter {key_info['prompt']}: ").strip()
        else:
            new_value = input(f"   Enter {key_info['prompt']}: ").strip()

        if new_value:
            # Update or add the key
            if key_info['current']:
                # Replace existing
                pattern = f"{key_name}=.+"
                replacement = f"{key_name}={new_value}"
                content = re.sub(pattern, replacement, content)
            else:
                # Add new key
                # Try to add it in the right section
                if 'CLAUDE' in key_name:
                    section_marker = "# REQUIRED: Claude AI Configuration"
                elif 'AZURE' in key_name:
                    section_marker = "# REQUIRED: Azure Speech Services Configuration"
                elif 'META' in key_name or 'WHATSAPP' in key_name:
                    section_marker = "# REQUIRED: WhatsApp Cloud API Configuration"
                else:
                    section_marker = "# OPTIONAL:"

                if section_marker in content:
                    # Add after section marker
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if section_marker in line:
                            # Insert after the section header comments
                            insert_pos = i + 3  # Skip section header and separator
                            if insert_pos < len(lines):
                                lines.insert(insert_pos, f"{key_name}={new_value}")
                                content = '\n'.join(lines)
                                break
                else:
                    # Just append at the end
                    content += f"\n{key_name}={new_value}\n"

            updates_made = True
            print(f"   ✅ {key_name} updated successfully!")

    if updates_made:
        # Write updated content
        with open(env_path, 'w') as f:
            f.write(content)

        print("\n" + "="*50)
        print("✅ Configuration updated successfully!")
        print("="*50)

        # Check if server is running
        import subprocess
        try:
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            if ':8080' in result.stdout:
                print("\n🔄 Server detected on port 8080 - it should auto-reload with new keys")
            else:
                print("\n💡 To start the server, run:")
                print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload")
        except:
            pass

        print("\n📊 Access your dashboard at: http://localhost:8080/dashboard")
    else:
        print("\n❌ No updates were made")

    # Verify Claude key specifically
    with open(env_path, 'r') as f:
        final_content = f.read()

    if 'CLAUDE_API_KEY=' in final_content:
        claude_match = re.search(r'CLAUDE_API_KEY=(.+)', final_content)
        if claude_match and claude_match.group(1) != 'your_claude_api_key_here':
            print("\n✅ Claude API key is configured and ready!")
        else:
            print("\n⚠️  Claude API key still needs to be configured")
            print("   You can run this script again to add it")

if __name__ == "__main__":
    try:
        # Change to Memory directory if not already there
        if not Path(".env").exists() and Path("Memory/.env").exists():
            os.chdir("Memory")

        update_env_file()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease make sure you're in the Memory directory")

    input("\n\nPress Enter to exit...")