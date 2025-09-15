"""
Rate limiting middleware for Memory App
Implements token bucket algorithm with Redis backend
"""

import time
import json
import hashlib
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis
from redis import Redis
import asyncio
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter with Redis backend"""

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        default_limit: int = 100,
        default_window: int = 60,
        prefix: str = "rate_limit:"
    ):
        self.redis = redis_client or self._create_redis_client()
        self.default_limit = default_limit
        self.default_window = default_window  # in seconds
        self.prefix = prefix

    def _create_redis_client(self) -> Redis:
        """Create Redis client with fallback to in-memory if Redis unavailable"""
        try:
            client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=1
            )
            client.ping()
            logger.info("Connected to Redis for rate limiting")
            return client
        except:
            logger.warning("Redis not available, using in-memory rate limiting")
            return InMemoryRateLimiter()

    def get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        # Priority: API Key > User ID > IP Address

        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

        # Check for authenticated user
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Check for phone number in WhatsApp requests
        if request.url.path == "/webhook" and request.method == "POST":
            try:
                body = asyncio.run(request.body())
                data = json.loads(body)
                phone = self._extract_phone_from_webhook(data)
                if phone:
                    return f"phone:{phone}"
            except:
                pass

        # Fallback to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    def _extract_phone_from_webhook(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract phone number from WhatsApp webhook"""
        try:
            entries = data.get("entry", [])
            if entries:
                changes = entries[0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    messages = value.get("messages", [])
                    if messages:
                        return messages[0].get("from")
        except:
            pass
        return None

    def get_limits_for_endpoint(self, path: str, method: str) -> Tuple[int, int]:
        """Get rate limits for specific endpoint"""
        endpoint_limits = {
            # Critical endpoints with lower limits
            ("/webhook", "POST"): (30, 60),  # 30 requests per minute
            ("/process-audio", "POST"): (10, 60),  # 10 requests per minute
            ("/api/v1/claude/analyze", "POST"): (20, 60),  # 20 requests per minute

            # Search endpoints
            ("/api/v1/memory/search", "GET"): (50, 60),  # 50 searches per minute

            # Health checks have higher limits
            ("/health", "GET"): (1000, 60),  # Essentially unlimited
            ("/metrics", "GET"): (100, 60),

            # Default for other endpoints
            ("default", "default"): (self.default_limit, self.default_window)
        }

        key = (path, method)
        if key in endpoint_limits:
            return endpoint_limits[key]

        # Check for path patterns
        if path.startswith("/api/v1/"):
            return (60, 60)  # Standard API endpoints

        return endpoint_limits[("default", "default")]

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request should be rate limited"""
        key = f"{self.prefix}{identifier}"
        now = time.time()

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, now - window)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry
            pipe.expire(key, window + 1)

            results = pipe.execute()
            request_count = results[1]

            # Calculate rate limit headers
            remaining = max(0, limit - request_count - 1)
            reset_time = now + window

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_time)),
                "X-RateLimit-Reset-After": str(window)
            }

            if request_count >= limit:
                # Calculate retry after
                oldest = self.redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - now)
                    headers["Retry-After"] = str(retry_after)
                return False, headers

            return True, headers

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # On error, allow request but log it
            return True, {}

    def reset_limit(self, identifier: str):
        """Reset rate limit for identifier (admin function)"""
        key = f"{self.prefix}{identifier}"
        self.redis.delete(key)


class InMemoryRateLimiter:
    """Fallback in-memory rate limiter when Redis is not available"""

    def __init__(self):
        self.buckets = {}
        self.cleanup_interval = 60  # Clean old entries every minute
        self.last_cleanup = time.time()

    def pipeline(self):
        """Mock pipeline for compatibility"""
        return self

    def zremrangebyscore(self, key, min_score, max_score):
        """Remove old entries"""
        if key in self.buckets:
            self.buckets[key] = [
                t for t in self.buckets[key]
                if t > max_score
            ]

    def zcard(self, key):
        """Count entries"""
        return len(self.buckets.get(key, []))

    def zadd(self, key, mapping):
        """Add entry"""
        if key not in self.buckets:
            self.buckets[key] = []
        for timestamp in mapping.values():
            self.buckets[key].append(timestamp)

    def expire(self, key, seconds):
        """Mock expire for compatibility"""
        pass

    def execute(self):
        """Execute pipeline operations"""
        # Cleanup old buckets periodically
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()
            self.last_cleanup = now
        return [None, len(self.buckets.get("current_key", [])), None, None]

    def zrange(self, key, start, stop, withscores=False):
        """Get range of entries"""
        if key not in self.buckets:
            return []
        entries = sorted(self.buckets[key])
        if withscores:
            return [(str(t), t) for t in entries[start:stop+1]]
        return entries[start:stop+1]

    def delete(self, key):
        """Delete key"""
        if key in self.buckets:
            del self.buckets[key]

    def _cleanup(self):
        """Clean up old entries"""
        now = time.time()
        for key in list(self.buckets.keys()):
            self.buckets[key] = [
                t for t in self.buckets[key]
                if now - t < 300  # Keep last 5 minutes
            ]
            if not self.buckets[key]:
                del self.buckets[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""

    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static files and docs
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]:
            return await call_next(request)

        # Get identifier and limits
        identifier = self.rate_limiter.get_identifier(request)
        limit, window = self.rate_limiter.get_limits_for_endpoint(
            request.url.path,
            request.method
        )

        # Check rate limit
        allowed, headers = await self.rate_limiter.check_rate_limit(
            identifier, limit, window
        )

        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier} on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please retry after some time.",
                    "retry_after": headers.get("Retry-After", window)
                },
                headers=headers
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response


def rate_limit(requests: int = 10, window: int = 60):
    """Decorator for rate limiting specific endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            rate_limiter = RateLimiter()
            identifier = rate_limiter.get_identifier(request)

            allowed, headers = await rate_limiter.check_rate_limit(
                identifier, requests, window
            )

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers=headers
                )

            # Add headers to request state for later use
            request.state.rate_limit_headers = headers

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Advanced rate limiting strategies

