#!/usr/bin/env python3
"""
WhatsApp Cloud API Integration for Memory App
Handles message classification, Markdown storage, and WhatsApp Cloud API communication
"""

import os
import json
import requests
import hashlib
import hmac
import yaml
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import re
import logging
from pathlib import Path
import sys

# Add app directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import search functionality
try:
    from app.memory.search import search_contact_memories
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# Import voice guard and session management
try:
    from app.voice.guard import voice_guard
    from app.security.session import session_manager
    VOICE_GUARD_AVAILABLE = True
except ImportError:
    VOICE_GUARD_AVAILABLE = False
    voice_guard = None
    session_manager = None

# Import voice processing modules
try:
    from app.voice.transcription import voice_transcriber
    from app.voice.synthesis import voice_synthesizer
    VOICE_PROCESSING_AVAILABLE = True
except ImportError:
    VOICE_PROCESSING_AVAILABLE = False
    voice_transcriber = None
    voice_synthesizer = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log import availability
if not SEARCH_AVAILABLE:
    logger.warning("⚠️ Search functionality not available")
if not VOICE_GUARD_AVAILABLE:
    logger.warning("⚠️ Voice guard functionality not available")
if not VOICE_PROCESSING_AVAILABLE:
    logger.warning("⚠️ Voice processing functionality not available")

class SecurityLevel(Enum):
    """Security levels for message classification"""
    GENERAL = "general"  # Casual conversations, greetings, etc.
    CHRONOLOGICAL = "chronological"  # Time-based memories, appointments, events
    CONFIDENTIAL = "confidential"  # Personal information, relationships, emotions
    SECRET = "secret"  # Private information, health records, financial details
    ULTRA_SECRET = "ultra_secret"  # Credentials, seed phrases, highly sensitive data

class MessageClassifier:
    """Classifies messages into security levels based on content"""
    
    # Pattern definitions for different security levels
    PATTERNS = {
        SecurityLevel.ULTRA_SECRET: [
            r'\b(?:seed\s+phrase|recovery\s+phrase|mnemonic|private\s+key)\b',
            r'\b[0-9a-fA-F]{64}\b',  # Private keys
            r'\b(?:password|passwd|pwd|pass)[\s:=]+\S+',
            r'\bBearer\s+[A-Za-z0-9\-._~\+\/]+=*\b',  # Bearer tokens
            r'\b(?:api[_-]?key|apikey|secret[_-]?key)[\s:=]+\S+',
            r'\b(?:BTC|ETH|crypto|wallet).*(?:address|key|seed)\b',
        ],
        SecurityLevel.SECRET: [
            r'\b(?:ssn|social\s+security)\b',
            r'\b(?:credit\s+card|debit\s+card|cvv|cvc)\b',
            r'\b(?:bank\s+account|routing\s+number|iban)\b',
            r'\b(?:medical|diagnosis|prescription|medication)\b',
            r'\b(?:salary|income|tax|financial)\b',
            r'\$\d{4,}',  # Large monetary amounts
            r'\b(?:pin\s+code|pin\s+number|access\s+code)\b',
        ],
        SecurityLevel.CONFIDENTIAL: [
            r'\b(?:love|relationship|breakup|divorce|marriage)\b',
            r'\b(?:pregnant|pregnancy|baby|birth)\b',
            r'\b(?:fired|laid\s+off|terminated|resignation)\b',
            r'\b(?:email|phone\s+number|address|date\s+of\s+birth)\b',
            r'\b(?:family|mother|father|brother|sister|child)\b',
            r'\b(?:anxiety|depression|therapy|counseling)\b',
            r'\b(?:confidential|private|personal|sensitive)\b',
        ],
        SecurityLevel.CHRONOLOGICAL: [
            r'\b(?:tomorrow|yesterday|today|next\s+week|last\s+week)\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:appointment|meeting|deadline|schedule|calendar)\b',
            r'\b(?:birthday|anniversary|holiday|vacation)\b',
            r'\b\d{1,2}[:\/]\d{1,2}(?:[:\/]\d{2,4})?\b',  # Dates
            r'\b\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?\b',  # Times
        ]
    }
    
    @classmethod
    def classify_message(cls, content: str) -> SecurityLevel:
        """Classify a message based on its content"""
        content_lower = content.lower()
        
        # Check patterns in order of sensitivity (highest to lowest)
        for level in [SecurityLevel.ULTRA_SECRET, SecurityLevel.SECRET, 
                     SecurityLevel.CONFIDENTIAL, SecurityLevel.CHRONOLOGICAL]:
            patterns = cls.PATTERNS.get(level, [])
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    logger.info(f"🔐 Message classified as: {level.value}")
                    return level
        
        # Default to GENERAL if no patterns match
        return SecurityLevel.GENERAL

