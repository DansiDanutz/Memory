#!/usr/bin/env python3
"""
Voice Synthesis Module - Text-to-Speech for WhatsApp voice responses
Generates audio responses using Azure Speech SDK or OpenAI TTS
"""

import os
import tempfile
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import requests
from pydub import AudioSegment
import base64

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Speech SDK
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("⚠️ Azure Speech SDK not available, will use OpenAI TTS")

# OpenAI SDK for TTS
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ OpenAI SDK not available")

class VoiceSynthesizer:
    """Handles text-to-speech synthesis for WhatsApp voice responses"""
    
    # Voice profiles for different response types
    VOICE_PROFILES = {
        'friendly': {
            'azure': 'en-US-JennyNeural',
            'openai': 'nova',
            'style': 'friendly'
        },
        'professional': {
            'azure': 'en-US-AriaNeural',
            'openai': 'alloy',
            'style': 'professional'
        },
        'excited': {
            'azure': 'en-US-GuyNeural',
            'openai': 'echo',
            'style': 'excited'
        },
        'calm': {
            'azure': 'en-US-AmberNeural',
            'openai': 'shimmer',
            'style': 'calm'
        }
    }
    
    def __init__(self):
        self.azure_key = os.environ.get('AZURE_SPEECH_KEY')
        self.azure_region = os.environ.get('AZURE_SPEECH_REGION', 'eastus')
        self.openai_key = os.environ.get('OPENAI_API_KEY')
        self.voice_enabled = os.environ.get('VOICE_ENABLED', 'true').lower() == 'true'
        self.default_voice = 'friendly'
        
        # Initialize Azure Speech if available
        if AZURE_AVAILABLE and self.azure_key:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.azure_key,
                region=self.azure_region
            )
            # Set synthesis voice
            self.speech_config.speech_synthesis_voice_name = self.VOICE_PROFILES[self.default_voice]['azure']
            logger.info("✅ Azure Speech SDK initialized for synthesis")
        else:
            self.speech_config = None
            
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
            logger.info("✅ OpenAI TTS available for synthesis")
        else:
            self.openai_client = None
    
    def detect_response_mood(self, text: str) -> str:
        """
        Detect the mood of the response to select appropriate voice
        
        Args:
            text: Text to analyze
            
        Returns:
            Voice profile name
        """
        text_lower = text.lower()
        
        # Check for different moods
        if any(word in text_lower for word in ['congratulations', 'amazing', 'fantastic', 'great job']):
            return 'excited'
        elif any(word in text_lower for word in ['error', 'failed', 'invalid', 'incorrect']):
            return 'calm'
        elif any(word in text_lower for word in ['verified', 'granted', 'successful', 'unlocked']):
            return 'professional'
        else:
            return 'friendly'
    
    def synthesize_with_azure(self, text: str, voice_profile: str = 'friendly') -> Optional[bytes]:
        """
        Generate speech using Azure Speech SDK
        
        Args:
            text: Text to synthesize
            voice_profile: Voice profile to use
            
        Returns:
            Audio bytes (OGG format) or None if failed
        """
        if not self.speech_config:
            return None
        
        try:
            # Set voice for this synthesis
            voice_name = self.VOICE_PROFILES[voice_profile]['azure']
            self.speech_config.speech_synthesis_voice_name = voice_name
            
            # Configure output format to OGG Opus (WhatsApp compatible)
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Ogg24Khz16BitMonoOpus
            )
            
            # Create synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # We'll get audio data directly
            )
            
            # Add SSML for better expression
            ssml = f"""
            <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
                <voice name='{voice_name}'>
                    <prosody rate='1.0' pitch='0%'>
                        {text}
                    </prosody>
                </voice>
            </speak>
            """
            
            # Synthesize
            result = synthesizer.speak_ssml_async(ssml).get()
            
            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                logger.info(f"✅ Azure synthesis completed ({len(audio_data)} bytes)")
                return audio_data
            else:
                logger.error(f"❌ Azure synthesis failed: {result.reason}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Azure synthesis error: {e}")
            return None
    
    def synthesize_with_openai(self, text: str, voice_profile: str = 'friendly') -> Optional[bytes]:
        """
        Generate speech using OpenAI TTS API
        
        Args:
            text: Text to synthesize
            voice_profile: Voice profile to use
            
        Returns:
            Audio bytes (OGG format) or None if failed
        """
        if not self.openai_client:
            return None
        
        try:
            # Get voice for this profile
            voice = self.VOICE_PROFILES[voice_profile]['openai']
            
            # Call OpenAI TTS API
            response = self.openai_client.audio.speech.create(
                model="tts-1",  # or "tts-1-hd" for higher quality
                voice=voice,
                input=text,
                response_format="opus"  # WhatsApp compatible format
            )
            
            # Get audio data
            audio_data = response.content
            logger.info(f"✅ OpenAI TTS completed ({len(audio_data)} bytes)")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ OpenAI TTS error: {e}")
            return None
    
    def convert_to_ogg(self, audio_data: bytes, source_format: str = 'mp3') -> Optional[bytes]:
        """
        Convert audio to OGG/Opus format for WhatsApp
        
        Args:
            audio_data: Raw audio bytes
            source_format: Source format
            
        Returns:
            OGG audio bytes or None if failed
        """
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=f'.{source_format}', delete=False) as src_file:
                src_file.write(audio_data)
                src_path = src_file.name
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as ogg_file:
                ogg_path = ogg_file.name
            
            # Load audio with pydub
            audio = AudioSegment.from_file(src_path, format=source_format)
            
            # Export as OGG
            audio.export(ogg_path, format='ogg', codec='libopus', parameters=['-b:a', '64k'])
            
            # Read OGG file
            with open(ogg_path, 'rb') as f:
                ogg_data = f.read()
            
            # Clean up temp files
            os.unlink(src_path)
            os.unlink(ogg_path)
            
            logger.info(f"✅ Converted to OGG/Opus ({len(ogg_data)} bytes)")
            return ogg_data
            
        except Exception as e:
            logger.error(f"❌ Failed to convert to OGG: {e}")
            # Clean up temp files if they exist
            for path in [src_path, ogg_path]:
                if 'path' in locals() and os.path.exists(path):
                    os.unlink(path)
            return None
    
    def synthesize_speech(self, text: str, auto_detect_mood: bool = True) -> Tuple[bool, Optional[bytes]]:
        """
        Main synthesis method - generates speech from text
        
        Args:
            text: Text to synthesize
            auto_detect_mood: Whether to automatically detect mood for voice selection
            
        Returns:
            Tuple of (success, audio_bytes)
        """
        if not self.voice_enabled:
            logger.warning("⚠️ Voice synthesis disabled")
            return (False, None)
        
        # Detect mood for voice selection
        if auto_detect_mood:
            voice_profile = self.detect_response_mood(text)
        else:
            voice_profile = self.default_voice
        
        logger.info(f"🎭 Using voice profile: {voice_profile}")
        
        # Try Azure first
        audio_data = self.synthesize_with_azure(text, voice_profile)
        
        # Fall back to OpenAI if Azure fails
        if not audio_data:
            audio_data = self.synthesize_with_openai(text, voice_profile)
        
        if audio_data:
            return (True, audio_data)
        else:
            logger.error("❌ All synthesis methods failed")
            return (False, None)
    
    def upload_to_whatsapp(self, audio_data: bytes, access_token: str, phone_number_id: str) -> Optional[str]:
        """
        Upload audio to WhatsApp Media API
        
        Args:
            audio_data: Audio bytes to upload
            access_token: Bearer token for authentication
            phone_number_id: WhatsApp Business phone number ID
            
        Returns:
            Media ID or None if failed
        """
        try:
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
            
            # Prepare multipart form data
            files = {
                'file': ('voice_response.ogg', audio_data, 'audio/ogg'),
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'type': 'audio/ogg'
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Upload media
            response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            media_id = result.get('id')
            
            if media_id:
                logger.info(f"✅ Audio uploaded to WhatsApp: {media_id}")
                return media_id
            else:
                logger.error(f"❌ No media ID in response: {result}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to upload audio to WhatsApp: {e}")
            return None
    
    def create_voice_response(self, text: str, recipient_name: Optional[str] = None) -> str:
        """
        Create a personalized voice response text
        
        Args:
            text: Base response text
            recipient_name: Optional recipient name for personalization
            
        Returns:
            Personalized response text
        """
        # Add personalization if name is available
        if recipient_name:
            # Add greeting with name
            if not text.startswith(('Hello', 'Hi', 'Hey')):
                text = f"Hello {recipient_name}, {text}"
        
        # Ensure proper ending
        if not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text

# Create global instance
voice_synthesizer = VoiceSynthesizer()