#!/usr/bin/env python3
"""
Memory API Routes - Flask backend for Memory System
Handles all memory-related operations and integrates with our memory components
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin

# Add the parent directory to the path to import our memory system
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from memory_system.md_file_manager import MDFileManager, MemoryTag
    from memory_system.conversation_classifier import ConversationClassifier, ConversationContext
    from memory_system.enhanced_user_onboarding import EnhancedUserOnboarding
    from memory_system.daily_memory_manager import DailyMemoryManager
    from memory_system.confidential_manager import ConfidentialManager, SecurityLevel, AuthMethod, AccessLevel
except ImportError as e:
    print(f"Warning: Could not import memory system components: {e}")
    # Create mock classes for development
    class MDFileManager:
        async def create_user_file(self, *args, **kwargs):
            return {'success': True, 'message': 'Mock user created'}
        async def get_user_memories(self, *args, **kwargs):
            return {'success': True, 'memories': []}
        async def update_file(self, *args, **kwargs):
            return {'success': True, 'message': 'Mock memory saved'}
        async def search_memories(self, *args, **kwargs):
            return {'success': True, 'memories': []}
        async def get_file_stats(self, *args, **kwargs):
            return {'success': True, 'stats': {}}
    
    class ConversationClassifier:
        async def classify_message(self, *args, **kwargs):
            from dataclasses import dataclass
            from enum import Enum
            class MemoryTag(Enum):
                GENERAL = "general"
            class Confidence(Enum):
                HIGH = "high"
            @dataclass
            class ClassificationResult:
                primary_tag = MemoryTag.GENERAL
                confidence = Confidence.HIGH
                related_contacts = []
                topics = []
                reasoning = "Mock classification"
            return ClassificationResult()
    
    class ConversationContext:
        def __init__(self, **kwargs):
            pass
    
    class EnhancedUserOnboarding:
        def __init__(self, **kwargs):
            pass
        async def register_new_user(self, *args, **kwargs):
            return {'success': True, 'message': 'Mock user registered'}
        async def handle_onboarding_response(self, *args, **kwargs):
            return {'response': 'Mock onboarding response'}
    
    class ConfidentialManager:
        async def create_security_profile(self, *args, **kwargs):
            return {'success': True, 'message': 'Mock security profile created'}
        async def authenticate_user(self, *args, **kwargs):
            return {'success': True, 'session_token': 'mock_token'}
    
    class SecurityLevel:
        STANDARD = "standard"
    
    class AuthMethod:
        PASSWORD = "password"
    
    class AccessLevel:
        PRIVATE = "private"
    
    class MemoryTag:
        GENERAL = "general"

memory_bp = Blueprint('memory', __name__)

# Initialize memory system components
md_manager = MDFileManager()
classifier = ConversationClassifier()
onboarding = EnhancedUserOnboarding()
security_manager = ConfidentialManager()

def run_async(coro):
    """Helper function to run async functions in Flask routes"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@memory_bp.route('/signup', methods=['POST'])
