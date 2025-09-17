#!/usr/bin/env python3
"""
Performance Optimization Module for Memory App Platform
Implements caching, connection pooling, compression, and optimization strategies
"""

import os
import json
import gzip
import time
import hashlib
import pickle
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import redis
from redis.connection import ConnectionPool
import psycopg2
from psycopg2 import pool
from flask import Flask, request, Response, g
import threading
from collections import OrderedDict
import zlib
import brotli

logger = logging.getLogger(__name__)

# ============================================
# Cache Backends
# ============================================

class CacheBackend:
    """Abstract cache backend"""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        raise NotImplementedError
    
    def delete(self, key: str):
        raise NotImplementedError
    
    def clear(self):
        raise NotImplementedError
    
    def exists(self, key: str) -> bool:
        raise NotImplementedError

class RedisCache(CacheBackend):
    """Redis-based cache backend"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.pool = ConnectionPool.from_url(self.redis_url, max_connections=50)
        self.client = redis.Redis(connection_pool=self.pool)
        self.default_ttl = int(os.getenv('CACHE_DEFAULT_TTL', '3600'))
    
    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.client.get(self._make_key(key))
            if value:
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        try:
            serialized = pickle.dumps(value)
            self.client.setex(
                self._make_key(key),
                ttl or self.default_ttl,
                serialized
            )
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str):
        try:
            self.client.delete(self._make_key(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    def clear(self):
        try:
            # Clear all keys with our prefix
            keys = self.client.keys(f"{self._prefix()}:*")
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    def exists(self, key: str) -> bool:
        try:
            return bool(self.client.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    def _make_key(self, key: str) -> str:
        return f"{self._prefix()}:{key}"
    
    def _prefix(self) -> str:
        return os.getenv('CACHE_KEY_PREFIX', 'memory_app')

class MemoryCache(CacheBackend):
    """In-memory LRU cache backend"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.RLock()
        self.expiry: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            # Check expiry
            if key in self.expiry:
                if time.time() > self.expiry[key]:
                    del self.cache[key]
                    del self.expiry[key]
                    return None
            
            # Get and move to end (LRU)
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self.lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                if oldest in self.expiry:
                    del self.expiry[oldest]
            
            # Set value
            self.cache[key] = value
            if ttl:
                self.expiry[key] = time.time() + ttl
            elif key in self.expiry:
                del self.expiry[key]
            
            # Move to end
            self.cache.move_to_end(key)
    
    def delete(self, key: str):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            if key in self.expiry:
                del self.expiry[key]
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.expiry.clear()
    
    def exists(self, key: str) -> bool:
        with self.lock:
            return key in self.cache

# ============================================
# Cache Manager
# ============================================

class CacheManager:
    """Unified cache manager with multiple backends"""
    
    def __init__(self):
        self.backends: List[CacheBackend] = []
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        # Initialize backends
        self._init_backends()
    
    def _init_backends(self):
        """Initialize cache backends based on configuration"""
        # Try Redis first
        if os.getenv('REDIS_URL'):
            try:
                redis_cache = RedisCache()
                redis_cache.client.ping()  # Test connection
                self.backends.append(redis_cache)
                logger.info("✅ Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis cache unavailable: {e}")
        
        # Always add memory cache as fallback
        memory_cache = MemoryCache(max_size=int(os.getenv('CACHE_MAX_KEYS', '1000')))
        self.backends.append(memory_cache)
        logger.info("✅ Memory cache initialized")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (checks all backends)"""
        for backend in self.backends:
            value = backend.get(key)
            if value is not None:
                self.stats['hits'] += 1
                # Populate to higher-priority backends
                for b in self.backends:
                    if b == backend:
                        break
                    b.set(key, value)
                return value
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in all backends"""
        self.stats['sets'] += 1
        for backend in self.backends:
            backend.set(key, value, ttl)
    
    def delete(self, key: str):
        """Delete from all backends"""
        self.stats['deletes'] += 1
        for backend in self.backends:
            backend.delete(key)
    
    def clear(self):
        """Clear all caches"""
        for backend in self.backends:
            backend.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': f"{hit_rate:.2f}%",
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'backends': len(self.backends)
        }

