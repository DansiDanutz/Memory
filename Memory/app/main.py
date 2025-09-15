import os, psutil
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response, RedirectResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.webhook import router as webhook_router
from app.claude_router import router as claude_router

app = FastAPI(title="MemoApp WhatsApp Bot", version="1.0.0")
app.include_router(webhook_router)
app.include_router(claude_router)

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
def root(): return {'status':'ok'}

@app.get('/metrics')
def metrics(): return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get('/health')
def health():
    """Health check endpoint for container orchestration"""
    return {'status': 'healthy', 'service': 'whatsapp-memory-bot', 'timestamp': datetime.utcnow().isoformat()}

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
