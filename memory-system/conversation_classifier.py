#!/usr/bin/env python3
"""
AI Conversation Classifier - Advanced Message Classification System
Uses AI to intelligently classify conversations and extract relevant information
"""

import os
import json
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import re
import openai
from pathlib import Path

from md_file_manager import MemoryTag, MemoryEntry

logger = logging.getLogger(__name__)

class ClassificationConfidence(Enum):
    """Classification confidence levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class ClassificationResult:
    """Result of message classification"""
    primary_tag: MemoryTag
    confidence: ClassificationConfidence
    secondary_tags: List[MemoryTag]
    extracted_entities: Dict[str, List[str]]
    sentiment: str
    importance_score: float
    related_contacts: List[str]
    topics: List[str]
    action_items: List[str]
    temporal_references: List[str]
    reasoning: str

@dataclass
class ConversationContext:
    """Context for conversation classification"""
    user_phone: str
    conversation_history: List[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]] = None
    known_contacts: Optional[List[str]] = None
    recent_topics: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.known_contacts is None:
            self.known_contacts = []
        if self.recent_topics is None:
            self.recent_topics = []

class ConversationClassifier:
    """Advanced AI-powered conversation classifier"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the conversation classifier"""
        # Get API key from parameter or environment
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
        # Only initialize OpenAI client if we have an API key
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
            logger.info("✅ OpenAI client initialized for conversation classifier")
        else:
            self.openai_client = None
            logger.warning("⚠️ OpenAI API key not configured - using fallback classification")
        
        # Classification prompts and rules
        self.classification_prompts = self._load_classification_prompts()
        self.entity_patterns = self._load_entity_patterns()
        
        # Cache for performance
        self.classification_cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(hours=1)
        
        logger.info("🤖 AI Conversation Classifier initialized")
    
    def _load_classification_prompts(self) -> Dict[str, str]:
        """Load classification prompts for different scenarios"""
        return {
            'primary_classification': """
You are an expert AI assistant that classifies personal conversations and messages into memory categories.

Analyze the following message and classify it into ONE primary category:

1. CHRONOLOGICAL - Timeline events, appointments, meetings, things that happened or will happen
2. GENERAL - Facts, preferences, general information, knowledge that can be reused
3. CONFIDENTIAL - Private information that should be kept secure but not highly sensitive
4. SECRET - Highly sensitive information requiring elevated security
5. ULTRA_SECRET - Maximum security information requiring special authentication

Message: "{message}"
Context: "{context}"
User Profile: {user_profile}
Recent Conversation: {conversation_history}

Provide your response in JSON format:
{{
    "primary_tag": "chronological|general|confidential|secret|ultra_secret",
    "confidence": "low|medium|high|very_high",
    "reasoning": "Brief explanation of why this classification was chosen",
    "importance_score": 0.0-1.0,
    "sentiment": "positive|negative|neutral"
}}
""",
            
            'entity_extraction': """
Extract relevant entities and information from this message:

Message: "{message}"
Context: "{context}"

Extract and return in JSON format:
{{
    "people": ["list of people mentioned"],
    "places": ["list of places mentioned"],
    "organizations": ["list of organizations mentioned"],
    "dates_times": ["list of dates and times mentioned"],
    "topics": ["list of main topics discussed"],
    "action_items": ["list of tasks or actions mentioned"],
    "phone_numbers": ["list of phone numbers mentioned"],
    "emails": ["list of email addresses mentioned"],
    "urls": ["list of URLs mentioned"],
    "financial_info": ["list of financial information mentioned"],
    "health_info": ["list of health-related information mentioned"]
}}
""",
            
            'contact_identification': """
Identify and extract contact information from this message:

Message: "{message}"
Known Contacts: {known_contacts}

Determine:
1. Who is speaking (if identifiable)
2. Who is being mentioned
3. New contacts that should be tracked
4. Relationship context

Return in JSON format:
{{
    "speaker": "identified speaker or null",
    "mentioned_contacts": ["list of contacts mentioned"],
    "new_contacts": ["list of new contacts to track"],
    "relationship_context": "description of relationships mentioned"
}}
""",
            
            'topic_analysis': """
Analyze the topics and themes in this message:

Message: "{message}"
Recent Topics: {recent_topics}

Identify:
1. Main topics discussed
2. Subtopics and themes
3. Topic relationships
4. Topic importance

Return in JSON format:
{{
    "main_topics": ["list of main topics"],
    "subtopics": ["list of subtopics"],
    "topic_relationships": ["how topics relate to each other"],
    "topic_importance": {{"topic": importance_score}},
    "new_topics": ["topics not seen recently"]
}}
"""
        }
    
    def _load_entity_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for entity extraction"""
        return {
            'phone_numbers': [
                r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
                r'\+?([0-9]{1,3})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})'
            ],
            'emails': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'urls': [
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            ],
            'dates': [
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b(?:today|tomorrow|yesterday|next week|last week|this week)\b'
            ],
            'times': [
                r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b',
                r'\b(?:morning|afternoon|evening|night|noon|midnight)\b'
            ],
            'money': [
                r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
                r'\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|cents?)\b'
            ]
        }
    
    async def classify_message(self, message: str, context: ConversationContext) -> ClassificationResult:
        """Classify a message using AI and rule-based approaches"""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(message, context)
            if self._is_cache_valid(cache_key):
                logger.debug(f"Using cached classification for message")
                return self.classification_cache[cache_key]
            
            # Step 1: Primary classification using AI
            primary_result = await self._classify_primary_tag(message, context)
            
            # Step 2: Extract entities
            entities = await self._extract_entities(message, context)
            
            # Step 3: Identify contacts
            contacts = await self._identify_contacts(message, context)
            
            # Step 4: Analyze topics
            topics = await self._analyze_topics(message, context)
            
            # Step 5: Extract temporal references
            temporal_refs = self._extract_temporal_references(message)
            
            # Step 6: Determine secondary tags
            secondary_tags = self._determine_secondary_tags(
                message, primary_result, entities, contacts, topics
            )
            
            # Create classification result
            result = ClassificationResult(
                primary_tag=MemoryTag(primary_result['primary_tag']),
                confidence=ClassificationConfidence(primary_result['confidence']),
                secondary_tags=secondary_tags,
                extracted_entities=entities,
                sentiment=primary_result['sentiment'],
                importance_score=primary_result['importance_score'],
                related_contacts=contacts['mentioned_contacts'] + contacts['new_contacts'],
                topics=topics['main_topics'],
                action_items=entities.get('action_items', []),
                temporal_references=temporal_refs,
                reasoning=primary_result['reasoning']
            )
            
            # Cache the result
            self.classification_cache[cache_key] = result
            self.cache_expiry[cache_key] = datetime.now() + self.cache_duration
            
            logger.info(f"🏷️ Classified message: {result.primary_tag.value} (confidence: {result.confidence.value})")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to classify message: {e}")
            # Return default classification
            return ClassificationResult(
                primary_tag=MemoryTag.GENERAL,
                confidence=ClassificationConfidence.LOW,
                secondary_tags=[],
                extracted_entities={},
                sentiment="neutral",
                importance_score=0.5,
                related_contacts=[],
                topics=[],
                action_items=[],
                temporal_references=[],
                reasoning=f"Classification failed: {str(e)}"
            )
    
    async def _classify_primary_tag(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Use AI to classify the primary memory tag"""
        try:
            prompt = self.classification_prompts['primary_classification'].format(
                message=message,
                context=context.user_phone,
                user_profile=json.dumps(context.user_profile or {}),
                conversation_history=json.dumps(context.conversation_history[-5:])  # Last 5 messages
            )
            
            response = await self._call_openai(prompt, max_tokens=200)
            
            # Parse JSON response
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # Fallback parsing
                return self._parse_classification_fallback(response)
                
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {
                'primary_tag': 'general',
                'confidence': 'low',
                'reasoning': f'AI classification failed: {str(e)}',
                'importance_score': 0.5,
                'sentiment': 'neutral'
            }
    
    async def _extract_entities(self, message: str, context: ConversationContext) -> Dict[str, List[str]]:
        """Extract entities from the message"""
        try:
            # Use AI for entity extraction
            prompt = self.classification_prompts['entity_extraction'].format(
                message=message,
                context=context.user_phone
            )
            
            response = await self._call_openai(prompt, max_tokens=300)
            
            try:
                ai_entities = json.loads(response)
            except json.JSONDecodeError:
                ai_entities = {}
            
            # Combine with regex-based extraction
            regex_entities = self._extract_entities_regex(message)
            
            # Merge results
            combined_entities = {}
            all_keys = set(ai_entities.keys()) | set(regex_entities.keys())
            
            for key in all_keys:
                combined_entities[key] = list(set(
                    ai_entities.get(key, []) + regex_entities.get(key, [])
                ))
            
            return combined_entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return self._extract_entities_regex(message)
    
    def _extract_entities_regex(self, message: str) -> Dict[str, List[str]]:
        """Extract entities using regex patterns"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            entities[entity_type] = []
            
            for pattern in patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                if matches:
                    if isinstance(matches[0], tuple):
                        # Handle grouped matches
                        entities[entity_type].extend([''.join(match) for match in matches])
                    else:
                        entities[entity_type].extend(matches)
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    async def _identify_contacts(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Identify contacts mentioned in the message"""
        try:
            prompt = self.classification_prompts['contact_identification'].format(
                message=message,
                known_contacts=json.dumps(context.known_contacts)
            )
            
            response = await self._call_openai(prompt, max_tokens=200)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    'speaker': '',
                    'mentioned_contacts': [],
                    'new_contacts': [],
                    'relationship_context': ''
                }
                
        except Exception as e:
            logger.error(f"Contact identification failed: {e}")
            return {
                'speaker': '',
                'mentioned_contacts': [],
                'new_contacts': [],
                'relationship_context': ''
            }
    
    async def _analyze_topics(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Analyze topics in the message"""
        try:
            prompt = self.classification_prompts['topic_analysis'].format(
                message=message,
                recent_topics=json.dumps(context.recent_topics)
            )
            
            response = await self._call_openai(prompt, max_tokens=250)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    'main_topics': [],
                    'subtopics': [],
                    'topic_relationships': [],
                    'topic_importance': {},
                    'new_topics': []
                }
                
        except Exception as e:
            logger.error(f"Topic analysis failed: {e}")
            return {
                'main_topics': [],
                'subtopics': [],
                'topic_relationships': [],
                'topic_importance': {},
                'new_topics': []
            }
    
    def _extract_temporal_references(self, message: str) -> List[str]:
        """Extract temporal references from the message"""
        temporal_patterns = [
            r'\b(?:today|tomorrow|yesterday)\b',
            r'\b(?:next|last|this)\s+(?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:in|after|before)\s+\d+\s+(?:minutes?|hours?|days?|weeks?|months?|years?)\b',
            r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        ]
        
        temporal_refs = []
        for pattern in temporal_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            temporal_refs.extend(matches)
        
        return list(set(temporal_refs))
    
    def _determine_secondary_tags(self, message: str, primary_result: Dict[str, Any],
                                 entities: Dict[str, List[str]], contacts: Dict[str, List[str]],
                                 topics: Dict[str, Any]) -> List[MemoryTag]:
        """Determine secondary tags based on analysis"""
        secondary_tags = []
        
        # Check for financial information
        if entities.get('financial_info') or entities.get('money'):
            if primary_result['primary_tag'] != 'confidential':
                secondary_tags.append(MemoryTag.CONFIDENTIAL)
        
        # Check for health information
        if entities.get('health_info'):
            if primary_result['primary_tag'] not in ['confidential', 'secret']:
                secondary_tags.append(MemoryTag.CONFIDENTIAL)
        
        # Check for personal relationships
        relationship_context = contacts.get('relationship_context', '')
        if relationship_context and isinstance(relationship_context, str) and 'personal' in relationship_context.lower():
            if primary_result['primary_tag'] == 'general':
                secondary_tags.append(MemoryTag.CONFIDENTIAL)
        
        # Check for high importance
        if primary_result.get('importance_score', 0) > 0.8:
            if MemoryTag.CHRONOLOGICAL not in secondary_tags:
                secondary_tags.append(MemoryTag.CHRONOLOGICAL)
        
        return secondary_tags
    
    async def _call_openai(self, prompt: str, max_tokens: int = 150) -> str:
        """Call OpenAI API with error handling"""
        # Check if OpenAI client is available
        if not self.openai_client:
            # Return a fallback response when API is not configured
            logger.warning("⚠️ OpenAI API not configured - using fallback classification")
            return self._get_fallback_response(prompt)
        
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert AI assistant for personal memory management and conversation analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=max_tokens,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            return content.strip() if content else ''
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            # Return fallback response instead of raising
            return self._get_fallback_response(prompt)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Generate fallback response when OpenAI API is not available"""
        # Simple rule-based fallback that returns JSON-like response
        if "primary_classification" in prompt:
            return json.dumps({
                "primary_tag": "general",
                "confidence": "medium",
                "reasoning": "Fallback classification - AI not available",
                "importance_score": 0.5,
                "sentiment": "neutral"
            })
        elif "entity_extraction" in prompt:
            return json.dumps({
                "people": [],
                "locations": [],
                "dates": [],
                "phone_numbers": [],
                "email_addresses": [],
                "action_items": [],
                "financial_info": [],
                "health_info": []
            })
        elif "contact_identification" in prompt:
            return json.dumps({
                "mentioned_contacts": [],
                "new_contacts": [],
                "relationship_context": "unknown"
            })
        elif "topic_analysis" in prompt:
            return json.dumps({
                "main_topics": ["general"],
                "subtopics": [],
                "keywords": [],
                "domain": "general"
            })
        else:
            # Generic fallback
            return json.dumps({
                "result": "fallback",
                "confidence": "low"
            })
    
    def _parse_classification_fallback(self, response: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails"""
        # Simple regex-based parsing
        result = {
            'primary_tag': 'general',
            'confidence': 'medium',
            'reasoning': 'Fallback classification',
            'importance_score': 0.5,
            'sentiment': 'neutral'
        }
        
        # Try to extract tag
        tag_match = re.search(r'(?:primary_tag|tag).*?(?:chronological|general|confidential|secret|ultra_secret)', response, re.IGNORECASE)
        if tag_match:
            tag = tag_match.group().split()[-1].lower()
            if tag in ['chronological', 'general', 'confidential', 'secret', 'ultra_secret']:
                result['primary_tag'] = tag
        
        # Try to extract confidence
        conf_match = re.search(r'(?:confidence).*?(?:low|medium|high|very_high)', response, re.IGNORECASE)
        if conf_match:
            conf = conf_match.group().split()[-1].lower()
            if conf in ['low', 'medium', 'high', 'very_high']:
                result['confidence'] = conf
        
        return result
    
    def _generate_cache_key(self, message: str, context: ConversationContext) -> str:
        """Generate cache key for classification result"""
        content = f"{message}_{context.user_phone}_{len(context.conversation_history)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self.classification_cache:
            return False
        
        if cache_key not in self.cache_expiry:
            return False
        
        return datetime.now() < self.cache_expiry[cache_key]
    
    async def batch_classify_messages(self, messages: List[Tuple[str, ConversationContext]]) -> List[ClassificationResult]:
        """Classify multiple messages in batch"""
        tasks = []
        for message, context in messages:
            task = self.classify_message(message, context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch classification failed for message {i}: {result}")
                # Create default result
                processed_results.append(ClassificationResult(
                    primary_tag=MemoryTag.GENERAL,
                    confidence=ClassificationConfidence.LOW,
                    secondary_tags=[],
                    extracted_entities={},
                    sentiment="neutral",
                    importance_score=0.5,
                    related_contacts=[],
                    topics=[],
                    action_items=[],
                    temporal_references=[],
                    reasoning=f"Batch processing failed: {str(result)}"
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics"""
        total_classifications = len(self.classification_cache)
        
        if total_classifications == 0:
            return {
                'total_classifications': 0,
                'cache_hit_rate': 0,
                'tag_distribution': {},
                'confidence_distribution': {}
            }
        
        # Analyze cached results
        tag_counts = {}
        confidence_counts = {}
        
        for result in self.classification_cache.values():
            tag = result.primary_tag.value
            confidence = result.confidence.value
            
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        
        return {
            'total_classifications': total_classifications,
            'cache_entries': len(self.classification_cache),
            'tag_distribution': tag_counts,
            'confidence_distribution': confidence_counts,
            'average_importance': sum(r.importance_score for r in self.classification_cache.values()) / total_classifications
        }

# Example usage and testing
async def main():
    """Test the conversation classifier"""
    classifier = ConversationClassifier()
    
    # Test context
    context = ConversationContext(
        user_phone="+1234567890",
        conversation_history=[
            {"role": "user", "content": "Hey, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thanks!"}
        ],
        known_contacts=["Mom", "John", "Sarah"],
        recent_topics=["work", "family"]
    )
    
    # Test messages
    test_messages = [
        "Remember to call mom about dinner plans for Sunday",
        "My bank account number is 123456789 and routing is 987654321",
        "I have a doctor's appointment tomorrow at 3 PM",
        "John mentioned the project deadline is next Friday",
        "The password for my crypto wallet is supersecret123"
    ]
    
    for message in test_messages:
        result = await classifier.classify_message(message, context)
        print(f"\nMessage: {message}")
        print(f"Classification: {result.primary_tag.value}")
        print(f"Confidence: {result.confidence.value}")
        print(f"Contacts: {result.related_contacts}")
        print(f"Topics: {result.topics}")
        print(f"Reasoning: {result.reasoning}")
    
    # Test batch classification
    batch_messages = [(msg, context) for msg in test_messages]
    batch_results = await classifier.batch_classify_messages(batch_messages)
    print(f"\nBatch processed {len(batch_results)} messages")
    
    # Get stats
    stats = classifier.get_classification_stats()
    print(f"\nClassification Stats: {stats}")

if __name__ == "__main__":
    asyncio.run(main())

