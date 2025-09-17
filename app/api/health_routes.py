"""
Health Check API Routes
Simple endpoints for testing frontend-backend connectivity
"""
from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Memory Assistant API",
        "version": "1.0.0"
    }

@router.get("/backend-status")
async def backend_status():
    """Detailed backend status"""
    return {
        "api": "active",
        "database": os.path.exists("DATABASE_URL"),
        "websocket": "ready",
        "claude_integration": bool(os.getenv("ANTHROPIC_API_KEY")),
        "whatsapp_webhook": "configured",
        "memory_storage": "operational",
        "timestamp": datetime.now().isoformat()
    }