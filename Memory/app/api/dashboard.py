"""
Dashboard API endpoints and static file serving
Provides monitoring dashboard interface
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import os

router = APIRouter()

# Get dashboard HTML path
DASHBOARD_PATH = Path(__file__).parent.parent / "static" / "dashboard.html"


@router.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the monitoring dashboard"""
    if not DASHBOARD_PATH.exists():
        return HTMLResponse(
            content="<h1>Dashboard not found</h1><p>Please ensure dashboard.html is in the static directory.</p>",
            status_code=404
        )

    with open(DASHBOARD_PATH, 'r') as f:
        content = f.read()

    return HTMLResponse(content=content)


@router.get("/")
async def root():
    """Redirect root to dashboard"""
    return HTMLResponse(
        content='<meta http-equiv="refresh" content="0; url=/dashboard">',
        status_code=200
    )


# Dashboard configuration endpoint
@router.get("/dashboard/config")
async def get_dashboard_config():
    """Get dashboard configuration"""
    return {
        "refreshInterval": int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "5000")),
        "metricsEndpoint": "/api/v1/metrics",
        "healthEndpoint": "/api/v1/health/detailed",
        "websocketUrl": f"ws://{os.getenv('APP_HOST', 'localhost')}:{os.getenv('APP_PORT', '8000')}/ws/metrics",
        "features": {
            "websocket": os.getenv("ENABLE_WEBSOCKET", "true") == "true",
            "simulation": os.getenv("DASHBOARD_SIMULATION", "false") == "true"
        },
        "thresholds": {
            "cpu_warning": 70,
            "cpu_critical": 90,
            "memory_warning": 80,
            "memory_critical": 95,
            "disk_warning": 80,
            "disk_critical": 90,
            "response_time_warning": 500,
            "response_time_critical": 1000
        }
    }