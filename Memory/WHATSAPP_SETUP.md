# WhatsApp Business API Setup Guide

## Overview
This will connect your Memory App to WhatsApp so users can chat with your bot via WhatsApp.

## Prerequisites
- Facebook/Meta account
- A phone number (can be virtual) that's NOT already on WhatsApp

## Step-by-Step Setup

### Step 1: Create Meta Business Account
1. Go to: https://business.facebook.com/
2. Click "Create account"
3. Enter your business name (e.g., "Memory App")
4. Enter your name and business email
5. Click "Submit"

### Step 2: Access Meta for Developers
1. Go to: https://developers.facebook.com/
2. Click "My Apps" → "Create App"
3. Choose "Business" as app type
4. Select "Business" → Click "Next"

### Step 3: Set Up WhatsApp Product
1. App Name: "Memory Bot" (or your choice)
2. Contact Email: Your email
3. App Purpose: Select "Yourself or your own business"
4. Click "Create App"

### Step 4: Add WhatsApp Product
1. In your app dashboard, find "WhatsApp"
2. Click "Set up"
3. You'll see the WhatsApp Getting Started page

### Step 5: Get Test Phone Number (FREE)
1. In WhatsApp section, click "API Setup"
2. You'll get a TEST phone number like: +1 555 123 4567
3. Copy the "Phone number ID" (looks like: 123456789012345)
4. This is your `WA_PHONE_NUMBER_ID`

### Step 6: Get Access Token
1. In the same page, find "Temporary access token"
2. Click "Generate" button
3. Copy the long token (starts with "EAAI...")
4. This is your `META_ACCESS_TOKEN`

Note: Temporary token expires in 24 hours. For permanent token:
- Go to "System Users" in Business Settings
- Create system user → Generate token
- Select permissions: whatsapp_business_messaging, whatsapp_business_management

### Step 7: Configure Webhook (for receiving messages)
1. In WhatsApp > Configuration
2. Click "Configure Webhooks"
3. Callback URL: `https://your-domain.com/webhook/whatsapp`
4. Verify Token: `memory-app-verify-2024` (already in your .env)
5. Subscribe to: messages, messaging_postbacks

### Step 8: Test Number Setup
The test number can send messages to up to 5 verified phone numbers:
1. Go to "API Setup"
2. Under "To", click "Manage phone number list"
3. Add your personal WhatsApp number
4. Verify with the code sent via WhatsApp

## What You Need to Add to .env:

```
META_ACCESS_TOKEN=EAAI...your-long-token-here...
WA_PHONE_NUMBER_ID=123456789012345
APP_PUBLIC_URL=https://your-app-url.com
```

## Free Tier Limits
- 1,000 free messages per month
- Can message up to 5 verified numbers
- Perfect for testing and development

## Testing Your Setup
1. Send a WhatsApp message to your test number
2. Your bot should respond
3. Check dashboard for message logs

## Next Steps for Production
1. Business Verification (takes 2-5 days)
2. Get a dedicated WhatsApp Business number
3. Apply for higher messaging limits

---

**Ready? Let's add your WhatsApp credentials!**