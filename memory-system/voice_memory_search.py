#!/usr/bin/env python3
"""
Voice Memory Search System - Voice-Only Authenticated Memory Search
Advanced AI-powered memory search with strict voice authentication requirements
"""

import os
import json
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

# AI Integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# Import our memory system components
from md_file_manager import MDFileManager, MemoryTag
from conversation_classifier import ConversationClassifier
from voice_authentication_service import (
    voice_auth_service, 
    VoiceSession, 
    AuthenticationLevel,
    MemoryAccessLevel
)
from confidential_manager import ConfidentialManager, SecurityLevel, AccessLevel

logger = logging.getLogger(__name__)

class SearchAccessType(Enum):
    """Types of search access based on authentication"""
    VOICE_ONLY = "voice_only"      # Requires voice auth
    TEXT_ALLOWED = "text_allowed"   # Text search allowed
    BLOCKED = "blocked"              # Search blocked

class MemorySearchResult:
    """Structure for memory search results"""
    def __init__(self, 
                 query: str,
                 answer: str,
                 memories_found: List[Dict],
                 confidence: float,
                 source_files: List[str],
                 authentication_method: str,
                 access_level: str):
        self.query = query
        self.answer = answer
        self.memories_found = memories_found
        self.confidence = confidence
        self.source_files = source_files
        self.authentication_method = authentication_method
        self.access_level = access_level
        self.timestamp = datetime.now()

