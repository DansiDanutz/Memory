import os, psutil
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response, RedirectResponse, FileResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.webhook import router as webhook_router
from app.api.memory_routes import router as memory_router
from app.api.claude_routes import router as claude_router
from app.api.health_routes import router as health_router
from app.api.md_agent_routes import router as md_agent_router
from app.api.voice_collection_routes import router as voice_collection_router
from app.claude_service import ClaudeService
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path

app = FastAPI(title="MemoApp WhatsApp Bot", version="2.1.0", description="Enterprise Memory Management System with Claude AI Integration")

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhook_router)
app.include_router(memory_router)
app.include_router(claude_router)
app.include_router(health_router)
app.include_router(md_agent_router)
app.include_router(voice_collection_router)

# Import and include WebSocket routes
from app.api.websocket_routes import router as websocket_router
app.include_router(websocket_router)

# Import and include Gamification routes
try:
    from app.api.gamification_routes import router as gamification_router
    app.include_router(gamification_router)
    
    # Import and include Quest/FOMO routes
    from app.api.quest_fomo_routes import router as quest_fomo_router
    app.include_router(quest_fomo_router)
    
    # Initialize secure gamification dashboard
    from app.gamification.invitation_dashboard_secure import get_secure_invitation_dashboard
    dashboard = get_secure_invitation_dashboard(app)
    logging.info("✅ Gamification system integrated with secure dashboard")
    logging.info("✅ Quest and FOMO system initialized")
except ImportError as e:
    logging.warning(f"⚠️ Gamification routes not loaded: {e}")
except Exception as e:
    logging.warning(f"⚠️ Error loading gamification system: {e}")

# Serve static files from React build
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static")

# Admin API key authentication
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '')
security = HTTPBearer(auto_error=False)

def verify_admin_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify admin API key for protected endpoints"""
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if not credentials or credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

# Legacy webhook redirect for compatibility
@app.get('/webhook')
async def webhook_redirect_get(request: Request):
    """Redirect old webhook endpoint to new location"""
    query = str(request.url.query)
    return RedirectResponse(url=f'/webhook/whatsapp?{query}' if query else '/webhook/whatsapp')

@app.post('/webhook')
async def webhook_redirect_post(request: Request):
    """Redirect old webhook POST to new location with body forwarding"""
    # Use 307 to preserve POST method and body
    return RedirectResponse(url='/webhook/whatsapp', status_code=307)

@app.get('/')
async def root():
    """Serve the React app at the root URL"""
    frontend_dist = Path("frontend/dist")
    index_file = frontend_dist / "index.html"
    
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        return {"error": "Frontend not built. Run 'cd frontend && npm run build'", "status": "backend_ok"}

@app.get('/metrics')
def metrics(): return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get('/health')
def health():
    """Health check endpoint for container orchestration"""
    claude = ClaudeService()
    return {
        'status': 'healthy', 
        'service': 'whatsapp-memory-bot', 
        'timestamp': datetime.utcnow().isoformat(),
        'claude_available': claude.is_available(),
        'claude_model': claude.model if claude.is_available() else None
    }

@app.get('/api/health')
def api_health():
    """API health check endpoint"""
    return health()

@app.get('/api/claude/status')
async def claude_status():
    """Get Claude AI service status"""
    claude = ClaudeService()
    if claude.is_available():
        success, message = await claude.test_connection()
        return {
            'available': True,
            'model': claude.model,
            'connection_test': success,
            'message': message if not success else 'Connected successfully'
        }
    else:
        return {
            'available': False,
            'model': None,
            'connection_test': False,
            'message': 'ANTHROPIC_API_KEY not configured'
        }

@app.get('/admin/status')
def status(_: None = Depends(verify_admin_key)):
    return {
        'cpu_percent': psutil.cpu_percent(),
        'mem': psutil.virtual_memory()._asdict(),
        'pid': os.getpid()
    }

# PR-2 Admin endpoints for tenant management
from app.tenancy.model import reload_tenancy, TENANCY
from app.tenancy.rbac import whoami

@app.post("/admin/tenants/reload")
def tenants_reload(_: None = Depends(verify_admin_key)):
    reload_tenancy()
    return {"reloaded": True}

@app.get("/admin/tenants")
def tenants_info(_: None = Depends(verify_admin_key)):
    return {"tenants": list(TENANCY.tenants.keys())}

@app.get("/admin/whoami")
def whoami_endpoint(phone: str, _: None = Depends(verify_admin_key)):
    return {"whoami": whoami(phone)}

# Startup event to verify Claude connection
@app.on_event("startup")
async def startup_event():
    """Verify Claude AI connection on startup"""
    logger = logging.getLogger(__name__)
    claude = ClaudeService()
    
    if claude.is_available():
        # Test connection
        success, message = await claude.test_connection()
        if success:
            logger.info(f"✅ Claude AI initialized successfully with model: {claude.model}")
        else:
            logger.warning(f"⚠️ Claude AI configured but connection test failed: {message}")
    else:
        logger.warning("⚠️ Claude AI not configured. Set ANTHROPIC_API_KEY to enable Claude features.")
    
    logger.info("🚀 MemoApp WhatsApp Bot started successfully")

# Catch-all route for React app - MUST be last!
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve React app for all non-API routes"""
    # Skip API routes
    if full_path.startswith(("api/", "webhook/", "ws/", "claude/", "metrics", "health", "admin/")):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Serve the React app
    frontend_dist = Path("frontend/dist")
    index_file = frontend_dist / "index.html"
    
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        return {"error": "Frontend not built. Run 'cd frontend && npm run build'"}
