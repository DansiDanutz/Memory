"""
Claude AI API Routes
FastAPI router for Claude AI integration endpoints
"""
import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio

from ..models.claude_models import (
    AnalyzeRequest, AnalyzeResponse,
    GenerateRequest, GenerateResponse,
    SummarizeRequest, SummarizeResponse,
    ExtractMemoryRequest, ExtractMemoryResponse,
    ClaudeStatusResponse, ClaudeHealthResponse,
    ClaudeUsageStats, ErrorResponse,
    ConversationMessage
)
from ..claude_service import ClaudeService, ClaudeAnalysis, MemoryExtraction
from ..utils.claude_utils import (
    RateLimiter, CacheManager,
    get_rate_limiter, get_cache_manager
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/claude", tags=["Claude AI"])

# Initialize Claude service
claude_service = ClaudeService()

# Dependency to check Claude availability
async def check_claude_available():
    """Dependency to ensure Claude service is available"""
    if not claude_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Claude AI service is not available. Please check API key configuration."
        )
    return True

# Rate limiting dependency
async def check_rate_limit(request: Request):
    """Check rate limit for user"""
    rate_limiter = get_rate_limiter()
    user_id = request.headers.get("X-User-ID", request.client.host)
    
    if not await rate_limiter.is_allowed(user_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    return user_id

@router.get("/status", response_model=ClaudeStatusResponse)
async def get_claude_status():
    """Get Claude service availability status"""
    try:
        return ClaudeStatusResponse(
            available=claude_service.is_available(),
            model=claude_service.model,
            api_key_configured=bool(claude_service.api_key),
            connection_status="connected" if claude_service.is_available() else "disconnected",
            error=None if claude_service.is_available() else "API key not configured"
        )
    except Exception as e:
        logger.error(f"Error getting Claude status: {e}")
        return ClaudeStatusResponse(
            available=False,
            model="",
            api_key_configured=False,
            connection_status="error",
            error=str(e)
        )

@router.get("/health", response_model=ClaudeHealthResponse)
async def claude_health_check():
    """Perform health check with API connection test"""
    start_time = time.time()
    
    try:
        if not claude_service.is_available():
            return ClaudeHealthResponse(
                status="unavailable",
                available=False,
                model=claude_service.model,
                response_time=None,
                error="Claude service not configured"
            )
        
        # Test actual API connection
        success, message = await claude_service.test_connection()
        response_time = time.time() - start_time
        
        return ClaudeHealthResponse(
            status="healthy" if success else "unhealthy",
            available=success,
            model=claude_service.model,
            response_time=response_time,
            error=None if success else message
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ClaudeHealthResponse(
            status="error",
            available=False,
            model=claude_service.model,
            response_time=time.time() - start_time,
            error=str(e)
        )

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_message(
    request: AnalyzeRequest,
    _: bool = Depends(check_claude_available),
    user_id: str = Depends(check_rate_limit)
):
    """Analyze message sentiment, intent, and categorization"""
    try:
        # Check cache first
        cache_manager = get_cache_manager()
        cache_key = f"analyze:{claude_service.get_cache_key('analyze', request.message)}"
        cached_result = await cache_manager.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for analyze request from {user_id}")
            return AnalyzeResponse(**cached_result)
        
        # Convert context to format expected by service
        context = None
        if request.context:
            context = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.context
            ]
        
        # Analyze with Claude
        analysis = await claude_service.analyze_message(
            request.message,
            context
        )
        
        # Convert to response model
        response = AnalyzeResponse(
            sentiment=analysis.sentiment,
            intent=analysis.intent,
            category=analysis.category,
            confidence=analysis.confidence,
            tags=analysis.tags,
            is_command=analysis.is_command,
            extracted_entities=analysis.extracted_entities,
            priority=analysis.priority,
            suggested_response_tone=analysis.suggested_response_tone
        )
        
        # Cache the result
        await cache_manager.set(cache_key, response.dict(), ttl=3600)
        
        return response
        
    except Exception as e:
        logger.error(f"Error analyzing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate", response_model=GenerateResponse)
async def generate_response(
    request: GenerateRequest,
    _: bool = Depends(check_claude_available),
    user_id: str = Depends(check_rate_limit)
):
    """Generate contextual response based on message and tone"""
    try:
        # Check cache
        cache_manager = get_cache_manager()
        cache_key = f"generate:{claude_service.get_cache_key('generate', request.message, request.tone.value)}"
        cached_result = await cache_manager.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for generate request from {user_id}")
            return GenerateResponse(**cached_result)
        
        # Convert context
        context = None
        if request.context:
            context = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.context
            ]
        
        # Generate response
        generated_text = await claude_service.generate_response(
            request.message,
            context,
            request.tone.value
        )
        
        # Truncate if needed
        if request.max_length and len(generated_text) > request.max_length:
            generated_text = generated_text[:request.max_length]
        
        response = GenerateResponse(
            response=generated_text,
            tone_used=request.tone.value,
            confidence=0.95  # Claude typically has high confidence
        )
        
        # Cache result
        await cache_manager.set(cache_key, response.dict(), ttl=3600)
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_conversation(
    request: SummarizeRequest,
    _: bool = Depends(check_claude_available),
    user_id: str = Depends(check_rate_limit)
):
    """Summarize conversation history"""
    try:
        # Convert messages to format expected by service
        messages = [
            {
                "sender": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            }
            for msg in request.messages
        ]
        
        # Get summary
        summary = await claude_service.summarize_conversation(
            messages,
            request.max_length
        )
        
        # Extract key points and topics (simplified extraction)
        key_points = []
        topics = request.focus_topics or []
        action_items = []
        
        # Parse summary for structured data (in production, Claude would extract these)
        lines = summary.split('\n')
        for line in lines:
            if line.strip().startswith('-'):
                key_points.append(line.strip('- '))
            if 'action' in line.lower() or 'todo' in line.lower():
                action_items.append(line.strip())
        
        return SummarizeResponse(
            summary=summary,
            key_points=key_points[:5],  # Limit to 5 key points
            action_items=action_items[:3],  # Limit to 3 action items
            topics=topics
        )
        
    except Exception as e:
        logger.error(f"Error summarizing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-memory", response_model=ExtractMemoryResponse)
