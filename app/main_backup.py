#!/usr/bin/env python3
"""
Main FastAPI Application for WhatsApp Memory Bot
Production-ready with Phase 1 features only
"""

import os
import logging
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import PlainTextResponse
from typing import Dict, Any
from datetime import datetime, timedelta
import psutil
import json

from whatsapp import WhatsAppHandler
from memory.storage import MemoryStorage
from security.session_store import SessionStore
from logging_config import setup_json_logging, get_logger

# Setup JSON logging
setup_json_logging(level=logging.INFO)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MemoApp Memory Bot",
    description="Phase 1 WhatsApp memory application with voice authentication - Your Personal Memory Guardian",
    version="1.0.0"
)

# Initialize components
session_store = SessionStore()
memory_storage = MemoryStorage(base_dir="memory-system")
whatsapp_handler = WhatsAppHandler(memory_storage, session_store)

# Get webhook verification token from environment
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "memory-app-verify-2024")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "webhook-secret-key")

# Track request metrics
request_metrics = {
    "total_requests": 0,
    "webhook_requests": 0,
    "errors": 0
}

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "MemoApp Memory Bot",
        "version": "1.0.0",
        "phase": "1"
    }

@app.get("/webhook")
async def verify_webhook(request: Request):
    """WhatsApp webhook verification endpoint"""
    params = request.query_params
    
    # WhatsApp webhook verification
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode and token:
        if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
            logger.info("Webhook verified successfully", extra={"action": "webhook_verify", "status": "success"})
            return PlainTextResponse(content=challenge)
        else:
            logger.warning("Invalid verification token", extra={"action": "webhook_verify", "status": "failed"})
            raise HTTPException(status_code=403, detail="Verification failed")
    
    return {"status": "ready"}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming WhatsApp webhook messages"""
    try:
        # Get request body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        # Verify webhook signature if configured
        signature = request.headers.get("X-Hub-Signature-256")
        if signature and WEBHOOK_SECRET != "webhook-secret-key":
            expected_signature = hmac.new(
                WEBHOOK_SECRET.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature.replace("sha256=", ""), expected_signature):
                logger.warning("❌ Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        webhook_data = await request.json()
        
        # Process WhatsApp message
        response = await whatsapp_handler.process_webhook(webhook_data)
        
        return {"status": "success", "data": response}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", extra={"action": "webhook_process", "error": str(e)})
        # Return 200 to prevent WhatsApp from retrying
        return {"status": "error", "message": str(e)}

@app.post("/api/search")
async def search_memories(request: Request):
    """Search memories endpoint"""
    try:
        data = await request.json()
        phone = data.get("phone")
        query = data.get("query")
        category = data.get("category")
        
        # Verify session
        session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not session_store.validate_session(phone, session_token):
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Search memories
        from memory.search import MemorySearch
        searcher = MemorySearch(memory_storage)
        results = await searcher.search(
            user_phone=phone,
            query=query,
            category=category
        )
        
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Search error: {e}", extra={"action": "memory_search", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/authenticate")
async def voice_authenticate(request: Request):
    """Voice authentication endpoint"""
    try:
        data = await request.json()
        phone = data.get("phone")
        audio_data = data.get("audio_data")  # Base64 encoded
        
        # Process voice authentication
        from voice.guard import VoiceGuard
        voice_guard = VoiceGuard()
        
        result = await voice_guard.authenticate(phone, audio_data)
        
        if result["authenticated"]:
            # Create session
            session_token = session_store.create_session(phone)
            result["session_token"] = session_token
        
        return result
        
    except Exception as e:
        logger.error(f"Voice authentication error: {e}", extra={"action": "voice_auth", "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/session/{phone}")
async def logout(phone: str, request: Request):
    """Logout endpoint"""
    session_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    session_store.invalidate_session(phone, session_token)
    return {"status": "logged out"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # Collect metrics
    stats = {
        "total_memories": 0,
        "active_sessions": 0,
        "categories": {},
        "request_count": request_metrics.get("total_requests", 0),
        "error_count": request_metrics.get("errors", 0)
    }
    
    # Get aggregated stats from memory storage
    try:
        user_dirs = memory_storage.users_dir.glob("*")
        for user_dir in user_dirs:
            if user_dir.is_dir():
                index_file = user_dir / "index.json"
                if index_file.exists():
                    with open(index_file, 'r') as f:
                        index = json.load(f)
                        stats["total_memories"] += index.get("stats", {}).get("total", 0)
                        for cat, count in index.get("stats", {}).get("by_category", {}).items():
                            stats["categories"][cat] = stats["categories"].get(cat, 0) + count
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}", extra={"action": "metrics_collection", "error": str(e)})
    
    # Format as Prometheus metrics
    metrics_text = f"""# HELP memoapp_memories_total Total number of stored memories