# Global cache manager instance
cache_manager = CacheManager()

# ============================================
# Database Connection Pooling
# ============================================

class DatabasePool:
    """PostgreSQL connection pool manager"""
    
    def __init__(self):
        self.pool = None
        self.config = {
            'minconn': int(os.getenv('DATABASE_POOL_MIN', '2')),
            'maxconn': int(os.getenv('DATABASE_POOL_MAX', '10')),
            'dsn': os.getenv('DATABASE_URL', '')
        }
        self._init_pool()
    
    def _init_pool(self):
        """Initialize connection pool"""
        if self.config['dsn']:
            try:
                self.pool = psycopg2.pool.ThreadedConnectionPool(
                    self.config['minconn'],
                    self.config['maxconn'],
                    self.config['dsn']
                )
                logger.info(f"✅ Database pool initialized (min={self.config['minconn']}, max={self.config['maxconn']})")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
    
    def get_connection(self):
        """Get connection from pool"""
        if self.pool:
            return self.pool.getconn()
        else:
            # Fallback to direct connection
            return psycopg2.connect(self.config['dsn'])
    
    def put_connection(self, conn):
        """Return connection to pool"""
        if self.pool:
            self.pool.putconn(conn)
        else:
            conn.close()
    
    def close_all(self):
        """Close all connections"""
        if self.pool:
            self.pool.closeall()

# Global database pool
db_pool = DatabasePool()

# ============================================
# Response Compression
# ============================================

class CompressionMiddleware:
    """Response compression middleware"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.min_size = 500  # Minimum size to compress (bytes)
        self.compression_level = 6  # 1-9 (speed vs compression)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize compression middleware"""
        self.app = app
        app.after_request(self.compress_response)
    
    def compress_response(self, response: Response) -> Response:
        """Compress response if beneficial"""
        # Check if compression is requested
        accept_encoding = request.headers.get('Accept-Encoding', '')
        
        # Skip if already compressed or too small
        if (response.direct_passthrough or
            len(response.get_data()) < self.min_size or
            'Content-Encoding' in response.headers):
            return response
        
        # Choose compression method
        if 'br' in accept_encoding:
            # Brotli compression (best compression)
            compressed = brotli.compress(
                response.get_data(),
                quality=self.compression_level
            )
            response.set_data(compressed)
            response.headers['Content-Encoding'] = 'br'
        elif 'gzip' in accept_encoding:
            # Gzip compression (most compatible)
            compressed = gzip.compress(
                response.get_data(),
                compresslevel=self.compression_level
            )
            response.set_data(compressed)
            response.headers['Content-Encoding'] = 'gzip'
        elif 'deflate' in accept_encoding:
            # Deflate compression
            compressed = zlib.compress(
                response.get_data(),
                self.compression_level
            )
            response.set_data(compressed)
            response.headers['Content-Encoding'] = 'deflate'
        
        # Update content length
        response.headers['Content-Length'] = len(response.get_data())
        
        # Add Vary header for caching
        vary = response.headers.get('Vary', '')
        if vary:
            response.headers['Vary'] = f"{vary}, Accept-Encoding"
        else:
            response.headers['Vary'] = 'Accept-Encoding'
        
        return response

# ============================================
# Caching Decorators
# ============================================

