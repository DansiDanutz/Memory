#!/usr/bin/env python3
"""
Category Manager - Expanded Semantic Category System
Manages 20+ semantic categories with dedicated MD files and evolution tracking
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import hashlib

logger = logging.getLogger(__name__)

class SemanticCategory(str, Enum):
    """Expanded semantic categories for better memory organization"""
    # Core Life Areas
    WORK = "work"
    PERSONAL = "personal"
    FINANCE = "finance"
    HEALTH = "health"
    EDUCATION = "education"
    TRAVEL = "travel"
    SHOPPING = "shopping"
    RELATIONSHIPS = "relationships"
    
    # Creative & Intellectual
    IDEAS = "ideas"
    GOALS = "goals"
    HABITS = "habits"
    SKILLS = "skills"
    PROJECTS = "projects"
    BOOKS = "books"
    MOVIES = "movies"
    MUSIC = "music"
    
    # Lifestyle & Personal Growth
    FOOD = "food"
    HOBBIES = "hobbies"
    DREAMS = "dreams"
    QUOTES = "quotes"
    LESSONS = "lessons"
    
    # Social & Professional
    CONTACTS = "contacts"
    EVENTS = "events"
    ACHIEVEMENTS = "achievements"
    CHALLENGES = "challenges"
    
    # Additional Categories
    TECHNOLOGY = "technology"
    SPORTS = "sports"
    POLITICS = "politics"
    SPIRITUALITY = "spirituality"
    MEMORIES = "memories"
    
    # Default fallback
    GENERAL = "general"

@dataclass
class CategoryMetadata:
    """Metadata for each category"""
    name: str
    description: str
    retention_days: int  # How long to keep memories
    importance_threshold: float  # Minimum importance to keep
    max_slots: int = 5
    auto_archive: bool = True
    keywords: List[str] = field(default_factory=list)
    
CATEGORY_CONFIGS = {
    SemanticCategory.FINANCE: CategoryMetadata(
        name="Finance",
        description="Financial records, transactions, investments",
        retention_days=2555,  # 7 years
        importance_threshold=0.2,
        keywords=["money", "payment", "investment", "salary", "expense", "budget", "tax"]
    ),
    SemanticCategory.HEALTH: CategoryMetadata(
        name="Health",
        description="Medical records, fitness, wellness",
        retention_days=1825,  # 5 years
        importance_threshold=0.3,
        keywords=["doctor", "medicine", "health", "fitness", "symptom", "treatment", "diagnosis"]
    ),
    SemanticCategory.PERSONAL: CategoryMetadata(
        name="Personal",
        description="Personal memories and experiences",
        retention_days=365,  # 1 year
        importance_threshold=0.4,
        keywords=["family", "friend", "birthday", "anniversary", "personal"]
    ),
    SemanticCategory.WORK: CategoryMetadata(
        name="Work",
        description="Professional activities and projects",
        retention_days=180,  # 6 months
        importance_threshold=0.5,
        keywords=["work", "job", "meeting", "project", "colleague", "office", "client"]
    ),
    SemanticCategory.EDUCATION: CategoryMetadata(
        name="Education",
        description="Learning, courses, certifications",
        retention_days=730,  # 2 years
        importance_threshold=0.4,
        keywords=["learn", "course", "study", "exam", "degree", "certificate", "training"]
    ),
    SemanticCategory.TRAVEL: CategoryMetadata(
        name="Travel",
        description="Trips, vacations, destinations",
        retention_days=365,
        importance_threshold=0.3,
        keywords=["travel", "trip", "vacation", "flight", "hotel", "destination", "journey"]
    ),
    SemanticCategory.RELATIONSHIPS: CategoryMetadata(
        name="Relationships",
        description="Social connections and interactions",
        retention_days=365,
        importance_threshold=0.4,
        keywords=["relationship", "partner", "spouse", "dating", "marriage", "friendship"]
    ),
    SemanticCategory.GOALS: CategoryMetadata(
        name="Goals",
        description="Aspirations and objectives",
        retention_days=365,
        importance_threshold=0.6,
        keywords=["goal", "objective", "target", "aspiration", "ambition", "plan", "future"]
    ),
    SemanticCategory.IDEAS: CategoryMetadata(
        name="Ideas",
        description="Creative thoughts and innovations",
        retention_days=180,
        importance_threshold=0.5,
        keywords=["idea", "thought", "concept", "innovation", "brainstorm", "creative"]
    ),
    SemanticCategory.PROJECTS: CategoryMetadata(
        name="Projects",
        description="Ongoing and completed projects",
        retention_days=365,
        importance_threshold=0.5,
        keywords=["project", "task", "milestone", "deadline", "deliverable", "assignment"]
    ),
    SemanticCategory.HABITS: CategoryMetadata(
        name="Habits",
        description="Routines and behavioral patterns",
        retention_days=90,
        importance_threshold=0.4,
        keywords=["habit", "routine", "daily", "weekly", "practice", "behavior"]
    ),
    SemanticCategory.SKILLS: CategoryMetadata(
        name="Skills",
        description="Abilities and competencies",
        retention_days=730,
        importance_threshold=0.5,
        keywords=["skill", "ability", "expertise", "competency", "proficiency", "talent"]
    ),
    SemanticCategory.EVENTS: CategoryMetadata(
        name="Events",
        description="Important occasions and gatherings",
        retention_days=180,
        importance_threshold=0.4,
        keywords=["event", "party", "celebration", "conference", "wedding", "meeting", "gathering"]
    ),
    SemanticCategory.ACHIEVEMENTS: CategoryMetadata(
        name="Achievements",
        description="Accomplishments and successes",
        retention_days=1095,  # 3 years
        importance_threshold=0.6,
        keywords=["achievement", "success", "accomplishment", "award", "recognition", "milestone"]
    ),
    SemanticCategory.CHALLENGES: CategoryMetadata(
        name="Challenges",
        description="Difficulties and obstacles",
        retention_days=180,
        importance_threshold=0.5,
        keywords=["challenge", "problem", "issue", "difficulty", "obstacle", "struggle"]
    ),
    # Default for others
    SemanticCategory.GENERAL: CategoryMetadata(
        name="General",
        description="Uncategorized memories",
        retention_days=90,  # 3 months default
        importance_threshold=0.3,
        keywords=[]
    )
}

# Apply default config to categories not explicitly configured
for category in SemanticCategory:
    if category not in CATEGORY_CONFIGS:
        CATEGORY_CONFIGS[category] = CategoryMetadata(
            name=category.value.title(),
            description=f"{category.value.title()} related memories",
            retention_days=90,
            importance_threshold=0.3,
            keywords=[category.value]
        )

class CategoryManager:
    """Manages semantic categories and their MD files"""
    
    def __init__(self, base_dir: str = 'app/memory_categories'):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize category directories and files
        self._initialize_categories()
        
        # Category statistics
        self.stats = {
            'total_memories': 0,
            'memories_per_category': {},
            'last_updated': {},
            'importance_scores': {}
        }
        
        logger.info(f"📁 Category Manager initialized with {len(SemanticCategory)} categories")
    
    def _initialize_categories(self):
        """Initialize category directories and MD files"""
        for category in SemanticCategory:
            category_dir = self.base_dir / category.value
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Create main category MD file if doesn't exist
            category_file = category_dir / f"{category.value}.md"
            if not category_file.exists():
                config = CATEGORY_CONFIGS[category]
                header = f"""# {config.name} Category

