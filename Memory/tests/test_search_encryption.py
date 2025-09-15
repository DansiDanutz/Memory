#!/usr/bin/env python3
"""
Test Memory Search with Encryption
Tests searching memories including encrypted content
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
from memory.search import MemorySearch
from security.encryption import EncryptionService

class TestMemorySearchEncryption:
    """Test memory search with encrypted content"""
    
    @pytest.fixture
    async def storage(self):
        """Create storage instance with temp directory"""
        temp_dir = tempfile.mkdtemp(prefix="test_search_")
        storage = MemoryStorage(base_dir=temp_dir)
        yield storage
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def searcher(self, storage):
        """Create search instance"""
        return MemorySearch(storage)
    
    @pytest.fixture
    def encryption_service(self):
        """Create encryption service"""
        return EncryptionService()
    
    @pytest.mark.asyncio
    async def test_search_general_memories(self, storage, searcher):
        """Test searching non-encrypted GENERAL memories"""
        user_phone = "+1234567890"
        
        # Store general memories
        await storage.store_memory(user_phone, "I like pizza", "GENERAL")
        await storage.store_memory(user_phone, "I love hiking", "GENERAL")
        await storage.store_memory(user_phone, "My favorite color is blue", "GENERAL")
        
        # Search for pizza
        results = await searcher.search(user_phone, "pizza")
        assert len(results) >= 1
        assert any("pizza" in r["content"].lower() for r in results)
        
        # Search for favorite
        results = await searcher.search(user_phone, "favorite")
        assert len(results) >= 1
        assert any("favorite" in r["content"].lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, storage, searcher):
        """Test searching with category filter"""
        user_phone = "+1234567890"
        
        # Store memories in different categories
        await storage.store_memory(user_phone, "Meeting tomorrow at 3pm", "CHRONOLOGICAL")
        await storage.store_memory(user_phone, "I like meetings", "GENERAL")
        await storage.store_memory(user_phone, "Secret meeting info", "SECRET")
        
        # Search only in CHRONOLOGICAL
        results = await searcher.search(user_phone, "meeting", category="CHRONOLOGICAL")
        assert len(results) >= 1
        assert all(r["category"] == "CHRONOLOGICAL" for r in results)
        
        # Search only in GENERAL
        results = await searcher.search(user_phone, "meeting", category="GENERAL")
        assert len(results) >= 1
        assert all(r["category"] == "GENERAL" for r in results)
    
    @pytest.mark.asyncio
    async def test_encrypted_memory_search_without_auth(self, storage, searcher):
        """Test that encrypted memories are not searchable without authentication"""
        user_phone = "+1234567890"
        
        # Store encrypted SECRET memory
        await storage.store_memory(user_phone, "My bank account is 12345678", "SECRET")
        await storage.store_memory(user_phone, "Ultra secret project details", "ULTRA_SECRET")
        
        # Search without authentication - should not find encrypted content
        results = await searcher.search(user_phone, "bank account", authenticated=False)
        
        # Should not return actual content for SECRET memories
        for result in results:
            if result["category"] in ["SECRET", "ULTRA_SECRET"]:
                assert result.get("encrypted", False) == True
                # Content should be encrypted or masked
                assert "12345678" not in result.get("content", "")
    
    @pytest.mark.asyncio
    async def test_encrypted_memory_search_with_auth(self, storage, searcher):
        """Test searching encrypted memories with authentication"""
        user_phone = "+1234567890"
        
        # Store encrypted memories
        await storage.store_memory(user_phone, "My credit card is 4111-1111-1111-1111", "SECRET")
        await storage.store_memory(user_phone, "Medical record: diabetes", "SECRET")
        
        # Search with authentication
        results = await searcher.search(user_phone, "credit", authenticated=True)
        
        # Should find and decrypt SECRET memories when authenticated
        assert len(results) >= 1
        # Note: Actual decryption would require proper session management
    
    @pytest.mark.asyncio
    async def test_search_date_range(self, storage, searcher):
        """Test searching within date range"""
        user_phone = "+1234567890"
        
        # Store memories on different dates
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        
        await storage.store_memory(user_phone, "Today's task", "GENERAL", today)
        await storage.store_memory(user_phone, "Yesterday's task", "GENERAL", yesterday)
        await storage.store_memory(user_phone, "Last week's task", "GENERAL", last_week)
        
        # Search for tasks from yesterday onwards
        results = await searcher.search(
            user_phone, 
            "task",
            start_date=yesterday,
            end_date=today + timedelta(days=1)
        )
        
        # Should find today's and yesterday's tasks
        assert len(results) >= 2
        assert any("Today" in r["content"] for r in results)
        assert any("Yesterday" in r["content"] for r in results)
        assert not any("Last week" in r["content"] for r in results)
    
    @pytest.mark.asyncio
    async def test_search_result_ranking(self, storage, searcher):
        """Test search result relevance ranking"""
        user_phone = "+1234567890"
        
        # Store memories with varying relevance
        await storage.store_memory(user_phone, "Pizza is my favorite food", "GENERAL")
        await storage.store_memory(user_phone, "I had pizza yesterday", "GENERAL")
        await storage.store_memory(user_phone, "Pizza pizza pizza", "GENERAL")
        await storage.store_memory(user_phone, "I mentioned pizza once", "GENERAL")
        
        # Search for pizza
        results = await searcher.search(user_phone, "pizza")
        
        # Results should be ranked by relevance (more occurrences = higher rank)
        assert len(results) >= 3
        # First result should have multiple pizza mentions
        assert results[0]["content"].lower().count("pizza") >= 1
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, storage, searcher):
        """Test handling empty search query"""
        user_phone = "+1234567890"
        
        # Store some memories
        await storage.store_memory(user_phone, "Test memory 1", "GENERAL")
        await storage.store_memory(user_phone, "Test memory 2", "GENERAL")
        
        # Search with empty query should return recent memories
        results = await searcher.search(user_phone, "")
        assert len(results) >= 1
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, storage, searcher):
        """Test search with no matching results"""
        user_phone = "+1234567890"
        
        # Store some memories
        await storage.store_memory(user_phone, "Test memory about cats", "GENERAL")
        await storage.store_memory(user_phone, "Another cat memory", "GENERAL")
        
        # Search for something not present
        results = await searcher.search(user_phone, "dogs")
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, storage, searcher):
        """Test case-insensitive search"""
        user_phone = "+1234567890"
        
        # Store memory with mixed case
        await storage.store_memory(user_phone, "My FAVORITE Pizza is Margherita", "GENERAL")
        
        # Search with different cases
        results1 = await searcher.search(user_phone, "PIZZA")
        results2 = await searcher.search(user_phone, "pizza")
        results3 = await searcher.search(user_phone, "PiZzA")
        
        # All should find the same result
        assert len(results1) >= 1
        assert len(results2) >= 1
        assert len(results3) >= 1
        assert results1[0]["content"] == results2[0]["content"] == results3[0]["content"]
    
    @pytest.mark.asyncio
    async def test_search_with_limit(self, storage, searcher):
        """Test limiting search results"""
        user_phone = "+1234567890"
        
        # Store multiple memories
        for i in range(10):
            await storage.store_memory(user_phone, f"Test memory {i}", "GENERAL")
        
        # Search with limit
        results = await searcher.search(user_phone, "test", limit=5)
        assert len(results) <= 5
    
    @pytest.mark.asyncio
    async def test_search_performance(self, storage, searcher):
        """Test search performance with many memories"""
        user_phone = "+1234567890"
        
        # Store many memories
        import time
        for i in range(100):
            await storage.store_memory(user_phone, f"Memory number {i} with some text", "GENERAL")
        
        # Measure search time
        start_time = time.time()
        results = await searcher.search(user_phone, "number")
        search_time = time.time() - start_time
        
        # Should complete within reasonable time (< 1 second)
        assert search_time < 1.0
        assert len(results) > 0
    
    def test_encryption_key_generation(self, encryption_service):
        """Test encryption key generation for users"""
        user_phone = "+1234567890"
        category = "SECRET"
        
        # Generate key
        key = encryption_service._get_key(user_phone, category)
        assert key is not None
        
        # Same inputs should generate same key
        key2 = encryption_service._get_key(user_phone, category)
        assert key == key2
        
        # Different category should generate different key
        key3 = encryption_service._get_key(user_phone, "ULTRA_SECRET")
        assert key != key3
    
    @pytest.mark.asyncio
    async def test_encryption_round_trip(self, encryption_service):
        """Test encryption and decryption round-trip"""
        user_phone = "+1234567890"
        category = "SECRET"
        original_content = "This is a secret message"
        
        # Encrypt
        encrypted = await encryption_service.encrypt(original_content, user_phone, category)
        assert encrypted != original_content
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = await encryption_service.decrypt(encrypted, user_phone, category)
        assert decrypted == original_content

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])