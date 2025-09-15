#!/usr/bin/env python3
"""
Voice Authentication Service for Memory App
Advanced biometric voice authentication with multi-factor support
"""

import os
import json
import hashlib
import secrets
import logging
import base64
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import tempfile
from pathlib import Path
import uuid
import wave
import struct

# Import encryption for voiceprint protection
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticationLevel(Enum):
    """Voice authentication confidence levels"""
    HIGH = "high"           # 0.85+ similarity - full access
    MEDIUM = "medium"       # 0.70-0.85 - requires challenge
    LOW = "low"            # 0.55-0.70 - restricted access
    FAILED = "failed"      # <0.55 - denied

class VoiceSessionStatus(Enum):
    """Voice authentication session states"""
    PENDING_ENROLLMENT = "pending_enrollment"
    ENROLLING = "enrolling"
    ENROLLED = "enrolled"
    VERIFYING = "verifying"
    AUTHENTICATED = "authenticated"
    CHALLENGE_REQUIRED = "challenge_required"
    FAILED = "failed"
    EXPIRED = "expired"

class MemoryAccessLevel(Enum):
    """Memory access levels based on authentication"""
    FULL = "full"              # All memories including super secret
    RESTRICTED = "restricted"   # Only non-sensitive memories
    FAMILY = "family"          # Family-shared memories only
    EMERGENCY = "emergency"    # Emergency access with audit
    DENIED = "denied"          # No access

@dataclass
class VoiceProfile:
    """Enhanced voice profile with multiple samples"""
    profile_id: str
    user_id: str
    display_name: str
    embeddings: List[bytes]  # Multiple encrypted embeddings
    model_version: str = "advanced_v2.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    device_hints: List[str] = field(default_factory=list)
    enrollment_samples: int = 0
    confidence_threshold: float = 0.85
    is_primary: bool = True
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AuthenticationAttempt:
    """Record of authentication attempt"""
    attempt_id: str
    user_id: str
    profile_id: Optional[str]
    timestamp: datetime
    confidence_score: float
    authentication_level: AuthenticationLevel
    success: bool
    failure_reason: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    session_id: Optional[str] = None
    challenge_required: bool = False
    challenge_passed: bool = False

@dataclass
class VoiceSession:
    """Voice authentication session with security features"""
    session_id: str
    user_id: str
    profile_id: str
    status: VoiceSessionStatus
    authentication_level: AuthenticationLevel
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=30))
    last_activity: datetime = field(default_factory=datetime.now)
    attempts_count: int = 0
    max_attempts: int = 3
    challenge_token: Optional[str] = None
    challenge_answer: Optional[str] = None
    access_level: MemoryAccessLevel = MemoryAccessLevel.DENIED
    authorized_categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EnrollmentSession:
    """Voice enrollment session tracking"""
    enrollment_id: str
    user_id: str
    display_name: str
    status: str = "initializing"
    samples_collected: int = 0
    required_samples: int = 3
    temporary_embeddings: List[bytes] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=10))
    metadata: Dict[str, Any] = field(default_factory=dict)

