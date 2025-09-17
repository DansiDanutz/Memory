#!/usr/bin/env python3
"""
Dynamic Cleaner Agent - Intelligent Data Maintenance System
Works with Dynamic Category Manager to respect category scores and policies
"""

import os
import json
import logging
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import difflib

try:
    from .dynamic_category_manager import (
        DynamicCategoryManager, 
        DynamicCategory, 
        SecurityLevel,
        CategoryScore
    )
except ImportError:
    from dynamic_category_manager import (
        DynamicCategoryManager, 
        DynamicCategory, 
        SecurityLevel,
        CategoryScore
    )

logger = logging.getLogger(__name__)

@dataclass
class DynamicCleaningStats:
    """Statistics for dynamic cleaning operations"""
    memories_processed: int = 0
    memories_deleted: int = 0
    memories_archived: int = 0
    memories_encrypted: int = 0
    duplicates_removed: int = 0
    memories_consolidated: int = 0
    categories_cleaned: int = 0
    categories_protected: int = 0
    high_score_categories_skipped: int = 0
    total_space_freed_kb: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def duration_seconds(self) -> float:
        """Calculate cleaning duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON"""
        return {
            'memories_processed': self.memories_processed,
            'memories_deleted': self.memories_deleted,
            'memories_archived': self.memories_archived,
            'memories_encrypted': self.memories_encrypted,
            'duplicates_removed': self.duplicates_removed,
            'memories_consolidated': self.memories_consolidated,
            'categories_cleaned': self.categories_cleaned,
            'categories_protected': self.categories_protected,
            'high_score_categories_skipped': self.high_score_categories_skipped,
            'total_space_freed_kb': self.total_space_freed_kb,
            'errors': self.errors,
            'warnings': self.warnings,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds()
        }

