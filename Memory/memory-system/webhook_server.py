#!/usr/bin/env python3
"""
Production Webhook Server for Memory App
Handles Twilio, WhatsApp Business API, and WebSocket connections
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import jwt
import hmac
import hashlib
import base64
from twilio.twiml.voice_response import VoiceResponse, Record, Gather
from twilio.request_validator import RequestValidator
from memory_app import memory_app
from whatsapp_bot import WhatsAppMemoryBot
from telegram_bot import TelegramMemoryBot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# WebSocket configuration
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize bot instances
whatsapp_bot = WhatsAppMemoryBot()
telegram_bot = TelegramMemoryBot()

# Configuration from environment
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "your-verify-token")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret-webhook-key")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret-key")

# Track WebSocket connections
websocket_connections: Dict[str, str] = {}  # socket_id -> user_id

# ==========================
# AUTHENTICATION HELPERS
# ==========================

def verify_twilio_signature(request_data) -> bool:
    """Verify that webhook came from Twilio"""
    if not TWILIO_AUTH_TOKEN:
        logger.warning("⚠️ Twilio auth token not configured")
        return True  # Allow in development
    
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    signature = request.headers.get('X-Twilio-Signature', '')
    url = request.url
    
    # Validate the request came from Twilio
    is_valid = validator.validate(url, request.form, signature)
    
    if not is_valid:
        logger.error("❌ Invalid Twilio signature")
    
    return is_valid

def verify_whatsapp_signature(request_data) -> bool:
    """Verify WhatsApp webhook signature"""
    signature = request.headers.get('X-Hub-Signature-256', '')
    
    if not signature:
        logger.warning("⚠️ No WhatsApp signature header")
        return False
    
    # Calculate expected signature
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        request.data,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    provided = signature.replace('sha256=', '')
    is_valid = hmac.compare_digest(expected, provided)
    
    if not is_valid:
        logger.error("❌ Invalid WhatsApp signature")
    
    return is_valid

def generate_jwt_token(user_id: str) -> str:
    """Generate JWT token for WebSocket authentication"""
    payload = {
        'user_id': user_id,
        'timestamp': datetime.now().isoformat(),
        'exp': datetime.now().timestamp() + 86400  # 24 hours
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token: str) -> Optional[str]:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload.get('user_id')
    except:
        return None

# ==========================
# TWILIO VOICE WEBHOOKS
# ==========================

@app.route('/webhook/twilio/voice', methods=['POST'])
async def twilio_voice_webhook():
    """Handle incoming Twilio voice calls"""
    
    # Verify Twilio signature
    if not verify_twilio_signature(request.form):
        return Response(status=403)
    
    # Extract call information
    from_number = request.form.get('From', '')
    to_number = request.form.get('To', '')
    call_sid = request.form.get('CallSid', '')
    
    logger.info(f"📞 Incoming call from {from_number} to {to_number}")
    
    # Check if AI should handle the call
    result = await memory_app.handle_incoming_call(
        caller_id=from_number,
        platform='twilio'
    )
    
    response = VoiceResponse()
    
    if result['should_answer']:
        # AI will handle the call
        session_id = result['session_id']
        greeting = result['greeting']
        
        # Speak the greeting
        response.say(greeting, voice='alice')
        
        # Start recording the conversation
        response.record(
            action=f'/webhook/twilio/recording/{session_id}',
            method='POST',
            max_length=600,  # 10 minutes max
            transcribe=True,
            transcribe_callback=f'/webhook/twilio/transcription/{session_id}',
            play_beep=False
        )
        
        logger.info(f"✅ AI handling call with session {session_id}")
    else:
        # Let call go to voicemail
        response.say("The person you're calling is not available. Please leave a message after the beep.")
        response.record(
            action='/webhook/twilio/voicemail',
            method='POST',
            max_length=120,  # 2 minutes for voicemail
            transcribe=True
        )
    
    return Response(str(response), mimetype='text/xml')

@app.route('/webhook/twilio/recording/<session_id>', methods=['POST'])
async def twilio_recording_webhook(session_id: str):
    """Handle completed call recording"""
    
    if not verify_twilio_signature(request.form):
        return Response(status=403)
    
    recording_url = request.form.get('RecordingUrl', '')
    recording_duration = request.form.get('RecordingDuration', '0')
    
    logger.info(f"📼 Recording completed for session {session_id}: {recording_duration}s")
    
    # Store the recording URL in the call session
    if session_id in memory_app.active_calls:
        memory_app.active_calls[session_id].recording_url = recording_url
        memory_app.active_calls[session_id].duration = int(recording_duration)
    
    # End the call and create transcript memory
    memory_number = await memory_app.end_call(session_id)
    
    response = VoiceResponse()
    response.say(f"Thank you for your call. Your conversation has been saved as Memory {memory_number}.")
    response.hangup()
    
    return Response(str(response), mimetype='text/xml')

@app.route('/webhook/twilio/transcription/<session_id>', methods=['POST'])
async def twilio_transcription_webhook(session_id: str):
    """Handle call transcription from Twilio"""
    
    if not verify_twilio_signature(request.form):
        return Response(status=403)
    
    transcription_text = request.form.get('TranscriptionText', '')
    
    logger.info(f"📝 Transcription received for session {session_id}")
    
    # Add transcription to call session
    if session_id in memory_app.active_calls:
        memory_app.active_calls[session_id].transcript = transcription_text
    
    return Response(status=200)

# ==========================
# HEALTH CHECK ENDPOINT
# ==========================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Memory App Webhook Server',
        'timestamp': datetime.utcnow().isoformat(),
        'features': {
            'twilio_voice': True,
            'whatsapp': True,
            'telegram': True,
            'websocket': True
        }
    }), 200

# ==========================
# WHATSAPP BUSINESS API WEBHOOKS
# ==========================

@app.route('/webhook/whatsapp', methods=['GET'])
def whatsapp_verify():
    """Verify WhatsApp webhook during setup"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ WhatsApp webhook verified")
        return challenge
    
    return Response(status=403)

