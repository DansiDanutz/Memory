"""
Utilities for Claude AI integration
Includes caching, rate limiting, and helper functions
"""
import os
import json
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Simple in-memory rate limiter
    In production, use Redis for distributed rate limiting
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, user_id: str) -> bool:
        """
        Check if user is allowed to make request
        
        Args:
            user_id: User identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        async with self.lock:
            now = time.time()
            # Clean old requests
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if now - req_time < self.window_seconds
            ]
            
            # Check if under limit
            if len(self.requests[user_id]) < self.max_requests:
                self.requests[user_id].append(now)
                return True
            return False
    
    async def reset(self, user_id: str):
        """Reset rate limit for user"""
        async with self.lock:
            self.requests[user_id] = []
    
    async def get_remaining(self, user_id: str) -> int:
        """Get remaining requests for user"""
        async with self.lock:
            now = time.time()
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if now - req_time < self.window_seconds
            ]
            return self.max_requests - len(self.requests[user_id])

class CacheManager:
    """
    Simple in-memory cache manager
    In production, use Redis for distributed caching
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache manager
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self.cache = {}
        self.ttl_map = {}
        self.default_ttl = default_ttl
        self.lock = asyncio.Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self.lock:
            # Check if key exists and not expired
            if key in self.cache:
                if key in self.ttl_map:
                    if time.time() > self.ttl_map[key]:
                        # Expired, remove it
                        del self.cache[key]
                        del self.ttl_map[key]
                        self.stats["evictions"] += 1
                        self.stats["misses"] += 1
                        return None
                
                self.stats["hits"] += 1
                return self.cache[key]
            
            self.stats["misses"] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        async with self.lock:
            ttl = ttl or self.default_ttl
            self.cache[key] = value
            self.ttl_map[key] = time.time() + ttl
            self.stats["sets"] += 1
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.ttl_map:
                    del self.ttl_map[key]
                return True
            return False
    
    async def clear_all(self):
        """Clear all cache entries"""
        async with self.lock:
            self.cache.clear()
            self.ttl_map.clear()
            self.stats["evictions"] += len(self.cache)
    
    async def clear_pattern(self, pattern: str):
        """
        Clear cache entries matching pattern
        
        Args:
            pattern: Pattern to match (supports * wildcard)
        """
        async with self.lock:
            import fnmatch
            keys_to_delete = [
                key for key in self.cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            for key in keys_to_delete:
                del self.cache[key]
                if key in self.ttl_map:
                    del self.ttl_map[key]
                self.stats["evictions"] += 1
    
    async def cleanup_expired(self):
        """Remove expired entries from cache"""
        async with self.lock:
            now = time.time()
            expired_keys = [
                key for key, expiry in self.ttl_map.items()
                if now > expiry
            ]
            for key in expired_keys:
                del self.cache[key]
                del self.ttl_map[key]
                self.stats["evictions"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            **self.stats,
            "size": len(self.cache),
            "hit_rate": self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
            if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
        }

# Global instances
_rate_limiter = None
_cache_manager = None

def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        # Get configuration from environment
        max_requests = int(os.getenv('CLAUDE_RATE_LIMIT_REQUESTS', '10'))
        window_seconds = int(os.getenv('CLAUDE_RATE_LIMIT_WINDOW', '60'))
        _rate_limiter = RateLimiter(max_requests, window_seconds)
    return _rate_limiter

def get_cache_manager() -> CacheManager:
    """Get or create cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        # Get configuration from environment
        default_ttl = int(os.getenv('CLAUDE_CACHE_TTL', '3600'))
        _cache_manager = CacheManager(default_ttl)
        
        # Start background cleanup task
        asyncio.create_task(_cache_cleanup_task())
    return _cache_manager

async def _cache_cleanup_task():
    """Background task to cleanup expired cache entries"""
    cache_manager = get_cache_manager()
    while True:
        try:
            await asyncio.sleep(300)  # Cleanup every 5 minutes
            await cache_manager.cleanup_expired()
            logger.debug(f"Cache cleanup completed. Stats: {cache_manager.get_stats()}")
        except Exception as e:
            logger.error(f"Error in cache cleanup task: {e}")

def generate_cache_key(*args) -> str:
    """
    Generate a cache key from arguments
    
    Args:
        *args: Arguments to include in key
        
    Returns:
        MD5 hash of combined arguments
    """
    key_data = ":".join(str(arg) for arg in args)
    return hashlib.md5(key_data.encode()).hexdigest()

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extract keywords from text (simplified version)
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords
        
    Returns:
        List of keywords
    """
    # Simple keyword extraction based on word frequency
    # In production, use NLP libraries for better extraction
    import re
    from collections import Counter
    
    # Remove common words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might',
        'can', 'must', 'shall', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'what', 'which', 'who', 'when', 'where', 'why', 'how', 'this', 'that',
        'these', 'those', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
    }
    
    # Extract words
    words = re.findall(r'\b[a-z]+\b', text.lower())
    
    # Filter stop words and count
    word_counts = Counter(
        word for word in words
        if word not in stop_words and len(word) > 2
    )
    
    # Return top keywords
    return [word for word, _ in word_counts.most_common(max_keywords)]

def estimate_tokens(text: str) -> int:
    """
    Estimate number of tokens in text
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    # Rough estimation: 1 token ≈ 4 characters
    # This is a simplified estimation
    return len(text) // 4

def format_conversation_context(
    messages: List[Dict[str, Any]],
    max_messages: int = 10
) -> str:
    """
    Format conversation messages for context
    
    Args:
        messages: List of messages
        max_messages: Maximum messages to include
        
    Returns:
        Formatted context string
    """
    # Take last N messages
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    # Format each message
    formatted = []
    for msg in recent_messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)

class ConversationBuffer:
    """
    Manage conversation context buffer
    """
    
    def __init__(self, max_size: int = 20):
        """
        Initialize conversation buffer
        
        Args:
            max_size: Maximum messages to keep
        """
        self.max_size = max_size
        self.conversations = defaultdict(list)
    
    def add_message(self, user_id: str, role: str, content: str):
        """Add message to conversation"""
        self.conversations[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Trim to max size
        if len(self.conversations[user_id]) > self.max_size:
            self.conversations[user_id] = self.conversations[user_id][-self.max_size:]
    
    def get_context(self, user_id: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get conversation context for user"""
        messages = self.conversations.get(user_id, [])
        return messages[-max_messages:] if len(messages) > max_messages else messages
    
    def clear(self, user_id: str):
        """Clear conversation for user"""
        if user_id in self.conversations:
            del self.conversations[user_id]

# Global conversation buffer
_conversation_buffer = None

def get_conversation_buffer() -> ConversationBuffer:
    """Get or create conversation buffer instance"""
    global _conversation_buffer
    if _conversation_buffer is None:
        _conversation_buffer = ConversationBuffer()
    return _conversation_buffer