# TYPE memoapp_memories_total counter
memoapp_memories_total {stats['total_memories']}

# HELP memoapp_active_sessions Number of active authentication sessions
# TYPE memoapp_active_sessions gauge
memoapp_active_sessions {len(session_store.sessions)}

# HELP memoapp_memories_by_category Memories count by category
# TYPE memoapp_memories_by_category counter
"""
    
    for category, count in stats["categories"].items():
        metrics_text += f'memoapp_memories_by_category{{category="{category}"}} {count}\n'
    
    # Add system metrics
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage('/').percent
    
    metrics_text += f"""\n# HELP memoapp_cpu_usage_percent CPU usage percentage
# TYPE memoapp_cpu_usage_percent gauge
memoapp_cpu_usage_percent {cpu_percent}

# HELP memoapp_memory_usage_percent Memory usage percentage
# TYPE memoapp_memory_usage_percent gauge
memoapp_memory_usage_percent {memory_percent}

# HELP memoapp_disk_usage_percent Disk usage percentage
# TYPE memoapp_disk_usage_percent gauge
memoapp_disk_usage_percent {disk_percent}

# HELP memoapp_requests_total Total number of HTTP requests
# TYPE memoapp_requests_total counter
memoapp_requests_total {stats['request_count']}

# HELP memoapp_errors_total Total number of errors
# TYPE memoapp_errors_total counter
memoapp_errors_total {stats['error_count']}
"""
    
    return PlainTextResponse(content=metrics_text, media_type="text/plain")

@app.get("/admin/status")
async def admin_status(request: Request):
    """Admin status endpoint showing system statistics"""
    # Simple auth check - in production, implement proper admin auth
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = os.getenv("ADMIN_TOKEN", "admin-secret-2024")
    
    if admin_token != expected_token:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Collect system stats
    stats = {
        "service": "MemoApp Memory Bot",
        "version": "1.0.0",
        "phase": "1",
        "uptime": str(datetime.now() - app.state.startup_time if hasattr(app.state, 'startup_time') else datetime.now()),
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_memory_mb": psutil.Process().memory_info().rss / 1024 / 1024
        },
        "storage": {
            "total_memories": 0,
            "total_users": 0,
            "categories": {},
            "storage_path": str(memory_storage.base_dir)
        },
        "sessions": {
            "active": len(session_store.sessions),
            "total_created": getattr(session_store, 'total_created', 0)
        },
        "voice_auth": {
            "enrolled_users": 0
        },
        "requests": request_metrics
    }
    
    # Count memories and users
    try:
        user_dirs = list(memory_storage.users_dir.glob("*"))
        stats["storage"]["total_users"] = len(user_dirs)
        
        for user_dir in user_dirs:
            if user_dir.is_dir():
                index_file = user_dir / "index.json"
                if index_file.exists():
                    with open(index_file, 'r') as f:
                        index = json.load(f)
                        stats["storage"]["total_memories"] += index.get("stats", {}).get("total", 0)
                        for cat, count in index.get("stats", {}).get("by_category", {}).items():
                            stats["storage"]["categories"][cat] = stats["storage"]["categories"].get(cat, 0) + count
        
        # Count enrolled voice users
        from pathlib import Path
        voice_auth_file = Path("memory-system/voice_auth/passphrases.json")
        if voice_auth_file.exists():
            with open(voice_auth_file, 'r') as f:
                voice_data = json.load(f)
                stats["voice_auth"]["enrolled_users"] = len(voice_data.get("passphrases", {}))
    
    except Exception as e:
        logger.error(f"Error collecting admin stats: {e}", extra={"action": "admin_stats", "error": str(e)})
        stats["error"] = str(e)
    
    return stats

@app.on_event("startup")
async def startup_event():
    """Initialize app state on startup"""
    app.state.startup_time = datetime.now()
    logger.info(f"MemoApp Memory Bot started", extra={"action": "startup", "startup_time": app.state.startup_time.isoformat()})

@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Middleware to track request metrics"""
    request_metrics["total_requests"] += 1
    
    if request.url.path == "/webhook":
        request_metrics["webhook_requests"] += 1
    
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            request_metrics["errors"] += 1
        return response
    except Exception as e:
        request_metrics["errors"] += 1
        raise

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)