class SlidingWindowRateLimiter(RateLimiter):
    """Sliding window rate limiter for more accurate rate limiting"""

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window algorithm"""
        key = f"{self.prefix}{identifier}"
        now = time.time()
        window_start = now - window

        # Use Lua script for atomic operation
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local window_start = now - window

        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- Count current entries
        local current = redis.call('ZCARD', key)

        if current < limit then
            -- Add new entry
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, window + 1)
            return {1, limit - current - 1}
        else
            -- Get oldest entry for retry calculation
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local retry_after = 0
            if oldest[2] then
                retry_after = oldest[2] + window - now
            end
            return {0, retry_after}
        end
        """

        try:
            result = self.redis.eval(lua_script, 1, key, now, window, limit)
            allowed = result[0] == 1

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Window": str(window)
            }

            if allowed:
                headers["X-RateLimit-Remaining"] = str(result[1])
            else:
                headers["Retry-After"] = str(int(result[1]))

            return allowed, headers

        except Exception as e:
            logger.error(f"Sliding window rate limit failed: {e}")
            return True, {}


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts based on system load"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_threshold = 0.8
        self.adjustment_factor = 0.5

    async def get_system_load(self) -> float:
        """Get current system load (0.0 to 1.0)"""
        try:
            # This could check CPU, memory, response times, etc.
            import psutil
            return psutil.cpu_percent() / 100.0
        except:
            return 0.5  # Default to medium load

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Adaptive rate limiting based on system load"""

        # Get current system load
        load = await self.get_system_load()

        # Adjust limit based on load
        if load > self.load_threshold:
            adjusted_limit = int(limit * self.adjustment_factor)
            logger.info(f"High load ({load:.2f}), reducing limit from {limit} to {adjusted_limit}")
        else:
            adjusted_limit = limit

        # Use parent's rate limiting with adjusted limit
        return await super().check_rate_limit(identifier, adjusted_limit, window)