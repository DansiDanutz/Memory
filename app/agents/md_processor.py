#!/usr/bin/env python3
"""
MD Processor - Background processor for MD Agent
Handles scheduled and on-demand processing of transcript files
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .md_agent import MDAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MDProcessor:
    """
    Background processor for MD Agent
    Handles scheduled and on-demand processing
    """
    
    def __init__(
        self,
        base_dir: str = 'data/memories',
        use_anthropic: bool = False,
        process_interval_minutes: int = 30
    ):
        """
        Initialize the processor
        
        Args:
            base_dir: Base directory for memory storage
            use_anthropic: Use Anthropic Claude instead of OpenAI
            process_interval_minutes: Processing interval in minutes
        """
        self.agent = MDAgent(base_dir=base_dir, use_anthropic=use_anthropic)
        self.scheduler = AsyncIOScheduler()
        self.process_interval = process_interval_minutes
        self.is_running = False
        self.last_run = None
        self.processing_history = []
        
        # Statistics
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_memories_processed': 0,
            'last_error': None
        }
        
        logger.info(f"📋 MD Processor initialized - Interval: {process_interval_minutes} minutes")
    
    async def start(self) -> None:
        """Start the background processor"""
        if self.is_running:
            logger.warning("Processor is already running")
            return
        
        # Schedule periodic processing
        self.scheduler.add_job(
            self.process_all,
            trigger=IntervalTrigger(minutes=self.process_interval),
            id='md_processor',
            name='MD Agent Processing',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info("✅ MD Processor started")
        
        # Run initial processing
        await self.process_all()
    
    async def stop(self) -> None:
        """Stop the background processor"""
        if not self.is_running:
            logger.warning("Processor is not running")
            return
        
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        
        logger.info("⏹️ MD Processor stopped")
    
    async def process_all(self, contact_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process transcripts for all contacts or a specific contact
        
        Args:
            contact_id: Optional specific contact to process
            
        Returns:
            Processing results
        """
        start_time = datetime.now()
        self.stats['total_runs'] += 1
        
        try:
            if contact_id:
                # Process specific contact
                logger.info(f"Processing transcripts for contact: {contact_id}")
                results = await self.agent.process_contact_transcript(contact_id)
                results = {
                    'contacts_processed': 1,
                    'memories_created': results.get('memories_created', 0),
                    'errors': [],
                    'timestamp': datetime.now().isoformat(),
                    'specific_contact': contact_id
                }
            else:
                # Process all contacts
                logger.info("Processing transcripts for all contacts")
                results = await self.agent.process_all_transcripts()
            
            # Update statistics
            self.stats['successful_runs'] += 1
            self.stats['total_memories_processed'] += results.get('memories_created', 0)
            self.last_run = datetime.now()
            
            # Add to history
            processing_entry = {
                'timestamp': start_time.isoformat(),
                'duration': (datetime.now() - start_time).total_seconds(),
                'contacts_processed': results.get('contacts_processed', 0),
                'memories_created': results.get('memories_created', 0),
                'status': 'success',
                'errors': results.get('errors', [])
            }
            self.processing_history.append(processing_entry)
            
            # Keep only last 100 entries
            if len(self.processing_history) > 100:
                self.processing_history = self.processing_history[-100:]
            
            logger.info(f"✅ Processing completed: {results['memories_created']} memories created")
            
            return results
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(error_msg)
            
            self.stats['failed_runs'] += 1
            self.stats['last_error'] = error_msg
            
            # Add error to history
            processing_entry = {
                'timestamp': start_time.isoformat(),
                'duration': (datetime.now() - start_time).total_seconds(),
                'status': 'failed',
                'error': error_msg
            }
            self.processing_history.append(processing_entry)
            
            return {
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }
    
    async def process_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Process transcript for a specific contact
        
        Args:
            contact_id: Contact identifier
            
        Returns:
            Processing results
        """
        return await self.process_all(contact_id=contact_id)
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get processor status and statistics
        
        Returns:
            Status information
        """
        agent_stats = await self.agent.get_processing_stats()
        
        return {
            'processor': {
                'is_running': self.is_running,
                'process_interval_minutes': self.process_interval,
                'last_run': self.last_run.isoformat() if self.last_run else None,
                'next_run': self._get_next_run_time()
            },
            'statistics': {
                **self.stats,
                'agent_stats': agent_stats
            },
            'recent_history': self.processing_history[-10:] if self.processing_history else []
        }
    
    def _get_next_run_time(self) -> Optional[str]:
        """Get next scheduled run time"""
        if not self.is_running or not self.scheduler.running:
            return None
        
        job = self.scheduler.get_job('md_processor')
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        
        return None
    
    async def reprocess_all(self) -> Dict[str, Any]:
        """
        Force reprocess all transcripts regardless of status
        
        Returns:
            Processing results
        """
        logger.info("Force reprocessing all transcripts")
        
        # Clear processing flags and reprocess
        results = await self.process_all()
        
        return {
            **results,
            'forced_reprocess': True
        }
    
    async def analyze_memory_distribution(self) -> Dict[str, Any]:
        """
        Analyze memory distribution across categories
        
        Returns:
            Distribution analysis
        """
        base_dir = Path('data/memories')
        distribution = {}
        
        # Analyze each contact
        for contact_dir in base_dir.iterdir():
            if not contact_dir.is_dir():
                continue
            
            contact_id = contact_dir.name
            contact_stats = {}
            
            # Count memories in each category file
            for category, config in self.agent.CATEGORIES.items():
                category_file = contact_dir / config['file']
                if category_file.exists():
                    content = category_file.read_text(encoding='utf-8')
                    # Count memory entries (look for ### 📝 pattern)
                    memory_count = content.count('### 📝')
                    contact_stats[category] = memory_count
            
            distribution[contact_id] = contact_stats
        
        # Calculate totals
        total_by_category = {}
        for contact_stats in distribution.values():
            for category, count in contact_stats.items():
                total_by_category[category] = total_by_category.get(category, 0) + count
        
        return {
            'by_contact': distribution,
            'totals': total_by_category,
            'analysis_timestamp': datetime.now().isoformat()
        }

# Global processor instance
_processor_instance = None

def get_processor(
    base_dir: str = 'data/memories',
    use_anthropic: bool = False,
    process_interval_minutes: int = 30
) -> MDProcessor:
    """
    Get or create the global processor instance
    
    Args:
        base_dir: Base directory for memory storage
        use_anthropic: Use Anthropic Claude instead of OpenAI
        process_interval_minutes: Processing interval in minutes
        
    Returns:
        MDProcessor instance
    """
    global _processor_instance
    
    if _processor_instance is None:
        _processor_instance = MDProcessor(
            base_dir=base_dir,
            use_anthropic=use_anthropic,
            process_interval_minutes=process_interval_minutes
        )
    
    return _processor_instance

async def main():
    """Main function for testing"""
    # Create processor
    processor = get_processor(process_interval_minutes=1)  # 1 minute for testing
    
    # Start processor
    await processor.start()
    
    # Wait for a few cycles
    print("Processor started. Waiting for processing cycles...")
    await asyncio.sleep(5)
    
    # Get status
    status = await processor.get_status()
    print("\nProcessor Status:")
    print(json.dumps(status, indent=2))
    
    # Analyze distribution
    distribution = await processor.analyze_memory_distribution()
    print("\nMemory Distribution:")
    print(json.dumps(distribution, indent=2))
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nStopping processor...")
        await processor.stop()

if __name__ == "__main__":
    asyncio.run(main())