class DynamicCleanerAgent:
    """
    Intelligent Cleaner Agent that respects dynamic category scores
    Works in harmony with Dynamic Category Manager
    """
    
    def __init__(
        self,
        category_manager: Optional[DynamicCategoryManager] = None,
        base_dir: str = 'app/memory_categories_dynamic',
        archive_dir: str = 'app/memory_archive_dynamic',
        secure_archive_dir: str = 'app/memory_secure_archive',
        log_dir: str = 'cleaning_logs',
        enable_scheduler: bool = True,
        dry_run: bool = False
    ):
        """
        Initialize the Dynamic Cleaner Agent
        
        Args:
            category_manager: DynamicCategoryManager instance
            base_dir: Base directory for memories
            archive_dir: Directory for standard archived memories
            secure_archive_dir: Directory for high-security archived memories
            log_dir: Directory for cleaning logs
            enable_scheduler: Enable automatic scheduling
            dry_run: If True, only simulate cleaning without actual changes
        """
        self.category_manager = category_manager or DynamicCategoryManager(base_dir=base_dir)
        self.base_dir = Path(base_dir)
        self.archive_dir = Path(archive_dir)
        self.secure_archive_dir = Path(secure_archive_dir)
        self.log_dir = Path(log_dir)
        
        # Create directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.secure_archive_dir.mkdir(parents=True, exist_ok=True, mode=0o700)  # Restricted permissions
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.dry_run = dry_run
        
        # Similarity threshold for duplicate detection
        self.similarity_threshold = 0.85
        
        # Score thresholds
        self.never_clean_threshold = 0.7
        self.aggressive_clean_threshold = 0.2
        self.encryption_threshold = 0.6
        
        # Initialize scheduler
        self.scheduler = None
        if enable_scheduler:
            self._setup_scheduler()
        
        logger.info(f"🤖 Dynamic Cleaner Agent initialized {'(DRY RUN MODE)' if dry_run else ''}")
    
    def _setup_scheduler(self):
        """Setup automatic scheduling for cleaning tasks"""
        self.scheduler = AsyncIOScheduler()
        
        # Schedule intelligent cleaning at 3 AM daily
        self.scheduler.add_job(
            self.run_intelligent_cleanup,
            CronTrigger(hour=3, minute=0),
            id='intelligent_cleanup',
            name='Intelligent Dynamic Cleanup',
            misfire_grace_time=3600
        )
        
        # Schedule deep clean with analysis on Sunday at 2 AM
        self.scheduler.add_job(
            self.run_deep_analysis_cleanup,
            CronTrigger(day_of_week='sun', hour=2, minute=0),
            id='deep_analysis_cleanup',
            name='Deep Analysis Cleanup',
            misfire_grace_time=7200
        )
        
        # Schedule category optimization every Monday at 4 AM
        self.scheduler.add_job(
            self.optimize_categories,
            CronTrigger(day_of_week='mon', hour=4, minute=0),
            id='category_optimization',
            name='Category Optimization',
            misfire_grace_time=3600
        )
        
        # Start scheduler
        self.scheduler.start()
        
        logger.info("📅 Dynamic cleaning scheduler configured with intelligent policies")
    
    async def run_intelligent_cleanup(self) -> DynamicCleaningStats:
        """
        Run intelligent cleanup that respects category scores
        
        Returns:
            Cleaning statistics
        """
        stats = DynamicCleaningStats()
        logger.info("🧠 Starting intelligent cleanup process...")
        
        try:
            # Get all categories with their scores
            categories = self.category_manager.categories
            
            for cat_id, category in categories.items():
                # Check if category should be cleaned
                if not self._should_clean_category(category):
                    stats.categories_protected += 1
                    stats.high_score_categories_skipped += 1 if category.score.total_score > self.never_clean_threshold else 0
                    logger.info(f"⛔ Skipping protected category: {category.name} (score: {category.score.total_score:.2f})")
                    continue
                
                # Clean based on category score
                category_stats = await self._clean_category_by_score(category)
                self._merge_stats(stats, category_stats)
                stats.categories_cleaned += 1
            
            # Remove duplicates with intelligent merging
            dup_stats = await self.remove_intelligent_duplicates()
            self._merge_stats(stats, dup_stats)
            
            # Archive with security levels
            archive_stats = await self.archive_with_security()
            self._merge_stats(stats, archive_stats)
            
            # Optimize category structure
            optimization_stats = await self.optimize_categories()
            self._merge_stats(stats, optimization_stats)
            
        except Exception as e:
            logger.error(f"Error during intelligent cleanup: {e}")
            stats.errors.append(str(e))
        
        # Finalize stats
        stats.end_time = datetime.now()
        
        # Save cleaning report
        await self.save_cleaning_report(stats)
        
        logger.info(f"✅ Intelligent cleanup completed: "
                   f"{stats.memories_deleted} deleted, "
                   f"{stats.memories_archived} archived, "
                   f"{stats.categories_protected} protected")
        
        return stats
    
    def _should_clean_category(self, category: DynamicCategory) -> bool:
        """
        Determine if a category should be cleaned based on its score and policy
        
        Args:
            category: Category to check
            
        Returns:
            True if category can be cleaned
        """
        # Never clean high-score categories
        if category.score.total_score >= self.never_clean_threshold:
            return False
        
        # Check cleaning policy
        policy = category.cleaning_policy
        if not policy['cleanable']:
            return False
        
        # Check lifecycle stage
        if category.lifecycle_stage in ["birth", "growth"]:
            return False  # Don't clean young categories
        
        return True
    
    async def _clean_category_by_score(self, category: DynamicCategory) -> DynamicCleaningStats:
        """
        Clean a category based on its score with intelligent policies
        
        Args:
            category: Category to clean
            
        Returns:
            Cleaning statistics
        """
        stats = DynamicCleaningStats()
        score = category.score.total_score
        
        # Determine cleaning aggressiveness based on score
        if score < self.aggressive_clean_threshold:
            # Aggressive cleaning for low-score categories
            policy = {
                'retention_days': 30,
                'importance_threshold': 0.5,
                'consolidate': True,
                'archive': False
            }
        elif score < 0.5:
            # Moderate cleaning
            policy = {
                'retention_days': 90,
                'importance_threshold': 0.4,
                'consolidate': True,
                'archive': True
            }
        else:
            # Conservative cleaning
            policy = {
                'retention_days': 365,
                'importance_threshold': 0.3,
                'consolidate': False,
                'archive': True
            }
        
        # Apply cleaning policy
        category_dir = self.base_dir / category.category_id
        if not category_dir.exists():
            return stats
        
        # Process memories in category
        for memory_file in category_dir.glob("*.json"):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                
                stats.memories_processed += 1
                
                # Check retention
                memory_date = datetime.fromisoformat(memory.get('timestamp', datetime.now().isoformat()))
                age_days = (datetime.now() - memory_date).days
                importance = memory.get('importance', 0.3)
                
                if age_days > policy['retention_days'] and importance < policy['importance_threshold']:
                    if not self.dry_run:
                        if policy['archive']:
                            # Archive before deletion
                            await self._archive_memory(memory, category, memory_file)
                            stats.memories_archived += 1
                        
                        # Delete memory
                        memory_file.unlink()
                        stats.memories_deleted += 1
                        stats.total_space_freed_kb += memory_file.stat().st_size / 1024
                    
                    logger.debug(f"Cleaned memory from {category.name}: {memory_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing memory {memory_file}: {e}")
                stats.errors.append(f"Memory processing error: {e}")
        
        return stats
    
    async def _archive_memory(self, memory: Dict, category: DynamicCategory, memory_file: Path):
        """
        Archive a memory with appropriate security level
        
        Args:
            memory: Memory data
            category: Memory's category
            memory_file: Original memory file path
        """
        # Determine archive location based on security level
        if category.score.security_level in [SecurityLevel.SECRET, SecurityLevel.ULTRA_SECRET]:
            archive_base = self.secure_archive_dir
        else:
            archive_base = self.archive_dir
        
        # Create archive structure
        archive_category = archive_base / category.category_id
        archive_category.mkdir(parents=True, exist_ok=True)
        
        # Add archive metadata
        memory['archived_at'] = datetime.now().isoformat()
        memory['original_category'] = category.name
        memory['category_score'] = category.score.total_score
        memory['security_level'] = category.score.security_level.value
        
        # Save to archive
        archive_file = archive_category / f"archived_{memory_file.name}"
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2)
        
        # Set appropriate permissions for secure archives
        if category.score.security_level in [SecurityLevel.SECRET, SecurityLevel.ULTRA_SECRET]:
            archive_file.chmod(0o600)  # Read/write for owner only
    
    async def remove_intelligent_duplicates(self) -> DynamicCleaningStats:
        """
        Remove duplicates with intelligent merging based on category scores
        
        Returns:
            Cleaning statistics
        """
        stats = DynamicCleaningStats()
        
        # Track memories across all categories
        memory_hashes = {}
        
        for category in self.category_manager.categories.values():
            category_dir = self.base_dir / category.category_id
            if not category_dir.exists():
                continue
            
            for memory_file in category_dir.glob("*.json"):
                try:
                    with open(memory_file, 'r', encoding='utf-8') as f:
                        memory = json.load(f)
                    
                    # Generate hash for duplicate detection
                    content = memory.get('content', '')
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    if content_hash in memory_hashes:
                        # Duplicate found - keep the one in higher-score category
                        existing = memory_hashes[content_hash]
                        existing_category = self.category_manager.categories.get(existing['category_id'])
                        
                        if existing_category and existing_category.score.total_score < category.score.total_score:
                            # Current category has higher score - keep this one
                            if not self.dry_run:
                                Path(existing['file_path']).unlink()
                            memory_hashes[content_hash] = {
                                'category_id': category.category_id,
                                'file_path': str(memory_file)
                            }
                        else:
                            # Existing has higher score - delete current
                            if not self.dry_run:
                                memory_file.unlink()
                        
                        stats.duplicates_removed += 1
                    else:
                        memory_hashes[content_hash] = {
                            'category_id': category.category_id,
                            'file_path': str(memory_file)
                        }
                    
                except Exception as e:
                    logger.error(f"Error checking duplicate for {memory_file}: {e}")
                    stats.errors.append(f"Duplicate check error: {e}")
        
        logger.info(f"🔍 Removed {stats.duplicates_removed} intelligent duplicates")
        return stats
    
    async def archive_with_security(self) -> DynamicCleaningStats:
        """
        Archive memories with appropriate security levels
        
        Returns:
            Cleaning statistics
        """
        stats = DynamicCleaningStats()
        
        for category in self.category_manager.categories.values():
            # Skip if category doesn't need archiving
            if category.lifecycle_stage not in ["decline", "archive"]:
                continue
            
            category_dir = self.base_dir / category.category_id
            if not category_dir.exists():
                continue
            
            # Determine if this is a high-security category
            is_secure = category.score.total_score >= self.encryption_threshold
            
            for memory_file in category_dir.glob("*.json"):
                try:
                    with open(memory_file, 'r', encoding='utf-8') as f:
                        memory = json.load(f)
                    
                    # Only archive important memories from declining categories
                    if memory.get('importance', 0) >= 0.5:
                        await self._archive_memory(memory, category, memory_file)
                        stats.memories_archived += 1
                        
                        if is_secure:
                            stats.memories_encrypted += 1
                        
                        # Remove original after archiving
                        if not self.dry_run:
                            memory_file.unlink()
                            stats.memories_deleted += 1
                
                except Exception as e:
                    logger.error(f"Error archiving {memory_file}: {e}")
                    stats.errors.append(f"Archive error: {e}")
        
        return stats
    
    async def optimize_categories(self) -> DynamicCleaningStats:
        """
        Optimize category structure by merging similar categories
        
        Returns:
            Cleaning statistics
        """
        stats = DynamicCleaningStats()
        
        # Get recommendations from category manager
        recommendations = self.category_manager.get_cleaning_recommendations()
        
        for rec in recommendations:
            if rec['action'] == 'archive':
                # Archive entire category
                category = self.category_manager.categories.get(rec['category_id'])
                if category:
                    await self._archive_category(category)
                    stats.categories_cleaned += 1
            
            elif rec['action'] == 'delete':
                # Delete empty category
                if not self.dry_run:
                    category_dir = self.base_dir / rec['category_id']
                    if category_dir.exists():
                        shutil.rmtree(category_dir)
                    
                    # Remove from manager
                    if rec['category_id'] in self.category_manager.categories:
                        del self.category_manager.categories[rec['category_id']]
                
                stats.categories_cleaned += 1
        
        # Save updated category structure
        self.category_manager._save_categories()
        
        return stats
    
    async def _archive_category(self, category: DynamicCategory):
        """Archive an entire category"""
        category_dir = self.base_dir / category.category_id
        if not category_dir.exists():
            return
        
        # Determine archive location
        if category.score.security_level in [SecurityLevel.SECRET, SecurityLevel.ULTRA_SECRET]:
            archive_base = self.secure_archive_dir
        else:
            archive_base = self.archive_dir
        
        # Create archive
        archive_dir = archive_base / f"archived_categories/{category.category_id}_{datetime.now().strftime('%Y%m%d')}"
        
        if not self.dry_run:
            # Move entire category to archive
            shutil.move(str(category_dir), str(archive_dir))
            
            # Remove from active categories
            if category.category_id in self.category_manager.categories:
                del self.category_manager.categories[category.category_id]
    
    async def run_deep_analysis_cleanup(self) -> DynamicCleaningStats:
        """
        Run deep analysis with category evolution insights
        
        Returns:
            Cleaning statistics
        """
        logger.info("🔬 Starting deep analysis cleanup...")
        
        # Run intelligent cleanup first
        stats = await self.run_intelligent_cleanup()
        
        # Analyze category evolution
        evolution_report = self._analyze_category_evolution()
        
        # Log insights
        logger.info(f"📊 Category Evolution Insights:")
        logger.info(f"  • Categories in decline: {evolution_report['declining']}")
        logger.info(f"  • Categories growing: {evolution_report['growing']}")
        logger.info(f"  • High-security categories: {evolution_report['high_security']}")
        logger.info(f"  • Merge candidates: {evolution_report['merge_candidates']}")
        
        return stats
    
    def _analyze_category_evolution(self) -> Dict[str, Any]:
        """Analyze how categories are evolving"""
        report = {
            'declining': [],
            'growing': [],
            'high_security': [],
            'merge_candidates': []
        }
        
        for category in self.category_manager.categories.values():
            if category.lifecycle_stage == "decline":
                report['declining'].append(category.name)
            elif category.lifecycle_stage == "growth":
                report['growing'].append(category.name)
            
            if category.score.total_score >= self.encryption_threshold:
                report['high_security'].append({
                    'name': category.name,
                    'score': category.score.total_score,
                    'level': category.score.security_level.value
                })
        
        return report
    
    def _merge_stats(self, main: DynamicCleaningStats, other: DynamicCleaningStats):
        """Merge statistics from another operation"""
        main.memories_processed += other.memories_processed
        main.memories_deleted += other.memories_deleted
        main.memories_archived += other.memories_archived
        main.memories_encrypted += other.memories_encrypted
        main.duplicates_removed += other.duplicates_removed
        main.memories_consolidated += other.memories_consolidated
        main.total_space_freed_kb += other.total_space_freed_kb
        main.errors.extend(other.errors)
        main.warnings.extend(other.warnings)
    
    async def save_cleaning_report(self, stats: DynamicCleaningStats):
        """Save detailed cleaning report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'stats': stats.to_dict(),
            'category_summary': self.category_manager.get_category_stats(),
            'mode': 'dry_run' if self.dry_run else 'active'
        }
        
        report_file = self.log_dir / f"cleaning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📝 Cleaning report saved to {report_file}")


# Example usage
if __name__ == "__main__":
    async def test_dynamic_cleaner():
        """Test the dynamic cleaner system"""
        # Initialize managers
        category_mgr = DynamicCategoryManager(max_categories=10)
        cleaner = DynamicCleanerAgent(
            category_manager=category_mgr,
            enable_scheduler=False,
            dry_run=True  # Test mode
        )
        
        print("\n🧹 Testing Dynamic Cleaner Agent\n")
        print("=" * 60)
        
        # Create some test memories with different scores
        test_memories = [
            ("Old meeting notes from last year about office supplies", {'importance': 0.2}),
            ("Critical financial report with sensitive data", {'importance': 0.9}),
            ("Random thought about lunch options", {'importance': 0.1}),
            ("Medical test results and doctor recommendations", {'importance': 0.8}),
            ("Expired coupon codes from 6 months ago", {'importance': 0.1})
        ]
        
        # Process memories to create categories
        for content, metadata in test_memories:
            await category_mgr.detect_category(content, metadata)
        
        # Run intelligent cleanup
        print("\nRunning Intelligent Cleanup...")
        stats = await cleaner.run_intelligent_cleanup()
        
        print(f"\n📊 Cleanup Results:")
        print(f"  • Memories processed: {stats.memories_processed}")
        print(f"  • Memories deleted: {stats.memories_deleted}")
        print(f"  • Memories archived: {stats.memories_archived}")
        print(f"  • High-security memories encrypted: {stats.memories_encrypted}")
        print(f"  • Categories protected: {stats.categories_protected}")
        print(f"  • High-score categories skipped: {stats.high_score_categories_skipped}")
        
        # Show category protection status
        print(f"\n🛡️ Category Protection Status:")
        for category in category_mgr.categories.values():
            can_clean = cleaner._should_clean_category(category)
            print(f"  • {category.name}: Score={category.score.total_score:.2f}, "
                  f"Security={category.score.security_level.value}, "
                  f"Cleanable={'Yes' if can_clean else 'No'}")
    
    # Run test
    asyncio.run(test_dynamic_cleaner())