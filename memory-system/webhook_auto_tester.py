#!/usr/bin/env python3
"""
Automated Webhook Tester for Memory App
Tests WhatsApp and Twilio webhook configurations
"""

import os
import json
import time
import requests
from datetime import datetime
from twilio.rest import Client

# Environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_BUSINESS_API_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_local_webhook_server():
    """Test if local webhook server is running"""
    print(f"\n{BLUE}Testing Local Webhook Server...{RESET}")
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        if response.status_code == 200:
            print(f"{GREEN}✅ Webhook server is running!{RESET}")
            return True
        else:
            print(f"{RED}❌ Webhook server returned status: {response.status_code}{RESET}")
            return False
    except Exception as e:
        print(f"{RED}❌ Cannot connect to webhook server: {e}{RESET}")
        return False

def test_twilio_sms():
    """Send a test SMS via Twilio"""
    print(f"\n{BLUE}Testing Twilio SMS...{RESET}")
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send test SMS to yourself
        message = client.messages.create(
            body=f"🧠 Memory App Test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            from_=TWILIO_PHONE_NUMBER,
            to=TWILIO_PHONE_NUMBER  # Sending to self for testing
        )
        
        print(f"{GREEN}✅ Twilio SMS sent! Message SID: {message.sid}{RESET}")
        print(f"   From: {TWILIO_PHONE_NUMBER}")
        print(f"   Status: {message.status}")
        return True
    except Exception as e:
        print(f"{RED}❌ Twilio SMS failed: {e}{RESET}")
        return False

def test_whatsapp_message():
    """Send a test WhatsApp message"""
    print(f"\n{BLUE}Testing WhatsApp Business API...{RESET}")
    
    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test message template (you need to create this in Meta Business)
    data = {
        "messaging_product": "whatsapp",
        "to": "48690333648",  # Your WhatsApp number
        "type": "text",
        "text": {
            "body": f"🧠 Memory App Test Message\n\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nYour Digital Immortality Platform is connected!"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"{GREEN}✅ WhatsApp message sent!{RESET}")
            print(f"   Message ID: {result.get('messages', [{}])[0].get('id', 'N/A')}")
            return True
        else:
            print(f"{YELLOW}⚠️ WhatsApp API returned status: {response.status_code}{RESET}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 401:
                print(f"\n{RED}   → Invalid API token. Check WHATSAPP_BUSINESS_API_TOKEN{RESET}")
            elif response.status_code == 404:
                print(f"\n{RED}   → Phone number ID not found. Check WHATSAPP_PHONE_NUMBER_ID{RESET}")
            return False
    except Exception as e:
        print(f"{RED}❌ WhatsApp message failed: {e}{RESET}")
        return False

def check_webhook_configuration():
    """Check if webhooks are properly configured"""
    print(f"\n{BLUE}Checking Webhook Configuration...{RESET}")
    
    # Check Twilio webhook configuration
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Get phone number configuration
            phone_numbers = client.incoming_phone_numbers.list(phone_number=TWILIO_PHONE_NUMBER)
            
            if phone_numbers:
                number = phone_numbers[0]
                print(f"\n{GREEN}📱 Twilio Phone Number Configuration:{RESET}")
                print(f"   Number: {number.phone_number}")
                
                if number.sms_url:
                    print(f"   {GREEN}✅ SMS Webhook: {number.sms_url}{RESET}")
                else:
                    print(f"   {RED}❌ SMS Webhook: Not configured{RESET}")
                
                if number.voice_url:
                    print(f"   {GREEN}✅ Voice Webhook: {number.voice_url}{RESET}")
                else:
                    print(f"   {RED}❌ Voice Webhook: Not configured{RESET}")
            else:
                print(f"{RED}❌ Phone number {TWILIO_PHONE_NUMBER} not found in account{RESET}")
        except Exception as e:
            print(f"{RED}❌ Could not check Twilio configuration: {e}{RESET}")
    
    # Check WhatsApp webhook subscription
    if WHATSAPP_API_TOKEN and WHATSAPP_BUSINESS_ACCOUNT_ID:
        try:
            # Check webhook subscriptions
            url = f"https://graph.facebook.com/v17.0/{WHATSAPP_BUSINESS_ACCOUNT_ID}/subscribed_apps"
            headers = {"Authorization": f"Bearer {WHATSAPP_API_TOKEN}"}
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    print(f"\n{GREEN}📱 WhatsApp Webhook Subscriptions:{RESET}")
                    for app in data['data']:
                        print(f"   {GREEN}✅ App subscribed with fields: {', '.join(app.get('subscribed_fields', []))}{RESET}")
                else:
                    print(f"\n{YELLOW}⚠️ No WhatsApp webhook subscriptions found{RESET}")
            else:
                print(f"\n{YELLOW}⚠️ Could not check WhatsApp subscriptions: {response.status_code}{RESET}")
        except Exception as e:
            print(f"{RED}❌ Could not check WhatsApp configuration: {e}{RESET}")

def main():
    print("=" * 70)
    print(f"{BLUE}🤖 MEMORY APP WEBHOOK AUTOMATED TESTER{RESET}")
    print("=" * 70)
    
    # Test local server
    if not test_local_webhook_server():
        print(f"\n{RED}⚠️ Please ensure the webhook server is running on port 8080{RESET}")
        return
    
    # Check configuration
    check_webhook_configuration()
    
    # Test services
    print(f"\n{YELLOW}📨 SENDING TEST MESSAGES...{RESET}")
    print("-" * 70)
    
    twilio_ok = False
    whatsapp_ok = False
    
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        twilio_ok = test_twilio_sms()
    else:
        print(f"\n{YELLOW}⚠️ Twilio credentials not configured{RESET}")
    
    if WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
        whatsapp_ok = test_whatsapp_message()
    else:
        print(f"\n{YELLOW}⚠️ WhatsApp credentials not configured{RESET}")
    
    # Summary
    print("\n" + "=" * 70)
    print(f"{BLUE}📊 TEST SUMMARY{RESET}")
    print("=" * 70)
    
    print(f"\n✅ Local webhook server: {GREEN}Running{RESET}")
    print(f"{'✅' if twilio_ok else '❌'} Twilio SMS: {'Working' if twilio_ok else 'Not configured or failed'}")
    print(f"{'✅' if whatsapp_ok else '❌'} WhatsApp API: {'Working' if whatsapp_ok else 'Not configured or failed'}")
    
    if twilio_ok and whatsapp_ok:
        print(f"\n{GREEN}🎉 All systems operational! Your Memory App is ready!{RESET}")
    else:
        print(f"\n{YELLOW}⚠️ Some services need configuration. Check the messages above.{RESET}")
        print(f"\n{BLUE}To configure webhooks:{RESET}")
        print("1. Twilio: https://www.twilio.com/console/phone-numbers/")
        print("2. WhatsApp: https://developers.facebook.com/apps/")

if __name__ == "__main__":
    main()