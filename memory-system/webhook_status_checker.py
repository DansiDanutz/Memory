#!/usr/bin/env python3
"""
Comprehensive Status Checker for Memory App Webhooks
"""

import os
import json
import requests
from datetime import datetime
import time

# Environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_BUSINESS_API_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')

# Public URL
PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:8080')

def check_status(name, condition, details=""):
    """Print status check result"""
    if condition:
        print(f"✅ {name}: CONFIGURED {details}")
        return True
    else:
        print(f"❌ {name}: NOT CONFIGURED {details}")
        return False

print("=" * 70)
print("🔍 MEMORY APP WEBHOOK STATUS CHECK")
print("=" * 70)
print()

# Check environment variables
print("1️⃣ ENVIRONMENT VARIABLES")
print("-" * 70)

env_ok = True
env_ok &= check_status("Twilio Account SID", bool(TWILIO_ACCOUNT_SID), f"({TWILIO_ACCOUNT_SID[:10]}...)" if TWILIO_ACCOUNT_SID else "")
env_ok &= check_status("Twilio Auth Token", bool(TWILIO_AUTH_TOKEN), "(hidden)")
env_ok &= check_status("Twilio Phone Number", bool(TWILIO_PHONE_NUMBER), TWILIO_PHONE_NUMBER or "")
env_ok &= check_status("WhatsApp API Token", bool(WHATSAPP_API_TOKEN), f"({WHATSAPP_API_TOKEN[:10]}...)" if WHATSAPP_API_TOKEN else "")
env_ok &= check_status("WhatsApp Phone Number ID", bool(WHATSAPP_PHONE_NUMBER_ID), WHATSAPP_PHONE_NUMBER_ID or "")
env_ok &= check_status("WhatsApp Business Account ID", bool(WHATSAPP_BUSINESS_ACCOUNT_ID), WHATSAPP_BUSINESS_ACCOUNT_ID or "")
env_ok &= check_status("WhatsApp Verify Token", bool(WHATSAPP_VERIFY_TOKEN), WHATSAPP_VERIFY_TOKEN or "")

print()

# Check webhook server
print("2️⃣ WEBHOOK SERVER")
print("-" * 70)

server_ok = False
try:
    response = requests.get("http://localhost:8080/health", timeout=2)
    server_ok = check_status("Webhook Server", response.status_code == 200, f"Port 8080")
except:
    check_status("Webhook Server", False, "Not running on port 8080")

print()

# Check WhatsApp webhook verification
print("3️⃣ WHATSAPP WEBHOOK")
print("-" * 70)

whatsapp_ok = False
if server_ok and WHATSAPP_VERIFY_TOKEN:
    try:
        verify_url = f"http://localhost:8080/webhook/whatsapp?hub.mode=subscribe&hub.verify_token={WHATSAPP_VERIFY_TOKEN}&hub.challenge=test123"
        response = requests.get(verify_url, timeout=2)
        whatsapp_ok = check_status("WhatsApp Webhook Verification", response.status_code == 200 and response.text == "test123")
    except:
        check_status("WhatsApp Webhook Verification", False)
else:
    check_status("WhatsApp Webhook Verification", False, "Server not running or token not set")

# Check WhatsApp API connection
if WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
    try:
        url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}"
        headers = {"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=5)
        api_ok = check_status("WhatsApp API Connection", response.status_code == 200, "Can access phone number")
    except:
        check_status("WhatsApp API Connection", False, "Cannot connect to API")

print()

# Check webhook subscriptions
print("4️⃣ WEBHOOK SUBSCRIPTIONS")
print("-" * 70)

if WHATSAPP_API_TOKEN and WHATSAPP_BUSINESS_ACCOUNT_ID:
    try:
        url = f"https://graph.facebook.com/v17.0/{WHATSAPP_BUSINESS_ACCOUNT_ID}/subscribed_apps"
        headers = {"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                for app in data['data']:
                    fields = app.get('subscribed_fields', [])
                    if 'messages' in fields:
                        check_status("WhatsApp 'messages' field", True, "Subscribed")
                    else:
                        check_status("WhatsApp 'messages' field", False, "Not subscribed")
                    
                    if 'message_status' in fields:
                        check_status("WhatsApp 'message_status' field", True, "Subscribed")
                    else:
                        check_status("WhatsApp 'message_status' field", False, "Not subscribed")
            else:
                check_status("WhatsApp Webhook Subscriptions", False, "No subscriptions found")
        else:
            check_status("WhatsApp Webhook Subscriptions", False, f"API returned {response.status_code}")
    except Exception as e:
        check_status("WhatsApp Webhook Subscriptions", False, f"Error: {str(e)}")

print()

# Configuration URLs
print("5️⃣ WEBHOOK URLS FOR CONFIGURATION")
print("-" * 70)

print(f"WhatsApp Webhook URL:")
print(f"  {PUBLIC_URL}/webhook/whatsapp")
print(f"WhatsApp Verify Token:")
print(f"  {WHATSAPP_VERIFY_TOKEN or 'NOT SET'}")
print()
print(f"Twilio Voice Webhook:")
print(f"  {PUBLIC_URL}/webhook/twilio/voice")
print(f"Twilio SMS Webhook:")
print(f"  {PUBLIC_URL}/webhook/twilio/sms")

print()
print("=" * 70)
print("📊 OVERALL STATUS")
print("=" * 70)

if env_ok and server_ok and whatsapp_ok:
    print("✅ ALL SYSTEMS OPERATIONAL!")
    print("Your Digital Immortality Platform is ready to capture memories!")
    print()
    print("📱 Test it by sending a WhatsApp message to: +48 690 333 648")
else:
    print("⚠️ SOME CONFIGURATION NEEDED")
    print()
    if not env_ok:
        print("• Check environment variables above")
    if not server_ok:
        print("• Ensure webhook server is running on port 8080")
    if not whatsapp_ok:
        print("• Configure WhatsApp webhook in Meta Business Dashboard")

print()
print("💡 TIP: If messages aren't being received:")
print("  1. Make sure you subscribed to 'messages' field in Meta Dashboard")
print("  2. The recipient must have opted in (sent a message to you first)")
print("  3. Check that webhook URL is accessible from internet")
print()