class VoiceAuthenticationService:
    """Advanced voice authentication service with enhanced security"""
    
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.voice_profiles: Dict[str, List[VoiceProfile]] = {}  # user_id -> profiles
        self.auth_sessions: Dict[str, VoiceSession] = {}  # session_id -> session
        self.enrollment_sessions: Dict[str, EnrollmentSession] = {}  # enrollment_id -> session
        self.auth_attempts: List[AuthenticationAttempt] = []
        
        # Security thresholds
        self.threshold_high = 0.85
        self.threshold_medium = 0.70
        self.threshold_low = 0.55
        
        # Rate limiting
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_attempts = 3
        self.user_attempt_times: Dict[str, List[datetime]] = {}
        
        # Challenge questions for medium confidence
        self.challenge_questions = [
            {"question": "What year were you born?", "type": "year"},
            {"question": "What's your mother's maiden name?", "type": "text"},
            {"question": "What city were you born in?", "type": "text"},
            {"question": "What's your favorite color?", "type": "text"},
            {"question": "What's your pet's name?", "type": "text"}
        ]
        
        # Initialize encryption
        self.master_key = self._generate_master_key()
        self.fernet = Fernet(self.master_key)
        
        # Create directories
        self.data_dir = Path("memory-system/voice_auth_data")
        self.samples_dir = self.data_dir / "samples"
        self.profiles_dir = self.data_dir / "profiles"
        self.logs_dir = self.data_dir / "logs"
        
        for directory in [self.data_dir, self.samples_dir, self.profiles_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize demo data if in demo mode
        if demo_mode:
            self._initialize_demo_data()
        
        logger.info(f"🎙️ Voice Authentication Service initialized ({'DEMO' if demo_mode else 'PRODUCTION'} mode)")
    
    def _generate_master_key(self) -> bytes:
        """Generate or load master encryption key"""
        key_file = Path("memory-system/voice_auth_key.key")
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _initialize_demo_data(self):
        """Create demo voice profiles for testing"""
        demo_users = [
            {"user_id": "demo_user_1", "name": "Alice Johnson"},
            {"user_id": "demo_user_2", "name": "Bob Smith"},
            {"user_id": "test_user_123", "name": "Test User"}
        ]
        
        for user_data in demo_users:
            # Create demo embeddings (simulated)
            embeddings = []
            for i in range(3):
                embedding = self._generate_demo_embedding(f"{user_data['user_id']}_sample_{i}")
                encrypted_embedding = self.fernet.encrypt(embedding)
                embeddings.append(encrypted_embedding)
            
            profile = VoiceProfile(
                profile_id=f"profile_{uuid.uuid4().hex[:8]}",
                user_id=user_data['user_id'],
                display_name=user_data['name'],
                embeddings=embeddings,
                enrollment_samples=3,
                device_hints=["iPhone", "MacBook Pro"],
                metadata={"demo": True}
            )
            
            if user_data['user_id'] not in self.voice_profiles:
                self.voice_profiles[user_data['user_id']] = []
            self.voice_profiles[user_data['user_id']].append(profile)
            
            logger.info(f"📱 Created demo voice profile for {user_data['name']}")
    
    def _generate_demo_embedding(self, seed: str) -> bytes:
        """Generate deterministic demo embedding for testing"""
        # Create a 512-dimensional embedding (typical for speaker recognition)
        hash_obj = hashlib.sha256(seed.encode())
        base_hash = hash_obj.digest()
        
        # Expand to 512 dimensions
        embedding = []
        for i in range(16):  # 16 * 32 = 512 bytes
            expanded = hashlib.sha256(base_hash + str(i).encode()).digest()
            embedding.extend(expanded)
        
        return bytes(embedding[:512])
    
    def _extract_voice_embedding(self, audio_data: bytes) -> np.ndarray:
        """Extract voice embedding from audio data"""
        if self.demo_mode:
            # Demo mode: Create deterministic embedding from audio data
            hash_obj = hashlib.sha256(audio_data)
            embedding = np.frombuffer(hash_obj.digest(), dtype=np.uint8).astype(np.float32)
            # Expand to 512 dimensions
            embedding = np.tile(embedding, 16)[:512]
            return embedding / 255.0  # Normalize
        else:
            # Production: Would use real speaker recognition model
            # e.g., ECAPA-TDNN, x-vector, or resemblyzer
            raise NotImplementedError("Production voice embedding extraction not implemented")
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        dot_product = np.dot(embedding1, embedding2)
        norms = np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        return float(dot_product / norms) if norms > 0 else 0.0
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        now = datetime.now()
        
        if user_id not in self.user_attempt_times:
            self.user_attempt_times[user_id] = []
        
        # Remove old attempts outside window
        cutoff_time = now - timedelta(seconds=self.rate_limit_window)
        self.user_attempt_times[user_id] = [
            t for t in self.user_attempt_times[user_id] if t > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(self.user_attempt_times[user_id]) >= self.rate_limit_max_attempts:
            logger.warning(f"⚠️ Rate limit exceeded for user {user_id}")
            return False
        
        # Record this attempt
        self.user_attempt_times[user_id].append(now)
        return True
    
    async def start_enrollment(
        self,
        user_id: str,
        display_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initialize voice enrollment session"""
        enrollment_id = f"enroll_{uuid.uuid4().hex[:12]}"
        
        session = EnrollmentSession(
            enrollment_id=enrollment_id,
            user_id=user_id,
            display_name=display_name,
            metadata=metadata or {}
        )
        
        self.enrollment_sessions[enrollment_id] = session
        
        logger.info(f"🎙️ Started voice enrollment for {display_name} (session: {enrollment_id})")
        
        return {
            'success': True,
            'enrollment_id': enrollment_id,
            'status': 'initialized',
            'required_samples': session.required_samples,
            'instructions': 'Please provide 3 voice samples. Each sample should be 3-5 seconds of natural speech.',
            'expires_at': session.expires_at.isoformat()
        }
    
    async def add_enrollment_sample(
        self,
        enrollment_id: str,
        audio_data: bytes,
        device_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add voice sample to enrollment session"""
        if enrollment_id not in self.enrollment_sessions:
            return {
                'success': False,
                'error': 'Invalid or expired enrollment session'
            }
        
        session = self.enrollment_sessions[enrollment_id]
        
        # Check if session expired
        if datetime.now() > session.expires_at:
            session.status = "expired"
            return {
                'success': False,
                'error': 'Enrollment session expired'
            }
        
        # Extract embedding from audio
        embedding = self._extract_voice_embedding(audio_data)
        encrypted_embedding = self.fernet.encrypt(embedding.tobytes())
        
        session.temporary_embeddings.append(encrypted_embedding)
        session.samples_collected += 1
        
        # Save audio sample for future reference (demo mode only)
        if self.demo_mode:
            sample_path = self.samples_dir / f"{enrollment_id}_sample_{session.samples_collected}.wav"
            with open(sample_path, 'wb') as f:
                f.write(audio_data)
        
        # Check if enrollment complete
        if session.samples_collected >= session.required_samples:
            session.status = "complete"
            
            # Create voice profile
            profile_id = f"profile_{uuid.uuid4().hex[:8]}"
            profile = VoiceProfile(
                profile_id=profile_id,
                user_id=session.user_id,
                display_name=session.display_name,
                embeddings=session.temporary_embeddings,
                enrollment_samples=session.samples_collected,
                device_hints=[device_hint] if device_hint else [],
                metadata=session.metadata
            )
            
            # Store profile
            if session.user_id not in self.voice_profiles:
                self.voice_profiles[session.user_id] = []
            self.voice_profiles[session.user_id].append(profile)
            
            # Save profile to disk
            self._save_profile(profile)
            
            logger.info(f"✅ Voice enrollment completed for {session.display_name}")
            
            return {
                'success': True,
                'status': 'enrolled',
                'profile_id': profile_id,
                'message': f'Voice profile created successfully',
                'samples_collected': session.samples_collected
            }
        else:
            session.status = "collecting"
            remaining = session.required_samples - session.samples_collected
            
            return {
                'success': True,
                'status': 'collecting',
                'samples_collected': session.samples_collected,
                'samples_remaining': remaining,
                'message': f'Sample {session.samples_collected} recorded. Please provide {remaining} more sample(s).'
            }
    
    async def verify_voice(
        self,
        user_id: str,
        audio_data: bytes,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify voice against stored profiles"""
        # Check rate limiting
        if not self._check_rate_limit(user_id):
            return {
                'success': False,
                'error': 'Too many attempts. Please try again later.',
                'retry_after': self.rate_limit_window
            }
        
        # Check if user has profiles
        if user_id not in self.voice_profiles or not self.voice_profiles[user_id]:
            return {
                'success': False,
                'error': 'No voice profile found. Please enroll first.'
            }
        
        # Extract embedding from provided audio
        current_embedding = self._extract_voice_embedding(audio_data)
        
        # Compare with all stored profiles
        max_similarity = 0.0
        best_profile = None
        
        for profile in self.voice_profiles[user_id]:
            if not profile.is_active:
                continue
            
            for encrypted_embedding in profile.embeddings:
                stored_embedding_bytes = self.fernet.decrypt(encrypted_embedding)
                stored_embedding = np.frombuffer(stored_embedding_bytes, dtype=np.float32)
                
                similarity = self._calculate_similarity(current_embedding, stored_embedding)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_profile = profile
        
        # Determine authentication level
        if max_similarity >= self.threshold_high:
            auth_level = AuthenticationLevel.HIGH
            success = True
            access_level = MemoryAccessLevel.FULL
        elif max_similarity >= self.threshold_medium:
            auth_level = AuthenticationLevel.MEDIUM
            success = False  # Requires challenge
            access_level = MemoryAccessLevel.RESTRICTED
        elif max_similarity >= self.threshold_low:
            auth_level = AuthenticationLevel.LOW
            success = False
            access_level = MemoryAccessLevel.FAMILY
        else:
            auth_level = AuthenticationLevel.FAILED
            success = False
            access_level = MemoryAccessLevel.DENIED
        
        # Create session if successful or challenge required
        session_id = None
        if auth_level in [AuthenticationLevel.HIGH, AuthenticationLevel.MEDIUM]:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
            session = VoiceSession(
                session_id=session_id,
                user_id=user_id,
                profile_id=best_profile.profile_id if best_profile else "",
                status=VoiceSessionStatus.AUTHENTICATED if success else VoiceSessionStatus.CHALLENGE_REQUIRED,
                authentication_level=auth_level,
                access_level=access_level
            )
            
            if auth_level == AuthenticationLevel.MEDIUM:
                # Generate challenge
                challenge = secrets.choice(self.challenge_questions)
                session.challenge_token = secrets.token_urlsafe(16)
                session.metadata['challenge'] = challenge
            
            self.auth_sessions[session_id] = session
        
        # Log attempt
        attempt = AuthenticationAttempt(
            attempt_id=f"attempt_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            profile_id=best_profile.profile_id if best_profile else None,
            timestamp=datetime.now(),
            confidence_score=max_similarity,
            authentication_level=auth_level,
            success=success,
            failure_reason=None if success else f"Low confidence: {max_similarity:.3f}",
            ip_address=ip_address,
            device_info=device_info,
            session_id=session_id,
            challenge_required=(auth_level == AuthenticationLevel.MEDIUM)
        )
        self.auth_attempts.append(attempt)
        self._log_attempt(attempt)
        
        # Prepare response
        response = {
            'success': success,
            'session_id': session_id,
            'confidence_score': max_similarity,
            'authentication_level': auth_level.value,
            'access_level': access_level.value
        }
        
        if auth_level == AuthenticationLevel.HIGH:
            response['message'] = 'Voice authenticated successfully'
            response['authorized_categories'] = ['all']
        elif auth_level == AuthenticationLevel.MEDIUM:
            response['challenge_required'] = True
            response['challenge_token'] = session.challenge_token
            response['message'] = 'Additional verification required'
        elif auth_level == AuthenticationLevel.LOW:
            response['message'] = 'Voice partially recognized. Limited access granted.'
            response['authorized_categories'] = ['family', 'general']
        else:
            response['error'] = 'Voice not recognized'
        
        logger.info(f"🔐 Voice verification for {user_id}: {auth_level.value} (confidence: {max_similarity:.3f})")
        
        return response
    
    async def get_challenge_question(self, session_id: str) -> Dict[str, Any]:
        """Get challenge question for medium confidence authentication"""
        if session_id not in self.auth_sessions:
            return {
                'success': False,
                'error': 'Invalid session'
            }
        
        session = self.auth_sessions[session_id]
        
        if session.status != VoiceSessionStatus.CHALLENGE_REQUIRED:
            return {
                'success': False,
                'error': 'No challenge required for this session'
            }
        
        challenge = session.metadata.get('challenge', {})
        
        return {
            'success': True,
            'challenge_token': session.challenge_token,
            'question': challenge.get('question', 'What year were you born?'),
            'question_type': challenge.get('type', 'text'),
            'attempts_remaining': session.max_attempts - session.attempts_count
        }
    
    async def answer_challenge(
        self,
        session_id: str,
        challenge_token: str,
        answer: str
    ) -> Dict[str, Any]:
        """Verify challenge answer"""
        if session_id not in self.auth_sessions:
            return {
                'success': False,
                'error': 'Invalid session'
            }
        
        session = self.auth_sessions[session_id]
        
        if session.challenge_token != challenge_token:
            return {
                'success': False,
                'error': 'Invalid challenge token'
            }
        
        session.attempts_count += 1
        
        # In demo mode, accept any non-empty answer
        # In production, would verify against stored security answers
        if self.demo_mode:
            correct = len(answer.strip()) > 0
        else:
            # Production: Verify against stored answers
            correct = False  # Placeholder
        
        if correct:
            session.status = VoiceSessionStatus.AUTHENTICATED
            session.access_level = MemoryAccessLevel.FULL
            session.challenge_passed = True
            
            logger.info(f"✅ Challenge passed for session {session_id}")
            
            return {
                'success': True,
                'message': 'Challenge completed successfully',
                'access_level': session.access_level.value,
                'authorized_categories': ['all']
            }
        else:
            if session.attempts_count >= session.max_attempts:
                session.status = VoiceSessionStatus.FAILED
                logger.warning(f"❌ Challenge failed for session {session_id} - max attempts reached")
                
                return {
                    'success': False,
                    'error': 'Maximum attempts exceeded. Session terminated.',
                    'session_expired': True
                }
            else:
                remaining = session.max_attempts - session.attempts_count
                return {
                    'success': False,
                    'error': 'Incorrect answer',
                    'attempts_remaining': remaining
                }
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current authentication session status"""
        if session_id not in self.auth_sessions:
            return {
                'success': False,
                'error': 'Session not found'
            }
        
        session = self.auth_sessions[session_id]
        
        # Check if expired
        if datetime.now() > session.expires_at:
            session.status = VoiceSessionStatus.EXPIRED
            return {
                'success': False,
                'error': 'Session expired',
                'expired_at': session.expires_at.isoformat()
            }
        
        # Update last activity
        session.last_activity = datetime.now()
        
        return {
            'success': True,
            'session_id': session_id,
            'user_id': session.user_id,
            'status': session.status.value,
            'authentication_level': session.authentication_level.value,
            'access_level': session.access_level.value,
            'authorized_categories': session.authorized_categories,
            'created_at': session.created_at.isoformat(),
            'expires_at': session.expires_at.isoformat(),
            'challenge_required': session.status == VoiceSessionStatus.CHALLENGE_REQUIRED
        }
    
    async def list_voice_profiles(self, user_id: str) -> Dict[str, Any]:
        """List all voice profiles for a user"""
        if user_id not in self.voice_profiles:
            return {
                'success': True,
                'profiles': [],
                'message': 'No voice profiles found'
            }
        
        profiles = []
        for profile in self.voice_profiles[user_id]:
            profiles.append({
                'profile_id': profile.profile_id,
                'display_name': profile.display_name,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat(),
                'is_primary': profile.is_primary,
                'is_active': profile.is_active,
                'enrollment_samples': profile.enrollment_samples,
                'confidence_threshold': profile.confidence_threshold,
                'device_hints': profile.device_hints
            })
        
        return {
            'success': True,
            'profiles': profiles,
            'count': len(profiles)
        }
    
    async def delete_voice_profile(
        self,
        user_id: str,
        profile_id: str
    ) -> Dict[str, Any]:
        """Delete a voice profile"""
        if user_id not in self.voice_profiles:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        for i, profile in enumerate(self.voice_profiles[user_id]):
            if profile.profile_id == profile_id:
                deleted_profile = self.voice_profiles[user_id].pop(i)
                
                # Delete saved profile file
                profile_file = self.profiles_dir / f"{profile_id}.json"
                if profile_file.exists():
                    profile_file.unlink()
                
                logger.info(f"🗑️ Deleted voice profile {profile_id} for user {user_id}")
                
                return {
                    'success': True,
                    'message': f'Voice profile "{deleted_profile.display_name}" deleted successfully'
                }
        
        return {
            'success': False,
            'error': 'Profile not found'
        }
    
    async def get_authentication_logs(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get authentication attempt logs"""
        logs = self.auth_attempts
        
        if user_id:
            logs = [a for a in logs if a.user_id == user_id]
        
        # Sort by timestamp (most recent first)
        logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        formatted_logs = []
        for attempt in logs:
            formatted_logs.append({
                'attempt_id': attempt.attempt_id,
                'user_id': attempt.user_id,
                'timestamp': attempt.timestamp.isoformat(),
                'confidence_score': attempt.confidence_score,
                'authentication_level': attempt.authentication_level.value,
                'success': attempt.success,
                'failure_reason': attempt.failure_reason,
                'ip_address': attempt.ip_address,
                'device_info': attempt.device_info,
                'challenge_required': attempt.challenge_required,
                'challenge_passed': attempt.challenge_passed
            })
        
        return {
            'success': True,
            'logs': formatted_logs,
            'count': len(formatted_logs)
        }
    
    def _save_profile(self, profile: VoiceProfile):
        """Save voice profile to disk"""
        profile_data = {
            'profile_id': profile.profile_id,
            'user_id': profile.user_id,
            'display_name': profile.display_name,
            'model_version': profile.model_version,
            'created_at': profile.created_at.isoformat(),
            'updated_at': profile.updated_at.isoformat(),
            'device_hints': profile.device_hints,
            'enrollment_samples': profile.enrollment_samples,
            'confidence_threshold': profile.confidence_threshold,
            'is_primary': profile.is_primary,
            'is_active': profile.is_active,
            'metadata': profile.metadata,
            # Don't save embeddings in JSON (they're encrypted bytes)
            'embeddings_count': len(profile.embeddings)
        }
        
        profile_file = self.profiles_dir / f"{profile.profile_id}.json"
        with open(profile_file, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        # Save embeddings separately
        embeddings_file = self.profiles_dir / f"{profile.profile_id}.embeddings"
        with open(embeddings_file, 'wb') as f:
            for embedding in profile.embeddings:
                f.write(len(embedding).to_bytes(4, 'big'))
                f.write(embedding)
    
    def _log_attempt(self, attempt: AuthenticationAttempt):
        """Log authentication attempt to file"""
        log_file = self.logs_dir / f"auth_log_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        log_entry = {
            'attempt_id': attempt.attempt_id,
            'user_id': attempt.user_id,
            'profile_id': attempt.profile_id,
            'timestamp': attempt.timestamp.isoformat(),
            'confidence_score': attempt.confidence_score,
            'authentication_level': attempt.authentication_level.value,
            'success': attempt.success,
            'failure_reason': attempt.failure_reason,
            'ip_address': attempt.ip_address,
            'device_info': attempt.device_info,
            'session_id': attempt.session_id
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    async def validate_memory_access(
        self,
        session_id: str,
        memory_category: str
    ) -> Dict[str, Any]:
        """Validate if session has access to specific memory category"""
        if session_id not in self.auth_sessions:
            return {
                'success': False,
                'error': 'Invalid session',
                'access_granted': False
            }
        
        session = self.auth_sessions[session_id]
        
        # Check if session is authenticated
        if session.status != VoiceSessionStatus.AUTHENTICATED:
            return {
                'success': False,
                'error': 'Session not authenticated',
                'access_granted': False
            }
        
        # Check expiration
        if datetime.now() > session.expires_at:
            session.status = VoiceSessionStatus.EXPIRED
            return {
                'success': False,
                'error': 'Session expired',
                'access_granted': False
            }
        
        # Check access level
        access_granted = False
        reason = ""
        
        if session.access_level == MemoryAccessLevel.FULL:
            access_granted = True
            reason = "Full access granted"
        elif session.access_level == MemoryAccessLevel.RESTRICTED:
            # Restricted access - only non-sensitive categories
            if memory_category not in ['super_secret', 'confidential', 'finance']:
                access_granted = True
                reason = "Restricted access - non-sensitive category"
            else:
                reason = "Access denied - sensitive category requires full authentication"
        elif session.access_level == MemoryAccessLevel.FAMILY:
            # Family access only
            if memory_category == 'family':
                access_granted = True
                reason = "Family access granted"
            else:
                reason = "Access denied - only family memories allowed"
        elif session.access_level == MemoryAccessLevel.EMERGENCY:
            # Emergency access with audit
            access_granted = True
            reason = "Emergency access granted (audited)"
            # Log emergency access
            logger.warning(f"⚠️ EMERGENCY ACCESS: User {session.user_id} accessed {memory_category}")
        else:
            reason = "Access denied"
        
        # Update session activity
        session.last_activity = datetime.now()
        
        return {
            'success': True,
            'access_granted': access_granted,
            'reason': reason,
            'access_level': session.access_level.value,
            'session_expires_at': session.expires_at.isoformat()
        }
    
    def generate_demo_audio_sample(self, text: str = "Hello, this is my voice sample") -> bytes:
        """Generate a demo audio sample for testing (WAV format)"""
        # Create a simple WAV file with dummy data
        sample_rate = 16000
        duration = 3  # seconds
        num_samples = sample_rate * duration
        
        # Generate a sine wave as dummy audio
        frequency = 440  # A4 note
        t = np.linspace(0, duration, num_samples)
        audio_data = np.sin(2 * np.pi * frequency * t)
        
        # Add some noise to make it unique
        noise = np.random.normal(0, 0.1, num_samples)
        audio_data = audio_data + noise
        
        # Normalize and convert to 16-bit PCM
        audio_data = np.int16(audio_data * 32767 / np.max(np.abs(audio_data)))
        
        # Create WAV file in memory
        wav_buffer = tempfile.SpooledTemporaryFile()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        wav_buffer.seek(0)
        wav_data = wav_buffer.read()
        wav_buffer.close()
        
        return wav_data

# Initialize global service instance
voice_auth_service = VoiceAuthenticationService(demo_mode=True)

# Export service
__all__ = ['voice_auth_service', 'VoiceAuthenticationService', 'AuthenticationLevel', 
           'VoiceSessionStatus', 'MemoryAccessLevel']