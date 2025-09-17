#!/usr/bin/env python3
"""
5-Slot Evolution System for Memory Management
Maintains top 5 memories per category with different criteria
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import hashlib
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class SlotMemory:
    """Memory entry for a slot"""
    content: str
    timestamp: datetime
    importance_score: float
    reference_count: int = 0
    memory_id: str = ""
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_accessed: Optional[datetime] = None
    action_required: bool = False
    action_details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'importance_score': self.importance_score,
            'reference_count': self.reference_count,
            'memory_id': self.memory_id,
            'source': self.source,
            'metadata': self.metadata,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'action_required': self.action_required,
            'action_details': self.action_details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlotMemory':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('last_accessed'):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)

@dataclass
class CategorySlots:
    """5-slot structure for each category"""
    slot1_recent: Optional[SlotMemory] = None  # Most Recent
    slot2_important: Optional[SlotMemory] = None  # Most Important
    slot3_referenced: Optional[SlotMemory] = None  # Most Referenced
    slot4_action: Optional[SlotMemory] = None  # Action Required
    slot5_summary: Optional[str] = None  # AI-generated summary/insight
    
    last_updated: datetime = field(default_factory=datetime.now)
    total_memories: int = 0
    category_insights: Dict[str, Any] = field(default_factory=dict)

class SlotEvolutionManager:
    """Manages the 5-slot evolution system for all categories"""
    
    def __init__(self, base_dir: str = 'app/memory_categories'):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.slots_file = self.base_dir / 'evolution_slots.json'
        self.memory_index = self.base_dir / 'memory_index.json'
        
        # Load existing slots
        self.category_slots = self._load_slots()
        self.reference_tracker = self._load_references()
        
        logger.info(f"🎯 Slot Evolution Manager initialized")
    
    def _load_slots(self) -> Dict[str, CategorySlots]:
        """Load existing slot data"""
        if self.slots_file.exists():
            try:
                with open(self.slots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    slots = {}
                    for category, slot_data in data.items():
                        slots[category] = self._deserialize_slots(slot_data)
                    return slots
            except Exception as e:
                logger.error(f"Error loading slots: {e}")
        return {}
    
    def _deserialize_slots(self, data: Dict) -> CategorySlots:
        """Deserialize slot data from JSON"""
        slots = CategorySlots()
        
        if data.get('slot1_recent'):
            slots.slot1_recent = SlotMemory.from_dict(data['slot1_recent'])
        if data.get('slot2_important'):
            slots.slot2_important = SlotMemory.from_dict(data['slot2_important'])
        if data.get('slot3_referenced'):
            slots.slot3_referenced = SlotMemory.from_dict(data['slot3_referenced'])
        if data.get('slot4_action'):
            slots.slot4_action = SlotMemory.from_dict(data['slot4_action'])
        
        slots.slot5_summary = data.get('slot5_summary')
        slots.last_updated = datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
        slots.total_memories = data.get('total_memories', 0)
        slots.category_insights = data.get('category_insights', {})
        
        return slots
    
    def _serialize_slots(self, slots: CategorySlots) -> Dict:
        """Serialize slot data for JSON"""
        return {
            'slot1_recent': slots.slot1_recent.to_dict() if slots.slot1_recent else None,
            'slot2_important': slots.slot2_important.to_dict() if slots.slot2_important else None,
            'slot3_referenced': slots.slot3_referenced.to_dict() if slots.slot3_referenced else None,
            'slot4_action': slots.slot4_action.to_dict() if slots.slot4_action else None,
            'slot5_summary': slots.slot5_summary,
            'last_updated': slots.last_updated.isoformat(),
            'total_memories': slots.total_memories,
            'category_insights': slots.category_insights
        }
    
    def _save_slots(self):
        """Save slots to file"""
        try:
            data = {}
            for category, slots in self.category_slots.items():
                data[category] = self._serialize_slots(slots)
            
            with open(self.slots_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Saved slots for {len(data)} categories")
        except Exception as e:
            logger.error(f"Error saving slots: {e}")
    
    def _load_references(self) -> Dict[str, int]:
        """Load reference count tracker"""
        if self.memory_index.exists():
            try:
                with open(self.memory_index, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('references', {})
            except Exception as e:
                logger.error(f"Error loading references: {e}")
        return defaultdict(int)
    
    def _save_references(self):
        """Save reference tracker"""
        try:
            data = {'references': dict(self.reference_tracker)}
            with open(self.memory_index, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving references: {e}")
    
    def evolve_slot(
        self,
        category: str,
        content: str,
        importance: float = 0.5,
        action_required: bool = False,
        action_details: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Process a new memory and evolve the category slots
        
        Args:
            category: Category name
            content: Memory content
            importance: Importance score (0-1)
            action_required: Whether action is needed
            action_details: Details of required action
            metadata: Additional metadata
            
        Returns:
            Memory ID
        """
        # Generate memory ID
        timestamp = datetime.now()
        memory_id = hashlib.md5(f"{timestamp.isoformat()}{content[:50]}".encode()).hexdigest()[:8]
        
        # Create new memory entry
        new_memory = SlotMemory(
            content=content,
            timestamp=timestamp,
            importance_score=importance,
            reference_count=0,
            memory_id=memory_id,
            source=metadata.get('source', 'unknown') if metadata else 'unknown',
            metadata=metadata or {},
            action_required=action_required,
            action_details=action_details
        )
        
        # Get or create category slots
        if category not in self.category_slots:
            self.category_slots[category] = CategorySlots()
        
        slots = self.category_slots[category]
        
        # Evolve Slot 1: Most Recent
        slots.slot1_recent = new_memory
        
        # Evolve Slot 2: Most Important
        if importance > 0.7:  # High importance threshold
            if not slots.slot2_important or importance > slots.slot2_important.importance_score:
                slots.slot2_important = new_memory
        
        # Evolve Slot 4: Action Required
        if action_required:
            if not slots.slot4_action or importance > slots.slot4_action.importance_score:
                slots.slot4_action = new_memory
        
        # Update metadata
        slots.total_memories += 1
        slots.last_updated = timestamp
        
        # Save changes
        self._save_slots()
        
        logger.info(f"Evolved slots for category '{category}' with memory {memory_id}")
        
        return memory_id
    
    def reference_memory(self, memory_id: str, category: Optional[str] = None):
        """
        Increment reference count for a memory
        
        Args:
            memory_id: Memory ID to reference
            category: Optional category hint
        """
        self.reference_tracker[memory_id] = self.reference_tracker.get(memory_id, 0) + 1
        count = self.reference_tracker[memory_id]
        
        # Update Slot 3: Most Referenced if count is high
        if count >= 3 and category:  # Threshold for "frequently referenced"
            if category in self.category_slots:
                slots = self.category_slots[category]
                
                # Check if this memory should be in slot 3
                if not slots.slot3_referenced or count > slots.slot3_referenced.reference_count:
                    # Find the memory in other slots
                    for slot in [slots.slot1_recent, slots.slot2_important, slots.slot4_action]:
                        if slot and slot.memory_id == memory_id:
                            slot.reference_count = count
                            slot.last_accessed = datetime.now()
                            slots.slot3_referenced = slot
                            break
        
        self._save_references()
        self._save_slots()
        
        logger.debug(f"Referenced memory {memory_id} (count: {count})")
    
    def update_summary(self, category: str, summary: str, insights: Optional[Dict] = None):
        """
        Update the AI-generated summary for a category (Slot 5)
        
        Args:
            category: Category name
            summary: Generated summary text
            insights: Optional insights dictionary
        """
        if category not in self.category_slots:
            self.category_slots[category] = CategorySlots()
        
        slots = self.category_slots[category]
        slots.slot5_summary = summary
        
        if insights:
            slots.category_insights.update(insights)
        
        slots.last_updated = datetime.now()
        
        self._save_slots()
        
        logger.info(f"Updated summary for category '{category}'")
    
    def get_category_slots(self, category: str) -> Optional[CategorySlots]:
        """Get slots for a specific category"""
        return self.category_slots.get(category)
    
    def get_all_slots(self) -> Dict[str, CategorySlots]:
        """Get all category slots"""
        return self.category_slots
    
    def get_slot_summary(self, category: str) -> Dict[str, Any]:
        """
        Get a summary of slots for a category
        
        Args:
            category: Category name
            
        Returns:
            Summary dictionary
        """
        if category not in self.category_slots:
            return {'error': f'Category {category} not found'}
        
        slots = self.category_slots[category]
        
        summary = {
            'category': category,
            'total_memories': slots.total_memories,
            'last_updated': slots.last_updated.isoformat(),
            'slots': {
                'slot1_recent': {
                    'content': slots.slot1_recent.content[:100] if slots.slot1_recent else None,
                    'timestamp': slots.slot1_recent.timestamp.isoformat() if slots.slot1_recent else None
                },
                'slot2_important': {
                    'content': slots.slot2_important.content[:100] if slots.slot2_important else None,
                    'importance': slots.slot2_important.importance_score if slots.slot2_important else None
                },
                'slot3_referenced': {
                    'content': slots.slot3_referenced.content[:100] if slots.slot3_referenced else None,
                    'references': slots.slot3_referenced.reference_count if slots.slot3_referenced else None
                },
                'slot4_action': {
                    'content': slots.slot4_action.content[:100] if slots.slot4_action else None,
                    'action': slots.slot4_action.action_details if slots.slot4_action else None
                },
                'slot5_summary': slots.slot5_summary[:200] if slots.slot5_summary else None
            },
            'insights': slots.category_insights
        }
        
        return summary
    
    def update_slot_md_file(self, category: str, category_file: Path):
        """
        Update the MD file with current slot information
        
        Args:
            category: Category name
            category_file: Path to category MD file
        """
        if category not in self.category_slots:
            return
        
        slots = self.category_slots[category]
        
        # Read current file
        if category_file.exists():
            with open(category_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        else:
            lines = []
        
        # Find slot section
        slot_start = -1
        slot_end = -1
        for i, line in enumerate(lines):
            if '## 📊 Evolution Slots' in line:
                slot_start = i
            elif slot_start > -1 and line.startswith('## ') and i > slot_start:
                slot_end = i
                break
        
        if slot_end == -1:
            slot_end = len(lines)
        
        # Generate new slot content
        slot_content = ['## 📊 Evolution Slots\n', '\n']
        
        # Slot 1: Most Recent
        slot_content.append('### Slot 1: Most Recent\n')
        if slots.slot1_recent:
            slot_content.append(f"**ID:** {slots.slot1_recent.memory_id}\n")
            slot_content.append(f"**Time:** {slots.slot1_recent.timestamp.strftime('%Y-%m-%d %H:%M')}\n")
            slot_content.append(f"```\n{slots.slot1_recent.content[:200]}{'...' if len(slots.slot1_recent.content) > 200 else ''}\n```\n")
        else:
            slot_content.append('_Empty_\n')
        slot_content.append('\n')
        
        # Slot 2: Most Important
        slot_content.append('### Slot 2: Most Important\n')
        if slots.slot2_important:
            slot_content.append(f"**Importance:** {slots.slot2_important.importance_score:.2f}\n")
            slot_content.append(f"```\n{slots.slot2_important.content[:200]}{'...' if len(slots.slot2_important.content) > 200 else ''}\n```\n")
        else:
            slot_content.append('_Empty_\n')
        slot_content.append('\n')
        
        # Slot 3: Most Referenced
        slot_content.append('### Slot 3: Most Referenced\n')
        if slots.slot3_referenced:
            slot_content.append(f"**References:** {slots.slot3_referenced.reference_count}\n")
            slot_content.append(f"```\n{slots.slot3_referenced.content[:200]}{'...' if len(slots.slot3_referenced.content) > 200 else ''}\n```\n")
        else:
            slot_content.append('_Empty_\n')
        slot_content.append('\n')
        
        # Slot 4: Action Required
        slot_content.append('### Slot 4: Action Required\n')
        if slots.slot4_action:
            slot_content.append(f"**Action:** {slots.slot4_action.action_details or 'Pending'}\n")
            slot_content.append(f"```\n{slots.slot4_action.content[:200]}{'...' if len(slots.slot4_action.content) > 200 else ''}\n```\n")
        else:
            slot_content.append('_Empty_\n')
        slot_content.append('\n')
        
        # Slot 5: Summary/Insight
        slot_content.append('### Slot 5: Summary/Insight\n')
        if slots.slot5_summary:
            slot_content.append(f"{slots.slot5_summary}\n")
        else:
            slot_content.append('_Empty_\n')
        slot_content.append('\n')
        
        slot_content.append('---\n\n')
        
        # Replace slot section in file
        if slot_start > -1:
            new_lines = lines[:slot_start] + slot_content
            if slot_end < len(lines):
                new_lines.extend(lines[slot_end:])
        else:
            # Add slot section after header
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('---'):
                    header_end = i + 1
                    break
            
            new_lines = lines[:header_end] + ['\n'] + slot_content + lines[header_end:]
        
        # Write updated file
        with open(category_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        logger.debug(f"Updated MD file for category '{category}'")