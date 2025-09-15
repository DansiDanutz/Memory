"""
API v1 Router Configuration
Centralizes all v1 API endpoints with versioning
"""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.v1.memory import router as memory_router
from app.api.v1.webhook import router as webhook_router
from app.api.v1.voice import router as voice_router
from app.api.v1.claude import router as claude_router
from app.api.v1.auth import router as auth_router

# Create main v1 router
v1_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
v1_router.include_router(health_router, tags=["health"])
v1_router.include_router(memory_router, prefix="/memory", tags=["memory"])
v1_router.include_router(webhook_router, prefix="/webhook", tags=["webhook"])
v1_router.include_router(voice_router, prefix="/voice", tags=["voice"])
v1_router.include_router(claude_router, prefix="/claude", tags=["ai"])
v1_router.include_router(auth_router, prefix="/auth", tags=["authentication"])

# API version information
API_VERSION = "1.0.0"
API_DESCRIPTION = """
Memory App API v1

## Features
- WhatsApp webhook integration
- Voice transcription and synthesis
- Memory storage and search
- Claude AI integration
- Multi-tenant support

## Authentication
Use API key in header: `X-API-Key: your-api-key`

## Rate Limiting
Default: 100 requests/minute
Voice: 10 requests/minute
Claude: 20 requests/minute
"""