#!/usr/bin/env python3
"""
WhatsApp Cloud API Testing and Management Endpoints
Provides endpoints for testing and managing WhatsApp Cloud API integration
"""

from flask import Blueprint, request, jsonify
from whatsapp_cloud_api import whatsapp_cloud_api, SecurityLevel
import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create Blueprint
whatsapp_cloud_bp = Blueprint('whatsapp_cloud', __name__, url_prefix='/api/whatsapp')

@whatsapp_cloud_bp.route('/test/classify', methods=['POST'])
def test_classify_message():
    """Test message classification endpoint"""
    try:
        data = request.json
        content = data.get('content', '')
        
        # Classify the message
        security_level = whatsapp_cloud_api.classifier.classify_message(content)
        
        return jsonify({
            'success': True,
            'content': content,
            'security_level': security_level.value,
            'description': {
                'general': 'Casual conversations, greetings',
                'chronological': 'Time-based memories, appointments, events',
                'confidential': 'Personal information, relationships, emotions',
                'secret': 'Private information, health records, financial details',
                'ultra_secret': 'Credentials, seed phrases, highly sensitive data'
            }.get(security_level.value, 'Unknown')
        })
    except Exception as e:
        logger.error(f"Error in classification test: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@whatsapp_cloud_bp.route('/test/send', methods=['POST'])
async def test_send_message():
    """Test sending a WhatsApp message"""
    try:
        data = request.json
        to_number = data.get('to_number')
        message = data.get('message', 'Test message from Memory App')
        
        if not to_number:
            return jsonify({'success': False, 'error': 'to_number is required'}), 400
        
        # Send the message
        success = await whatsapp_cloud_api.send_message(to_number, message)
        
        return jsonify({
            'success': success,
            'to_number': to_number,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@whatsapp_cloud_bp.route('/test/store', methods=['POST'])
def test_store_message():
    """Test storing a message in the Markdown storage"""
    try:
        data = request.json
        phone_number = data.get('phone_number', '+15551234567')
        content = data.get('content', 'Test message for storage')
        security_level_str = data.get('security_level', 'general')
        
        # Get security level enum
        security_level = SecurityLevel[security_level_str.upper()]
        
        # Create message data
        message_data = {
            'id': data.get('id', 'test_msg_001'),
            'from': phone_number,
            'type': 'text',
            'text': {'body': content},
            'profile_name': data.get('profile_name', 'Test User'),
            'wa_id': phone_number
        }
        
        # Store the message
        success = whatsapp_cloud_api.storage.store_message(
            phone_number, 
            message_data, 
            security_level
        )
        
        return jsonify({
            'success': success,
            'phone_number': phone_number,
            'security_level': security_level.value,
            'content': content
        })
    except Exception as e:
        logger.error(f"Error storing test message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@whatsapp_cloud_bp.route('/memories/<phone_number>', methods=['GET'])
def get_contact_memories(phone_number):
    """Retrieve memories for a contact"""
    try:
        security_level_str = request.args.get('security_level')
        limit = int(request.args.get('limit', 10))
        
        security_level = None
        if security_level_str:
            security_level = SecurityLevel[security_level_str.upper()]
        
        # Get memories
        memories = whatsapp_cloud_api.storage.get_memories(
            phone_number,
            security_level,
            limit
        )
        
        return jsonify({
            'success': True,
            'phone_number': phone_number,
            'memories': memories,
            'count': len(memories)
        })
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@whatsapp_cloud_bp.route('/test/webhook', methods=['POST'])
async def test_webhook_processing():
    """Test webhook processing with sample data"""
    try:
        # Sample WhatsApp webhook data
        sample_data = {
            "entry": [{
                "id": "ENTRY_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550123456",
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "messages": [{
                            "from": request.json.get('from', '+15551234567'),
                            "id": "wamid.TEST_MESSAGE_ID",
                            "timestamp": "1669233778",
                            "text": {
                                "body": request.json.get('message', 'Test message for webhook processing')
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        # Process the webhook
        result = await whatsapp_cloud_api.process_webhook(sample_data)
        
        return jsonify({
            'success': True,
            'webhook_result': result,
            'test_data': sample_data
        })
    except Exception as e:
        logger.error(f"Error in webhook test: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@whatsapp_cloud_bp.route('/status', methods=['GET'])
def get_api_status():
    """Get WhatsApp Cloud API configuration status"""
    return jsonify({
        'configured': bool(whatsapp_cloud_api.access_token),
        'phone_number_id': whatsapp_cloud_api.phone_number_id or 'Not configured',
        'api_version': whatsapp_cloud_api.api_version,
        'storage_base_dir': str(whatsapp_cloud_api.storage.base_dir),
        'security_levels': [level.value for level in SecurityLevel],
        'demo_mode': not bool(whatsapp_cloud_api.access_token)
    })

def init_whatsapp_cloud_endpoints(app):
    """Initialize WhatsApp Cloud API endpoints"""
    app.register_blueprint(whatsapp_cloud_bp)
    logger.info("📱 WhatsApp Cloud API endpoints initialized")