**Description:** {config.description}
**Retention Policy:** {config.retention_days} days
**Importance Threshold:** {config.importance_threshold}
**Keywords:** {', '.join(config.keywords)}

---

## 📊 Evolution Slots

### Slot 1: Most Recent
_Empty_

### Slot 2: Most Important
_Empty_

### Slot 3: Most Referenced
_Empty_

### Slot 4: Action Required
_Empty_

### Slot 5: Summary/Insight
_Empty_

---

## 📝 Historical Memories

"""
                category_file.write_text(header, encoding='utf-8')
                logger.info(f"Created category file: {category_file}")
    
    def categorize_memory(self, content: str, metadata: Optional[Dict] = None) -> SemanticCategory:
        """
        Determine the best category for a memory based on content and keywords
        
        Args:
            content: Memory content
            metadata: Optional metadata with hints
            
        Returns:
            Best matching semantic category
        """
        content_lower = content.lower()
        
        # Check for explicit category in metadata
        if metadata and 'category' in metadata:
            try:
                return SemanticCategory(metadata['category'])
            except ValueError:
                pass
        
        # Score each category based on keyword matches
        category_scores = {}
        
        for category, config in CATEGORY_CONFIGS.items():
            score = 0
            for keyword in config.keywords:
                if keyword.lower() in content_lower:
                    score += 1
            
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, or GENERAL if no matches
        if category_scores:
            best_category = max(category_scores.keys(), key=lambda k: category_scores[k])
            logger.debug(f"Categorized memory as {best_category.value} (score: {category_scores[best_category]})")
            return best_category
        
        return SemanticCategory.GENERAL
    
    def get_category_file(self, category: SemanticCategory) -> Path:
        """Get the MD file path for a category"""
        return self.base_dir / category.value / f"{category.value}.md"
    
    def get_category_config(self, category: SemanticCategory) -> CategoryMetadata:
        """Get configuration for a category"""
        return CATEGORY_CONFIGS[category]
    
    def add_memory_to_category(
        self,
        category: SemanticCategory,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a memory to a category file
        
        Args:
            category: Target category
            content: Memory content
            importance: Importance score (0-1)
            metadata: Additional metadata
            
        Returns:
            Memory ID
        """
        timestamp = datetime.now()
        memory_id = hashlib.md5(f"{timestamp.isoformat()}{content[:50]}".encode()).hexdigest()[:8]
        
        category_file = self.get_category_file(category)
        
        # Format memory entry
        entry = f"""
### [{memory_id}] {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Importance:** {importance:.2f}
{f"**Metadata:** {json.dumps(metadata, indent=2)}" if metadata else ""}

{content}

---
"""
        
        # Append to category file
        with open(category_file, 'a', encoding='utf-8') as f:
            f.write(entry)
        
        # Update stats
        self.stats['total_memories'] += 1
        if category not in self.stats['memories_per_category']:
            self.stats['memories_per_category'][category] = 0
        self.stats['memories_per_category'][category] += 1
        self.stats['last_updated'][category] = timestamp.isoformat()
        
        logger.info(f"Added memory {memory_id} to category {category.value}")
        
        return memory_id
    
    def get_category_stats(self) -> Dict[str, Any]:
        """Get statistics for all categories"""
        stats = {
            'total_categories': len(SemanticCategory),
            'total_memories': self.stats['total_memories'],
            'categories': {}
        }
        
        for category in SemanticCategory:
            category_file = self.get_category_file(category)
            if category_file.exists():
                file_size = category_file.stat().st_size
                memory_count = self.stats['memories_per_category'].get(category, 0)
                
                stats['categories'][category.value] = {
                    'memory_count': memory_count,
                    'file_size_kb': file_size / 1024,
                    'last_updated': self.stats['last_updated'].get(category, 'Never'),
                    'retention_days': CATEGORY_CONFIGS[category].retention_days
                }
        
        return stats
    
    def search_categories(self, query: str) -> List[Tuple[SemanticCategory, float]]:
        """
        Search for relevant categories based on a query
        
        Args:
            query: Search query
            
        Returns:
            List of (category, relevance_score) tuples
        """
        query_lower = query.lower()
        results = []
        
        for category, config in CATEGORY_CONFIGS.items():
            score = 0.0
            
            # Check category name
            if category.value in query_lower:
                score += 2.0
            
            # Check keywords
            for keyword in config.keywords:
                if keyword.lower() in query_lower:
                    score += 1.0
            
            # Check description
            if any(word in config.description.lower() for word in query_lower.split()):
                score += 0.5
            
            if score > 0:
                results.append((category, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def get_retention_policy(self, category: SemanticCategory) -> Dict[str, Any]:
        """Get retention policy for a category"""
        config = CATEGORY_CONFIGS[category]
        
        return {
            'category': category.value,
            'retention_days': config.retention_days,
            'importance_threshold': config.importance_threshold,
            'auto_archive': config.auto_archive,
            'expires_at': (datetime.now() + timedelta(days=config.retention_days)).isoformat()
        }