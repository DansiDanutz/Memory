#!/usr/bin/env python3
"""
Context Enhancement System for Circleback-style MD Agent
Integrates calendar, profiles, and historical context
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Import schemas
from .schemas import (
    ConversationContext, Utterance, Entity, ActionItem, 
    Memory, MemoryCategory
)

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """User profile information"""
    user_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    preferences: Dict[str, Any] = None
    history_summary: Dict[str, Any] = None
    voice_profile: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'department': self.department,
            'preferences': self.preferences or {},
            'history_summary': self.history_summary or {},
            'voice_profile': self.voice_profile,
            'metadata': self.metadata or {}
        }

@dataclass
class CalendarEvent:
    """Calendar event information"""
    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    participants: List[str]
    location: Optional[str] = None
    description: Optional[str] = None
    agenda: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    meeting_type: Optional[str] = None
    recurring: bool = False
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'title': self.title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'participants': self.participants,
            'location': self.location,
            'description': self.description,
            'agenda': self.agenda,
            'attachments': self.attachments,
            'meeting_type': self.meeting_type,
            'recurring': self.recurring,
            'metadata': self.metadata or {}
        }

class ContextEnhancer:
    """
    Enhances conversations with calendar, profile, and historical context
    """
    
    def __init__(
        self,
        base_dir: str = 'data/memories',
        profiles_dir: str = 'memory-system/users/profiles',
        calendar_dir: str = 'memory-system/calendar'
    ):
        """
        Initialize the context enhancer
        
        Args:
            base_dir: Base directory for memories
            profiles_dir: Directory for user profiles
            calendar_dir: Directory for calendar data
        """
        self.base_dir = Path(base_dir)
        self.profiles_dir = Path(profiles_dir)
        self.calendar_dir = Path(calendar_dir)
        
        # Ensure directories exist
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.calendar_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for loaded data
        self.profile_cache: Dict[str, UserProfile] = {}
        self.calendar_cache: Dict[str, CalendarEvent] = {}
        self.memory_cache: Dict[str, List[Memory]] = {}
        
        logger.info("🌐 Context Enhancer initialized")
    
    async def enhance_context(
        self,
        utterances: List[Utterance],
        entities: List[Entity],
        action_items: List[ActionItem],
        contact_id: str,
        initial_context: Optional[ConversationContext] = None
    ) -> ConversationContext:
        """
        Enhance conversation context with external data
        
        Args:
            utterances: List of conversation utterances
            entities: Extracted entities
            action_items: Extracted action items
            contact_id: Contact identifier
            initial_context: Optional initial context
            
        Returns:
            Enhanced conversation context
        """
        context = initial_context or ConversationContext()
        
        # Enhance with calendar context
        context = await self._enhance_with_calendar(context, utterances)
        
        # Enhance with participant profiles
        context = await self._enhance_with_profiles(context, utterances, entities)
        
        # Enhance with historical context
        context = await self._enhance_with_history(context, contact_id, entities)
        
        # Enhance with related documents
        context = await self._enhance_with_documents(context, entities, action_items)
        
        # Apply organizational corrections
        context = await self._apply_corrections(context, entities)
        
        # Calculate context confidence
        context.metadata['confidence'] = self._calculate_context_confidence(context)
        
        logger.info(f"Enhanced context with {len(context.participants)} participants")
        
        return context
    
    async def _enhance_with_calendar(
        self,
        context: ConversationContext,
        utterances: List[Utterance]
    ) -> ConversationContext:
        """Enhance with calendar information"""
        
        if not utterances:
            return context
        
        # Get conversation timeframe
        start_time = utterances[0].timestamp
        end_time = utterances[-1].timestamp
        
        # Find matching calendar events
        matching_events = await self._find_calendar_events(start_time, end_time)
        
        if matching_events:
            # Use best matching event
            best_event = matching_events[0]
            
            context.meeting_title = best_event.title
            context.meeting_type = best_event.meeting_type
            context.scheduled_time = best_event.start_time
            context.actual_time = start_time
            context.location = best_event.location
            context.agenda = best_event.agenda
            
            # Add event metadata
            context.metadata['calendar_event'] = best_event.to_dict()
            
            # Extract participants from calendar
            calendar_participants = []
            for participant_email in best_event.participants:
                calendar_participants.append({
                    'email': participant_email,
                    'source': 'calendar'
                })
            
            # Merge with existing participants
            if not context.participants:
                context.participants = []
            
            for cal_participant in calendar_participants:
                # Check if not already in list
                if not any(p.get('email') == cal_participant['email'] 
                          for p in context.participants):
                    context.participants.append(cal_participant)
        
        return context
    
    async def _find_calendar_events(
        self,
        start_time: datetime,
        end_time: datetime,
        tolerance_minutes: int = 30
    ) -> List[CalendarEvent]:
        """Find calendar events matching the timeframe"""
        
        matching_events = []
        
        # Load calendar data (mock implementation)
        calendar_file = self.calendar_dir / "events.json"
        
        if calendar_file.exists():
            try:
                with open(calendar_file, 'r', encoding='utf-8') as f:
                    events_data = json.load(f)
                
                for event_data in events_data:
                    # Parse event
                    event = CalendarEvent(
                        event_id=event_data['id'],
                        title=event_data['title'],
                        start_time=datetime.fromisoformat(event_data['start_time']),
                        end_time=datetime.fromisoformat(event_data['end_time']),
                        participants=event_data.get('participants', []),
                        location=event_data.get('location'),
                        description=event_data.get('description'),
                        agenda=event_data.get('agenda'),
                        meeting_type=event_data.get('meeting_type'),
                        recurring=event_data.get('recurring', False)
                    )
                    
                    # Check if event overlaps with conversation
                    tolerance = timedelta(minutes=tolerance_minutes)
                    
                    if (event.start_time - tolerance <= start_time <= event.end_time + tolerance or
                        event.start_time - tolerance <= end_time <= event.end_time + tolerance):
                        matching_events.append(event)
                        
                        # Cache event
                        self.calendar_cache[event.event_id] = event
            
            except Exception as e:
                logger.error(f"Error loading calendar: {e}")
        
        # Sort by best match (closest to conversation time)
        matching_events.sort(key=lambda e: abs((e.start_time - start_time).total_seconds()))
        
        return matching_events
    
    async def _enhance_with_profiles(
        self,
        context: ConversationContext,
        utterances: List[Utterance],
        entities: List[Entity]
    ) -> ConversationContext:
        """Enhance with participant profiles"""
        
        # Collect unique speakers
        speakers = set()
        for utterance in utterances:
            speakers.add(utterance.speaker_id)
        
        # Add entities that are people
        from .schemas import EntityType
        for entity in entities:
            if entity.type == EntityType.PERSON:
                speakers.add(entity.canonical_name)
        
        # Load profiles for each speaker
        profiles = []
        for speaker_id in speakers:
            profile = await self._load_profile(speaker_id)
            
            if profile:
                profiles.append(profile)
                
                # Add to participants with profile info
                participant_data = {
                    'id': profile.user_id,
                    'name': profile.name,
                    'email': profile.email,
                    'role': profile.role,
                    'department': profile.department,
                    'utterance_count': len([u for u in utterances if u.speaker_id == speaker_id])
                }
                
                # Check if not already in participants
                if not any(p.get('id') == profile.user_id for p in context.participants):
                    context.participants.append(participant_data)
        
        # Store profiles in metadata
        context.metadata['profiles'] = [p.to_dict() for p in profiles]
        
        # Analyze participant roles for meeting type inference
        if profiles:
            roles = [p.role for p in profiles if p.role]
            
            if any('manager' in r.lower() for r in roles if r):
                context.meeting_type = context.meeting_type or '1:1'
            elif any('engineer' in r.lower() for r in roles if r) and len(profiles) > 2:
                context.meeting_type = context.meeting_type or 'standup'
            elif any('product' in r.lower() for r in roles if r):
                context.meeting_type = context.meeting_type or 'planning'
        
        return context
    
    async def _load_profile(self, user_id: str) -> Optional[UserProfile]:
        """Load user profile from storage"""
        
        # Check cache
        if user_id in self.profile_cache:
            return self.profile_cache[user_id]
        
        # Try to load profile
        profile_file = self.profiles_dir / f"{user_id}.json"
        
        if profile_file.exists():
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                profile = UserProfile(
                    user_id=user_id,
                    name=profile_data.get('name', user_id),
                    email=profile_data.get('email'),
                    phone=profile_data.get('phone'),
                    role=profile_data.get('role'),
                    department=profile_data.get('department'),
                    preferences=profile_data.get('preferences', {}),
                    history_summary=profile_data.get('history_summary', {}),
                    voice_profile=profile_data.get('voice_profile'),
                    metadata=profile_data.get('metadata', {})
                )
                
                # Cache profile
                self.profile_cache[user_id] = profile
                
                return profile
            
            except Exception as e:
                logger.error(f"Error loading profile for {user_id}: {e}")
        
        # Create basic profile if not found
        profile = UserProfile(
            user_id=user_id,
            name=user_id,
            preferences={},
            history_summary={},
            metadata={'auto_created': True}
        )
        
        self.profile_cache[user_id] = profile
        
        return profile
    
    async def _enhance_with_history(
        self,
        context: ConversationContext,
        contact_id: str,
        entities: List[Entity]
    ) -> ConversationContext:
        """Enhance with historical context"""
        
        # Load recent memories for contact
        recent_memories = await self._load_recent_memories(contact_id, limit=10)
        
        if recent_memories:
            # Extract relevant topics
            topics = set()
            for memory in recent_memories:
                topics.update(memory.tags)
                topics.update(memory.keywords[:3])  # Top keywords
            
            context.metadata['recent_topics'] = list(topics)
            
            # Find related memories based on entities
            related_memories = []
            entity_values = {e.canonical_name.lower() for e in entities}
            
            for memory in recent_memories:
                # Check if memory mentions any current entities
                memory_text = memory.content.lower()
                
                if any(entity_val in memory_text for entity_val in entity_values):
                    related_memories.append({
                        'memory_id': memory.id,
                        'summary': memory.summary or memory.content[:100],
                        'timestamp': memory.timestamp.isoformat(),
                        'category': memory.category.value
                    })
            
            if related_memories:
                context.metadata['related_memories'] = related_memories[:5]  # Top 5
            
            # Track conversation continuity
            if recent_memories:
                last_memory = recent_memories[0]
                time_since_last = (datetime.now() - last_memory.timestamp).total_seconds() / 3600
                
                if time_since_last < 24:  # Within 24 hours
                    context.metadata['continuation'] = True
                    context.previous_meeting_id = last_memory.metadata.get('conversation_id')
        
        return context
    
    async def _load_recent_memories(
        self,
        contact_id: str,
        limit: int = 10
    ) -> List[Memory]:
        """Load recent memories for a contact"""
        
        # Check cache
        cache_key = f"{contact_id}:recent"
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key][:limit]
        
        memories = []
        contact_dir = self.base_dir / contact_id
        
        if contact_dir.exists():
            # Load metadata files
            metadata_files = list(contact_dir.glob("*_metadata.json"))
            
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        memories_data = json.load(f)
                    
                    for mem_data in memories_data:
                        # Convert to Memory object (simplified)
                        memory = Memory(
                            id=mem_data['id'],
                            content=mem_data['content'],
                            summary=mem_data.get('summary'),
                            category=MemoryCategory(mem_data['category']),
                            timestamp=datetime.fromisoformat(mem_data['timestamp']),
                            tags=mem_data.get('tags', []),
                            keywords=mem_data.get('keywords', []),
                            metadata=mem_data.get('metadata', {})
                        )
                        memories.append(memory)
                
                except Exception as e:
                    logger.error(f"Error loading memories from {metadata_file}: {e}")
            
            # Sort by timestamp (most recent first)
            memories.sort(key=lambda m: m.timestamp, reverse=True)
            
            # Cache results
            self.memory_cache[cache_key] = memories
        
        return memories[:limit]
    
    async def _enhance_with_documents(
        self,
        context: ConversationContext,
        entities: List[Entity],
        action_items: List[ActionItem]
    ) -> ConversationContext:
        """Enhance with related documents"""
        
        related_docs = []
        
        # Check for document references in entities
        from .schemas import EntityType
        for entity in entities:
            if entity.type == EntityType.URL:
                # Check if it's a document URL
                url = entity.value
                if any(ext in url.lower() for ext in ['.pdf', '.doc', '.docx', '.ppt', '.xls']):
                    related_docs.append({
                        'type': 'document',
                        'url': url,
                        'entity_id': entity.id,
                        'confidence': entity.confidence
                    })
            
            elif entity.type == EntityType.PRODUCT:
                # Could be a document or project name
                related_docs.append({
                    'type': 'product',
                    'name': entity.canonical_name,
                    'entity_id': entity.id,
                    'confidence': entity.confidence
                })
        
        # Check action items for document references
        for action in action_items:
            if 'document' in action.title.lower() or 'report' in action.title.lower():
                related_docs.append({
                    'type': 'action_document',
                    'title': action.title,
                    'action_id': action.id,
                    'due_date': action.due_date.isoformat() if action.due_date else None
                })
        
        if related_docs:
            context.related_documents = [doc['url'] if 'url' in doc else doc['name'] 
                                        for doc in related_docs[:5]]
            context.metadata['document_details'] = related_docs
        
        return context
    
    async def _apply_corrections(
        self,
        context: ConversationContext,
        entities: List[Entity]
    ) -> ConversationContext:
        """Apply organizational corrections and normalization"""
        
        # Load organization rules
        corrections = await self._load_org_corrections()
        
        # Apply to entities
        for entity in entities:
            # Normalize names
            if entity.canonical_name in corrections.get('name_corrections', {}):
                corrected = corrections['name_corrections'][entity.canonical_name]
                entity.aliases.append(entity.canonical_name)  # Keep original as alias
                entity.canonical_name = corrected
                entity.metadata['corrected'] = True
            
            # Apply department mappings
            from .schemas import EntityType
            if entity.type == EntityType.PERSON:
                for participant in context.participants:
                    if participant.get('name') == entity.canonical_name:
                        if entity.canonical_name in corrections.get('departments', {}):
                            participant['department'] = corrections['departments'][entity.canonical_name]
        
        # Apply meeting type corrections
        if context.meeting_title:
            title_lower = context.meeting_title.lower()
            
            for pattern, meeting_type in corrections.get('meeting_patterns', {}).items():
                if pattern.lower() in title_lower:
                    context.meeting_type = meeting_type
                    break
        
        return context
    
    async def _load_org_corrections(self) -> Dict[str, Any]:
        """Load organization-specific corrections"""
        
        corrections_file = self.profiles_dir / "org_corrections.json"
        
        if corrections_file.exists():
            try:
                with open(corrections_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading corrections: {e}")
        
        # Return default corrections
        return {
            'name_corrections': {},
            'departments': {},
            'meeting_patterns': {
                'standup': 'standup',
                'sync': 'sync',
                '1:1': '1:1',
                'review': 'review',
                'planning': 'planning',
                'retrospective': 'retrospective'
            }
        }
    
    def _calculate_context_confidence(self, context: ConversationContext) -> float:
        """Calculate overall context confidence"""
        
        confidence_factors = []
        
        # Calendar match confidence
        if 'calendar_event' in context.metadata:
            confidence_factors.append(0.9)
        
        # Profile match confidence
        if 'profiles' in context.metadata:
            profile_count = len(context.metadata['profiles'])
            participant_count = len(context.participants) if context.participants else 1
            confidence_factors.append(min(profile_count / participant_count, 1.0))
        
        # Meeting type confidence
        if context.meeting_type:
            confidence_factors.append(0.8)
        
        # Related memories confidence
        if 'related_memories' in context.metadata:
            confidence_factors.append(min(len(context.metadata['related_memories']) / 3, 1.0))
        
        # Calculate average
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        
        return 0.5  # Default confidence
    
    async def save_profile(self, profile: UserProfile) -> bool:
        """Save user profile to storage"""
        
        try:
            profile_file = self.profiles_dir / f"{profile.user_id}.json"
            
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, default=str)
            
            # Update cache
            self.profile_cache[profile.user_id] = profile
            
            logger.info(f"Saved profile for {profile.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return False
    
    async def save_calendar_event(self, event: CalendarEvent) -> bool:
        """Save calendar event to storage"""
        
        try:
            calendar_file = self.calendar_dir / "events.json"
            
            # Load existing events
            events = []
            if calendar_file.exists():
                with open(calendar_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            
            # Add or update event
            event_dict = event.to_dict()
            event_exists = False
            
            for i, existing in enumerate(events):
                if existing['id'] == event.event_id:
                    events[i] = event_dict
                    event_exists = True
                    break
            
            if not event_exists:
                events.append(event_dict)
            
            # Save back
            with open(calendar_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, default=str)
            
            # Update cache
            self.calendar_cache[event.event_id] = event
            
            logger.info(f"Saved calendar event {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving calendar event: {e}")
            return False
    
    def get_context_statistics(self, context: ConversationContext) -> Dict[str, Any]:
        """Get statistics about the enhanced context"""
        
        stats = {
            'has_calendar': 'calendar_event' in context.metadata,
            'participant_count': len(context.participants) if context.participants else 0,
            'has_profiles': 'profiles' in context.metadata,
            'profile_count': len(context.metadata.get('profiles', [])),
            'has_history': 'related_memories' in context.metadata,
            'related_memory_count': len(context.metadata.get('related_memories', [])),
            'document_count': len(context.related_documents) if context.related_documents else 0,
            'meeting_type': context.meeting_type,
            'duration_minutes': context.duration,
            'confidence': context.metadata.get('confidence', 0.0)
        }
        
        return stats