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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from md_file_manager import MDFileManager, MemoryTag
    from md_file_organizer import MDFileOrganizer
    from conversation_classifier import ConversationClassifier, ConversationContext
    from enhanced_user_onboarding import EnhancedUserOnboarding
    from daily_memory_manager import DailyMemoryManager
    from confidential_manager import ConfidentialManager, SecurityLevel, AuthMethod, AccessLevel
    
    # Import agents
    from agents import (
        AgentFactory,
        MemoryHarvesterAgent,
        PatternAnalyzerAgent,
        SourceType,
        ContentType,
        RawMemoryInput,
        PatternType,
        MEMORY_HARVESTER_AVAILABLE,
        PATTERN_ANALYZER_AVAILABLE
    )
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
    
    class MDFileOrganizer:
        async def mark_memory_agreed(self, *args, **kwargs):
            return {'success': True, 'message': 'Mock memory agreed'}
        async def mark_memory_not_agreed(self, *args, **kwargs):
            return {'success': True, 'message': 'Mock memory not agreed'}
        async def get_pending_memories(self, *args, **kwargs):
            return {'success': True, 'memories': [], 'count': 0}
    
    # Mock agent classes
    MEMORY_HARVESTER_AVAILABLE = False
    PATTERN_ANALYZER_AVAILABLE = False
    
    class AgentFactory:
        @staticmethod
        def create_memory_harvester(config=None):
            return None
        @staticmethod
        def create_pattern_analyzer(config=None):
            return None

memory_bp = Blueprint('memory', __name__)

# Initialize memory system components
md_manager = MDFileManager()
md_organizer = MDFileOrganizer()
classifier = ConversationClassifier()
onboarding = EnhancedUserOnboarding()
security_manager = ConfidentialManager()

# Initialize agents
memory_harvester = None
pattern_analyzer = None

if MEMORY_HARVESTER_AVAILABLE:
    memory_harvester = AgentFactory.create_memory_harvester({
        'md_file_manager': md_manager,
        'conversation_classifier': classifier
    })

if PATTERN_ANALYZER_AVAILABLE:
    pattern_analyzer = AgentFactory.create_pattern_analyzer({
        'md_file_manager': md_manager,
        'conversation_classifier': classifier
    })

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

@memory_bp.route('/memory/agree', methods=['POST'])
@cross_origin()
def mark_memory_agreed():
    """Mark a memory as agreed by the user"""
    try:
        phone_number = session.get('user_phone')
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        data = request.get_json()
        memory_id = data.get('memory_id')
        
        if not memory_id:
            return jsonify({
                'success': False,
                'message': 'Memory ID is required'
            }), 400
        
        # Mark memory as agreed
        result = run_async(md_organizer.mark_memory_agreed(phone_number, memory_id))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to mark memory as agreed: {str(e)}'
        }), 500

@memory_bp.route('/memory/disagree', methods=['POST'])
@cross_origin()
def mark_memory_not_agreed():
    """Mark a memory as not agreed by the user"""
    try:
        phone_number = session.get('user_phone')
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        data = request.get_json()
        memory_id = data.get('memory_id')
        
        if not memory_id:
            return jsonify({
                'success': False,
                'message': 'Memory ID is required'
            }), 400
        
        # Mark memory as not agreed
        result = run_async(md_organizer.mark_memory_not_agreed(phone_number, memory_id))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to mark memory as not agreed: {str(e)}'
        }), 500

@memory_bp.route('/memory/pending', methods=['GET'])
@cross_origin()
def get_pending_memories():
    """Get memories pending review for the user"""
    try:
        phone_number = session.get('user_phone')
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401
        
        # Get pending memories
        result = run_async(md_organizer.get_pending_memories(phone_number))
        
        # Format memories for the frontend
        if result['success']:
            memories = result.get('memories', [])
            formatted_memories = []
            
            for memory in memories:
                formatted_memories.append({
                    'id': memory.get('id'),
                    'content': memory.get('content'),
                    'tag': memory.get('tag'),
                    'timestamp': memory.get('timestamp'),
                    'agreement_status': 'pending'
                })
            
            return jsonify({
                'success': True,
                'memories': formatted_memories,
                'count': len(formatted_memories)
            })
        else:
            return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get pending memories: {str(e)}'
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

@memory_bp.route('/api/voice/search', methods=['POST'])
@cross_origin()
def voice_search():
    """Voice-authenticated memory search endpoint"""
    try:
        # Import voice memory search if available
        try:
            from voice_memory_search import voice_memory_search
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Voice memory search service not available'
            }), 503
        
        data = request.get_json()
        user_phone = data.get('user_phone') or session.get('user_phone')
        voice_session_token = data.get('voice_session_token')
        query = data.get('query')
        voice_audio_base64 = data.get('voice_audio')  # Optional base64 encoded audio
        
        if not user_phone or not query:
            return jsonify({
                'success': False,
                'error': 'User phone and query are required'
            }), 400
        
        if not voice_session_token:
            return jsonify({
                'success': False,
                'error': 'Voice authentication required. Please authenticate with your voice first.',
                'authentication_required': True,
                'method_required': 'voice'
            }), 401
        
        # Convert base64 audio to bytes if provided
        voice_audio_data = None
        if voice_audio_base64:
            import base64
            try:
                voice_audio_data = base64.b64decode(voice_audio_base64)
            except:
                pass
        
        # Perform voice-authenticated search
        result = run_async(voice_memory_search.search_memories_by_voice(
            user_id=user_phone,
            voice_query=query,
            session_token=voice_session_token,
            voice_audio_data=voice_audio_data
        ))
        
        if result.get('success'):
            return jsonify(result)
        else:
            # Check if authentication failed
            if result.get('authentication_required'):
                return jsonify(result), 401
            else:
                return jsonify(result), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Voice search failed: {str(e)}'
        }), 500

