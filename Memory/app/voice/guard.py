#!/usr/bin/env python3
"""
Voice Guard - Voice Authentication Module
Authenticates users with voice passphrase (10+ words)
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import base64

from app.voice.azure_voice_service import AzureVoiceService

logger = logging.getLogger(__name__)

class VoiceGuard:
    """Voice authentication system with passphrase verification"""
    
    MINIMUM_PASSPHRASE_WORDS = 10
    
    def __init__(self, data_dir: str = "memory-system/voice_auth"):
        """Initialize voice authentication guard"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.voice_service = AzureVoiceService()
        self.user_passphrases = {}
        self.authentication_attempts = {}
        
        # Load existing passphrases
        self._load_passphrases()
        
        logger.info("🔐 Voice Guard initialized")
    
    def _load_passphrases(self):
        """Load stored user passphrases"""
        passphrase_file = self.data_dir / "passphrases.json"
        if passphrase_file.exists():
            with open(passphrase_file, 'r') as f:
                data = json.load(f)
                self.user_passphrases = data.get("passphrases", {})
                logger.info(f"Loaded {len(self.user_passphrases)} user passphrases")
    
    def _save_passphrases(self):
        """Save user passphrases to disk"""
        passphrase_file = self.data_dir / "passphrases.json"
        data = {
            "passphrases": self.user_passphrases,
            "updated_at": datetime.now().isoformat()
        }
        with open(passphrase_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _hash_passphrase(self, passphrase: str) -> str:
        """Create secure hash of passphrase"""
        # Normalize passphrase (lowercase, single spaces)
        normalized = ' '.join(passphrase.lower().split())
        
        # Create salted hash
        salt = os.getenv("VOICE_AUTH_SALT", "memory-app-voice-salt-2024")
        salted = f"{salt}:{normalized}"
        
        # Return SHA-256 hash
        return hashlib.sha256(salted.encode()).hexdigest()
    
    async def enroll_passphrase(self, user_phone: str, audio_data: bytes) -> Dict[str, Any]:
        """
        Enroll a new voice passphrase for a user
        
        Args:
            user_phone: User's phone number
            audio_data: Audio recording of passphrase
        
        Returns:
            Enrollment result
        """
        try:
            # Transcribe the audio
            transcription = await self.voice_service.transcribe(audio_data)
            
            if not transcription:
                return {
                    "success": False,
                    "message": "Could not transcribe audio. Please speak clearly."
                }
            
            # Count words in passphrase
            words = transcription.strip().split()
            word_count = len(words)
            
            if word_count < self.MINIMUM_PASSPHRASE_WORDS:
                return {
                    "success": False,
                    "message": f"Passphrase must be at least {self.MINIMUM_PASSPHRASE_WORDS} words. You said {word_count} words.",
                    "transcription": transcription
                }
            
            # Hash and store passphrase
            passphrase_hash = self._hash_passphrase(transcription)
            
            self.user_passphrases[user_phone] = {
                "hash": passphrase_hash,
                "word_count": word_count,
                "enrolled_at": datetime.now().isoformat(),
                "hint": f"First word: {words[0]}, Last word: {words[-1]}"
            }
            
            # Save to disk
            self._save_passphrases()
            
            # Log enrollment
            self._log_authentication(user_phone, "enrollment", True, "Passphrase enrolled")
            
            logger.info(f"✅ Passphrase enrolled for {user_phone} ({word_count} words)")
            
            return {
                "success": True,
                "message": f"Passphrase enrolled successfully with {word_count} words.",
                "hint": f"Remember: starts with '{words[0]}' and ends with '{words[-1]}'",
                "transcription": transcription
            }
            
        except Exception as e:
            logger.error(f"Enrollment error: {e}")
            return {
                "success": False,
                "message": f"Enrollment failed: {str(e)}"
            }
    
    async def authenticate(self, user_phone: str, audio_data: bytes) -> Dict[str, Any]:
        """
        Authenticate user with voice passphrase
        
        Args:
            user_phone: User's phone number
            audio_data: Audio recording of passphrase attempt
        
        Returns:
            Authentication result with session validity
        """
        try:
            # Check if user has enrolled passphrase
            if user_phone not in self.user_passphrases:
                return {
                    "authenticated": False,
                    "message": "No passphrase enrolled. Please enroll first.",
                    "needs_enrollment": True
                }
            
            # Check for rate limiting (max 5 attempts per hour)
            if not self._check_rate_limit(user_phone):
                return {
                    "authenticated": False,
                    "message": "Too many attempts. Please try again later.",
                    "rate_limited": True
                }
            
            # Transcribe the audio
            transcription = await self.voice_service.transcribe(audio_data)
            
            if not transcription:
                self._log_authentication(user_phone, "authentication", False, "Transcription failed")
                return {
                    "authenticated": False,
                    "message": "Could not understand audio. Please speak clearly."
                }
            
            # Verify passphrase
            provided_hash = self._hash_passphrase(transcription)
            stored_data = self.user_passphrases[user_phone]
            expected_hash = stored_data["hash"]
            
            if provided_hash == expected_hash:
                # Authentication successful
                session_expiry = datetime.now() + timedelta(minutes=10)
                
                self._log_authentication(user_phone, "authentication", True, "Correct passphrase")
                
                logger.info(f"✅ Authentication successful for {user_phone}")
                
                return {
                    "authenticated": True,
                    "message": "Authentication successful",
                    "session_expiry": session_expiry.isoformat(),
                    "session_duration_minutes": 10
                }
            else:
                # Authentication failed
                self._log_authentication(user_phone, "authentication", False, "Incorrect passphrase")
                
                # Provide hint after 3 failed attempts
                attempts = self._get_recent_attempts(user_phone)
                hint = ""
                if attempts >= 3:
                    hint = f" Hint: {stored_data.get('hint', 'No hint available')}"
                
                logger.warning(f"❌ Authentication failed for {user_phone}")
                
                return {
                    "authenticated": False,
                    "message": f"Incorrect passphrase.{hint}",
                    "attempts_remaining": 5 - attempts
                }
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {
                "authenticated": False,
                "message": f"Authentication failed: {str(e)}"
            }
    
    async def verify_voice_match(self, user_phone: str, audio_data: bytes) -> Tuple[bool, float]:
        """
        Verify if voice matches enrolled voice profile (future enhancement)
        Currently returns basic verification based on passphrase
        
        Args:
            user_phone: User's phone number
            audio_data: Audio to verify
        
        Returns:
            Tuple of (matches, confidence_score)
        """
        # For Phase 1, we only verify passphrase, not voice biometrics
        # This is a placeholder for future voice biometric verification
        
        result = await self.authenticate(user_phone, audio_data)
        
        if result.get("authenticated"):
            return (True, 1.0)
        else:
            return (False, 0.0)
    
    def _check_rate_limit(self, user_phone: str) -> bool:
        """Check if user has exceeded rate limit"""
        attempts = self._get_recent_attempts(user_phone)
        return attempts < 5
    
    def _get_recent_attempts(self, user_phone: str) -> int:
        """Get number of recent authentication attempts"""
        log_file = self.data_dir / f"auth_log_{user_phone.replace('+', '')}.json"
        
        if not log_file.exists():
            return 0
        
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        # Count attempts in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_attempts = 0
        
        for log in logs.get("attempts", []):
            timestamp = datetime.fromisoformat(log["timestamp"])
            if timestamp > one_hour_ago and log["action"] == "authentication" and not log["success"]:
                recent_attempts += 1
        
        return recent_attempts
    
    def _log_authentication(self, user_phone: str, action: str, success: bool, details: str):
        """Log authentication attempt"""
        log_file = self.data_dir / f"auth_log_{user_phone.replace('+', '')}.json"
        
        # Load existing logs
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = {"attempts": []}
        
        # Add new log entry
        logs["attempts"].append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "success": success,
            "details": details
        })
        
        # Keep only last 100 attempts
        logs["attempts"] = logs["attempts"][-100:]
        
        # Save logs
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def reset_passphrase(self, user_phone: str) -> bool:
        """Reset user's passphrase (requires admin action)"""
        if user_phone in self.user_passphrases:
            del self.user_passphrases[user_phone]
            self._save_passphrases()
            
            self._log_authentication(user_phone, "reset", True, "Passphrase reset by admin")
            logger.info(f"Passphrase reset for {user_phone}")
            return True
        
        return False
    
    def get_user_status(self, user_phone: str) -> Dict[str, Any]:
        """Get user's authentication status"""
        if user_phone not in self.user_passphrases:
            return {
                "enrolled": False,
                "message": "No passphrase enrolled"
            }
        
        data = self.user_passphrases[user_phone]
        recent_attempts = self._get_recent_attempts(user_phone)
        
        return {
            "enrolled": True,
            "enrolled_at": data["enrolled_at"],
            "word_count": data["word_count"],
            "hint": data.get("hint", ""),
            "recent_attempts": recent_attempts,
            "rate_limited": recent_attempts >= 5
        }