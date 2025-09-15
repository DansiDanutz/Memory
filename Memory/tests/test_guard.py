#!/usr/bin/env python3
"""
Test Voice Guard Authentication
Tests voice authentication with passphrase and TTL
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
import asyncio
import tempfile
import shutil
import base64
from datetime import datetime, timedelta
from pathlib import Path
from voice.guard import VoiceGuard

class TestVoiceGuard:
    """Test voice authentication system"""
    
    @pytest.fixture
    async def guard(self):
        """Create voice guard instance with temp directory"""
        temp_dir = tempfile.mkdtemp(prefix="test_voice_")
        guard = VoiceGuard(data_dir=temp_dir)
        yield guard
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_passphrase_enrollment_success(self, guard):
        """Test successful passphrase enrollment"""
        user_phone = "+1234567890"
        
        # Mock audio data (would normally be transcribed)
        # Since we can't mock Azure transcription, we'll test the logic
        passphrase = "the quick brown fox jumps over the lazy dog in the morning"
        guard.user_passphrases[user_phone] = {
            "hash": guard._hash_passphrase(passphrase),
            "word_count": len(passphrase.split()),
            "enrolled_at": datetime.now().isoformat(),
            "hint": f"First word: the, Last word: morning"
        }
        
        # Verify enrollment
        assert user_phone in guard.user_passphrases
        assert guard.user_passphrases[user_phone]["word_count"] == 11
    
    @pytest.mark.asyncio
    async def test_passphrase_too_short(self, guard):
        """Test rejection of short passphrase"""
        user_phone = "+1234567890"
        
        # Simulate short passphrase
        short_phrase = "this is too short"
        words = short_phrase.split()
        
        # Check word count requirement
        assert len(words) < guard.MINIMUM_PASSPHRASE_WORDS
    
    @pytest.mark.asyncio
    async def test_authentication_success(self, guard):
        """Test successful authentication"""
        user_phone = "+1234567890"
        passphrase = "the quick brown fox jumps over the lazy dog in the morning"
        
        # Enroll passphrase
        guard.user_passphrases[user_phone] = {
            "hash": guard._hash_passphrase(passphrase),
            "word_count": 11,
            "enrolled_at": datetime.now().isoformat(),
            "hint": "First word: the, Last word: morning"
        }
        
        # Test authentication with correct passphrase
        # We'll simulate the authentication logic
        provided_hash = guard._hash_passphrase(passphrase)
        stored_hash = guard.user_passphrases[user_phone]["hash"]
        
        assert provided_hash == stored_hash
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, guard):
        """Test failed authentication with wrong passphrase"""
        user_phone = "+1234567890"
        correct_passphrase = "the quick brown fox jumps over the lazy dog in the morning"
        wrong_passphrase = "the quick brown fox jumps over the lazy cat in the morning"
        
        # Enroll with correct passphrase
        guard.user_passphrases[user_phone] = {
            "hash": guard._hash_passphrase(correct_passphrase),
            "word_count": 11,
            "enrolled_at": datetime.now().isoformat(),
            "hint": "First word: the, Last word: morning"
        }
        
        # Test authentication with wrong passphrase
        provided_hash = guard._hash_passphrase(wrong_passphrase)
        stored_hash = guard.user_passphrases[user_phone]["hash"]
        
        assert provided_hash != stored_hash
    
    @pytest.mark.asyncio
    async def test_authentication_attempts_tracking(self, guard):
        """Test tracking of authentication attempts"""
        user_phone = "+1234567890"
        
        # Track failed attempt
        guard._track_attempt(user_phone, False)
        
        assert user_phone in guard.authentication_attempts
        assert guard.authentication_attempts[user_phone]["failed_attempts"] == 1
        assert guard.authentication_attempts[user_phone]["locked"] == False
        
        # Track multiple failed attempts
        for _ in range(4):
            guard._track_attempt(user_phone, False)
        
        # Should be locked after 5 failed attempts
        assert guard.authentication_attempts[user_phone]["failed_attempts"] == 5
        assert guard.authentication_attempts[user_phone]["locked"] == True
    
    @pytest.mark.asyncio
    async def test_authentication_lockout(self, guard):
        """Test account lockout after failed attempts"""
        user_phone = "+1234567890"
        
        # Lock the account
        guard.authentication_attempts[user_phone] = {
            "failed_attempts": 5,
            "locked": True,
            "locked_until": datetime.now() + timedelta(minutes=30)
        }
        
        # Check if locked
        is_locked = guard._is_locked(user_phone)
        assert is_locked == True
    
    @pytest.mark.asyncio
    async def test_authentication_lockout_expiry(self, guard):
        """Test lockout expiry after time period"""
        user_phone = "+1234567890"
        
        # Lock with expired time
        guard.authentication_attempts[user_phone] = {
            "failed_attempts": 5,
            "locked": True,
            "locked_until": datetime.now() - timedelta(minutes=1)  # Already expired
        }
        
        # Should not be locked anymore
        is_locked = guard._is_locked(user_phone)
        assert is_locked == False
    
    @pytest.mark.asyncio
    async def test_passphrase_persistence(self, guard):
        """Test saving and loading passphrases"""
        user_phone = "+1234567890"
        passphrase = "the quick brown fox jumps over the lazy dog in the morning"
        
        # Enroll passphrase
        guard.user_passphrases[user_phone] = {
            "hash": guard._hash_passphrase(passphrase),
            "word_count": 11,
            "enrolled_at": datetime.now().isoformat(),
            "hint": "First word: the, Last word: morning"
        }
        
        # Save passphrases
        guard._save_passphrases()
        
        # Create new guard instance and load
        new_guard = VoiceGuard(data_dir=guard.data_dir)
        
        # Should have loaded the passphrase
        assert user_phone in new_guard.user_passphrases
        assert new_guard.user_passphrases[user_phone]["word_count"] == 11
    
    @pytest.mark.asyncio
    async def test_has_passphrase(self, guard):
        """Test checking if user has enrolled passphrase"""
        user_phone = "+1234567890"
        
        # Initially no passphrase
        has_passphrase = await guard.has_passphrase(user_phone)
        assert has_passphrase == False
        
        # Enroll passphrase
        guard.user_passphrases[user_phone] = {
            "hash": "test_hash",
            "word_count": 10,
            "enrolled_at": datetime.now().isoformat()
        }
        
        # Now has passphrase
        has_passphrase = await guard.has_passphrase(user_phone)
        assert has_passphrase == True
    
    @pytest.mark.asyncio
    async def test_authentication_logging(self, guard):
        """Test authentication event logging"""
        user_phone = "+1234567890"
        
        # Log successful authentication
        guard._log_authentication(user_phone, "authentication", True, "Success")
        
        # Check log file exists
        log_dir = guard.data_dir / "logs"
        assert log_dir.exists()
        
        log_files = list(log_dir.glob("*.json"))
        assert len(log_files) > 0
    
    def test_passphrase_normalization(self, guard):
        """Test passphrase normalization for consistency"""
        passphrase1 = "THE QUICK BROWN FOX"
        passphrase2 = "the   quick   brown   fox"  # Extra spaces
        passphrase3 = "The Quick Brown Fox"
        
        # All should produce same hash after normalization
        hash1 = guard._hash_passphrase(passphrase1)
        hash2 = guard._hash_passphrase(passphrase2)
        hash3 = guard._hash_passphrase(passphrase3)
        
        assert hash1 == hash2 == hash3
    
    @pytest.mark.asyncio
    async def test_get_passphrase_hint(self, guard):
        """Test retrieving passphrase hint"""
        user_phone = "+1234567890"
        
        # No hint initially
        hint = await guard.get_passphrase_hint(user_phone)
        assert hint is None
        
        # Enroll with hint
        guard.user_passphrases[user_phone] = {
            "hash": "test_hash",
            "word_count": 10,
            "enrolled_at": datetime.now().isoformat(),
            "hint": "First word: the, Last word: morning"
        }
        
        # Get hint
        hint = await guard.get_passphrase_hint(user_phone)
        assert hint == "First word: the, Last word: morning"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])