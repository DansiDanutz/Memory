#!/usr/bin/env python3
"""
Memory Search Module
Provides search functionality for stored memories
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MemorySearch:
    """Search through user memories"""
    
    def __init__(self, memory_storage):
        """Initialize search with memory storage instance"""
        self.memory_storage = memory_storage
        # Import tenancy manager for scoped searches
        # Import tenancy manager for scoped searches
        from app.tenancy.model import TenancyManager
        self.tenancy_manager = TenancyManager()
        logger.info("🔍 Memory search initialized")
    
    async def search(self, user_phone: str, query: str, 
                    category: Optional[str] = None,
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None,
                    limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search memories with various filters
        
        Args:
            user_phone: User's phone number
            query: Search query string
            category: Optional category filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results to return
        
        Returns:
            List of matching memories
        """
        try:
            user_dir = self.memory_storage._get_user_dir(user_phone)
            index_file = user_dir / "index.json"
            
            if not index_file.exists():
                return []
            
            # Load index
            with open(index_file, 'r') as f:
                index = json.load(f)
            
            memories = index.get("memories", [])
            results = []
            
            # Prepare search terms
            search_terms = query.lower().split()
            
            for memory in memories:
                # Category filter
                if category and memory["category"] != category:
                    continue
                
                # Date filter
                if start_date or end_date:
                    memory_date = datetime.fromisoformat(memory["timestamp"])
                    if start_date and memory_date < start_date:
                        continue
                    if end_date and memory_date > end_date:
                        continue
                
                # Search in memory content
                score = 0
                content_preview = memory.get("content_preview", "").lower()
                
                # Check each search term
                for term in search_terms:
                    if term in content_preview:
                        score += content_preview.count(term)
                
                # If encrypted, we need to decrypt and search
                if memory.get("encrypted") and score == 0:
                    # Get full memory to search encrypted content
                    full_memory = await self.memory_storage.get_memory(user_phone, memory["id"])
                    if full_memory:
                        decrypted_content = full_memory.get("content", "").lower()
                        for term in search_terms:
                            if term in decrypted_content:
                                score += decrypted_content.count(term)
                                # Update preview for results
                                memory["content_preview"] = full_memory["content"][:100]
                
                if score > 0:
                    memory["search_score"] = score
                    results.append(memory)
            
            # Sort by relevance (score) and then by date
            results.sort(key=lambda x: (-x.get("search_score", 0), x["timestamp"]), reverse=True)
            
            # Limit results
            results = results[:limit]
            
            # Clean up score from results
            for result in results:
                result.pop("search_score", None)
            
            logger.info(f"Search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    async def search_department(self, department_id: str, tenant_id: str, 
                               query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search memories within a department"""
        try:
            # Get all users in the department
            dept_users = self.tenancy_manager.get_department_users(tenant_id, department_id)
            
            all_results = []
            search_terms = query.lower().split()
            
            # Search each user's memories
            for user_phone in dept_users:
                user_dir = self.memory_storage._get_user_dir(user_phone)
                index_file = user_dir / "index.json"
                
                if not index_file.exists():
                    continue
                
                with open(index_file, 'r') as f:
                    index = json.load(f)
                
                # Search user's memories
                for memory in index.get("memories", []):
                    # Check if memory belongs to this department
                    if memory.get("department_id") != department_id:
                        continue
                    
                    score = 0
                    content_preview = memory.get("content_preview", "").lower()
                    
                    for term in search_terms:
                        if term in content_preview:
                            score += content_preview.count(term)
                    
                    if score > 0:
                        memory["search_score"] = score
                        memory["user_phone"] = user_phone  # Include user info
                        all_results.append(memory)
            
            # Sort and limit results
            all_results.sort(key=lambda x: (-x.get("search_score", 0), x["timestamp"]), reverse=True)
            all_results = all_results[:limit]
            
            # Clean up score
            for result in all_results:
                result.pop("search_score", None)
            
            logger.info(f"Department search for '{query}' returned {len(all_results)} results")
            return all_results
            
        except Exception as e:
            logger.error(f"Department search error: {e}")
            return []
    
    async def search_tenant(self, tenant_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search memories across entire tenant"""
        try:
            # Get all users in the tenant
            tenant_users = self.tenancy_manager.get_tenant_users(tenant_id)
            
            all_results = []
            search_terms = query.lower().split()
            
            # Search each user's memories
            for user_phone in tenant_users:
                user_dir = self.memory_storage._get_user_dir(user_phone)
                index_file = user_dir / "index.json"
                
                if not index_file.exists():
                    continue
                
                with open(index_file, 'r') as f:
                    index = json.load(f)
                
                # Search user's memories
                for memory in index.get("memories", []):
                    # Check if memory belongs to this tenant
                    if memory.get("tenant_id") != tenant_id:
                        continue
                    
                    score = 0
                    content_preview = memory.get("content_preview", "").lower()
                    
                    for term in search_terms:
                        if term in content_preview:
                            score += content_preview.count(term)
                    
                    if score > 0:
                        memory["search_score"] = score
                        memory["user_phone"] = user_phone  # Include user info
                        all_results.append(memory)
            
            # Sort and limit results
            all_results.sort(key=lambda x: (-x.get("search_score", 0), x["timestamp"]), reverse=True)
            all_results = all_results[:limit]
            
            # Clean up score
            for result in all_results:
                result.pop("search_score", None)
            
            logger.info(f"Tenant search for '{query}' returned {len(all_results)} results")
            return all_results
            
        except Exception as e:
            logger.error(f"Tenant search error: {e}")
            return []
    
    async def search_by_regex(self, user_phone: str, pattern: str, 
                            category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search memories using regex pattern"""
        try:
            user_dir = self.memory_storage._get_user_dir(user_phone)
            results = []
            regex = re.compile(pattern, re.IGNORECASE)
            
            # Search through category directories
            for category_dir in user_dir.iterdir():
                if category_dir.is_dir():
                    # Apply category filter
                    if category and category_dir.name != category:
                        continue
                    
                    # Search markdown files
                    for file_path in category_dir.glob("*.md"):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Find all memory blocks
                        memory_blocks = re.findall(
                            r'## Memory \[(.*?)\].*?(?=## Memory|\Z)',
                            content,
                            re.DOTALL
                        )
                        
                        for memory_block in memory_blocks:
                            if regex.search(memory_block):
                                # Extract memory ID from block
                                memory_id_match = re.search(r'\[(.*?)\]', memory_block)
                                if memory_id_match:
                                    memory_id = memory_id_match.group(1)
                                    memory = await self.memory_storage.get_memory(user_phone, memory_id)
                                    if memory:
                                        results.append(memory)
            
            return results
            
        except Exception as e:
            logger.error(f"Regex search error: {e}")
            return []
    
    async def get_related_memories(self, user_phone: str, memory_id: str, 
                                 max_results: int = 5) -> List[Dict[str, Any]]:
        """Find memories related to a specific memory"""
        try:
            # Get the source memory
            source_memory = await self.memory_storage.get_memory(user_phone, memory_id)
            if not source_memory:
                return []
            
            # Extract keywords from source memory
            content = source_memory.get("content", "")
            
            # Simple keyword extraction (can be improved with NLP)
            words = re.findall(r'\b[a-z]{4,}\b', content.lower())
            
            # Remove common words
            common_words = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'what', 'when', 'where', 'which', 'their', 'would', 'could', 'should'}
            keywords = [w for w in words if w not in common_words]
            
            # Get most common keywords
            from collections import Counter
            keyword_counts = Counter(keywords)
            top_keywords = [word for word, _ in keyword_counts.most_common(5)]
            
            # Search for memories with these keywords
            if top_keywords:
                query = ' '.join(top_keywords)
                results = await self.search(user_phone, query, limit=max_results + 1)
                
                # Remove the source memory from results
                results = [r for r in results if r["id"] != memory_id]
                
                return results[:max_results]
            
            return []
            
        except Exception as e:
            logger.error(f"Related memories search error: {e}")
            return []
    
    async def get_memories_by_topic(self, user_phone: str, topic: str) -> List[Dict[str, Any]]:
        """Get memories related to a specific topic"""
        # Define topic keywords
        topic_keywords = {
            "work": ["office", "job", "work", "meeting", "project", "deadline", "colleague", "boss", "client"],
            "family": ["family", "mother", "father", "sister", "brother", "parent", "child", "son", "daughter"],
            "health": ["health", "doctor", "medical", "medicine", "hospital", "sick", "pain", "treatment"],
            "finance": ["money", "bank", "payment", "bill", "expense", "income", "budget", "investment"],
            "travel": ["travel", "trip", "vacation", "flight", "hotel", "visit", "journey", "destination"],
            "education": ["school", "university", "study", "learn", "course", "exam", "degree", "education"],
            "hobby": ["hobby", "fun", "enjoy", "weekend", "free time", "interest", "activity", "sport"],
            "food": ["food", "eat", "meal", "breakfast", "lunch", "dinner", "restaurant", "cook"]
        }
        
        # Get keywords for topic
        keywords = topic_keywords.get(topic.lower(), [topic.lower()])
        query = ' '.join(keywords)
        
        # Search with topic keywords
        return await self.search(user_phone, query)
    
    async def get_timeline_memories(self, user_phone: str, 
                                  date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get chronological memories for a specific date or period"""
        if not date:
            date = datetime.now()
        
        # Get memories from CHRONOLOGICAL category for the date
        memories = await self.search(
            user_phone,
            query="",  # Empty query to get all
            category="CHRONOLOGICAL",
            start_date=datetime(date.year, date.month, date.day),
            end_date=datetime(date.year, date.month, date.day, 23, 59, 59)
        )
        
        # Sort by time
        memories.sort(key=lambda x: x["timestamp"])
        
        return memories