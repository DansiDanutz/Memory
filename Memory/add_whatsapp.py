"""
WhatsApp Business API Setup Script
"""

import os
import re
from pathlib import Path

def add_whatsapp_config():
    print("\n" + "="*60)
    print("  WHATSAPP BUSINESS API SETUP")
    print("="*60)
    print("\nFollow the guide in WHATSAPP_SETUP.md to get your credentials")
    print("Or if you already have them, enter below:\n")

    # Get Meta Access Token
    print("Step 1: Meta Access Token")
    print("(Get from: developers.facebook.com > Your App > WhatsApp > API Setup)")
    access_token = input("Enter META_ACCESS_TOKEN (starts with 'EAAI'): ").strip()

    if not access_token:
        print("\nSkipped. You can add it later.")
        return False

    # Get Phone Number ID
    print("\nStep 2: WhatsApp Phone Number ID")
    print("(15-digit number from API Setup page)")
    phone_id = input("Enter WA_PHONE_NUMBER_ID: ").strip()

    if not phone_id:
        print("\nPhone Number ID is required!")
        return False

    # Get Public URL (optional for local testing)
    print("\nStep 3: Public URL (optional for local testing)")
    print("(Your app's public URL for webhooks, or press Enter to skip)")
    public_url = input("Enter APP_PUBLIC_URL (or press Enter): ").strip()

    # Read current .env
    env_path = Path(".env")
    with open(env_path, 'r') as f:
        content = f.read()

    # Update Meta Access Token
    content = re.sub(
        r'META_ACCESS_TOKEN=.*',
        f'META_ACCESS_TOKEN={access_token}',
        content
    )

    # Update Phone Number ID
    content = re.sub(
        r'WA_PHONE_NUMBER_ID=.*',
        f'WA_PHONE_NUMBER_ID={phone_id}',
        content
    )

    # Update Public URL if provided
    if public_url:
        content = re.sub(
            r'APP_PUBLIC_URL=.*',
            f'APP_PUBLIC_URL={public_url}',
            content
        )

    # Also update backward compatibility variables
    content = re.sub(
        r'WHATSAPP_ACCESS_TOKEN=.*',
        f'WHATSAPP_ACCESS_TOKEN={access_token}',
        content
    )

    content = re.sub(
        r'WHATSAPP_PHONE_NUMBER_ID=.*',
        f'WHATSAPP_PHONE_NUMBER_ID={phone_id}',
        content
    )

    # Write back
    with open(env_path, 'w') as f:
        f.write(content)

    print("\n" + "="*60)
    print("  SUCCESS! WhatsApp API configured!")
    print("="*60)
    print(f"\n  Access Token: {access_token[:20]}...")
    print(f"  Phone Number ID: {phone_id}")
    if public_url:
        print(f"  Public URL: {public_url}")

    print("\nTesting WhatsApp connection...")

    # Quick test
    import requests
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"https://graph.facebook.com/v17.0/{phone_id}"
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Connected to WhatsApp number: {data.get('display_phone_number', 'Test Number')}")
            print(f"     Quality rating: {data.get('quality_rating', 'N/A')}")
        elif response.status_code == 401:
            print("[ERROR] Invalid access token")
        elif response.status_code == 404:
            print("[ERROR] Invalid phone number ID")
        else:
            print(f"[WARNING] Got status {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Could not connect: {e}")

    print("\n## Next Steps:")
    print("1. Add your phone number to the test list in Meta dashboard")
    print("2. Send a message to the test number to activate the conversation")
    print("3. Your bot will respond to WhatsApp messages!")

    return True

if __name__ == "__main__":
    add_whatsapp_config()
    input("\nPress Enter to exit...")