@cross_origin()
def signup():
    """Handle user signup"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        name = data.get('name')
        password = data.get('password')
        
        if not phone_number or not password:
            return jsonify({
                'success': False,
                'message': 'Phone number and password are required'
            }), 400
        
        # Create security profile
        security_result = run_async(security_manager.create_security_profile(
            user_phone=phone_number,
            master_password=password,
            security_level=SecurityLevel.STANDARD,
            auth_methods=[AuthMethod.PASSWORD]
        ))
        
        if not security_result['success']:
            return jsonify(security_result), 400
        
        # Register user with onboarding system
        onboarding_result = run_async(onboarding.register_new_user(phone_number, name))
        
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': {
                'phone_number': phone_number,
                'name': name
            },
            'security': security_result,
            'onboarding': onboarding_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Signup failed: {str(e)}'
        }), 500

@memory_bp.route('/login', methods=['POST'])
@cross_origin()
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        password = data.get('password')
        
        if not phone_number or not password:
            return jsonify({
                'success': False,
                'message': 'Phone number and password are required'
            }), 400
        
        # Authenticate user
        auth_result = run_async(security_manager.authenticate_user(
            user_phone=phone_number,
            auth_method=AuthMethod.PASSWORD,
            credentials={'password': password},
            access_level=AccessLevel.PRIVATE
        ))
        
        if auth_result['success']:
            session['user_phone'] = phone_number
            session['session_token'] = auth_result['session_token']
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'phone_number': phone_number
                },
                'session_token': auth_result['session_token']
            })
        else:
            return jsonify(auth_result), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Login failed: {str(e)}'
        }), 500

@memory_bp.route('/memories', methods=['GET'])
@cross_origin()
def get_memories():
    """Get user memories in chat format"""
    try:
        phone_number = session.get('user_phone')
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Get memories from MD file manager
        memories_result = run_async(md_manager.get_user_memories(phone_number, limit=100))
        
        if not memories_result['success']:
            return jsonify(memories_result), 400
        
        # Format memories as chat messages
        chat_messages = []
        for memory in memories_result['memories']:
            message = {
                'id': memory.get('id', ''),
                'content': memory.get('content', ''),
                'timestamp': memory.get('metadata', {}).get('time', ''),
                'tag': memory.get('metadata', {}).get('tag', ''),
                'type': 'memory',
                'sender': 'user'
            }
            chat_messages.append(message)
        
        # Sort by timestamp
        chat_messages.sort(key=lambda x: x['timestamp'])
        
        return jsonify({
            'success': True,
            'messages': chat_messages,
            'count': len(chat_messages)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get memories: {str(e)}'
        }), 500

@memory_bp.route('/chat', methods=['POST'])
@cross_origin()
def chat_with_agent():
    """Handle chat messages with the memory agent"""
    try:
        phone_number = session.get('user_phone')
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400
        
        # Classify the message
        context = ConversationContext(
            user_phone=phone_number,
            conversation_history=[],
            known_contacts=[],
            recent_topics=[]
        )
        
        classification = run_async(classifier.classify_message(message, context))
        
        # Save the memory
        memory_result = run_async(md_manager.update_file(
            phone_number=phone_number,
            message=message,
            tag=classification.primary_tag,
            source=phone_number,
            context="User chat message",
            related_contacts=classification.related_contacts
        ))
        
        # Generate agent response
        agent_response = generate_agent_response(message, classification)
        
        # Return both user message and agent response
        return jsonify({
            'success': True,
            'messages': [
                {
                    'id': f"user_{datetime.now().isoformat()}",
                    'content': message,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'user_message',
                    'sender': 'user',
                    'classification': {
                        'tag': classification.primary_tag.value,
                        'confidence': classification.confidence.value,
                        'reasoning': classification.reasoning
                    }
                },
                {
                    'id': f"agent_{datetime.now().isoformat()}",
                    'content': agent_response,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'agent_response',
                    'sender': 'agent'
                }
            ],
            'memory_saved': memory_result['success']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Chat failed: {str(e)}'
        }), 500

@memory_bp.route('/search', methods=['POST'])
@cross_origin()
def search_memories():
    """Search memories"""
    try:
        phone_number = session.get('user_phone')
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        # Search memories
        search_result = run_async(md_manager.search_memories(phone_number, query))
        
        if not search_result['success']:
            return jsonify(search_result), 400
        
        # Format as chat messages
        chat_messages = []
        for memory in search_result['memories']:
            message = {
                'id': memory.get('id', ''),
                'content': memory.get('content', ''),
                'timestamp': memory.get('metadata', {}).get('time', ''),
                'tag': memory.get('metadata', {}).get('tag', ''),
                'type': 'search_result',
                'sender': 'user',
                'relevance_score': memory.get('relevance_score', 0)
            }
            chat_messages.append(message)
        
        return jsonify({
            'success': True,
            'messages': chat_messages,
            'query': query,
            'count': len(chat_messages)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Search failed: {str(e)}'
        }), 500

@memory_bp.route('/stats', methods=['GET'])
@cross_origin()
def get_stats():
    """Get user memory statistics"""
    try:
        phone_number = session.get('user_phone')
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Get file stats
        stats_result = run_async(md_manager.get_file_stats(phone_number))
        
        return jsonify(stats_result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get stats: {str(e)}'
        }), 500

@memory_bp.route('/logout', methods=['POST'])
@cross_origin()
def logout():
    """Handle user logout"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Logout failed: {str(e)}'
        }), 500

def generate_agent_response(user_message, classification):
    """Generate appropriate agent response based on message classification"""
    
    responses = {
        'general': [
            "Got it! I've saved that information for you. 📝",
            "Thanks for sharing! I'll remember that. 🧠",
            "Noted! This information is now in your memory bank. ✅",
            "Perfect! I've stored that detail for future reference. 💾"
        ],
        'chronological': [
            "I've added this to your timeline! ⏰",
            "This event is now recorded in your chronological memories. 📅",
            "Timeline updated! I'll help you remember this moment. 🕐",
            "Added to your personal history! 📖"
        ],
        'confidential': [
            "This sensitive information has been securely stored. 🔒",
            "I've saved this with enhanced privacy protection. 🛡️",
            "Confidential information secured in your private vault. 🔐",
            "This private detail is safely stored and encrypted. 🔑"
        ],
        'secret': [
            "This highly sensitive information is now in maximum security storage. 🔒🔒",
            "Secret information secured with advanced encryption. 🛡️✨",
            "This is safely locked away in your most secure vault. 🔐🔐",
            "Maximum security protocols applied to this sensitive data. 🔑🛡️"
        ],
        'ultra_secret': [
            "Ultra-secure storage activated for this information. 🔒🔒🔒",
            "This information requires special authentication to access. 🛡️🔐",
            "Maximum security level applied. This data is ultra-protected. 🔑🛡️🔒",
            "Top-secret information secured with biometric protection. 🔐✨🛡️"
        ]
    }
    
    tag = classification.primary_tag.value
    import random
    
    if tag in responses:
        base_response = random.choice(responses[tag])
    else:
        base_response = "I've processed and saved your message. 💭"
    
    # Add contextual information
    if classification.related_contacts:
        base_response += f"\n\nI noticed you mentioned: {', '.join(classification.related_contacts)}"
    
    if classification.topics:
        base_response += f"\n\nTopics identified: {', '.join(classification.topics)}"
    
    return base_response