async def extract_memory(
    request: ExtractMemoryRequest,
    _: bool = Depends(check_claude_available),
    user_id: str = Depends(check_rate_limit)
):
    """Extract memories and key information from text"""
    try:
        # Check cache
        cache_manager = get_cache_manager()
        cache_key = f"extract:{claude_service.get_cache_key('extract', request.message)}"
        cached_result = await cache_manager.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for extract request from {user_id}")
            return ExtractMemoryResponse(**cached_result)
        
        # Convert context
        context = None
        if request.context:
            context = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.context
            ]
        
        # Extract memory
        extraction = await claude_service.extract_memory(
            request.message,
            context
        )
        
        response = ExtractMemoryResponse(
            content=extraction.content,
            category=extraction.category,
            importance=extraction.importance,
            tags=extraction.tags,
            people_mentioned=extraction.people_mentioned,
            locations=extraction.locations,
            dates=extraction.dates,
            action_items=extraction.action_items,
            summary=extraction.summary
        )
        
        # Cache result
        await cache_manager.set(cache_key, response.dict(), ttl=3600)
        
        return response
        
    except Exception as e:
        logger.error(f"Error extracting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usage", response_model=ClaudeUsageStats)
async def get_usage_stats(
    _: bool = Depends(check_claude_available)
):
    """Get Claude API usage statistics"""
    try:
        stats = await claude_service.get_usage_stats()
        return ClaudeUsageStats(**stats)
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-cache")
async def clear_cache(user_id: Optional[str] = None):
    """Clear Claude response cache"""
    try:
        cache_manager = get_cache_manager()
        if user_id:
            # Clear cache for specific user
            await cache_manager.clear_pattern(f"*:{user_id}:*")
            return {"message": f"Cache cleared for user {user_id}"}
        else:
            # Clear all cache
            await cache_manager.clear_all()
            return {"message": "All cache cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Note: Exception handlers are added at the app level, not router level
# This function can be called from main.py if needed
async def claude_exception_handler(request: Request, exc: Exception):
    """Handle Claude-specific exceptions"""
    logger.error(f"Claude API error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Claude AI service error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )