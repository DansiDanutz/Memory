#!/usr/bin/env python3
"""
Upgraded MD Agent - Circleback-style Memory Processing System
Integrates all components with ensemble model orchestration
"""

import os
import sys
import json
import logging
import asyncio
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
import anthropic

# Import all our new components
from .schemas import (
    Memory, MemoryCategory, Utterance, Entity, EntityType, ActionItem, 
    ActionPriority, Relation, ConversationContext, ProcessingResult
)
from .circleback_orchestrator import CirclebackOrchestrator
from .entity_extractor import EntityExtractor
from .action_extractor import ActionExtractor
from .context_enhancer import ContextEnhancer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MDAgentUpgraded:
    """
    Advanced Memory Document Agent with Circleback-style architecture
    Implements ensemble model orchestration with multiple processing stages
    """
    
    def __init__(
        self,
        base_dir: str = 'data/memories',
        enable_ai: bool = True,
        enable_parallel: bool = True,
        confidence_threshold: float = 0.6
    ):
        """
        Initialize the upgraded MD Agent
        
        Args:
            base_dir: Base directory for memory storage
            enable_ai: Enable AI models (GPT-4/Claude)
            enable_parallel: Enable parallel processing
            confidence_threshold: Minimum confidence for acceptance
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.enable_ai = enable_ai
        self.confidence_threshold = confidence_threshold
        
        # Initialize primary AI clients (ensemble models)
        self.openai_client = None
        self.anthropic_client = None
        
        if enable_ai:
            # Initialize OpenAI (primary)
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("✅ OpenAI GPT-4 initialized (primary model)")
            else:
                logger.warning("OpenAI API key not found")
            
            # Initialize Anthropic (secondary/fallback)
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("✅ Anthropic Claude initialized (fallback model)")
            else:
                logger.warning("Anthropic API key not found")
        
        # Initialize processing components
        self.orchestrator = CirclebackOrchestrator(
            base_dir=base_dir,
            enable_parallel=enable_parallel,
            confidence_threshold=confidence_threshold
        )
        
        self.entity_extractor = EntityExtractor(enable_spacy=True)
        self.action_extractor = ActionExtractor()
        self.context_enhancer = ContextEnhancer(base_dir=base_dir)
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'memories_created': 0,
            'entities_extracted': 0,
            'actions_extracted': 0,
            'avg_confidence': 0.0,
            'processing_times': [],
            'model_usage': {'openai': 0, 'anthropic': 0, 'local': 0},
            'last_run': None
        }
        
        logger.info("🚀 MD Agent Upgraded initialized with Circleback architecture")
    
    async def process_conversation(
        self,
        input_data: Any,
        contact_id: str,
        use_orchestrator: bool = True
    ) -> ProcessingResult:
        """
        Process a conversation using ensemble model orchestration
        
        Args:
            input_data: Raw conversation data (text, messages, or transcript)
            contact_id: Contact identifier
            use_orchestrator: Use full orchestrator pipeline
            
        Returns:
            Complete processing result
        """
        start_time = time.time()
        
        # Convert input to standard format
        formatted_input = await self._format_input(input_data)
        
        if use_orchestrator:
            # Use full Circleback orchestrator pipeline
            result = await self.orchestrator.process_conversation(
                formatted_input,
                contact_id
            )
        else:
            # Direct processing (for simple cases)
            result = await self._direct_process(formatted_input, contact_id)
        
        # Apply ensemble enhancement
        result = await self._ensemble_enhance(result, contact_id)
        
        # Calculate final confidence
        result = self._aggregate_confidence(result)
        
        # Update statistics
        processing_time = time.time() - start_time
        self._update_stats(result, processing_time)
        
        logger.info(f"✅ Processed conversation in {processing_time:.2f}s with {len(result.memories)} memories")
        
        return result
    
    async def _format_input(self, input_data: Any) -> Dict[str, Any]:
        """Format various input types to standard format"""
        
        if isinstance(input_data, str):
            # Plain text input
            return {'text': input_data}
        
        elif isinstance(input_data, dict):
            # Already formatted
            return input_data
        
        elif isinstance(input_data, list):
            # List of messages
            return {'messages': input_data}
        
        else:
            # Try to convert to string
            return {'text': str(input_data)}
    
    async def _direct_process(
        self,
        input_data: Dict[str, Any],
        contact_id: str
    ) -> ProcessingResult:
        """Direct processing without full orchestrator"""
        
        result = ProcessingResult()
        
        # Create utterances
        if 'text' in input_data:
            utterance = Utterance(
                speaker_id=contact_id,
                text=input_data['text'],
                timestamp=datetime.now()
            )
            result.utterances = [utterance]
        
        elif 'messages' in input_data:
            utterances = []
            for msg in input_data['messages']:
                utterance = Utterance(
                    speaker_id=msg.get('sender', contact_id),
                    text=msg.get('text', ''),
                    timestamp=datetime.fromisoformat(msg['timestamp']) if 'timestamp' in msg else datetime.now()
                )
                utterances.append(utterance)
            result.utterances = utterances
        
        # Extract entities
        entities, relations = await self.entity_extractor.extract_entities(result.utterances)
        result.entities = entities
        result.relations = relations
        
        # Extract action items
        actions = await self.action_extractor.extract_actions(result.utterances, entities)
        result.action_items = actions
        
        # Create memories
        memories = await self._create_memories(result.utterances, entities, actions, contact_id)
        result.memories = memories
        
        return result
    
    async def _ensemble_enhance(
        self,
        result: ProcessingResult,
        contact_id: str
    ) -> ProcessingResult:
        """Apply ensemble model enhancement"""
        
        if not self.enable_ai or (not self.openai_client and not self.anthropic_client):
            return result
        
        # Prepare data for AI enhancement
        conversation_text = '\n'.join(utt.text for utt in result.utterances)
        
        # Try GPT-4 first (primary model)
        enhanced_data = None
        
        if self.openai_client:
            try:
                enhanced_data = await self._enhance_with_gpt4(conversation_text, result)
                self.stats['model_usage']['openai'] += 1
            except Exception as e:
                logger.warning(f"GPT-4 enhancement failed: {e}")
        
        # Fallback to Claude if needed
        if not enhanced_data and self.anthropic_client:
            try:
                enhanced_data = await self._enhance_with_claude(conversation_text, result)
                self.stats['model_usage']['anthropic'] += 1
            except Exception as e:
                logger.warning(f"Claude enhancement failed: {e}")
        
        # Apply enhancements
        if enhanced_data:
            result = await self._apply_ai_enhancements(result, enhanced_data)
        
        # Apply context enhancement
        result.context = await self.context_enhancer.enhance_context(
            result.utterances,
            result.entities,
            result.action_items,
            contact_id,
            result.context
        )
        
        return result
    
    async def _enhance_with_gpt4(
        self,
        conversation_text: str,
        result: ProcessingResult
    ) -> Dict[str, Any]:
        """Enhance using GPT-4"""
        
        # Prepare context
        entities_summary = f"Found {len(result.entities)} entities"
        actions_summary = f"Found {len(result.action_items)} action items"
        
        prompt = f"""
        Analyze this conversation and enhance the extracted information:
        
        Conversation:
        {conversation_text}
        
        Current extraction:
        - {entities_summary}
        - {actions_summary}
        
        Please provide:
        1. Key insights and summary
        2. Additional entities that might have been missed
        3. Hidden action items or commitments
        4. Relationship mappings between entities
        5. Confidence scores for each extraction
        6. Suggested categories for memories
        
        Return as JSON with structure:
        {{
            "summary": "brief summary",
            "insights": ["key insight 1", "key insight 2"],
            "additional_entities": [
                {{"type": "PERSON", "value": "name", "confidence": 0.8}}
            ],
            "additional_actions": [
                {{"title": "action", "assignee": "person", "priority": "high"}}
            ],
            "relationships": [
                {{"source": "entity1", "target": "entity2", "type": "works_with"}}
            ],
            "memory_categories": ["category1", "category2"],
            "overall_confidence": 0.85
        }}
        """
        
        response = await asyncio.to_thread(
            self.openai_client.chat.completions.create,
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an advanced conversation analyzer. Extract insights, entities, and action items with high accuracy."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except:
            # Fallback to text analysis
            return {
                "summary": response.choices[0].message.content,
                "overall_confidence": 0.7
            }
    
    async def _enhance_with_claude(
        self,
        conversation_text: str,
        result: ProcessingResult
    ) -> Dict[str, Any]:
        """Enhance using Claude"""
        
        prompt = f"""
        Analyze this conversation for memory extraction:
        
        {conversation_text}
        
        Extract:
        1. Main topics and summary
        2. People, organizations, dates, locations
        3. Action items and commitments
        4. Important decisions made
        5. Follow-up items
        
        Return as structured JSON.
        """
        
        response = await asyncio.to_thread(
            self.anthropic_client.messages.create,
            model="claude-3-sonnet-20241022",
            max_tokens=1500,
            temperature=0.3,
            system="You are an expert conversation analyst. Extract and categorize information with high precision.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            return json.loads(response.content[0].text)
        except:
            return {
                "summary": response.content[0].text,
                "overall_confidence": 0.6
            }
    
    async def _apply_ai_enhancements(
        self,
        result: ProcessingResult,
        enhanced_data: Dict[str, Any]
    ) -> ProcessingResult:
        """Apply AI-generated enhancements to result"""
        
        # Add summary to context
        if 'summary' in enhanced_data:
            if not result.context:
                result.context = ConversationContext()
            result.context.metadata['ai_summary'] = enhanced_data['summary']
        
        # Add additional entities
        if 'additional_entities' in enhanced_data:
            for entity_data in enhanced_data['additional_entities']:
                # Safe enum lookup with fallback
                entity_type_str = entity_data.get('type', 'PERSON').upper()
                try:
                    entity_type = EntityType[entity_type_str]
                except KeyError:
                    # Fallback to PRODUCT for unknown types
                    entity_type = EntityType.PRODUCT
                
                entity = Entity(
                    type=entity_type,
                    value=entity_data['value'],
                    canonical_name=entity_data['value'],
                    confidence=entity_data.get('confidence', 0.7)
                )
                result.entities.append(entity)
        
        # Add additional actions
        if 'additional_actions' in enhanced_data:
            for action_data in enhanced_data['additional_actions']:
                # Safe priority enum lookup with fallback
                priority_str = action_data.get('priority', 'MEDIUM').upper()
                try:
                    priority = ActionPriority[priority_str]
                except KeyError:
                    # Fallback to MEDIUM for unknown priorities
                    priority = ActionPriority.MEDIUM
                
                action = ActionItem(
                    title=action_data['title'],
                    assignee=action_data.get('assignee'),
                    priority=priority,
                    metadata={'source': 'ai_enhancement'}
                )
                result.action_items.append(action)
        
        # Update confidence scores
        if 'overall_confidence' in enhanced_data:
            result.confidence_scores['ai_enhancement'] = enhanced_data['overall_confidence']
        
        return result
    
    async def _create_memories(
        self,
        utterances: List[Utterance],
        entities: List[Entity],
        actions: List[ActionItem],
        contact_id: str
    ) -> List[Memory]:
        """Create memories from processed data"""
        
        memories = []
        
        # Group utterances into logical chunks
        chunks = self._chunk_utterances(utterances)
        
        for chunk in chunks:
            # Determine category
            category = self._determine_category(chunk, entities, actions)
            
            # Create memory
            memory = Memory(
                content='\n'.join(utt.text for utt in chunk),
                summary=self._generate_summary(chunk),
                category=category,
                entities=[e for e in entities if any(
                    uid in e.utterance_ids for uid in [u.id for u in chunk]
                )],
                action_items=[a for a in actions if any(
                    uid in a.utterance_ids for uid in [u.id for u in chunk]
                )],
                timestamp=datetime.now(),
                source_timestamp=chunk[0].timestamp if chunk else None,
                confidence=self._calculate_confidence(chunk),
                importance=self._calculate_importance(chunk, entities, actions),
                utterance_ids=[u.id for u in chunk],
                provenance={
                    'source': 'conversation',
                    'contact_id': contact_id,
                    'processing_version': '2.0.0',
                    'model': 'ensemble'
                }
            )
            
            memories.append(memory)
        
        return memories
    
    def _chunk_utterances(self, utterances: List[Utterance], max_size: int = 5) -> List[List[Utterance]]:
        """Group utterances into logical chunks"""
        chunks = []
        current_chunk = []
        
        for utterance in utterances:
            current_chunk.append(utterance)
            
            # Start new chunk on size limit or significant pause
            if len(current_chunk) >= max_size:
                chunks.append(current_chunk)
                current_chunk = []
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _determine_category(
        self,
        chunk: List[Utterance],
        entities: List[Entity],
        actions: List[ActionItem]
    ) -> MemoryCategory:
        """Determine memory category using ensemble approach"""
        
        # Combine text from chunk
        text = ' '.join(utt.text.lower() for utt in chunk)
        
        # Score each category
        category_scores = {}
        
        # Check for action items
        if any(a for a in actions if any(
            uid in a.utterance_ids for uid in [u.id for u in chunk]
        )):
            category_scores[MemoryCategory.ACTION_ITEMS] = 0.9
        
        # Check for decisions
        if any(word in text for word in ['decided', 'agreed', 'decision', 'conclude']):
            category_scores[MemoryCategory.DECISIONS] = 0.85
        
        # Check for dates
        if any(e.type == EntityType.DATE for e in entities):
            category_scores[MemoryCategory.IMPORTANT_DATES] = 0.8
        
        # Check for personal content
        if any(word in text for word in ['feel', 'think', 'personal', 'private']):
            category_scores[MemoryCategory.PERSONAL] = 0.75
        
        # Check for professional content
        if any(word in text for word in ['work', 'project', 'business', 'client']):
            category_scores[MemoryCategory.PROFESSIONAL] = 0.7
        
        # Return highest scoring category
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return MemoryCategory.NOTES
    
    def _generate_summary(self, chunk: List[Utterance]) -> str:
        """Generate summary of utterance chunk"""
        if not chunk:
            return ""
        
        full_text = ' '.join(utt.text for utt in chunk)
        # Take first 150 chars as summary
        return full_text[:150] + ('...' if len(full_text) > 150 else '')
    
    def _calculate_confidence(self, chunk: List[Utterance]) -> float:
        """Calculate confidence score for chunk"""
        if not chunk:
            return 0.0
        
        confidences = [utt.confidence for utt in chunk]
        return sum(confidences) / len(confidences)
    
    def _calculate_importance(
        self,
        chunk: List[Utterance],
        entities: List[Entity],
        actions: List[ActionItem]
    ) -> int:
        """Calculate importance score (1-10)"""
        
        score = 5  # Base score
        
        # Increase for action items
        relevant_actions = len([a for a in actions if any(
            uid in a.utterance_ids for uid in [u.id for u in chunk]
        )])
        score += min(relevant_actions, 3)
        
        # Increase for multiple entities
        relevant_entities = len([e for e in entities if any(
            uid in e.utterance_ids for uid in [u.id for u in chunk]
        )])
        if relevant_entities > 3:
            score += 1
        
        # Increase for high-confidence content
        confidence = self._calculate_confidence(chunk)
        if confidence > 0.8:
            score += 1
        
        return min(score, 10)
    
    def _aggregate_confidence(self, result: ProcessingResult) -> ProcessingResult:
        """Aggregate confidence scores across all models"""
        
        confidence_scores = []
        
        # Collect all confidence scores
        if result.utterances:
            utterance_conf = sum(u.confidence for u in result.utterances) / len(result.utterances)
            confidence_scores.append(('utterances', utterance_conf))
        
        if result.entities:
            entity_conf = sum(e.confidence for e in result.entities) / len(result.entities)
            confidence_scores.append(('entities', entity_conf))
        
        if result.memories:
            memory_conf = sum(m.confidence for m in result.memories) / len(result.memories)
            confidence_scores.append(('memories', memory_conf))
        
        # Add model-specific confidences
        for key, value in result.confidence_scores.items():
            confidence_scores.append((key, value))
        
        # Calculate weighted average
        if confidence_scores:
            # Weight recent AI enhancements higher
            weights = {
                'ai_enhancement': 1.5,
                'entities': 1.2,
                'memories': 1.3,
                'utterances': 1.0
            }
            
            weighted_sum = 0
            total_weight = 0
            
            for source, conf in confidence_scores:
                weight = weights.get(source, 1.0)
                weighted_sum += conf * weight
                total_weight += weight
            
            result.confidence_scores['aggregated'] = weighted_sum / total_weight
        else:
            result.confidence_scores['aggregated'] = 0.5
        
        return result
    
    def _update_stats(self, result: ProcessingResult, processing_time: float):
        """Update processing statistics"""
        
        self.stats['total_processed'] += 1
        self.stats['memories_created'] += len(result.memories)
        self.stats['entities_extracted'] += len(result.entities)
        self.stats['actions_extracted'] += len(result.action_items)
        self.stats['processing_times'].append(processing_time)
        
        # Update average confidence
        if result.confidence_scores:
            agg_conf = result.confidence_scores.get('aggregated', 0)
            if self.stats['avg_confidence'] == 0:
                self.stats['avg_confidence'] = agg_conf
            else:
                # Running average
                self.stats['avg_confidence'] = (
                    self.stats['avg_confidence'] * 0.9 + agg_conf * 0.1
                )
        
        self.stats['last_run'] = datetime.now()
        
        # Keep only last 100 processing times
        if len(self.stats['processing_times']) > 100:
            self.stats['processing_times'] = self.stats['processing_times'][-100:]
    
    async def process_all_transcripts(self) -> Dict[str, Any]:
        """Process all pending transcripts"""
        
        results = {
            'contacts_processed': 0,
            'total_memories': 0,
            'total_entities': 0,
            'total_actions': 0,
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Find all contact directories
        contact_dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        
        for contact_dir in contact_dirs:
            try:
                contact_id = contact_dir.name
                logger.info(f"Processing contact: {contact_id}")
                
                # Process any pending transcripts
                transcript_file = contact_dir / 'transcripts.md'
                
                if transcript_file.exists():
                    content = transcript_file.read_text(encoding='utf-8')
                    
                    if content.strip() and 'Awaiting Analysis' in content:
                        # Process using new architecture
                        result = await self.process_conversation(
                            {'transcript': content},
                            contact_id,
                            use_orchestrator=True
                        )
                        
                        results['contacts_processed'] += 1
                        results['total_memories'] += len(result.memories)
                        results['total_entities'] += len(result.entities)
                        results['total_actions'] += len(result.action_items)
                        
                        # Clear transcript after processing
                        await self._clear_transcript(contact_id)
                
            except Exception as e:
                error_msg = f"Error processing {contact_id}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    async def _clear_transcript(self, contact_id: str):
        """Clear processed transcript"""
        
        transcript_file = self.base_dir / contact_id / 'transcripts.md'
        
        if transcript_file.exists():
            # Archive the processed content
            archive_dir = self.base_dir / contact_id / 'archive'
            archive_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_file = archive_dir / f'transcript_{timestamp}.md'
            
            # Move content to archive
            content = transcript_file.read_text(encoding='utf-8')
            archive_file.write_text(content, encoding='utf-8')
            
            # Clear transcript
            transcript_file.write_text('# Transcript\n\n## Awaiting Analysis\n\n', encoding='utf-8')
            
            logger.info(f"Archived transcript for {contact_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        
        stats = dict(self.stats)
        
        # Calculate average processing time
        if stats['processing_times']:
            stats['avg_processing_time'] = sum(stats['processing_times']) / len(stats['processing_times'])
        else:
            stats['avg_processing_time'] = 0
        
        # Model usage percentages
        total_model_usage = sum(stats['model_usage'].values())
        if total_model_usage > 0:
            stats['model_usage_pct'] = {
                k: (v / total_model_usage * 100) 
                for k, v in stats['model_usage'].items()
            }
        
        return stats

# Singleton instance
_agent_instance: Optional[MDAgentUpgraded] = None

def get_upgraded_agent() -> MDAgentUpgraded:
    """Get or create the upgraded MD Agent instance"""
    global _agent_instance
    
    if _agent_instance is None:
        _agent_instance = MDAgentUpgraded()
    
    return _agent_instance