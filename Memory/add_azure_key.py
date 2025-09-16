"""
Add Azure Speech Services Key to .env
"""

import os
import re
from pathlib import Path

def add_azure_key():
    print("\n" + "="*60)
    print("  AZURE SPEECH SERVICES SETUP")
    print("="*60)
    print("\nFollow the guide in AZURE_SETUP.md to get your key")
    print("Or if you already have one, enter it below:\n")

    # Get Azure key
    azure_key = input("Enter your Azure Speech key (or press Enter to skip): ").strip()

    if not azure_key:
        print("\nSkipped. You can add it later.")
        return False

    # Get region
    print("\nCommon regions: eastus, westus, westeurope, northeurope, southeastasia")
    region = input("Enter your Azure region (default: eastus): ").strip()
    if not region:
        region = "eastus"

    # Read current .env
    env_path = Path(".env")
    with open(env_path, 'r') as f:
        content = f.read()

    # Update Azure key
    content = re.sub(
        r'AZURE_SPEECH_KEY=.*',
        f'AZURE_SPEECH_KEY={azure_key}',
        content
    )

    # Update region
    content = re.sub(
        r'AZURE_SPEECH_REGION=.*',
        f'AZURE_SPEECH_REGION={region}',
        content
    )

    # Write back
    with open(env_path, 'w') as f:
        f.write(content)

    print("\n" + "="*60)
    print("  SUCCESS! Azure Speech Services configured!")
    print("="*60)
    print(f"\n  Key: {azure_key[:20]}...")
    print(f"  Region: {region}")
    print("\nYour app now has voice capabilities!")
    print("\nTesting Azure connection...")

    # Quick test
    import requests
    try:
        headers = {'Ocp-Apim-Subscription-Key': azure_key}
        url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        response = requests.post(url, headers=headers, timeout=5)

        if response.status_code == 200:
            print("[OK] Azure connection successful!")
        else:
            print(f"[WARNING] Got status {response.status_code} - check your key")
    except Exception as e:
        print(f"[ERROR] Could not connect: {e}")

    return True

if __name__ == "__main__":
    add_azure_key()
    input("\nPress Enter to exit...")