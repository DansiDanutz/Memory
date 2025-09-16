"""
ElevenLabs Voice Service - Premium Voice Cloning for PREMIUM Tier Users
======================================================================
Provides high-quality voice cloning using ElevenLabs API.
Available to paying PREMIUM tier users.
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

logger = logging.getLogger(__name__)


class ElevenLabsError(Exception):
    """Base exception for ElevenLabs service errors"""
    pass


class VoiceCreationError(ElevenLabsError):
    """Error creating voice avatar"""
    pass


class SpeechSynthesisError(ElevenLabsError):
    """Error during speech synthesis"""
    pass


class QuotaExceededError(ElevenLabsError):
    """API quota exceeded"""
    pass


class AuthenticationError(ElevenLabsError):
    """API authentication failed"""
    pass


class AudioFormat(str, Enum):
    """Supported audio formats"""
    MP3_22050_32 = "mp3_22050_32"
    MP3_44100_32 = "mp3_44100_32"
    MP3_44100_64 = "mp3_44100_64"
    MP3_44100_96 = "mp3_44100_96"
    MP3_44100_128 = "mp3_44100_128"
    MP3_44100_192 = "mp3_44100_192"
    PCM_16000 = "pcm_16000"
    PCM_22050 = "pcm_22050"
    PCM_24000 = "pcm_24000"
    PCM_44100 = "pcm_44100"
    ULAW_8000 = "ulaw_8000"


class VoiceSettings(str, Enum):
    """Voice generation settings presets"""
    BALANCED = "balanced"
    CLEAR = "clear"
    EXPRESSIVE = "expressive"
    MONOTONE = "monotone"


@dataclass
class VoiceProfile:
    """ElevenLabs voice profile"""
    voice_id: str
    user_id: str
    voice_name: str
    elevenlabs_voice_id: str
    created_at: datetime
    sample_count: int
    character_limit: int
    characters_used: int = 0
    settings: Dict[str, float] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.settings is None:
            self.settings = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.0}
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
    request_id: Optional[str] = None


@dataclass
class UsageStats:
    """Usage statistics"""
    character_count: int
    character_limit: int
    reset_date: datetime
    subscription_tier: str


class ElevenLabsService:
    """
    ElevenLabs voice cloning service for premium users
    High-quality voice synthesis and cloning
    """

    # API Configuration
    BASE_URL = "https://api.elevenlabs.io/v1"
    VOICE_CLONE_URL = f"{BASE_URL}/voices/add"
    SYNTHESIS_URL = f"{BASE_URL}/text-to-speech"
    USER_URL = f"{BASE_URL}/user"

    # Service limits
    MIN_SAMPLE_SIZE = 1024  # 1KB minimum
    MAX_SAMPLE_SIZE = 25 * 1024 * 1024  # 25MB maximum
    MAX_SAMPLES_PER_VOICE = 25
    MIN_SAMPLES_PER_VOICE = 1

    def __init__(self):
        # Configuration from environment
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.enabled = self.api_key is not None
        self.voices_path = os.getenv("ELEVENLABS_VOICES_PATH", "./data/voices/elevenlabs")
        self.default_format = AudioFormat(os.getenv("ELEVENLABS_DEFAULT_FORMAT", "mp3_44100_128"))

        # Rate limiting
        self.max_requests_per_minute = int(os.getenv("ELEVENLABS_RATE_LIMIT", "60"))
        self.request_timestamps: List[datetime] = []

        # Session management
        self.session: Optional[aiohttp.ClientSession] = None

        # Voice profiles storage
        self.profiles: Dict[str, VoiceProfile] = {}

        # Ensure directories exist
        Path(self.voices_path).mkdir(parents=True, exist_ok=True)

        # Load existing profiles
        self._load_profiles()

        logger.info(f"ElevenLabsService initialized - Enabled: {self.enabled}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize the service"""
        if not self.enabled:
            raise AuthenticationError("ElevenLabs API key not configured")

        # Initialize HTTP session with headers
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=timeout
        )

        # Verify API key
        await self._verify_api_key()

        logger.info("ElevenLabsService initialized successfully")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("ElevenLabsService cleaned up")

    async def create_voice_avatar(
        self,
        user_id: str,
        voice_name: str,
        audio_samples: List[bytes],
        description: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> VoiceProfile:
        """
        Create a voice avatar using ElevenLabs voice cloning

        Args:
            user_id: User identifier
            voice_name: Name for the voice avatar
            audio_samples: List of audio sample data
            description: Optional description
            labels: Optional metadata labels

        Returns:
            VoiceProfile: Created voice profile
        """
        if not self.enabled:
            raise AuthenticationError("ElevenLabs service not available")

        if len(audio_samples) < self.MIN_SAMPLES_PER_VOICE:
            raise VoiceCreationError(f"Minimum {self.MIN_SAMPLES_PER_VOICE} audio sample required")

        if len(audio_samples) > self.MAX_SAMPLES_PER_VOICE:
            raise VoiceCreationError(f"Maximum {self.MAX_SAMPLES_PER_VOICE} audio samples allowed")

        # Validate sample sizes
        for i, sample in enumerate(audio_samples):
            if len(sample) < self.MIN_SAMPLE_SIZE:
                raise VoiceCreationError(f"Sample {i} too small: {len(sample)} bytes")
            if len(sample) > self.MAX_SAMPLE_SIZE:
                raise VoiceCreationError(f"Sample {i} too large: {len(sample)} bytes")

        try:
            await self._rate_limit_check()

            # Prepare multipart form data
            form_data = aiohttp.FormData()
            form_data.add_field('name', voice_name)

            if description:
                form_data.add_field('description', description)

            if labels:
                form_data.add_field('labels', json.dumps(labels))

            # Add audio samples
            for i, sample in enumerate(audio_samples):
                form_data.add_field(
                    'files',
                    sample,
                    filename=f'sample_{i}.wav',
                    content_type='audio/wav'
                )

            # Create voice clone
            async with self.session.post(self.VOICE_CLONE_URL, data=form_data) as response:
                if response.status == 200:
                    data = await response.json()
                    elevenlabs_voice_id = data['voice_id']
                elif response.status == 400:
                    error_data = await response.json()
                    raise VoiceCreationError(f"Invalid request: {error_data.get('detail', 'Unknown error')}")
                elif response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 422:
                    error_data = await response.json()
                    raise VoiceCreationError(f"Validation error: {error_data.get('detail', 'Unknown error')}")
                else:
                    error_text = await response.text()
                    raise VoiceCreationError(f"API error {response.status}: {error_text}")

            # Generate internal voice ID
            voice_id = self._generate_voice_id(user_id, voice_name)

            # Get user's character limit
            usage_stats = await self.get_usage_stats()

            # Create voice profile
            profile = VoiceProfile(
                voice_id=voice_id,
                user_id=user_id,
                voice_name=voice_name,
                elevenlabs_voice_id=elevenlabs_voice_id,
                created_at=datetime.now(),
                sample_count=len(audio_samples),
                character_limit=usage_stats.character_limit,
                settings={"stability": 0.5, "similarity_boost": 0.8, "style": 0.0},
                metadata={
                    "service": "elevenlabs",
                    "description": description,
                    "labels": labels or {},
                    "samples_count": len(audio_samples)
                }
            )

            # Save profile
            self.profiles[voice_id] = profile
            await self._save_profile(profile)

            logger.info(f"ElevenLabs voice avatar created: {voice_id} -> {elevenlabs_voice_id}")
            return profile

        except ElevenLabsError:
            raise
        except Exception as e:
            logger.error(f"Failed to create voice avatar: {e}")
            raise VoiceCreationError(f"Voice creation failed: {str(e)}")

    async def generate_speech(
        self,
        voice_id: str,
        text: str,
        format: AudioFormat = None,
        voice_settings: Optional[Dict[str, float]] = None,
        model_id: str = "eleven_monolingual_v1",
        optimize_streaming_latency: int = 0
    ) -> SynthesisResult:
        """
        Generate speech using a voice avatar

        Args:
            voice_id: Voice avatar identifier
            text: Text to synthesize
            format: Output audio format
            voice_settings: Voice generation settings
            model_id: ElevenLabs model to use
            optimize_streaming_latency: Latency optimization level

        Returns:
            SynthesisResult: Generated speech data
        """
        if not self.enabled:
            raise AuthenticationError("ElevenLabs service not available")

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

        try:
            await self._rate_limit_check()

            start_time = datetime.now()

            # Use provided settings or profile defaults
            settings = voice_settings or profile.settings

            # Prepare request
            synthesis_url = f"{self.SYNTHESIS_URL}/{profile.elevenlabs_voice_id}"

            payload = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": settings.get("stability", 0.5),
                    "similarity_boost": settings.get("similarity_boost", 0.8),
                    "style": settings.get("style", 0.0),
                    "use_speaker_boost": settings.get("use_speaker_boost", True)
                }
            }

            if optimize_streaming_latency > 0:
                payload["optimize_streaming_latency"] = optimize_streaming_latency

            # Set output format in headers
            output_format = format or self.default_format
            headers = {"Accept": f"audio/{output_format.value}"}

            # Make synthesis request
            async with self.session.post(
                synthesis_url,
                json=payload,
                headers=headers
            ) as response:

                if response.status == 200:
                    audio_data = await response.read()
                    request_id = response.headers.get("xi-request-id")
                elif response.status == 400:
                    error_data = await response.json()
                    raise SpeechSynthesisError(f"Bad request: {error_data.get('detail', 'Unknown error')}")
                elif response.status == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status == 422:
                    error_data = await response.json()
                    raise SpeechSynthesisError(f"Validation error: {error_data.get('detail', 'Unknown error')}")
                elif response.status == 429:
                    raise QuotaExceededError("Rate limit exceeded")
                else:
                    error_text = await response.text()
                    raise SpeechSynthesisError(f"API error {response.status}: {error_text}")

            generation_time = (datetime.now() - start_time).total_seconds()

            # Update character usage
            profile.characters_used += character_count
            await self._save_profile(profile)

            # Estimate duration (rough calculation based on format)
            duration = len(audio_data) / self._get_bytes_per_second(output_format)

            result = SynthesisResult(
                audio_data=audio_data,
                format=output_format,
                duration=duration,
                voice_id=voice_id,
                text=text,
                characters_used=character_count,
                generation_time=generation_time,
                request_id=request_id
            )

            logger.info(f"ElevenLabs speech generated: {character_count} chars for voice {voice_id}")
            return result

        except ElevenLabsError:
            raise
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            raise SpeechSynthesisError(f"Synthesis failed: {str(e)}")

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

            # Delete from ElevenLabs
            delete_url = f"{self.BASE_URL}/voices/{profile.elevenlabs_voice_id}"
            async with self.session.delete(delete_url) as response:
                if response.status not in [200, 404]:  # 404 means already deleted
                    logger.warning(f"Could not delete ElevenLabs voice: {response.status}")

            # Remove local profile
            del self.profiles[voice_id]

            # Remove profile file
            profile_file = Path(self.voices_path) / f"{voice_id}.json"
            if profile_file.exists():
                profile_file.unlink()

            logger.info(f"Voice profile deleted: {voice_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete voice profile: {e}")
            return False

    async def get_usage_stats(self) -> UsageStats:
        """Get current usage statistics"""
        try:
            await self._rate_limit_check()

            async with self.session.get(self.USER_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    subscription = data.get("subscription", {})

                    return UsageStats(
                        character_count=subscription.get("character_count", 0),
                        character_limit=subscription.get("character_limit", 10000),
                        reset_date=datetime.fromisoformat(
                            subscription.get("next_character_count_reset_unix",
                                           datetime.now().isoformat()).replace("Z", "+00:00")
                        ),
                        subscription_tier=subscription.get("tier", "free")
                    )
                elif response.status == 401:
                    raise AuthenticationError("Invalid API key")
                else:
                    error_text = await response.text()
                    raise ElevenLabsError(f"Failed to get usage stats: {error_text}")

        except ElevenLabsError:
            raise
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            # Return default stats on error
            return UsageStats(
                character_count=0,
                character_limit=10000,
                reset_date=datetime.now() + timedelta(days=30),
                subscription_tier="unknown"
            )

    async def update_voice_settings(
        self,
        voice_id: str,
        user_id: str,
        settings: Dict[str, float]
    ) -> bool:
        """Update voice generation settings"""
        if voice_id not in self.profiles:
            return False

        profile = self.profiles[voice_id]
        if profile.user_id != user_id:
            raise VoiceCreationError("Permission denied: not your voice profile")

        # Validate settings
        valid_keys = {"stability", "similarity_boost", "style", "use_speaker_boost"}
        for key in settings:
            if key not in valid_keys:
                raise VoiceCreationError(f"Invalid setting: {key}")

        # Update profile
        profile.settings.update(settings)
        await self._save_profile(profile)

        logger.info(f"Voice settings updated for {voice_id}")
        return True

    async def get_service_status(self) -> Dict[str, Any]:
        """Get service status and health"""
        status = {
            "service": "elevenlabs",
            "enabled": self.enabled,
            "status": "healthy" if self.enabled else "disabled",
            "voice_count": len(self.profiles),
            "api_key_configured": bool(self.api_key),
            "voices_path": self.voices_path
        }

        if self.enabled:
            try:
                usage = await self.get_usage_stats()
                status.update({
                    "character_usage": usage.character_count,
                    "character_limit": usage.character_limit,
                    "subscription_tier": usage.subscription_tier,
                    "reset_date": usage.reset_date.isoformat()
                })
            except Exception as e:
                status["status"] = "degraded"
                status["error"] = str(e)

        return status

    # Private helper methods

    def _generate_voice_id(self, user_id: str, voice_name: str) -> str:
        """Generate unique voice ID"""
        timestamp = str(int(datetime.now().timestamp()))
        content = f"{user_id}:{voice_name}:{timestamp}"
        return f"el_{hashlib.sha256(content.encode()).hexdigest()[:16]}"

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
            async with self.session.get(self.USER_URL) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid ElevenLabs API key")
                elif response.status != 200:
                    error_text = await response.text()
                    raise ElevenLabsError(f"API verification failed: {error_text}")

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"API key verification failed: {e}")
            raise ElevenLabsError(f"Could not verify API key: {str(e)}")

    def _get_bytes_per_second(self, format: AudioFormat) -> float:
        """Estimate bytes per second for audio format"""
        format_map = {
            AudioFormat.MP3_22050_32: 4000,    # 32kbps = 4000 bytes/sec
            AudioFormat.MP3_44100_32: 4000,
            AudioFormat.MP3_44100_64: 8000,    # 64kbps = 8000 bytes/sec
            AudioFormat.MP3_44100_96: 12000,   # 96kbps = 12000 bytes/sec
            AudioFormat.MP3_44100_128: 16000,  # 128kbps = 16000 bytes/sec
            AudioFormat.MP3_44100_192: 24000,  # 192kbps = 24000 bytes/sec
            AudioFormat.PCM_16000: 32000,      # 16kHz * 2 bytes
            AudioFormat.PCM_22050: 44100,      # 22.05kHz * 2 bytes
            AudioFormat.PCM_24000: 48000,      # 24kHz * 2 bytes
            AudioFormat.PCM_44100: 88200,      # 44.1kHz * 2 bytes
            AudioFormat.ULAW_8000: 8000,       # 8kHz * 1 byte
        }
        return format_map.get(format, 16000)  # Default estimate

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
                        elevenlabs_voice_id=data["elevenlabs_voice_id"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        sample_count=data["sample_count"],
                        character_limit=data["character_limit"],
                        characters_used=data.get("characters_used", 0),
                        settings=data.get("settings", {"stability": 0.5, "similarity_boost": 0.8, "style": 0.0}),
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
                "elevenlabs_voice_id": profile.elevenlabs_voice_id,
                "created_at": profile.created_at.isoformat(),
                "sample_count": profile.sample_count,
                "character_limit": profile.character_limit,
                "characters_used": profile.characters_used,
                "settings": profile.settings,
                "metadata": profile.metadata
            }

            async with aiofiles.open(profile_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Could not save profile: {e}")


# Singleton instance
_elevenlabs_service: Optional[ElevenLabsService] = None


async def get_elevenlabs_service() -> ElevenLabsService:
    """Get singleton ElevenLabs service instance"""
    global _elevenlabs_service
    if _elevenlabs_service is None:
        _elevenlabs_service = ElevenLabsService()
        await _elevenlabs_service.initialize()
    return _elevenlabs_service