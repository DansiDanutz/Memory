"""
Memory Harvester Agent - Complete Implementation
The intelligent data collection and preprocessing layer for the Memory Assistant system.

This agent is responsible for:
- Multi-source data collection (chat, documents, calendar, photos, voice)
- Content normalization and standardization
- Quality validation and duplicate detection
- Metadata enrichment and context extraction
- Adaptive learning and source intelligence
"""

import asyncio
import logging
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles
import httpx
from pathlib import Path
import mimetypes
import base64

# External libraries for content processing
try:
    import speech_recognition as sr
    from PIL import Image, ExifTags
    import pytesseract
    from langdetect import detect
    from textblob import TextBlob
except ImportError as e:
    logging.warning(f"Optional dependency not available: {e}")

logger = logging.getLogger(__name__)

class SourceType(Enum):
    """Enumeration of supported memory sources"""
    CHAT_MESSAGE = "chat_message"
    EMAIL = "email"
    DOCUMENT = "document"
    CALENDAR_EVENT = "calendar_event"
    PHOTO = "photo"
    VOICE_MESSAGE = "voice_message"
    MANUAL_ENTRY = "manual_entry"
    WEB_CLIP = "web_clip"
    SMS = "sms"
    SOCIAL_MEDIA = "social_media"

class ContentType(Enum):
    """Enumeration of content types"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    MIXED = "mixed"

class QualityLevel(Enum):
    """Quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    REJECTED = "rejected"

@dataclass
class RawMemoryInput:
    """Raw memory input from various sources"""
    content: Union[str, bytes, Dict[str, Any]]
    source_type: SourceType
    source_metadata: Dict[str, Any]
    timestamp: Optional[datetime] = None
    user_id: Optional[str] = None
    content_type: Optional[ContentType] = None

