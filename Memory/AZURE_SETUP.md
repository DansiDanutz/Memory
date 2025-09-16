# Azure Speech Services Setup Guide

## Quick Setup (5 minutes)

### Step 1: Get Free Azure Account
1. Go to: https://azure.microsoft.com/free/
2. Click "Start free"
3. Sign in with Microsoft account (or create one)
4. You get $200 credit for 30 days + free tier services

### Step 2: Create Speech Service
1. Go to Azure Portal: https://portal.azure.com
2. Click "Create a resource"
3. Search for "Speech"
4. Select "Speech" by Microsoft
5. Click "Create"

### Step 3: Configure Your Speech Service
Fill in these fields:
- **Subscription**: Your free subscription
- **Resource group**: Create new → name it "memory-app"
- **Region**: Choose closest to you (e.g., "East US", "West Europe")
- **Name**: "memory-speech" (or any unique name)
- **Pricing tier**: Select "F0 (Free)" - 5 hours free per month

Click "Review + create" → "Create"

### Step 4: Get Your Keys
1. Once created, go to your Speech resource
2. Click "Keys and Endpoint" in left menu
3. You'll see:
   - KEY 1: `[your-key-here]`
   - KEY 2: `[backup-key]`
   - Location/Region: `eastus` (or your chosen region)

### Step 5: Add to Your App
Copy KEY 1 and your region, then I'll add them to your .env file.

## Free Tier Limits
- 5 hours of speech-to-text per month
- 0.5 million characters text-to-speech per month
- Perfect for testing and development

## What You Get
✅ Voice transcription for audio messages
✅ Text-to-speech for voice responses
✅ Multiple language support
✅ Real-time voice processing

---

**Ready to add your Azure key? Just paste it below!**