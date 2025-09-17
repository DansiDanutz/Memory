#!/usr/bin/env python3
"""
Voice Transcription Module - Speech-to-Text for WhatsApp voice messages
Handles audio format conversion and transcription using Azure Speech SDK or OpenAI Whisper
"""

import os
import tempfile
import logging
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import requests
from pydub import AudioSegment
import soundfile as sf
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Speech SDK
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("⚠️ Azure Speech SDK not available, will use OpenAI Whisper")

# OpenAI SDK for Whisper fallback
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ OpenAI SDK not available")

class VoiceTranscriber:
    """Handles audio transcription for WhatsApp voice messages"""
    
    def __init__(self):
        self.azure_key = os.environ.get('AZURE_SPEECH_KEY')
        self.azure_region = os.environ.get('AZURE_SPEECH_REGION', 'eastus')
        self.openai_key = os.environ.get('OPENAI_API_KEY')
        self.voice_enabled = os.environ.get('VOICE_ENABLED', 'true').lower() == 'true'
        
        # Initialize Azure Speech if available
        if AZURE_AVAILABLE and self.azure_key:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.azure_key,
                region=self.azure_region
            )
            # Set recognition language
            self.speech_config.speech_recognition_language = "en-US"
            logger.info("✅ Azure Speech SDK initialized for transcription")
        else:
            self.speech_config = None
            
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
            logger.info("✅ OpenAI Whisper available as fallback")
        else:
            self.openai_client = None
    
    def download_audio(self, media_url: str, access_token: str) -> Optional[bytes]:
        """
        Download audio file from WhatsApp Media API
        
        Args:
            media_url: URL to download the media
            access_token: Bearer token for authentication
            
        Returns:
            Audio file bytes or None if failed
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(media_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ Downloaded audio file ({len(response.content)} bytes)")
            return response.content
            
        except Exception as e:
            logger.error(f"❌ Failed to download audio: {e}")
            return None
    
    def convert_to_wav(self, audio_data: bytes, source_format: str = 'ogg') -> Optional[bytes]:
        """
        Convert audio from OGG/Opus to WAV format (16kHz, mono)
        
        Args:
            audio_data: Raw audio bytes
            source_format: Source format (ogg, opus, mp3, etc.)
            
        Returns:
            WAV audio bytes or None if failed
        """
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=f'.{source_format}', delete=False) as src_file:
                src_file.write(audio_data)
                src_path = src_file.name
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                wav_path = wav_file.name
            
            # Load audio with pydub
            audio = AudioSegment.from_file(src_path, format=source_format)
            
            # Convert to mono 16kHz WAV
            audio = audio.set_channels(1)  # Mono
            audio = audio.set_frame_rate(16000)  # 16kHz
            audio = audio.set_sample_width(2)  # 16-bit
            
            # Export as WAV
            audio.export(wav_path, format='wav')
            
            # Read WAV file
            with open(wav_path, 'rb') as f:
                wav_data = f.read()
            
            # Clean up temp files
            os.unlink(src_path)
            os.unlink(wav_path)
            
            logger.info(f"✅ Converted audio to WAV (16kHz, mono, {len(wav_data)} bytes)")
            return wav_data
            
        except Exception as e:
            logger.error(f"❌ Failed to convert audio: {e}")
            # Clean up temp files if they exist
            for path in [src_path, wav_path]:
                if 'path' in locals() and os.path.exists(path):
                    os.unlink(path)
            return None
    
    def transcribe_with_azure(self, wav_data: bytes) -> Optional[str]:
        """
        Transcribe audio using Azure Speech SDK
        
        Args:
            wav_data: WAV audio bytes (16kHz, mono)
            
        Returns:
            Transcribed text or None if failed
        """
        if not self.speech_config:
            return None
        
        try:
            # Create temporary WAV file for Azure
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                wav_file.write(wav_data)
                wav_path = wav_file.name
            
            # Create audio config from file
            audio_config = speechsdk.AudioConfig(filename=wav_path)
            
            # Create recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Perform recognition
            result = recognizer.recognize_once()
            
            # Clean up temp file
            os.unlink(wav_path)
            
            # Check result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info(f"✅ Azure transcription: {result.text}")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("⚠️ Azure: No speech could be recognized")
                return None
            else:
                logger.error(f"❌ Azure transcription failed: {result.reason}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Azure transcription error: {e}")
            # Clean up temp file if it exists
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.unlink(wav_path)
            return None
    
    def transcribe_with_whisper(self, wav_data: bytes) -> Optional[str]:
        """
        Transcribe audio using OpenAI Whisper API
        
        Args:
            wav_data: WAV audio bytes
            
        Returns:
            Transcribed text or None if failed
        """
        if not self.openai_client:
            return None
        
        try:
            # Create temporary WAV file for Whisper
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_file:
                wav_file.write(wav_data)
                wav_path = wav_file.name
            
            # Open file for Whisper API
            with open(wav_path, 'rb') as audio_file:
                # Call Whisper API
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            # Clean up temp file
            os.unlink(wav_path)
            
            # Get transcription
            text = response.text
            logger.info(f"✅ Whisper transcription: {text}")
            return text
            
        except Exception as e:
            logger.error(f"❌ Whisper transcription error: {e}")
            # Clean up temp file if it exists
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.unlink(wav_path)
            return None
    
    def transcribe_audio(self, audio_data: bytes, source_format: str = 'ogg') -> Tuple[bool, Optional[str]]:
        """
        Main transcription method - converts audio and transcribes
        
        Args:
            audio_data: Raw audio bytes
            source_format: Source format (ogg, opus, mp3, etc.)
            
        Returns:
            Tuple of (success, transcribed_text)
        """
        if not self.voice_enabled:
            logger.warning("⚠️ Voice transcription disabled")
            return (False, None)
        
        # Convert to WAV
        wav_data = self.convert_to_wav(audio_data, source_format)
        if not wav_data:
            return (False, None)
        
        # Try Azure first
        text = self.transcribe_with_azure(wav_data)
        
        # Fall back to Whisper if Azure fails
        if not text:
            text = self.transcribe_with_whisper(wav_data)
        
        if text:
            return (True, text)
        else:
            logger.error("❌ All transcription methods failed")
            return (False, None)
    
    def process_voice_command(self, text: str) -> Dict[str, Any]:
        """
        Process transcribed text for commands or queries
        
        Args:
            text: Transcribed text
            
        Returns:
            Dict with command type and parameters
        """
        text_lower = text.lower().strip()
        
        # Check for verification command
        if text_lower.startswith('verify:') or text_lower.startswith('verify '):
            # Extract passphrase
            passphrase = text[7:].strip() if ':' in text else text[6:].strip()
            return {
                'type': 'verify',
                'passphrase': passphrase,
                'original_text': text
            }
        
        # Check for enrollment command
        if text_lower.startswith('enroll:') or text_lower.startswith('enroll '):
            # Extract passphrase
            passphrase = text[7:].strip() if ':' in text else text[6:].strip()
            return {
                'type': 'enroll',
                'passphrase': passphrase,
                'original_text': text
            }
        
        # Check for search command
        if text_lower.startswith('search:') or text_lower.startswith('search '):
            # Extract query
            query = text[7:].strip() if ':' in text else text[6:].strip()
            return {
                'type': 'search',
                'query': query,
                'original_text': text
            }
        
        # Default to search query
        return {
            'type': 'search',
            'query': text,
            'original_text': text
        }

# Create global instance
voice_transcriber = VoiceTranscriber()