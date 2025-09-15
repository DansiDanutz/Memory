#!/usr/bin/env python3
"""
Voice Cloning API Endpoints for Memory App
Handles voice sample collection, training, and synthesis
"""

import os
import json
import asyncio
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import logging

from voice_cloning_service import (
    VoiceCloningService,
    VoiceProvider,
    VoiceQuality,
    ConversationStyle,
    SynthesisRequest,
    VoiceCloneStatus
)

logger = logging.getLogger(__name__)

# Create Flask blueprint
voice_cloning_api = Blueprint('voice_cloning', __name__)

# Initialize voice cloning service
voice_service = VoiceCloningService()

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm', 'm4a', 'flac'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================
# PROFILE MANAGEMENT
# ==========================

@voice_cloning_api.route('/api/voice/profiles', methods=['GET'])
async def get_voice_profiles():
    """Get all voice profiles for a user"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    profiles = voice_service.get_voice_profiles(user_id)
    
    return jsonify({
        "success": True,
        "profiles": [
            {
                "profile_id": p.profile_id,
                "name": p.name,
                "provider": p.provider.value,
                "status": p.status.value,
                "samples_collected": p.samples_collected,
                "samples_required": p.samples_required,
                "total_duration": p.total_duration_seconds,
                "is_ready": p.is_ready(),
                "created_at": p.created_at.isoformat()
            }
            for p in profiles
        ]
    })

@voice_cloning_api.route('/api/voice/profiles', methods=['POST'])
async def create_voice_profile():
    """Create a new voice profile"""
    data = request.json
    
    if not data.get('user_id') or not data.get('name'):
        return jsonify({"error": "user_id and name required"}), 400
    
    # Get provider (default to DEMO)
    provider_name = data.get('provider', 'demo').upper()
    try:
        provider = VoiceProvider[provider_name]
    except KeyError:
        provider = VoiceProvider.DEMO
    
    try:
        profile = await voice_service.create_voice_profile(
            user_id=data['user_id'],
            name=data['name'],
            provider=provider
        )
        
        return jsonify({
            "success": True,
            "profile": {
                "profile_id": profile.profile_id,
                "name": profile.name,
                "provider": profile.provider.value,
                "status": profile.status.value,
                "samples_required": profile.samples_required,
                "min_duration_required": profile.min_duration_required
            }
        })
    except Exception as e:
        logger.error(f"Failed to create voice profile: {e}")
        return jsonify({"error": str(e)}), 500

@voice_cloning_api.route('/api/voice/profiles/<profile_id>', methods=['DELETE'])
async def delete_voice_profile(profile_id: str):
    """Delete a voice profile"""
    if profile_id in voice_service.profiles:
        del voice_service.profiles[profile_id]
        if profile_id in voice_service.samples:
            del voice_service.samples[profile_id]
        
        return jsonify({"success": True, "message": "Profile deleted"})
    
    return jsonify({"error": "Profile not found"}), 404

# ==========================
# VOICE SAMPLE COLLECTION
# ==========================

@voice_cloning_api.route('/api/voice/samples/upload', methods=['POST'])
async def upload_voice_sample():
    """Upload a voice sample for training"""
    profile_id = request.form.get('profile_id')
    transcript = request.form.get('transcript', '')
    
    if not profile_id:
        return jsonify({"error": "profile_id required"}), 400
    
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    file = request.files['audio']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}"}), 400
    
    try:
        # Read audio data
        audio_data = file.read()
        
        # Add sample to profile
        sample = await voice_service.add_voice_sample(
            profile_id=profile_id,
            audio_data=audio_data,
            transcript=transcript
        )
        
        # Check if ready to train
        profile = voice_service.profiles[profile_id]
        can_train = profile.can_train()
        
        return jsonify({
            "success": True,
            "sample": {
                "sample_id": sample.sample_id,
                "duration": sample.duration_seconds,
                "quality_score": sample.quality_score
            },
            "profile_status": {
                "samples_collected": profile.samples_collected,
                "samples_required": profile.samples_required,
                "total_duration": profile.total_duration_seconds,
                "can_train": can_train,
                "status": profile.status.value
            }
        })
    except Exception as e:
        logger.error(f"Failed to upload voice sample: {e}")
        return jsonify({"error": str(e)}), 500

@voice_cloning_api.route('/api/voice/samples/record', methods=['POST'])
async def record_voice_sample():
    """Record voice sample from browser (base64 encoded)"""
    data = request.json
    
    if not data.get('profile_id') or not data.get('audio_data'):
        return jsonify({"error": "profile_id and audio_data required"}), 400
    
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(data['audio_data'])
        transcript = data.get('transcript', '')
        
        # Add sample to profile
        sample = await voice_service.add_voice_sample(
            profile_id=data['profile_id'],
            audio_data=audio_data,
            transcript=transcript
        )
        
        profile = voice_service.profiles[data['profile_id']]
        
        return jsonify({
            "success": True,
            "sample": {
                "sample_id": sample.sample_id,
                "duration": sample.duration_seconds,
                "quality_score": sample.quality_score
            },
            "profile_status": {
                "samples_collected": profile.samples_collected,
                "total_duration": profile.total_duration_seconds,
                "can_train": profile.can_train()
            }
        })
    except Exception as e:
        logger.error(f"Failed to record voice sample: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# VOICE TRAINING
# ==========================

@voice_cloning_api.route('/api/voice/train', methods=['POST'])
async def train_voice_clone():
    """Train voice clone from collected samples"""
    data = request.json
    
    if not data.get('profile_id'):
        return jsonify({"error": "profile_id required"}), 400
    
    profile_id = data['profile_id']
    
    if profile_id not in voice_service.profiles:
        return jsonify({"error": "Profile not found"}), 404
    
    profile = voice_service.profiles[profile_id]
    
    if not profile.can_train():
        return jsonify({
            "error": "Not enough samples collected",
            "samples_collected": profile.samples_collected,
            "samples_required": profile.samples_required,
            "total_duration": profile.total_duration_seconds,
            "min_duration_required": profile.min_duration_required
        }), 400
    
    try:
        # Start training
        success = await voice_service.train_voice_clone(profile_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Voice clone trained successfully",
                "voice_id": profile.voice_id,
                "status": profile.status.value
            })
        else:
            return jsonify({
                "success": False,
                "error": "Training failed",
                "status": profile.status.value
            }), 500
    except Exception as e:
        logger.error(f"Failed to train voice clone: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# VOICE SYNTHESIS
# ==========================

@voice_cloning_api.route('/api/voice/synthesize', methods=['POST'])
async def synthesize_speech():
    """Synthesize speech using cloned voice"""
    data = request.json
    
    if not data.get('text') or not data.get('profile_id') or not data.get('user_id'):
        return jsonify({"error": "text, profile_id, and user_id required"}), 400
    
    # Create synthesis request
    request_obj = SynthesisRequest(
        text=data['text'],
        profile_id=data['profile_id'],
        user_id=data['user_id'],
        quality=VoiceQuality[data.get('quality', 'STANDARD').upper()],
        speed=data.get('speed', 1.0),
        pitch=data.get('pitch', 1.0),
        emotion=data.get('emotion'),
        style=ConversationStyle[data.get('style', 'SUPPORTIVE').upper()],
        cache_result=data.get('cache', True),
        stream=data.get('stream', False)
    )
    
    try:
        result = await voice_service.synthesize_speech(request_obj)
        
        if result.error:
            return jsonify({"error": result.error}), 500
        
        return jsonify({
            "success": True,
            "request_id": result.request_id,
            "audio_url": result.audio_url,
            "duration": result.duration_seconds,
            "characters_used": result.characters_used,
            "synthesis_time_ms": result.synthesis_time_ms,
            "cached": result.cached
        })
    except Exception as e:
        logger.error(f"Failed to synthesize speech: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# SELF-CONVERSATIONS
# ==========================

@voice_cloning_api.route('/api/voice/conversations/start', methods=['POST'])
async def start_conversation():
    """Start a self-conversation with AI twin"""
    data = request.json
    
    if not data.get('user_id') or not data.get('profile_id'):
        return jsonify({"error": "user_id and profile_id required"}), 400
    
    style = ConversationStyle[data.get('style', 'SUPPORTIVE').upper()]
    topic = data.get('topic')
    
    try:
        conversation = await voice_service.start_self_conversation(
            user_id=data['user_id'],
            profile_id=data['profile_id'],
            style=style,
            topic=topic
        )
        
        return jsonify({
            "success": True,
            "conversation": {
                "conversation_id": conversation.conversation_id,
                "style": conversation.style.value,
                "topic": conversation.topic,
                "messages": conversation.messages
            }
        })
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        return jsonify({"error": str(e)}), 500

@voice_cloning_api.route('/api/voice/conversations/<conversation_id>/message', methods=['POST'])
async def send_conversation_message(conversation_id: str):
    """Send message in self-conversation"""
    data = request.json
    
    if not data.get('message'):
        return jsonify({"error": "message required"}), 400
    
    try:
        response, audio_url = await voice_service.respond_to_user(
            conversation_id=conversation_id,
            user_message=data['message']
        )
        
        conversation = voice_service.conversations[conversation_id]
        
        return jsonify({
            "success": True,
            "ai_response": response,
            "audio_url": audio_url,
            "insights": conversation.insights_generated[-1:] if conversation.insights_generated else []
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        return jsonify({"error": str(e)}), 500

@voice_cloning_api.route('/api/voice/conversations', methods=['GET'])
async def get_conversations():
    """Get conversation history for user"""
    user_id = request.args.get('user_id')
    limit = int(request.args.get('limit', 10))
    
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    conversations = voice_service.get_conversation_history(user_id, limit)
    
    return jsonify({
        "success": True,
        "conversations": [
            {
                "conversation_id": c.conversation_id,
                "style": c.style.value,
                "topic": c.topic,
                "started_at": c.started_at.isoformat(),
                "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                "message_count": len(c.messages),
                "insights_count": len(c.insights_generated)
            }
            for c in conversations
        ]
    })

# ==========================
# STATISTICS & EXPORT
# ==========================

@voice_cloning_api.route('/api/voice/stats/<user_id>', methods=['GET'])
async def get_voice_stats(user_id: str):
    """Get voice synthesis statistics"""
    stats = voice_service.get_synthesis_stats(user_id)
    
    return jsonify({
        "success": True,
        "stats": stats
    })

@voice_cloning_api.route('/api/voice/export/<profile_id>', methods=['GET'])
async def export_voice_profile(profile_id: str):
    """Export voice profile data"""
    try:
        export_data = await voice_service.export_voice_profile(profile_id)
        
        return jsonify({
            "success": True,
            "export": export_data
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Failed to export profile: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# AUDIO FILE SERVING
# ==========================

@voice_cloning_api.route('/audio/<filename>')
def serve_audio(filename: str):
    """Serve synthesized audio files"""
    try:
        file_path = voice_service.synthesis_path / secure_filename(filename)
        if file_path.exists():
            return send_file(str(file_path), mimetype='audio/wav')
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Failed to serve audio: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# HEALTH CHECK
# ==========================

@voice_cloning_api.route('/api/voice/health', methods=['GET'])
def voice_health_check():
    """Health check for voice cloning service"""
    providers_status = {}
    
    for provider, config in voice_service.providers.items():
        if provider == VoiceProvider.DEMO:
            providers_status[provider.value] = "ready"
        else:
            providers_status[provider.value] = "configured" if config else "not_configured"
    
    return jsonify({
        "status": "healthy",
        "providers": providers_status,
        "profiles_count": len(voice_service.profiles),
        "conversations_count": len(voice_service.conversations),
        "cache_size": len(voice_service.synthesis_cache)
    })

# ==========================
# DEMO ENDPOINTS
# ==========================

@voice_cloning_api.route('/api/voice/demo', methods=['POST'])
async def run_voice_demo():
    """Run a complete voice cloning demo"""
    data = request.json
    user_id = data.get('user_id', 'demo_user')
    
    try:
        # Create demo profile
        profile = await voice_service.create_voice_profile(
            user_id=user_id,
            name="Demo Voice Twin",
            provider=VoiceProvider.DEMO
        )
        
        # Synthesize sample text
        synthesis_request = SynthesisRequest(
            text="Hello! I'm your AI voice twin. This is a demo of what I can do!",
            profile_id=profile.profile_id,
            user_id=user_id,
            quality=VoiceQuality.PREMIUM
        )
        
        result = await voice_service.synthesize_speech(synthesis_request)
        
        # Start conversation
        conversation = await voice_service.start_self_conversation(
            user_id=user_id,
            profile_id=profile.profile_id,
            style=ConversationStyle.SUPPORTIVE,
            topic="demo conversation"
        )
        
        return jsonify({
            "success": True,
            "demo": {
                "profile_id": profile.profile_id,
                "synthesis_result": {
                    "audio_url": result.audio_url,
                    "duration": result.duration_seconds
                },
                "conversation": {
                    "conversation_id": conversation.conversation_id,
                    "initial_message": conversation.messages[0] if conversation.messages else None
                }
            }
        })
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        return jsonify({"error": str(e)}), 500


# Initialize endpoints when module is imported
def init_voice_cloning_endpoints(app):
    """Initialize voice cloning endpoints with Flask app"""
    app.register_blueprint(voice_cloning_api)
    logger.info("🎤 Voice Cloning API endpoints registered")
    return voice_cloning_api