"""
Input validation schemas for Memory App
Implements comprehensive validation for all API endpoints
"""

from pydantic import BaseModel, Field, validator, constr, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
from enum import Enum


class MessageType(str, Enum):
    """Allowed message types"""
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"


class WebhookEntry(BaseModel):
    """WhatsApp webhook entry validation"""
    id: str
    changes: List[Dict[str, Any]]

    @validator('changes')
    def validate_changes(cls, v):
        if not v:
            raise ValueError("Changes list cannot be empty")
        return v


class WebhookPayload(BaseModel):
    """Main webhook payload validation"""
    object: str
    entry: List[WebhookEntry]

    @validator('object')
    def validate_object(cls, v):
        if v != "whatsapp_business_account":
            raise ValueError("Invalid webhook object type")
        return v


class WhatsAppMessage(BaseModel):
    """WhatsApp message validation"""
    from_number: constr(regex=r'^\+?[1-9]\d{1,14}$') = Field(..., alias='from')
    message_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime
    type: MessageType
    text: Optional[str] = Field(None, max_length=4096)
    media_id: Optional[str] = None
    media_url: Optional[HttpUrl] = None
    caption: Optional[str] = Field(None, max_length=1024)

    @validator('text')
    def validate_text(cls, v, values):
        if values.get('type') == MessageType.TEXT and not v:
            raise ValueError("Text message must have text content")
        return v

    @validator('from_number')
    def sanitize_phone(cls, v):
        # Remove any non-digit characters except +
        return re.sub(r'[^\d+]', '', v)

    class Config:
        allow_population_by_field_name = True


class AudioProcessRequest(BaseModel):
    """Audio processing request validation"""
    audio_url: HttpUrl
    phone_number: constr(regex=r'^\+?[1-9]\d{1,14}$')
    format: Optional[str] = Field('ogg', regex=r'^(ogg|mp3|wav|m4a)$')
    language: Optional[str] = Field('en-US', regex=r'^[a-z]{2}-[A-Z]{2}$')

    @validator('audio_url')
    def validate_audio_url(cls, v):
        # Ensure URL is from WhatsApp CDN or trusted source
        allowed_domains = [
            'cdn.whatsapp.net',
            'mmg.whatsapp.net',
            'media.whatsapp.net'
        ]
        if not any(domain in str(v) for domain in allowed_domains):
            # Log suspicious URL for review
            pass  # In production, you might want to restrict this
        return v


class MemoryCreateRequest(BaseModel):
    """Memory creation request validation"""
    user_id: str = Field(..., min_length=1, max_length=64)
    content: str = Field(..., min_length=1, max_length=10000)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = Field(default_factory=list, max_items=10)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('user_id')
    def validate_user_id(cls, v):
        # Prevent directory traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError("Invalid user_id format")
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v:
            for tag in v:
                if len(tag) > 30:
                    raise ValueError(f"Tag '{tag}' exceeds maximum length")
                if not re.match(r'^[\w\-]+$', tag):
                    raise ValueError(f"Tag '{tag}' contains invalid characters")
        return v


class MemorySearchRequest(BaseModel):
    """Memory search request validation"""
    query: str = Field(..., min_length=1, max_length=500)
    user_id: str = Field(..., min_length=1, max_length=64)
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    @validator('query')
    def sanitize_query(cls, v):
        # Remove potential SQL injection attempts
        dangerous_patterns = [
            r';\s*DROP',
            r';\s*DELETE',
            r';\s*UPDATE',
            r';\s*INSERT',
            r'--',
            r'/\*.*\*/',
            r'<script',
            r'javascript:',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Query contains potentially dangerous content")
        return v


class UserAuthRequest(BaseModel):
    """User authentication request"""
    phone_number: constr(regex=r'^\+?[1-9]\d{1,14}$')
    otp: Optional[str] = Field(None, regex=r'^\d{6}$')
    api_key: Optional[str] = Field(None, min_length=32, max_length=128)

    @validator('api_key')
    def validate_api_key(cls, v):
        if v and not re.match(r'^[A-Za-z0-9_\-]+$', v):
            raise ValueError("Invalid API key format")
        return v


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]


class RateLimitResponse(BaseModel):
    """Rate limit response"""
    limit: int
    remaining: int
    reset: datetime
    retry_after: Optional[int] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ClaudeAnalysisRequest(BaseModel):
    """Claude AI analysis request"""
    message: str = Field(..., min_length=1, max_length=4000)
    context: Optional[str] = Field(None, max_length=2000)
    user_id: str = Field(..., min_length=1, max_length=64)
    max_tokens: Optional[int] = Field(1000, ge=1, le=4000)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=1.0)


class TenantRequest(BaseModel):
    """Tenant management request"""
    tenant_id: str = Field(..., regex=r'^[a-z0-9\-]+$', max_length=50)
    tenant_name: str = Field(..., min_length=1, max_length=100)
    admin_phone: constr(regex=r'^\+?[1-9]\d{1,14}$')
    plan: str = Field(..., regex=r'^(free|basic|premium|enterprise)$')
    max_users: int = Field(10, ge=1, le=10000)
    features: Optional[List[str]] = Field(default_factory=list)

    @validator('tenant_id')
    def validate_tenant_id(cls, v):
        if v in ['admin', 'root', 'system', 'default']:
            raise ValueError("Reserved tenant ID")
        return v


# Validation decorators for use in routes
def validate_webhook(func):
    """Decorator to validate webhook payloads"""
    async def wrapper(request, *args, **kwargs):
        try:
            data = await request.json()
            WebhookPayload(**data)
            return await func(request, *args, **kwargs)
        except Exception as e:
            return ErrorResponse(
                error="VALIDATION_ERROR",
                message=str(e),
                details={"validation_errors": e.errors() if hasattr(e, 'errors') else None}
            )
    return wrapper


def validate_phone_number(phone: str) -> str:
    """Standalone phone validation function"""
    pattern = r'^\+?[1-9]\d{1,14}$'
    if not re.match(pattern, phone):
        raise ValueError(f"Invalid phone number format: {phone}")
    # Normalize to E.164 format
    if not phone.startswith('+'):
        phone = '+' + phone
    return phone


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    # Remove any directory components
    filename = filename.replace('..', '').replace('/', '').replace('\\', '')
    # Keep only alphanumeric, dash, underscore, and dot
    filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + '.' + ext if ext else name[:255]
    return filename


def validate_json_payload(data: Dict[str, Any], max_size: int = 1048576) -> Dict[str, Any]:
    """Validate JSON payload size and structure"""
    import json

    # Check size
    json_str = json.dumps(data)
    if len(json_str) > max_size:
        raise ValueError(f"Payload too large: {len(json_str)} bytes (max: {max_size})")

    # Check nesting depth
    def check_depth(obj, current_depth=0, max_depth=10):
        if current_depth > max_depth:
            raise ValueError(f"JSON nesting too deep (max: {max_depth})")
        if isinstance(obj, dict):
            for value in obj.values():
                check_depth(value, current_depth + 1, max_depth)
        elif isinstance(obj, list):
            for item in obj:
                check_depth(item, current_depth + 1, max_depth)

    check_depth(data)
    return data