"""
WhatsApp Voice Collector Service
Automatically collects and stores voice messages for voice cloning
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.voice.whatsapp_media import download_media, ogg_opus_to_wav
from app.voice.transcription import voice_transcriber
from app.gamification.voice_sample_storage import VoiceSampleStorage
from app.gamification.database_models import SessionLocal

logger = logging.getLogger(__name__)

class WhatsAppVoiceCollector:
    """
    Service to automatically collect and store WhatsApp voice messages
    for ElevenLabs voice cloning
    """
    
    def __init__(self):
        """Initialize the voice collector"""
        self.voice_storage = VoiceSampleStorage()
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.enabled = os.getenv("VOICE_COLLECTION_ENABLED", "true").lower() == "true"
        
        # Track user consent for voice collection
        self.user_consents = {}  # {user_id: bool}
        
        logger.info(f"✅ WhatsApp Voice Collector initialized (enabled: {self.enabled})")
    
    def check_user_consent(self, user_id: str) -> bool:
        """
        Check if user has consented to voice collection
        For now, we'll assume consent is given by default (can be changed)
        """
        # In production, you might want to:
        # 1. Ask for explicit consent first time
        # 2. Store consent in database
        # 3. Allow users to opt-out
        
        if user_id not in self.user_consents:
            # Default to True for now, but you can change this
            # to require explicit consent
            self.user_consents[user_id] = True
        
        return self.user_consents[user_id]
    
    async def process_voice_message(
        self,
        from_number: str,
        message: Dict[str, Any],
        auto_clone: bool = True
    ) -> Dict[str, Any]:
        """
        Process an incoming WhatsApp voice message
        
        Args:
            from_number: Sender's phone number
            message: WhatsApp message object
            auto_clone: Whether to automatically trigger cloning when ready
            
        Returns:
            Processing result with status and details
        """
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "Voice collection is disabled"
            }
        
        # Check user consent
        if not self.check_user_consent(from_number):
            return {
                "status": "no_consent",
                "message": "User has not consented to voice collection"
            }
        
        try:
            # Extract audio information
            audio_data = None
            media_id = None
            
            if message.get("type") == "audio":
                # Voice note (audio type)
                media_id = message.get("audio", {}).get("id")
            elif message.get("type") == "voice":
                # Voice message (voice type)
                media_id = message.get("voice", {}).get("id")
            else:
                return {
                    "status": "invalid_type",
                    "message": f"Not a voice message: {message.get('type')}"
                }
            
            if not media_id:
                return {
                    "status": "error",
                    "message": "No media ID found in message"
                }
            
            # Download the audio file
            logger.info(f"Downloading voice message {media_id} from {from_number}")
            audio_data = download_media(media_id, self.access_token)
            
            if not audio_data:
                return {
                    "status": "error",
                    "message": "Failed to download voice message"
                }
            
            # Convert to WAV format
            logger.info(f"Converting voice message to WAV format")
            wav_path = ogg_opus_to_wav(audio_data)
            
            # Read the converted WAV file
            with open(wav_path, 'rb') as f:
                wav_data = f.read()
            
            # Clean up temporary file
            os.unlink(wav_path)
            
            # Store the voice sample
            logger.info(f"Storing voice sample for {from_number}")
            success, result = self.voice_storage.store_voice_sample(
                user_id=from_number,
                audio_data=wav_data,
                source="whatsapp",
                metadata={
                    "message_id": message.get("id"),
                    "media_id": media_id,
                    "timestamp": message.get("timestamp", datetime.utcnow().isoformat()),
                    "mime_type": message.get("audio", {}).get("mime_type") or message.get("voice", {}).get("mime_type")
                }
            )
            
            if not success:
                return {
                    "status": "storage_failed",
                    "message": "Failed to store voice sample",
                    "details": result
                }
            
            # Get user progress
            progress = self.voice_storage.get_user_progress(from_number)
            
            # Prepare response
            response = {
                "status": "success",
                "sample_id": result.get("sample_id"),
                "duration": result.get("duration"),
                "quality_score": result.get("quality_score"),
                "progress": {
                    "total_samples": progress.total_samples,
                    "total_duration": progress.total_duration_formatted,
                    "instant_ready": progress.instant_clone_ready,
                    "instant_progress": progress.instant_clone_progress,
                    "professional_ready": progress.professional_clone_ready,
                    "professional_progress": progress.professional_clone_progress
                }
            }
            
            # Check if we should auto-trigger cloning
            if auto_clone and result.get("clone_ready"):
                clone_type = result.get("clone_type")
                logger.info(f"Auto-triggering {clone_type} voice cloning for {from_number}")
                
                clone_success, clone_result = await self.voice_storage.trigger_voice_cloning(
                    user_id=from_number,
                    clone_type=clone_type
                )
                
                if clone_success:
                    response["clone_triggered"] = True
                    response["clone_details"] = clone_result
                    response["message"] = f"🎉 Voice cloning triggered! Your {clone_type} voice avatar is being created."
                else:
                    response["clone_triggered"] = False
                    response["clone_error"] = clone_result
            
            # Add progress message for user
            if progress.instant_clone_ready and not progress.professional_clone_ready:
                response["user_message"] = (
                    f"✅ You can create an instant voice clone now! "
                    f"Keep sending voice messages to unlock professional cloning "
                    f"({progress.duration_needed_professional / 60:.0f} more minutes needed)."
                )
            elif not progress.instant_clone_ready:
                response["user_message"] = (
                    f"📊 Voice sample saved! Progress: {progress.instant_clone_progress:.0f}%\n"
                    f"Send {progress.samples_needed_instant} more voice messages to enable voice cloning."
                )
            elif progress.professional_clone_ready:
                response["user_message"] = "🏆 You have enough samples for professional voice cloning!"
            
            # Optionally transcribe the audio for additional features
            if os.getenv("TRANSCRIBE_VOICE_SAMPLES", "false").lower() == "true":
                success, transcript = voice_transcriber.transcribe_audio(audio_data, "ogg")
                if success and transcript:
                    response["transcript"] = transcript
            
            logger.info(f"✅ Successfully processed voice message for {from_number}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_collection_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get voice collection statistics for a user
        """
        progress = self.voice_storage.get_user_progress(user_id)
        
        return {
            "user_id": user_id,
            "total_samples": progress.total_samples,
            "total_duration": progress.total_duration_formatted,
            "quality_score": progress.quality_score,
            "instant_clone": {
                "ready": progress.instant_clone_ready,
                "progress": progress.instant_clone_progress,
                "samples_needed": progress.samples_needed_instant
            },
            "professional_clone": {
                "ready": progress.professional_clone_ready,
                "progress": progress.professional_clone_progress,
                "duration_needed_minutes": progress.duration_needed_professional / 60
            },
            "recommendations": progress.recommendations,
            "recent_samples": progress.recent_samples
        }
    
    def set_user_consent(self, user_id: str, consent: bool):
        """
        Set user consent for voice collection
        """
        self.user_consents[user_id] = consent
        logger.info(f"User {user_id} consent for voice collection: {consent}")
        
        # In production, you'd want to persist this to database
        # For now, it's just in memory
    
    async def send_progress_update(self, user_id: str) -> str:
        """
        Generate a progress update message for the user
        """
        progress = self.voice_storage.get_user_progress(user_id)
        
        if progress.total_samples == 0:
            return (
                "🎤 Welcome to Voice Avatar Creation!\n\n"
                "Send me voice messages and I'll help you create your personal voice avatar.\n"
                "I need at least 1 minute of clear audio to get started."
            )
        
        message_parts = [
            f"📊 *Voice Collection Progress*\n",
            f"Samples collected: {progress.total_samples}",
            f"Total duration: {progress.total_duration_formatted}",
            f"Average quality: {progress.quality_score:.0f}/100\n"
        ]
        
        if progress.instant_clone_ready:
            message_parts.append("✅ *Instant Voice Clone: READY*")
        else:
            message_parts.append(
                f"⏳ *Instant Voice Clone: {progress.instant_clone_progress:.0f}%*\n"
                f"   Need {progress.samples_needed_instant} more samples"
            )
        
        if progress.professional_clone_ready:
            message_parts.append("✅ *Professional Voice Clone: READY*")
        else:
            message_parts.append(
                f"⏳ *Professional Voice Clone: {progress.professional_clone_progress:.0f}%*\n"
                f"   Need {progress.duration_needed_professional / 60:.0f} more minutes"
            )
        
        if progress.recommendations:
            message_parts.append("\n💡 *Tips:*")
            for rec in progress.recommendations[:2]:  # Show max 2 recommendations
                message_parts.append(f"• {rec}")
        
        return "\n".join(message_parts)

# Create global instance
voice_collector = WhatsAppVoiceCollector()