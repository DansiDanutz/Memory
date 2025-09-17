"""
Claude AI Service for Memory Management
Provides intelligent message analysis, response generation, and memory extraction
"""
import os
import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio
from anthropic import AsyncAnthropic, Anthropic
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ConversationTone(Enum):
    """Available conversation tones"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    EMPATHETIC = "empathetic"
    CASUAL = "casual"
    FORMAL = "formal"
    SUPPORTIVE = "supportive"

@dataclass
class ClaudeAnalysis:
    """Analysis result from Claude"""
    sentiment: str
    intent: str
    category: str
    confidence: float
    tags: List[str]
    is_command: bool
    extracted_entities: Dict[str, Any]
    priority: int
    suggested_response_tone: str

@dataclass
class MemoryExtraction:
    """Extracted memory from message"""
    content: str
    category: str
    importance: int
    tags: List[str]
    people_mentioned: List[str]
    locations: List[str]
    dates: List[str]
    action_items: List[str]
    summary: str

class ClaudeService:
    """
    Claude AI Service for intelligent message processing and memory management
    Uses the latest Claude Sonnet model for advanced analysis
    """
    
    def __init__(self):
        """Initialize Claude Service with API key from environment"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.model = "claude-sonnet-4-20250514"  # Latest model as specified
        self.client = None
        self.async_client = None
        self.initialized = False
        
        if self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                self.async_client = AsyncAnthropic(api_key=self.api_key)
                self.initialized = True
                logger.info(f"Claude Service initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
                self.initialized = False
        else:
            logger.warning("ANTHROPIC_API_KEY not found. Claude features disabled.")
    
    def is_available(self) -> bool:
        """Check if Claude service is configured and available"""
        return self.initialized and bool(self.api_key)
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Test Claude API connection"""
        if not self.is_available():
            return False, "Claude service not configured"
        
        try:
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=50,
                messages=[
                    {"role": "user", "content": "Say 'OK' if you can hear me"}
                ]
            )
            if response.content:
                return True, "Claude API connection successful"
            return False, "Unexpected response from Claude"
        except Exception as e:
            logger.error(f"Claude connection test failed: {e}")
            return False, f"Connection failed: {str(e)}"
    
    async def analyze_message(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> ClaudeAnalysis:
        """
        Analyze message for sentiment, intent, and categorization
        
        Args:
            message: Message to analyze
            context: Previous conversation context
            
        Returns:
            ClaudeAnalysis object with detailed analysis
        """
        if not self.is_available():
            # Return default analysis if service unavailable
            return ClaudeAnalysis(
                sentiment="neutral",
                intent="general",
                category="GENERAL",
                confidence=0.5,
                tags=[],
                is_command=message.strip().lower().endswith(':'),
                extracted_entities={},
                priority=5,
                suggested_response_tone="friendly"
            )
        
        try:
            # Build context string
            context_str = ""
            if context:
                context_str = "Previous conversation:\n"
                for msg in context[-5:]:  # Last 5 messages
                    context_str += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"
            
            prompt = f"""Analyze the following message and provide a detailed analysis.

{f'Context: {context_str}' if context_str else ''}

Message to analyze: "{message}"

Provide analysis in JSON format with these fields:
- sentiment: positive/negative/neutral/mixed
- intent: question/command/statement/greeting/farewell/request/complaint/praise
- category: GENERAL/CONFIDENTIAL/SECRET/ULTRA_SECRET/CHRONOLOGICAL
- confidence: 0.0 to 1.0
- tags: list of relevant tags
- is_command: boolean (true if it's a command like "search:", "help:", etc.)
- extracted_entities: dict of entities (names, dates, locations, numbers, etc.)
- priority: 1-10 (1=lowest, 10=highest)
- suggested_response_tone: professional/friendly/empathetic/casual/formal/supportive

Base categorization on:
- GENERAL: Regular conversations, daily activities
- CHRONOLOGICAL: Time-based events, appointments, schedules
- CONFIDENTIAL: Personal information, private matters
- SECRET: Sensitive information, passwords, financial data
- ULTRA_SECRET: Highly sensitive, medical records, legal matters

Respond ONLY with valid JSON."""

            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse response
            result_text = response.content[0].text if response.content else "{}"
            
            # Try to extract JSON from response
            try:
                # Clean up response to extract JSON
                import re
                json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = json.loads(result_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Claude response: {result_text}")
                result = {}
            
            return ClaudeAnalysis(
                sentiment=result.get('sentiment', 'neutral'),
                intent=result.get('intent', 'general'),
                category=result.get('category', 'GENERAL'),
                confidence=float(result.get('confidence', 0.5)),
                tags=result.get('tags', []),
                is_command=result.get('is_command', False),
                extracted_entities=result.get('extracted_entities', {}),
                priority=int(result.get('priority', 5)),
                suggested_response_tone=result.get('suggested_response_tone', 'friendly')
            )
            
        except Exception as e:
            logger.error(f"Error analyzing message with Claude: {e}")
            return ClaudeAnalysis(
                sentiment="neutral",
                intent="general",
                category="GENERAL",
                confidence=0.0,
                tags=[],
                is_command=False,
                extracted_entities={},
                priority=5,
                suggested_response_tone="friendly"
            )
    
    async def generate_response(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]] = None,
        tone: str = "friendly"
    ) -> str:
        """
        Generate intelligent response based on message and context
        
        Args:
            message: User message to respond to
            context: Conversation history
            tone: Desired response tone
            
        Returns:
            Generated response text
        """
        if not self.is_available():
            return "I understand your message. How can I assist you further?"
        
        try:
            # Build context
            context_str = ""
            if context:
                context_str = "Previous conversation:\n"
                for msg in context[-10:]:  # Last 10 messages
                    context_str += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"
            
            prompt = f"""Generate a helpful response to the user's message.

{f'Context: {context_str}' if context_str else ''}

User message: "{message}"

Response tone: {tone}

Guidelines:
- Be concise but complete
- Use the specified tone consistently
- If the message is a question, provide a clear answer
- If it's a command, acknowledge and explain what will happen
- For statements, show understanding and engage appropriately
- Maximum 200 words

Generate only the response text, no additional formatting."""

            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text if response.content else "I understand. How can I help you?"
            
        except Exception as e:
            logger.error(f"Error generating response with Claude: {e}")
            return "I understand your message. How can I assist you?"
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, Any]],
        max_length: int = 500
    ) -> str:
        """
        Summarize a conversation thread
        
        Args:
            messages: List of messages to summarize
            max_length: Maximum summary length
            
        Returns:
            Conversation summary
        """
        if not self.is_available() or not messages:
            return "No conversation to summarize."
        
        try:
            # Format messages
            conversation = "\n".join([
                f"{msg.get('sender', 'User')}: {msg.get('content', '')}"
                for msg in messages
            ])
            
            prompt = f"""Summarize this conversation in {max_length} characters or less.

Conversation:
{conversation}

Provide a concise summary covering:
1. Main topics discussed
2. Key decisions or agreements
3. Action items or next steps
4. Important information shared

Summary:"""

            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            summary = response.content[0].text if response.content else "Conversation summary unavailable."
            return summary[:max_length] if len(summary) > max_length else summary
            
        except Exception as e:
            logger.error(f"Error summarizing conversation with Claude: {e}")
            return "Unable to generate summary."
    
    async def extract_memory(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> MemoryExtraction:
        """
        Extract key memories and information from message
        
        Args:
            message: Message to extract memories from
            context: Conversation context
            
        Returns:
            MemoryExtraction object with extracted information
        """
        if not self.is_available():
            # Basic extraction without AI
            return MemoryExtraction(
                content=message,
                category="GENERAL",
                importance=5,
                tags=[],
                people_mentioned=[],
                locations=[],
                dates=[],
                action_items=[],
                summary=message[:100]
            )
        
        try:
            context_str = ""
            if context:
                context_str = "Context:\n" + "\n".join([
                    f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                    for msg in context[-5:]
                ])
            
            prompt = f"""Extract important information from this message to store as a memory.

{context_str}

Message: "{message}"

Extract and provide in JSON format:
- content: the core information to remember
- category: GENERAL/CONFIDENTIAL/SECRET/ULTRA_SECRET/CHRONOLOGICAL
- importance: 1-10 (1=trivial, 10=critical)
- tags: relevant tags for searching
- people_mentioned: list of people names mentioned
- locations: list of locations mentioned
- dates: list of dates/times mentioned
- action_items: list of tasks or actions to remember
- summary: brief summary (max 100 chars)

Focus on extracting:
1. Facts and information worth remembering
2. Commitments and promises
3. Important dates and deadlines
4. Personal preferences or details shared
5. Tasks or action items

Respond ONLY with valid JSON."""

            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=400,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = response.content[0].text if response.content else "{}"
            
            # Parse JSON response
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = json.loads(result_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse memory extraction: {result_text}")
                result = {}
            
            return MemoryExtraction(
                content=result.get('content', message),
                category=result.get('category', 'GENERAL'),
                importance=int(result.get('importance', 5)),
                tags=result.get('tags', []),
                people_mentioned=result.get('people_mentioned', []),
                locations=result.get('locations', []),
                dates=result.get('dates', []),
                action_items=result.get('action_items', []),
                summary=result.get('summary', message[:100])
            )
            
        except Exception as e:
            logger.error(f"Error extracting memory with Claude: {e}")
            return MemoryExtraction(
                content=message,
                category="GENERAL",
                importance=5,
                tags=[],
                people_mentioned=[],
                locations=[],
                dates=[],
                action_items=[],
                summary=message[:100]
            )
    
    def get_cache_key(self, method: str, *args) -> str:
        """Generate cache key for Claude responses"""
        # Create a unique key based on method and arguments
        key_data = f"{method}:" + ":".join(str(arg) for arg in args)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get Claude API usage statistics"""
        # This would typically connect to your usage tracking system
        return {
            "available": self.is_available(),
            "model": self.model,
            "requests_today": 0,  # Would track actual usage
            "tokens_used": 0,     # Would track actual tokens
            "cache_hits": 0,      # Would track cache usage
            "avg_response_time": 0.0  # Would track performance
        }