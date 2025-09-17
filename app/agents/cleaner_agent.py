#!/usr/bin/env python3
"""
Cleaner Agent - Mandatory Data Maintenance System
Handles memory cleanup, deduplication, archiving, and retention policies
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

from .category_manager import SemanticCategory, CATEGORY_CONFIGS

logger = logging.getLogger(__name__)

@dataclass
class CleaningStats:
    """Statistics for cleaning operations"""
    memories_processed: int = 0
    memories_deleted: int = 0
    memories_archived: int = 0
    duplicates_removed: int = 0
    memories_consolidated: int = 0
    categories_cleaned: int = 0
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
            'duplicates_removed': self.duplicates_removed,
            'memories_consolidated': self.memories_consolidated,
            'categories_cleaned': self.categories_cleaned,
            'total_space_freed_kb': self.total_space_freed_kb,
            'errors': self.errors,
            'warnings': self.warnings,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds()
        }

@dataclass
class RetentionPolicy:
    """Retention policy for a category"""
    category: SemanticCategory
    retention_days: int
    importance_threshold: float
    archive_enabled: bool = True
    consolidation_enabled: bool = True
    
    def is_expired(self, memory_date: datetime) -> bool:
        """Check if a memory has expired based on retention policy"""
        age = (datetime.now() - memory_date).days
        return age > self.retention_days
    
    def should_keep(self, memory_date: datetime, importance: float) -> bool:
        """Determine if a memory should be kept"""
        if importance >= 0.8:  # Always keep very important memories
            return True
        if self.is_expired(memory_date) and importance < self.importance_threshold:
            return False
        return True

class CleanerAgent:
    """
    Mandatory Cleaner Agent for memory maintenance
    Handles cleanup, deduplication, archiving, and retention
    """
    
    def __init__(
        self,
        base_dir: str = 'app/memory_categories',
        archive_dir: str = 'app/memory_archive',
        log_dir: str = 'cleaning_logs',
        enable_scheduler: bool = True,
        dry_run: bool = False
    ):
        """
        Initialize the Cleaner Agent
        
        Args:
            base_dir: Base directory for memories
            archive_dir: Directory for archived memories
            log_dir: Directory for cleaning logs
            enable_scheduler: Enable automatic scheduling
            dry_run: If True, only simulate cleaning without actual changes
        """
        self.base_dir = Path(base_dir)
        self.archive_dir = Path(archive_dir)
        self.log_dir = Path(log_dir)
        
        # Create directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.dry_run = dry_run
        
        # Initialize retention policies
        self.retention_policies = self._initialize_retention_policies()
        
        # Similarity threshold for duplicate detection
        self.similarity_threshold = 0.85
        
        # Initialize scheduler
        self.scheduler = None
        if enable_scheduler:
            self._setup_scheduler()
        
        logger.info(f"🧹 Cleaner Agent initialized {'(DRY RUN MODE)' if dry_run else ''}")
    
    def _initialize_retention_policies(self) -> Dict[SemanticCategory, RetentionPolicy]:
        """Initialize retention policies for all categories"""
        policies = {}
        
        for category in SemanticCategory:
            config = CATEGORY_CONFIGS[category]
            policies[category] = RetentionPolicy(
                category=category,
                retention_days=config.retention_days,
                importance_threshold=config.importance_threshold,
                archive_enabled=config.auto_archive,
                consolidation_enabled=True
            )
        
        return policies
    
    def _setup_scheduler(self):
        """Setup automatic scheduling for cleaning tasks"""
        self.scheduler = AsyncIOScheduler()
        
        # Schedule daily cleaning at 3 AM
        self.scheduler.add_job(
            self.run_full_cleanup,
            CronTrigger(hour=3, minute=0),
            id='daily_cleanup',
            name='Daily Memory Cleanup',
            misfire_grace_time=3600  # 1 hour grace period
        )
        
        # Schedule weekly deep clean on Sunday at 2 AM
        self.scheduler.add_job(
            self.run_deep_cleanup,
            CronTrigger(day_of_week='sun', hour=2, minute=0),
            id='weekly_deep_cleanup',
            name='Weekly Deep Cleanup',
            misfire_grace_time=7200  # 2 hour grace period
        )
        
        # Start scheduler
        self.scheduler.start()
        
        logger.info("📅 Cleaning scheduler configured (Daily at 3 AM, Deep clean Sunday at 2 AM)")
    
    async def run_full_cleanup(self) -> CleaningStats:
        """
        Run full cleanup process
        
        Returns:
            Cleaning statistics
        """
        stats = CleaningStats()
        logger.info("🧹 Starting full cleanup process...")
        
        try:
            # Clean each category
            for category in SemanticCategory:
                category_stats = await self.clean_category(category)
                self._merge_stats(stats, category_stats)
                stats.categories_cleaned += 1
            
            # Remove duplicates across all categories
            dup_stats = await self.remove_duplicates()
            self._merge_stats(stats, dup_stats)
            
            # Archive old important memories
            archive_stats = await self.archive_old_memories()
            self._merge_stats(stats, archive_stats)
            
            # Consolidate similar memories
            consolidation_stats = await self.consolidate_memories()
            self._merge_stats(stats, consolidation_stats)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            stats.errors.append(str(e))
        
        # Finalize stats
        stats.end_time = datetime.now()
        
        # Save cleaning report
        await self.save_cleaning_report(stats)
        
        logger.info(f"✅ Cleanup completed: {stats.memories_deleted} deleted, "
                   f"{stats.memories_archived} archived, {stats.duplicates_removed} duplicates removed")
        
        return stats
    
    async def run_deep_cleanup(self) -> CleaningStats:
        """
        Run deep cleanup with more aggressive consolidation
        
        Returns:
            Cleaning statistics
        """
        logger.info("🔍 Starting deep cleanup process...")
        
        # Run full cleanup first
        stats = await self.run_full_cleanup()
        
        # Additional deep cleaning operations
        try:
            # Reorganize category files
            await self.reorganize_categories()
            
            # Clean up orphaned files
            await self.clean_orphaned_files()
            
            # Optimize storage
            await self.optimize_storage()
            
        except Exception as e:
            logger.error(f"Error during deep cleanup: {e}")
            stats.errors.append(f"Deep cleanup error: {e}")
        
        return stats
    
    async def clean_category(self, category: SemanticCategory) -> CleaningStats:
        """
        Clean a specific category based on retention policy
        
        Args:
            category: Category to clean
            
        Returns:
            Cleaning statistics
        """
        stats = CleaningStats()
        policy = self.retention_policies[category]
        
        category_dir = self.base_dir / category.value
        if not category_dir.exists():
            return stats
        
        category_file = category_dir / f"{category.value}.md"
        if not category_file.exists():
            return stats
        
        try:
            # Parse memories from MD file
            memories = await self._parse_memories_from_md(category_file)
            stats.memories_processed += len(memories)
            
            memories_to_keep = []
            memories_to_archive = []
            memories_to_delete = []
            
            for memory in memories:
                memory_date = memory.get('timestamp', datetime.now())
                importance = memory.get('importance', 0.5)
                
                if policy.should_keep(memory_date, importance):
                    memories_to_keep.append(memory)
                elif policy.archive_enabled and importance >= 0.5:
                    memories_to_archive.append(memory)
                else:
                    memories_to_delete.append(memory)
            
            if not self.dry_run:
                # Archive memories
                if memories_to_archive:
                    await self._archive_memories(category, memories_to_archive)
                    stats.memories_archived += len(memories_to_archive)
                
                # Update category file with kept memories
                await self._update_category_file(category_file, memories_to_keep)
                
                # Track deleted memories
                stats.memories_deleted += len(memories_to_delete)
                
                # Calculate space freed
                original_size = category_file.stat().st_size / 1024
                new_size = category_file.stat().st_size / 1024
                stats.total_space_freed_kb += (original_size - new_size)
            
            logger.info(f"Cleaned category {category.value}: "
                       f"{len(memories_to_delete)} deleted, {len(memories_to_archive)} archived")
            
        except Exception as e:
            logger.error(f"Error cleaning category {category.value}: {e}")
            stats.errors.append(f"Category {category.value}: {e}")
        
        return stats
    
    async def remove_duplicates(self) -> CleaningStats:
        """
        Remove duplicate memories across all categories
        
        Returns:
            Cleaning statistics
        """
        stats = CleaningStats()
        all_memories = []
        
        # Collect all memories
        for category in SemanticCategory:
            category_file = self.base_dir / category.value / f"{category.value}.md"
            if category_file.exists():
                memories = await self._parse_memories_from_md(category_file)
                for memory in memories:
                    memory['category'] = category
                    all_memories.append(memory)
        
        stats.memories_processed = len(all_memories)
        
        # Find duplicates using content similarity
        duplicates = []
        seen_hashes = set()
        
        for i, memory in enumerate(all_memories):
            content = memory.get('content', '')
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if content_hash in seen_hashes:
                duplicates.append(i)
            else:
                seen_hashes.add(content_hash)
                
                # Check for similar (not exact) duplicates
                for j, other in enumerate(all_memories[:i]):
                    if self._calculate_similarity(content, other.get('content', '')) > self.similarity_threshold:
                        # Keep the one with higher importance
                        if memory.get('importance', 0) < other.get('importance', 0):
                            duplicates.append(i)
                        else:
                            duplicates.append(j)
                        break
        
        stats.duplicates_removed = len(set(duplicates))
        
        if not self.dry_run and duplicates:
            # Remove duplicates from their respective categories
            await self._remove_duplicate_memories(all_memories, duplicates)
        
        logger.info(f"Removed {stats.duplicates_removed} duplicate memories")
        
        return stats
    
    async def archive_old_memories(self) -> CleaningStats:
        """
        Archive old but important memories
        
        Returns:
            Cleaning statistics
        """
        stats = CleaningStats()
        
        for category in SemanticCategory:
            policy = self.retention_policies[category]
            
            if not policy.archive_enabled:
                continue
            
            category_file = self.base_dir / category.value / f"{category.value}.md"
            if not category_file.exists():
                continue
            
            memories = await self._parse_memories_from_md(category_file)
            memories_to_archive = []
            
            for memory in memories:
                memory_date = memory.get('timestamp', datetime.now())
                importance = memory.get('importance', 0.5)
                
                # Archive old memories with moderate to high importance
                if policy.is_expired(memory_date) and importance >= 0.5:
                    memories_to_archive.append(memory)
            
            if memories_to_archive and not self.dry_run:
                await self._archive_memories(category, memories_to_archive)
                stats.memories_archived += len(memories_to_archive)
        
        logger.info(f"Archived {stats.memories_archived} old memories")
        
        return stats
    
    async def consolidate_memories(self) -> CleaningStats:
        """
        Consolidate similar memories into summaries
        
        Returns:
            Cleaning statistics
        """
        stats = CleaningStats()
        
        for category in SemanticCategory:
            category_file = self.base_dir / category.value / f"{category.value}.md"
            if not category_file.exists():
                continue
            
            memories = await self._parse_memories_from_md(category_file)
            
            # Group similar memories
            memory_groups = await self._group_similar_memories(memories)
            
            # Consolidate groups with more than 3 similar memories
            consolidated = []
            for group in memory_groups:
                if len(group) > 3:
                    summary = await self._create_memory_summary(group)
                    consolidated.append(summary)
                    stats.memories_consolidated += len(group)
            
            if consolidated and not self.dry_run:
                # Add consolidated summaries to category
                await self._add_consolidated_memories(category_file, consolidated)
        
        logger.info(f"Consolidated {stats.memories_consolidated} memories")
        
        return stats
    
    async def _parse_memories_from_md(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse memories from an MD file"""
        memories = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple parser - split by memory delimiter
            memory_blocks = content.split('### [')
            
            for block in memory_blocks[1:]:  # Skip header
                memory = {}
                
                # Extract memory ID
                if ']' in block:
                    memory_id = block.split(']')[0]
                    memory['id'] = memory_id
                
                # Extract timestamp
                if '**' in block:
                    lines = block.split('\n')
                    for line in lines:
                        if line.startswith('**Importance:**'):
                            try:
                                importance = float(line.split(':')[1].strip())
                                memory['importance'] = importance
                            except:
                                memory['importance'] = 0.5
                
                # Extract content
                if '---' in block:
                    content_part = block.split('---')[0]
                    # Remove metadata lines
                    content_lines = [l for l in content_part.split('\n') 
                                   if not l.startswith('**') and l.strip()]
                    memory['content'] = '\n'.join(content_lines).strip()
                
                # Extract timestamp from first line
                first_line = block.split('\n')[0]
                try:
                    date_str = first_line.split(']')[1].strip()
                    memory['timestamp'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except:
                    memory['timestamp'] = datetime.now()
                
                if memory.get('content'):
                    memories.append(memory)
        
        except Exception as e:
            logger.error(f"Error parsing memories from {file_path}: {e}")
        
        return memories
    
    async def _archive_memories(self, category: SemanticCategory, memories: List[Dict]):
        """Archive memories to archive directory"""
        archive_category_dir = self.archive_dir / category.value
        archive_category_dir.mkdir(parents=True, exist_ok=True)
        
        # Create archive file with timestamp
        archive_file = archive_category_dir / f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        content = f"# Archived {category.value.title()} Memories\n"
        content += f"**Archived on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for memory in memories:
            content += f"### [{memory.get('id', 'unknown')}] {memory.get('timestamp', 'unknown')}\n"
            content += f"**Importance:** {memory.get('importance', 0.5)}\n"
            content += f"{memory.get('content', '')}\n"
            content += "---\n"
        
        archive_file.write_text(content, encoding='utf-8')
        
        logger.debug(f"Archived {len(memories)} memories to {archive_file}")
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    async def _group_similar_memories(self, memories: List[Dict]) -> List[List[Dict]]:
        """Group similar memories together"""
        groups = []
        used = set()
        
        for i, memory in enumerate(memories):
            if i in used:
                continue
            
            group = [memory]
            used.add(i)
            
            for j, other in enumerate(memories[i+1:], i+1):
                if j in used:
                    continue
                
                similarity = self._calculate_similarity(
                    memory.get('content', ''),
                    other.get('content', '')
                )
                
                if similarity > 0.7:  # High similarity threshold for grouping
                    group.append(other)
                    used.add(j)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    async def _create_memory_summary(self, memories: List[Dict]) -> Dict:
        """Create a summary from a group of similar memories"""
        # Simple summary - can be enhanced with AI
        contents = [m.get('content', '') for m in memories]
        timestamps = [m.get('timestamp', datetime.now()) for m in memories]
        importances = [m.get('importance', 0.5) for m in memories]
        
        summary = {
            'id': hashlib.md5(f"summary_{datetime.now().isoformat()}".encode()).hexdigest()[:8],
            'timestamp': max(timestamps),
            'importance': max(importances),
            'content': f"[CONSOLIDATED SUMMARY of {len(memories)} memories]\n" + 
                      f"Date range: {min(timestamps).strftime('%Y-%m-%d')} to {max(timestamps).strftime('%Y-%m-%d')}\n" +
                      f"Common theme: {contents[0][:100]}...\n" +
                      f"[{len(memories)} similar memories consolidated]"
        }
        
        return summary
    
    async def save_cleaning_report(self, stats: CleaningStats):
        """Save cleaning report to log file"""
        report_file = self.log_dir / f"cleaning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'stats': stats.to_dict(),
            'policies': {
                cat.value: {
                    'retention_days': pol.retention_days,
                    'importance_threshold': pol.importance_threshold
                }
                for cat, pol in self.retention_policies.items()
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Cleaning report saved to {report_file}")
    
    def _merge_stats(self, main_stats: CleaningStats, new_stats: CleaningStats):
        """Merge statistics from different operations"""
        main_stats.memories_processed += new_stats.memories_processed
        main_stats.memories_deleted += new_stats.memories_deleted
        main_stats.memories_archived += new_stats.memories_archived
        main_stats.duplicates_removed += new_stats.duplicates_removed
        main_stats.memories_consolidated += new_stats.memories_consolidated
        main_stats.total_space_freed_kb += new_stats.total_space_freed_kb
        main_stats.errors.extend(new_stats.errors)
        main_stats.warnings.extend(new_stats.warnings)
    
    async def _update_category_file(self, file_path: Path, memories: List[Dict]):
        """Update category file with filtered memories"""
        # Read header
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find where memories start
        memory_start = 0
        for i, line in enumerate(lines):
            if '## 📝 Historical Memories' in line:
                memory_start = i + 2  # Skip header and blank line
                break
        
        # Keep header and slots
        new_content = ''.join(lines[:memory_start])
        
        # Add filtered memories
        for memory in memories:
            new_content += f"\n### [{memory.get('id', 'unknown')}] {memory.get('timestamp', 'unknown')}\n"
            new_content += f"**Importance:** {memory.get('importance', 0.5)}\n"
            new_content += f"{memory.get('content', '')}\n"
            new_content += "---\n"
        
        # Write updated content
        file_path.write_text(new_content, encoding='utf-8')
    
    async def _remove_duplicate_memories(self, all_memories: List[Dict], duplicate_indices: List[int]):
        """Remove duplicate memories from their categories"""
        # Group duplicates by category
        duplicates_by_category = {}
        for idx in set(duplicate_indices):
            memory = all_memories[idx]
            category = memory.get('category')
            if category:
                if category not in duplicates_by_category:
                    duplicates_by_category[category] = []
                duplicates_by_category[category].append(memory['id'])
        
        # Remove from each category file
        for category, memory_ids in duplicates_by_category.items():
            category_file = self.base_dir / category.value / f"{category.value}.md"
            if category_file.exists():
                memories = await self._parse_memories_from_md(category_file)
                filtered = [m for m in memories if m.get('id') not in memory_ids]
                await self._update_category_file(category_file, filtered)
    
    async def _add_consolidated_memories(self, file_path: Path, consolidated: List[Dict]):
        """Add consolidated memory summaries to category file"""
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write("\n## 📊 Consolidated Summaries\n\n")
            for summary in consolidated:
                f.write(f"### [{summary['id']}] {summary['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Type:** Consolidated Summary\n")
                f.write(f"**Importance:** {summary['importance']}\n")
                f.write(f"{summary['content']}\n")
                f.write("---\n")
    
    async def reorganize_categories(self):
        """Reorganize category files for optimal structure"""
        logger.info("Reorganizing category files...")
        # Implementation for file reorganization
        pass
    
    async def clean_orphaned_files(self):
        """Clean up orphaned or temporary files"""
        logger.info("Cleaning orphaned files...")
        # Implementation for orphaned file cleanup
        pass
    
    async def optimize_storage(self):
        """Optimize storage by compressing old archives"""
        logger.info("Optimizing storage...")
        # Implementation for storage optimization
        pass
    
    def stop_scheduler(self):
        """Stop the cleaning scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Cleaning scheduler stopped")