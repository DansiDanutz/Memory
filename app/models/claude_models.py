"""
Pydantic models for Claude API requests and responses
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    """Message roles in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ToneType(str, Enum):
    """Available response tones"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    EMPATHETIC = "empathetic"
    CASUAL = "casual"
    FORMAL = "formal"
    SUPPORTIVE = "supportive"

class ConversationMessage(BaseModel):
    """Single message in conversation"""
    role: MessageRole = Field(default=MessageRole.USER)
    content: str = Field(..., min_length=1, max_length=10000)
    timestamp: Optional[datetime] = None
    sender: Optional[str] = None

class AnalyzeRequest(BaseModel):
    """Request model for message analysis"""
    message: str = Field(..., min_length=1, max_length=10000, description="Message to analyze")
    context: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Previous conversation context"
    )
    user_id: Optional[str] = Field(default=None, description="User identifier for personalization")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

class AnalyzeResponse(BaseModel):
    """Response model for message analysis"""
    sentiment: str = Field(..., description="Detected sentiment")
    intent: str = Field(..., description="Detected intent")
    category: str = Field(..., description="Memory category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence")
    tags: List[str] = Field(default_factory=list, description="Extracted tags")
    is_command: bool = Field(default=False, description="Whether message is a command")
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities from message"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Message priority")
    suggested_response_tone: str = Field(default="friendly", description="Suggested response tone")

class GenerateRequest(BaseModel):
    """Request model for response generation"""
    message: str = Field(..., min_length=1, max_length=10000, description="Message to respond to")
    context: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Conversation history"
    )
    tone: ToneType = Field(default=ToneType.FRIENDLY, description="Desired response tone")
    max_length: Optional[int] = Field(default=500, ge=50, le=2000, description="Maximum response length")
    user_id: Optional[str] = Field(default=None, description="User identifier for personalization")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

class GenerateResponse(BaseModel):
    """Response model for generated text"""
    response: str = Field(..., description="Generated response")
    tone_used: str = Field(..., description="Tone used in response")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Generation confidence")

class SummarizeRequest(BaseModel):
    """Request model for conversation summarization"""
    messages: List[ConversationMessage] = Field(..., min_items=1, description="Messages to summarize")
    max_length: int = Field(default=500, ge=50, le=2000, description="Maximum summary length")
    focus_topics: Optional[List[str]] = Field(default=None, description="Topics to focus on")
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError("At least one message required for summarization")
        return v

class SummarizeResponse(BaseModel):
    """Response model for summarization"""
    summary: str = Field(..., description="Conversation summary")
    key_points: List[str] = Field(default_factory=list, description="Key points from conversation")
    action_items: List[str] = Field(default_factory=list, description="Identified action items")
    topics: List[str] = Field(default_factory=list, description="Main topics discussed")

class ExtractMemoryRequest(BaseModel):
    """Request model for memory extraction"""
    message: str = Field(..., min_length=1, max_length=10000, description="Message to extract memory from")
    context: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Conversation context"
    )
    user_id: Optional[str] = Field(default=None, description="User identifier")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

class ExtractMemoryResponse(BaseModel):
    """Response model for memory extraction"""
    content: str = Field(..., description="Core memory content")
    category: str = Field(..., description="Memory category")
    importance: int = Field(..., ge=1, le=10, description="Memory importance")
    tags: List[str] = Field(default_factory=list, description="Memory tags")
    people_mentioned: List[str] = Field(default_factory=list, description="People mentioned")
    locations: List[str] = Field(default_factory=list, description="Locations mentioned")
    dates: List[str] = Field(default_factory=list, description="Dates mentioned")
    action_items: List[str] = Field(default_factory=list, description="Action items")
    summary: str = Field(..., max_length=200, description="Brief summary")

class ClaudeStatusResponse(BaseModel):
    """Response model for Claude service status"""
    available: bool = Field(..., description="Whether Claude service is available")
    model: str = Field(..., description="Claude model being used")
    api_key_configured: bool = Field(..., description="Whether API key is configured")
    connection_status: str = Field(..., description="Connection status")
    error: Optional[str] = Field(default=None, description="Error message if any")

class ClaudeHealthResponse(BaseModel):
    """Response model for Claude health check"""
    status: str = Field(..., description="Health status")
    available: bool = Field(..., description="Service availability")
    model: str = Field(..., description="Model in use")
    response_time: Optional[float] = Field(default=None, description="API response time in seconds")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Time of health check")
    error: Optional[str] = Field(default=None, description="Error details if any")

class ClaudeUsageStats(BaseModel):
    """Claude API usage statistics"""
    available: bool = Field(..., description="Service availability")
    model: str = Field(..., description="Model name")
    requests_today: int = Field(default=0, description="Requests made today")
    tokens_used: int = Field(default=0, description="Total tokens used")
    cache_hits: int = Field(default=0, description="Cache hits")
    avg_response_time: float = Field(default=0.0, description="Average response time")

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")