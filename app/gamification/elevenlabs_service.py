"""
ElevenLabs Voice Service
Integrates with ElevenLabs API for voice cloning and text-to-speech
"""

import os
import json
import logging
import httpx
import asyncio
from typing import Dict, List, Any, Optional, Tuple, AsyncIterator, Union
from datetime import datetime, timedelta
import base64
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VoiceSettings:
    """Voice settings for TTS"""
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True

@dataclass
class VoiceCloneRequest:
    """Request for voice cloning"""
    name: str
    files: List[bytes]
    description: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

class ElevenLabsService:
    """
    ElevenLabs Conversational AI and Voice Cloning Service
    Provides voice cloning, TTS, and voice management capabilities
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    CONVERSATIONAL_URL = "https://api.elevenlabs.io/v1/conversational-ai"
    
    def __init__(self):
        """Initialize ElevenLabs service"""
        self.api_key = os.getenv('ELEVENLABS_API_KEY', '')
        self.write_api_key = os.getenv('ELEVENLABS_WRITE_API_KEY', '')
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        self.write_headers = {
            "xi-api-key": self.write_api_key if self.write_api_key else self.api_key,
            "Content-Type": "application/json"
        }
        self.initialized = bool(self.api_key)
        
        # Rate limiting
        self.rate_limit_per_minute = 60
        self.last_request_times: List[datetime] = []
        
        # Cache for voice IDs
        self.voice_cache: Dict[str, Dict] = {}
        self.cache_ttl = timedelta(hours=1)
        self.cache_timestamp: Optional[datetime] = None
        
        if self.initialized:
            logger.info("✅ ElevenLabs service initialized")
            if self.write_api_key:
                logger.info("✅ ElevenLabs write API key configured")
            else:
                logger.info("ℹ️ Using read API key for all operations")
        else:
            logger.warning("⚠️ ElevenLabs API key not found. Voice features disabled.")
    
    def is_available(self) -> bool:
        """Check if service is configured and available"""
        return self.initialized
    
    async def _check_rate_limit(self) -> bool:
        """Check and enforce rate limiting"""
        now = datetime.now()
        # Remove requests older than 1 minute
        self.last_request_times = [
            t for t in self.last_request_times 
            if now - t < timedelta(minutes=1)
        ]
        
        if len(self.last_request_times) >= self.rate_limit_per_minute:
            return False
        
        self.last_request_times.append(now)
        return True
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Union[Dict, List]] = None,
        stream: bool = False,
        use_write_key: bool = False
    ) -> Dict[str, Any]:
        """Make API request with error handling"""
        if not self.is_available():
            raise ValueError("ElevenLabs service not configured")
        
        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded. Please try again later.")
        
        url = f"{self.BASE_URL}{endpoint}"
        
        # Determine which API key to use
        if use_write_key and self.write_api_key:
            api_key = self.write_api_key
            headers = self.write_headers
        else:
            api_key = self.api_key
            headers = self.headers
        
        async with httpx.AsyncClient() as client:
            try:
                if files:
                    # For file uploads, use multipart form data
                    headers = {"xi-api-key": api_key}
                    response = await client.request(
                        method, url, files=files, data=data, headers=headers
                    )
                else:
                    response = await client.request(
                        method, url, json=data, headers=headers
                    )
                
                if response.status_code >= 400:
                    error_msg = f"ElevenLabs API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                if stream:
                    return {"audio_stream": response.content}
                
                return response.json() if response.text else {}
                
            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                raise Exception(f"Failed to connect to ElevenLabs: {str(e)}")
    
    async def get_voices(self, refresh: bool = False) -> List[Dict[str, Any]]:
        """Get list of available voices"""
        if not refresh and self.voice_cache and self.cache_timestamp:
            if datetime.now() - self.cache_timestamp < self.cache_ttl:
                return list(self.voice_cache.values())
        
        try:
            response = await self._make_request("GET", "/voices")
            voices = response.get("voices", [])
            
            # Update cache
            self.voice_cache = {v["voice_id"]: v for v in voices}
            self.cache_timestamp = datetime.now()
            
            return voices
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []
    
    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific voice"""
        # Check cache first
        if voice_id in self.voice_cache:
            return self.voice_cache[voice_id]
        
        try:
            response = await self._make_request("GET", f"/voices/{voice_id}")
            self.voice_cache[voice_id] = response
            return response
        except Exception as e:
            logger.error(f"Failed to get voice {voice_id}: {e}")
            return None
    
    async def clone_voice(
        self,
        name: str,
        audio_samples: List[bytes],
        description: str = "",
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Clone a voice from audio samples
        
        Args:
            name: Name for the cloned voice
            audio_samples: List of audio file bytes (WAV/MP3)
            description: Optional description
            labels: Optional metadata labels
            
        Returns:
            Voice ID if successful, None otherwise
        """
        if not audio_samples:
            raise ValueError("At least one audio sample is required")
        
        if len(audio_samples) > 25:
            raise ValueError("Maximum 25 audio samples allowed")
        
        try:
            # Prepare files for multipart upload
            files = []
            for i, sample in enumerate(audio_samples):
                files.append(("files", (f"sample_{i}.wav", sample, "audio/wav")))
            
            data = {
                "name": name,
                "description": description or f"Voice clone created on {datetime.now().isoformat()}"
            }
            
            if labels:
                data["labels"] = json.dumps(labels)
            
            response = await self._make_request(
                "POST",
                "/voices/add",
                data=data,
                files=files,
                use_write_key=True
            )
            
            voice_id = response.get("voice_id")
            if voice_id:
                logger.info(f"Successfully cloned voice: {name} (ID: {voice_id})")
                # Clear cache to force refresh
                self.voice_cache.pop(voice_id, None)
            
            return voice_id
            
        except Exception as e:
            logger.error(f"Failed to clone voice: {e}")
            return None
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str,
        settings: Optional[VoiceSettings] = None,
        model_id: str = "eleven_monolingual_v1"
    ) -> Optional[bytes]:
        """
        Convert text to speech using a voice
        
        Args:
            text: Text to convert
            voice_id: Voice ID to use
            settings: Voice settings for generation
            model_id: Model to use for TTS
            
        Returns:
            Audio bytes if successful, None otherwise
        """
        if not text:
            raise ValueError("Text cannot be empty")
        
        if not settings:
            settings = VoiceSettings()
        
        try:
            data = {
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": settings.stability,
                    "similarity_boost": settings.similarity_boost,
                    "style": settings.style,
                    "use_speaker_boost": settings.use_speaker_boost
                }
            }
            
            response = await self._make_request(
                "POST",
                f"/text-to-speech/{voice_id}",
                data=data,
                stream=True
            )
            
            audio_data = response.get("audio_stream")
            if audio_data:
                logger.info(f"Generated speech: {len(text)} chars -> {len(audio_data)} bytes")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return None
    
    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: str,
        settings: Optional[VoiceSettings] = None,
        model_id: str = "eleven_monolingual_v1"
    ) -> AsyncIterator[bytes]:
        """
        Stream text-to-speech conversion
        
        Yields audio chunks as they're generated
        """
        if not text or not self.is_available():
            return
        
        if not settings:
            settings = VoiceSettings()
        
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}/stream"
        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": settings.stability,
                "similarity_boost": settings.similarity_boost,
                "style": settings.style,
                "use_speaker_boost": settings.use_speaker_boost
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Use write key for streaming if available
                stream_headers = self.write_headers if self.write_api_key else self.headers
                async with client.stream(
                    "POST",
                    url,
                    json=data,
                    headers=stream_headers
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                return
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice"""
        try:
            await self._make_request("DELETE", f"/voices/{voice_id}", use_write_key=True)
            self.voice_cache.pop(voice_id, None)
            logger.info(f"Deleted voice: {voice_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete voice {voice_id}: {e}")
            return False
    
    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get user subscription info and usage"""
        try:
            response = await self._make_request("GET", "/user")
            return response
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        user_info = await self.get_user_info()
        if not user_info:
            return {}
        
        subscription = user_info.get("subscription", {})
        return {
            "character_count": subscription.get("character_count", 0),
            "character_limit": subscription.get("character_limit", 0),
            "available_characters": subscription.get("character_limit", 0) - subscription.get("character_count", 0),
            "voice_limit": subscription.get("voice_limit", 0),
            "professional_voice_limit": subscription.get("professional_voice_limit", 0),
            "can_use_instant_voice_cloning": subscription.get("can_use_instant_voice_cloning", False),
            "can_use_professional_voice_cloning": subscription.get("can_use_professional_voice_cloning", False),
            "currency": subscription.get("currency", "USD"),
            "status": subscription.get("status", "free")
        }
    
    async def validate_audio_sample(self, audio_data: bytes) -> Tuple[bool, str]:
        """
        Validate audio sample for voice cloning
        
        Returns:
            (is_valid, message) tuple
        """
        # Check file size (max 10MB per sample)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(audio_data) > max_size:
            return False, "Audio file too large (max 10MB)"
        
        # Check if it's actually audio (basic check)
        # WAV files start with "RIFF"
        # MP3 files often start with "ID3" or FF FB/FF FA
        if audio_data[:4] == b'RIFF':
            # It's a WAV file
            return True, "Valid WAV file"
        elif audio_data[:3] == b'ID3' or audio_data[:2] in [b'\xff\xfb', b'\xff\xfa']:
            # It's likely an MP3 file
            return True, "Valid MP3 file"
        else:
            return False, "Invalid audio format. Please use WAV or MP3"
    
    async def create_conversational_ai_agent(
        self,
        name: str,
        voice_id: str,
        system_prompt: str,
        first_message: str = "Hello! How can I help you today?"
    ) -> Optional[str]:
        """
        Create a conversational AI agent (for future use)
        
        Args:
            name: Agent name
            voice_id: Voice ID to use
            system_prompt: System instructions for the agent
            first_message: Initial greeting message
            
        Returns:
            Agent ID if successful
        """
        # This is a placeholder for future ElevenLabs Conversational AI integration
        # The API is not yet publicly available
        logger.info("Conversational AI agent creation is pending API availability")
        return None

# Singleton instance
_elevenlabs_service: Optional[ElevenLabsService] = None

def get_elevenlabs_service() -> ElevenLabsService:
    """Get or create ElevenLabs service singleton"""
    global _elevenlabs_service
    if _elevenlabs_service is None:
        _elevenlabs_service = ElevenLabsService()
    return _elevenlabs_service