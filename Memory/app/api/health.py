"""
Health check and monitoring endpoints
Provides system status and dependency checks
"""

import os
import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
import redis
import aiohttp
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthChecker:
    """Comprehensive health checking service"""

    def __init__(self):
        self.checks = []
        self.last_check_time = None
        self.cache_duration = 10  # Cache health status for 10 seconds

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        try:
            client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                socket_connect_timeout=1
            )
            start = time.time()
            client.ping()
            latency = (time.time() - start) * 1000
            return {
                "service": "redis",
                "status": "healthy",
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "service": "redis",
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_azure_speech(self) -> Dict[str, Any]:
        """Check Azure Speech Services"""
        try:
            key = os.getenv("AZURE_SPEECH_KEY")
            region = os.getenv("AZURE_SPEECH_REGION", "eastus")

            if not key:
                return {
                    "service": "azure_speech",
                    "status": "not_configured"
                }

            url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
            headers = {"Ocp-Apim-Subscription-Key": key}

            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.post(url, headers=headers) as response:
                    latency = (time.time() - start) * 1000
                    if response.status == 200:
                        return {
                            "service": "azure_speech",
                            "status": "healthy",
                            "latency_ms": round(latency, 2)
                        }
                    else:
                        return {
                            "service": "azure_speech",
                            "status": "degraded",
                            "http_status": response.status
                        }
        except Exception as e:
            logger.error(f"Azure Speech health check failed: {e}")
            return {
                "service": "azure_speech",
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_claude_api(self) -> Dict[str, Any]:
        """Check Claude API connectivity"""
        try:
            key = os.getenv("CLAUDE_API_KEY")

            if not key:
                return {
                    "service": "claude_api",
                    "status": "not_configured"
                }

            # Simple connectivity check
            import anthropic
            client = anthropic.Anthropic(api_key=key)

            # We can't actually make a request without incurring cost,
            # so we just check if the client initializes
            return {
                "service": "claude_api",
                "status": "configured",
                "model": os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")
            }
        except Exception as e:
            logger.error(f"Claude API health check failed: {e}")
            return {
                "service": "claude_api",
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_whatsapp(self) -> Dict[str, Any]:
        """Check WhatsApp API configuration"""
        try:
            token = os.getenv("WHATSAPP_API_KEY")
            phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

            if not token or not phone_id:
                return {
                    "service": "whatsapp",
                    "status": "not_configured"
                }

            # Check Meta Graph API health
            url = f"https://graph.facebook.com/v18.0/{phone_id}"
            headers = {"Authorization": f"Bearer {token}"}

            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get(url, headers=headers) as response:
                    latency = (time.time() - start) * 1000
                    if response.status == 200:
                        return {
                            "service": "whatsapp",
                            "status": "healthy",
                            "latency_ms": round(latency, 2)
                        }
                    elif response.status == 401:
                        return {
                            "service": "whatsapp",
                            "status": "auth_error",
                            "http_status": response.status
                        }
                    else:
                        return {
                            "service": "whatsapp",
                            "status": "degraded",
                            "http_status": response.status
                        }
        except Exception as e:
            logger.error(f"WhatsApp health check failed: {e}")
            return {
                "service": "whatsapp",
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space"""
        try:
            usage = psutil.disk_usage('/')
            return {
                "service": "disk",
                "status": "healthy" if usage.percent < 90 else "warning",
                "used_percent": usage.percent,
                "free_gb": round(usage.free / (1024**3), 2)
            }
        except Exception as e:
            return {
                "service": "disk",
                "status": "error",
                "error": str(e)
            }

    async def check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            return {
                "service": "memory",
                "status": "healthy" if memory.percent < 85 else "warning",
                "used_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2)
            }
        except Exception as e:
            return {
                "service": "memory",
                "status": "error",
                "error": str(e)
            }

    async def check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            return {
                "service": "cpu",
                "status": "healthy" if cpu_percent < 80 else "warning",
                "usage_percent": cpu_percent,
                "cores": psutil.cpu_count()
            }
        except Exception as e:
            return {
                "service": "cpu",
                "status": "error",
                "error": str(e)
            }

    async def check_file_system(self) -> Dict[str, Any]:
        """Check file system access"""
        try:
            memory_path = Path("./app/memory-system/users")
            if memory_path.exists():
                # Count memories
                memory_count = sum(1 for _ in memory_path.rglob("*.md"))
                return {
                    "service": "filesystem",
                    "status": "healthy",
                    "memory_count": memory_count,
                    "writable": os.access(memory_path, os.W_OK)
                }
            else:
                return {
                    "service": "filesystem",
                    "status": "not_initialized",
                    "path": str(memory_path)
                }
        except Exception as e:
            return {
                "service": "filesystem",
                "status": "error",
                "error": str(e)
            }

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        # Check cache
        if self.last_check_time:
            elapsed = (datetime.now() - self.last_check_time).seconds
            if elapsed < self.cache_duration and hasattr(self, '_cached_result'):
                return self._cached_result

        # Run checks in parallel
        checks = await asyncio.gather(
            self.check_redis(),
            self.check_azure_speech(),
            self.check_claude_api(),
            self.check_whatsapp(),
            self.check_disk_space(),
            self.check_memory(),
            self.check_cpu(),
            self.check_file_system(),
            return_exceptions=True
        )

        # Process results
        services = []
        overall_status = "healthy"
        degraded_count = 0
        unhealthy_count = 0

        for check in checks:
            if isinstance(check, Exception):
                services.append({
                    "service": "unknown",
                    "status": "error",
                    "error": str(check)
                })
                unhealthy_count += 1
            else:
                services.append(check)
                if check["status"] == "unhealthy" or check["status"] == "error":
                    unhealthy_count += 1
                elif check["status"] in ["degraded", "warning", "not_configured"]:
                    degraded_count += 1

        # Determine overall status
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"

        result = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "services": services,
            "summary": {
                "healthy": len([s for s in services if s["status"] == "healthy"]),
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "total": len(services)
            }
        }

        # Cache result
        self._cached_result = result
        self.last_check_time = datetime.now()

        return result


# Singleton health checker
_health_checker = HealthChecker()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "memory-app"
    }


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe"""
    # Quick check of critical services
    try:
        # Check Redis
        client = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        client.ping()

        return {"status": "ready"}
    except:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check of all services"""
    result = await _health_checker.run_all_checks()

    # Return appropriate HTTP status
    if result["status"] == "unhealthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result
        )
    elif result["status"] == "degraded":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )
    else:
        return result


@router.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    metrics_lines = []

    # System metrics
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    disk = psutil.disk_usage('/')

    metrics_lines.extend([
        "# HELP memory_usage_bytes Memory usage in bytes",
        "# TYPE memory_usage_bytes gauge",
        f"memory_usage_bytes {memory.used}",
        "",
        "# HELP memory_available_bytes Available memory in bytes",
        "# TYPE memory_available_bytes gauge",
        f"memory_available_bytes {memory.available}",
        "",
        "# HELP cpu_usage_percent CPU usage percentage",
        "# TYPE cpu_usage_percent gauge",
        f"cpu_usage_percent {cpu}",
        "",
        "# HELP disk_usage_percent Disk usage percentage",
        "# TYPE disk_usage_percent gauge",
        f"disk_usage_percent {disk.percent}",
        "",
        "# HELP app_info Application information",
        "# TYPE app_info gauge",
        f'app_info{{version="{os.getenv("APP_VERSION", "1.0.0")}",environment="{os.getenv("ENVIRONMENT", "development")}"}} 1',
    ])

    return "\n".join(metrics_lines)


@router.get("/status")
async def status():
    """Application status and statistics"""
    uptime = time.time() - _startup_time if '_startup_time' in globals() else 0

    return {
        "application": "Memory App",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "uptime_seconds": round(uptime),
        "current_time": datetime.utcnow().isoformat(),
        "features": {
            "voice_processing": os.getenv("ENABLE_VOICE_PROCESSING", "true") == "true",
            "memory_search": os.getenv("ENABLE_MEMORY_SEARCH", "true") == "true",
            "ai_analysis": os.getenv("ENABLE_AI_ANALYSIS", "true") == "true",
            "multi_tenant": os.getenv("ENABLE_MULTI_TENANT", "true") == "true"
        },
        "limits": {
            "rate_limit_default": os.getenv("RATE_LIMIT_DEFAULT", "100/minute"),
            "max_beta_users": int(os.getenv("MAX_BETA_USERS", "10"))
        }
    }


# Store startup time
_startup_time = time.time()