"""
Claude AI API Router for Memory App
Provides REST endpoints for Claude AI functionality
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.claude_service import claude_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claude", tags=["Claude AI"])

# Request/Response Models
class MessageAnalysisRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ResponseGenerationRequest(BaseModel):
    message: str
    context: Optional[str] = None
    tone: str = "helpful"

class ConversationMessage(BaseModel):
    sender: str
    content: str

class ConversationSummaryRequest(BaseModel):
    messages: List[ConversationMessage]

class MemoryExtractionRequest(BaseModel):
    text: str

class ClaudeResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    available: bool

def check_claude_availability():
    """Dependency to check if Claude service is available"""
    if not claude_service.is_available():
        raise HTTPException(
            status_code=503, 
            detail="Claude AI service is not available. Please check CLAUDE_API_KEY configuration."
        )

@router.get("/status")
async def claude_status():
    """Check Claude service status"""
    return ClaudeResponse(
        success=True,
        data={"available": claude_service.is_available()},
        available=claude_service.is_available()
    )

@router.post("/analyze", response_model=ClaudeResponse)
async def analyze_message(
    request: MessageAnalysisRequest,
    _: None = Depends(check_claude_availability)
):
    """
    Analyze a message for sentiment, intent, and key information
    """
    try:
        result = await claude_service.analyze_message(
            message=request.message,
            context=request.context
        )
        
        if "error" in result:
            return ClaudeResponse(
                success=False,
                error=result["error"],
                available=result.get("available", False)
            )
        
        return ClaudeResponse(
            success=True,
            data=result,
            available=True
        )
        
    except Exception as e:
        logger.error(f"Message analysis endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate", response_model=ClaudeResponse)
async def generate_response(
    request: ResponseGenerationRequest,
    _: None = Depends(check_claude_availability)
):
    """
    Generate a response to a message
    """
    try:
        result = await claude_service.generate_response(
            message=request.message,
            context=request.context,
            tone=request.tone
        )
        
        if "error" in result:
            return ClaudeResponse(
                success=False,
                error=result["error"],
                available=result.get("available", False)
            )
        
        return ClaudeResponse(
            success=True,
            data=result,
            available=True
        )
        
    except Exception as e:
        logger.error(f"Response generation endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summarize", response_model=ClaudeResponse)
async def summarize_conversation(
    request: ConversationSummaryRequest,
    _: None = Depends(check_claude_availability)
):
    """
    Summarize a conversation thread
    """
    try:
        # Convert Pydantic models to dictionaries
        messages = [{"sender": msg.sender, "content": msg.content} for msg in request.messages]
        
        result = await claude_service.summarize_conversation(messages)
        
        if "error" in result:
            return ClaudeResponse(
                success=False,
                error=result["error"],
                available=result.get("available", False)
            )
        
        return ClaudeResponse(
            success=True,
            data=result,
            available=True
        )
        
    except Exception as e:
        logger.error(f"Conversation summarization endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-memory", response_model=ClaudeResponse)
async def extract_memory_items(
    request: MemoryExtractionRequest,
    _: None = Depends(check_claude_availability)
):
    """
    Extract important information that should be remembered
    """
    try:
        result = await claude_service.extract_memory_items(request.text)
        
        if "error" in result:
            return ClaudeResponse(
                success=False,
                error=result["error"],
                available=result.get("available", False)
            )
        
        return ClaudeResponse(
            success=True,
            data=result,
            available=True
        )
        
    except Exception as e:
        logger.error(f"Memory extraction endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint specifically for Claude
@router.get("/health")
async def claude_health():
    """Health check for Claude AI service"""
    is_available = claude_service.is_available()
    
    return {
        "service": "claude-ai",
        "status": "healthy" if is_available else "unavailable",
        "available": is_available,
        "message": "Claude AI service is ready" if is_available else "CLAUDE_API_KEY not configured"
    }
