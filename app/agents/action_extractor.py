#!/usr/bin/env python3
"""
Action Item Intelligence System for Circleback-style MD Agent
Extracts action items with assignees, dependencies, and priorities
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
import json

# Import schemas
from .schemas import ActionItem, ActionPriority, ActionStatus, Utterance, Entity, EntityType

# Setup logging
logger = logging.getLogger(__name__)

class ActionExtractor:
    """
    Advanced action item extraction with dependency tracking and priority scoring
    """
    
    # Action patterns for detection
    ACTION_PATTERNS = {
        'direct_action': [
            r'\b(?:i|we|you)\s+(?:need to|should|must|have to|got to|gotta)\s+([^.!?]+)',
            r'\b(?:please|kindly|could you|can you|will you)\s+([^.!?]+)',
            r'\b(?:make sure|ensure|remember) (?:to|that)\s+([^.!?]+)'
        ],
        'commitment': [
            r'\b(?:i|we)(?:\'ll| will)\s+([^.!?]+)',
            r'\b(?:i am|we are|i\'m|we\'re)\s+(?:going to|gonna)\s+([^.!?]+)',
            r'\b(?:let me|i can|i\'ll)\s+([^.!?]+)'
        ],
        'task': [
            r'\b(?:action item|todo|task|to-do):\s*([^.!?\n]+)',
            r'\[\s*(?:todo|task|action)\s*\]\s*([^.!?\n]+)',
            r'(?:^|\n)\s*[-*•]\s*([^.!?\n]+)'  # Bullet points
        ],
        'assignment': [
            r'([^.!?]+)\s+(?:is|are)\s+(?:assigned to|responsible for)\s+([^.!?]+)',
            r'([A-Z][a-z]+)\s+(?:will|should|must)\s+([^.!?]+)',
            r'(?:assign|delegate)\s+([^.!?]+)\s+to\s+([A-Z][a-z]+)'
        ],
        'deadline': [
            r'([^.!?]+)\s+(?:by|before|until|due)\s+((?:tomorrow|today|next\s+\w+|\d{1,2}[/-]\d{1,2}))',
            r'(?:deadline|due date)(?:\s+is)?\s*:?\s*([^.!?\n]+)'
        ]
    }
    
    # Priority keywords
    PRIORITY_KEYWORDS = {
        ActionPriority.CRITICAL: ['critical', 'urgent', 'asap', 'immediately', 'emergency', 'blocker'],
        ActionPriority.HIGH: ['important', 'high priority', 'soon', 'priority', 'quickly'],
        ActionPriority.MEDIUM: ['normal', 'standard', 'regular', 'when you can'],
        ActionPriority.LOW: ['low priority', 'nice to have', 'optional', 'if time permits'],
        ActionPriority.OPTIONAL: ['maybe', 'consider', 'think about', 'explore']
    }
    
    # Status keywords
    STATUS_KEYWORDS = {
        ActionStatus.COMPLETED: ['done', 'completed', 'finished', 'resolved', 'closed'],
        ActionStatus.IN_PROGRESS: ['working on', 'in progress', 'started', 'ongoing'],
        ActionStatus.BLOCKED: ['blocked', 'waiting', 'depends on', 'need', 'stuck'],
        ActionStatus.CANCELLED: ['cancelled', 'no longer needed', 'skip', 'ignore'],
        ActionStatus.DEFERRED: ['later', 'postponed', 'deferred', 'next quarter']
    }
    
    def __init__(self):
        """Initialize the action extractor"""
        self.action_cache: Dict[str, ActionItem] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        logger.info("📋 Action Extractor initialized")
    
    async def extract_actions(
        self,
        utterances: List[Utterance],
        entities: Optional[List[Entity]] = None
    ) -> List[ActionItem]:
        """
        Extract action items from utterances
        
        Args:
            utterances: List of utterances to process
            entities: Optional entities for assignment resolution
            
        Returns:
            List of extracted action items
        """
        actions = []
        
        # Clear cache for new processing
        self.action_cache.clear()
        self.dependency_graph.clear()
        
        # Extract actions from each utterance
        for utterance in utterances:
            utt_actions = await self._extract_from_utterance(utterance, entities)
            
            # Add utterance ID to actions
            for action in utt_actions:
                if utterance.id not in action.utterance_ids:
                    action.utterance_ids.append(utterance.id)
            
            actions.extend(utt_actions)
        
        # Merge duplicate actions
        merged_actions = self._merge_actions(actions)
        
        # Extract dependencies
        merged_actions = await self._extract_dependencies(merged_actions, utterances)
        
        # Resolve assignees using entities
        if entities:
            merged_actions = await self._resolve_assignees(merged_actions, entities)
        
        # Calculate priorities
        merged_actions = await self._calculate_priorities(merged_actions, utterances)
        
        # Update statuses based on conversation
        merged_actions = await self._update_statuses(merged_actions, utterances)
        
        logger.info(f"Extracted {len(merged_actions)} action items")
        
        return merged_actions
    
    async def _extract_from_utterance(
        self,
        utterance: Utterance,
        entities: Optional[List[Entity]] = None
    ) -> List[ActionItem]:
        """
        Extract actions from a single utterance
        """
        actions = []
        text = utterance.text
        
        # Direct action patterns
        for pattern_type, patterns in self.ACTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    # Extract action text based on pattern type
                    if pattern_type == 'assignment':
                        # Special handling for assignment patterns
                        if len(match.groups()) >= 2:
                            action_text = match.group(1)
                            assignee_text = match.group(2) if len(match.groups()) > 1 else None
                        else:
                            action_text = match.group(0)
                            assignee_text = None
                    else:
                        action_text = match.group(1) if match.groups() else match.group(0)
                        assignee_text = None
                    
                    # Clean up action text
                    action_text = action_text.strip()
                    if len(action_text) < 5 or len(action_text) > 500:
                        continue  # Skip too short or too long
                    
                    # Check cache
                    cache_key = f"{utterance.speaker_id}:{action_text[:50]}"
                    if cache_key in self.action_cache:
                        actions.append(self.action_cache[cache_key])
                        continue
                    
                    # Create action item
                    action = ActionItem(
                        title=self._clean_action_title(action_text),
                        description=text[max(0, match.start()-50):min(len(text), match.end()+50)],
                        owner=utterance.speaker_id,
                        created_at=utterance.timestamp,
                        updated_at=utterance.timestamp,
                        metadata={
                            'pattern_type': pattern_type,
                            'pattern': pattern,
                            'confidence': self._get_pattern_confidence(pattern_type)
                        }
                    )
                    
                    # Set assignee if extracted
                    if assignee_text:
                        action.assignee = assignee_text.strip()
                    elif pattern_type == 'commitment':
                        # Self-assignment for commitments
                        action.assignee = utterance.speaker_id
                    
                    # Extract due date if present
                    due_date = self._extract_due_date(text[match.start():match.end()+100])
                    if due_date:
                        action.due_date = due_date
                    
                    self.action_cache[cache_key] = action
                    actions.append(action)
        
        return actions
    
    def _clean_action_title(self, text: str) -> str:
        """Clean and format action title"""
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        # Remove trailing punctuation
        text = re.sub(r'[.!?,;]+$', '', text)
        
        # Limit length
        if len(text) > 200:
            text = text[:197] + '...'
        
        return text
    
    def _get_pattern_confidence(self, pattern_type: str) -> float:
        """Get confidence score based on pattern type"""
        confidence_map = {
            'direct_action': 0.85,
            'commitment': 0.80,
            'task': 0.90,
            'assignment': 0.75,
            'deadline': 0.70
        }
        return confidence_map.get(pattern_type, 0.5)
    
    def _extract_due_date(self, text: str) -> Optional[datetime]:
        """Extract due date from text"""
        text_lower = text.lower()
        today = datetime.now()
        
        # Relative date patterns
        if 'today' in text_lower:
            return today.replace(hour=23, minute=59, second=59)
        elif 'tomorrow' in text_lower:
            return (today + timedelta(days=1)).replace(hour=23, minute=59, second=59)
        elif 'next week' in text_lower:
            return (today + timedelta(weeks=1)).replace(hour=23, minute=59, second=59)
        elif 'next month' in text_lower:
            return (today + timedelta(days=30)).replace(hour=23, minute=59, second=59)
        
        # Day of week patterns
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            if day in text_lower:
                current_day = today.weekday()
                days_ahead = (i - current_day) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next occurrence
                return (today + timedelta(days=days_ahead)).replace(hour=23, minute=59, second=59)
        
        # Explicit date patterns
        date_pattern = r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?'
        match = re.search(date_pattern, text)
        if match:
            try:
                month = int(match.group(1))
                day = int(match.group(2))
                year = int(match.group(3)) if match.group(3) else today.year
                
                # Handle 2-digit year
                if year < 100:
                    year += 2000
                
                return datetime(year, month, day, 23, 59, 59)
            except:
                pass
        
        return None
    
    def _merge_actions(self, actions: List[ActionItem]) -> List[ActionItem]:
        """Merge duplicate action items"""
        merged = {}
        
        for action in actions:
            # Create merge key based on title similarity
            key = self._get_merge_key(action.title)
            
            if key in merged:
                # Merge with existing
                existing = merged[key]
                
                # Combine utterance IDs
                existing.utterance_ids.extend(action.utterance_ids)
                existing.utterance_ids = list(set(existing.utterance_ids))
                
                # Update dates if newer
                if action.due_date and (not existing.due_date or action.due_date < existing.due_date):
                    existing.due_date = action.due_date
                
                # Keep higher priority
                if self._priority_value(action.priority) > self._priority_value(existing.priority):
                    existing.priority = action.priority
                
                # Update assignee if not set
                if action.assignee and not existing.assignee:
                    existing.assignee = action.assignee
                
                # Merge tags
                existing.tags = list(set(existing.tags + action.tags))
                
                # Update confidence
                if 'confidence' in action.metadata and 'confidence' in existing.metadata:
                    existing.metadata['confidence'] = max(
                        existing.metadata['confidence'],
                        action.metadata['confidence']
                    )
            else:
                merged[key] = action
        
        return list(merged.values())
    
    def _get_merge_key(self, title: str) -> str:
        """Generate merge key for action title"""
        # Simple key: lowercase, remove common words
        stopwords = {'the', 'a', 'an', 'to', 'for', 'of', 'with', 'and', 'or'}
        words = title.lower().split()
        key_words = [w for w in words if w not in stopwords]
        return ' '.join(key_words[:5])  # Use first 5 meaningful words
    
    def _priority_value(self, priority: ActionPriority) -> int:
        """Get numeric value for priority"""
        priority_values = {
            ActionPriority.CRITICAL: 5,
            ActionPriority.HIGH: 4,
            ActionPriority.MEDIUM: 3,
            ActionPriority.LOW: 2,
            ActionPriority.OPTIONAL: 1
        }
        return priority_values.get(priority, 3)
    
    async def _extract_dependencies(
        self,
        actions: List[ActionItem],
        utterances: List[Utterance]
    ) -> List[ActionItem]:
        """Extract dependencies between actions"""
        
        # Build action map
        action_map = {action.id: action for action in actions}
        
        # Analyze utterances for dependency patterns
        dependency_patterns = [
            r'(?:after|once|when)\s+(.+?)\s+(?:is done|is complete|finishes)',
            r'(?:depends on|requires|needs)\s+(.+)',
            r'(?:blocked by|waiting for)\s+(.+)',
            r'(?:first|before that|prior to)\s+(.+)'
        ]
        
        for utterance in utterances:
            text = utterance.text.lower()
            
            for pattern in dependency_patterns:
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    dependency_text = match.group(1)
                    
                    # Find matching actions
                    dependent_action = None
                    blocking_action = None
                    
                    for action in actions:
                        if any(uid == utterance.id for uid in action.utterance_ids):
                            dependent_action = action
                        
                        # Simple text matching for blocking action
                        if dependency_text in action.title.lower():
                            blocking_action = action
                    
                    # Create dependency
                    if dependent_action and blocking_action and dependent_action.id != blocking_action.id:
                        if blocking_action.id not in dependent_action.dependencies:
                            dependent_action.dependencies.append(blocking_action.id)
                        
                        # Update dependency graph
                        if dependent_action.id not in self.dependency_graph:
                            self.dependency_graph[dependent_action.id] = set()
                        self.dependency_graph[dependent_action.id].add(blocking_action.id)
        
        # Detect circular dependencies
        for action in actions:
            if self._has_circular_dependency(action.id):
                logger.warning(f"Circular dependency detected for action: {action.title}")
                action.metadata['has_circular_dependency'] = True
        
        return actions
    
    def _has_circular_dependency(self, action_id: str, visited: Optional[Set[str]] = None) -> bool:
        """Check for circular dependencies"""
        if visited is None:
            visited = set()
        
        if action_id in visited:
            return True
        
        visited.add(action_id)
        
        if action_id in self.dependency_graph:
            for dep_id in self.dependency_graph[action_id]:
                if self._has_circular_dependency(dep_id, visited.copy()):
                    return True
        
        return False
    
    async def _resolve_assignees(
        self,
        actions: List[ActionItem],
        entities: List[Entity]
    ) -> List[ActionItem]:
        """Resolve assignees using extracted entities"""
        
        # Build person entity map
        person_entities = {}
        for entity in entities:
            if entity.type == EntityType.PERSON:
                # Create multiple keys for matching
                person_entities[entity.value.lower()] = entity
                person_entities[entity.canonical_name.lower()] = entity
                for alias in entity.aliases:
                    person_entities[alias.lower()] = entity
        
        for action in actions:
            # Try to resolve assignee if it's text
            if action.assignee and isinstance(action.assignee, str):
                assignee_lower = action.assignee.lower()
                
                # Direct match
                if assignee_lower in person_entities:
                    entity = person_entities[assignee_lower]
                    action.assignee = entity.canonical_name
                    action.metadata['assignee_entity_id'] = entity.id
                    action.metadata['assignee_confidence'] = entity.confidence
                else:
                    # Partial match
                    for key, entity in person_entities.items():
                        if key in assignee_lower or assignee_lower in key:
                            action.assignee = entity.canonical_name
                            action.metadata['assignee_entity_id'] = entity.id
                            action.metadata['assignee_confidence'] = entity.confidence * 0.8
                            break
        
        return actions
    
    async def _calculate_priorities(
        self,
        actions: List[ActionItem],
        utterances: List[Utterance]
    ) -> List[ActionItem]:
        """Calculate action priorities based on context"""
        
        # Build utterance map
        utterance_map = {u.id: u for u in utterances}
        
        for action in actions:
            # Get relevant utterances
            relevant_texts = []
            for uid in action.utterance_ids:
                if uid in utterance_map:
                    relevant_texts.append(utterance_map[uid].text.lower())
            
            combined_text = ' '.join(relevant_texts)
            
            # Check for priority keywords
            priority_score = 3  # Default medium
            
            for priority, keywords in self.PRIORITY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in combined_text:
                        priority_score = self._priority_value(priority)
                        action.priority = priority
                        break
            
            # Adjust based on due date
            if action.due_date:
                days_until = (action.due_date - datetime.now()).days
                if days_until < 1:
                    priority_score = max(priority_score, 4)  # At least high
                elif days_until < 3:
                    priority_score = max(priority_score, 3)  # At least medium
            
            # Adjust based on dependencies
            if action.blockers:
                priority_score = min(priority_score, 3)  # Cap at medium if blocked
            
            # Set final priority
            if priority_score >= 5:
                action.priority = ActionPriority.CRITICAL
            elif priority_score >= 4:
                action.priority = ActionPriority.HIGH
            elif priority_score >= 3:
                action.priority = ActionPriority.MEDIUM
            elif priority_score >= 2:
                action.priority = ActionPriority.LOW
            else:
                action.priority = ActionPriority.OPTIONAL
            
            action.metadata['priority_score'] = priority_score
        
        return actions
    
    async def _update_statuses(
        self,
        actions: List[ActionItem],
        utterances: List[Utterance]
    ) -> List[ActionItem]:
        """Update action statuses based on conversation"""
        
        # Build utterance map
        utterance_map = {u.id: u for u in utterances}
        
        for action in actions:
            # Get utterances after action creation
            creation_time = action.created_at
            later_utterances = [
                u for u in utterances
                if u.timestamp > creation_time
            ]
            
            # Check for status updates
            for utterance in later_utterances:
                text_lower = utterance.text.lower()
                
                # Look for action title in utterance
                if action.title.lower() in text_lower or any(
                    word in text_lower 
                    for word in action.title.lower().split()[:3]
                ):
                    # Check status keywords
                    for status, keywords in self.STATUS_KEYWORDS.items():
                        for keyword in keywords:
                            if keyword in text_lower:
                                action.status = status
                                action.updated_at = utterance.timestamp
                                
                                if status == ActionStatus.COMPLETED:
                                    action.completed_at = utterance.timestamp
                                
                                # Add status update to metadata
                                if 'status_updates' not in action.metadata:
                                    action.metadata['status_updates'] = []
                                
                                action.metadata['status_updates'].append({
                                    'status': status.value,
                                    'timestamp': utterance.timestamp.isoformat(),
                                    'utterance_id': utterance.id,
                                    'updated_by': utterance.speaker_id
                                })
                                
                                break
            
            # Identify blockers
            if action.dependencies:
                blocking_actions = [
                    a for a in actions
                    if a.id in action.dependencies and a.status != ActionStatus.COMPLETED
                ]
                
                if blocking_actions:
                    action.blockers = [a.id for a in blocking_actions]
                    if action.status == ActionStatus.PENDING:
                        action.status = ActionStatus.BLOCKED
        
        return actions
    
    def get_action_statistics(self, actions: List[ActionItem]) -> Dict[str, Any]:
        """Get statistics about extracted actions"""
        stats = {
            'total_actions': len(actions),
            'by_status': {},
            'by_priority': {},
            'with_assignee': 0,
            'with_due_date': 0,
            'with_dependencies': 0,
            'overdue': 0,
            'completion_rate': 0.0
        }
        
        now = datetime.now()
        completed_count = 0
        
        for action in actions:
            # Status counts
            status = action.status.value
            if status not in stats['by_status']:
                stats['by_status'][status] = 0
            stats['by_status'][status] += 1
            
            if action.status == ActionStatus.COMPLETED:
                completed_count += 1
            
            # Priority counts
            priority = action.priority.value
            if priority not in stats['by_priority']:
                stats['by_priority'][priority] = 0
            stats['by_priority'][priority] += 1
            
            # Other metrics
            if action.assignee:
                stats['with_assignee'] += 1
            
            if action.due_date:
                stats['with_due_date'] += 1
                if action.due_date < now and action.status != ActionStatus.COMPLETED:
                    stats['overdue'] += 1
            
            if action.dependencies:
                stats['with_dependencies'] += 1
        
        # Calculate completion rate
        if actions:
            stats['completion_rate'] = completed_count / len(actions)
        
        return stats
    
    async def generate_action_report(self, actions: List[ActionItem]) -> str:
        """Generate a formatted action report"""
        report_lines = ["# Action Items Report\n"]
        
        # Group by status
        by_status = {}
        for action in actions:
            status = action.status.value
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(action)
        
        # Report sections
        status_order = [
            ActionStatus.PENDING,
            ActionStatus.IN_PROGRESS,
            ActionStatus.BLOCKED,
            ActionStatus.COMPLETED,
            ActionStatus.CANCELLED,
            ActionStatus.DEFERRED
        ]
        
        for status in status_order:
            if status.value in by_status:
                status_actions = by_status[status.value]
                report_lines.append(f"\n## {status.value.replace('_', ' ').title()} ({len(status_actions)})\n")
                
                # Sort by priority
                status_actions.sort(key=lambda a: self._priority_value(a.priority), reverse=True)
                
                for action in status_actions:
                    # Format action
                    priority_emoji = {
                        ActionPriority.CRITICAL: "🔴",
                        ActionPriority.HIGH: "🟠",
                        ActionPriority.MEDIUM: "🟡",
                        ActionPriority.LOW: "🟢",
                        ActionPriority.OPTIONAL: "⚪"
                    }.get(action.priority, "⚪")
                    
                    report_lines.append(f"### {priority_emoji} {action.title}")
                    
                    if action.assignee:
                        report_lines.append(f"**Assignee:** {action.assignee}")
                    
                    if action.due_date:
                        due_str = action.due_date.strftime("%Y-%m-%d")
                        if action.due_date < datetime.now():
                            report_lines.append(f"**Due:** ⚠️ {due_str} (OVERDUE)")
                        else:
                            report_lines.append(f"**Due:** {due_str}")
                    
                    if action.dependencies:
                        report_lines.append(f"**Dependencies:** {len(action.dependencies)} items")
                    
                    if action.blockers:
                        report_lines.append(f"**Blockers:** {len(action.blockers)} items")
                    
                    report_lines.append("")  # Empty line
        
        # Statistics
        stats = self.get_action_statistics(actions)
        report_lines.append("\n## Statistics\n")
        report_lines.append(f"- Total Actions: {stats['total_actions']}")
        report_lines.append(f"- Completion Rate: {stats['completion_rate']:.1%}")
        report_lines.append(f"- Overdue: {stats['overdue']}")
        report_lines.append(f"- With Dependencies: {stats['with_dependencies']}")
        
        return '\n'.join(report_lines)