#!/usr/bin/env python3
"""
Circleback-style Orchestrator for MD Agent
Implements multi-stage processing pipeline with parallel execution
"""

import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
import time
from dataclasses import dataclass, field

# Import schemas
from .schemas import (
    Utterance, Memory, Entity, ActionItem, Relation,
    ConversationContext, ProcessingResult, MemoryCategory,
    EntityType, RelationType, ActionPriority, ActionStatus
)

# Import processors (to be created)
# from .entity_extractor import EntityExtractor
# from .action_extractor import ActionExtractor
# from .context_enhancer import ContextEnhancer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CirclebackOrchestrator:
    """
    Multi-stage processing orchestrator inspired by Circleback
    Coordinates parallel processing of conversation data
    """
    
    def __init__(
        self,
        base_dir: str = 'data/memories',
        enable_parallel: bool = True,
        confidence_threshold: float = 0.6
    ):
        """
        Initialize the orchestrator
        
        Args:
            base_dir: Base directory for memory storage
            enable_parallel: Enable parallel processing
            confidence_threshold: Minimum confidence for acceptance
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.enable_parallel = enable_parallel
        self.confidence_threshold = confidence_threshold
        
        # Initialize processors (will be created in next steps)
        # self.entity_extractor = EntityExtractor()
        # self.action_extractor = ActionExtractor()
        # self.context_enhancer = ContextEnhancer()
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'stage_timings': {},
            'errors': [],
            'warnings': []
        }
        
        logger.info(f"🚀 Circleback Orchestrator initialized")
    
    async def process_conversation(
        self,
        input_data: Dict[str, Any],
        contact_id: str,
        context: Optional[ConversationContext] = None
    ) -> ProcessingResult:
        """
        Process a conversation through all stages
        
        Args:
            input_data: Raw conversation data
            contact_id: Contact identifier
            context: Optional conversation context
            
        Returns:
            Complete processing result
        """
        start_time = time.time()
        result = ProcessingResult()
        
        try:
            # Stage 1: Audio/Text Ingestion
            logger.info("📝 Stage 1: Ingesting conversation data")
            utterances = await self._stage1_ingestion(input_data, contact_id)
            result.utterances = utterances
            
            # Stage 2: Speaker Diarization
            logger.info("🎭 Stage 2: Speaker diarization")
            utterances = await self._stage2_diarization(utterances, contact_id)
            result.utterances = utterances
            
            if self.enable_parallel:
                # Parallel execution of stages 3 and 4
                logger.info("⚡ Running stages 3 & 4 in parallel")
                
                stage3_task = asyncio.create_task(
                    self._stage3_extraction(utterances, contact_id)
                )
                stage4_task = asyncio.create_task(
                    self._stage4_enhancement(utterances, context, contact_id)
                )
                
                extraction_result, enhanced_context = await asyncio.gather(
                    stage3_task, stage4_task
                )
                
                entities, relations, action_items = extraction_result
                result.entities = entities
                result.relations = relations
                result.action_items = action_items
                result.context = enhanced_context
            else:
                # Sequential execution
                logger.info("🔄 Running stages 3 & 4 sequentially")
                
                # Stage 3: Entity & Action Extraction
                entities, relations, action_items = await self._stage3_extraction(
                    utterances, contact_id
                )
                result.entities = entities
                result.relations = relations
                result.action_items = action_items
                
                # Stage 4: Context Enhancement
                enhanced_context = await self._stage4_enhancement(
                    utterances, context, contact_id
                )
                result.context = enhanced_context
            
            # Stage 5: Categorization & Storage
            logger.info("💾 Stage 5: Categorization and storage")
            memories = await self._stage5_categorization(
                utterances, entities, action_items, relations, 
                enhanced_context, contact_id
            )
            result.memories = memories
            
            # Calculate processing time
            result.processing_time = time.time() - start_time
            
            # Add metadata
            result.model_versions = {
                'orchestrator': '1.0.0',
                'entity_extractor': '1.0.0',
                'action_extractor': '1.0.0',
                'context_enhancer': '1.0.0'
            }
            
            # Calculate confidence scores
            result.confidence_scores = self._calculate_confidence(result)
            
            # Update statistics
            self.stats['total_processed'] += 1
            
            logger.info(f"✅ Processing complete in {result.processing_time:.2f}s")
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            self.stats['errors'].append(error_msg)
        
        return result
    
    async def _stage1_ingestion(
        self,
        input_data: Dict[str, Any],
        contact_id: str
    ) -> List[Utterance]:
        """
        Stage 1: Ingest and parse conversation data
        
        Args:
            input_data: Raw input data
            contact_id: Contact identifier
            
        Returns:
            List of utterances
        """
        stage_start = time.time()
        utterances = []
        
        try:
            # Handle different input formats
            if 'messages' in input_data:
                # WhatsApp-style messages
                for msg in input_data['messages']:
                    utterance = Utterance(
                        speaker_id=msg.get('sender', 'unknown'),
                        text=msg.get('text', ''),
                        timestamp=self._parse_timestamp(msg.get('timestamp')),
                        metadata={
                            'source': 'whatsapp',
                            'message_id': msg.get('id'),
                            'reply_to': msg.get('reply_to')
                        }
                    )
                    utterances.append(utterance)
            
            elif 'transcript' in input_data:
                # Transcript format
                lines = input_data['transcript'].split('\n')
                for line in lines:
                    if line.strip():
                        # Parse transcript line
                        utterance = self._parse_transcript_line(line)
                        if utterance:
                            utterances.append(utterance)
            
            elif 'utterances' in input_data:
                # Pre-parsed utterances
                for utt_data in input_data['utterances']:
                    utterance = Utterance(
                        speaker_id=utt_data.get('speaker_id', 'unknown'),
                        text=utt_data.get('text', ''),
                        timestamp=self._parse_timestamp(utt_data.get('timestamp')),
                        confidence=utt_data.get('confidence', 1.0),
                        metadata=utt_data.get('metadata', {})
                    )
                    utterances.append(utterance)
            
            else:
                # Raw text input
                text = str(input_data.get('text', input_data))
                utterance = Utterance(
                    speaker_id=contact_id,
                    text=text,
                    timestamp=datetime.now(),
                    metadata={'source': 'raw_text'}
                )
                utterances.append(utterance)
            
            logger.info(f"Ingested {len(utterances)} utterances")
            
        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            self.stats['errors'].append(f"Stage 1 error: {e}")
        
        self.stats['stage_timings']['stage1'] = time.time() - stage_start
        return utterances
    
    async def _stage2_diarization(
        self,
        utterances: List[Utterance],
        contact_id: str
    ) -> List[Utterance]:
        """
        Stage 2: Speaker diarization and identification
        
        Args:
            utterances: List of utterances
            contact_id: Contact identifier
            
        Returns:
            Utterances with speaker information
        """
        stage_start = time.time()
        
        try:
            # Simple heuristic-based diarization
            # In production, would use voice biometrics or ML models
            
            speakers = {}
            current_speaker = None
            
            for utterance in utterances:
                # Identify speaker based on patterns
                if utterance.speaker_id == 'unknown':
                    # Try to identify from context
                    if 'I' in utterance.text or 'my' in utterance.text.lower():
                        utterance.speaker_id = 'self'
                    elif 'you' in utterance.text.lower():
                        utterance.speaker_id = contact_id
                    else:
                        # Assume alternating speakers
                        if current_speaker == 'self':
                            utterance.speaker_id = contact_id
                        else:
                            utterance.speaker_id = 'self'
                
                current_speaker = utterance.speaker_id
                
                # Track speakers
                if utterance.speaker_id not in speakers:
                    speakers[utterance.speaker_id] = {
                        'count': 0,
                        'total_words': 0
                    }
                
                speakers[utterance.speaker_id]['count'] += 1
                speakers[utterance.speaker_id]['total_words'] += len(utterance.text.split())
            
            logger.info(f"Identified {len(speakers)} speakers")
            
        except Exception as e:
            logger.error(f"Diarization error: {e}")
            self.stats['errors'].append(f"Stage 2 error: {e}")
        
        self.stats['stage_timings']['stage2'] = time.time() - stage_start
        return utterances
    
    async def _stage3_extraction(
        self,
        utterances: List[Utterance],
        contact_id: str
    ) -> Tuple[List[Entity], List[Relation], List[ActionItem]]:
        """
        Stage 3: Extract entities, relations, and action items
        
        Args:
            utterances: List of utterances
            contact_id: Contact identifier
            
        Returns:
            Tuple of entities, relations, and action items
        """
        stage_start = time.time()
        entities = []
        relations = []
        action_items = []
        
        try:
            # Placeholder for entity extraction
            # Will be replaced with EntityExtractor
            for utterance in utterances:
                # Simple pattern-based extraction
                text = utterance.text.lower()
                
                # Extract dates
                import re
                date_patterns = [
                    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                    r'\b(tomorrow|today|yesterday|next week|next month)\b'
                ]
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        entity = Entity(
                            type=EntityType.DATE,
                            value=match,
                            canonical_name=match,
                            confidence=0.8,
                            utterance_ids=[utterance.id],
                            context=utterance.text[:100]
                        )
                        entities.append(entity)
                
                # Extract action items
                action_patterns = [
                    r'\b(need to|should|must|will|going to|have to)\s+([^.!?]+)',
                    r'\b(todo|task|action):\s*([^.!?]+)'
                ]
                
                for pattern in action_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        action_text = match[1] if isinstance(match, tuple) else match
                        action = ActionItem(
                            title=action_text[:100],
                            description=utterance.text,
                            priority=ActionPriority.MEDIUM,
                            status=ActionStatus.PENDING,
                            utterance_ids=[utterance.id],
                            created_at=utterance.timestamp
                        )
                        action_items.append(action)
            
            logger.info(f"Extracted {len(entities)} entities, {len(action_items)} actions")
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            self.stats['errors'].append(f"Stage 3 error: {e}")
        
        self.stats['stage_timings']['stage3'] = time.time() - stage_start
        return entities, relations, action_items
    
    async def _stage4_enhancement(
        self,
        utterances: List[Utterance],
        context: Optional[ConversationContext],
        contact_id: str
    ) -> ConversationContext:
        """
        Stage 4: Enhance with context
        
        Args:
            utterances: List of utterances
            context: Optional existing context
            contact_id: Contact identifier
            
        Returns:
            Enhanced conversation context
        """
        stage_start = time.time()
        
        if not context:
            context = ConversationContext()
        
        try:
            # Enhance context with conversation metadata
            if utterances:
                context.actual_time = utterances[0].timestamp
                context.duration = int(
                    (utterances[-1].timestamp - utterances[0].timestamp).total_seconds() / 60
                )
            
            # Identify participants
            speakers = set(utt.speaker_id for utt in utterances)
            context.participants = [
                {'id': speaker, 'name': speaker, 'utterance_count': 
                 len([u for u in utterances if u.speaker_id == speaker])}
                for speaker in speakers
            ]
            
            # Detect meeting type from content
            full_text = ' '.join(utt.text for utt in utterances).lower()
            if 'standup' in full_text or 'daily' in full_text:
                context.meeting_type = 'standup'
            elif '1:1' in full_text or 'one on one' in full_text:
                context.meeting_type = '1:1'
            elif 'review' in full_text:
                context.meeting_type = 'review'
            else:
                context.meeting_type = 'general'
            
            logger.info(f"Enhanced context: {context.meeting_type} meeting")
            
        except Exception as e:
            logger.error(f"Enhancement error: {e}")
            self.stats['errors'].append(f"Stage 4 error: {e}")
        
        self.stats['stage_timings']['stage4'] = time.time() - stage_start
        return context
    
    async def _stage5_categorization(
        self,
        utterances: List[Utterance],
        entities: List[Entity],
        action_items: List[ActionItem],
        relations: List[Relation],
        context: ConversationContext,
        contact_id: str
    ) -> List[Memory]:
        """
        Stage 5: Categorize and create memories
        
        Args:
            utterances: List of utterances
            entities: Extracted entities
            action_items: Extracted action items
            relations: Entity relations
            context: Conversation context
            contact_id: Contact identifier
            
        Returns:
            List of categorized memories
        """
        stage_start = time.time()
        memories = []
        
        try:
            # Group utterances into logical chunks
            chunks = self._chunk_utterances(utterances)
            
            for chunk in chunks:
                # Determine category based on content
                category = self._determine_category(chunk, entities, action_items)
                
                # Create memory
                memory = Memory(
                    content='\n'.join(utt.text for utt in chunk),
                    summary=self._generate_summary(chunk),
                    category=category,
                    entities=[e for e in entities if any(
                        uid in e.utterance_ids for uid in [u.id for u in chunk]
                    )],
                    action_items=[a for a in action_items if any(
                        uid in a.utterance_ids for uid in [u.id for u in chunk]
                    )],
                    relations=relations,
                    timestamp=datetime.now(),
                    source_timestamp=chunk[0].timestamp if chunk else None,
                    confidence=self._calculate_chunk_confidence(chunk),
                    importance=self._calculate_importance(chunk, entities, action_items),
                    utterance_ids=[u.id for u in chunk],
                    context=context.to_dict() if context else None,
                    provenance={
                        'source': 'conversation',
                        'contact_id': contact_id,
                        'processing_version': '1.0.0'
                    }
                )
                
                # Extract tags and keywords
                memory.tags = self._extract_tags(memory.content)
                memory.keywords = self._extract_keywords(memory.content)
                
                memories.append(memory)
            
            # Store memories
            await self._store_memories(memories, contact_id)
            
            logger.info(f"Created {len(memories)} memories")
            
        except Exception as e:
            logger.error(f"Categorization error: {e}")
            self.stats['errors'].append(f"Stage 5 error: {e}")
        
        self.stats['stage_timings']['stage5'] = time.time() - stage_start
        return memories
    
    def _chunk_utterances(
        self,
        utterances: List[Utterance],
        max_chunk_size: int = 5
    ) -> List[List[Utterance]]:
        """
        Group utterances into logical chunks
        """
        chunks = []
        current_chunk = []
        
        for utterance in utterances:
            current_chunk.append(utterance)
            
            # Start new chunk on topic change or size limit
            if len(current_chunk) >= max_chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _determine_category(self, chunk, entities, action_items) -> MemoryCategory:
        """Determine memory category based on content"""
        text = ' '.join(utt.text.lower() for utt in chunk)
        
        # Priority-based categorization
        if any(a for a in action_items if any(
            uid in a.utterance_ids for uid in [u.id for u in chunk]
        )):
            return MemoryCategory.ACTION_ITEMS
        
        if 'decision' in text or 'decided' in text or 'agreed' in text:
            return MemoryCategory.DECISIONS
        
        if any(e.type == EntityType.DATE for e in entities):
            return MemoryCategory.IMPORTANT_DATES
        
        if 'personal' in text or 'private' in text:
            return MemoryCategory.PERSONAL
        
        if 'work' in text or 'project' in text or 'business' in text:
            return MemoryCategory.PROFESSIONAL
        
        return MemoryCategory.NOTES
    
    def _generate_summary(self, chunk: List[Utterance]) -> str:
        """Generate summary of utterance chunk"""
        if not chunk:
            return ""
        
        # Simple summary: first 100 chars
        full_text = ' '.join(utt.text for utt in chunk)
        return full_text[:100] + ('...' if len(full_text) > 100 else '')
    
    def _calculate_chunk_confidence(self, chunk: List[Utterance]) -> float:
        """Calculate average confidence for chunk"""
        if not chunk:
            return 0.0
        
        confidences = [utt.confidence for utt in chunk]
        return sum(confidences) / len(confidences)
    
    def _calculate_importance(
        self,
        chunk: List[Utterance],
        entities: List[Entity],
        action_items: List[ActionItem]
    ) -> int:
        """Calculate importance score (1-10)"""
        score = 5  # Base score
        
        # Increase for action items
        relevant_actions = [a for a in action_items if any(
            uid in a.utterance_ids for uid in [u.id for u in chunk]
        )]
        if relevant_actions:
            score += min(len(relevant_actions), 3)
        
        # Increase for high-priority actions
        if any(a.priority in [ActionPriority.HIGH, ActionPriority.CRITICAL] 
               for a in relevant_actions):
            score += 2
        
        # Increase for multiple entities
        relevant_entities = [e for e in entities if any(
            uid in e.utterance_ids for uid in [u.id for u in chunk]
        )]
        if len(relevant_entities) > 3:
            score += 1
        
        return min(score, 10)
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract tags from text"""
        tags = []
        
        # Extract hashtags
        import re
        hashtags = re.findall(r'#(\w+)', text)
        tags.extend(hashtags)
        
        # Add topic tags
        topics = ['meeting', 'decision', 'action', 'followup', 'important']
        for topic in topics:
            if topic in text.lower():
                tags.append(topic)
        
        return list(set(tags))
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        # In production, would use TF-IDF or similar
        import re
        
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                    'to', 'for', 'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Count frequency
        from collections import Counter
        word_freq = Counter(keywords)
        
        # Return top keywords
        return [word for word, _ in word_freq.most_common(10)]
    
    async def _store_memories(
        self,
        memories: List[Memory],
        contact_id: str
    ) -> None:
        """
        Store memories to files
        """
        contact_dir = self.base_dir / contact_id
        contact_dir.mkdir(parents=True, exist_ok=True)
        
        # Group memories by category
        from collections import defaultdict
        by_category = defaultdict(list)
        
        for memory in memories:
            by_category[memory.category].append(memory)
        
        # Store in category files
        for category, cat_memories in by_category.items():
            file_path = contact_dir / f"{category.value}.md"
            
            # Read existing content
            existing_content = ""
            if file_path.exists():
                existing_content = file_path.read_text(encoding='utf-8')
            
            # Append new memories
            with open(file_path, 'a', encoding='utf-8') as f:
                if not existing_content:
                    f.write(f"# {category.value.replace('_', ' ').title()} Memories\n\n")
                
                for memory in cat_memories:
                    f.write(memory.to_markdown())
            
            # Also store JSON metadata
            json_path = contact_dir / f"{category.value}_metadata.json"
            metadata = []
            
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            metadata.extend([m.to_dict() for m in cat_memories])
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
    
    def _calculate_confidence(self, result: ProcessingResult) -> Dict[str, float]:
        """Calculate overall confidence scores"""
        scores = {}
        
        # Utterance confidence
        if result.utterances:
            scores['utterances'] = sum(u.confidence for u in result.utterances) / len(result.utterances)
        
        # Entity confidence
        if result.entities:
            scores['entities'] = sum(e.confidence for e in result.entities) / len(result.entities)
        
        # Memory confidence
        if result.memories:
            scores['memories'] = sum(m.confidence for m in result.memories) / len(result.memories)
        
        # Overall confidence
        if scores:
            scores['overall'] = sum(scores.values()) / len(scores)
        else:
            scores['overall'] = 0.0
        
        return scores
    
    def _parse_timestamp(self, timestamp_str: Any) -> datetime:
        """Parse timestamp from various formats"""
        if isinstance(timestamp_str, datetime):
            return timestamp_str
        
        if timestamp_str is None:
            return datetime.now()
        
        # Try common formats
        from dateutil import parser
        try:
            return parser.parse(str(timestamp_str))
        except:
            return datetime.now()
    
    def _parse_transcript_line(self, line: str) -> Optional[Utterance]:
        """Parse a line from transcript format"""
        import re
        
        # Pattern: [timestamp] speaker: text
        pattern = r'\[(.*?)\]\s*(.*?):\s*(.*)'
        match = re.match(pattern, line)
        
        if match:
            timestamp_str, speaker, text = match.groups()
            return Utterance(
                speaker_id=speaker.strip(),
                text=text.strip(),
                timestamp=self._parse_timestamp(timestamp_str),
                metadata={'source': 'transcript'}
            )
        
        return None
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'total_processed': self.stats['total_processed'],
            'stage_timings': self.stats['stage_timings'],
            'error_count': len(self.stats['errors']),
            'warning_count': len(self.stats['warnings']),
            'recent_errors': self.stats['errors'][-5:] if self.stats['errors'] else []
        }