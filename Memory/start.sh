#!/bin/bash
# Startup script for Phase 1 WhatsApp Memory Bot

echo "🚀 Starting WhatsApp Memory Bot (Phase 1)..."

# Create necessary directories
mkdir -p memory-system/users
mkdir -p memory-system/voice_auth
mkdir -p memory-system/sessions

# Export default environment variables if not set
export WEBHOOK_VERIFY_TOKEN=${WEBHOOK_VERIFY_TOKEN:-"memory-app-verify-2024"}
export WEBHOOK_SECRET=${WEBHOOK_SECRET:-"webhook-secret-key"}
export VOICE_AUTH_SALT=${VOICE_AUTH_SALT:-"memory-app-voice-salt-2024"}
export ENCRYPTION_MASTER_KEY=${ENCRYPTION_MASTER_KEY:-"development-key-change-in-production"}
export PORT=${PORT:-5000}

# Check for Azure Speech Services configuration
if [ -z "$AZURE_SPEECH_KEY" ]; then
    echo "⚠️  Warning: AZURE_SPEECH_KEY not set. Voice transcription will not work."
fi

if [ -z "$WHATSAPP_ACCESS_TOKEN" ]; then
    echo "⚠️  Warning: WHATSAPP_ACCESS_TOKEN not set. WhatsApp messaging will not work."
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Start the FastAPI application
echo "🎯 Starting FastAPI server on port $PORT..."
cd app && python -m uvicorn main:app --host 0.0.0.0 --port $PORT --reload