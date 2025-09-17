#!/usr/bin/env python3
"""
Dynamic Category Manager Agent - AI-Powered Adaptive Category System
Learns and creates categories dynamically based on user content patterns
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
import asyncio
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class SecurityLevel(str, Enum):
    """Security levels based on category score"""
    GENERAL = "general"         # 0.0 - 0.3
    CONFIDENTIAL = "confidential"  # 0.3 - 0.6
    SECRET = "secret"           # 0.6 - 0.8
    ULTRA_SECRET = "ultra_secret"  # 0.8 - 1.0

@dataclass
class CategoryScore:
    """Comprehensive scoring for a category"""
    sensitivity: float = 0.0  # 0-1: How sensitive is the content
    importance: float = 0.0   # 0-1: How important to user
    frequency: float = 0.0    # 0-1: How frequently accessed
    criticality: float = 0.0  # 0-1: Business/legal/health criticality
    
    @property
    def total_score(self) -> float:
        """Calculate weighted total score (0.0 - 1.0)"""
        weights = {
            'sensitivity': 0.35,
            'importance': 0.25,
            'frequency': 0.25,
            'criticality': 0.15
        }
        
        score = (
            self.sensitivity * weights['sensitivity'] +
            self.importance * weights['importance'] +
            self.frequency * weights['frequency'] +
            self.criticality * weights['criticality']
        )
        
        return min(1.0, max(0.0, score))
    
    @property
    def security_level(self) -> SecurityLevel:
        """Determine security level from score"""
        if self.total_score >= 0.8:
            return SecurityLevel.ULTRA_SECRET
        elif self.total_score >= 0.6:
            return SecurityLevel.SECRET
        elif self.total_score >= 0.3:
            return SecurityLevel.CONFIDENTIAL
        else:
            return SecurityLevel.GENERAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'sensitivity': self.sensitivity,
            'importance': self.importance,
            'frequency': self.frequency,
            'criticality': self.criticality,
            'total_score': self.total_score,
            'security_level': self.security_level.value
        }

@dataclass
class DynamicSlot:
    """Dynamic slot that adapts to category score"""
    type: str  # 'recent', 'important', 'referenced', 'action', 'summary', 'historical_best', 'predicted_next'
    content: Optional[str] = None
    memory_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.type,
            'content': self.content,
            'memory_id': self.memory_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'score': self.score,
            'metadata': self.metadata
        }

@dataclass
class DynamicCategory:
    """A dynamically created and managed category"""
    name: str
    category_id: str
    created_at: datetime
    score: CategoryScore
    slots: List[DynamicSlot]
    memory_count: int = 0
    last_accessed: Optional[datetime] = None
    lifecycle_stage: str = "birth"  # birth, growth, maturity, decline, archive
    ai_description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    similar_categories: List[str] = field(default_factory=list)
    
    @property
    def num_slots(self) -> int:
        """Determine number of slots based on score"""
        score = self.score.total_score
        if score >= 0.6:
            return 7  # Premium
        elif score >= 0.3:
            return 5  # Standard
        else:
            return 3  # Basic
    
    @property
    def cleaning_policy(self) -> Dict[str, Any]:
        """Determine cleaning policy based on score"""
        score = self.score.total_score
        
        if score >= 0.7:
            return {
                'cleanable': False,
                'reason': 'High-priority category - never clean',
                'retention_days': -1  # Infinite
            }
        elif score >= 0.5:
            return {
                'cleanable': True,
                'reason': 'Medium-priority category',
                'retention_days': 365
            }
        elif score >= 0.3:
            return {
                'cleanable': True,
                'reason': 'Standard category',
                'retention_days': 90
            }
        else:
            return {
                'cleanable': True,
                'reason': 'Low-priority category',
                'retention_days': 30
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'category_id': self.category_id,
            'created_at': self.created_at.isoformat(),
            'score': self.score.to_dict(),
            'slots': [slot.to_dict() for slot in self.slots],
            'memory_count': self.memory_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'lifecycle_stage': self.lifecycle_stage,
            'ai_description': self.ai_description,
            'keywords': self.keywords,
            'similar_categories': self.similar_categories,
            'num_slots': self.num_slots,
            'cleaning_policy': self.cleaning_policy
        }

class DynamicCategoryManager:
    """
    Intelligent Category Manager that learns and adapts
    Creates categories dynamically based on content patterns
    """
    
    def __init__(
        self,
        base_dir: str = 'app/memory_categories_dynamic',
        max_categories: int = 30,
        enable_ai: bool = True,
        merge_threshold: float = 0.85
    ):
        """
        Initialize Dynamic Category Manager
        
        Args:
            base_dir: Base directory for categories
            max_categories: Maximum number of categories allowed
            enable_ai: Enable AI-powered detection
            merge_threshold: Similarity threshold for merging categories
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_categories = max_categories
        self.enable_ai = enable_ai
        self.merge_threshold = merge_threshold
        
        # Category storage
        self.categories: Dict[str, DynamicCategory] = {}
        self.category_index = self.base_dir / 'category_index.json'
        self.category_embeddings: Dict[str, List[float]] = {}
        
        # High-sensitivity keywords for automatic scoring
        self.sensitive_keywords = {
            'financial': ['bank', 'account', 'password', 'credit', 'debit', 'ssn', 'tax', 'salary', 'investment'],
            'health': ['medical', 'doctor', 'diagnosis', 'treatment', 'prescription', 'illness', 'health'],
            'legal': ['contract', 'agreement', 'lawsuit', 'attorney', 'legal', 'court', 'confidential'],
            'personal': ['secret', 'private', 'confidential', 'sensitive', 'personal']
        }
        
        # Load existing categories
        self._load_categories()
        
        logger.info(f"🧠 Dynamic Category Manager initialized with {len(self.categories)} categories")
    
    def _load_categories(self):
        """Load existing categories from disk"""
        if self.category_index.exists():
            try:
                with open(self.category_index, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cat_id, cat_data in data.items():
                        self.categories[cat_id] = self._deserialize_category(cat_data)
                logger.info(f"Loaded {len(self.categories)} existing categories")
            except Exception as e:
                logger.error(f"Error loading categories: {e}")
    
    def _deserialize_category(self, data: Dict) -> DynamicCategory:
        """Deserialize category from JSON"""
        score = CategoryScore(
            sensitivity=data['score']['sensitivity'],
            importance=data['score']['importance'],
            frequency=data['score']['frequency'],
            criticality=data['score']['criticality']
        )
        
        slots = []
        for slot_data in data.get('slots', []):
            slot = DynamicSlot(
                type=slot_data['type'],
                content=slot_data.get('content'),
                memory_id=slot_data.get('memory_id'),
                timestamp=datetime.fromisoformat(slot_data['timestamp']) if slot_data.get('timestamp') else None,
                score=slot_data.get('score', 0.0),
                metadata=slot_data.get('metadata', {})
            )
            slots.append(slot)
        
        return DynamicCategory(
            name=data['name'],
            category_id=data['category_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            score=score,
            slots=slots,
            memory_count=data.get('memory_count', 0),
            last_accessed=datetime.fromisoformat(data['last_accessed']) if data.get('last_accessed') else None,
            lifecycle_stage=data.get('lifecycle_stage', 'birth'),
            ai_description=data.get('ai_description'),
            keywords=data.get('keywords', []),
            similar_categories=data.get('similar_categories', [])
        )
    
    def _save_categories(self):
        """Save all categories to disk"""
        try:
            data = {}
            for cat_id, category in self.categories.items():
                data[cat_id] = category.to_dict()
            
            with open(self.category_index, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Saved {len(data)} categories")
        except Exception as e:
            logger.error(f"Error saving categories: {e}")
    
    async def detect_category(self, content: str, metadata: Optional[Dict] = None) -> Tuple[str, DynamicCategory]:
        """
        Detect or create appropriate category for content
        
        Args:
            content: Memory content
            metadata: Optional metadata
            
        Returns:
            Tuple of (category_id, category)
        """
        # Calculate initial sensitivity score
        sensitivity = self._calculate_sensitivity(content)
        
        # Try to find existing category
        best_match = await self._find_best_category(content, metadata)
        
        if best_match:
            category_id, category = best_match
            # Update category stats
            category.memory_count += 1
            category.last_accessed = datetime.now()
            category.score.frequency = min(1.0, category.score.frequency + 0.01)
            
            # Update lifecycle stage
            self._update_lifecycle(category)
            
            logger.info(f"📁 Matched to existing category: {category.name} (score: {category.score.total_score:.2f})")
            
        else:
            # Create new category if under limit
            if len(self.categories) >= self.max_categories:
                # Merge or archive low-score categories
                await self._manage_category_limit()
            
            category = await self._create_new_category(content, sensitivity, metadata)
            category_id = category.category_id
            self.categories[category_id] = category
            
            logger.info(f"🆕 Created new category: {category.name} (score: {category.score.total_score:.2f})")
        
        # Save updated categories
        self._save_categories()
        
        return category_id, category
    
    def _calculate_sensitivity(self, content: str) -> float:
        """Calculate sensitivity score based on content"""
        content_lower = content.lower()
        sensitivity = 0.0
        
        # Check for sensitive keywords
        for category, keywords in self.sensitive_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    if category == 'financial':
                        sensitivity = max(sensitivity, 0.8)
                    elif category == 'health':
                        sensitivity = max(sensitivity, 0.7)
                    elif category == 'legal':
                        sensitivity = max(sensitivity, 0.75)
                    elif category == 'personal':
                        sensitivity = max(sensitivity, 0.6)
        
        # Check for patterns (emails, phone numbers, etc.)
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', content):  # SSN pattern
            sensitivity = max(sensitivity, 0.9)
        if re.search(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', content):  # Credit card pattern
            sensitivity = max(sensitivity, 0.85)
        
        return sensitivity
    
    async def _find_best_category(self, content: str, metadata: Optional[Dict]) -> Optional[Tuple[str, DynamicCategory]]:
        """Find best matching existing category"""
        if not self.categories:
            return None
        
        best_match = None
        best_score = 0.0
        
        content_lower = content.lower()
        
        for cat_id, category in self.categories.items():
            score = 0.0
            
            # Check keywords
            for keyword in category.keywords:
                if keyword.lower() in content_lower:
                    score += 0.3
            
            # Check description similarity (simple for now)
            if category.ai_description and category.ai_description.lower() in content_lower:
                score += 0.2
            
            # Boost recent categories
            if category.last_accessed:
                days_ago = (datetime.now() - category.last_accessed).days
                if days_ago < 7:
                    score += 0.1
            
            if score > best_score and score > 0.3:  # Minimum threshold
                best_score = score
                best_match = (cat_id, category)
        
        return best_match
    
    async def _create_new_category(self, content: str, sensitivity: float, metadata: Optional[Dict]) -> DynamicCategory:
        """Create a new category based on content"""
        # Generate category name (simplified - in real implementation would use AI)
        category_name = self._generate_category_name(content)
        
        # Generate category ID
        category_id = hashlib.md5(f"{category_name}{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        
        # Calculate initial scores
        score = CategoryScore(
            sensitivity=sensitivity,
            importance=0.5,  # Default medium importance
            frequency=0.1,   # Low initial frequency
            criticality=self._calculate_criticality(content)
        )
        
        # Extract keywords
        keywords = self._extract_keywords(content)
        
        # Create category
        category = DynamicCategory(
            name=category_name,
            category_id=category_id,
            created_at=datetime.now(),
            score=score,
            slots=self._initialize_slots(score.total_score),
            memory_count=1,
            last_accessed=datetime.now(),
            lifecycle_stage="birth",
            ai_description=f"Category for {category_name.lower()} related memories",
            keywords=keywords,
            similar_categories=[]
        )
        
        # Create category directory
        cat_dir = self.base_dir / category_id
        cat_dir.mkdir(parents=True, exist_ok=True)
        
        # Create initial MD file
        self._create_category_md(category, cat_dir)
        
        return category
    
    def _generate_category_name(self, content: str) -> str:
        """Generate category name from content (simplified)"""
        # Extract first significant phrase
        words = content.split()[:5]
        
        # Check for known patterns
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['meeting', 'conference', 'call']):
            return "Meetings"
        elif any(word in content_lower for word in ['expense', 'payment', 'invoice']):
            return "Financial"
        elif any(word in content_lower for word in ['idea', 'thought', 'concept']):
            return "Ideas"
        elif any(word in content_lower for word in ['task', 'todo', 'deadline']):
            return "Tasks"
        elif any(word in content_lower for word in ['personal', 'family', 'friend']):
            return "Personal"
        else:
            # Create from first significant word
            for word in words:
                if len(word) > 3 and word.isalpha():
                    return word.title()
            
            return "General"
    
    def _calculate_criticality(self, content: str) -> float:
        """Calculate criticality score"""
        content_lower = content.lower()
        criticality = 0.0
        
        # Check for critical keywords
        critical_terms = ['urgent', 'critical', 'emergency', 'deadline', 'important', 'asap']
        for term in critical_terms:
            if term in content_lower:
                criticality = max(criticality, 0.7)
        
        # Check for financial/legal terms
        if any(word in content_lower for word in ['contract', 'agreement', 'payment']):
            criticality = max(criticality, 0.6)
        
        return criticality
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content (simplified)"""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'is', 'are', 'was', 'were'}
        
        words = content.lower().split()
        keywords = []
        
        for word in words:
            # Clean word
            word = re.sub(r'[^\w\s]', '', word)
            
            # Add if significant
            if word and word not in stop_words and len(word) > 3:
                keywords.append(word)
                
            if len(keywords) >= 5:
                break
        
        return keywords
    
    def _initialize_slots(self, score: float) -> List[DynamicSlot]:
        """Initialize slots based on category score"""
        slots = []
        
        # Basic slots (all categories)
        slots.append(DynamicSlot(type="recent"))
        slots.append(DynamicSlot(type="important"))
        slots.append(DynamicSlot(type="referenced"))
        
        if score >= 0.3:
            # Standard slots
            slots.append(DynamicSlot(type="action"))
            slots.append(DynamicSlot(type="summary"))
        
        if score >= 0.6:
            # Premium slots
            slots.append(DynamicSlot(type="historical_best"))
            slots.append(DynamicSlot(type="predicted_next"))
        
        return slots
    
    def _create_category_md(self, category: DynamicCategory, cat_dir: Path):
        """Create markdown file for category"""
        md_file = cat_dir / f"{category.category_id}.md"
        
        # Determine encryption note
        encryption = "🔐 ENCRYPTED" if category.score.total_score > 0.6 else "📂 STANDARD"
        
        content = f"""# {category.name} Category

**Status:** {encryption}
**Security Level:** {category.score.security_level.value.upper()}
**Created:** {category.created_at.strftime('%Y-%m-%d %H:%M')}
**Lifecycle:** {category.lifecycle_stage.upper()}

## 📊 Category Scores
- **Sensitivity:** {category.score.sensitivity:.2f}
- **Importance:** {category.score.importance:.2f}
- **Frequency:** {category.score.frequency:.2f}
- **Criticality:** {category.score.criticality:.2f}
- **Total Score:** {category.score.total_score:.2f}

## 🎯 Dynamic Slots ({category.num_slots} allocated)

"""
        
        for i, slot in enumerate(category.slots, 1):
            content += f"### Slot {i}: {slot.type.replace('_', ' ').title()}\n"
            content += f"{slot.content if slot.content else '_Empty_'}\n\n"
        
        content += f"""
## 🔧 Cleaning Policy
- **Cleanable:** {'No' if not category.cleaning_policy['cleanable'] else 'Yes'}
- **Retention:** {category.cleaning_policy['retention_days']} days
- **Reason:** {category.cleaning_policy['reason']}

## 📝 Keywords
{', '.join(category.keywords) if category.keywords else 'No keywords yet'}

## 📈 Statistics
- **Total Memories:** {category.memory_count}
- **Last Accessed:** {category.last_accessed.strftime('%Y-%m-%d %H:%M') if category.last_accessed else 'Never'}

---
*This category is dynamically managed and will evolve based on usage patterns.*
"""
        
        md_file.write_text(content, encoding='utf-8')
    
    def _update_lifecycle(self, category: DynamicCategory):
        """Update category lifecycle stage based on metrics"""
        age_days = (datetime.now() - category.created_at).days
        
        if category.memory_count < 5 and age_days < 7:
            category.lifecycle_stage = "birth"
        elif category.memory_count >= 5 and category.memory_count < 20 and age_days < 30:
            category.lifecycle_stage = "growth"
        elif category.memory_count >= 20 and category.score.frequency > 0.5:
            category.lifecycle_stage = "maturity"
        elif category.score.frequency < 0.2 and age_days > 60:
            category.lifecycle_stage = "decline"
        elif category.score.frequency < 0.1 and age_days > 90:
            category.lifecycle_stage = "archive"
    
    async def _manage_category_limit(self):
        """Manage categories when limit is reached"""
        # Find categories eligible for merging or archiving
        candidates = []
        
        for cat_id, category in self.categories.items():
            if category.lifecycle_stage in ["decline", "archive"]:
                candidates.append((cat_id, category))
            elif category.score.total_score < 0.2:
                candidates.append((cat_id, category))
        
        # Sort by score (ascending)
        candidates.sort(key=lambda x: x[1].score.total_score)
        
        if candidates:
            # Archive lowest scoring category
            cat_id, category = candidates[0]
            
            # Create archive entry
            archive_dir = self.base_dir / "archived"
            archive_dir.mkdir(exist_ok=True)
            
            archive_file = archive_dir / f"{cat_id}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(category.to_dict(), f, indent=2)
            
            # Remove from active categories
            del self.categories[cat_id]
            
            logger.info(f"📦 Archived category: {category.name} (score: {category.score.total_score:.2f})")
    
    def update_slot(
        self,
        category_id: str,
        slot_type: str,
        content: str,
        memory_id: str,
        score: float = 0.5
    ):
        """Update a specific slot in a category"""
        if category_id not in self.categories:
            logger.error(f"Category {category_id} not found")
            return
        
        category = self.categories[category_id]
        
        # Find and update slot
        for slot in category.slots:
            if slot.type == slot_type:
                slot.content = content
                slot.memory_id = memory_id
                slot.timestamp = datetime.now()
                slot.score = score
                break
        
        # Update category access time
        category.last_accessed = datetime.now()
        
        # Save changes
        self._save_categories()
        
        # Update MD file
        cat_dir = self.base_dir / category_id
        self._create_category_md(category, cat_dir)
    
    def get_category_stats(self) -> Dict[str, Any]:
        """Get statistics about all categories"""
        stats = {
            'total_categories': len(self.categories),
            'max_categories': self.max_categories,
            'lifecycle_distribution': defaultdict(int),
            'security_distribution': defaultdict(int),
            'average_score': 0.0,
            'categories': []
        }
        
        total_score = 0.0
        
        for category in self.categories.values():
            stats['lifecycle_distribution'][category.lifecycle_stage] += 1
            stats['security_distribution'][category.score.security_level.value] += 1
            total_score += category.score.total_score
            
            stats['categories'].append({
                'name': category.name,
                'score': category.score.total_score,
                'memories': category.memory_count,
                'stage': category.lifecycle_stage,
                'security': category.score.security_level.value
            })
        
        if self.categories:
            stats['average_score'] = total_score / len(self.categories)
        
        # Sort categories by score
        stats['categories'].sort(key=lambda x: x['score'], reverse=True)
        
        return stats
    
    def get_cleaning_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for cleaning based on category scores"""
        recommendations = []
        
        for cat_id, category in self.categories.items():
            policy = category.cleaning_policy
            
            if policy['cleanable'] and category.lifecycle_stage in ["decline", "archive"]:
                recommendations.append({
                    'category_id': cat_id,
                    'category_name': category.name,
                    'score': category.score.total_score,
                    'action': 'archive',
                    'reason': f"{policy['reason']} - Category in {category.lifecycle_stage} stage",
                    'retention_days': policy['retention_days']
                })
            elif policy['cleanable'] and category.memory_count == 0:
                recommendations.append({
                    'category_id': cat_id,
                    'category_name': category.name,
                    'score': category.score.total_score,
                    'action': 'delete',
                    'reason': 'Empty category with no memories'
                })
        
        return recommendations


# Example usage and testing
if __name__ == "__main__":
    async def test_dynamic_categories():
        """Test the dynamic category system"""
        manager = DynamicCategoryManager(max_categories=10)
        
        # Test memories with different content
        test_memories = [
            ("Meeting with CEO about Q4 financial projections and acquisition strategy", None),
            ("Doctor appointment for annual checkup - blood test results pending", None),
            ("Idea: Create AI-powered memory assistant with voice recognition", None),
            ("Contract review with legal team regarding new vendor agreement", None),
            ("Personal note: Anniversary dinner reservation at Italian restaurant", None),
            ("Project deadline: Complete API integration by Friday", None),
            ("Bank account password changed - new security questions added", None),
            ("Team standup notes: Sprint planning and task allocation", None),
            ("Investment portfolio review with financial advisor", None),
            ("Kids soccer practice moved to Saturday morning", None)
        ]
        
        print("\n🧠 Testing Dynamic Category Manager\n")
        print("=" * 60)
        
        for content, metadata in test_memories:
            print(f"\n📝 Processing: {content[:50]}...")
            
            cat_id, category = await manager.detect_category(content, metadata)
            
            print(f"  📁 Category: {category.name}")
            print(f"  🎯 Score: {category.score.total_score:.2f}")
            print(f"  🔐 Security: {category.score.security_level.value}")
            print(f"  🎰 Slots: {category.num_slots}")
            print(f"  🧹 Cleanable: {'Yes' if category.cleaning_policy['cleanable'] else 'No'}")
        
        # Display statistics
        print("\n" + "=" * 60)
        print("📊 CATEGORY STATISTICS")
        print("=" * 60)
        
        stats = manager.get_category_stats()
        print(f"\nTotal Categories: {stats['total_categories']}/{stats['max_categories']}")
        print(f"Average Score: {stats['average_score']:.2f}")
        
        print("\n🔒 Security Distribution:")
        for level, count in stats['security_distribution'].items():
            print(f"  {level.upper()}: {count} categories")
        
        print("\n📈 Lifecycle Distribution:")
        for stage, count in stats['lifecycle_distribution'].items():
            print(f"  {stage.upper()}: {count} categories")
        
        print("\n🏆 Top Categories by Score:")
        for cat in stats['categories'][:5]:
            print(f"  • {cat['name']}: {cat['score']:.2f} ({cat['memories']} memories)")
        
        # Get cleaning recommendations
        recommendations = manager.get_cleaning_recommendations()
        if recommendations:
            print("\n🧹 Cleaning Recommendations:")
            for rec in recommendations:
                print(f"  • {rec['category_name']}: {rec['action']} - {rec['reason']}")
    
    # Run test
    asyncio.run(test_dynamic_categories())