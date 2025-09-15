#!/usr/bin/env python3
"""
Webhook Configuration Helper for Memory App
Provides exact webhook URLs and testing tools
"""

import os
import json
import requests
from datetime import datetime

# Get environment variables
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN', 'MemoryApp2025')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Public URL for webhooks - Gets from environment or uses localhost for testing
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:8080')

print("=" * 70)
print("🚀 WEBHOOK CONFIGURATION HELPER FOR MEMORY APP")
print("=" * 70)
print()

print("📍 YOUR WEBHOOK ENDPOINTS:")
print("-" * 70)
print()

# WhatsApp Configuration
print("1️⃣ WHATSAPP BUSINESS API CONFIGURATION")
print("   Go to: https://developers.facebook.com/apps/")
print("   Navigate to: Your App → WhatsApp → Configuration")
print()
print("   📌 Webhook URL:")
print(f"   {PUBLIC_URL}/webhook/whatsapp")
print()
print("   🔑 Verify Token:")
if WHATSAPP_VERIFY_TOKEN and WHATSAPP_VERIFY_TOKEN != 'MemoryApp2025':
    print(f"   ***configured (hidden for security)***")
else:
    print(f"   {WHATSAPP_VERIFY_TOKEN} (default - configure in production)")
print()
print("   ✅ Subscribe to these webhook fields:")
print("   • messages")
print("   • message_status")
print("   • message_template_status_update")
print()
print("-" * 70)
print()

# Twilio Configuration
print("2️⃣ TWILIO CONFIGURATION")
print("   Go to: https://www.twilio.com/console/phone-numbers/")
print("   Click on your phone number: " + TWILIO_PHONE_NUMBER)
print()
print("   📱 Voice & Fax Section:")
print("   • A CALL COMES IN:")
print(f"     Webhook: {PUBLIC_URL}/webhook/twilio/voice")
print("     HTTP Method: POST")
print()
print("   💬 Messaging Section:")
print("   • A MESSAGE COMES IN:")
print(f"     Webhook: {PUBLIC_URL}/webhook/twilio/sms")
print("     HTTP Method: POST")
print()
print("-" * 70)
print()

# Test the local webhook server
print("3️⃣ TESTING WEBHOOK SERVER STATUS")
print("-" * 70)
print()

try:
    # Test health endpoint
    response = requests.get("http://localhost:8080/health", timeout=2)
    if response.status_code == 200:
        print("✅ Webhook server is running and healthy!")
        print(f"   Response: {response.json()}")
    else:
        print("⚠️ Webhook server returned status:", response.status_code)
except Exception as e:
    print("❌ Cannot connect to webhook server on port 8080")
    print("   Make sure the webhook server is running!")
    print(f"   Error: {e}")

print()

# Test WhatsApp webhook verification
print("4️⃣ TESTING WHATSAPP WEBHOOK VERIFICATION")
print("-" * 70)
print()

try:
    # Test WhatsApp webhook verification
    verify_url = f"http://localhost:8080/webhook/whatsapp?hub.mode=subscribe&hub.verify_token={WHATSAPP_VERIFY_TOKEN}&hub.challenge=test_challenge_123"
    response = requests.get(verify_url, timeout=2)
    
    if response.status_code == 200:
        print("✅ WhatsApp webhook verification successful!")
        print(f"   Challenge response: {response.text}")
    else:
        print(f"⚠️ WhatsApp webhook verification failed with status: {response.status_code}")
        print(f"   Response: {response.text}")
        print()
        print("   Make sure WHATSAPP_VERIFY_TOKEN matches what you'll")
        print("   enter in the Meta Business Dashboard!")
except Exception as e:
    print(f"❌ Error testing WhatsApp webhook: {e}")

print()
print("=" * 70)
print("📋 NEXT STEPS:")
print("=" * 70)
print()
print("1. Copy the webhook URLs above")
print("2. Configure them in Meta Business Dashboard and Twilio Console")
print("3. Save the configurations")
print("4. Send a test message to verify everything works!")
print()
print("💡 TIP: If webhooks aren't working, check that:")
print("   • Port 8080 is accessible from the internet")
print("   • Your Replit is running and not sleeping")
print("   • The verify tokens match exactly")
print()
print("🎉 Once configured, your Memory App will automatically:")
print("   • Store all WhatsApp messages as memories")
print("   • Transcribe and save voice calls")
print("   • Process SMS messages")
print("   • Respond with AI-generated replies")
print()