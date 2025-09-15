#!/usr/bin/env python3
"""
Voice Authentication API Endpoints for Memory App
Flask-based endpoints for biometric voice authentication
"""

import os
import io
import json
import base64
import logging
from flask import Blueprint, request, jsonify, send_file
from functools import wraps
from typing import Optional
import asyncio
from datetime import datetime

# Import voice authentication service
from voice_authentication_service import voice_auth_service

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint
voice_auth_bp = Blueprint('voice_auth', __name__)

# Rate limiting decorator
def rate_limit(max_attempts=3, window=60):
    """Rate limiting decorator for endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user identifier
            user_id = request.json.get('user_id') if request.json else request.args.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'User ID required'}), 400
            
            # Check rate limit (handled by service)
            # Service will check internally
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def async_endpoint(f):
    """Decorator to run async functions in Flask"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return decorated_function

# ==========================
# ENROLLMENT ENDPOINTS
# ==========================

@voice_auth_bp.route('/api/voice-auth/enroll/start', methods=['POST'])
@async_endpoint
async def start_enrollment():
    """Initialize voice enrollment session"""
    try:
        data = request.json
        user_id = data.get('user_id')
        display_name = data.get('display_name')
        
        if not user_id or not display_name:
            return jsonify({
                'success': False,
                'error': 'user_id and display_name are required'
            }), 400
        
        # Additional metadata
        metadata = {
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': datetime.now().isoformat()
        }
        
        result = await voice_auth_service.start_enrollment(
            user_id=user_id,
            display_name=display_name,
            metadata=metadata
        )
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Error starting enrollment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_auth_bp.route('/api/voice-auth/enroll/sample', methods=['POST'])
@async_endpoint
async def add_enrollment_sample():
    """Submit voice sample for enrollment"""
    try:
        enrollment_id = request.form.get('enrollment_id')
        device_hint = request.form.get('device_hint', 'unknown')
        
        if not enrollment_id:
            return jsonify({
                'success': False,
                'error': 'enrollment_id is required'
            }), 400
        
        # Handle audio data (base64 or file upload)
        audio_data = None
        
        if 'audio' in request.files:
            # File upload
            audio_file = request.files['audio']
            audio_data = audio_file.read()
        elif 'audio_base64' in request.form:
            # Base64 encoded audio
            audio_base64 = request.form['audio_base64']
            audio_data = base64.b64decode(audio_base64)
        else:
            return jsonify({
                'success': False,
                'error': 'Audio data required (file or base64)'
            }), 400
        
        if not audio_data:
            return jsonify({
                'success': False,
                'error': 'Invalid audio data'
            }), 400
        
        result = await voice_auth_service.add_enrollment_sample(
            enrollment_id=enrollment_id,
            audio_data=audio_data,
            device_hint=device_hint
        )
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Error adding enrollment sample: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================
# VERIFICATION ENDPOINTS
# ==========================