@memory_bp.route('/api/text/search', methods=['POST'])
@cross_origin()
def text_search():
    """Text-based memory search - LIMITED to non-secure memories only"""
    try:
        # Import voice memory search if available
        try:
            from voice_memory_search import voice_memory_search
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Memory search service not available'
            }), 503
        
        data = request.get_json()
        user_phone = data.get('user_phone') or session.get('user_phone')
        query = data.get('query')
        auth_token = data.get('auth_token') or session.get('session_token')
        
        if not user_phone or not query:
            return jsonify({
                'success': False,
                'error': 'User phone and query are required'
            }), 400
        
        # Perform text search (limited to non-secure memories)
        result = run_async(voice_memory_search.search_memories_by_text(
            user_id=user_phone,
            text_query=query,
            auth_token=auth_token
        ))
        
        if result.get('success'):
            return jsonify(result)
        else:
            # Check if secure content was detected
            if result.get('secure_content_detected'):
                return jsonify(result), 403  # Forbidden - requires voice auth
            else:
                return jsonify(result), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Text search failed: {str(e)}'
        }), 500

@memory_bp.route('/api/search/stats', methods=['GET'])
@cross_origin()
def get_search_stats():
    """Get search statistics for the authenticated user"""
    try:
        # Import voice memory search if available
        try:
            from voice_memory_search import voice_memory_search
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Memory search service not available'
            }), 503
        
        user_phone = request.args.get('user_phone') or session.get('user_phone')
        
        if not user_phone:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # Get search statistics
        stats = run_async(voice_memory_search.get_search_statistics(user_phone))
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get search statistics: {str(e)}'
        }), 500

# ==========================
# AGENT API ENDPOINTS
# ==========================

@memory_bp.route('/harvest', methods=['POST'])
@cross_origin()
def trigger_harvest():
    """Trigger memory harvesting from various sources"""
    if not MEMORY_HARVESTER_AVAILABLE or not memory_harvester:
        return jsonify({
            'error': 'Memory Harvester Agent not available',
            'success': False
        }), 503
    
    try:
        data = request.get_json()
        user_id = session.get('user_phone', data.get('user_id', 'default_user'))
        source_type = data.get('source_type', 'manual_entry')
        content = data.get('content', '')
        
        # Create raw memory input
        raw_input = RawMemoryInput(
            content=content,
            source_type=SourceType[source_type.upper()] if hasattr(SourceType, source_type.upper()) else SourceType.MANUAL_ENTRY,
            source_metadata={'channel': 'dashboard_api', 'timestamp': datetime.now().isoformat()},
            user_id=user_id
        )
        
        # Initialize if needed
        if not memory_harvester.is_initialized:
            run_async(memory_harvester.initialize())
        
        # Process the memory
        processed_memory = run_async(memory_harvester.process_memory(raw_input))
        
        return jsonify({
            'success': True,
            'memory_id': processed_memory.id,
            'quality_score': processed_memory.quality_score,
            'quality_level': processed_memory.quality_level.value,
            'tags': processed_memory.tags,
            'content': processed_memory.content,
            'metadata': processed_memory.metadata
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@memory_bp.route('/patterns', methods=['GET'])
@cross_origin()
def get_patterns():
    """Get detected behavioral patterns for a user"""
    if not PATTERN_ANALYZER_AVAILABLE or not pattern_analyzer:
        return jsonify({
            'error': 'Pattern Analyzer Agent not available',
            'success': False
        }), 503
    
    try:
        user_id = session.get('user_phone', request.args.get('user_id', 'default_user'))
        pattern_type = request.args.get('pattern_type', None)
        
        # Initialize if needed
        if not pattern_analyzer.is_initialized:
            run_async(pattern_analyzer.initialize())
        
        # Get patterns
        if pattern_type:
            patterns = run_async(
                pattern_analyzer.get_patterns_by_type(user_id, PatternType[pattern_type.upper()])
            )
        else:
            patterns = run_async(pattern_analyzer.get_all_patterns(user_id))
        
        # Convert to JSON-serializable format
        patterns_data = []
        if patterns:
            for pattern in patterns:
                patterns_data.append({
                    'id': pattern.id,
                    'type': pattern.pattern_type.value,
                    'strength': pattern.strength.value,
                    'confidence': pattern.confidence,
                    'description': pattern.description,
                    'frequency': pattern.frequency,
                    'triggers': pattern.triggers,
                    'participants': pattern.participants
                })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'patterns': patterns_data,
            'count': len(patterns_data)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@memory_bp.route('/insights', methods=['GET'])
@cross_origin()
def get_insights():
    """Get behavioral insights and predictions"""
    if not PATTERN_ANALYZER_AVAILABLE or not pattern_analyzer:
        return jsonify({
            'error': 'Pattern Analyzer Agent not available',
            'success': False
        }), 503
    
    try:
        user_id = session.get('user_phone', request.args.get('user_id', 'default_user'))
        
        # Initialize if needed
        if not pattern_analyzer.is_initialized:
            run_async(pattern_analyzer.initialize())
        
        # Get insights
        insights = run_async(pattern_analyzer.generate_insights(user_id))
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'insights': insights if insights else []
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

