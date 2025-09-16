"""
Fish Audio Service - Mid-tier Voice Cloning Fallback Service
===========================================================
Provides mid-tier voice cloning using Fish Audio API.
Available as fallback service for when other services are unavailable.
"""

import os
import asyncio
import aiohttp
import aiofiles
import tempfile
import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
import hashlib
import json
from dataclasses import dataclass, asdict
from enum import Enum
import base64
from pathlib import Path
import urllib.parse

logger = logging.getLogger(__name__)


class FishAudioError(Exception):
    """Base exception for Fish Audio service errors"""
    pass


class VoiceCreationError(FishAudioError):
    """Error creating voice avatar"""
    pass


class SpeechSynthesisError(FishAudioError):
    """Error during speech synthesis"""
    pass


class QuotaExceededError(FishAudioError):
    """API quota exceeded"""
    pass


class AuthenticationError(FishAudioError):
    """API authentication failed"""
    pass


class ServiceUnavailableError(FishAudioError):
    """Service temporarily unavailable"""
    pass


class AudioFormat(str, Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"


class VoiceQuality(str, Enum):
    """Voice quality settings"""
    FAST = "fast"
    STANDARD = "standard"
    HIGH = "high"


@dataclass
class VoiceProfile:
    """Fish Audio voice profile"""
    voice_id: str
    user_id: str
    voice_name: str
    fish_model_id: str
    created_at: datetime
    sample_count: int
    quality: VoiceQuality
    language: str = "en"
    character_limit: int = 50000
    characters_used: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SynthesisResult:
    """Speech synthesis result"""
    audio_data: bytes
    format: AudioFormat
    duration: float
    voice_id: str
    text: str
    characters_used: int
    generation_time: float
    quality: VoiceQuality
    task_id: Optional[str] = None


@dataclass
class TrainingStatus:
    """Voice training status"""
    model_id: str
    status: str  # training, completed, failed
    progress: float
    started_at: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None


class FishAudioService:
    """
    Fish Audio service for mid-tier voice cloning
    Fallback service with decent quality and reasonable pricing
    """

    # API Configuration
    BASE_URL = "https://api.fish.audio/v1"
    MODELS_URL = f"{BASE_URL}/models"
    SYNTHESIS_URL = f"{BASE_URL}/tts"
    TRAINING_URL = f"{BASE_URL}/models/train"

    # Service limits
    MIN_SAMPLE_DURATION = 5  # 5 seconds minimum
    MAX_SAMPLE_DURATION = 300  # 5 minutes maximum
    MAX_SAMPLES_PER_VOICE = 20
    MIN_SAMPLES_PER_VOICE = 3
    MAX_SAMPLE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self):
        # Configuration from environment
        self.api_key = os.getenv("FISH_AUDIO_API_KEY")
        self.enabled = self.api_key is not None
        self.voices_path = os.getenv("FISH_VOICES_PATH", "./data/voices/fish")
        self.default_quality = VoiceQuality(os.getenv("FISH_DEFAULT_QUALITY", "standard"))

        # Fallback configuration
        self.use_as_fallback = os.getenv("FISH_ENABLE_FALLBACK", "true").lower() == "true"
        self.fallback_priority = int(os.getenv("FISH_FALLBACK_PRIORITY", "2"))

        # Rate limiting
        self.max_requests_per_minute = int(os.getenv("FISH_RATE_LIMIT", "30"))
        self.request_timestamps: List[datetime] = []

        # Session management
        self.session: Optional[aiohttp.ClientSession] = None

        # Voice profiles storage
        self.profiles: Dict[str, VoiceProfile] = {}
        self.training_status: Dict[str, TrainingStatus] = {}

        # Ensure directories exist
        Path(self.voices_path).mkdir(parents=True, exist_ok=True)

        # Load existing profiles
        self._load_profiles()

        logger.info(f"FishAudioService initialized - Enabled: {self.enabled}, Fallback: {self.use_as_fallback}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize the service"""
        if not self.enabled and not self.use_as_fallback:
            raise ServiceUnavailableError("Fish Audio service is disabled")

        # Initialize HTTP session with headers
        headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        connector = aiohttp.TCPConnector(limit=15, limit_per_host=8)
        timeout = aiohttp.ClientTimeout(total=120)
        self.session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout
        )

        # Verify API key if provided
        if self.api_key:
            await self._verify_api_key()

        logger.info("FishAudioService initialized successfully")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("FishAudioService cleaned up")

    async def create_voice_avatar(
        self,
        user_id: str,
        voice_name: str,
        audio_samples: List[bytes],
        transcriptions: Optional[List[str]] = None,
        language: str = "en",
        quality: VoiceQuality = None
    ) -> VoiceProfile:
        """
        Create a voice avatar using Fish Audio cloning

        Args:
            user_id: User identifier
            voice_name: Name for the voice avatar
            audio_samples: List of audio sample data
            transcriptions: Optional list of transcriptions for samples
            language: Language code (en, zh, ja, etc.)
            quality: Training quality level

        Returns:
            VoiceProfile: Created voice profile
        """
        if not self.enabled:
            raise ServiceUnavailableError("Fish Audio service not available")

        if len(audio_samples) < self.MIN_SAMPLES_PER_VOICE:
            raise VoiceCreationError(f"Minimum {self.MIN_SAMPLES_PER_VOICE} audio samples required")

        if len(audio_samples) > self.MAX_SAMPLES_PER_VOICE:
            raise VoiceCreationError(f"Maximum {self.MAX_SAMPLES_PER_VOICE} audio samples allowed")

        # Validate sample sizes and durations
        for i, sample in enumerate(audio_samples):
            if len(sample) > self.MAX_SAMPLE_SIZE:
                raise VoiceCreationError(f"Sample {i} too large: {len(sample)} bytes")

        try:
            await self._rate_limit_check()

            # Generate voice ID
            voice_id = self._generate_voice_id(user_id, voice_name)
            training_quality = quality or self.default_quality

            # Prepare training data
            training_data = await self._prepare_training_data(
                audio_samples, transcriptions, language
            )

            # Start voice training
            fish_model_id = await self._start_voice_training(
                voice_name, training_data, training_quality, language
            )

            # Create voice profile
            profile = VoiceProfile(
                voice_id=voice_id,
                user_id=user_id,
                voice_name=voice_name,
                fish_model_id=fish_model_id,
                created_at=datetime.now(),
                sample_count=len(audio_samples),
                quality=training_quality,
                language=language,
                metadata={
                    "service": "fish_audio",
                    "samples_count": len(audio_samples),
                    "language": language,
                    "quality": training_quality.value,
                    "training_started": datetime.now().isoformat()
                }
            )

            # Save profile
            self.profiles[voice_id] = profile
            await self._save_profile(profile)

            # Track training status
            self.training_status[fish_model_id] = TrainingStatus(
                model_id=fish_model_id,
                status="training",
                progress=0.0,
                started_at=datetime.now(),
                estimated_completion=datetime.now() + timedelta(hours=2)  # Estimate
            )

            logger.info(f"Fish Audio voice training started: {voice_id} -> {fish_model_id}")
            return profile

        except FishAudioError:
            raise
        except Exception as e:
            logger.error(f"Failed to create voice avatar: {e}")
            raise VoiceCreationError(f"Voice creation failed: {str(e)}")

    async def generate_speech(
        self,
        voice_id: str,
        text: str,
        format: AudioFormat = AudioFormat.MP3,
        speed: float = 1.0,
        pitch: float = 0.0,
        enable_enhancement: bool = True
    ) -> SynthesisResult:
        """
        Generate speech using a voice avatar

        Args:
            voice_id: Voice avatar identifier
            text: Text to synthesize
            format: Output audio format
            speed: Speech speed multiplier (0.5-2.0)
            pitch: Pitch adjustment (-12 to +12 semitones)
            enable_enhancement: Enable audio enhancement

        Returns:
            SynthesisResult: Generated speech data
        """
        if not self.enabled:
            raise ServiceUnavailableError("Fish Audio service not available")

        if voice_id not in self.profiles:
            raise SpeechSynthesisError(f"Voice profile not found: {voice_id}")

        profile = self.profiles[voice_id]
        character_count = len(text)

        # Check character limits
        if profile.characters_used + character_count > profile.character_limit:
            raise QuotaExceededError(
                f"Character limit exceeded. Used: {profile.characters_used}, "
                f"Limit: {profile.character_limit}, Requested: {character_count}"
            )

        # Check if model training is complete
        training_status = await self._check_training_status(profile.fish_model_id)
        if training_status.status != "completed":
            raise SpeechSynthesisError(
                f"Voice model not ready: {training_status.status} ({training_status.progress:.1f}%)"
            )

        try:
            await self._rate_limit_check()

            start_time = datetime.now()

            # Prepare synthesis request
            payload = {
                "model_id": profile.fish_model_id,
                "text": text,
                "format": format.value,
                "speed": max(0.5, min(2.0, speed)),  # Clamp speed
                "pitch": max(-12, min(12, pitch)),   # Clamp pitch
                "enhancement": enable_enhancement,
                "language": profile.language
            }

            # Make synthesis request
            async with self.session.post(self.SYNTHESIS_URL, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()

                    # Fish Audio might return audio data directly or a task ID
                    if "audio" in response_data:
                        # Direct audio response
                        audio_data = base64.b64decode(response_data["audio"])
                        task_id = None
                    elif "task_id" in response_data:
                        # Async generation - wait for completion
                        task_id = response_data["task_id"]
                        audio_data = await self._wait_for_synthesis_completion(task_id)
                    else:
                        raise SpeechSynthesisError("Invalid response format")

                elif response.status == 400:
                    error_data = await response.json()
                    raise SpeechSynthesisError(f"Bad request: {error_data.get('message', 'Unknown error')}")
                elif response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 402:
                    raise QuotaExceededError("Payment required or quota exceeded")
                elif response.status == 429:
                    raise QuotaExceededError("Rate limit exceeded")
                elif response.status == 503:
                    raise ServiceUnavailableError("Service temporarily unavailable")
                else:
                    error_text = await response.text()
                    raise SpeechSynthesisError(f"API error {response.status}: {error_text}")

            generation_time = (datetime.now() - start_time).total_seconds()

            # Update character usage
            profile.characters_used += character_count
            await self._save_profile(profile)

            # Estimate duration based on text length and speed
            words_per_minute = 150  # Average speaking rate
            word_count = len(text.split())
            duration = (word_count / words_per_minute) * 60 / speed

            result = SynthesisResult(
                audio_data=audio_data,
                format=format,
                duration=duration,
                voice_id=voice_id,
                text=text,
                characters_used=character_count,
                generation_time=generation_time,
                quality=profile.quality,
                task_id=task_id
            )

            logger.info(f"Fish Audio speech generated: {character_count} chars for voice {voice_id}")
            return result

        except FishAudioError:
            raise
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            raise SpeechSynthesisError(f"Synthesis failed: {str(e)}")

    async def check_voice_training_status(self, voice_id: str) -> TrainingStatus:
        """Check the training status of a voice"""
        if voice_id not in self.profiles:
            raise VoiceCreationError(f"Voice profile not found: {voice_id}")

        profile = self.profiles[voice_id]
        return await self._check_training_status(profile.fish_model_id)

    async def list_voice_profiles(self, user_id: str) -> List[VoiceProfile]:
        """List voice profiles for a user"""
        return [
            profile for profile in self.profiles.values()
            if profile.user_id == user_id
        ]

    async def delete_voice_profile(self, voice_id: str, user_id: str) -> bool:
        """Delete a voice profile"""
        if voice_id not in self.profiles:
            return False

        profile = self.profiles[voice_id]
        if profile.user_id != user_id:
            raise VoiceCreationError("Permission denied: not your voice profile")

        try:
            await self._rate_limit_check()

            # Delete from Fish Audio
            delete_url = f"{self.MODELS_URL}/{profile.fish_model_id}"
            async with self.session.delete(delete_url) as response:
                if response.status not in [200, 404]:  # 404 means already deleted
                    logger.warning(f"Could not delete Fish Audio model: {response.status}")

            # Remove local profile
            del self.profiles[voice_id]

            # Remove training status
            if profile.fish_model_id in self.training_status:
                del self.training_status[profile.fish_model_id]

            # Remove profile file
            profile_file = Path(self.voices_path) / f"{voice_id}.json"
            if profile_file.exists():
                profile_file.unlink()

            logger.info(f"Voice profile deleted: {voice_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete voice profile: {e}")
            return False

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health"""
        status = {
            "service": "fish_audio",
            "enabled": self.enabled,
            "fallback_enabled": self.use_as_fallback,
            "fallback_priority": self.fallback_priority,
            "status": "healthy" if self.enabled else "disabled",
            "voice_count": len(self.profiles),
            "training_count": len([s for s in self.training_status.values() if s.status == "training"]),
            "api_key_configured": bool(self.api_key),
            "voices_path": self.voices_path
        }

        if self.enabled:
            try:
                # Test API connectivity
                async with self.session.get(f"{self.BASE_URL}/health") as response:
                    status["api_reachable"] = response.status == 200
            except Exception as e:
                status["status"] = "degraded"
                status["api_reachable"] = False
                status["error"] = str(e)

        return status

    async def can_handle_fallback(self, original_service: str, error: Exception) -> bool:
        """Check if this service can handle fallback for another service"""
        if not self.use_as_fallback or not self.enabled:
            return False

        # Handle specific error types that Fish Audio can handle
        fallback_errors = {
            "quota_exceeded": QuotaExceededError,
            "rate_limited": QuotaExceededError,
            "service_unavailable": ServiceUnavailableError,
            "authentication_error": AuthenticationError
        }

        # Can handle fallback from specific services
        supported_fallbacks = ["elevenlabs", "coqui"]

        return (
            original_service in supported_fallbacks and
            any(isinstance(error, err_type) for err_type in fallback_errors.values())
        )

    # Private helper methods

    def _generate_voice_id(self, user_id: str, voice_name: str) -> str:
        """Generate unique voice ID"""
        timestamp = str(int(datetime.now().timestamp()))
        content = f"{user_id}:{voice_name}:{timestamp}"
        return f"fish_{hashlib.sha256(content.encode()).hexdigest()[:16]}"

    async def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        now = datetime.now()
        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if (now - ts).total_seconds() < 60
        ]

        if len(self.request_timestamps) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_timestamps[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)

        self.request_timestamps.append(now)

    async def _verify_api_key(self):
        """Verify API key is valid"""
        try:
            test_url = f"{self.BASE_URL}/user/profile"
            async with self.session.get(test_url) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Fish Audio API key")
                elif response.status not in [200, 404]:  # 404 might be normal for some endpoints
                    logger.warning(f"API key verification returned status: {response.status}")

        except AuthenticationError:
            raise
        except Exception as e:
            logger.warning(f"Could not verify API key: {e}")

    async def _prepare_training_data(
        self,
        audio_samples: List[bytes],
        transcriptions: Optional[List[str]],
        language: str
    ) -> List[Dict[str, Any]]:
        """Prepare training data for Fish Audio"""
        training_samples = []

        for i, audio_data in enumerate(audio_samples):
            # Convert audio to base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')

            sample_data = {
                "audio": audio_b64,
                "filename": f"sample_{i:03d}.wav"
            }

            # Add transcription if provided
            if transcriptions and i < len(transcriptions):
                sample_data["text"] = transcriptions[i]

            training_samples.append(sample_data)

        return training_samples

    async def _start_voice_training(
        self,
        voice_name: str,
        training_data: List[Dict[str, Any]],
        quality: VoiceQuality,
        language: str
    ) -> str:
        """Start voice model training"""
        payload = {
            "name": voice_name,
            "language": language,
            "quality": quality.value,
            "samples": training_data
        }

        async with self.session.post(self.TRAINING_URL, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data["model_id"]
            elif response.status == 400:
                error_data = await response.json()
                raise VoiceCreationError(f"Training request invalid: {error_data.get('message', 'Unknown error')}")
            elif response.status == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status == 402:
                raise QuotaExceededError("Insufficient credits for training")
            else:
                error_text = await response.text()
                raise VoiceCreationError(f"Training failed {response.status}: {error_text}")

    async def _check_training_status(self, model_id: str) -> TrainingStatus:
        """Check training status"""
        if model_id in self.training_status:
            cached_status = self.training_status[model_id]
            if cached_status.status == "completed":
                return cached_status

        try:
            status_url = f"{self.MODELS_URL}/{model_id}/status"
            async with self.session.get(status_url) as response:
                if response.status == 200:
                    data = await response.json()

                    status = TrainingStatus(
                        model_id=model_id,
                        status=data.get("status", "unknown"),
                        progress=data.get("progress", 0.0),
                        started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
                        estimated_completion=datetime.fromisoformat(data["estimated_completion"]) if "estimated_completion" in data else None,
                        error_message=data.get("error_message")
                    )

                    self.training_status[model_id] = status
                    return status
                else:
                    # Return cached status if API call fails
                    return self.training_status.get(model_id, TrainingStatus(
                        model_id=model_id,
                        status="unknown",
                        progress=0.0,
                        started_at=datetime.now()
                    ))

        except Exception as e:
            logger.error(f"Failed to check training status: {e}")
            return self.training_status.get(model_id, TrainingStatus(
                model_id=model_id,
                status="error",
                progress=0.0,
                started_at=datetime.now(),
                error_message=str(e)
            ))

    async def _wait_for_synthesis_completion(self, task_id: str, timeout: int = 60) -> bytes:
        """Wait for async synthesis to complete"""
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                task_url = f"{self.BASE_URL}/tasks/{task_id}"
                async with self.session.get(task_url) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data["status"] == "completed":
                            return base64.b64decode(data["result"]["audio"])
                        elif data["status"] == "failed":
                            raise SpeechSynthesisError(f"Synthesis failed: {data.get('error', 'Unknown error')}")

                        # Still processing, wait a bit
                        await asyncio.sleep(2)
                    else:
                        raise SpeechSynthesisError(f"Task status check failed: {response.status}")

            except Exception as e:
                logger.error(f"Error checking synthesis task: {e}")
                await asyncio.sleep(2)

        raise SpeechSynthesisError("Synthesis timeout")

    def _load_profiles(self):
        """Load voice profiles from disk"""
        try:
            voices_dir = Path(self.voices_path)
            for profile_file in voices_dir.glob("*.json"):
                try:
                    with open(profile_file, 'r') as f:
                        data = json.load(f)

                    profile = VoiceProfile(
                        voice_id=data["voice_id"],
                        user_id=data["user_id"],
                        voice_name=data["voice_name"],
                        fish_model_id=data["fish_model_id"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        sample_count=data["sample_count"],
                        quality=VoiceQuality(data["quality"]),
                        language=data.get("language", "en"),
                        character_limit=data.get("character_limit", 50000),
                        characters_used=data.get("characters_used", 0),
                        metadata=data.get("metadata", {})
                    )

                    self.profiles[profile.voice_id] = profile

                except Exception as e:
                    logger.warning(f"Could not load profile {profile_file}: {e}")

        except Exception as e:
            logger.warning(f"Could not load profiles: {e}")

    async def _save_profile(self, profile: VoiceProfile):
        """Save voice profile to disk"""
        try:
            profile_file = Path(self.voices_path) / f"{profile.voice_id}.json"

            data = {
                "voice_id": profile.voice_id,
                "user_id": profile.user_id,
                "voice_name": profile.voice_name,
                "fish_model_id": profile.fish_model_id,
                "created_at": profile.created_at.isoformat(),
                "sample_count": profile.sample_count,
                "quality": profile.quality.value,
                "language": profile.language,
                "character_limit": profile.character_limit,
                "characters_used": profile.characters_used,
                "metadata": profile.metadata
            }

            async with aiofiles.open(profile_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Could not save profile: {e}")


# Singleton instance
_fish_service: Optional[FishAudioService] = None


async def get_fish_service() -> FishAudioService:
    """Get singleton Fish Audio service instance"""
    global _fish_service
    if _fish_service is None:
        _fish_service = FishAudioService()
        await _fish_service.initialize()
    return _fish_service