@voice_auth_bp.route('/api/voice-auth/verify', methods=['POST'])
@rate_limit(max_attempts=3, window=60)
@async_endpoint
async def verify_voice():
    """Verify voice identity"""
    try:
        user_id = request.form.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        # Handle audio data
        audio_data = None
        
        if 'audio' in request.files:
            audio_file = request.files['audio']
            audio_data = audio_file.read()
        elif 'audio_base64' in request.form:
            audio_base64 = request.form['audio_base64']
            audio_data = base64.b64decode(audio_base64)
        else:
            return jsonify({
                'success': False,
                'error': 'Audio data required (file or base64)'
            }), 400
        
        # Additional context
        ip_address = request.remote_addr
        device_info = request.headers.get('User-Agent')
        
        result = await voice_auth_service.verify_voice(
            user_id=user_id,
            audio_data=audio_data,
            ip_address=ip_address,
            device_info=device_info
        )
        
        return jsonify(result), 200 if result['success'] else 401
    
    except Exception as e:
        logger.error(f"Error verifying voice: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================
# CHALLENGE ENDPOINTS
# ==========================

@voice_auth_bp.route('/api/voice-auth/challenge', methods=['GET'])
@async_endpoint
async def get_challenge():
    """Get challenge question for medium confidence authentication"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id is required'
            }), 400
        
        result = await voice_auth_service.get_challenge_question(session_id)
        
        return jsonify(result), 200 if result['success'] else 400
    
    except Exception as e:
        logger.error(f"Error getting challenge: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_auth_bp.route('/api/voice-auth/challenge/answer', methods=['POST'])
@async_endpoint
async def answer_challenge():
    """Submit answer to challenge question"""
    try:
        data = request.json
        session_id = data.get('session_id')
        challenge_token = data.get('challenge_token')
        answer = data.get('answer')
        
        if not all([session_id, challenge_token, answer]):
            return jsonify({
                'success': False,
                'error': 'session_id, challenge_token, and answer are required'
            }), 400
        
        result = await voice_auth_service.answer_challenge(
            session_id=session_id,
            challenge_token=challenge_token,
            answer=answer
        )
        
        return jsonify(result), 200 if result['success'] else 401
    
    except Exception as e:
        logger.error(f"Error answering challenge: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================
# SESSION & STATUS ENDPOINTS
# ==========================

@voice_auth_bp.route('/api/voice-auth/status', methods=['GET'])
@async_endpoint
async def get_auth_status():
    """Check current authentication status"""
    try:
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id is required'
            }), 400
        
        result = await voice_auth_service.get_session_status(session_id)
        
        return jsonify(result), 200 if result['success'] else 404
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_auth_bp.route('/api/voice-auth/validate-access', methods=['POST'])
@async_endpoint
async def validate_memory_access():
    """Validate if session has access to specific memory category"""
    try:
        data = request.json
        session_id = data.get('session_id')
        memory_category = data.get('memory_category')
        
        if not session_id or not memory_category:
            return jsonify({
                'success': False,
                'error': 'session_id and memory_category are required'
            }), 400
        
        result = await voice_auth_service.validate_memory_access(
            session_id=session_id,
            memory_category=memory_category
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error validating access: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================
# PROFILE MANAGEMENT ENDPOINTS
# ==========================

@voice_auth_bp.route('/api/voice-auth/profiles', methods=['GET'])
@async_endpoint
async def list_voice_profiles():
    """List all voice profiles for a user"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        result = await voice_auth_service.list_voice_profiles(user_id)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_auth_bp.route('/api/voice-auth/profiles/<profile_id>', methods=['DELETE'])
@async_endpoint
async def delete_voice_profile(profile_id):
    """Delete a voice profile"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        result = await voice_auth_service.delete_voice_profile(
            user_id=user_id,
            profile_id=profile_id
        )
        
        return jsonify(result), 200 if result['success'] else 404
    
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================
# AUDIT & LOGGING ENDPOINTS
# ==========================

@voice_auth_bp.route('/api/voice-auth/logs', methods=['GET'])
@async_endpoint
async def get_authentication_logs():
    """Get authentication attempt logs"""
    try:
        user_id = request.args.get('user_id')  # Optional filter
        limit = int(request.args.get('limit', 100))
        
        result = await voice_auth_service.get_authentication_logs(
            user_id=user_id,
            limit=limit
        )
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================
# DEMO & TESTING ENDPOINTS
# ==========================

@voice_auth_bp.route('/api/voice-auth/demo/generate-sample', methods=['GET'])
def generate_demo_sample():
    """Generate a demo audio sample for testing"""
    try:
        text = request.args.get('text', 'Hello, this is my voice sample')
        
        # Generate demo audio
        audio_data = voice_auth_service.generate_demo_audio_sample(text)
        
        # Return as downloadable WAV file
        return send_file(
            io.BytesIO(audio_data),
            mimetype='audio/wav',
            as_attachment=True,
            download_name='demo_voice_sample.wav'
        )
    
    except Exception as e:
        logger.error(f"Error generating demo sample: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_auth_bp.route('/api/voice-auth/demo/quick-test', methods=['POST'])
@async_endpoint
async def quick_test():
    """Quick test endpoint for voice authentication flow"""
    try:
        data = request.json
        test_user_id = data.get('user_id', 'demo_user_1')
        test_action = data.get('action', 'verify')  # enroll or verify
        
        if test_action == 'enroll':
            # Start enrollment
            enrollment = await voice_auth_service.start_enrollment(
                user_id=test_user_id,
                display_name=f"Test User {test_user_id}"
            )
            
            if not enrollment['success']:
                return jsonify(enrollment), 400
            
            # Add 3 demo samples
            for i in range(3):
                sample_data = voice_auth_service.generate_demo_audio_sample(
                    f"Sample {i+1} for {test_user_id}"
                )
                
                result = await voice_auth_service.add_enrollment_sample(
                    enrollment_id=enrollment['enrollment_id'],
                    audio_data=sample_data,
                    device_hint="demo_device"
                )
                
                if not result['success']:
                    return jsonify(result), 400
            
            return jsonify({
                'success': True,
                'message': 'Demo enrollment completed',
                'enrollment_id': enrollment['enrollment_id'],
                'profile_id': result.get('profile_id')
            }), 200
        
        elif test_action == 'verify':
            # Generate test audio
            test_audio = voice_auth_service.generate_demo_audio_sample(
                f"Verification for {test_user_id}"
            )
            
            # Verify voice
            result = await voice_auth_service.verify_voice(
                user_id=test_user_id,
                audio_data=test_audio,
                ip_address="127.0.0.1",
                device_info="Demo Test Client"
            )
            
            return jsonify(result), 200 if result['success'] else 401
        
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid action. Use "enroll" or "verify"'
            }), 400
    
    except Exception as e:
        logger.error(f"Error in quick test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_auth_bp.route('/api/voice-auth/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'service': 'Voice Authentication Service',
        'status': 'operational',
        'demo_mode': voice_auth_service.demo_mode,
        'timestamp': datetime.now().isoformat()
    }), 200

# ==========================
# STATISTICS ENDPOINT
# ==========================

@voice_auth_bp.route('/api/voice-auth/stats', methods=['GET'])
def get_statistics():
    """Get voice authentication statistics"""
    try:
        # Calculate statistics
        total_profiles = sum(len(profiles) for profiles in voice_auth_service.voice_profiles.values())
        total_users = len(voice_auth_service.voice_profiles)
        active_sessions = len([s for s in voice_auth_service.auth_sessions.values() 
                              if s.expires_at > datetime.now()])
        total_attempts = len(voice_auth_service.auth_attempts)
        successful_attempts = len([a for a in voice_auth_service.auth_attempts if a.success])
        
        success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_profiles': total_profiles,
                'total_users': total_users,
                'active_sessions': active_sessions,
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'success_rate': f"{success_rate:.2f}%",
                'demo_mode': voice_auth_service.demo_mode
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def init_voice_auth_endpoints(app):
    """Initialize voice authentication endpoints in Flask app"""
    app.register_blueprint(voice_auth_bp)
    logger.info("🎙️ Voice Authentication API endpoints registered")
    logger.info("📍 Endpoints available at:")
    logger.info("   • POST /api/voice-auth/enroll/start")
    logger.info("   • POST /api/voice-auth/enroll/sample")
    logger.info("   • POST /api/voice-auth/verify")
    logger.info("   • GET  /api/voice-auth/challenge")
    logger.info("   • POST /api/voice-auth/challenge/answer")
    logger.info("   • GET  /api/voice-auth/status")
    logger.info("   • GET  /api/voice-auth/profiles")
    logger.info("   • GET  /api/voice-auth/health")
    logger.info("   • GET  /api/voice-auth/demo/generate-sample")
    logger.info("   • POST /api/voice-auth/demo/quick-test")

# Export for use in other modules
__all__ = ['voice_auth_bp', 'init_voice_auth_endpoints']