def cache(key_prefix: str = '', ttl: int = 3600):
    """Cache decorator for functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(key_prefix or func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        # Add cache control methods
        wrapper.cache_clear = lambda: cache_manager.delete(key_prefix or func.__name__)
        wrapper.cache_key = lambda *a, **kw: _generate_cache_key(key_prefix or func.__name__, a, kw)
        
        return wrapper
    return decorator

def cache_async(key_prefix: str = '', ttl: int = 3600):
    """Cache decorator for async functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(key_prefix or func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        wrapper.cache_clear = lambda: cache_manager.delete(key_prefix or func.__name__)
        wrapper.cache_key = lambda *a, **kw: _generate_cache_key(key_prefix or func.__name__, a, kw)
        
        return wrapper
    return decorator

def _generate_cache_key(prefix: str, args: tuple, kwargs: dict) -> str:
    """Generate cache key from function arguments"""
    # Create a string representation of arguments
    key_parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            # Hash complex objects
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
    
    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")
        else:
            key_parts.append(f"{k}={hashlib.md5(str(v).encode()).hexdigest()[:8]}")
    
    return ':'.join(key_parts)

# ============================================
# Query Optimization
# ============================================

class QueryOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def batch_queries(queries: List[str], batch_size: int = 100) -> List[List[str]]:
        """Batch multiple queries for efficient execution"""
        return [queries[i:i+batch_size] for i in range(0, len(queries), batch_size)]
    
    @staticmethod
    def prepare_statement(query: str, params: tuple) -> Tuple[str, tuple]:
        """Prepare and validate SQL statement"""
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Validate parameter count
        param_count = query.count('%s')
        if param_count != len(params):
            raise ValueError(f"Parameter count mismatch: expected {param_count}, got {len(params)}")
        
        return query, params
    
    @staticmethod
    @cache(key_prefix='query_plan', ttl=7200)
    def analyze_query(query: str) -> Dict[str, Any]:
        """Analyze query execution plan"""
        conn = db_pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN ANALYZE {query}")
            plan = cursor.fetchall()
            cursor.close()
            
            # Parse execution plan
            total_time = 0
            rows_processed = 0
            
            for line in plan:
                line_str = line[0] if isinstance(line, tuple) else str(line)
                if 'Total runtime:' in line_str or 'Execution Time:' in line_str:
                    # Extract time
                    import re
                    match = re.search(r'(\d+\.?\d*)', line_str)
                    if match:
                        total_time = float(match.group(1))
                if 'rows=' in line_str:
                    match = re.search(r'rows=(\d+)', line_str)
                    if match:
                        rows_processed += int(match.group(1))
            
            return {
                'query': query,
                'total_time_ms': total_time,
                'rows_processed': rows_processed,
                'plan': [line[0] if isinstance(line, tuple) else str(line) for line in plan]
            }
        finally:
            db_pool.put_connection(conn)

# ============================================
# Memory Management
# ============================================

class MemoryManager:
    """Memory management and optimization"""
    
    def __init__(self):
        self.memory_limit = int(os.getenv('MAX_MEMORY_MB', '1024')) * 1024 * 1024
        self.check_interval = 60  # seconds
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start memory monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logger.info("Started memory monitoring")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped memory monitoring")
    
    def _monitor_loop(self):
        """Memory monitoring loop"""
        import psutil
        import gc
        
        while self.monitoring:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                
                # Check memory usage
                if memory_info.rss > self.memory_limit:
                    logger.warning(f"Memory limit exceeded: {memory_info.rss / 1024 / 1024:.2f}MB")
                    
                    # Force garbage collection
                    gc.collect()
                    
                    # Clear caches if still over limit
                    memory_info = process.memory_info()
                    if memory_info.rss > self.memory_limit * 0.9:
                        logger.warning("Clearing caches due to memory pressure")
                        cache_manager.clear()
                
                # Log memory stats periodically
                if time.time() % 300 < self.check_interval:  # Every 5 minutes
                    logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f}MB")
                
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
            
            time.sleep(self.check_interval)
    
    @staticmethod
    def optimize_data_structure(data: Any) -> Any:
        """Optimize data structures for memory efficiency"""
        if isinstance(data, dict):
            # Use slots for dict-like objects if possible
            return {k: MemoryManager.optimize_data_structure(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Convert to tuple if immutable
            return [MemoryManager.optimize_data_structure(item) for item in data]
        elif isinstance(data, str) and len(data) > 1000:
            # Compress large strings
            return zlib.compress(data.encode())
        return data

# ============================================
# Performance Monitoring
# ============================================

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.slow_query_threshold = 1.0  # seconds
        self.slow_request_threshold = 2.0  # seconds
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize performance monitoring"""
        self.app = app
        
        @app.before_request
        def before_request():
            g.start_time = time.time()
        
        @app.after_request
        def after_request(response):
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                
                # Log slow requests
                if duration > self.slow_request_threshold:
                    logger.warning(
                        f"Slow request: {request.method} {request.path} "
                        f"took {duration:.2f}s"
                    )
                
                # Add timing header
                response.headers['X-Response-Time'] = f"{duration*1000:.0f}ms"
            
            return response
    
    @staticmethod
    def profile_function(func: Callable) -> Callable:
        """Profile function execution"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            import cProfile
            import pstats
            from io import StringIO
            
            profiler = cProfile.Profile()
            profiler.enable()
            
            result = func(*args, **kwargs)
            
            profiler.disable()
            
            # Get profiling results
            stream = StringIO()
            stats = pstats.Stats(profiler, stream=stream)
            stats.sort_stats('cumulative')
            stats.print_stats(10)  # Top 10 functions
            
            logger.debug(f"Profile for {func.__name__}:\n{stream.getvalue()}")
            
            return result
        
        return wrapper

# ============================================
# Lazy Loading
# ============================================

class LazyLoader:
    """Lazy loading for expensive resources"""
    
    def __init__(self, loader_func: Callable):
        self.loader_func = loader_func
        self._value = None
        self._loaded = False
        self._lock = threading.Lock()
    
    @property
    def value(self):
        """Get the lazily loaded value"""
        if not self._loaded:
            with self._lock:
                if not self._loaded:  # Double-check
                    self._value = self.loader_func()
                    self._loaded = True
        return self._value
    
    def reload(self):
        """Force reload of the value"""
        with self._lock:
            self._value = self.loader_func()
            self._loaded = True
        return self._value

# ============================================
# Batch Processing
# ============================================

class BatchProcessor:
    """Process items in batches for efficiency"""
    
    def __init__(self, process_func: Callable, batch_size: int = 100, flush_interval: float = 1.0):
        self.process_func = process_func
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batch = []
        self.lock = threading.Lock()
        self.last_flush = time.time()
        self.flush_thread = None
        self.running = False
    
    def add(self, item: Any):
        """Add item to batch"""
        with self.lock:
            self.batch.append(item)
            
            # Process if batch is full
            if len(self.batch) >= self.batch_size:
                self._process_batch()
    
    def start(self):
        """Start batch processor"""
        if not self.running:
            self.running = True
            self.flush_thread = threading.Thread(target=self._flush_loop)
            self.flush_thread.daemon = True
            self.flush_thread.start()
    
    def stop(self):
        """Stop batch processor"""
        self.running = False
        if self.flush_thread:
            self.flush_thread.join(timeout=5)
        
        # Process remaining items
        with self.lock:
            if self.batch:
                self._process_batch()
    
    def _flush_loop(self):
        """Periodically flush batches"""
        while self.running:
            time.sleep(self.flush_interval)
            
            with self.lock:
                if self.batch and time.time() - self.last_flush >= self.flush_interval:
                    self._process_batch()
    
    def _process_batch(self):
        """Process current batch"""
        if not self.batch:
            return
        
        try:
            self.process_func(self.batch)
            self.batch = []
            self.last_flush = time.time()
        except Exception as e:
            logger.error(f"Batch processing error: {e}")

# ============================================
# Export
# ============================================

__all__ = [
    'CacheManager',
    'cache_manager',
    'cache',
    'cache_async',
    'DatabasePool',
    'db_pool',
    'CompressionMiddleware',
    'QueryOptimizer',
    'MemoryManager',
    'PerformanceMonitor',
    'LazyLoader',
    'BatchProcessor'
]