@dataclass
class ProcessedMemory:
    """Processed and normalized memory object"""
    id: str
    user_id: str
    content: str
    source_type: SourceType
    content_type: ContentType
    timestamp: datetime
    participants: List[str]
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    quality_score: float
    quality_level: QualityLevel
    language: str
    sentiment: Dict[str, float]
    tags: List[str]
    location: Optional[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = None

@dataclass
class ValidationResult:
    """Result of content validation"""
    is_valid: bool
    quality_score: float
    quality_level: QualityLevel
    issues: List[str]
    suggestions: List[str]

class MemoryHarvesterAgent:
    """
    Advanced Memory Harvester Agent with multi-source intelligence
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False
        
        # Core components
        self.content_processors = {}
        self.quality_validators = {}
        self.metadata_extractors = {}
        self.duplicate_detector = DuplicateDetector()
        self.adaptive_learner = AdaptiveLearner()
        
        # Performance metrics
        self.processing_stats = {
            'total_processed': 0,
            'by_source_type': {},
            'quality_distribution': {},
            'processing_times': [],
            'error_count': 0
        }
        
        # Cache for frequently accessed data
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        logger.info("Memory Harvester Agent initialized")
    
    async def initialize(self):
        """Initialize the agent and all its components"""
        try:
            logger.info("🔍 Initializing Memory Harvester Agent...")
            
            # Initialize content processors
            await self._initialize_content_processors()
            
            # Initialize quality validators
            await self._initialize_quality_validators()
            
            # Initialize metadata extractors
            await self._initialize_metadata_extractors()
            
            # Initialize duplicate detector
            await self.duplicate_detector.initialize()
            
            # Initialize adaptive learner
            await self.adaptive_learner.initialize()
            
            # Load user preferences and patterns
            await self._load_user_patterns()
            
            self.is_initialized = True
            logger.info("✅ Memory Harvester Agent initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize Memory Harvester Agent: {e}")
            raise
    
    async def process_memory(self, raw_input: RawMemoryInput) -> ProcessedMemory:
        """
        Main entry point for processing raw memory input
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Processing memory from {raw_input.source_type.value}")
            
            # Step 1: Validate input
            if not await self._validate_input(raw_input):
                raise ValueError("Invalid input data")
            
            # Step 2: Detect and handle duplicates
            duplicate_check = await self.duplicate_detector.check_duplicate(raw_input)
            if duplicate_check.is_duplicate:
                return await self._handle_duplicate(raw_input, duplicate_check)
            
            # Step 3: Process content based on source type
            processed_content = await self._process_content_by_source(raw_input)
            
            # Step 4: Normalize content
            normalized_content = await self._normalize_content(processed_content, raw_input)
            
            # Step 5: Extract metadata and context
            metadata = await self._extract_metadata(raw_input, normalized_content)
            context = await self._extract_context(normalized_content, metadata)
            
            # Step 6: Validate quality
            validation_result = await self._validate_quality(normalized_content, context)
            
            # Step 7: Enrich with additional data
            enriched_data = await self._enrich_content(normalized_content, context, metadata)
            
            # Step 8: Create processed memory object
            processed_memory = ProcessedMemory(
                id=self._generate_memory_id(raw_input, normalized_content),
                user_id=raw_input.user_id,
                content=enriched_data['content'],
                source_type=raw_input.source_type,
                content_type=enriched_data['content_type'],
                timestamp=raw_input.timestamp or datetime.now(),
                participants=enriched_data['participants'],
                context=context,
                metadata=metadata,
                quality_score=validation_result.quality_score,
                quality_level=validation_result.quality_level,
                language=enriched_data['language'],
                sentiment=enriched_data['sentiment'],
                tags=enriched_data['tags'],
                location=enriched_data.get('location'),
                attachments=enriched_data.get('attachments', [])
            )
            
            # Step 9: Learn from processing
            await self.adaptive_learner.learn_from_processing(raw_input, processed_memory)
            
            # Step 10: Update statistics
            await self._update_processing_stats(raw_input, processed_memory, start_time)
            
            logger.info(f"✅ Memory processed successfully: {processed_memory.id}")
            return processed_memory
            
        except Exception as e:
            logger.error(f"Error processing memory: {e}")
            await self._update_error_stats(raw_input, e)
            raise
    
    async def process_batch(self, raw_inputs: List[RawMemoryInput]) -> List[ProcessedMemory]:
        """
        Process multiple memories in batch for efficiency
        """
        logger.info(f"Processing batch of {len(raw_inputs)} memories")
        
        # Group by source type for optimized processing
        grouped_inputs = self._group_by_source_type(raw_inputs)
        
        results = []
        for source_type, inputs in grouped_inputs.items():
            batch_results = await self._process_batch_by_source(source_type, inputs)
            results.extend(batch_results)
        
        logger.info(f"✅ Batch processing complete: {len(results)} memories processed")
        return results
    
    async def _initialize_content_processors(self):
        """Initialize content processors for different source types"""
        self.content_processors = {
            SourceType.CHAT_MESSAGE: ChatMessageProcessor(),
            SourceType.EMAIL: EmailProcessor(),
            SourceType.DOCUMENT: DocumentProcessor(),
            SourceType.CALENDAR_EVENT: CalendarEventProcessor(),
            SourceType.PHOTO: PhotoProcessor(),
            SourceType.VOICE_MESSAGE: VoiceMessageProcessor(),
            SourceType.MANUAL_ENTRY: ManualEntryProcessor(),
            SourceType.WEB_CLIP: WebClipProcessor(),
            SourceType.SMS: SMSProcessor(),
            SourceType.SOCIAL_MEDIA: SocialMediaProcessor()
        }
        
        # Initialize each processor
        for processor in self.content_processors.values():
            await processor.initialize()
    
    async def _initialize_quality_validators(self):
        """Initialize quality validation components"""
        self.quality_validators = {
            'content_validator': ContentQualityValidator(),
            'completeness_validator': CompletenessValidator(),
            'relevance_validator': RelevanceValidator(),
            'authenticity_validator': AuthenticityValidator()
        }
        
        for validator in self.quality_validators.values():
            await validator.initialize()
    
    async def _initialize_metadata_extractors(self):
        """Initialize metadata extraction components"""
        self.metadata_extractors = {
            'temporal_extractor': TemporalMetadataExtractor(),
            'location_extractor': LocationMetadataExtractor(),
            'participant_extractor': ParticipantExtractor(),
            'context_extractor': ContextExtractor(),
            'sentiment_extractor': SentimentExtractor(),
            'tag_extractor': TagExtractor()
        }
        
        for extractor in self.metadata_extractors.values():
            await extractor.initialize()
    
    async def _process_content_by_source(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process content using appropriate source-specific processor"""
        processor = self.content_processors.get(raw_input.source_type)
        if not processor:
            raise ValueError(f"No processor available for source type: {raw_input.source_type}")
        
        return await processor.process(raw_input)
    
    async def _normalize_content(self, processed_content: Dict[str, Any], 
                                raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Normalize content to standard format"""
        normalizer = ContentNormalizer()
        return await normalizer.normalize(processed_content, raw_input)
    
    async def _extract_metadata(self, raw_input: RawMemoryInput, 
                               normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract comprehensive metadata from content"""
        metadata = {}
        
        # Extract metadata using all extractors
        for name, extractor in self.metadata_extractors.items():
            try:
                extracted = await extractor.extract(raw_input, normalized_content)
                metadata[name] = extracted
            except Exception as e:
                logger.warning(f"Metadata extraction failed for {name}: {e}")
                metadata[name] = {}
        
        # Add processing metadata
        metadata['processing'] = {
            'processed_at': datetime.now().isoformat(),
            'processor_version': '1.0.0',
            'source_metadata': raw_input.source_metadata
        }
        
        return metadata
    
    async def _extract_context(self, normalized_content: Dict[str, Any], 
                              metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contextual information"""
        context_extractor = self.metadata_extractors['context_extractor']
        return await context_extractor.extract_context(normalized_content, metadata)
    
    async def _validate_quality(self, normalized_content: Dict[str, Any], 
                               context: Dict[str, Any]) -> ValidationResult:
        """Validate content quality using multiple validators"""
        validation_results = []
        
        for name, validator in self.quality_validators.items():
            try:
                result = await validator.validate(normalized_content, context)
                validation_results.append(result)
            except Exception as e:
                logger.warning(f"Quality validation failed for {name}: {e}")
        
        # Combine validation results
        return self._combine_validation_results(validation_results)
    
    async def _enrich_content(self, normalized_content: Dict[str, Any], 
                             context: Dict[str, Any], 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich content with additional processed information"""
        enricher = ContentEnricher()
        return await enricher.enrich(normalized_content, context, metadata)
    
    def _generate_memory_id(self, raw_input: RawMemoryInput, 
                           normalized_content: Dict[str, Any]) -> str:
        """Generate unique memory ID"""
        content_hash = hashlib.sha256(
            str(normalized_content.get('content', '')).encode()
        ).hexdigest()[:16]
        
        timestamp = (raw_input.timestamp or datetime.now()).strftime('%Y%m%d_%H%M%S')
        source = raw_input.source_type.value[:4]
        
        return f"mem_{timestamp}_{source}_{content_hash}"
    
    async def _validate_input(self, raw_input: RawMemoryInput) -> bool:
        """Validate raw input data"""
        if not raw_input.user_id:
            logger.error("Missing user_id in raw input")
            return False
        
        if not raw_input.content:
            logger.error("Missing content in raw input")
            return False
        
        if not raw_input.source_type:
            logger.error("Missing source_type in raw input")
            return False
        
        return True
    
    def _group_by_source_type(self, raw_inputs: List[RawMemoryInput]) -> Dict[SourceType, List[RawMemoryInput]]:
        """Group inputs by source type for batch processing"""
        grouped = {}
        for raw_input in raw_inputs:
            if raw_input.source_type not in grouped:
                grouped[raw_input.source_type] = []
            grouped[raw_input.source_type].append(raw_input)
        return grouped
    
    async def _process_batch_by_source(self, source_type: SourceType, 
                                      inputs: List[RawMemoryInput]) -> List[ProcessedMemory]:
        """Process batch of inputs from same source type"""
        processor = self.content_processors.get(source_type)
        if not processor:
            raise ValueError(f"No processor for source type: {source_type}")
        
        # Use processor's batch processing if available
        if hasattr(processor, 'process_batch'):
            return await processor.process_batch(inputs)
        else:
            # Fall back to individual processing
            results = []
            for raw_input in inputs:
                try:
                    result = await self.process_memory(raw_input)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process memory in batch: {e}")
            return results
    
    def _combine_validation_results(self, results: List[ValidationResult]) -> ValidationResult:
        """Combine multiple validation results into single result"""
        if not results:
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                quality_level=QualityLevel.REJECTED,
                issues=["No validation results"],
                suggestions=[]
            )
        
        # Calculate average quality score
        avg_score = sum(r.quality_score for r in results) / len(results)
        
        # Determine overall validity (all must be valid)
        is_valid = all(r.is_valid for r in results)
        
        # Combine issues and suggestions
        all_issues = []
        all_suggestions = []
        for result in results:
            all_issues.extend(result.issues)
            all_suggestions.extend(result.suggestions)
        
        # Determine quality level based on score
        if avg_score >= 0.9:
            quality_level = QualityLevel.EXCELLENT
        elif avg_score >= 0.7:
            quality_level = QualityLevel.GOOD
        elif avg_score >= 0.5:
            quality_level = QualityLevel.ACCEPTABLE
        elif avg_score >= 0.3:
            quality_level = QualityLevel.POOR
        else:
            quality_level = QualityLevel.REJECTED
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=avg_score,
            quality_level=quality_level,
            issues=list(set(all_issues)),  # Remove duplicates
            suggestions=list(set(all_suggestions))
        )
    
    async def _update_processing_stats(self, raw_input: RawMemoryInput, 
                                      processed_memory: ProcessedMemory, 
                                      start_time: datetime):
        """Update processing statistics"""
        processing_time = (datetime.now() - start_time).total_seconds()
        
        self.processing_stats['total_processed'] += 1
        self.processing_stats['processing_times'].append(processing_time)
        
        # Update by source type
        source_type = raw_input.source_type.value
        if source_type not in self.processing_stats['by_source_type']:
            self.processing_stats['by_source_type'][source_type] = 0
        self.processing_stats['by_source_type'][source_type] += 1
        
        # Update quality distribution
        quality_level = processed_memory.quality_level.value
        if quality_level not in self.processing_stats['quality_distribution']:
            self.processing_stats['quality_distribution'][quality_level] = 0
        self.processing_stats['quality_distribution'][quality_level] += 1
    
    async def _update_error_stats(self, raw_input: RawMemoryInput, error: Exception):
        """Update error statistics"""
        self.processing_stats['error_count'] += 1
        logger.error(f"Processing error for {raw_input.source_type.value}: {error}")
    
    async def _handle_duplicate(self, raw_input: RawMemoryInput, 
                               duplicate_check: 'DuplicateCheckResult') -> ProcessedMemory:
        """Handle duplicate memory detection"""
        logger.info(f"Duplicate detected: {duplicate_check.original_id}")
        
        # Return reference to original memory
        # In a real implementation, you'd fetch the original from database
        return duplicate_check.original_memory
    
    async def _load_user_patterns(self):
        """Load user-specific patterns for adaptive processing"""
        # This would load user preferences and historical patterns
        # from the database to customize processing
        pass
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        stats = self.processing_stats.copy()
        
        if stats['processing_times']:
            stats['avg_processing_time'] = sum(stats['processing_times']) / len(stats['processing_times'])
            stats['max_processing_time'] = max(stats['processing_times'])
            stats['min_processing_time'] = min(stats['processing_times'])
        
        return stats
    
    async def shutdown(self):
        """Shutdown the agent and cleanup resources"""
        logger.info("🛑 Shutting down Memory Harvester Agent...")
        
        # Shutdown all processors
        for processor in self.content_processors.values():
            if hasattr(processor, 'shutdown'):
                await processor.shutdown()
        
        # Shutdown validators
        for validator in self.quality_validators.values():
            if hasattr(validator, 'shutdown'):
                await validator.shutdown()
        
        # Shutdown extractors
        for extractor in self.metadata_extractors.values():
            if hasattr(extractor, 'shutdown'):
                await extractor.shutdown()
        
        # Shutdown other components
        await self.duplicate_detector.shutdown()
        await self.adaptive_learner.shutdown()
        
        logger.info("✅ Memory Harvester Agent shutdown complete")

# Supporting Classes

class DuplicateDetector:
    """Detects duplicate memories using multiple strategies"""
    
    def __init__(self):
        self.content_hashes = set()
        self.similarity_threshold = 0.85
    
    async def initialize(self):
        """Initialize duplicate detection"""
        # Load existing content hashes from database
        pass
    
    async def check_duplicate(self, raw_input: RawMemoryInput) -> 'DuplicateCheckResult':
        """Check if memory is duplicate"""
        content_str = str(raw_input.content)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        
        # Exact match check
        if content_hash in self.content_hashes:
            return DuplicateCheckResult(
                is_duplicate=True,
                similarity_score=1.0,
                original_id=f"hash_{content_hash}",
                original_memory=None  # Would fetch from database
            )
        
        # Similarity check (simplified - would use more sophisticated algorithms)
        # This is where you'd implement fuzzy matching, semantic similarity, etc.
        
        # Add to known hashes
        self.content_hashes.add(content_hash)
        
        return DuplicateCheckResult(
            is_duplicate=False,
            similarity_score=0.0,
            original_id=None,
            original_memory=None
        )
    
    async def shutdown(self):
        """Shutdown duplicate detector"""
        pass

@dataclass
class DuplicateCheckResult:
    """Result of duplicate detection"""
    is_duplicate: bool
    similarity_score: float
    original_id: Optional[str]
    original_memory: Optional[ProcessedMemory]

class AdaptiveLearner:
    """Learns from processing patterns to improve future processing"""
    
    def __init__(self):
        self.learning_data = []
    
    async def initialize(self):
        """Initialize adaptive learning"""
        pass
    
    async def learn_from_processing(self, raw_input: RawMemoryInput, 
                                   processed_memory: ProcessedMemory):
        """Learn from successful processing"""
        learning_record = {
            'source_type': raw_input.source_type.value,
            'quality_score': processed_memory.quality_score,
            'processing_time': datetime.now().isoformat(),
            'content_length': len(processed_memory.content),
            'language': processed_memory.language,
            'sentiment': processed_memory.sentiment
        }
        
        self.learning_data.append(learning_record)
        
        # Implement learning algorithms here
        # This could include updating processing parameters,
        # improving quality thresholds, etc.
    
    async def shutdown(self):
        """Shutdown adaptive learner"""
        pass

# Content Processors

class BaseContentProcessor:
    """Base class for content processors"""
    
    async def initialize(self):
        """Initialize processor"""
        pass
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process raw input - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def shutdown(self):
        """Shutdown processor"""
        pass

class ChatMessageProcessor(BaseContentProcessor):
    """Processes chat messages from various platforms"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process chat message"""
        content = raw_input.content
        
        if isinstance(content, dict):
            # Structured chat message
            text_content = content.get('text', '')
            sender = content.get('sender', '')
            recipients = content.get('recipients', [])
            platform = content.get('platform', 'unknown')
        else:
            # Plain text message
            text_content = str(content)
            sender = raw_input.source_metadata.get('sender', '')
            recipients = raw_input.source_metadata.get('recipients', [])
            platform = raw_input.source_metadata.get('platform', 'unknown')
        
        # Extract mentions, hashtags, emojis
        mentions = self._extract_mentions(text_content)
        hashtags = self._extract_hashtags(text_content)
        emojis = self._extract_emojis(text_content)
        
        return {
            'content': text_content,
            'content_type': ContentType.TEXT,
            'sender': sender,
            'recipients': recipients,
            'platform': platform,
            'mentions': mentions,
            'hashtags': hashtags,
            'emojis': emojis,
            'message_type': self._classify_message_type(text_content)
        }
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from text"""
        return re.findall(r'@(\w+)', text)
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract #hashtags from text"""
        return re.findall(r'#(\w+)', text)
    
    def _extract_emojis(self, text: str) -> List[str]:
        """Extract emojis from text"""
        # Simplified emoji detection
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "]+", flags=re.UNICODE
        )
        return emoji_pattern.findall(text)
    
    def _classify_message_type(self, text: str) -> str:
        """Classify type of message"""
        text_lower = text.lower()
        
        if '?' in text:
            return 'question'
        elif any(word in text_lower for word in ['thanks', 'thank you', 'thx']):
            return 'gratitude'
        elif any(word in text_lower for word in ['sorry', 'apologize', 'my bad']):
            return 'apology'
        elif any(word in text_lower for word in ['love', 'miss', 'care']):
            return 'affection'
        elif len(text.split()) > 50:
            return 'long_message'
        else:
            return 'general'

class EmailProcessor(BaseContentProcessor):
    """Processes email messages"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process email"""
        if isinstance(raw_input.content, dict):
            email_data = raw_input.content
        else:
            # Parse email from raw text
            email_data = self._parse_email_text(str(raw_input.content))
        
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        sender = email_data.get('from', '')
        recipients = email_data.get('to', [])
        cc = email_data.get('cc', [])
        bcc = email_data.get('bcc', [])
        
        # Combine subject and body
        full_content = f"{subject}\n\n{body}" if subject else body
        
        return {
            'content': full_content,
            'content_type': ContentType.TEXT,
            'subject': subject,
            'body': body,
            'sender': sender,
            'recipients': recipients,
            'cc': cc,
            'bcc': bcc,
            'email_type': self._classify_email_type(subject, body),
            'importance': self._assess_importance(email_data)
        }
    
    def _parse_email_text(self, email_text: str) -> Dict[str, Any]:
        """Parse email from raw text"""
        # Simplified email parsing
        lines = email_text.split('\n')
        email_data = {}
        
        # Extract headers
        for i, line in enumerate(lines):
            if line.startswith('Subject:'):
                email_data['subject'] = line[8:].strip()
            elif line.startswith('From:'):
                email_data['from'] = line[5:].strip()
            elif line.startswith('To:'):
                email_data['to'] = [addr.strip() for addr in line[3:].split(',')]
            elif line == '':  # Empty line indicates start of body
                email_data['body'] = '\n'.join(lines[i+1:])
                break
        
        return email_data
    
    def _classify_email_type(self, subject: str, body: str) -> str:
        """Classify email type"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        if any(word in subject_lower for word in ['meeting', 'calendar', 'appointment']):
            return 'meeting'
        elif any(word in subject_lower for word in ['invoice', 'payment', 'bill']):
            return 'financial'
        elif any(word in subject_lower for word in ['newsletter', 'update', 'news']):
            return 'newsletter'
        elif 're:' in subject_lower or 'fwd:' in subject_lower:
            return 'reply_forward'
        else:
            return 'general'
    
    def _assess_importance(self, email_data: Dict[str, Any]) -> str:
        """Assess email importance"""
        subject = email_data.get('subject', '').lower()
        
        if any(word in subject for word in ['urgent', 'important', 'asap']):
            return 'high'
        elif any(word in subject for word in ['fyi', 'newsletter', 'notification']):
            return 'low'
        else:
            return 'medium'

class DocumentProcessor(BaseContentProcessor):
    """Processes documents (PDF, Word, etc.)"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process document"""
        if isinstance(raw_input.content, bytes):
            # Binary document content
            text_content = await self._extract_text_from_binary(
                raw_input.content, 
                raw_input.source_metadata.get('mime_type', '')
            )
        else:
            # Text document
            text_content = str(raw_input.content)
        
        # Extract document metadata
        doc_metadata = await self._extract_document_metadata(raw_input)
        
        return {
            'content': text_content,
            'content_type': ContentType.DOCUMENT,
            'document_type': doc_metadata.get('type', 'unknown'),
            'title': doc_metadata.get('title', ''),
            'author': doc_metadata.get('author', ''),
            'creation_date': doc_metadata.get('creation_date'),
            'page_count': doc_metadata.get('page_count', 1),
            'word_count': len(text_content.split()),
            'language': doc_metadata.get('language', 'unknown')
        }
    
    async def _extract_text_from_binary(self, content: bytes, mime_type: str) -> str:
        """Extract text from binary document"""
        # This would use libraries like PyPDF2, python-docx, etc.
        # For now, return placeholder
        return f"[Document content - {mime_type}]"
    
    async def _extract_document_metadata(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Extract document metadata"""
        metadata = raw_input.source_metadata.copy()
        
        # Add document-specific metadata extraction here
        return metadata

class CalendarEventProcessor(BaseContentProcessor):
    """Processes calendar events"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process calendar event"""
        if isinstance(raw_input.content, dict):
            event_data = raw_input.content
        else:
            event_data = json.loads(str(raw_input.content))
        
        title = event_data.get('title', event_data.get('summary', ''))
        description = event_data.get('description', '')
        location = event_data.get('location', '')
        start_time = event_data.get('start_time')
        end_time = event_data.get('end_time')
        attendees = event_data.get('attendees', [])
        
        # Create content from event details
        content_parts = [title]
        if description:
            content_parts.append(description)
        if location:
            content_parts.append(f"Location: {location}")
        
        full_content = '\n'.join(content_parts)
        
        return {
            'content': full_content,
            'content_type': ContentType.TEXT,
            'title': title,
            'description': description,
            'location': location,
            'start_time': start_time,
            'end_time': end_time,
            'attendees': attendees,
            'event_type': self._classify_event_type(title, description),
            'duration': self._calculate_duration(start_time, end_time)
        }
    
    def _classify_event_type(self, title: str, description: str) -> str:
        """Classify calendar event type"""
        text = f"{title} {description}".lower()
        
        if any(word in text for word in ['meeting', 'call', 'conference']):
            return 'meeting'
        elif any(word in text for word in ['birthday', 'anniversary', 'celebration']):
            return 'celebration'
        elif any(word in text for word in ['appointment', 'doctor', 'dentist']):
            return 'appointment'
        elif any(word in text for word in ['vacation', 'holiday', 'trip']):
            return 'travel'
        else:
            return 'general'
    
    def _calculate_duration(self, start_time: str, end_time: str) -> Optional[int]:
        """Calculate event duration in minutes"""
        try:
            if start_time and end_time:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                return int((end - start).total_seconds() / 60)
        except Exception:
            pass
        return None

class PhotoProcessor(BaseContentProcessor):
    """Processes photos and extracts memory content"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process photo"""
        if isinstance(raw_input.content, bytes):
            image_data = raw_input.content
        else:
            # Assume it's a file path or URL
            image_data = await self._load_image_data(str(raw_input.content))
        
        # Extract EXIF data
        exif_data = await self._extract_exif_data(image_data)
        
        # Extract text from image (OCR)
        ocr_text = await self._extract_text_from_image(image_data)
        
        # Analyze image content (would use computer vision APIs)
        image_analysis = await self._analyze_image_content(image_data)
        
        # Create textual description
        content_parts = []
        if ocr_text:
            content_parts.append(f"Text in image: {ocr_text}")
        if image_analysis.get('description'):
            content_parts.append(f"Image shows: {image_analysis['description']}")
        
        content = '\n'.join(content_parts) if content_parts else "[Photo]"
        
        return {
            'content': content,
            'content_type': ContentType.IMAGE,
            'ocr_text': ocr_text,
            'image_analysis': image_analysis,
            'exif_data': exif_data,
            'location': exif_data.get('location'),
            'timestamp': exif_data.get('datetime'),
            'camera_info': exif_data.get('camera_info', {})
        }
    
    async def _load_image_data(self, image_path: str) -> bytes:
        """Load image data from file or URL"""
        if image_path.startswith('http'):
            # Download from URL
            async with httpx.AsyncClient() as client:
                response = await client.get(image_path)
                return response.content
        else:
            # Read from file
            async with aiofiles.open(image_path, 'rb') as f:
                return await f.read()
    
    async def _extract_exif_data(self, image_data: bytes) -> Dict[str, Any]:
        """Extract EXIF data from image"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            image = Image.open(io.BytesIO(image_data))
            exif_data = {}
            
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_data[tag] = value
            
            return exif_data
        except Exception as e:
            logger.warning(f"Failed to extract EXIF data: {e}")
            return {}
    
    async def _extract_text_from_image(self, image_data: bytes) -> str:
        """Extract text from image using OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(io.BytesIO(image_data))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""
    
    async def _analyze_image_content(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image content using computer vision"""
        # This would integrate with services like Google Vision API,
        # AWS Rekognition, or Azure Computer Vision
        # For now, return placeholder
        return {
            'description': 'Image analysis not implemented',
            'objects': [],
            'faces': [],
            'text': [],
            'landmarks': []
        }

class VoiceMessageProcessor(BaseContentProcessor):
    """Processes voice messages and audio files"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process voice message"""
        if isinstance(raw_input.content, bytes):
            audio_data = raw_input.content
        else:
            audio_data = await self._load_audio_data(str(raw_input.content))
        
        # Transcribe audio to text
        transcription = await self._transcribe_audio(audio_data)
        
        # Analyze audio properties
        audio_analysis = await self._analyze_audio_properties(audio_data)
        
        return {
            'content': transcription,
            'content_type': ContentType.AUDIO,
            'transcription': transcription,
            'audio_analysis': audio_analysis,
            'duration': audio_analysis.get('duration'),
            'language': audio_analysis.get('language', 'unknown'),
            'speaker_info': audio_analysis.get('speaker_info', {})
        }
    
    async def _load_audio_data(self, audio_path: str) -> bytes:
        """Load audio data from file or URL"""
        if audio_path.startswith('http'):
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_path)
                return response.content
        else:
            async with aiofiles.open(audio_path, 'rb') as f:
                return await f.read()
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio to text"""
        try:
            import speech_recognition as sr
            
            # This is a simplified implementation
            # In practice, you'd use more sophisticated speech recognition
            recognizer = sr.Recognizer()
            
            # Convert audio data to format suitable for speech recognition
            # This would require additional audio processing
            
            return "[Audio transcription not implemented]"
        except Exception as e:
            logger.warning(f"Audio transcription failed: {e}")
            return "[Audio content]"
    
    async def _analyze_audio_properties(self, audio_data: bytes) -> Dict[str, Any]:
        """Analyze audio properties"""
        # This would analyze audio properties like duration, quality, etc.
        return {
            'duration': None,
            'quality': 'unknown',
            'language': 'unknown',
            'speaker_info': {}
        }

class ManualEntryProcessor(BaseContentProcessor):
    """Processes manually entered memories"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process manual entry"""
        content = str(raw_input.content)
        
        return {
            'content': content,
            'content_type': ContentType.TEXT,
            'entry_type': 'manual',
            'word_count': len(content.split()),
            'character_count': len(content)
        }

class WebClipProcessor(BaseContentProcessor):
    """Processes web page clips and bookmarks"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process web clip"""
        if isinstance(raw_input.content, dict):
            clip_data = raw_input.content
        else:
            clip_data = {'content': str(raw_input.content)}
        
        url = clip_data.get('url', '')
        title = clip_data.get('title', '')
        content = clip_data.get('content', '')
        selection = clip_data.get('selection', '')
        
        # Use selection if available, otherwise full content
        main_content = selection if selection else content
        
        # Create full content with metadata
        full_content_parts = []
        if title:
            full_content_parts.append(f"Title: {title}")
        if url:
            full_content_parts.append(f"URL: {url}")
        if main_content:
            full_content_parts.append(f"Content: {main_content}")
        
        full_content = '\n'.join(full_content_parts)
        
        return {
            'content': full_content,
            'content_type': ContentType.TEXT,
            'url': url,
            'title': title,
            'selection': selection,
            'full_content': content,
            'domain': self._extract_domain(url),
            'clip_type': self._classify_web_clip(title, content)
        }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return 'unknown'
    
    def _classify_web_clip(self, title: str, content: str) -> str:
        """Classify web clip type"""
        text = f"{title} {content}".lower()
        
        if any(word in text for word in ['news', 'article', 'report']):
            return 'news'
        elif any(word in text for word in ['recipe', 'cooking', 'ingredients']):
            return 'recipe'
        elif any(word in text for word in ['tutorial', 'how to', 'guide']):
            return 'tutorial'
        elif any(word in text for word in ['product', 'buy', 'price', 'review']):
            return 'shopping'
        else:
            return 'general'

class SMSProcessor(BaseContentProcessor):
    """Processes SMS messages"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process SMS message"""
        # SMS processing is similar to chat messages but with SMS-specific handling
        chat_processor = ChatMessageProcessor()
        result = await chat_processor.process(raw_input)
        
        # Add SMS-specific processing
        result['platform'] = 'sms'
        result['message_type'] = 'sms'
        
        return result

class SocialMediaProcessor(BaseContentProcessor):
    """Processes social media posts"""
    
    async def process(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Process social media post"""
        if isinstance(raw_input.content, dict):
            post_data = raw_input.content
        else:
            post_data = {'text': str(raw_input.content)}
        
        text = post_data.get('text', '')
        platform = post_data.get('platform', 'unknown')
        author = post_data.get('author', '')
        likes = post_data.get('likes', 0)
        shares = post_data.get('shares', 0)
        comments = post_data.get('comments', [])
        
        # Extract social media specific elements
        mentions = re.findall(r'@(\w+)', text)
        hashtags = re.findall(r'#(\w+)', text)
        
        return {
            'content': text,
            'content_type': ContentType.TEXT,
            'platform': platform,
            'author': author,
            'mentions': mentions,
            'hashtags': hashtags,
            'engagement': {
                'likes': likes,
                'shares': shares,
                'comments': len(comments)
            },
            'post_type': self._classify_post_type(text, post_data)
        }
    
    def _classify_post_type(self, text: str, post_data: Dict[str, Any]) -> str:
        """Classify social media post type"""
        if post_data.get('images'):
            return 'photo_post'
        elif post_data.get('video'):
            return 'video_post'
        elif len(text.split()) > 100:
            return 'long_post'
        elif any(word in text.lower() for word in ['check out', 'link', 'http']):
            return 'shared_link'
        else:
            return 'text_post'

# Quality Validators

class BaseQualityValidator:
    """Base class for quality validators"""
    
    async def initialize(self):
        """Initialize validator"""
        pass
    
    async def validate(self, content: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate content quality"""
        raise NotImplementedError
    
    async def shutdown(self):
        """Shutdown validator"""
        pass

class ContentQualityValidator(BaseQualityValidator):
    """Validates content quality and completeness"""
    
    async def validate(self, content: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate content quality"""
        issues = []
        suggestions = []
        score = 1.0
        
        text_content = content.get('content', '')
        
        # Check content length
        if len(text_content.strip()) < 10:
            issues.append("Content too short")
            score -= 0.3
            suggestions.append("Add more descriptive content")
        
        # Check for meaningful content
        if not text_content.strip():
            issues.append("Empty content")
            score -= 0.5
        
        # Check for spam indicators
        if self._is_spam_like(text_content):
            issues.append("Content appears spam-like")
            score -= 0.4
        
        # Check language quality
        if self._has_poor_language_quality(text_content):
            issues.append("Poor language quality detected")
            score -= 0.2
            suggestions.append("Consider improving grammar and spelling")
        
        score = max(0.0, score)
        is_valid = score >= 0.3
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=score,
            quality_level=self._score_to_quality_level(score),
            issues=issues,
            suggestions=suggestions
        )
    
    def _is_spam_like(self, text: str) -> bool:
        """Check if text appears spam-like"""
        spam_indicators = [
            'click here', 'buy now', 'limited time', 'act now',
            'free money', 'guaranteed', 'no risk'
        ]
        text_lower = text.lower()
        return sum(1 for indicator in spam_indicators if indicator in text_lower) >= 2
    
    def _has_poor_language_quality(self, text: str) -> bool:
        """Check for poor language quality"""
        # Simplified check - in practice would use more sophisticated NLP
        words = text.split()
        if len(words) < 3:
            return False
        
        # Check for excessive repetition
        unique_words = set(words)
        repetition_ratio = len(unique_words) / len(words)
        
        return repetition_ratio < 0.3
    
    def _score_to_quality_level(self, score: float) -> QualityLevel:
        """Convert score to quality level"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.REJECTED

class CompletenessValidator(BaseQualityValidator):
    """Validates completeness of memory data"""
    
    async def validate(self, content: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate completeness"""
        issues = []
        suggestions = []
        score = 1.0
        
        required_fields = ['content', 'content_type']
        for field in required_fields:
            if field not in content or not content[field]:
                issues.append(f"Missing required field: {field}")
                score -= 0.3
        
        # Check for temporal information
        if 'timestamp' not in context:
            issues.append("Missing timestamp information")
            score -= 0.1
            suggestions.append("Add timestamp for better temporal context")
        
        # Check for participant information
        if content.get('content_type') == ContentType.TEXT:
            if 'participants' not in content or not content['participants']:
                suggestions.append("Consider adding participant information")
                score -= 0.05
        
        score = max(0.0, score)
        is_valid = score >= 0.5
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=score,
            quality_level=self._score_to_quality_level(score),
            issues=issues,
            suggestions=suggestions
        )
    
    def _score_to_quality_level(self, score: float) -> QualityLevel:
        """Convert score to quality level"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.REJECTED

class RelevanceValidator(BaseQualityValidator):
    """Validates relevance of content as a memory"""
    
    async def validate(self, content: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate relevance"""
        issues = []
        suggestions = []
        score = 1.0
        
        text_content = content.get('content', '')
        
        # Check if content is memory-worthy
        if self._is_trivial_content(text_content):
            issues.append("Content appears trivial for memory storage")
            score -= 0.3
            suggestions.append("Consider if this content has lasting value")
        
        # Check for personal relevance
        if not self._has_personal_relevance(text_content, context):
            issues.append("Content lacks personal relevance")
            score -= 0.2
        
        score = max(0.0, score)
        is_valid = score >= 0.4
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=score,
            quality_level=self._score_to_quality_level(score),
            issues=issues,
            suggestions=suggestions
        )
    
    def _is_trivial_content(self, text: str) -> bool:
        """Check if content is trivial"""
        trivial_patterns = [
            r'^(ok|okay|yes|no|k|sure)$',
            r'^(lol|haha|hehe)$',
            r'^(thanks?|thx|ty)$'
        ]
        
        text_clean = text.strip().lower()
        return any(re.match(pattern, text_clean) for pattern in trivial_patterns)
    
    def _has_personal_relevance(self, text: str, context: Dict[str, Any]) -> bool:
        """Check for personal relevance"""
        # Simplified check - would use more sophisticated analysis
        personal_indicators = [
            'i ', 'my ', 'me ', 'we ', 'our ', 'us ',
            'family', 'friend', 'work', 'home'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in personal_indicators)
    
    def _score_to_quality_level(self, score: float) -> QualityLevel:
        """Convert score to quality level"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.REJECTED

class AuthenticityValidator(BaseQualityValidator):
    """Validates authenticity of content"""
    
    async def validate(self, content: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate authenticity"""
        issues = []
        suggestions = []
        score = 1.0
        
        # Check for suspicious patterns that might indicate fake content
        text_content = content.get('content', '')
        
        if self._has_suspicious_patterns(text_content):
            issues.append("Content contains suspicious patterns")
            score -= 0.2
        
        # Check source credibility
        source_type = content.get('source_type')
        if source_type and not self._is_credible_source(source_type):
            issues.append("Source may not be credible")
            score -= 0.1
        
        score = max(0.0, score)
        is_valid = score >= 0.6
        
        return ValidationResult(
            is_valid=is_valid,
            quality_score=score,
            quality_level=self._score_to_quality_level(score),
            issues=issues,
            suggestions=suggestions
        )
    
    def _has_suspicious_patterns(self, text: str) -> bool:
        """Check for suspicious patterns"""
        # Simplified check for obviously fake content
        suspicious_patterns = [
            r'click here to win',
            r'you have won',
            r'congratulations.*prize',
            r'urgent.*action required'
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in suspicious_patterns)
    
    def _is_credible_source(self, source_type: str) -> bool:
        """Check if source type is generally credible"""
        credible_sources = [
            SourceType.MANUAL_ENTRY.value,
            SourceType.CHAT_MESSAGE.value,
            SourceType.EMAIL.value,
            SourceType.CALENDAR_EVENT.value,
            SourceType.PHOTO.value,
            SourceType.VOICE_MESSAGE.value
        ]
        
        return source_type in credible_sources
    
    def _score_to_quality_level(self, score: float) -> QualityLevel:
        """Convert score to quality level"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.ACCEPTABLE
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.REJECTED

# Metadata Extractors

class BaseMetadataExtractor:
    """Base class for metadata extractors"""
    
    async def initialize(self):
        """Initialize extractor"""
        pass
    
    async def extract(self, raw_input: RawMemoryInput, 
                     normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata"""
        raise NotImplementedError
    
    async def shutdown(self):
        """Shutdown extractor"""
        pass

class TemporalMetadataExtractor(BaseMetadataExtractor):
    """Extracts temporal metadata"""
    
    async def extract(self, raw_input: RawMemoryInput, 
                     normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract temporal metadata"""
        timestamp = raw_input.timestamp or datetime.now()
        
        return {
            'timestamp': timestamp.isoformat(),
            'date': timestamp.date().isoformat(),
            'time': timestamp.time().isoformat(),
            'day_of_week': timestamp.strftime('%A'),
            'month': timestamp.strftime('%B'),
            'year': timestamp.year,
            'hour': timestamp.hour,
            'is_weekend': timestamp.weekday() >= 5,
            'time_of_day': self._classify_time_of_day(timestamp.hour),
            'season': self._get_season(timestamp.month)
        }
    
    def _classify_time_of_day(self, hour: int) -> str:
        """Classify time of day"""
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'
    
    def _get_season(self, month: int) -> str:
        """Get season from month"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'

class LocationMetadataExtractor(BaseMetadataExtractor):
    """Extracts location metadata"""
    
    async def extract(self, raw_input: RawMemoryInput, 
                     normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract location metadata"""
        location_data = {}
        
        # Extract from source metadata
        source_location = raw_input.source_metadata.get('location')
        if source_location:
            location_data.update(source_location)
        
        # Extract from content
        content_location = await self._extract_location_from_content(
            normalized_content.get('content', '')
        )
        if content_location:
            location_data.update(content_location)
        
        return location_data
    
    async def _extract_location_from_content(self, content: str) -> Dict[str, Any]:
        """Extract location mentions from content"""
        # Simplified location extraction
        # In practice, would use NER (Named Entity Recognition)
        location_patterns = [
            r'at ([A-Z][a-z]+ [A-Z][a-z]+)',  # "at New York"
            r'in ([A-Z][a-z]+)',              # "in Paris"
            r'from ([A-Z][a-z]+ [A-Z][a-z]+)' # "from Los Angeles"
        ]
        
        locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            locations.extend(matches)
        
        if locations:
            return {
                'mentioned_locations': locations,
                'primary_location': locations[0] if locations else None
            }
        
        return {}

class ParticipantExtractor(BaseMetadataExtractor):
    """Extracts participant information"""
    
    async def extract(self, raw_input: RawMemoryInput, 
                     normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract participant information"""
        participants = []
        
        # Extract from normalized content
        if 'participants' in normalized_content:
            participants.extend(normalized_content['participants'])
        
        # Extract from content text
        content_participants = await self._extract_participants_from_content(
            normalized_content.get('content', '')
        )
        participants.extend(content_participants)
        
        # Remove duplicates and clean
        unique_participants = list(set(participants))
        cleaned_participants = [p.strip() for p in unique_participants if p.strip()]
        
        return {
            'participants': cleaned_participants,
            'participant_count': len(cleaned_participants),
            'has_multiple_participants': len(cleaned_participants) > 1
        }
    
    async def _extract_participants_from_content(self, content: str) -> List[str]:
        """Extract participant names from content"""
        # Simplified name extraction
        # In practice, would use more sophisticated NER
        name_patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # "John Smith"
            r'\b([A-Z][a-z]+)\s+said',          # "John said"
            r'with ([A-Z][a-z]+)',              # "with Mary"
        ]
        
        participants = []
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            participants.extend(matches)
        
        return participants

class ContextExtractor(BaseMetadataExtractor):
    """Extracts contextual information"""
    
    async def extract(self, raw_input: RawMemoryInput, 
                     normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context information"""
        return {
            'source_context': await self._extract_source_context(raw_input),
            'content_context': await self._extract_content_context(normalized_content),
            'situational_context': await self._extract_situational_context(raw_input, normalized_content)
        }
    
    async def extract_context(self, normalized_content: Dict[str, Any], 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract comprehensive context"""
        context = {}
        
        # Combine all context information
        if 'source_context' in metadata.get('context_extractor', {}):
            context.update(metadata['context_extractor']['source_context'])
        
        if 'content_context' in metadata.get('context_extractor', {}):
            context.update(metadata['context_extractor']['content_context'])
        
        if 'situational_context' in metadata.get('context_extractor', {}):
            context.update(metadata['context_extractor']['situational_context'])
        
        return context
    
    async def _extract_source_context(self, raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Extract context from source"""
        return {
            'source_type': raw_input.source_type.value,
            'source_metadata': raw_input.source_metadata,
            'platform': raw_input.source_metadata.get('platform', 'unknown')
        }
    
    async def _extract_content_context(self, normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context from content"""
        content = normalized_content.get('content', '')
        
        return {
            'content_length': len(content),
            'word_count': len(content.split()),
            'content_type': normalized_content.get('content_type', ContentType.TEXT).value,
            'has_questions': '?' in content,
            'has_exclamations': '!' in content,
            'tone': self._analyze_tone(content)
        }
    
    async def _extract_situational_context(self, raw_input: RawMemoryInput, 
                                          normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract situational context"""
        # This would analyze the situation based on various factors
        return {
            'urgency': self._assess_urgency(normalized_content.get('content', '')),
            'formality': self._assess_formality(normalized_content.get('content', '')),
            'emotional_intensity': self._assess_emotional_intensity(normalized_content.get('content', ''))
        }
    
    def _analyze_tone(self, content: str) -> str:
        """Analyze tone of content"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['excited', 'amazing', 'wonderful', '!']):
            return 'excited'
        elif any(word in content_lower for word in ['sad', 'disappointed', 'upset']):
            return 'sad'
        elif any(word in content_lower for word in ['angry', 'frustrated', 'annoyed']):
            return 'angry'
        elif '?' in content:
            return 'questioning'
        else:
            return 'neutral'
    
    def _assess_urgency(self, content: str) -> str:
        """Assess urgency level"""
        urgent_words = ['urgent', 'asap', 'immediately', 'emergency', 'now']
        content_lower = content.lower()
        
        if any(word in content_lower for word in urgent_words):
            return 'high'
        elif '!' in content:
            return 'medium'
        else:
            return 'low'
    
    def _assess_formality(self, content: str) -> str:
        """Assess formality level"""
        formal_indicators = ['dear', 'sincerely', 'regards', 'please', 'thank you']
        informal_indicators = ['hey', 'lol', 'omg', 'btw', 'thx']
        
        content_lower = content.lower()
        
        formal_count = sum(1 for word in formal_indicators if word in content_lower)
        informal_count = sum(1 for word in informal_indicators if word in content_lower)
        
        if formal_count > informal_count:
            return 'formal'
        elif informal_count > formal_count:
            return 'informal'
        else:
            return 'neutral'
    
    def _assess_emotional_intensity(self, content: str) -> str:
        """Assess emotional intensity"""
        high_intensity_indicators = ['!!!', 'AMAZING', 'TERRIBLE', 'LOVE', 'HATE']
        
        content_upper = content.upper()
        
        if any(indicator in content_upper for indicator in high_intensity_indicators):
            return 'high'
        elif '!' in content or any(c.isupper() for c in content if c.isalpha()):
            return 'medium'
        else:
            return 'low'

class SentimentExtractor(BaseMetadataExtractor):
    """Extracts sentiment information"""
    
    async def extract(self, raw_input: RawMemoryInput, 
                     normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sentiment"""
        content = normalized_content.get('content', '')
        
        # Basic sentiment analysis
        sentiment = await self._analyze_sentiment(content)
        
        return {
            'sentiment': sentiment,
            'emotional_words': self._extract_emotional_words(content),
            'sentiment_confidence': sentiment.get('confidence', 0.5)
        }
    
    async def _analyze_sentiment(self, content: str) -> Dict[str, float]:
        """Analyze sentiment of content"""
        try:
            from textblob import TextBlob
            
            blob = TextBlob(content)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1
            
            # Convert to positive/negative/neutral
            if polarity > 0.1:
                sentiment_label = 'positive'
            elif polarity < -0.1:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
            
            return {
                'label': sentiment_label,
                'polarity': polarity,
                'subjectivity': subjectivity,
                'confidence': abs(polarity)
            }
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return {
                'label': 'neutral',
                'polarity': 0.0,
                'subjectivity': 0.0,
                'confidence': 0.0
            }
    
    def _extract_emotional_words(self, content: str) -> List[str]:
        """Extract emotional words from content"""
        emotional_words = [
            'happy', 'sad', 'angry', 'excited', 'frustrated', 'love', 'hate',
            'joy', 'fear', 'surprise', 'disgust', 'trust', 'anticipation',
            'amazing', 'terrible', 'wonderful', 'awful', 'fantastic', 'horrible'
        ]
        
        content_lower = content.lower()
        found_words = [word for word in emotional_words if word in content_lower]
        
        return found_words

class TagExtractor(BaseMetadataExtractor):
    """Extracts tags and categories"""
    
    async def extract(self, raw_input: RawMemoryInput, 
                     normalized_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tags"""
        content = normalized_content.get('content', '')
        
        # Extract various types of tags
        topic_tags = await self._extract_topic_tags(content)
        activity_tags = await self._extract_activity_tags(content)
        people_tags = await self._extract_people_tags(content)
        location_tags = await self._extract_location_tags(content)
        
        all_tags = topic_tags + activity_tags + people_tags + location_tags
        
        return {
            'all_tags': list(set(all_tags)),  # Remove duplicates
            'topic_tags': topic_tags,
            'activity_tags': activity_tags,
            'people_tags': people_tags,
            'location_tags': location_tags,
            'tag_count': len(set(all_tags))
        }
    
    async def _extract_topic_tags(self, content: str) -> List[str]:
        """Extract topic-based tags"""
        topic_keywords = {
            'work': ['work', 'job', 'office', 'meeting', 'project', 'boss', 'colleague'],
            'family': ['family', 'mom', 'dad', 'sister', 'brother', 'parent', 'child'],
            'health': ['doctor', 'hospital', 'medicine', 'sick', 'healthy', 'exercise'],
            'travel': ['travel', 'trip', 'vacation', 'flight', 'hotel', 'visit'],
            'food': ['restaurant', 'dinner', 'lunch', 'cooking', 'recipe', 'eat'],
            'entertainment': ['movie', 'music', 'book', 'game', 'show', 'concert'],
            'shopping': ['buy', 'shop', 'store', 'purchase', 'price', 'sale'],
            'education': ['school', 'study', 'learn', 'class', 'teacher', 'student']
        }
        
        content_lower = content.lower()
        tags = []
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(topic)
        
        return tags
    
    async def _extract_activity_tags(self, content: str) -> List[str]:
        """Extract activity-based tags"""
        activity_keywords = {
            'meeting': ['meeting', 'conference', 'call', 'discussion'],
            'celebration': ['birthday', 'anniversary', 'party', 'celebration'],
            'exercise': ['gym', 'run', 'workout', 'exercise', 'sport'],
            'cooking': ['cook', 'bake', 'recipe', 'kitchen'],
            'reading': ['read', 'book', 'article', 'news'],
            'watching': ['watch', 'movie', 'tv', 'show', 'video']
        }
        
        content_lower = content.lower()
        tags = []
        
        for activity, keywords in activity_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(activity)
        
        return tags
    
    async def _extract_people_tags(self, content: str) -> List[str]:
        """Extract people-related tags"""
        # This would extract and categorize people mentioned
        # For now, return simple categories
        people_indicators = {
            'family_time': ['family', 'mom', 'dad', 'sister', 'brother'],
            'friends': ['friend', 'buddy', 'pal'],
            'colleagues': ['colleague', 'coworker', 'boss', 'team'],
            'social': ['party', 'gathering', 'group', 'crowd']
        }
        
        content_lower = content.lower()
        tags = []
        
        for category, indicators in people_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                tags.append(category)
        
        return tags
    
    async def _extract_location_tags(self, content: str) -> List[str]:
        """Extract location-based tags"""
        location_indicators = {
            'home': ['home', 'house', 'apartment'],
            'work': ['office', 'workplace', 'work'],
            'restaurant': ['restaurant', 'cafe', 'diner'],
            'outdoor': ['park', 'beach', 'mountain', 'outdoor'],
            'travel': ['airport', 'hotel', 'vacation', 'trip']
        }
        
        content_lower = content.lower()
        tags = []
        
        for category, indicators in location_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                tags.append(category)
        
        return tags

# Content Processing Utilities

class ContentNormalizer:
    """Normalizes content to standard format"""
    
    async def normalize(self, processed_content: Dict[str, Any], 
                      raw_input: RawMemoryInput) -> Dict[str, Any]:
        """Normalize processed content"""
        normalized = processed_content.copy()
        
        # Normalize text content
        if 'content' in normalized:
            normalized['content'] = self._normalize_text(normalized['content'])
        
        # Ensure required fields
        normalized.setdefault('content_type', ContentType.TEXT)
        normalized.setdefault('participants', [])
        normalized.setdefault('language', 'unknown')
        
        # Detect language if not provided
        if normalized['language'] == 'unknown' and normalized.get('content'):
            normalized['language'] = await self._detect_language(normalized['content'])
        
        return normalized
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text content"""
        if not isinstance(text, str):
            text = str(text)
        
        # Basic text cleaning
        text = text.strip()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text
    
    async def _detect_language(self, text: str) -> str:
        """Detect language of text"""
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            return 'en'  # Default to English

class ContentEnricher:
    """Enriches content with additional processed information"""
    
    async def enrich(self, normalized_content: Dict[str, Any], 
                    context: Dict[str, Any], 
                    metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich content with additional information"""
        enriched = normalized_content.copy()
        
        # Add language detection
        if 'language' not in enriched or enriched['language'] == 'unknown':
            enriched['language'] = await self._detect_language(enriched.get('content', ''))
        
        # Add sentiment analysis
        enriched['sentiment'] = await self._analyze_sentiment(enriched.get('content', ''))
        
        # Add tags from metadata
        if 'tag_extractor' in metadata:
            enriched['tags'] = metadata['tag_extractor'].get('all_tags', [])
        else:
            enriched['tags'] = []
        
        # Add participants from metadata
        if 'participant_extractor' in metadata:
            enriched['participants'] = metadata['participant_extractor'].get('participants', [])
        
        # Add location from metadata
        if 'location_extractor' in metadata:
            location_data = metadata['location_extractor']
            if location_data:
                enriched['location'] = location_data
        
        # Ensure content type is set
        if 'content_type' not in enriched:
            enriched['content_type'] = ContentType.TEXT
        
        return enriched
    
    async def _detect_language(self, text: str) -> str:
        """Detect language of text"""
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            return 'en'
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment"""
        try:
            from textblob import TextBlob
            
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                label = 'positive'
            elif polarity < -0.1:
                label = 'negative'
            else:
                label = 'neutral'
            
            return {
                'label': label,
                'score': polarity,
                'confidence': abs(polarity)
            }
        except Exception:
            return {
                'label': 'neutral',
                'score': 0.0,
                'confidence': 0.0
            }

# Example usage and testing
if __name__ == "__main__":
    async def test_memory_harvester():
        """Test the Memory Harvester Agent"""
        
        # Initialize agent
        agent = MemoryHarvesterAgent()
        await agent.initialize()
        
        # Test chat message processing
        chat_input = RawMemoryInput(
            content="Had a great lunch with Sarah today at the new Italian restaurant downtown!",
            source_type=SourceType.CHAT_MESSAGE,
            source_metadata={
                'platform': 'whatsapp',
                'sender': 'user',
                'recipients': ['sarah']
            },
            user_id='user123',
            timestamp=datetime.now()
        )
        
        processed_memory = await agent.process_memory(chat_input)
        print(f"Processed memory: {processed_memory.id}")
        print(f"Quality score: {processed_memory.quality_score}")
        print(f"Tags: {processed_memory.tags}")
        
        # Test email processing
        email_input = RawMemoryInput(
            content={
                'subject': 'Family Reunion Planning',
                'body': 'Hi everyone, I wanted to start planning our annual family reunion. How does July work for everyone?',
                'from': 'mom@email.com',
                'to': ['family@email.com']
            },
            source_type=SourceType.EMAIL,
            source_metadata={'platform': 'gmail'},
            user_id='user123',
            timestamp=datetime.now()
        )
        
        processed_email = await agent.process_memory(email_input)
        print(f"Processed email: {processed_email.id}")
        print(f"Participants: {processed_email.participants}")
        
        # Get processing statistics
        stats = await agent.get_processing_stats()
        print(f"Processing stats: {stats}")
        
        # Shutdown
        await agent.shutdown()
    
    # Run test
    import asyncio
    asyncio.run(test_memory_harvester())

