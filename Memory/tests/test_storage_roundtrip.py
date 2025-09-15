#!/usr/bin/env python3
"""
Test Memory Storage Round-trip
Tests writing and reading memories with encryption
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from memory.storage import MemoryStorage

class TestMemoryStorage:
    """Test memory storage write and read operations"""
    
    @pytest.fixture
    async def storage(self):
        """Create storage instance with temp directory"""
        temp_dir = tempfile.mkdtemp(prefix="test_memory_")
        storage = MemoryStorage(base_dir=temp_dir)
        yield storage
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_general_memory(self, storage):
        """Test storing and retrieving a GENERAL memory"""
        user_phone = "+1234567890"
        content = "I like pizza and hiking"
        category = "GENERAL"
        timestamp = datetime.now()
        
        # Store memory
        memory_id = await storage.store_memory(user_phone, content, category, timestamp)
        assert memory_id is not None
        assert len(memory_id) == 8  # UUID first 8 chars
        
        # Retrieve memory
        memory = await storage.get_memory(user_phone, memory_id)
        assert memory is not None
        assert memory["content"] == content
        assert memory["category"] == category
        assert memory["id"] == memory_id
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_secret_memory(self, storage):
        """Test storing and retrieving an encrypted SECRET memory"""
        user_phone = "+1234567890"
        content = "My bank account number is 12345678"
        category = "SECRET"
        timestamp = datetime.now()
        
        # Store memory
        memory_id = await storage.store_memory(user_phone, content, category, timestamp)
        assert memory_id is not None
        
        # Retrieve memory - should be encrypted
        memory = await storage.get_memory(user_phone, memory_id)
        assert memory is not None
        assert memory["category"] == category
        assert memory["encrypted"] == True
        # Content should be encrypted
        assert memory["content"] != content  # Raw content is encrypted
    
    @pytest.mark.asyncio
    async def test_get_recent_memories(self, storage):
        """Test retrieving recent memories"""
        user_phone = "+1234567890"
        
        # Store multiple memories
        memory_ids = []
        for i in range(5):
            content = f"Test memory {i}"
            memory_id = await storage.store_memory(
                user_phone, 
                content, 
                "GENERAL", 
                datetime.now() - timedelta(minutes=i)
            )
            memory_ids.append(memory_id)
        
        # Get recent memories
        recent = await storage.get_recent_memories(user_phone, limit=3)
        assert len(recent) == 3
        # Should be ordered by most recent first
        assert "Test memory 0" in recent[0]["content"]
    
    @pytest.mark.asyncio
    async def test_get_memories_by_date(self, storage):
        """Test retrieving memories by specific date"""
        user_phone = "+1234567890"
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # Store memories on different dates
        await storage.store_memory(user_phone, "Today's memory", "GENERAL", today)
        await storage.store_memory(user_phone, "Yesterday's memory", "GENERAL", yesterday)
        
        # Get today's memories
        today_memories = await storage.get_memories_by_date(user_phone, today)
        assert len(today_memories) >= 1
        assert any("Today's memory" in m["content"] for m in today_memories)
        
        # Get yesterday's memories
        yesterday_memories = await storage.get_memories_by_date(user_phone, yesterday)
        assert len(yesterday_memories) >= 1
        assert any("Yesterday's memory" in m["content"] for m in yesterday_memories)
    
    @pytest.mark.asyncio
    async def test_get_category_stats(self, storage):
        """Test category statistics"""
        user_phone = "+1234567890"
        
        # Store memories in different categories
        await storage.store_memory(user_phone, "Meeting tomorrow", "CHRONOLOGICAL")
        await storage.store_memory(user_phone, "I like coffee", "GENERAL")
        await storage.store_memory(user_phone, "I like tea", "GENERAL")
        await storage.store_memory(user_phone, "My password", "CONFIDENTIAL")
        
        # Get stats
        stats = await storage.get_category_stats(user_phone)
        assert stats["CHRONOLOGICAL"] == 1
        assert stats["GENERAL"] == 2
        assert stats["CONFIDENTIAL"] == 1
        assert stats.get("SECRET", 0) == 0
    
    @pytest.mark.asyncio
    async def test_get_user_stats(self, storage):
        """Test user statistics"""
        user_phone = "+1234567890"
        
        # Store some memories
        first_time = datetime.now() - timedelta(days=5)
        await storage.store_memory(user_phone, "First memory", "GENERAL", first_time)
        await storage.store_memory(user_phone, "Second memory", "GENERAL")
        await storage.store_memory(user_phone, "Third memory", "CONFIDENTIAL")
        
        # Get stats
        stats = await storage.get_user_stats(user_phone)
        assert stats["total"] == 3
        assert "GENERAL" in stats["by_category"]
        assert stats["by_category"]["GENERAL"] == 2
        assert stats["by_category"]["CONFIDENTIAL"] == 1
        assert "first_memory" in stats
        assert "last_memory" in stats
    
    @pytest.mark.asyncio
    async def test_chronological_file_organization(self, storage):
        """Test that CHRONOLOGICAL memories are organized by date"""
        user_phone = "+1234567890"
        date1 = datetime(2024, 1, 15)
        date2 = datetime(2024, 1, 16)
        
        # Store memories on different dates
        await storage.store_memory(user_phone, "Meeting on 15th", "CHRONOLOGICAL", date1)
        await storage.store_memory(user_phone, "Meeting on 16th", "CHRONOLOGICAL", date2)
        
        # Check file structure
        user_dir = storage._get_user_dir(user_phone)
        chrono_dir = user_dir / "CHRONOLOGICAL"
        
        assert (chrono_dir / "2024-01-15.md").exists()
        assert (chrono_dir / "2024-01-16.md").exists()
    
    @pytest.mark.asyncio
    async def test_index_creation(self, storage):
        """Test that index.json is created and updated"""
        user_phone = "+1234567890"
        
        # Store a memory
        memory_id = await storage.store_memory(user_phone, "Test memory", "GENERAL")
        
        # Check index exists
        user_dir = storage._get_user_dir(user_phone)
        index_file = user_dir / "index.json"
        assert index_file.exists()
        
        # Load and verify index
        import json
        with open(index_file, 'r') as f:
            index = json.load(f)
        
        assert "memories" in index
        assert "stats" in index
        assert len(index["memories"]) == 1
        assert index["memories"][0]["id"] == memory_id
        assert index["stats"]["total"] == 1
    
    @pytest.mark.asyncio
    async def test_memory_not_found(self, storage):
        """Test retrieving non-existent memory"""
        user_phone = "+1234567890"
        
        # Try to get non-existent memory
        memory = await storage.get_memory(user_phone, "fake_id")
        assert memory is None

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])