class MarkdownMemoryStorage:
    """Handles storing WhatsApp messages in Markdown format with YAML frontmatter"""
    
    def __init__(self, base_dir: str = "memory-system/data/contacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_contact_dir(self, phone_number: str) -> Path:
        """Get or create contact directory"""
        # Sanitize phone number for directory name
        sanitized_phone = re.sub(r'[^\d+]', '', phone_number)
        contact_dir = self.base_dir / sanitized_phone / "memories"
        contact_dir.mkdir(parents=True, exist_ok=True)
        return contact_dir
    
    def _get_memory_file(self, phone_number: str, security_level: SecurityLevel) -> Path:
        """Get the memory file path for a specific security level"""
        contact_dir = self._get_contact_dir(phone_number)
        return contact_dir / f"{security_level.value}.md"
    
    def store_message(self, phone_number: str, message_data: Dict[str, Any], 
                     security_level: SecurityLevel) -> bool:
        """Store a message in the appropriate Markdown file"""
        try:
            file_path = self._get_memory_file(phone_number, security_level)
            
            # Prepare YAML frontmatter
            frontmatter = {
                'id': message_data.get('id'),
                'timestamp': message_data.get('timestamp', datetime.now().isoformat()),
                'from': message_data.get('from'),
                'type': message_data.get('type', 'text'),
                'security_level': security_level.value,
                'platform': 'whatsapp',
                'metadata': {
                    'profile_name': message_data.get('profile_name'),
                    'wa_id': message_data.get('wa_id'),
                }
            }
            
            # Handle different message types
            content = ""
            if message_data.get('type') == 'text':
                content = message_data.get('text', {}).get('body', '')
            elif message_data.get('type') == 'image':
                content = f"[Image: {message_data.get('image', {}).get('caption', 'No caption')}]"
                frontmatter['metadata']['media_id'] = message_data.get('image', {}).get('id')
            elif message_data.get('type') == 'audio':
                content = "[Audio message]"
                frontmatter['metadata']['media_id'] = message_data.get('audio', {}).get('id')
            elif message_data.get('type') == 'document':
                content = f"[Document: {message_data.get('document', {}).get('filename', 'Unknown')}]"
                frontmatter['metadata']['media_id'] = message_data.get('document', {}).get('id')
            
            # Create the Markdown entry
            entry = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n"
            entry += f"## Memory Entry\n\n"
            entry += f"{content}\n\n"
            entry += f"---\n\n"
            
            # Append to the file
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(entry)
            
            logger.info(f"✅ Message stored in {security_level.value} category for {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store message: {e}")
            return False
    
    def get_memories(self, phone_number: str, security_level: Optional[SecurityLevel] = None,
                    limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve memories for a contact"""
        memories = []
        
        if security_level:
            levels = [security_level]
        else:
            # Get from all levels, from least to most sensitive
            levels = list(SecurityLevel)
        
        for level in levels:
            file_path = self._get_memory_file(phone_number, level)
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Parse the Markdown file (simple parser for now)
                    entries = content.split('---\n\n')
                    for entry in entries[-limit:]:  # Get last N entries
                        if entry.strip():
                            memories.append({
                                'security_level': level.value,
                                'content': entry.strip()
                            })
                except Exception as e:
                    logger.error(f"Error reading {level.value} memories: {e}")
        
        return memories

class WhatsAppCloudAPI:
    """Handles WhatsApp Cloud API communication"""
    
    def __init__(self):
        self.access_token = os.environ.get('WHATSAPP_BUSINESS_API_TOKEN', os.environ.get('META_ACCESS_TOKEN', ''))
        self.phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', os.environ.get('WA_PHONE_NUMBER_ID', ''))
        self.verify_token = os.environ.get('WHATSAPP_VERIFY_TOKEN', os.environ.get('META_VERIFY_TOKEN', 'memory_app_2025'))
        self.api_version = 'v18.0'
        self.base_url = f'https://graph.facebook.com/{self.api_version}'
        
        # Initialize storage and classifier
        self.storage = MarkdownMemoryStorage()
        self.classifier = MessageClassifier()
        
        if not self.access_token:
            logger.warning("⚠️ WhatsApp API token not set - running in demo mode")
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify webhook subscription from Meta"""
        if mode == 'subscribe' and token == self.verify_token:
            logger.info("✅ WhatsApp webhook verified successfully")
            return challenge
        else:
            logger.error("❌ WhatsApp webhook verification failed")
            return None
    
    def verify_signature(self, signature: str, payload: bytes) -> bool:
        """Verify webhook signature from Meta"""
        if not signature:
            return False
        
        expected = hmac.new(
            self.verify_token.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    async def process_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook from WhatsApp"""
        results = []
        
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    
                    # Process messages
                    if 'messages' in value:
                        for message in value['messages']:
                            result = await self.process_message(message, value.get('metadata', {}))
                            results.append(result)
                    
                    # Process status updates
                    if 'statuses' in value:
                        for status in value['statuses']:
                            logger.info(f"📊 Status update: {status}")
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            logger.error(f"❌ Error processing webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    def download_media(self, media_id: str) -> Optional[bytes]:
        """Download media from WhatsApp Cloud API"""
        if not self.access_token:
            logger.warning("⚠️ No access token for media download")
            return None
        
        try:
            # First, get the media URL
            url = f"{self.base_url}/{media_id}"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            media_info = response.json()
            
            # Download the media file
            media_url = media_info.get('url')
            if media_url:
                media_response = requests.get(media_url, headers=headers)
                media_response.raise_for_status()
                logger.info(f"✅ Downloaded media ({len(media_response.content)} bytes)")
                return media_response.content
            
        except Exception as e:
            logger.error(f"❌ Failed to download media: {e}")
        
        return None
    
    async def send_audio_message(self, to_number: str, audio_data: bytes) -> bool:
        """Send an audio message via WhatsApp Cloud API"""
        if not self.access_token or not self.phone_number_id:
            logger.warning("⚠️ WhatsApp Cloud API not configured for audio")
            return False
        
        try:
            # Upload audio to WhatsApp if synthesizer is available
            if VOICE_PROCESSING_AVAILABLE and voice_synthesizer:
                media_id = voice_synthesizer.upload_to_whatsapp(
                    audio_data, 
                    self.access_token, 
                    self.phone_number_id
                )
                
                if media_id:
                    # Send the audio message
                    url = f"{self.base_url}/{self.phone_number_id}/messages"
                    headers = {
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    data = {
                        'messaging_product': 'whatsapp',
                        'to': to_number,
                        'type': 'audio',
                        'audio': {
                            'id': media_id
                        }
                    }
                    
                    response = requests.post(url, headers=headers, json=data)
                    response.raise_for_status()
                    logger.info(f"✅ Audio message sent to {to_number}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to send audio message: {e}")
        
        return False
    
    async def process_message(self, message: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming WhatsApp message"""
        try:
            from_number = message.get('from')
            message_type = message.get('type')
            message_id = message.get('id')
            timestamp = message.get('timestamp')
            
            # Validate required fields
            if not from_number:
                logger.error("Missing 'from' field in message")
                return {
                    'success': False,
                    'error': 'Missing sender phone number'
                }
            
            logger.info(f"📱 Processing {message_type} message from {from_number}")
            
            # Handle audio messages with voice processing
            if message_type == 'audio' and VOICE_PROCESSING_AVAILABLE:
                audio_info = message.get('audio', {})
                media_id = audio_info.get('id')
                
                if media_id and voice_transcriber:
                    # Download the audio
                    audio_data = self.download_media(media_id)
                    
                    if audio_data:
                        # Transcribe the audio
                        success, transcribed_text = voice_transcriber.transcribe_audio(audio_data, 'ogg')
                        
                        if success and transcribed_text:
                            logger.info(f"🎤 Transcribed: {transcribed_text}")
                            
                            # Process the transcribed text as a command
                            command = voice_transcriber.process_voice_command(transcribed_text)
                            
                            # Generate response text based on command type
                            response_text = ""
                            
                            if command['type'] == 'verify':
                                # Handle verification
                                if VOICE_GUARD_AVAILABLE and voice_guard and session_manager and from_number:
                                    result = voice_guard.verify_passphrase(from_number, command['passphrase'])
                                    
                                    if result['verified']:
                                        session_manager.create_session(from_number)
                                        response_text = result['message'] + f"\n\nSession expires in {session_manager.ttl_minutes} minutes."
                                    else:
                                        response_text = result['message']
                                else:
                                    response_text = "Voice guard functionality is currently unavailable."
                            
                            elif command['type'] == 'enroll':
                                # Handle enrollment
                                if VOICE_GUARD_AVAILABLE and voice_guard and from_number:
                                    result = voice_guard.enroll_passphrase(from_number, command['passphrase'])
                                    response_text = result['message']
                                else:
                                    response_text = "Voice guard functionality is currently unavailable."
                            
                            elif command['type'] == 'search':
                                # Handle search
                                if SEARCH_AVAILABLE and from_number and 'search_contact_memories' in globals():
                                    # Get allowed categories
                                    if VOICE_GUARD_AVAILABLE and session_manager:
                                        allowed_categories = session_manager.get_allowed_categories(from_number)
                                    else:
                                        allowed_categories = ['general', 'chronological', 'confidential']
                                    
                                    # Perform search
                                    search_result = search_contact_memories(
                                        phone_number=from_number,
                                        query=command['query'],
                                        allowed_categories=allowed_categories,
                                        limit=6
                                    )
                                    
                                    response_text = search_result['formatted']
                                    
                                    # Add session status if verified
                                    if VOICE_GUARD_AVAILABLE and session_manager and from_number and session_manager.is_verified(from_number):
                                        time_remaining = session_manager.get_time_remaining(from_number)
                                        response_text += f"\n\nSecret access active ({time_remaining} min remaining)"
                                else:
                                    response_text = "Search functionality is currently unavailable."
                            
                            # Send voice response if synthesizer is available
                            if voice_synthesizer and response_text:
                                # Synthesize the response
                                success, audio_response = voice_synthesizer.synthesize_speech(response_text)
                                
                                if success and audio_response:
                                    # Send as audio message
                                    if from_number:
                                        await self.send_audio_message(from_number, audio_response)
                                        # Also send text version
                                        await self.send_message(from_number, f"🎤 Voice transcription: {transcribed_text}\n\n{response_text}")
                                else:
                                    # Fallback to text only
                                    if from_number:
                                        await self.send_message(from_number, response_text)
                            else:
                                # Send text response
                                if from_number:
                                    await self.send_message(from_number, response_text)
                            
                            # Store the transcribed message
                            security_level = self.classifier.classify_message(transcribed_text)
                            message_data = {
                                'id': message_id,
                                'from': from_number,
                                'timestamp': timestamp,
                                'type': 'audio',
                                'audio': audio_info,
                                'transcribed_text': transcribed_text,
                                'profile_name': message.get('profile', {}).get('name'),
                                'wa_id': from_number
                            }
                            if from_number:
                                self.storage.store_message(from_number, message_data, security_level)
                            
                            return {
                                'success': True,
                                'message_id': message_id,
                                'message_type': 'audio',
                                'transcribed': transcribed_text,
                                'command_type': command['type'],
                                'security_level': security_level.value,
                                'from': from_number
                            }
                        else:
                            # Transcription failed
                            if from_number:
                                await self.send_message(from_number, "❌ Sorry, I couldn't understand the audio message. Please try again or send a text message.")
                            return {
                                'success': False,
                                'message_id': message_id,
                                'error': 'Transcription failed'
                            }
                    else:
                        # Download failed
                        if from_number:
                            await self.send_message(from_number, "❌ Failed to download the audio message. Please try again.")
                        return {
                            'success': False,
                            'message_id': message_id,
                            'error': 'Download failed'
                        }
                else:
                    # Fallback for audio without processing
                    content = "[Audio message received - processing unavailable]"
            else:
                # Extract content based on message type
                content = ""
                if message_type == 'text':
                    content = message.get('text', {}).get('body', '')
                elif message_type == 'audio':
                    content = "[Audio message received]"
                elif message_type == 'image':
                    content = f"[Image: {message.get('image', {}).get('caption', 'No caption')}]"
                elif message_type == 'document':
                    content = f"[Document: {message.get('document', {}).get('filename', 'Unknown')}]"
            
            # Check if this is an enroll command
            if message_type == 'text' and content.lower().startswith('enroll:'):
                # Extract passphrase
                passphrase = content[7:].strip()  # Remove 'enroll:' prefix
                
                if not passphrase:
                    if from_number:
                        await self.send_message(from_number, "❌ Please provide a passphrase. Example: enroll: mysecretpassphrase")
                    return {
                        'success': True,
                        'message_id': message_id,
                        'action': 'enroll_empty',
                        'from': from_number
                    }
                
                # Handle enrollment if available
                if VOICE_GUARD_AVAILABLE and voice_guard and from_number:
                    result = voice_guard.enroll_passphrase(from_number, passphrase)
                    await self.send_message(from_number, result['message'])
                    
                    return {
                        'success': result['success'],
                        'message_id': message_id,
                        'action': 'enroll',
                        'from': from_number
                    }
                else:
                    if from_number:
                        await self.send_message(from_number, "⚠️ Voice guard functionality is currently unavailable.")
                    return {
                        'success': True,
                        'message_id': message_id,
                        'action': 'enroll_unavailable',
                        'from': from_number
                    }
            
            # Check if this is a verify command
            if message_type == 'text' and content.lower().startswith('verify:'):
                # Extract passphrase
                passphrase = content[7:].strip()  # Remove 'verify:' prefix
                
                if not passphrase:
                    if from_number:
                        await self.send_message(from_number, "❌ Please provide your passphrase. Example: verify: mysecretpassphrase")
                    return {
                        'success': True,
                        'message_id': message_id,
                        'action': 'verify_empty',
                        'from': from_number
                    }
                
                # Handle verification if available
                if VOICE_GUARD_AVAILABLE and voice_guard and session_manager and from_number:
                    result = voice_guard.verify_passphrase(from_number, passphrase)
                    
                    if result['verified']:
                        # Create a session for the verified user
                        session_manager.create_session(from_number)
                        await self.send_message(from_number, result['message'] + f"\n\n⏱️ Session expires in {session_manager.ttl_minutes} minutes.")
                    else:
                        await self.send_message(from_number, result['message'])
                    
                    return {
                        'success': result['success'],
                        'message_id': message_id,
                        'action': 'verify',
                        'verified': result.get('verified', False),
                        'from': from_number
                    }
                else:
                    if from_number:
                        await self.send_message(from_number, "⚠️ Voice guard functionality is currently unavailable.")
                    return {
                        'success': True,
                        'message_id': message_id,
                        'action': 'verify_unavailable',
                        'from': from_number
                    }
            
            # Check if this is a search command
            if message_type == 'text' and content.lower().startswith('search:'):
                # Extract search query
                query = content[7:].strip()  # Remove 'search:' prefix
                
                if not query:
                    if from_number:
                        await self.send_message(from_number, "🔍 Please provide a search query. Example: search: appointment")
                    return {
                        'success': True,
                        'message_id': message_id,
                        'action': 'search_empty',
                        'from': from_number
                    }
                
                # Perform search if available
                if SEARCH_AVAILABLE:
                    logger.info(f"🔍 Searching for: {query}")
                    
                    # Get allowed categories based on verification status
                    if VOICE_GUARD_AVAILABLE and session_manager and from_number:
                        allowed_categories = session_manager.get_allowed_categories(from_number)
                    else:
                        # Default categories (non-sensitive)
                        allowed_categories = ['general', 'chronological', 'confidential']
                    
                    # Perform the search
                    if from_number and 'search_contact_memories' in globals():
                        search_result = search_contact_memories(
                            phone_number=from_number,
                        query=query,
                        allowed_categories=allowed_categories,
                        limit=6
                    )
                    
                        # Add session status to message if verified
                        message = search_result['formatted']
                        if VOICE_GUARD_AVAILABLE and session_manager and from_number and session_manager.is_verified(from_number):
                            time_remaining = session_manager.get_time_remaining(from_number)
                            message += f"\n\n🔓 Secret access active ({time_remaining} min remaining)"
                        
                        # Send search results
                        if from_number:
                            await self.send_message(from_number, message)
                    else:
                        # Search not available
                        if from_number:
                            await self.send_message(from_number, "⚠️ Search functionality is currently unavailable.")
                        return {
                            'success': False,
                            'message_id': message_id,
                            'action': 'search_error',
                            'from': from_number
                        }
                    
                    if 'search_result' in locals():
                        return {
                            'success': True,
                            'message_id': message_id,
                            'action': 'search',
                            'query': query,
                            'results_count': search_result['count'],
                            'from': from_number
                        }
                    else:
                        return {
                            'success': False,
                            'message_id': message_id,
                            'action': 'search_failed',
                            'from': from_number
                        }
                else:
                    if from_number:
                        await self.send_message(from_number, "⚠️ Search functionality is currently unavailable.")
                    return {
                        'success': True,
                        'message_id': message_id,
                        'action': 'search_unavailable',
                        'from': from_number
                    }
            
            # Regular message processing - classify and store
            security_level = self.classifier.classify_message(content)
            
            # Store the message
            message_data = {
                'id': message_id,
                'from': from_number,
                'timestamp': timestamp,
                'type': message_type,
                'text': message.get('text'),
                'image': message.get('image'),
                'audio': message.get('audio'),
                'document': message.get('document'),
                'profile_name': message.get('profile', {}).get('name'),
                'wa_id': from_number
            }
            
            if from_number:
                stored = self.storage.store_message(from_number, message_data, security_level)
            else:
                stored = False
            
            if stored:
                # Send acknowledgment
                ack_message = f"✅ Message received and stored in {security_level.value} category."
                if from_number:
                    await self.send_message(from_number, ack_message)
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'security_level': security_level.value,
                    'from': from_number
                }
            else:
                return {
                    'success': False,
                    'message_id': message_id,
                    'error': 'Failed to store message'
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def send_message(self, to_number: str, text: str) -> bool:
        """Send a message via WhatsApp Cloud API"""
        if not self.access_token or not self.phone_number_id:
            logger.warning("⚠️ WhatsApp Cloud API not configured - message not sent")
            return False
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'to': to_number,
            'type': 'text',
            'text': {
                'body': text
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            logger.info(f"✅ Message sent to {to_number}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            return False
    
    async def send_template_message(self, to_number: str, template_name: str, 
                                   language: str = 'en', parameters: List[str] = None) -> bool:
        """Send a template message via WhatsApp Cloud API"""
        if not self.access_token or not self.phone_number_id:
            logger.warning("⚠️ WhatsApp Cloud API not configured")
            return False
        
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'to': to_number,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {
                    'code': language
                }
            }
        }
        
        # Add parameters if provided
        if parameters:
            data['template']['components'] = [{
                'type': 'body',
                'parameters': [{'type': 'text', 'text': param} for param in parameters]
            }]
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            logger.info(f"✅ Template message sent to {to_number}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send template message: {e}")
            return False
    
    def get_media_url(self, media_id: str) -> Optional[str]:
        """Get media URL from WhatsApp Cloud API"""
        if not self.access_token:
            return None
        
        url = f"{self.base_url}/{media_id}"
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get('url')
        except Exception as e:
            logger.error(f"❌ Failed to get media URL: {e}")
            return None

# Create global instance
whatsapp_cloud_api = WhatsAppCloudAPI()