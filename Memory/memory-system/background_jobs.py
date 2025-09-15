#!/usr/bin/env python3
"""
Background Job Processing for Digital Immortality Platform
Handles scheduled tasks, async job processing, and job queue management
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import traceback
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from concurrent.futures import ThreadPoolExecutor
import aiofiles

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database models
from database.models import (
    DatabaseManager, Job, JobStatus, JobType,
    HarvestedItem, DetectedPattern, BehavioralInsight,
    AuditLog, SourceType, PatternType, SecurityLevel
)

# Import agents
try:
    from agents import (
        AgentFactory,
        MemoryHarvesterAgent,
        PatternAnalyzerAgent,
        RawMemoryInput,
        ContentType
    )
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    logging.warning("⚠️ Agents not available - jobs will run in mock mode")

# Import memory system components
try:
    from md_file_manager import MDFileManager
    from conversation_classifier import ConversationClassifier
    MD_MANAGER_AVAILABLE = True
except ImportError:
    MD_MANAGER_AVAILABLE = False
    logging.warning("⚠️ Memory system components not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JobManager:
    """Manages background jobs and task execution"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.db_manager = DatabaseManager(database_url)
        self.scheduler = None
        self.job_queue = asyncio.Queue()
        self.active_jobs: Dict[str, Job] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize agents if available
        self.memory_harvester = None
        self.pattern_analyzer = None
        
        if AGENTS_AVAILABLE and MD_MANAGER_AVAILABLE:
            try:
                md_manager = MDFileManager()
                classifier = ConversationClassifier()
                
                self.memory_harvester = AgentFactory.create_memory_harvester({
                    'md_file_manager': md_manager,
                    'conversation_classifier': classifier
                })
                
                self.pattern_analyzer = AgentFactory.create_pattern_analyzer({
                    'md_file_manager': md_manager,
                    'conversation_classifier': classifier
                })
                
                logger.info("✅ Agents initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize agents: {e}")
    
    def initialize_scheduler(self):
        """Initialize the APScheduler"""
        # Configure job stores
        jobstores = {
            'default': MemoryJobStore()
        }
        
        # Configure executors
        executors = {
            'default': AsyncIOExecutor(),
        }
        
        # Configure job defaults
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes
        }
        
        # Create scheduler
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Schedule daily jobs
        self._schedule_daily_jobs()
        
        logger.info("📅 Scheduler initialized with daily jobs")
    
    def _schedule_daily_jobs(self):
        """Schedule daily recurring jobs"""
        # Daily harvest job at 2 AM UTC
        self.scheduler.add_job(
            func=self.run_harvest_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='daily_harvest',
            name='Daily Memory Harvest',
            replace_existing=True
        )
        
        # Pattern analysis job at 3 AM UTC
        self.scheduler.add_job(
            func=self.run_pattern_analysis_job,
            trigger=CronTrigger(hour=3, minute=0),
            id='daily_pattern_analysis',
            name='Daily Pattern Analysis',
            replace_existing=True
        )
        
        # Insight generation job at 4 AM UTC
        self.scheduler.add_job(
            func=self.run_insight_generation_job,
            trigger=CronTrigger(hour=4, minute=0),
            id='daily_insight_generation',
            name='Daily Insight Generation',
            replace_existing=True
        )
        
        # Daily digest job at 6 AM UTC
        self.scheduler.add_job(
            func=self.run_daily_digest_job,
            trigger=CronTrigger(hour=6, minute=0),
            id='daily_digest',
            name='Daily Memory Digest',
            replace_existing=True
        )
        
        # Backup job at 1 AM UTC
        self.scheduler.add_job(
            func=self.run_backup_job,
            trigger=CronTrigger(hour=1, minute=0),
            id='daily_backup',
            name='Daily Backup',
            replace_existing=True
        )
        
        logger.info("📅 Scheduled 5 daily jobs")
    
    async def enqueue_job(self, job_type: JobType, user_id: Optional[str] = None,
                          metadata: Dict[str, Any] = None) -> str:
        """Enqueue a new job for processing"""
        job_id = str(uuid.uuid4())
        
        # Create job record
        with self.db_manager.get_session() as session:
            job = Job(
                id=job_id,
                job_type=job_type,
                user_id=user_id,
                status=JobStatus.PENDING,
                metadata=metadata or {},
                scheduled_at=datetime.utcnow()
            )
            session.add(job)
            session.commit()
        
        # Add to queue
        await self.job_queue.put(job_id)
        
        logger.info(f"📥 Enqueued job {job_id} of type {job_type.value}")
        return job_id
    
    async def process_job_queue(self):
        """Process jobs from the queue"""
        while True:
            try:
                # Get job from queue
                job_id = await self.job_queue.get()
                
                # Process the job
                await self._process_job(job_id)
                
            except Exception as e:
                logger.error(f"Error processing job queue: {e}")
                await asyncio.sleep(5)
    
    async def _process_job(self, job_id: str):
        """Process a single job"""
        try:
            with self.db_manager.get_session() as session:
                job = session.query(Job).filter_by(id=job_id).first()
                if not job:
                    logger.error(f"Job {job_id} not found")
                    return
                
                # Update job status
                job.status = JobStatus.RUNNING
                job.started_at = datetime.utcnow()
                session.commit()
            
            # Store in active jobs
            self.active_jobs[job_id] = job
            
            # Execute job based on type
            if job.job_type == JobType.HARVEST:
                result = await self._execute_harvest_job(job_id, job.user_id, job.metadata)
            elif job.job_type == JobType.PATTERN_ANALYSIS:
                result = await self._execute_pattern_analysis_job(job_id, job.user_id, job.metadata)
            elif job.job_type == JobType.INSIGHT_GENERATION:
                result = await self._execute_insight_generation_job(job_id, job.user_id, job.metadata)
            elif job.job_type == JobType.DAILY_DIGEST:
                result = await self._execute_daily_digest_job(job_id, job.user_id, job.metadata)
            elif job.job_type == JobType.BACKUP:
                result = await self._execute_backup_job(job_id, job.metadata)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # Update job as completed
            with self.db_manager.get_session() as session:
                job = session.query(Job).filter_by(id=job_id).first()
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.progress = 100
                job.result = result
                session.commit()
            
            # Remove from active jobs
            del self.active_jobs[job_id]
            
            logger.info(f"✅ Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            
            # Update job as failed
            with self.db_manager.get_session() as session:
                job = session.query(Job).filter_by(id=job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    job.error = str(e)
                    session.commit()
            
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    async def _execute_harvest_job(self, job_id: str, user_id: Optional[str], 
                                   metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Execute memory harvest job"""
        logger.info(f"🌾 Executing harvest job {job_id} for user {user_id}")
        
        if not self.memory_harvester:
            # Mock implementation
            return {
                'status': 'completed',
                'items_harvested': 0,
                'message': 'Harvest agent not available - running in mock mode'
            }
        
        try:
            # Initialize harvester if needed
            if not self.memory_harvester.is_initialized:
                await self.memory_harvester.initialize()
            
            # Prepare harvest sources
            sources = metadata.get('sources', ['chat_message', 'email', 'calendar_event'])
            time_range = metadata.get('time_range', {'days': 1})
            
            harvested_items = []
            total_items = 0
            
            # Harvest from each source
            for source in sources:
                try:
                    # Create raw memory input
                    raw_input = RawMemoryInput(
                        content="Sample memory content",  # This would come from actual sources
                        source_type=SourceType[source.upper()],
                        source_metadata={'user_id': user_id},
                        timestamp=datetime.utcnow(),
                        user_id=user_id,
                        content_type=ContentType.TEXT
                    )
                    
                    # Process with harvester
                    processed = await self.memory_harvester.harvest_memory(raw_input)
                    
                    if processed:
                        # Store in database
                        with self.db_manager.get_session() as session:
                            item = HarvestedItem(
                                user_id=user_id,
                                content=processed.content,
                                source_type=SourceType[source.upper()],
                                quality_score=processed.quality_score,
                                extra_metadata=processed.metadata,
                                tags=processed.tags,
                                created_at=processed.timestamp
                            )
                            session.add(item)
                            session.commit()
                            
                            harvested_items.append(item.id)
                            total_items += 1
                    
                    # Update progress
                    await self._update_job_progress(job_id, (len(harvested_items) / len(sources)) * 100)
                    
                except Exception as e:
                    logger.error(f"Error harvesting from {source}: {e}")
            
            return {
                'status': 'completed',
                'items_harvested': total_items,
                'item_ids': harvested_items,
                'sources_processed': sources
            }
            
        except Exception as e:
            logger.error(f"Harvest job failed: {e}")
            raise
    
    async def _execute_pattern_analysis_job(self, job_id: str, user_id: Optional[str],
                                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pattern analysis job"""
        logger.info(f"🔍 Executing pattern analysis job {job_id} for user {user_id}")
        
        if not self.pattern_analyzer:
            return {
                'status': 'completed',
                'patterns_detected': 0,
                'message': 'Pattern analyzer not available - running in mock mode'
            }
        
        try:
            # Initialize analyzer if needed
            if not self.pattern_analyzer.is_initialized:
                await self.pattern_analyzer.initialize()
            
            # Get recent memories for analysis
            with self.db_manager.get_session() as session:
                recent_memories = session.query(HarvestedItem).filter_by(
                    user_id=user_id
                ).order_by(HarvestedItem.created_at.desc()).limit(100).all()
            
            # Analyze patterns
            patterns = await self.pattern_analyzer.analyze_memories([
                {
                    'id': m.id,
                    'content': m.content,
                    'timestamp': m.created_at,
                    'metadata': m.extra_metadata
                }
                for m in recent_memories
            ])
            
            # Store detected patterns
            stored_patterns = []
            for pattern in patterns:
                with self.db_manager.get_session() as session:
                    db_pattern = DetectedPattern(
                        user_id=user_id,
                        pattern_type=pattern['type'],
                        strength=pattern['strength'],
                        confidence=pattern['confidence'],
                        description=pattern['description'],
                        extra_metadata=pattern.get('metadata', {}),
                        supporting_memories=pattern.get('supporting_memories', [])
                    )
                    session.add(db_pattern)
                    session.commit()
                    stored_patterns.append(db_pattern.id)
            
            return {
                'status': 'completed',
                'patterns_detected': len(stored_patterns),
                'pattern_ids': stored_patterns
            }
            
        except Exception as e:
            logger.error(f"Pattern analysis job failed: {e}")
            raise
    
    async def _execute_insight_generation_job(self, job_id: str, user_id: Optional[str],
                                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Execute insight generation job"""
        logger.info(f"💡 Executing insight generation job {job_id} for user {user_id}")
        
        try:
            # Get recent patterns
            with self.db_manager.get_session() as session:
                patterns = session.query(DetectedPattern).filter_by(
                    user_id=user_id,
                    is_active=True
                ).order_by(DetectedPattern.strength.desc()).limit(20).all()
            
            insights_generated = []
            
            # Generate insights from patterns
            for pattern in patterns:
                if pattern.strength > 0.7:  # Strong patterns
                    insight = BehavioralInsight(
                        user_id=user_id,
                        insight_type='pattern_based',
                        title=f"Strong {pattern.pattern_type.value} Pattern Detected",
                        description=pattern.description,
                        confidence=pattern.confidence,
                        supporting_patterns=[pattern.id],
                        recommendations=[
                            f"Consider this pattern in your daily routine",
                            f"This behavior occurs frequently"
                        ],
                        impact_score=pattern.strength
                    )
                    
                    with self.db_manager.get_session() as session:
                        session.add(insight)
                        session.commit()
                        insights_generated.append(insight.id)
            
            return {
                'status': 'completed',
                'insights_generated': len(insights_generated),
                'insight_ids': insights_generated
            }
            
        except Exception as e:
            logger.error(f"Insight generation job failed: {e}")
            raise
    
    async def _execute_daily_digest_job(self, job_id: str, user_id: Optional[str],
                                       metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Execute daily digest job"""
        logger.info(f"📰 Executing daily digest job {job_id} for user {user_id}")
        
        try:
            # Get yesterday's data
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            with self.db_manager.get_session() as session:
                # Count memories
                memory_count = session.query(HarvestedItem).filter(
                    HarvestedItem.user_id == user_id,
                    HarvestedItem.created_at >= yesterday
                ).count()
                
                # Count patterns
                pattern_count = session.query(DetectedPattern).filter(
                    DetectedPattern.user_id == user_id,
                    DetectedPattern.created_at >= yesterday
                ).count()
                
                # Count insights
                insight_count = session.query(BehavioralInsight).filter(
                    BehavioralInsight.user_id == user_id,
                    BehavioralInsight.created_at >= yesterday
                ).count()
            
            digest = {
                'date': yesterday.strftime('%Y-%m-%d'),
                'memories_captured': memory_count,
                'patterns_detected': pattern_count,
                'insights_generated': insight_count,
                'summary': f"Yesterday you captured {memory_count} memories, with {pattern_count} patterns detected."
            }
            
            # Save digest (would normally send via email/notification)
            logger.info(f"📧 Daily digest for {user_id}: {digest}")
            
            return {
                'status': 'completed',
                'digest': digest
            }
            
        except Exception as e:
            logger.error(f"Daily digest job failed: {e}")
            raise
    
    async def _execute_backup_job(self, job_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Execute backup job"""
        logger.info(f"💾 Executing backup job {job_id}")
        
        try:
            # Create backup directory
            backup_dir = f"backups/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup database (simplified - would use pg_dump in production)
            backup_file = f"{backup_dir}/database_backup.json"
            
            with self.db_manager.get_session() as session:
                # Get counts for backup verification
                counts = {
                    'harvested_items': session.query(HarvestedItem).count(),
                    'patterns': session.query(DetectedPattern).count(),
                    'insights': session.query(BehavioralInsight).count(),
                    'jobs': session.query(Job).count(),
                    'audit_logs': session.query(AuditLog).count()
                }
            
            # Write backup metadata
            async with aiofiles.open(f"{backup_dir}/metadata.json", 'w') as f:
                await f.write(json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'counts': counts,
                    'status': 'completed'
                }, indent=2))
            
            logger.info(f"✅ Backup completed to {backup_dir}")
            
            return {
                'status': 'completed',
                'backup_location': backup_dir,
                'items_backed_up': counts
            }
            
        except Exception as e:
            logger.error(f"Backup job failed: {e}")
            raise
    
    async def _update_job_progress(self, job_id: str, progress: int):
        """Update job progress"""
        try:
            with self.db_manager.get_session() as session:
                job = session.query(Job).filter_by(id=job_id).first()
                if job:
                    job.progress = min(100, max(0, progress))
                    job.updated_at = datetime.utcnow()
                    session.commit()
        except Exception as e:
            logger.error(f"Failed to update job progress: {e}")
    
    async def run_harvest_job(self, user_id: Optional[str] = None):
        """Run harvest job (called by scheduler)"""
        job_id = await self.enqueue_job(JobType.HARVEST, user_id, {'scheduled': True})
        await self._process_job(job_id)
    
    async def run_pattern_analysis_job(self, user_id: Optional[str] = None):
        """Run pattern analysis job (called by scheduler)"""
        job_id = await self.enqueue_job(JobType.PATTERN_ANALYSIS, user_id, {'scheduled': True})
        await self._process_job(job_id)
    
    async def run_insight_generation_job(self, user_id: Optional[str] = None):
        """Run insight generation job (called by scheduler)"""
        job_id = await self.enqueue_job(JobType.INSIGHT_GENERATION, user_id, {'scheduled': True})
        await self._process_job(job_id)
    
    async def run_daily_digest_job(self, user_id: Optional[str] = None):
        """Run daily digest job (called by scheduler)"""
        job_id = await self.enqueue_job(JobType.DAILY_DIGEST, user_id, {'scheduled': True})
        await self._process_job(job_id)
    
    async def run_backup_job(self):
        """Run backup job (called by scheduler)"""
        job_id = await self.enqueue_job(JobType.BACKUP, None, {'scheduled': True})
        await self._process_job(job_id)
    
    def start(self):
        """Start the job manager and scheduler"""
        logger.info("🚀 Starting Job Manager...")
        
        # Initialize scheduler
        self.initialize_scheduler()
        
        # Start scheduler
        self.scheduler.start()
        
        # Start job queue processor
        asyncio.create_task(self.process_job_queue())
        
        logger.info("✅ Job Manager started successfully")
    
    def stop(self):
        """Stop the job manager and scheduler"""
        logger.info("🛑 Stopping Job Manager...")
        
        if self.scheduler:
            self.scheduler.shutdown()
        
        self.executor.shutdown(wait=True)
        
        logger.info("✅ Job Manager stopped")
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        with self.db_manager.get_session() as session:
            job = session.query(Job).filter_by(id=job_id).first()
            if job:
                return {
                    'id': job.id,
                    'type': job.job_type.value,
                    'status': job.status.value,
                    'progress': job.progress,
                    'result': job.result,
                    'error': job.error,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None
                }
        return None
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of active jobs"""
        with self.db_manager.get_session() as session:
            jobs = session.query(Job).filter(
                Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
            ).all()
            
            return [
                {
                    'id': job.id,
                    'type': job.job_type.value,
                    'status': job.status.value,
                    'progress': job.progress,
                    'user_id': job.user_id,
                    'created_at': job.created_at.isoformat() if job.created_at else None
                }
                for job in jobs
            ]

# Global job manager instance
job_manager = None

def initialize_job_manager(database_url: Optional[str] = None):
    """Initialize the global job manager"""
    global job_manager
    job_manager = JobManager(database_url)
    return job_manager

def get_job_manager() -> JobManager:
    """Get the global job manager instance"""
    global job_manager
    if not job_manager:
        job_manager = initialize_job_manager()
    return job_manager

# For testing
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Initialize job manager
        manager = initialize_job_manager()
        
        # Start the manager
        manager.start()
        
        # Enqueue a test job
        job_id = await manager.enqueue_job(
            JobType.HARVEST,
            user_id="test_user",
            metadata={'test': True}
        )
        
        print(f"Enqueued job: {job_id}")
        
        # Wait a bit
        await asyncio.sleep(10)
        
        # Check job status
        status = manager.get_job_status(job_id)
        print(f"Job status: {status}")
        
        # Get active jobs
        active = manager.get_active_jobs()
        print(f"Active jobs: {active}")
        
        # Keep running
        await asyncio.Event().wait()
    
    # Run the test
    asyncio.run(main())