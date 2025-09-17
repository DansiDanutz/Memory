#!/usr/bin/env python3
"""
Advanced Entity Extraction System for Circleback-style MD Agent
Extracts entities with confidence scoring and relationship mapping
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
import json
from dataclasses import dataclass

# Import schemas
from .schemas import Entity, EntityType, Relation, RelationType, Utterance

# Try to import spaCy (optional)
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available - using pattern-based extraction only")

# Setup logging
logger = logging.getLogger(__name__)

class EntityExtractor:
    """
    Advanced entity extraction with NER, pattern matching, and confidence scoring
    """
    
    # Entity patterns for regex-based extraction
    ENTITY_PATTERNS = {
        EntityType.EMAIL: [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ],
        EntityType.PHONE: [
            r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\b(?:\+\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b'
        ],
        EntityType.URL: [
            r'\b(?:https?://|www\.|ftp://)[-A-Za-z0-9+&@#/%?=~_|!:,.;]*[-A-Za-z0-9+&@#/%=~_|]'
        ],
        EntityType.MONEY: [
            r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:million|billion|M|B|K))?',
            r'\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|dollars?|euros?|pounds?)\b'
        ],
        EntityType.DATE: [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?\b',
            r'\b(?:tomorrow|today|yesterday|next\s+(?:week|month|year)|last\s+(?:week|month|year))\b',
            r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b'
        ],
        EntityType.METRIC: [
            r'\b\d+(?:\.\d+)?\s*(?:%|percent|percentage)\b',
            r'\b\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB|ms|seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b'
        ]
    }
    
    # Keywords for entity type detection
    ENTITY_KEYWORDS = {
        EntityType.PERSON: ['mr', 'mrs', 'ms', 'dr', 'prof', 'ceo', 'cto', 'manager', 'director'],
        EntityType.ORGANIZATION: ['inc', 'llc', 'ltd', 'corp', 'company', 'corporation', 'foundation', 'institute'],
        EntityType.LOCATION: ['street', 'avenue', 'road', 'city', 'state', 'country', 'building'],
        EntityType.PROJECT: ['project', 'initiative', 'program', 'campaign', 'sprint'],
        EntityType.SKILL: ['python', 'java', 'javascript', 'react', 'aws', 'docker', 'kubernetes']
    }
    
    def __init__(self, enable_spacy: bool = True):
        """
        Initialize the entity extractor
        
        Args:
            enable_spacy: Whether to use spaCy NER if available
        """
        self.enable_spacy = enable_spacy and SPACY_AVAILABLE
        self.nlp = None
        
        if self.enable_spacy:
            try:
                # Try to load spaCy model
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("🤖 spaCy NER model loaded successfully")
            except:
                logger.warning("Failed to load spaCy model - install with: python -m spacy download en_core_web_sm")
                self.enable_spacy = False
        
        # Entity cache for deduplication
        self.entity_cache: Dict[str, Entity] = {}
        self.relation_cache: Set[Tuple[str, str, str]] = set()
        
        logger.info(f"🎯 Entity Extractor initialized (spaCy: {self.enable_spacy})")
    
    async def extract_entities(
        self,
        utterances: List[Utterance]
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        Extract entities and relations from utterances
        
        Args:
            utterances: List of utterances to process
            
        Returns:
            Tuple of extracted entities and relations
        """
        entities = []
        relations = []
        
        # Clear caches for new processing
        self.entity_cache.clear()
        self.relation_cache.clear()
        
        for utterance in utterances:
            # Extract entities from this utterance
            utt_entities = await self._extract_from_utterance(utterance)
            
            # Add utterance ID to entities
            for entity in utt_entities:
                entity.utterance_ids.append(utterance.id)
            
            entities.extend(utt_entities)
            
            # Extract relations between entities
            utt_relations = await self._extract_relations(utt_entities, utterance)
            relations.extend(utt_relations)
        
        # Deduplicate and merge entities
        merged_entities = self._merge_entities(entities)
        
        # Enhance entities with additional context
        enhanced_entities = await self._enhance_entities(merged_entities, utterances)
        
        # Build entity graph relations
        graph_relations = await self._build_entity_graph(enhanced_entities, utterances)
        relations.extend(graph_relations)
        
        logger.info(f"Extracted {len(enhanced_entities)} unique entities, {len(relations)} relations")
        
        return enhanced_entities, relations
    
    async def _extract_from_utterance(self, utterance: Utterance) -> List[Entity]:
        """
        Extract entities from a single utterance
        """
        entities = []
        text = utterance.text
        
        # Pattern-based extraction
        pattern_entities = self._extract_pattern_entities(text)
        entities.extend(pattern_entities)
        
        # spaCy NER extraction
        if self.enable_spacy and self.nlp:
            spacy_entities = self._extract_spacy_entities(text)
            entities.extend(spacy_entities)
        
        # Keyword-based extraction
        keyword_entities = self._extract_keyword_entities(text)
        entities.extend(keyword_entities)
        
        # Custom extractors
        entities.extend(self._extract_people(text))
        entities.extend(self._extract_organizations(text))
        entities.extend(self._extract_projects(text))
        
        return entities
    
    def _extract_pattern_entities(self, text: str) -> List[Entity]:
        """
        Extract entities using regex patterns
        """
        entities = []
        
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    value = match.group(0)
                    
                    # Skip if already cached
                    cache_key = f"{entity_type}:{value.lower()}"
                    if cache_key in self.entity_cache:
                        entities.append(self.entity_cache[cache_key])
                        continue
                    
                    entity = Entity(
                        type=entity_type,
                        value=value,
                        canonical_name=self._canonicalize(value, entity_type),
                        confidence=0.85,  # Pattern match confidence
                        context=text[max(0, match.start()-50):min(len(text), match.end()+50)]
                    )
                    
                    self.entity_cache[cache_key] = entity
                    entities.append(entity)
        
        return entities
    
    def _extract_spacy_entities(self, text: str) -> List[Entity]:
        """
        Extract entities using spaCy NER
        """
        entities = []
        
        if not self.nlp:
            return entities
        
        doc = self.nlp(text)
        
        # Map spaCy entity types to our types
        type_mapping = {
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'GPE': EntityType.LOCATION,
            'LOC': EntityType.LOCATION,
            'DATE': EntityType.DATE,
            'MONEY': EntityType.MONEY,
            'PRODUCT': EntityType.PRODUCT
        }
        
        for ent in doc.ents:
            if ent.label_ in type_mapping:
                entity_type = type_mapping[ent.label_]
                
                # Check cache
                cache_key = f"{entity_type}:{ent.text.lower()}"
                if cache_key in self.entity_cache:
                    entities.append(self.entity_cache[cache_key])
                    continue
                
                entity = Entity(
                    type=entity_type,
                    value=ent.text,
                    canonical_name=self._canonicalize(ent.text, entity_type),
                    confidence=0.75,  # spaCy confidence
                    context=text[max(0, ent.start_char-50):min(len(text), ent.end_char+50)],
                    attributes={'spacy_label': ent.label_}
                )
                
                self.entity_cache[cache_key] = entity
                entities.append(entity)
        
        return entities
    
    def _extract_keyword_entities(self, text: str) -> List[Entity]:
        """
        Extract entities based on keywords
        """
        entities = []
        text_lower = text.lower()
        
        for entity_type, keywords in self.ENTITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Find the context around the keyword
                    index = text_lower.find(keyword)
                    if index != -1:
                        # Extract surrounding words as potential entity
                        start = max(0, index - 50)
                        end = min(len(text), index + len(keyword) + 50)
                        context = text[start:end]
                        
                        # Extract entity name (simple heuristic)
                        words = context.split()
                        if len(words) > 0:
                            # Take words around the keyword
                            entity_value = ' '.join(words[:5])  # Simple extraction
                            
                            # Check cache
                            cache_key = f"{entity_type}:{entity_value.lower()}"
                            if cache_key not in self.entity_cache:
                                entity = Entity(
                                    type=entity_type,
                                    value=entity_value,
                                    canonical_name=self._canonicalize(entity_value, entity_type),
                                    confidence=0.6,  # Keyword match confidence
                                    context=context,
                                    attributes={'keyword_match': keyword}
                                )
                                
                                self.entity_cache[cache_key] = entity
                                entities.append(entity)
        
        return entities
    
    def _extract_people(self, text: str) -> List[Entity]:
        """
        Extract person entities using patterns
        """
        entities = []
        
        # Pattern for names (Title FirstName LastName)
        name_pattern = r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        matches = re.finditer(name_pattern, text)
        
        for match in matches:
            name = match.group(1)
            
            cache_key = f"{EntityType.PERSON}:{name.lower()}"
            if cache_key not in self.entity_cache:
                entity = Entity(
                    type=EntityType.PERSON,
                    value=name,
                    canonical_name=name,
                    confidence=0.8,
                    context=text[max(0, match.start()-30):min(len(text), match.end()+30)]
                )
                
                self.entity_cache[cache_key] = entity
                entities.append(entity)
        
        # Pattern for @mentions
        mention_pattern = r'@([A-Za-z0-9_]+)'
        matches = re.finditer(mention_pattern, text)
        
        for match in matches:
            username = match.group(1)
            
            cache_key = f"{EntityType.PERSON}:@{username.lower()}"
            if cache_key not in self.entity_cache:
                entity = Entity(
                    type=EntityType.PERSON,
                    value=f"@{username}",
                    canonical_name=username,
                    confidence=0.9,
                    context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                    attributes={'is_mention': True}
                )
                
                self.entity_cache[cache_key] = entity
                entities.append(entity)
        
        return entities
    
    def _extract_organizations(self, text: str) -> List[Entity]:
        """
        Extract organization entities
        """
        entities = []
        
        # Pattern for company names
        org_pattern = r'\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Inc|LLC|Ltd|Corp|Company|Corporation))\b'
        matches = re.finditer(org_pattern, text)
        
        for match in matches:
            org_name = match.group(1)
            
            cache_key = f"{EntityType.ORGANIZATION}:{org_name.lower()}"
            if cache_key not in self.entity_cache:
                entity = Entity(
                    type=EntityType.ORGANIZATION,
                    value=org_name,
                    canonical_name=org_name,
                    confidence=0.85,
                    context=text[max(0, match.start()-30):min(len(text), match.end()+30)]
                )
                
                self.entity_cache[cache_key] = entity
                entities.append(entity)
        
        return entities
    
    def _extract_projects(self, text: str) -> List[Entity]:
        """
        Extract project entities
        """
        entities = []
        
        # Pattern for project names
        project_patterns = [
            r'\b(?:Project|Initiative|Program|Campaign)\s+([A-Z][A-Za-z0-9\s]+?)(?=\.|,|;|\s+(?:is|was|will))'
        ]
        
        for pattern in project_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                project_name = match.group(1).strip()
                
                cache_key = f"{EntityType.PROJECT}:{project_name.lower()}"
                if cache_key not in self.entity_cache:
                    entity = Entity(
                        type=EntityType.PROJECT,
                        value=project_name,
                        canonical_name=project_name,
                        confidence=0.7,
                        context=text[max(0, match.start()-30):min(len(text), match.end()+30)]
                    )
                    
                    self.entity_cache[cache_key] = entity
                    entities.append(entity)
        
        return entities
    
    def _canonicalize(self, value: str, entity_type: EntityType) -> str:
        """
        Canonicalize entity value
        """
        if entity_type == EntityType.EMAIL:
            return value.lower().strip()
        
        elif entity_type == EntityType.PHONE:
            # Remove non-digits
            digits = re.sub(r'\D', '', value)
            if len(digits) == 10:  # US phone
                return f"+1{digits}"
            return f"+{digits}"
        
        elif entity_type == EntityType.URL:
            # Ensure protocol
            if not value.startswith(('http://', 'https://')):
                return f"https://{value}"
            return value.lower()
        
        elif entity_type == EntityType.DATE:
            # Try to parse and normalize date
            return self._normalize_date(value)
        
        elif entity_type == EntityType.MONEY:
            # Extract numeric value
            amount = re.findall(r'[\d,]+\.?\d*', value)
            if amount:
                return amount[0].replace(',', '')
            return value
        
        # Default: clean and title case
        return ' '.join(value.split()).title()
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date strings
        """
        date_str_lower = date_str.lower()
        
        # Handle relative dates
        today = datetime.now()
        
        if 'today' in date_str_lower:
            return today.strftime('%Y-%m-%d')
        elif 'tomorrow' in date_str_lower:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'yesterday' in date_str_lower:
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'next week' in date_str_lower:
            return (today + timedelta(weeks=1)).strftime('%Y-%m-%d')
        elif 'next month' in date_str_lower:
            return (today + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Try to parse actual date
        from dateutil import parser
        try:
            parsed_date = parser.parse(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return date_str
    
    def _merge_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Merge duplicate entities
        """
        merged = {}
        
        for entity in entities:
            key = f"{entity.type}:{entity.canonical_name.lower()}"
            
            if key in merged:
                # Merge with existing
                existing = merged[key]
                existing.utterance_ids.extend(entity.utterance_ids)
                existing.utterance_ids = list(set(existing.utterance_ids))
                
                # Update confidence (average)
                existing.confidence = (existing.confidence + entity.confidence) / 2
                
                # Merge aliases
                if entity.value not in existing.aliases:
                    existing.aliases.append(entity.value)
                
                # Merge attributes
                existing.attributes.update(entity.attributes)
            else:
                merged[key] = entity
        
        return list(merged.values())
    
    async def _enhance_entities(self, entities: List[Entity], utterances: List[Utterance]) -> List[Entity]:
        """
        Enhance entities with additional context
        """
        # Build utterance map
        utterance_map = {u.id: u for u in utterances}
        
        for entity in entities:
            # Add speaker information
            speakers = set()
            for utt_id in entity.utterance_ids:
                if utt_id in utterance_map:
                    speakers.add(utterance_map[utt_id].speaker_id)
            
            entity.attributes['mentioned_by'] = list(speakers)
            
            # Calculate importance based on frequency
            entity.attributes['frequency'] = len(entity.utterance_ids)
            
            # Adjust confidence based on frequency
            if len(entity.utterance_ids) > 1:
                entity.confidence = min(entity.confidence * 1.1, 1.0)
        
        return entities
    
    async def _extract_relations(self, entities: List[Entity], utterance: Utterance) -> List[Relation]:
        """
        Extract relations between entities in an utterance
        """
        relations = []
        text = utterance.text.lower()
        
        # Simple relation patterns
        relation_patterns = [
            (r'(\w+)\s+works?\s+(?:for|at|with)\s+(\w+)', RelationType.WORKS_FOR),
            (r'(\w+)\s+reports?\s+to\s+(\w+)', RelationType.REPORTS_TO),
            (r'(\w+)\s+(?:is|are)\s+located\s+(?:in|at)\s+(\w+)', RelationType.LOCATED_AT),
            (r'(\w+)\s+owns?\s+(\w+)', RelationType.OWNS),
            (r'(\w+)\s+(?:scheduled|planned)\s+for\s+(\w+)', RelationType.SCHEDULED_FOR),
            (r'(\w+)\s+assigned\s+to\s+(\w+)', RelationType.ASSIGNED_TO)
        ]
        
        for pattern, relation_type in relation_patterns:
            matches = re.finditer(pattern, text)
            
            for match in matches:
                source_text = match.group(1)
                target_text = match.group(2)
                
                # Find matching entities
                source_entity = None
                target_entity = None
                
                for entity in entities:
                    if source_text in entity.value.lower() or source_text in entity.canonical_name.lower():
                        source_entity = entity
                    if target_text in entity.value.lower() or target_text in entity.canonical_name.lower():
                        target_entity = entity
                
                if source_entity and target_entity:
                    # Check if relation already exists
                    rel_key = (source_entity.id, target_entity.id, relation_type.value)
                    if rel_key not in self.relation_cache:
                        relation = Relation(
                            source_entity_id=source_entity.id,
                            target_entity_id=target_entity.id,
                            relation_type=relation_type,
                            confidence=0.7,
                            evidence=[utterance.id],
                            timestamp=utterance.timestamp
                        )
                        
                        self.relation_cache.add(rel_key)
                        relations.append(relation)
        
        return relations
    
    async def _build_entity_graph(self, entities: List[Entity], utterances: List[Utterance]) -> List[Relation]:
        """
        Build entity relationship graph
        """
        relations = []
        
        # Group entities by utterance
        utterance_entities = {}
        for entity in entities:
            for utt_id in entity.utterance_ids:
                if utt_id not in utterance_entities:
                    utterance_entities[utt_id] = []
                utterance_entities[utt_id].append(entity)
        
        # Find co-occurring entities
        for utt_id, utt_entities in utterance_entities.items():
            if len(utt_entities) < 2:
                continue
            
            # Create MENTIONED_IN relations for co-occurring entities
            for i, entity1 in enumerate(utt_entities):
                for entity2 in utt_entities[i+1:]:
                    rel_key = (entity1.id, entity2.id, RelationType.MENTIONED_IN.value)
                    
                    if rel_key not in self.relation_cache:
                        relation = Relation(
                            source_entity_id=entity1.id,
                            target_entity_id=entity2.id,
                            relation_type=RelationType.MENTIONED_IN,
                            confidence=0.5,
                            evidence=[utt_id],
                            metadata={'co_occurrence': True}
                        )
                        
                        self.relation_cache.add(rel_key)
                        relations.append(relation)
        
        return relations
    
    def get_entity_statistics(self, entities: List[Entity]) -> Dict[str, Any]:
        """
        Get statistics about extracted entities
        """
        stats = {
            'total_entities': len(entities),
            'by_type': {},
            'avg_confidence': 0.0,
            'high_confidence_count': 0,
            'unique_canonical': len(set(e.canonical_name for e in entities))
        }
        
        # Count by type
        for entity in entities:
            entity_type = entity.type.value
            if entity_type not in stats['by_type']:
                stats['by_type'][entity_type] = 0
            stats['by_type'][entity_type] += 1
            
            if entity.confidence > 0.8:
                stats['high_confidence_count'] += 1
        
        # Average confidence
        if entities:
            stats['avg_confidence'] = sum(e.confidence for e in entities) / len(entities)
        
        return stats