class VoiceMemorySearch:
    """Voice-Authenticated Intelligent Memory Search System"""
    
    def __init__(self):
        """Initialize the Voice Memory Search system"""
        # Initialize components
        self.md_manager = MDFileManager(base_dir="memory-system/users")
        self.classifier = ConversationClassifier()
        self.confidential_manager = ConfidentialManager()
        
        # Security configuration
        self.secure_tags = [
            MemoryTag.CONFIDENTIAL,
            MemoryTag.SECRET,
            MemoryTag.ULTRA_SECRET
        ]
        
        # OpenAI configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            logger.info("✅ OpenAI API key configured for Voice Memory Search")
        else:
            logger.warning("⚠️ OpenAI API key not configured - some features may be limited")
        
        # Search logs for security auditing
        self.search_logs_dir = Path("memory-system/security/search_logs")
        self.search_logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Active voice sessions cache
        self.active_voice_sessions = {}
        
        logger.info("🔊 Voice Memory Search System initialized")
    
    async def verify_voice_authentication(self, 
                                         user_id: str, 
                                         session_token: Optional[str] = None) -> Tuple[bool, Optional[VoiceSession]]:
        """Verify if user has active voice authentication"""
        try:
            # Check for active voice session
            if session_token:
                session = await voice_auth_service.validate_session(session_token)
                if session and session.status.value == 'authenticated':
                    # Update session activity
                    session.last_activity = datetime.now()
                    
                    # Check if session is not expired
                    if datetime.now() < session.expires_at:
                        return True, session
                    else:
                        logger.warning(f"Voice session expired for user {user_id}")
                        return False, None
            
            # Check cached sessions
            if user_id in self.active_voice_sessions:
                cached_session = self.active_voice_sessions[user_id]
                if datetime.now() < cached_session['expires_at']:
                    return True, cached_session['session']
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error verifying voice authentication: {e}")
            return False, None
    
    def determine_access_type(self, memory_tag: MemoryTag) -> SearchAccessType:
        """Determine if search requires voice authentication based on memory tag"""
        if memory_tag in self.secure_tags:
            return SearchAccessType.VOICE_ONLY
        elif memory_tag in [MemoryTag.GENERAL, MemoryTag.CHRONOLOGICAL]:
            return SearchAccessType.TEXT_ALLOWED
        else:
            return SearchAccessType.VOICE_ONLY  # Default to secure
    
    async def search_memories_by_voice(self, 
                                      user_id: str,
                                      voice_query: str,
                                      session_token: str,
                                      voice_audio_data: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Search memories using voice authentication only
        
        Args:
            user_id: User's phone number or ID
            voice_query: The transcribed voice query
            session_token: Voice authentication session token
            voice_audio_data: Optional raw voice data for additional verification
        
        Returns:
            Search results with natural language answer
        """
        try:
            # Step 1: Verify voice authentication
            is_authenticated, voice_session = await self.verify_voice_authentication(user_id, session_token)
            
            if not is_authenticated:
                # Log failed attempt
                await self._log_search_attempt(
                    user_id=user_id,
                    query=voice_query,
                    success=False,
                    reason="Voice authentication required",
                    authentication_method="voice_required"
                )
                
                return {
                    'success': False,
                    'error': 'Voice authentication required. Please authenticate with your voice first.',
                    'authentication_required': True,
                    'method_required': 'voice'
                }
            
            # Step 2: Additional voice verification if audio data provided
            if voice_audio_data and voice_session:
                verification_result = await voice_auth_service.verify_voice(
                    user_id=user_id,
                    audio_data=voice_audio_data
                )
                
                if not verification_result.get('success'):
                    await self._log_search_attempt(
                        user_id=user_id,
                        query=voice_query,
                        success=False,
                        reason="Voice verification failed",
                        authentication_method="voice_failed"
                    )
                    
                    return {
                        'success': False,
                        'error': 'Voice verification failed. Your voice does not match the registered profile.',
                        'authentication_failed': True
                    }
            
            # Step 3: Determine accessible memory categories based on auth level
            accessible_tags = self._get_accessible_tags(voice_session.access_level)
            
            # Step 4: Search memories across all user files
            search_results = await self._search_user_memories(
                user_id=user_id,
                query=voice_query,
                accessible_tags=accessible_tags
            )
            
            if not search_results:
                return {
                    'success': True,
                    'answer': f"I couldn't find any information about '{voice_query}' in your memories.",
                    'memories_found': 0,
                    'authenticated_via': 'voice',
                    'access_level': voice_session.access_level.value
                }
            
            # Step 5: Extract intelligent answer using AI
            answer = await self._extract_answer_with_ai(
                query=voice_query,
                memories=search_results,
                user_context={'user_id': user_id, 'name': voice_session.metadata.get('user_name')}
            )
            
            # Step 6: Log successful search
            await self._log_search_attempt(
                user_id=user_id,
                query=voice_query,
                success=True,
                results_count=len(search_results),
                answer_preview=answer[:100],
                authentication_method="voice",
                access_level=voice_session.access_level.value
            )
            
            # Step 7: Format and return results
            return {
                'success': True,
                'answer': answer,
                'query': voice_query,
                'memories_found': len(search_results),
                'confidence': self._calculate_confidence(search_results),
                'authenticated_via': 'voice',
                'access_level': voice_session.access_level.value,
                'session_valid_until': voice_session.expires_at.isoformat(),
                'source_files': list(set([m.get('source_file', 'unknown') for m in search_results]))
            }
            
        except Exception as e:
            logger.error(f"Error in voice memory search: {e}")
            await self._log_search_attempt(
                user_id=user_id,
                query=voice_query,
                success=False,
                reason=str(e),
                authentication_method="voice_error"
            )
            
            return {
                'success': False,
                'error': f'Search failed: {str(e)}',
                'requires_authentication': True
            }
    
    async def search_memories_by_text(self,
                                     user_id: str,
                                     text_query: str,
                                     auth_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Search memories using text - ONLY allowed for non-secure memories
        
        Args:
            user_id: User's phone number or ID
            text_query: The text search query
            auth_token: Optional authentication token
        
        Returns:
            Search results or authentication required message
        """
        try:
            # Only allow searching general and chronological memories via text
            accessible_tags = [MemoryTag.GENERAL, MemoryTag.CHRONOLOGICAL]
            
            # Check if query might be asking for secure information
            is_potentially_secure = await self._check_if_secure_query(text_query)
            
            if is_potentially_secure:
                # Block the search and require voice authentication
                await self._log_search_attempt(
                    user_id=user_id,
                    query=text_query,
                    success=False,
                    reason="Secure content requires voice authentication",
                    authentication_method="text_blocked"
                )
                
                return {
                    'success': False,
                    'error': 'This query appears to request secure information. Voice authentication is required for accessing confidential, secret, or ultra-secret memories.',
                    'authentication_required': True,
                    'method_required': 'voice',
                    'secure_content_detected': True
                }
            
            # Search only non-secure memories
            search_results = await self._search_user_memories(
                user_id=user_id,
                query=text_query,
                accessible_tags=accessible_tags
            )
            
            if not search_results:
                return {
                    'success': True,
                    'answer': f"I couldn't find any information about '{text_query}' in your general memories. Note: Secure memories require voice authentication.",
                    'memories_found': 0,
                    'authenticated_via': 'text',
                    'access_level': 'general_only',
                    'note': 'Only searching general and chronological memories. Use voice authentication to search all memories.'
                }
            
            # Extract answer for general queries
            answer = await self._extract_answer_with_ai(
                query=text_query,
                memories=search_results,
                user_context={'user_id': user_id}
            )
            
            # Log the text search
            await self._log_search_attempt(
                user_id=user_id,
                query=text_query,
                success=True,
                results_count=len(search_results),
                answer_preview=answer[:100],
                authentication_method="text",
                access_level="general_only"
            )
            
            return {
                'success': True,
                'answer': answer,
                'query': text_query,
                'memories_found': len(search_results),
                'authenticated_via': 'text',
                'access_level': 'general_only',
                'note': 'Showing results from general memories only. Voice authentication required for complete search.'
            }
            
        except Exception as e:
            logger.error(f"Error in text memory search: {e}")
            return {
                'success': False,
                'error': f'Search failed: {str(e)}'
            }
    
    async def _check_if_secure_query(self, query: str) -> bool:
        """Check if query is asking for potentially secure information"""
        secure_keywords = [
            'password', 'secret', 'confidential', 'private', 'sensitive',
            'bank', 'credit card', 'ssn', 'social security', 'pin',
            'medical', 'health', 'diagnosis', 'medication',
            'legal', 'contract', 'agreement', 'will',
            'intimate', 'personal', 'relationship',
            'financial', 'salary', 'income', 'debt'
        ]
        
        query_lower = query.lower()
        for keyword in secure_keywords:
            if keyword in query_lower:
                return True
        
        # Use AI to detect if query is asking for sensitive information
        if self.openai_api_key:
            try:
                if OPENAI_AVAILABLE:
                    client = OpenAI(api_key=self.openai_api_key)
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Determine if this query is asking for sensitive, private, or confidential information. Reply with only 'yes' or 'no'."},
                            {"role": "user", "content": query}
                        ],
                        max_tokens=10,
                        temperature=0
                    )
                
                answer = response.choices[0].message.content.strip().lower()
                return answer == 'yes'
                
            except Exception as e:
                logger.warning(f"Could not check query sensitivity with AI: {e}")
        
        return False
    
    def _get_accessible_tags(self, access_level: MemoryAccessLevel) -> List[MemoryTag]:
        """Get list of accessible memory tags based on access level"""
        if access_level == MemoryAccessLevel.FULL:
            return list(MemoryTag)  # All tags
        elif access_level == MemoryAccessLevel.RESTRICTED:
            return [MemoryTag.GENERAL, MemoryTag.CHRONOLOGICAL]
        elif access_level == MemoryAccessLevel.FAMILY:
            return [MemoryTag.GENERAL, MemoryTag.CHRONOLOGICAL]  # Add family tag when available
        else:
            return []  # No access
    
    async def _search_user_memories(self, 
                                   user_id: str, 
                                   query: str,
                                   accessible_tags: List[MemoryTag]) -> List[Dict]:
        """Search through user's memory files"""
        try:
            results = []
            
            # Search in user's main file
            user_memories = await self.md_manager.search_memories(
                phone_number=user_id,
                search_query=query,
                tags=accessible_tags
            )
            
            if user_memories.get('success') and user_memories.get('memories'):
                for memory in user_memories['memories']:
                    results.append({
                        'content': memory.get('content', ''),
                        'timestamp': memory.get('timestamp', ''),
                        'tag': memory.get('tag', 'general'),
                        'source_file': f"user_{user_id}",
                        'relevance_score': memory.get('relevance_score', 0.5)
                    })
            
            # Search in related files (contacts, relationships, topics)
            related_files = await self._get_related_files(user_id)
            
            for file_info in related_files:
                file_results = await self._search_file(
                    file_path=file_info['path'],
                    query=query,
                    accessible_tags=accessible_tags
                )
                
                for result in file_results:
                    result['source_file'] = file_info['type']
                    results.append(result)
            
            # Sort by relevance
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            return results[:20]  # Return top 20 results
            
        except Exception as e:
            logger.error(f"Error searching user memories: {e}")
            return []
    
    async def _get_related_files(self, user_id: str) -> List[Dict]:
        """Get list of related memory files for user"""
        related_files = []
        
        # Get user's contacts
        contacts_dir = Path(self.md_manager.contacts_dir)
        if contacts_dir.exists():
            for contact_file in contacts_dir.glob("*.md"):
                # Check if contact is related to user
                content = contact_file.read_text()
                if user_id in content:
                    related_files.append({
                        'path': str(contact_file),
                        'type': f"contact_{contact_file.stem}"
                    })
        
        # Get user's relationships
        relationships_dir = Path(self.md_manager.relationships_dir)
        if relationships_dir.exists():
            sanitized_user = self.md_manager._sanitize_filename(user_id)
            for rel_file in relationships_dir.glob(f"{sanitized_user}_*.md"):
                related_files.append({
                    'path': str(rel_file),
                    'type': f"relationship_{rel_file.stem}"
                })
        
        # Get user's topics
        topics_dir = Path(self.md_manager.topics_dir)
        if topics_dir.exists():
            for topic_file in topics_dir.glob("*.md"):
                content = topic_file.read_text()
                if user_id in content:
                    related_files.append({
                        'path': str(topic_file),
                        'type': f"topic_{topic_file.stem}"
                    })
        
        return related_files
    
    async def _search_file(self, 
                          file_path: str, 
                          query: str,
                          accessible_tags: List[MemoryTag]) -> List[Dict]:
        """Search within a specific file"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse memories from file
            memories = self._parse_memories_from_content(content)
            
            # Search for query in memories
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            for memory in memories:
                # Check if memory tag is accessible
                memory_tag_str = memory.get('tag', 'general').lower()
                try:
                    memory_tag = MemoryTag(memory_tag_str)
                    if memory_tag not in accessible_tags:
                        continue
                except:
                    continue
                
                # Calculate relevance
                memory_content = memory.get('content', '').lower()
                relevance = self._calculate_relevance(query_words, memory_content)
                
                if relevance > 0.1:  # Threshold for inclusion
                    memory['relevance_score'] = relevance
                    results.append(memory)
            
        except Exception as e:
            logger.error(f"Error searching file {file_path}: {e}")
        
        return results
    
    def _parse_memories_from_content(self, content: str) -> List[Dict]:
        """Parse memories from markdown content"""
        memories = []
        
        # Parse memory entries (format: - **[timestamp]** [tag]: content)
        pattern = r'-\s+\*\*\[([\d\-:\s]+)\]\*\*\s+\[([^\]]+)\]:\s+(.+?)(?=\n-\s+\*\*\[|\n##|\Z)'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            timestamp, tag, memory_content = match.groups()
            memories.append({
                'timestamp': timestamp.strip(),
                'tag': tag.strip(),
                'content': memory_content.strip()
            })
        
        return memories
    
    def _calculate_relevance(self, query_words: set, content: str) -> float:
        """Calculate relevance score between query and content"""
        content_words = set(content.lower().split())
        
        # Calculate word overlap
        overlap = query_words.intersection(content_words)
        
        if not query_words:
            return 0.0
        
        # Basic relevance: percentage of query words found
        relevance = len(overlap) / len(query_words)
        
        # Boost for exact phrase match
        query_phrase = ' '.join(query_words)
        if query_phrase in content.lower():
            relevance += 0.5
        
        # Normalize to 0-1 range
        return min(relevance, 1.0)
    
    def _calculate_confidence(self, search_results: List[Dict]) -> float:
        """Calculate confidence score for search results"""
        if not search_results:
            return 0.0
        
        # Average of top 3 relevance scores
        top_scores = sorted([r.get('relevance_score', 0) for r in search_results], reverse=True)[:3]
        
        if top_scores:
            return sum(top_scores) / len(top_scores)
        
        return 0.0
    
    async def _extract_answer_with_ai(self, 
                                     query: str, 
                                     memories: List[Dict],
                                     user_context: Dict) -> str:
        """Use AI to extract intelligent answer from memories"""
        if not self.openai_api_key:
            # Fallback to simple extraction
            return self._extract_answer_simple(query, memories)
        
        try:
            # Prepare context from memories
            memory_context = "\n\n".join([
                f"[{m.get('timestamp', 'Unknown time')}] ({m.get('tag', 'general')}): {m.get('content', '')}"
                for m in memories[:10]  # Use top 10 memories
            ])
            
            # Create prompt for AI
            system_prompt = """You are an intelligent memory assistant. Your task is to answer the user's question based on their stored memories. 
            Provide a natural, conversational answer that directly addresses their question. 
            If the memories contain the answer, extract and present it clearly. 
            If the answer is not in the memories, say so politely.
            Be specific with dates, names, and details when available."""
            
            user_prompt = f"""Based on these memories:

{memory_context}

Please answer this question: {query}

Provide a clear, natural answer as if you're talking to the person who owns these memories."""
            
            # Call OpenAI
            if OPENAI_AVAILABLE:
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4-turbo-preview" if "gpt-4" in os.getenv('OPENAI_MODEL', '') else "gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
            
            answer = response.choices[0].message.content.strip()
            
            # Add source indication if highly confident
            if self._calculate_confidence(memories) > 0.7:
                answer += f"\n\n(Found in {len(memories)} related memories)"
            
            return answer
            
        except Exception as e:
            logger.error(f"Error using AI for answer extraction: {e}")
            # Fallback to simple extraction
            return self._extract_answer_simple(query, memories)
    
    def _extract_answer_simple(self, query: str, memories: List[Dict]) -> str:
        """Simple answer extraction without AI"""
        if not memories:
            return f"I couldn't find any information about '{query}' in your memories."
        
        # For date/time questions
        if any(word in query.lower() for word in ['when', 'date', 'time']):
            # Look for dates in memories
            for memory in memories:
                content = memory.get('content', '')
                # Extract dates using regex
                date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{1,2} \w+ \d{4})\b'
                dates = re.findall(date_pattern, content)
                if dates:
                    return f"Based on your memories, the relevant date is: {dates[0]}"
        
        # For who/name questions
        if any(word in query.lower() for word in ['who', 'name', 'person']):
            # Look for names (capitalized words)
            names = []
            for memory in memories:
                content = memory.get('content', '')
                # Extract potential names
                name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
                found_names = re.findall(name_pattern, content)
                names.extend(found_names)
            
            if names:
                unique_names = list(set(names))
                return f"The following names were found: {', '.join(unique_names[:3])}"
        
        # Default: return the most relevant memory
        best_memory = memories[0]
        return f"From your memory on {best_memory.get('timestamp', 'unknown date')}: {best_memory.get('content', '')[:200]}..."
    
    async def _log_search_attempt(self, 
                                 user_id: str,
                                 query: str,
                                 success: bool,
                                 reason: Optional[str] = None,
                                 results_count: Optional[int] = None,
                                 answer_preview: Optional[str] = None,
                                 authentication_method: str = "unknown",
                                 access_level: Optional[str] = None):
        """Log search attempt for security auditing"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'query': query,
                'success': success,
                'authentication_method': authentication_method,
                'access_level': access_level,
                'results_count': results_count,
                'failure_reason': reason,
                'answer_preview': answer_preview
            }
            
            # Create user-specific log file
            log_file = self.search_logs_dir / f"{self._sanitize_filename(user_id)}_searches.json"
            
            # Load existing logs
            existing_logs = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    try:
                        existing_logs = json.load(f)
                    except:
                        existing_logs = []
            
            # Add new log entry
            existing_logs.append(log_entry)
            
            # Keep only last 1000 entries
            if len(existing_logs) > 1000:
                existing_logs = existing_logs[-1000:]
            
            # Save logs
            with open(log_file, 'w') as f:
                json.dump(existing_logs, f, indent=2)
            
            # Log security events
            if not success and reason:
                logger.warning(f"Search attempt failed for {user_id}: {reason}")
            
            if authentication_method == "text_blocked":
                logger.warning(f"Text search blocked for secure content - User: {user_id}, Query: {query}")
            
        except Exception as e:
            logger.error(f"Failed to log search attempt: {e}")
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for safe file system usage"""
        return re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    
    async def get_search_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get search statistics for a user"""
        try:
            log_file = self.search_logs_dir / f"{self._sanitize_filename(user_id)}_searches.json"
            
            if not log_file.exists():
                return {
                    'total_searches': 0,
                    'successful_searches': 0,
                    'failed_searches': 0,
                    'voice_searches': 0,
                    'text_searches': 0,
                    'blocked_searches': 0
                }
            
            with open(log_file, 'r') as f:
                logs = json.load(f)
            
            stats = {
                'total_searches': len(logs),
                'successful_searches': sum(1 for log in logs if log.get('success')),
                'failed_searches': sum(1 for log in logs if not log.get('success')),
                'voice_searches': sum(1 for log in logs if log.get('authentication_method') == 'voice'),
                'text_searches': sum(1 for log in logs if log.get('authentication_method') == 'text'),
                'blocked_searches': sum(1 for log in logs if log.get('authentication_method') == 'text_blocked'),
                'recent_searches': logs[-10:] if logs else []
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting search statistics: {e}")
            return {}

# Global instance
voice_memory_search = VoiceMemorySearch()

# Export for use in other modules
__all__ = ['VoiceMemorySearch', 'voice_memory_search', 'MemorySearchResult', 'SearchAccessType']