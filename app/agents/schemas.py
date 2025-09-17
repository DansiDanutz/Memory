#!/usr/bin/env python3
"""
Structured Data Models for Circleback-style MD Agent
Provides comprehensive schemas for transcript processing and memory management
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
import json
from uuid import uuid4

# Enums for type safety
class EntityType(str, Enum):
    """Types of entities we can extract"""
    PERSON = "person"
    ORGANIZATION = "organization"
    DATE = "date"
    LOCATION = "location"
    MONEY = "money"
    PRODUCT = "product"
    METRIC = "metric"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    PROJECT = "project"
    SKILL = "skill"

class RelationType(str, Enum):
    """Types of relationships between entities"""
    WORKS_FOR = "works_for"
    REPORTS_TO = "reports_to"
    COLLABORATES_WITH = "collaborates_with"
    OWNS = "owns"
    LOCATED_AT = "located_at"
    SCHEDULED_FOR = "scheduled_for"
    ASSIGNED_TO = "assigned_to"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    MENTIONED_IN = "mentioned_in"

class MemoryCategory(str, Enum):
    """Memory categories with enhanced granularity"""
    PERSONAL = "personal"
    SHARED = "shared"
    IMPORTANT_DATES = "important_dates"
    ACTION_ITEMS = "action_items"
    DECISIONS = "decisions"
    NOTES = "notes"
    VOICE = "voice"
    MEDIA = "media"
    PROFESSIONAL = "professional"
    CONFIDENTIAL = "confidential"
    KNOWLEDGE = "knowledge"
    RELATIONSHIPS = "relationships"
    PREFERENCES = "preferences"
    GOALS = "goals"

class ActionPriority(str, Enum):
    """Priority levels for action items"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"

class ActionStatus(str, Enum):
    """Status of action items"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"

@dataclass
class Utterance:
    """
    Represents a single utterance in a conversation
    Fundamental unit of conversation analysis
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    speaker_id: str = ""
    speaker_name: Optional[str] = None
    text: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    audio_segment: Optional[Dict[str, Any]] = None  # Start/end times, audio file ref
    language: Optional[str] = None
    sentiment: Optional[float] = None  # -1 to 1
    emotion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'speaker_id': self.speaker_id,
            'speaker_name': self.speaker_name,
            'text': self.text,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'audio_segment': self.audio_segment,
            'language': self.language,
            'sentiment': self.sentiment,
            'emotion': self.emotion,
            'metadata': self.metadata
        }

@dataclass
class Entity:
    """
    Represents an extracted entity from conversation
    Includes confidence scoring and normalization
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    type: EntityType = EntityType.PERSON
    value: str = ""  # Raw extracted value
    canonical_name: str = ""  # Normalized/cleaned value
    confidence: float = 1.0
    utterance_ids: List[str] = field(default_factory=list)  # Where mentioned
    context: Optional[str] = None  # Surrounding text
    attributes: Dict[str, Any] = field(default_factory=dict)  # Additional properties
    aliases: List[str] = field(default_factory=list)  # Alternative names
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'type': self.type.value,
            'value': self.value,
            'canonical_name': self.canonical_name,
            'confidence': self.confidence,
            'utterance_ids': self.utterance_ids,
            'context': self.context,
            'attributes': self.attributes,
            'aliases': self.aliases
        }

@dataclass
class Relation:
    """
    Represents a relationship between entities
    Builds knowledge graph of connections
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    source_entity_id: str = ""
    target_entity_id: str = ""
    relation_type: RelationType = RelationType.RELATED_TO
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)  # Utterance IDs supporting this
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'source_entity_id': self.source_entity_id,
            'target_entity_id': self.target_entity_id,
            'relation_type': self.relation_type.value,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

@dataclass
class ActionItem:
    """
    Represents an action item or task extracted from conversation
    Includes assignee, dependencies, and tracking
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: Optional[str] = None
    assignee: Optional[str] = None  # Entity ID or name
    owner: Optional[str] = None  # Who created/owns this
    due_date: Optional[datetime] = None
    priority: ActionPriority = ActionPriority.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # Other action IDs
    blockers: List[str] = field(default_factory=list)
    utterance_ids: List[str] = field(default_factory=list)  # Source utterances
    tags: List[str] = field(default_factory=list)
    completion_criteria: Optional[str] = None
    estimated_effort: Optional[str] = None  # e.g., "2 hours", "1 day"
    actual_effort: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'assignee': self.assignee,
            'owner': self.owner,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority.value,
            'status': self.status.value,
            'dependencies': self.dependencies,
            'blockers': self.blockers,
            'utterance_ids': self.utterance_ids,
            'tags': self.tags,
            'completion_criteria': self.completion_criteria,
            'estimated_effort': self.estimated_effort,
            'actual_effort': self.actual_effort,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.metadata
        }

@dataclass
class Memory:
    """
    Represents a categorized memory with full provenance
    Core unit of knowledge storage
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    summary: Optional[str] = None  # Brief summary of content
    category: MemoryCategory = MemoryCategory.NOTES
    subcategory: Optional[str] = None
    entities: List[Entity] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    source_timestamp: Optional[datetime] = None  # When originally said/created
    confidence: float = 1.0
    importance: int = 5  # 1-10 scale
    provenance: Dict[str, Any] = field(default_factory=dict)  # Source tracking
    utterance_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    context: Optional[Dict[str, Any]] = None  # Meeting info, participants, etc.
    related_memory_ids: List[str] = field(default_factory=list)
    corrections: List[Dict[str, Any]] = field(default_factory=list)  # Edit history
    verified: bool = False
    visibility: Literal["private", "shared", "public"] = "private"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'content': self.content,
            'summary': self.summary,
            'category': self.category.value,
            'subcategory': self.subcategory,
            'entities': [e.to_dict() for e in self.entities],
            'action_items': [a.to_dict() for a in self.action_items],
            'relations': [r.to_dict() for r in self.relations],
            'timestamp': self.timestamp.isoformat(),
            'source_timestamp': self.source_timestamp.isoformat() if self.source_timestamp else None,
            'confidence': self.confidence,
            'importance': self.importance,
            'provenance': self.provenance,
            'utterance_ids': self.utterance_ids,
            'tags': self.tags,
            'keywords': self.keywords,
            'context': self.context,
            'related_memory_ids': self.related_memory_ids,
            'corrections': self.corrections,
            'verified': self.verified,
            'visibility': self.visibility,
            'metadata': self.metadata
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format for storage"""
        md_parts = [f"### 📝 {self.summary or self.content[:50]}..."]
        
        # Metadata section
        md_parts.append(f"**ID:** `{self.id}`")
        md_parts.append(f"**Date:** {self.timestamp.strftime('%Y-%m-%d %H:%M')}")
        md_parts.append(f"**Confidence:** {self.confidence:.2f}")
        md_parts.append(f"**Importance:** {'⭐' * min(self.importance, 10)}")
        
        # Content
        md_parts.append(f"\n{self.content}")
        
        # Entities
        if self.entities:
            md_parts.append("\n**Entities:**")
            for entity in self.entities:
                md_parts.append(f"- {entity.type.value}: {entity.canonical_name} ({entity.confidence:.2f})")
        
        # Action Items
        if self.action_items:
            md_parts.append("\n**Action Items:**")
            for action in self.action_items:
                status_emoji = "✅" if action.status == ActionStatus.COMPLETED else "⏳"
                md_parts.append(f"- {status_emoji} {action.title}")
                if action.assignee:
                    md_parts.append(f"  - Assignee: {action.assignee}")
                if action.due_date:
                    md_parts.append(f"  - Due: {action.due_date.strftime('%Y-%m-%d')}")
        
        # Tags
        if self.tags:
            md_parts.append(f"\n**Tags:** {', '.join([f'#{tag}' for tag in self.tags])}")
        
        # Metadata (JSON for preservation)
        md_parts.append(f"\n<details>")
        md_parts.append(f"<summary>Metadata</summary>")
        md_parts.append(f"\n```json")
        md_parts.append(json.dumps(self.to_dict(), indent=2))
        md_parts.append(f"```")
        md_parts.append(f"</details>")
        
        return '\n'.join(md_parts) + '\n\n---\n'

@dataclass
class ConversationContext:
    """
    Context information for a conversation
    Provides meeting details, participants, and related data
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    meeting_title: Optional[str] = None
    meeting_type: Optional[str] = None  # standup, 1:1, review, etc.
    participants: List[Dict[str, Any]] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    actual_time: Optional[datetime] = None
    duration: Optional[int] = None  # minutes
    location: Optional[str] = None
    agenda: Optional[List[str]] = None
    related_documents: List[str] = field(default_factory=list)
    previous_meeting_id: Optional[str] = None
    next_meeting_id: Optional[str] = None
    project: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'meeting_title': self.meeting_title,
            'meeting_type': self.meeting_type,
            'participants': self.participants,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'actual_time': self.actual_time.isoformat() if self.actual_time else None,
            'duration': self.duration,
            'location': self.location,
            'agenda': self.agenda,
            'related_documents': self.related_documents,
            'previous_meeting_id': self.previous_meeting_id,
            'next_meeting_id': self.next_meeting_id,
            'project': self.project,
            'metadata': self.metadata
        }

@dataclass
class ProcessingResult:
    """
    Complete result of processing a conversation
    Contains all extracted data and metadata
    """
    conversation_id: str = field(default_factory=lambda: str(uuid4()))
    utterances: List[Utterance] = field(default_factory=list)
    memories: List[Memory] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    context: Optional[ConversationContext] = None
    processing_time: float = 0.0
    model_versions: Dict[str, str] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'conversation_id': self.conversation_id,
            'utterances': [u.to_dict() for u in self.utterances],
            'memories': [m.to_dict() for m in self.memories],
            'entities': [e.to_dict() for e in self.entities],
            'relations': [r.to_dict() for r in self.relations],
            'action_items': [a.to_dict() for a in self.action_items],
            'context': self.context.to_dict() if self.context else None,
            'processing_time': self.processing_time,
            'model_versions': self.model_versions,
            'confidence_scores': self.confidence_scores,
            'errors': self.errors,
            'warnings': self.warnings,
            'metadata': self.metadata
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of processing results"""
        return {
            'conversation_id': self.conversation_id,
            'total_utterances': len(self.utterances),
            'total_memories': len(self.memories),
            'total_entities': len(self.entities),
            'total_relations': len(self.relations),
            'total_action_items': len(self.action_items),
            'action_items_pending': len([a for a in self.action_items if a.status == ActionStatus.PENDING]),
            'high_priority_actions': len([a for a in self.action_items if a.priority in [ActionPriority.HIGH, ActionPriority.CRITICAL]]),
            'processing_time': self.processing_time,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }