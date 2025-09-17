"""
Voice Avatar Management System
Handles creation, training, and management of voice avatars
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from .database_models import (
    VoiceAvatar, VoiceSample, User,
    AvatarStatus, SessionLocal
)
from .elevenlabs_service import ElevenLabsService
from .subscription_service import SubscriptionService, SubscriptionTier
from .voice_config import (
    get_default_voice_config,
    get_voice_by_preference,
    VOICE_SWITCH_CONFIG,
    TTS_CONFIG
)

logger = logging.getLogger(__name__)

class VoiceAvatarSystem:
    """
    Manages voice avatars and their lifecycle
    """
    
    # Configuration
    MIN_SAMPLES_REQUIRED = 3
    MAX_SAMPLES_PER_AVATAR = 10
    MIN_SAMPLE_DURATION = 3.0  # seconds
    MAX_SAMPLE_DURATION = 60.0  # seconds
    MAX_SAMPLE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize voice avatar system"""
        self.db = db_session or SessionLocal()
        self.elevenlabs = ElevenLabsService()
        self.subscription = SubscriptionService(self.db)
        
        # Cache for avatar data
        self.avatar_cache = {}
        
        # Default voice configuration
        self.default_voice = get_default_voice_config()
        self.voice_preferences = {}  # Store user voice preferences
        
        logger.info("✅ Voice Avatar System initialized with premium gating")
        logger.info(f"📣 Default voice: {self.default_voice['voice_name']} configured")
    
    def _validate_audio_sample(self, audio_data: bytes) -> Tuple[bool, str]:
        """
        Validate audio sample
        
        Returns:
            (is_valid, error_message)
        """
        # Check size
        if len(audio_data) > self.MAX_SAMPLE_SIZE:
            return False, f"Sample too large (max {self.MAX_SAMPLE_SIZE / 1024 / 1024}MB)"
        
        # Check if it's actually audio (basic check for WAV/MP3 headers)
        if not (audio_data[:4] == b'RIFF' or  # WAV
                audio_data[:3] == b'ID3' or   # MP3 with ID3
                audio_data[:2] == b'\xff\xfb'):  # MP3 without ID3
            return False, "Invalid audio format. Please provide WAV or MP3"
        
        return True, ""
    
    async def create_avatar(
        self,
        user_id: str,
        name: str,
        audio_samples: List[bytes],
        description: str = "",
        language: str = "en"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new voice avatar
        """
        try:
            # Validate samples
            if len(audio_samples) < self.MIN_SAMPLES_REQUIRED:
                return False, {
                    "error": f"Minimum {self.MIN_SAMPLES_REQUIRED} audio samples required",
                    "provided": len(audio_samples)
                }
            
            if len(audio_samples) > self.MAX_SAMPLES_PER_AVATAR:
                return False, {
                    "error": f"Maximum {self.MAX_SAMPLES_PER_AVATAR} audio samples allowed",
                    "provided": len(audio_samples)
                }
            
            # Validate each sample
            for idx, sample in enumerate(audio_samples):
                is_valid, error = self._validate_audio_sample(sample)
                if not is_valid:
                    return False, {
                        "error": f"Sample {idx + 1} validation failed: {error}"
                    }
            
            # Check user tier for locking status
            user_tier = self.subscription.get_user_tier(user_id)
            is_locked = (user_tier == SubscriptionTier.FREE)
            
            # Create avatar in database
            avatar = VoiceAvatar(
                owner_id=user_id,
                name=name,
                description=description,
                language=language,
                status=AvatarStatus.PROCESSING,
                is_locked=is_locked,  # Lock for free users
                preview_text="Hello! This is what your personalized voice avatar sounds like.",
                created_at=datetime.utcnow()
            )
            self.db.add(avatar)
            self.db.commit()
            
            # Clone voice with ElevenLabs
            if self.elevenlabs.is_available():
                try:
                    voice_id = await self.elevenlabs.clone_voice(
                        name=f"{user_id}_{name}",
                        audio_samples=audio_samples,
                        description=description
                    )
                    
                    if voice_id:
                        avatar.voice_id = voice_id
                        avatar.status = AvatarStatus.ACTIVE
                        avatar.provider = "elevenlabs"
                        avatar.preview_generated = True  # Mark preview as ready
                        
                        # Store voice characteristics
                        voice_info = await self.elevenlabs.get_voice(voice_id)
                        if voice_info:
                            avatar.voice_characteristics = {
                                "labels": voice_info.get("labels", {}),
                                "settings": voice_info.get("settings", {})
                            }
                    else:
                        avatar.status = AvatarStatus.FAILED
                        avatar.processing_error = "Failed to clone voice with ElevenLabs"
                    
                except Exception as e:
                    logger.error(f"ElevenLabs cloning failed: {e}")
                    avatar.status = AvatarStatus.FAILED
                    avatar.processing_error = str(e)
            else:
                # Fallback: Store samples locally
                logger.warning("ElevenLabs not available, storing samples locally")
                avatar.status = AvatarStatus.DRAFT
                
                # Store sample metadata
                sample_urls = []
                for idx, sample_data in enumerate(audio_samples):
                    # Generate unique filename
                    sample_hash = hashlib.sha256(sample_data).hexdigest()[:12]
                    filename = f"voice_samples/{user_id}/{avatar.id}/{sample_hash}.wav"
                    
                    # Store file path (actual file storage would be handled separately)
                    sample_urls.append(filename)
                    
                    # Create VoiceSample record
                    voice_sample = VoiceSample(
                        avatar_id=avatar.id,
                        file_url=filename,
                        duration_seconds=10.0,  # Would be calculated from actual audio
                        created_at=datetime.utcnow()
                    )
                    self.db.add(voice_sample)
                
                avatar.sample_urls = sample_urls
            
            # Update user stats
            user = self.db.query(User).filter_by(id=user_id).first()
            if user:
                user.total_voice_avatars += 1
            
            self.db.commit()
            
            logger.info(f"Created voice avatar {avatar.id} for user {user_id}")
            
            # Add FOMO message if avatar is locked
            response_data = {
                "avatar_id": avatar.id,
                "name": avatar.name,
                "status": avatar.status.value,
                "voice_id": avatar.voice_id,
                "provider": avatar.provider,
                "is_locked": avatar.is_locked,
                "created_at": avatar.created_at.isoformat()
            }
            
            if avatar.is_locked:
                response_data["premium_notice"] = {
                    "message": "🎉 Your voice avatar is ready!",
                    "details": "Your personalized AI voice has been created successfully.",
                    "cta": "Upgrade to Premium to start using it!",
                    "benefits": [
                        "Generate unlimited speech with your voice",
                        "Create up to 5 unique voice avatars",
                        "Priority support"
                    ]
                }
            
            return True, response_data
            
        except Exception as e:
            logger.error(f"Failed to create avatar: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    async def get_avatar(self, avatar_id: int) -> Optional[Dict[str, Any]]:
        """Get avatar details"""
        avatar = self.db.query(VoiceAvatar).filter_by(id=avatar_id).first()
        
        if not avatar:
            return None
        
        return {
            "id": avatar.id,
            "name": avatar.name,
            "description": avatar.description,
            "status": avatar.status.value,
            "voice_id": avatar.voice_id,
            "provider": avatar.provider,
            "language": avatar.language,
            "is_public": avatar.is_public,
            "is_default": avatar.is_default,
            "times_used": avatar.times_used,
            "created_at": avatar.created_at.isoformat(),
            "characteristics": avatar.voice_characteristics
        }
    
    async def list_user_avatars(
        self,
        user_id: str,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List all avatars for a user"""
        query = self.db.query(VoiceAvatar).filter_by(owner_id=user_id)
        
        if not include_archived:
            query = query.filter(VoiceAvatar.status != AvatarStatus.ARCHIVED)
        
        avatars = query.order_by(VoiceAvatar.created_at.desc()).all()
        
        return [
            {
                "id": avatar.id,
                "name": avatar.name,
                "description": avatar.description,
                "status": avatar.status.value,
                "voice_id": avatar.voice_id,
                "provider": avatar.provider,
                "is_default": avatar.is_default,
                "is_locked": avatar.is_locked,  # Include lock status
                "preview_generated": avatar.preview_generated,
                "times_used": avatar.times_used,
                "created_at": avatar.created_at.isoformat()
            }
            for avatar in avatars
        ]
    
    async def generate_speech(
        self,
        avatar_id: int,
        text: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Any]:
        """
        Generate speech using a voice avatar (Premium feature)
        """
        # Get avatar
        avatar = self.db.query(VoiceAvatar).filter_by(id=avatar_id).first()
        
        if not avatar:
            return False, {"error": "Avatar not found"}
        
        # Check permissions if user_id provided
        if user_id and avatar.owner_id != user_id and not avatar.is_public:
            return False, {"error": "Access denied to this avatar"}
        
        # Premium gating check
        if avatar.is_locked:
            # Check if user has upgraded
            can_use, access_info = self.subscription.check_voice_generation_access(avatar.owner_id)
            
            if not can_use:
                # Return premium gate message instead of error
                preview_info = self.subscription.generate_voice_preview(avatar.owner_id, avatar_id)
                return False, {
                    "error": "premium_required",
                    "locked": True,
                    "avatar_name": avatar.name,
                    "preview": preview_info.get("preview_message"),
                    "upgrade_prompt": preview_info.get("upgrade_prompt"),
                    "current_tier": access_info.get("current_tier"),
                    "upgrade_benefits": access_info.get("upgrade_benefits")
                }
        
        # Check avatar status
        if avatar.status != AvatarStatus.ACTIVE:
            return False, {
                "error": f"Avatar is not active (status: {avatar.status.value})"
            }
        
        # Generate speech using ElevenLabs
        if avatar.voice_id and self.elevenlabs.is_available():
            try:
                audio_data = await self.elevenlabs.generate_speech(
                    voice_id=avatar.voice_id,
                    text=text
                )
                
                if audio_data:
                    # Update usage stats
                    avatar.times_used += 1
                    avatar.total_characters += len(text)
                    avatar.last_used_at = datetime.utcnow()
                    self.db.commit()
                    
                    return True, {
                        "audio_data": audio_data,
                        "format": "mp3",
                        "avatar_id": avatar_id,
                        "characters": len(text)
                    }
                else:
                    return False, {"error": "Failed to generate speech"}
                    
            except Exception as e:
                logger.error(f"Speech generation failed: {e}")
                return False, {"error": str(e)}
        else:
            return False, {
                "error": "Voice generation service not available"
            }
    
    async def update_avatar(
        self,
        avatar_id: int,
        user_id: str,
        **updates
    ) -> Tuple[bool, Dict[str, Any]]:
        """Update avatar properties"""
        avatar = self.db.query(VoiceAvatar).filter_by(
            id=avatar_id,
            owner_id=user_id
        ).first()
        
        if not avatar:
            return False, {"error": "Avatar not found or access denied"}
        
        # Update allowed fields
        allowed_fields = [
            "name", "description", "is_public", 
            "is_default", "language"
        ]
        
        for field in allowed_fields:
            if field in updates:
                setattr(avatar, field, updates[field])
        
        # Handle default avatar
        if updates.get("is_default"):
            # Remove default from other avatars
            self.db.query(VoiceAvatar).filter(
                VoiceAvatar.owner_id == user_id,
                VoiceAvatar.id != avatar_id
            ).update({"is_default": False})
        
        avatar.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True, await self.get_avatar(avatar_id)
    
    async def archive_avatar(
        self,
        avatar_id: int,
        user_id: str
    ) -> Tuple[bool, str]:
        """Archive a voice avatar"""
        avatar = self.db.query(VoiceAvatar).filter_by(
            id=avatar_id,
            owner_id=user_id
        ).first()
        
        if not avatar:
            return False, "Avatar not found or access denied"
        
        avatar.status = AvatarStatus.ARCHIVED
        avatar.updated_at = datetime.utcnow()
        self.db.commit()
        
        # Delete from ElevenLabs if needed
        if avatar.voice_id and self.elevenlabs.is_available():
            try:
                await self.elevenlabs.delete_voice(avatar.voice_id)
            except Exception as e:
                logger.error(f"Failed to delete voice from ElevenLabs: {e}")
        
        return True, "Avatar archived successfully"
    
    async def get_voice_providers(self) -> Dict[str, bool]:
        """Get available voice providers and their status"""
        return {
            "elevenlabs": self.elevenlabs.is_available(),
            "azure": False,  # Could add Azure TTS
            "google": False,  # Could add Google TTS
            "aws": False,     # Could add AWS Polly
            "local": True     # Always available for storage
        }
    
    async def get_or_default_voice(
        self,
        user_id: str,
        avatar_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get user's voice preference or default wise man voice
        
        Returns voice configuration with ID and settings
        """
        # If specific avatar requested
        if avatar_id:
            avatar = self.db.query(VoiceAvatar).filter_by(
                id=avatar_id,
                owner_id=user_id
            ).first()
            
            if avatar and avatar.voice_id:
                return {
                    "voice_id": avatar.voice_id,
                    "voice_name": avatar.name,
                    "settings": self.default_voice["settings"],  # Use default settings
                    "is_cloned": True,
                    "avatar_id": avatar.id
                }
        
        # Check if user has a voice preference stored
        user_pref = self.voice_preferences.get(user_id)
        if user_pref:
            if user_pref == "default":
                return {
                    **self.default_voice,
                    "is_cloned": False
                }
            # Try to get user's preferred cloned voice
            avatar = self.db.query(VoiceAvatar).filter_by(
                id=user_pref,
                owner_id=user_id,
                status=AvatarStatus.ACTIVE
            ).first()
            
            if avatar and avatar.voice_id:
                return {
                    "voice_id": avatar.voice_id,
                    "voice_name": avatar.name,
                    "settings": self.default_voice["settings"],
                    "is_cloned": True,
                    "avatar_id": avatar.id
                }
        
        # Return default wise man voice
        return {
            **self.default_voice,
            "is_cloned": False
        }
    
    async def set_voice_preference(
        self,
        user_id: str,
        preference: str
    ) -> Tuple[bool, str]:
        """
        Set user's voice preference
        
        Args:
            user_id: User ID
            preference: "default" or avatar_id
        """
        if preference == "default":
            self.voice_preferences[user_id] = "default"
            return True, f"Voice set to default wise narrator: {self.default_voice['voice_name']}"
        
        try:
            avatar_id = int(preference)
            avatar = self.db.query(VoiceAvatar).filter_by(
                id=avatar_id,
                owner_id=user_id,
                status=AvatarStatus.ACTIVE
            ).first()
            
            if avatar:
                self.voice_preferences[user_id] = avatar_id
                return True, f"Voice set to your cloned avatar: {avatar.name}"
            else:
                return False, "Avatar not found or not active"
                
        except ValueError:
            return False, "Invalid preference. Use 'default' or a valid avatar ID"
    
    async def generate_speech_with_fallback(
        self,
        text: str,
        user_id: str,
        avatar_id: Optional[int] = None
    ) -> Tuple[bool, Any]:
        """
        Generate speech with automatic fallback to default voice
        """
        if not self.elevenlabs.is_available():
            return False, {"error": "Voice service not available"}
        
        # Get voice configuration
        voice_config = await self.get_or_default_voice(user_id, avatar_id)
        
        try:
            # Try to generate speech with selected voice
            from .elevenlabs_service import VoiceSettings
            settings = VoiceSettings(
                stability=voice_config["settings"]["stability"],
                similarity_boost=voice_config["settings"]["similarity_boost"],
                style=voice_config["settings"]["style"],
                use_speaker_boost=voice_config["settings"]["use_speaker_boost"]
            )
            
            audio_data = await self.elevenlabs.text_to_speech(
                text=text,
                voice_id=voice_config["voice_id"],
                settings=settings,
                model_id=TTS_CONFIG["default_model"]
            )
            
            if audio_data:
                # Update usage stats if using cloned voice
                if voice_config.get("is_cloned") and voice_config.get("avatar_id"):
                    avatar = self.db.query(VoiceAvatar).filter_by(
                        id=voice_config["avatar_id"]
                    ).first()
                    if avatar:
                        avatar.times_used += 1
                        avatar.total_characters += len(text)
                        avatar.last_used_at = datetime.utcnow()
                        self.db.commit()
                
                return True, {
                    "audio_data": audio_data,
                    "format": "mp3",
                    "voice_name": voice_config["voice_name"],
                    "is_cloned": voice_config.get("is_cloned", False),
                    "characters": len(text)
                }
            
            # If failed and using cloned voice, try default
            if voice_config.get("is_cloned") and VOICE_SWITCH_CONFIG["default_on_error"]:
                logger.warning(f"Cloned voice failed, falling back to default wise narrator")
                
                audio_data = await self.elevenlabs.text_to_speech(
                    text=text,
                    voice_id=self.default_voice["voice_id"],
                    settings=settings,
                    model_id=TTS_CONFIG["default_model"]
                )
                
                if audio_data:
                    return True, {
                        "audio_data": audio_data,
                        "format": "mp3",
                        "voice_name": self.default_voice["voice_name"],
                        "is_cloned": False,
                        "fallback": True,
                        "characters": len(text)
                    }
            
            return False, {"error": "Failed to generate speech"}
            
        except Exception as e:
            logger.error(f"Speech generation error: {e}")
            
            # Try fallback to default voice on any error
            if VOICE_SWITCH_CONFIG["default_on_error"]:
                try:
                    from .elevenlabs_service import VoiceSettings
                    settings = VoiceSettings(**self.default_voice["settings"])
                    
                    audio_data = await self.elevenlabs.text_to_speech(
                        text=text,
                        voice_id=self.default_voice["voice_id"],
                        settings=settings,
                        model_id=TTS_CONFIG["default_model"]
                    )
                    
                    if audio_data:
                        return True, {
                            "audio_data": audio_data,
                            "format": "mp3",
                            "voice_name": self.default_voice["voice_name"],
                            "is_cloned": False,
                            "fallback": True,
                            "error_fallback": str(e),
                            "characters": len(text)
                        }
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
            
            return False, {"error": str(e)}
    
    async def process_whatsapp_voice_command(
        self,
        user_id: str,
        command: str,
        args: List[str]
    ) -> str:
        """Process voice-related WhatsApp commands"""
        if command == "/voice_list":
            avatars = await self.list_user_avatars(user_id)
            
            if not avatars:
                return "🎭 No voice avatars yet. Earn credits by inviting friends!"
            
            response = "🎭 Your Voice Avatars:\n"
            response += "═══════════════════\n"
            
            for avatar in avatars:
                status_emoji = {
                    "active": "✅",
                    "processing": "⏳",
                    "draft": "📝",
                    "failed": "❌"
                }.get(avatar['status'], "❓")
                
                response += (
                    f"{status_emoji} {avatar['name']}\n"
                    f"  ID: {avatar['id']}\n"
                    f"  Used: {avatar['times_used']} times\n"
                )
            
            return response
        
        elif command == "/voice_create":
            # This would need audio samples, so guide user
            return (
                "🎭 Voice Avatar Creation\n"
                "════════════════════\n"
                "To create a voice avatar:\n\n"
                "1. Record 3-5 voice samples (3-60 seconds each)\n"
                "2. Send them as voice messages\n"
                "3. Use command: /voice_finalize NAME\n\n"
                "💡 Tip: Speak naturally and clearly!\n"
                "📍 Note: You need avatar credits (5 invites = 1 credit)"
            )
        
        else:
            return (
                "🎭 Voice Commands:\n"
                "════════════════\n"
                "/voice_list - List your avatars\n"
                "/voice_create - Create new avatar\n"
                "/voice_info ID - Avatar details"
            )