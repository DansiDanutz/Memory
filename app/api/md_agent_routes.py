#!/usr/bin/env python3
"""
API Routes for MD Agent (FastAPI)
Provides endpoints to trigger and monitor transcript processing
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import asyncio
from datetime import datetime

# Import MD processor
from ..agents.md_processor import get_processor

logger = logging.getLogger(__name__)

# Create Router
router = APIRouter(prefix="/api/md-agent", tags=["md-agent"])

# Pydantic models for requests
class ProcessRequest(BaseModel):
    contact_id: Optional[str] = None

class StartProcessorRequest(BaseModel):
    interval_minutes: int = 30

class TestCategorizationRequest(BaseModel):
    text: str
    contact_id: Optional[str] = "test_contact"

@router.post("/process")
async def process_transcripts(request: ProcessRequest = Body(default=ProcessRequest())):
    """
    Process transcripts for all contacts or a specific contact
    
    Body (optional):
    - contact_id: specific contact ID to process
    
    Returns:
        Processing results
    """
    try:
        # Get processor instance
        processor = get_processor()
        
        # Process transcripts
        if request.contact_id:
            logger.info(f"Processing transcripts for contact: {request.contact_id}")
            results = await processor.process_contact(request.contact_id)
        else:
            logger.info("Processing transcripts for all contacts")
            results = await processor.process_all()
        
        return {
            'status': 'success',
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing transcripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_processor_status():
    """
    Get MD Agent processor status and statistics
    
    Returns:
        Processor status information
    """
    try:
        # Get processor instance
        processor = get_processor()
        
        # Get status
        status = await processor.get_status()
        
        return {
            'status': 'success',
            'data': status,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting processor status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_processor(request: StartProcessorRequest = Body(default=StartProcessorRequest())):
    """
    Start the background processor
    
    Body:
    - interval_minutes: Processing interval in minutes (default: 30)
    
    Returns:
        Start confirmation
    """
    try:
        # Get or create processor with specified interval
        processor = get_processor(process_interval_minutes=request.interval_minutes)
        
        # Start processor
        await processor.start()
        
        return {
            'status': 'success',
            'message': f'MD Agent processor started with {request.interval_minutes} minute interval',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting processor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_processor():
    """
    Stop the background processor
    
    Returns:
        Stop confirmation
    """
    try:
        # Get processor instance
        processor = get_processor()
        
        # Stop processor
        await processor.stop()
        
        return {
            'status': 'success',
            'message': 'MD Agent processor stopped',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping processor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reprocess")
async def reprocess_all():
    """
    Force reprocess all transcripts
    
    Returns:
        Reprocessing results
    """
    try:
        # Get processor instance
        processor = get_processor()
        
        # Force reprocess
        results = await processor.reprocess_all()
        
        return {
            'status': 'success',
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reprocessing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/distribution")
async def get_memory_distribution():
    """
    Get memory distribution analysis across categories
    
    Returns:
        Distribution analysis
    """
    try:
        # Get processor instance
        processor = get_processor()
        
        # Analyze distribution
        distribution = await processor.analyze_memory_distribution()
        
        return {
            'status': 'success',
            'distribution': distribution,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_categorization(request: TestCategorizationRequest):
    """
    Test categorization with sample text
    
    Body:
    - text: Sample text to categorize
    - contact_id: Contact ID (optional, default: test_contact)
    
    Returns:
        Categorization results
    """
    try:
        # Get processor instance
        processor = get_processor()
        
        # Create test conversation
        test_conv = {
            'timestamp': datetime.now(),
            'direction': 'Incoming Message',
            'message': request.text,
            'raw': f"[{datetime.now()}] Test\n{request.text}"
        }
        
        # Analyze using MD Agent
        memories = await processor.agent.analyze_conversation(test_conv, request.contact_id)
        
        # Convert memories to JSON-serializable format
        results = []
        for memory in memories:
            results.append({
                'content': memory.content,
                'category': memory.category,
                'timestamp': memory.timestamp.isoformat(),
                'tags': memory.tags,
                'importance': memory.importance,
                'source': memory.source,
                'context': memory.context
            })
        
        return {
            'status': 'success',
            'text': request.text,
            'memories': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing categorization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    Health check endpoint for MD Agent
    
    Returns:
        Health status
    """
    try:
        # Get processor instance
        processor = get_processor()
        
        # Check AI availability
        ai_status = 'enabled' if processor.agent.ai_enabled else 'disabled'
        
        return {
            'status': 'healthy',
            'service': 'MD Agent',
            'ai_status': ai_status,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'service': 'MD Agent',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }