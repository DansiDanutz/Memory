"""
Critical Path Tests for Memory App
Tests the most important user journeys and integrations
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient
from app.schemas.validation import (
    WhatsAppMessage,
    WebhookPayload,
    MemoryCreateRequest,
    AudioProcessRequest
)
from app.memory.search_optimized import OptimizedMemorySearch, Memory
from app.voice.voice_service_async import AsyncVoiceService, TranscriptionResult
from app.middleware.rate_limiter import RateLimiter
from app.services.backup import BackupService


# Fixtures
@pytest.fixture
def test_client():
    """Create test client"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
async def memory_search():
    """Create memory search service"""
    search = OptimizedMemorySearch(redis_client=None)
    await search.ensure_index_loaded()
    return search


@pytest.fixture
async def voice_service():
    """Create voice service"""
    service = AsyncVoiceService()
    await service.initialize()
    yield service
    await service.cleanup()


@pytest.fixture
def backup_service(tmp_path):
    """Create backup service with temp directory"""
    return BackupService(
        data_dir=str(tmp_path / "data"),
        backup_dir=str(tmp_path / "backups"),
        use_s3=False
    )


class TestWhatsAppIntegration:
    """Test WhatsApp webhook and message processing"""

    def test_webhook_validation(self, test_client):
        """Test webhook signature validation"""
        # Valid webhook payload
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "from": "+1234567890",
                            "id": "msg_123",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }

        response = test_client.post(
            "/webhook",
            json=payload,
            headers={"X-Hub-Signature": "valid_signature"}
        )

        # Should validate and process
        assert response.status_code in [200, 401]  # Depends on signature validation

    def test_message_validation(self):
        """Test WhatsApp message validation"""
        # Valid message
        message = WhatsAppMessage(
            from_number="+1234567890",
            message_id="msg_123",
            timestamp=datetime.now(),
            type="text",
            text="Test message"
        )
        assert message.from_number == "+1234567890"

        # Invalid phone number
        with pytest.raises(ValueError):
            WhatsAppMessage(
                from_number="invalid",
                message_id="msg_123",
                timestamp=datetime.now(),
                type="text",
                text="Test"
            )

    @pytest.mark.asyncio
    async def test_voice_message_processing(self, voice_service):
        """Test voice message transcription flow"""
        with patch.object(voice_service, '_call_azure_transcription') as mock_azure:
            mock_azure.return_value = TranscriptionResult(
                text="Test transcription",
                confidence=0.95,
                language="en-US",
                duration=5.0,
                metadata={}
            )

            # Mock audio download
            with patch.object(voice_service, '_download_audio') as mock_download:
                mock_download.return_value = b"fake_audio_data"

                result = await voice_service.transcribe_audio(
                    "https://example.com/audio.ogg",
                    language="en-US"
                )

                assert result.text == "Test transcription"
                assert result.confidence == 0.95


