"""
Optimized memory search with Redis caching and indexing
Replaces the slow file-based search with O(1) lookups
"""

import os
import json
import hashlib
import pickle
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import redis
from redis import Redis
import numpy as np
from functools import lru_cache
from pathlib import Path
import aiofiles
import logging
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import re

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """Memory data structure"""
    id: str
    user_id: str
    content: str
    category: str
    timestamp: datetime
    tags: List[str]
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class MemoryIndex:
    """In-memory index for fast searching"""

    def __init__(self):
        self.word_to_memories: Dict[str, Set[str]] = {}  # word -> memory_ids
        self.category_to_memories: Dict[str, Set[str]] = {}  # category -> memory_ids
        self.tag_to_memories: Dict[str, Set[str]] = {}  # tag -> memory_ids
        self.user_to_memories: Dict[str, Set[str]] = {}  # user_id -> memory_ids
        self.memories: Dict[str, Memory] = {}  # memory_id -> Memory

    def add_memory(self, memory: Memory):
        """Add memory to indexes"""
        memory_id = memory.id

        # Add to main storage
        self.memories[memory_id] = memory

        # Index by user
        if memory.user_id not in self.user_to_memories:
            self.user_to_memories[memory.user_id] = set()
        self.user_to_memories[memory.user_id].add(memory_id)

        # Index by category
        if memory.category:
            if memory.category not in self.category_to_memories:
                self.category_to_memories[memory.category] = set()
            self.category_to_memories[memory.category].add(memory_id)

        # Index by tags
        for tag in memory.tags:
            if tag not in self.tag_to_memories:
                self.tag_to_memories[tag] = set()
            self.tag_to_memories[tag].add(memory_id)

        # Index by words (simple tokenization)
        words = self._tokenize(memory.content)
        for word in words:
            if word not in self.word_to_memories:
                self.word_to_memories[word] = set()
            self.word_to_memories[word].add(memory_id)

    def _tokenize(self, text: str) -> Set[str]:
        """Simple tokenization"""
        # Convert to lowercase and split by non-alphanumeric
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        return set(w for w in words if w not in stop_words and len(w) > 2)

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories using indexes"""
        # Start with all memories for user
        if user_id:
            candidate_ids = self.user_to_memories.get(user_id, set())
        else:
            candidate_ids = set(self.memories.keys())

        # Filter by category
        if category and category in self.category_to_memories:
            candidate_ids &= self.category_to_memories[category]

        # Filter by tags
        if tags:
            for tag in tags:
                if tag in self.tag_to_memories:
                    candidate_ids &= self.tag_to_memories[tag]

        # Search by query words
        if query:
            query_words = self._tokenize(query)
            matching_ids = set()
            for word in query_words:
                if word in self.word_to_memories:
                    matching_ids |= self.word_to_memories[word]
            candidate_ids &= matching_ids

        # Get memories and sort by relevance
        results = []
        for memory_id in candidate_ids:
            memory = self.memories[memory_id]
            score = self._calculate_relevance(memory, query)
            results.append((score, memory))

        # Sort by score and return top results
        results.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in results[:limit]]

    def _calculate_relevance(self, memory: Memory, query: str) -> float:
        """Calculate relevance score"""
        if not query:
            return memory.timestamp.timestamp()

        query_words = self._tokenize(query)
        memory_words = self._tokenize(memory.content)

        # Calculate Jaccard similarity
        intersection = len(query_words & memory_words)
        union = len(query_words | memory_words)

        if union == 0:
            return 0.0

        jaccard = intersection / union

        # Boost recent memories
        recency_boost = 1.0 / (1.0 + (datetime.now() - memory.timestamp).days)

        return jaccard + recency_boost * 0.1


class OptimizedMemorySearch:
    """Optimized memory search with caching and indexing"""

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        memory_path: str = "./app/memory-system/users",
        cache_ttl: int = 3600
    ):
        self.redis = redis_client or self._create_redis_client()
        self.memory_path = Path(memory_path)
        self.cache_ttl = cache_ttl
        self.index = MemoryIndex()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._index_loaded = False
        self._index_lock = asyncio.Lock()

    def _create_redis_client(self) -> Optional[Redis]:
        """Create Redis client with fallback"""
        try:
            client = redis.Redis(
                host='localhost',
                port=6379,
                db=1,  # Use different DB for memories
                decode_responses=False,  # We'll use pickle
                socket_connect_timeout=1
            )
            client.ping()
            logger.info("Connected to Redis for memory caching")
            return client
        except:
            logger.warning("Redis not available, using in-memory cache only")
            return None

    async def ensure_index_loaded(self):
        """Ensure index is loaded (lazy loading)"""
        if self._index_loaded:
            return

        async with self._index_lock:
            if self._index_loaded:
                return

            await self._load_index()
            self._index_loaded = True

    async def _load_index(self):
        """Load all memories into index"""
        logger.info("Loading memory index...")
        start_time = asyncio.get_event_loop().time()

        # Try to load from Redis cache first
        if self.redis:
            try:
                cached_index = self.redis.get("memory:index")
                if cached_index:
                    self.index = pickle.loads(cached_index)
                    logger.info("Loaded index from Redis cache")
                    return
            except Exception as e:
                logger.error(f"Failed to load cached index: {e}")

        # Load from files
        memory_count = 0
        tasks = []

        for user_dir in self.memory_path.glob("*"):
            if user_dir.is_dir():
                for category_dir in user_dir.glob("*"):
                    if category_dir.is_dir():
                        for memory_file in category_dir.glob("*.md"):
                            tasks.append(self._load_memory_file(
                                user_dir.name,
                                category_dir.name,
                                memory_file
                            ))

        # Load memories in parallel
        if tasks:
            memories = await asyncio.gather(*tasks, return_exceptions=True)
            for memory in memories:
                if isinstance(memory, Memory):
                    self.index.add_memory(memory)
                    memory_count += 1

        # Cache the index
        if self.redis and memory_count > 0:
            try:
                serialized = pickle.dumps(self.index)
                self.redis.setex("memory:index", self.cache_ttl, serialized)
            except Exception as e:
                logger.error(f"Failed to cache index: {e}")

        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info(f"Loaded {memory_count} memories in {elapsed:.2f}s")

    async def _load_memory_file(
        self,
        user_id: str,
        category: str,
        file_path: Path
    ) -> Optional[Memory]:
        """Load a single memory file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Extract metadata from filename
            memory_id = file_path.stem

            # Parse tags from content (assuming format: #tag1 #tag2)
            tags = re.findall(r'#(\w+)', content)

            # Get file modification time as timestamp
            timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)

            return Memory(
                id=memory_id,
                user_id=user_id,
                content=content,
                category=category,
                timestamp=timestamp,
                tags=tags,
                metadata={}
            )
        except Exception as e:
            logger.error(f"Failed to load memory {file_path}: {e}")
            return None

    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Search memories with caching"""
        # Ensure index is loaded
        await self.ensure_index_loaded()

        # Generate cache key
        cache_key = self._generate_cache_key(query, user_id, category, tags, limit)

        # Try cache first
        if use_cache and self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for query: {query}")
                    return pickle.loads(cached)
            except Exception as e:
                logger.error(f"Cache retrieval failed: {e}")

        # Perform search
        memories = self.index.search(query, user_id, category, tags, limit)

        # Convert to dict format
        results = [memory.to_dict() for memory in memories]

        # Cache results
        if use_cache and self.redis and results:
            try:
                self.redis.setex(
                    cache_key,
                    300,  # 5 minute cache for search results
                    pickle.dumps(results)
                )
            except Exception as e:
                logger.error(f"Cache storage failed: {e}")

        return results

    def _generate_cache_key(
        self,
        query: str,
        user_id: Optional[str],
        category: Optional[str],
        tags: Optional[List[str]],
        limit: int
    ) -> str:
        """Generate cache key for search"""
        key_parts = [
            "search",
            hashlib.md5(query.encode()).hexdigest()[:8],
            user_id or "all",
            category or "all",
            "_".join(sorted(tags)) if tags else "notags",
            str(limit)
        ]
        return ":".join(key_parts)

    async def add_memory(
        self,
        user_id: str,
        content: str,
        category: str = "GENERAL",
        tags: Optional[List[str]] = None
    ) -> str:
        """Add new memory and update index"""
        # Generate memory ID
        memory_id = hashlib.md5(
            f"{user_id}{content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Create memory object
        memory = Memory(
            id=memory_id,
            user_id=user_id,
            content=content,
            category=category,
            timestamp=datetime.now(),
            tags=tags or [],
            metadata={}
        )

        # Add to index
        self.index.add_memory(memory)

        # Save to file
        await self._save_memory_file(memory)

        # Invalidate caches
        await self._invalidate_user_cache(user_id)

        return memory_id

    async def _save_memory_file(self, memory: Memory):
        """Save memory to file"""
        user_dir = self.memory_path / memory.user_id / memory.category
        user_dir.mkdir(parents=True, exist_ok=True)

        file_path = user_dir / f"{memory.id}.md"

        # Format content with tags
        content = memory.content
        if memory.tags:
            content += "\n\n" + " ".join(f"#{tag}" for tag in memory.tags)

        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)

    async def _invalidate_user_cache(self, user_id: str):
        """Invalidate cache for user"""
        if not self.redis:
            return

        try:
            # Delete all cache keys for this user
            pattern = f"search:*:{user_id}:*"
            for key in self.redis.scan_iter(match=pattern):
                self.redis.delete(key)

            # Mark index for reload
            self.redis.delete("memory:index")
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get search statistics"""
        await self.ensure_index_loaded()

        return {
            "total_memories": len(self.index.memories),
            "total_users": len(self.index.user_to_memories),
            "total_categories": len(self.index.category_to_memories),
            "total_tags": len(self.index.tag_to_memories),
            "index_loaded": self._index_loaded,
            "cache_available": self.redis is not None
        }


# Singleton instance
_search_instance: Optional[OptimizedMemorySearch] = None


def get_memory_search() -> OptimizedMemorySearch:
    """Get singleton instance of memory search"""
    global _search_instance
    if _search_instance is None:
        _search_instance = OptimizedMemorySearch()
    return _search_instance


# FastAPI dependency
async def get_search_service() -> OptimizedMemorySearch:
    """FastAPI dependency for memory search"""
    search = get_memory_search()
    await search.ensure_index_loaded()
    return search