@app.route('/webhook/whatsapp', methods=['POST'])
async def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    
    # Verify signature
    if not verify_whatsapp_signature(request.data):
        return Response(status=403)
    
    data = request.json
    
    # Process each message
    if 'entry' in data:
        for entry in data['entry']:
            for change in entry.get('changes', []):
                if change['field'] == 'messages':
                    messages = change['value'].get('messages', [])
                    
                    for message in messages:
                        sender_id = message['from']
                        message_type = message['type']
                        
                        # Prepare message data
                        message_data = {
                            'sender_id': sender_id,
                            'type': message_type,
                            'timestamp': message['timestamp']
                        }
                        
                        # Extract content based on type
                        if message_type == 'text':
                            message_data['content'] = message['text']['body']
                        elif message_type == 'audio':
                            # WhatsApp sends audio as media ID
                            message_data['audio_id'] = message['audio']['id']
                            message_data['audio_data'] = await download_whatsapp_media(
                                message['audio']['id']
                            )
                        elif message_type == 'image':
                            message_data['image_id'] = message['image']['id']
                            message_data['caption'] = message.get('image', {}).get('caption', '')
                        
                        # Process with WhatsApp bot
                        response = await whatsapp_bot.handle_message(message_data)
                        
                        # Send response back via WhatsApp API
                        if response.get('response'):
                            await send_whatsapp_message(
                                sender_id,
                                response['response']
                            )
    
    return jsonify({'status': 'ok'})

async def download_whatsapp_media(media_id: str) -> Optional[str]:
    """Download media from WhatsApp"""
    # Implementation for downloading WhatsApp media
    # This requires WhatsApp Business API access token
    logger.info(f"📥 Downloading WhatsApp media {media_id}")
    # Return base64 encoded audio data
    return None  # Placeholder

async def send_whatsapp_message(recipient: str, message: str):
    """Send message via WhatsApp Business API"""
    # Implementation for sending WhatsApp messages
    logger.info(f"📤 Sending WhatsApp message to {recipient}")
    # Use WhatsApp Business API to send message
    pass  # Placeholder

# ==========================
# WEBSOCKET HANDLERS
# ==========================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"🔌 WebSocket connected: {request.sid}")
    emit('connected', {'message': 'Connected to Memory App WebSocket'})

@socketio.on('authenticate')
def handle_authenticate(data):
    """Authenticate WebSocket connection"""
    token = data.get('token')
    user_id = verify_jwt_token(token)
    
    if user_id:
        # Store connection mapping
        websocket_connections[request.sid] = user_id
        
        # Join user's room for targeted notifications
        join_room(f"user_{user_id}")
        
        logger.info(f"✅ WebSocket authenticated for user {user_id}")
        emit('authenticated', {'user_id': user_id})
        
        # Send any pending notifications
        asyncio.create_task(send_pending_notifications(user_id))
    else:
        logger.warning(f"❌ WebSocket authentication failed")
        emit('auth_failed', {'error': 'Invalid token'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    if request.sid in websocket_connections:
        user_id = websocket_connections[request.sid]
        leave_room(f"user_{user_id}")
        del websocket_connections[request.sid]
        logger.info(f"🔌 WebSocket disconnected for user {user_id}")
    else:
        logger.info(f"🔌 WebSocket disconnected: {request.sid}")

async def send_pending_notifications(user_id: str):
    """Send any pending notifications to user"""
    # Get pending notifications from memory app
    if hasattr(memory_app, 'pending_notifications'):
        pending = [n for n in memory_app.pending_notifications if n.user_id == user_id and not n.delivered]
        
        for notification in pending:
            socketio.emit('notification', {
                'id': notification.id,
                'type': notification.type.value,
                'title': notification.title,
                'message': notification.message,
                'data': notification.data,
                'timestamp': notification.timestamp.isoformat(),
                'urgent': notification.urgent
            }, room=f"user_{user_id}")
            
            notification.delivered = True
            logger.info(f"📨 Delivered pending notification to {user_id}")

# ==========================
# API ENDPOINTS
# ==========================

@app.route('/api/auth/token', methods=['POST'])
def get_auth_token():
    """Get JWT token for WebSocket authentication"""
    data = request.json
    user_id = data.get('user_id')
    
    # In production, verify user credentials here
    # For now, just generate token
    token = generate_jwt_token(user_id)
    
    return jsonify({
        'token': token,
        'expires_in': 86400
    })

@app.route('/api/notifications/send', methods=['POST'])
async def send_notification():
    """Send real-time notification to user"""
    data = request.json
    user_id = data.get('user_id')
    notification_data = data.get('notification')
    
    # Send via WebSocket if user is connected
    socketio.emit('notification', notification_data, room=f"user_{user_id}")
    
    return jsonify({'status': 'sent'})

@app.route('/api/health', methods=['GET'])
def api_health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'websocket_connections': len(websocket_connections)
    })

# ==========================
# MAIN ENTRY POINT
# ==========================

if __name__ == '__main__':
    logger.info("🚀 Starting Memory App Webhook Server")
    logger.info(f"📡 Webhooks ready at:")
    logger.info(f"   • Twilio: /webhook/twilio/voice")
    logger.info(f"   • WhatsApp: /webhook/whatsapp")
    logger.info(f"   • WebSocket: ws://localhost:8080")
    
    # Run the server
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)