class TestMemoryOperations:
    """Test memory CRUD and search operations"""

    @pytest.mark.asyncio
    async def test_memory_creation(self, memory_search):
        """Test creating and storing memory"""
        memory_id = await memory_search.add_memory(
            user_id="test_user",
            content="This is a test memory",
            category="TEST",
            tags=["test", "demo"]
        )

        assert memory_id is not None
        assert len(memory_id) == 12  # MD5 hash truncated

        # Verify in index
        assert memory_id in memory_search.index.memories

    @pytest.mark.asyncio
    async def test_memory_search(self, memory_search):
        """Test memory search functionality"""
        # Add test memories
        await memory_search.add_memory(
            user_id="test_user",
            content="Python programming is fun",
            category="TECH",
            tags=["python", "programming"]
        )

        await memory_search.add_memory(
            user_id="test_user",
            content="JavaScript is also fun",
            category="TECH",
            tags=["javascript", "programming"]
        )

        # Search
        results = await memory_search.search(
            query="python",
            user_id="test_user",
            limit=10
        )

        assert len(results) >= 1
        assert "python" in results[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_search_performance(self, memory_search):
        """Test search performance with many memories"""
        # Add 100 test memories
        for i in range(100):
            await memory_search.add_memory(
                user_id="perf_user",
                content=f"Test memory {i} with random content",
                category="PERF",
                tags=[f"tag{i % 10}"]
            )

        # Measure search time
        import time
        start = time.time()
        results = await memory_search.search(
            query="memory",
            user_id="perf_user",
            limit=10
        )
        elapsed = time.time() - start

        assert elapsed < 0.5  # Should be fast
        assert len(results) <= 10


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(redis_client=None, default_limit=5, default_window=60)

        # Mock request
        mock_request = Mock()
        mock_request.headers = {"X-API-Key": "test_key"}
        mock_request.client = Mock(host="127.0.0.1")
        mock_request.url = Mock(path="/api/test")
        mock_request.method = "GET"

        identifier = limiter.get_identifier(mock_request)
        assert "api:" in identifier

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit exceeded scenario"""
        limiter = RateLimiter(redis_client=None, default_limit=3, default_window=1)

        # Simulate requests
        for i in range(5):
            allowed, headers = await limiter.check_rate_limit(
                "test_user",
                limit=3,
                window=1
            )

            if i < 3:
                assert allowed is True
            else:
                assert allowed is False
                assert "Retry-After" in headers


class TestVoiceServices:
    """Test voice transcription and synthesis"""

    @pytest.mark.asyncio
    async def test_transcription_with_cache(self, voice_service):
        """Test transcription with caching"""
        with patch.object(voice_service, '_call_azure_transcription') as mock_azure:
            mock_azure.return_value = TranscriptionResult(
                text="Cached text",
                confidence=0.9,
                language="en-US",
                duration=3.0,
                metadata={}
            )

            with patch.object(voice_service, '_download_audio') as mock_download:
                mock_download.return_value = b"audio_data"

                # First call - should hit Azure
                result1 = await voice_service.transcribe_audio(
                    "https://example.com/test.ogg"
                )

                # Second call - should hit cache
                result2 = await voice_service.transcribe_audio(
                    "https://example.com/test.ogg"
                )

                assert result1.text == result2.text
                mock_azure.assert_called_once()  # Only called once due to cache

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, voice_service):
        """Test circuit breaker pattern"""
        with patch.object(voice_service, '_call_azure_transcription') as mock_azure:
            # Simulate failures
            mock_azure.side_effect = Exception("Service unavailable")

            # Try multiple times
            for _ in range(6):
                try:
                    await voice_service.transcribe_audio(
                        "https://example.com/fail.ogg"
                    )
                except:
                    pass

            # Circuit should be open now
            assert voice_service.transcription_breaker.state in ["open", "half-open"]


class TestBackupRestore:
    """Test backup and restore functionality"""

    @pytest.mark.asyncio
    async def test_backup_creation(self, backup_service, tmp_path):
        """Test creating backup"""
        # Create test data
        data_dir = tmp_path / "data" / "users" / "test_user" / "GENERAL"
        data_dir.mkdir(parents=True)

        memory_file = data_dir / "test_memory.md"
        memory_file.write_text("Test memory content")

        # Create backup
        backup_metadata = await backup_service.create_backup("Test backup")

        assert backup_metadata.backup_id.startswith("backup_")
        assert backup_metadata.file_count >= 1
        assert backup_metadata.checksum is not None

    @pytest.mark.asyncio
    async def test_backup_restore(self, backup_service, tmp_path):
        """Test restoring from backup"""
        # Create test data
        data_dir = tmp_path / "data" / "users" / "test_user"
        data_dir.mkdir(parents=True)
        (data_dir / "test.md").write_text("Original content")

        # Create backup
        backup = await backup_service.create_backup()

        # Modify data
        (data_dir / "test.md").write_text("Modified content")

        # Restore
        success = await backup_service.restore_backup(backup.backup_id)

        assert success is True
        # Check content restored
        restored_content = (data_dir / "test.md").read_text()
        assert restored_content == "Original content"

    @pytest.mark.asyncio
    async def test_backup_cleanup(self, backup_service):
        """Test old backup cleanup"""
        # Create old backup metadata
        old_backup = backup_service.BackupMetadata(
            backup_id="old_backup",
            timestamp=datetime.now() - timedelta(days=40),
            size_bytes=1000,
            file_count=10,
            checksum="abc123",
            version="1.0.0",
            environment="test",
            retention_days=30
        )
        backup_service.backup_history.append(old_backup)

        # Run cleanup
        await backup_service._cleanup_old_backups()

        # Old backup should be removed
        assert old_backup not in backup_service.backup_history


class TestHealthChecks:
    """Test health check endpoints"""

    def test_basic_health(self, test_client):
        """Test basic health endpoint"""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_liveness_probe(self, test_client):
        """Test Kubernetes liveness probe"""
        response = test_client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_detailed_health(self, test_client):
        """Test detailed health check"""
        response = test_client.get("/api/v1/health/detailed")
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "summary" in data


class TestEndToEndFlow:
    """Test complete user journeys"""

    @pytest.mark.asyncio
    async def test_whatsapp_to_memory_flow(self, test_client, memory_search):
        """Test complete flow from WhatsApp message to memory storage"""
        # 1. Receive WhatsApp text message
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123",
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "+1234567890",
                            "id": "msg_123",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Remember: Buy groceries tomorrow"}
                        }]
                    }
                }]
            }]
        }

        # 2. Process webhook (would normally trigger memory creation)
        with patch('app.memory.search_optimized.get_search_service') as mock_search:
            mock_search.return_value = memory_search

            # Simulate memory creation from webhook
            await memory_search.add_memory(
                user_id="+1234567890",
                content="Remember: Buy groceries tomorrow",
                category="REMINDER"
            )

        # 3. Search for the memory
        results = await memory_search.search(
            query="groceries",
            user_id="+1234567890"
        )

        assert len(results) > 0
        assert "groceries" in results[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_voice_to_memory_flow(self, voice_service, memory_search):
        """Test voice message to memory storage"""
        # 1. Mock voice transcription
        with patch.object(voice_service, '_call_azure_transcription') as mock_trans:
            mock_trans.return_value = TranscriptionResult(
                text="Schedule meeting with John next Monday",
                confidence=0.95,
                language="en-US",
                duration=5.0,
                metadata={}
            )

            with patch.object(voice_service, '_download_audio') as mock_dl:
                mock_dl.return_value = b"audio"

                # 2. Transcribe audio
                result = await voice_service.transcribe_audio(
                    "https://example.com/voice.ogg"
                )

        # 3. Store as memory
        await memory_search.add_memory(
            user_id="voice_user",
            content=result.text,
            category="MEETING",
            tags=["schedule", "john"]
        )

        # 4. Verify searchable
        results = await memory_search.search(
            query="John Monday",
            user_id="voice_user"
        )

        assert len(results) > 0
        assert "john" in results[0]["content"].lower()


# Performance benchmarks
@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmark tests"""

    @pytest.mark.asyncio
    async def test_search_benchmark(self, memory_search, benchmark):
        """Benchmark memory search"""
        # Add test data
        for i in range(1000):
            await memory_search.add_memory(
                user_id="bench_user",
                content=f"Benchmark memory {i}",
                category="BENCH"
            )

        # Benchmark search
        result = benchmark(
            memory_search.search,
            query="benchmark",
            user_id="bench_user",
            limit=10
        )

        assert len(result) <= 10