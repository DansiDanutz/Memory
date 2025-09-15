"""
Async voice service with comprehensive error handling
Replaces synchronous Azure calls with async operations
"""

import asyncio
import aiohttp
import os
import logging
import tempfile
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import aiofiles
from functools import wraps
import backoff
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class VoiceServiceError(Exception):
    """Base exception for voice service"""
    pass


class TranscriptionError(VoiceServiceError):
    """Transcription specific error"""
    pass


class SynthesisError(VoiceServiceError):
    """Speech synthesis specific error"""
    pass


class ServiceUnavailableError(VoiceServiceError):
    """Service temporarily unavailable"""
    pass


class VoiceFormat(str, Enum):
    """Supported audio formats"""
    OGG = "ogg"
    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"


@dataclass
class TranscriptionResult:
    """Transcription result"""
    text: str
    confidence: float
    language: str
    duration: float
    metadata: Dict[str, Any]


@dataclass
class SynthesisResult:
    """Speech synthesis result"""
    audio_data: bytes
    format: str
    duration: float
    voice: str


class CircuitBreaker:
    """Circuit breaker for handling service failures"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func):
        """Decorator for circuit breaker"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if (datetime.now() - self.last_failure_time).seconds > self.timeout:
                    self.state = "half-open"
                    logger.info(f"Circuit breaker half-open for {func.__name__}")
                else:
                    raise ServiceUnavailableError("Service circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                if self.state == "half-open":
                    self.state = "closed"
                    self.failures = 0
                    logger.info(f"Circuit breaker closed for {func.__name__}")
                return result

            except Exception as e:
                self.failures += 1
                self.last_failure_time = datetime.now()

                if self.failures >= self.failure_threshold:
                    self.state = "open"
                    logger.error(f"Circuit breaker opened for {func.__name__}")

                raise e

        return wrapper


class AsyncVoiceService:
    """Async voice service with error handling and retries"""

    def __init__(self):
        self.azure_key = os.getenv("AZURE_SPEECH_KEY")
        self.azure_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.azure_endpoint = f"https://{self.azure_region}.api.cognitive.microsoft.com"

        # Circuit breakers for each service
        self.transcription_breaker = CircuitBreaker()
        self.synthesis_breaker = CircuitBreaker()

        # Connection pooling
        self.session: Optional[aiohttp.ClientSession] = None

        # Cache directory
        self.cache_dir = Path("./cache/voice")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize the service"""
        if not self.session:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300
            )
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        logger.info("Voice service initialized")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Voice service cleaned up")

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def transcribe_audio(
        self,
        audio_url: str,
        language: str = "en-US",
        format: VoiceFormat = VoiceFormat.OGG
    ) -> TranscriptionResult:
        """Transcribe audio with retries and error handling"""
        if not self.azure_key:
            raise VoiceServiceError("Azure Speech key not configured")

        # Check cache first
        cache_key = self._generate_cache_key(audio_url, language)
        cached_result = await self._get_cached_transcription(cache_key)
        if cached_result:
            logger.info(f"Transcription cache hit for {audio_url}")
            return cached_result

        try:
            # Download audio file
            audio_data = await self._download_audio(audio_url)

            # Convert if necessary
            if format != VoiceFormat.WAV:
                audio_data = await self._convert_audio(audio_data, format, VoiceFormat.WAV)

            # Call Azure Speech API
            result = await self._call_azure_transcription(audio_data, language)

            # Cache result
            await self._cache_transcription(cache_key, result)

            return result

        except aiohttp.ClientError as e:
            logger.error(f"Network error during transcription: {e}")
            raise TranscriptionError(f"Failed to transcribe audio: {e}")

        except asyncio.TimeoutError:
            logger.error("Transcription timeout")
            raise TranscriptionError("Transcription request timed out")

        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            raise TranscriptionError(f"Transcription failed: {e}")

    @CircuitBreaker().call
    async def _call_azure_transcription(
        self,
        audio_data: bytes,
        language: str
    ) -> TranscriptionResult:
        """Call Azure Speech API for transcription"""
        url = f"{self.azure_endpoint}/speech/recognition/conversation/cognitiveservices/v1"

        headers = {
            "Ocp-Apim-Subscription-Key": self.azure_key,
            "Content-Type": "audio/wav",
            "Accept": "application/json"
        }

        params = {
            "language": language,
            "format": "detailed"
        }

        async with self.session.post(
            url,
            headers=headers,
            params=params,
            data=audio_data
        ) as response:
            if response.status == 200:
                data = await response.json()
                return TranscriptionResult(
                    text=data.get("DisplayText", ""),
                    confidence=data.get("RecognitionStatus", {}).get("Confidence", 0.0),
                    language=language,
                    duration=data.get("Duration", 0.0) / 10000000,  # Convert to seconds
                    metadata=data
                )
            elif response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise ServiceUnavailableError(f"Rate limited, retry after {retry_after}s")
            else:
                error_text = await response.text()
                raise TranscriptionError(f"Azure API error {response.status}: {error_text}")

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def synthesize_speech(
        self,
        text: str,
        voice: str = "en-US-JennyNeural",
        format: VoiceFormat = VoiceFormat.OGG
    ) -> SynthesisResult:
        """Synthesize speech with error handling"""
        if not self.azure_key:
            raise VoiceServiceError("Azure Speech key not configured")

        # Check cache
        cache_key = self._generate_cache_key(text, voice, format.value)
        cached_result = await self._get_cached_synthesis(cache_key)
        if cached_result:
            logger.info(f"Synthesis cache hit for text: {text[:50]}...")
            return cached_result

        try:
            # Call Azure Speech API
            result = await self._call_azure_synthesis(text, voice, format)

            # Cache result
            await self._cache_synthesis(cache_key, result)

            return result

        except aiohttp.ClientError as e:
            logger.error(f"Network error during synthesis: {e}")
            raise SynthesisError(f"Failed to synthesize speech: {e}")

        except asyncio.TimeoutError:
            logger.error("Synthesis timeout")
            raise SynthesisError("Synthesis request timed out")

        except Exception as e:
            logger.error(f"Unexpected error during synthesis: {e}")
            raise SynthesisError(f"Synthesis failed: {e}")

    @CircuitBreaker().call
    async def _call_azure_synthesis(
        self,
        text: str,
        voice: str,
        format: VoiceFormat
    ) -> SynthesisResult:
        """Call Azure Speech API for synthesis"""
        url = f"{self.azure_endpoint}/cognitiveservices/v1"

        headers = {
            "Ocp-Apim-Subscription-Key": self.azure_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": self._get_azure_format(format)
        }

        # Create SSML
        ssml = f"""
        <speak version='1.0' xml:lang='en-US'>
            <voice xml:lang='en-US' name='{voice}'>
                {self._escape_ssml(text)}
            </voice>
        </speak>
        """

        async with self.session.post(
            url,
            headers=headers,
            data=ssml.encode('utf-8')
        ) as response:
            if response.status == 200:
                audio_data = await response.read()
                return SynthesisResult(
                    audio_data=audio_data,
                    format=format.value,
                    duration=len(audio_data) / 16000,  # Estimate
                    voice=voice
                )
            elif response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise ServiceUnavailableError(f"Rate limited, retry after {retry_after}s")
            else:
                error_text = await response.text()
                raise SynthesisError(f"Azure API error {response.status}: {error_text}")

    async def _download_audio(self, audio_url: str) -> bytes:
        """Download audio file with timeout"""
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(audio_url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    raise VoiceServiceError(f"Failed to download audio: {response.status}")

    async def _convert_audio(
        self,
        audio_data: bytes,
        from_format: VoiceFormat,
        to_format: VoiceFormat
    ) -> bytes:
        """Convert audio format using ffmpeg"""
        try:
            import ffmpeg

            # Save input to temp file
            with tempfile.NamedTemporaryFile(suffix=f".{from_format.value}", delete=False) as input_file:
                input_file.write(audio_data)
                input_path = input_file.name

            # Create output temp file
            output_path = input_path.replace(f".{from_format.value}", f".{to_format.value}")

            # Convert using ffmpeg
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path)
            await asyncio.create_subprocess_exec(
                *ffmpeg.compile(stream),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Read converted file
            async with aiofiles.open(output_path, 'rb') as f:
                converted_data = await f.read()

            # Cleanup
            os.unlink(input_path)
            os.unlink(output_path)

            return converted_data

        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise VoiceServiceError(f"Failed to convert audio: {e}")

    def _generate_cache_key(self, *args) -> str:
        """Generate cache key"""
        key_str = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def _get_cached_transcription(self, cache_key: str) -> Optional[TranscriptionResult]:
        """Get cached transcription"""
        cache_file = self.cache_dir / f"trans_{cache_key}.json"
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    import json
                    data = json.loads(await f.read())
                    return TranscriptionResult(**data)
            except Exception as e:
                logger.error(f"Cache read failed: {e}")
        return None

    async def _cache_transcription(self, cache_key: str, result: TranscriptionResult):
        """Cache transcription result"""
        cache_file = self.cache_dir / f"trans_{cache_key}.json"
        try:
            import json
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps({
                    "text": result.text,
                    "confidence": result.confidence,
                    "language": result.language,
                    "duration": result.duration,
                    "metadata": result.metadata
                }))
        except Exception as e:
            logger.error(f"Cache write failed: {e}")

    async def _get_cached_synthesis(self, cache_key: str) -> Optional[SynthesisResult]:
        """Get cached synthesis"""
        cache_file = self.cache_dir / f"synth_{cache_key}.audio"
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'rb') as f:
                    audio_data = await f.read()
                    # Get metadata from companion file
                    meta_file = self.cache_dir / f"synth_{cache_key}.json"
                    if meta_file.exists():
                        async with aiofiles.open(meta_file, 'r') as mf:
                            import json
                            metadata = json.loads(await mf.read())
                            return SynthesisResult(
                                audio_data=audio_data,
                                format=metadata["format"],
                                duration=metadata["duration"],
                                voice=metadata["voice"]
                            )
            except Exception as e:
                logger.error(f"Cache read failed: {e}")
        return None

    async def _cache_synthesis(self, cache_key: str, result: SynthesisResult):
        """Cache synthesis result"""
        cache_file = self.cache_dir / f"synth_{cache_key}.audio"
        meta_file = self.cache_dir / f"synth_{cache_key}.json"
        try:
            # Save audio data
            async with aiofiles.open(cache_file, 'wb') as f:
                await f.write(result.audio_data)

            # Save metadata
            import json
            async with aiofiles.open(meta_file, 'w') as f:
                await f.write(json.dumps({
                    "format": result.format,
                    "duration": result.duration,
                    "voice": result.voice
                }))
        except Exception as e:
            logger.error(f"Cache write failed: {e}")

    def _get_azure_format(self, format: VoiceFormat) -> str:
        """Get Azure format string"""
        format_map = {
            VoiceFormat.OGG: "ogg-24khz-16bit-mono-opus",
            VoiceFormat.MP3: "audio-24khz-96kbitrate-mono-mp3",
            VoiceFormat.WAV: "riff-24khz-16bit-mono-pcm",
            VoiceFormat.M4A: "audio-24khz-96kbitrate-mono-mp3"
        }
        return format_map.get(format, "ogg-24khz-16bit-mono-opus")

    def _escape_ssml(self, text: str) -> str:
        """Escape text for SSML"""
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&apos;"
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    async def get_service_health(self) -> Dict[str, Any]:
        """Get service health status"""
        health = {
            "service": "voice",
            "status": "healthy",
            "azure_configured": bool(self.azure_key),
            "transcription_circuit": self.transcription_breaker.state,
            "synthesis_circuit": self.synthesis_breaker.state,
            "session_active": self.session is not None
        }

        # Test Azure connectivity
        if self.azure_key:
            try:
                await self.synthesize_speech("test", format=VoiceFormat.WAV)
                health["azure_reachable"] = True
            except:
                health["azure_reachable"] = False
                health["status"] = "degraded"

        return health


# Singleton instance
_voice_service: Optional[AsyncVoiceService] = None


async def get_voice_service() -> AsyncVoiceService:
    """Get singleton voice service"""
    global _voice_service
    if _voice_service is None:
        _voice_service = AsyncVoiceService()
        await _voice_service.initialize()
    return _voice_service