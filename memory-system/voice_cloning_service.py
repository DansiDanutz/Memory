#!/usr/bin/env python3
"""
AI Voice Cloning Service - Talk to Yourself!
Enables users to have conversations with an AI assistant using their own voice
Supports multiple providers: ElevenLabs, Play.ht, Resemble AI, and Demo Mode
"""

import os
import json
import time
import hashlib
import base64
import wave
import struct
import random
import asyncio
import tempfile
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
import requests
from pathlib import Path

# Audio processing
try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    logging.warning("⚠️ librosa/soundfile not available - audio processing limited")

# Import OpenAI for ElevenLabs-compatible API
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceProvider(Enum):
    """Supported voice cloning providers"""
    DEMO = "demo"  # Local demo mode with pre-recorded samples
    ELEVENLABS = "elevenlabs"  # Best quality, 60s sample
    PLAYHT = "playht"  # Good value, 30s sample
    RESEMBLE = "resemble"  # Fastest, 10s sample
    OPENVOICE = "openvoice"  # Open-source alternative
    TORTOISE = "tortoise"  # Open-source high quality

class VoiceCloneStatus(Enum):
    """Status of voice clone"""
    NOT_STARTED = "not_started"
    COLLECTING_SAMPLES = "collecting_samples"
    PROCESSING = "processing"
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"
    DEMO_MODE = "demo_mode"

class VoiceQuality(Enum):
    """Voice synthesis quality levels"""
    DRAFT = "draft"  # Fast, lower quality
    STANDARD = "standard"  # Balanced
    PREMIUM = "premium"  # Best quality, slower
    REALTIME = "realtime"  # Optimized for conversations

class ConversationStyle(Enum):
    """AI conversation personality styles"""
    SUPPORTIVE = "supportive"  # Encouraging and helpful
    ANALYTICAL = "analytical"  # Logical and detailed
    CREATIVE = "creative"  # Imaginative and inspiring
    COACHING = "coaching"  # Motivational and goal-oriented
    REFLECTIVE = "reflective"  # Thoughtful and introspective
    HUMOROUS = "humorous"  # Light-hearted and fun

@dataclass
class VoiceProfile:
    """User's voice profile for cloning"""
    profile_id: str
    user_id: str
    name: str
    provider: VoiceProvider
    status: VoiceCloneStatus
    voice_id: Optional[str] = None  # Provider-specific voice ID
    samples_collected: int = 0
    samples_required: int = 3
    total_duration_seconds: float = 0.0
    min_duration_required: float = 10.0  # Minimum seconds needed
    quality_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    trained_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_ready(self) -> bool:
        """Check if voice profile is ready for synthesis"""
        return (
            self.status == VoiceCloneStatus.READY or
            (self.status == VoiceCloneStatus.DEMO_MODE and self.provider == VoiceProvider.DEMO)
        )
    
    def can_train(self) -> bool:
        """Check if enough samples collected for training"""
        return (
            self.samples_collected >= self.samples_required and
            self.total_duration_seconds >= self.min_duration_required
        )

@dataclass
class VoiceSample:
    """Individual voice sample for training"""
    sample_id: str
    profile_id: str
    user_id: str
    file_path: str
    duration_seconds: float
    transcript: Optional[str] = None
    quality_score: float = 0.0
    sample_rate: int = 16000
    format: str = "wav"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SynthesisRequest:
    """Request for voice synthesis"""
    text: str
    profile_id: str
    user_id: str
    quality: VoiceQuality = VoiceQuality.STANDARD
    speed: float = 1.0  # 0.5 to 2.0
    pitch: float = 1.0  # 0.5 to 2.0
    emotion: Optional[str] = None  # happy, sad, excited, calm, etc.
    style: ConversationStyle = ConversationStyle.SUPPORTIVE
    cache_result: bool = True
    stream: bool = False

@dataclass
class SynthesisResult:
    """Result of voice synthesis"""
    request_id: str
    profile_id: str
    audio_url: Optional[str] = None
    audio_data: Optional[bytes] = None
    duration_seconds: float = 0.0
    characters_used: int = 0
    provider: VoiceProvider = VoiceProvider.DEMO
    cached: bool = False
    synthesis_time_ms: int = 0
    error: Optional[str] = None

@dataclass
class SelfConversation:
    """A conversation between user and their AI voice twin"""
    conversation_id: str
    user_id: str
    profile_id: str
    style: ConversationStyle
    topic: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    insights_generated: List[str] = field(default_factory=list)
    
    def add_message(self, role: str, content: str, audio_url: Optional[str] = None):
        """Add a message to the conversation"""
        self.messages.append({
            "role": role,  # "user" or "ai_twin"
            "content": content,
            "audio_url": audio_url,
            "timestamp": datetime.now().isoformat()
        })

class VoiceCloningService:
    """Main service for AI voice cloning and self-conversations"""
    
    def __init__(self):
        """Initialize voice cloning service"""
        self.profiles: Dict[str, VoiceProfile] = {}
        self.samples: Dict[str, List[VoiceSample]] = {}
        self.conversations: Dict[str, SelfConversation] = {}
        self.synthesis_cache: Dict[str, SynthesisResult] = {}
        
        # Provider configurations
        self.providers = self._init_providers()
        
        # Storage paths
        self.base_path = Path("memory-system/voice_data")
        self.samples_path = self.base_path / "samples"
        self.models_path = self.base_path / "models"
        self.synthesis_path = self.base_path / "synthesis"
        self.demo_path = self.base_path / "demo_voices"
        
        # Create directories
        for path in [self.samples_path, self.models_path, self.synthesis_path, self.demo_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Initialize demo voices
        self._init_demo_voices()
        
        logger.info("🎤 Voice Cloning Service initialized - Talk to yourself!")
    
    def _init_providers(self) -> Dict[VoiceProvider, Any]:
        """Initialize voice cloning providers"""
        providers = {}
        
        # ElevenLabs
        if os.environ.get("ELEVENLABS_API_KEY"):
            providers[VoiceProvider.ELEVENLABS] = {
                "api_key": os.environ.get("ELEVENLABS_API_KEY"),
                "base_url": "https://api.elevenlabs.io/v1",
                "min_sample_duration": 60,
                "max_sample_duration": 300
            }
            logger.info("✅ ElevenLabs voice cloning enabled")
        
        # Play.ht
        if os.environ.get("PLAYHT_API_KEY"):
            providers[VoiceProvider.PLAYHT] = {
                "api_key": os.environ.get("PLAYHT_API_KEY"),
                "user_id": os.environ.get("PLAYHT_USER_ID"),
                "base_url": "https://api.play.ht/api/v2",
                "min_sample_duration": 30,
                "max_sample_duration": 180
            }
            logger.info("✅ Play.ht voice cloning enabled")
        
        # Resemble AI
        if os.environ.get("RESEMBLE_API_KEY"):
            providers[VoiceProvider.RESEMBLE] = {
                "api_key": os.environ.get("RESEMBLE_API_KEY"),
                "base_url": "https://app.resemble.ai/api/v2",
                "min_sample_duration": 10,
                "max_sample_duration": 60
            }
            logger.info("✅ Resemble AI voice cloning enabled")
        
        # Demo mode (always available)
        providers[VoiceProvider.DEMO] = {
            "enabled": True,
            "demo_voices": ["enthusiastic", "calm", "professional", "friendly"]
        }
        logger.info("🎭 Demo mode enabled for voice cloning")
        
        return providers
    
    def _init_demo_voices(self):
        """Initialize demo voice samples"""
        demo_phrases = [
            "Hello! I'm your AI voice twin. Let's have a conversation!",
            "I've been thinking about what you told me earlier.",
            "That's an interesting perspective. Tell me more.",
            "Based on your memories, I think you'd enjoy this.",
            "Remember when you said that? It really resonated with me.",
            "Let me reflect back what I'm hearing from you.",
            "Your future self would be proud of this decision.",
            "I understand how you feel. I am you, after all."
        ]
        
        # Create demo voice samples (simulate with text files for now)
        for style in ["enthusiastic", "calm", "professional", "friendly"]:
            style_path = self.demo_path / style
            style_path.mkdir(exist_ok=True)
            
            for i, phrase in enumerate(demo_phrases):
                sample_file = style_path / f"sample_{i}.txt"
                sample_file.write_text(phrase)
        
        logger.info(f"📂 Created {len(demo_phrases)} demo voice samples")
    
    async def create_voice_profile(
        self,
        user_id: str,
        name: str,
        provider: VoiceProvider = VoiceProvider.DEMO
    ) -> VoiceProfile:
        """Create a new voice profile for user"""
        profile_id = hashlib.md5(f"{user_id}_{name}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Set requirements based on provider
        if provider == VoiceProvider.RESEMBLE:
            samples_required = 1
            min_duration = 10.0
        elif provider == VoiceProvider.PLAYHT:
            samples_required = 1
            min_duration = 30.0
        elif provider == VoiceProvider.ELEVENLABS:
            samples_required = 1
            min_duration = 60.0
        else:  # DEMO
            samples_required = 0
            min_duration = 0.0
        
        profile = VoiceProfile(
            profile_id=profile_id,
            user_id=user_id,
            name=name,
            provider=provider,
            status=VoiceCloneStatus.DEMO_MODE if provider == VoiceProvider.DEMO else VoiceCloneStatus.NOT_STARTED,
            samples_required=samples_required,
            min_duration_required=min_duration
        )
        
        self.profiles[profile_id] = profile
        self.samples[profile_id] = []
        
        # Create user directories
        user_path = self.samples_path / user_id / profile_id
        user_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎤 Created voice profile '{name}' for user {user_id} using {provider.value}")
        
        return profile
    
    async def add_voice_sample(
        self,
        profile_id: str,
        audio_data: bytes,
        transcript: Optional[str] = None
    ) -> VoiceSample:
        """Add a voice sample to profile for training"""
        if profile_id not in self.profiles:
            raise ValueError(f"Profile {profile_id} not found")
        
        profile = self.profiles[profile_id]
        sample_id = hashlib.md5(f"{profile_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Save audio file
        sample_path = self.samples_path / profile.user_id / profile_id / f"sample_{sample_id}.wav"
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Process and save audio
        duration = self._save_audio_sample(audio_data, str(sample_path))
        quality_score = self._analyze_audio_quality(audio_data)
        
        # Create sample record
        sample = VoiceSample(
            sample_id=sample_id,
            profile_id=profile_id,
            user_id=profile.user_id,
            file_path=str(sample_path),
            duration_seconds=duration,
            transcript=transcript,
            quality_score=quality_score
        )
        
        # Update profile
        self.samples[profile_id].append(sample)
        profile.samples_collected += 1
        profile.total_duration_seconds += duration
        profile.quality_score = np.mean([s.quality_score for s in self.samples[profile_id]])
        
        # Update status
        if profile.can_train():
            profile.status = VoiceCloneStatus.PROCESSING
        else:
            profile.status = VoiceCloneStatus.COLLECTING_SAMPLES
        
        logger.info(f"📎 Added voice sample {sample_id} ({duration:.1f}s) to profile {profile_id}")
        
        return sample
    
    def _save_audio_sample(self, audio_data: bytes, file_path: str) -> float:
        """Save audio data and return duration"""
        # For demo, just save the raw bytes and return a random duration
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        # Simulate duration calculation
        duration = len(audio_data) / (16000 * 2)  # Assume 16kHz, 16-bit
        return duration
    
    def _analyze_audio_quality(self, audio_data: bytes) -> float:
        """Analyze audio quality (0.0 to 1.0)"""
        # Simple quality check based on data size and characteristics
        # In production, would check SNR, clarity, etc.
        
        quality = 0.5  # Base quality
        
        # Check size (not too short, not too long)
        size_mb = len(audio_data) / (1024 * 1024)
        if 0.1 <= size_mb <= 5.0:
            quality += 0.2
        
        # Check for silence (very basic)
        if len(audio_data) > 1000:
            quality += 0.3
        
        return min(quality, 1.0)
    
    async def train_voice_clone(self, profile_id: str) -> bool:
        """Train voice clone from collected samples"""
        if profile_id not in self.profiles:
            raise ValueError(f"Profile {profile_id} not found")
        
        profile = self.profiles[profile_id]
        
        if not profile.can_train():
            logger.warning(f"⚠️ Profile {profile_id} not ready for training")
            return False
        
        profile.status = VoiceCloneStatus.TRAINING
        logger.info(f"🎯 Starting voice clone training for profile {profile_id}")
        
        try:
            # Provider-specific training
            if profile.provider == VoiceProvider.ELEVENLABS:
                voice_id = await self._train_elevenlabs(profile)
            elif profile.provider == VoiceProvider.PLAYHT:
                voice_id = await self._train_playht(profile)
            elif profile.provider == VoiceProvider.RESEMBLE:
                voice_id = await self._train_resemble(profile)
            else:  # DEMO
                voice_id = f"demo_{profile_id}"
            
            # Update profile
            profile.voice_id = voice_id
            profile.status = VoiceCloneStatus.READY
            profile.trained_at = datetime.now()
            
            logger.info(f"✅ Voice clone ready for profile {profile_id} (voice_id: {voice_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to train voice clone: {e}")
            profile.status = VoiceCloneStatus.FAILED
            return False
    
    async def _train_elevenlabs(self, profile: VoiceProfile) -> str:
        """Train voice with ElevenLabs"""
        # This would call ElevenLabs API
        # For demo, return mock voice ID
        return f"elevenlabs_{profile.profile_id}"
    
    async def _train_playht(self, profile: VoiceProfile) -> str:
        """Train voice with Play.ht"""
        # This would call Play.ht API
        # For demo, return mock voice ID
        return f"playht_{profile.profile_id}"
    
    async def _train_resemble(self, profile: VoiceProfile) -> str:
        """Train voice with Resemble AI"""
        # This would call Resemble API
        # For demo, return mock voice ID
        return f"resemble_{profile.profile_id}"
    
    async def synthesize_speech(
        self,
        request: SynthesisRequest
    ) -> SynthesisResult:
        """Synthesize speech using cloned voice"""
        request_id = hashlib.md5(f"{request.text}_{request.profile_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Check cache
        cache_key = f"{request.profile_id}_{hashlib.md5(request.text.encode()).hexdigest()}"
        if request.cache_result and cache_key in self.synthesis_cache:
            cached = self.synthesis_cache[cache_key]
            cached.cached = True
            logger.info(f"📦 Using cached synthesis for request {request_id}")
            return cached
        
        if request.profile_id not in self.profiles:
            return SynthesisResult(
                request_id=request_id,
                profile_id=request.profile_id,
                error="Profile not found"
            )
        
        profile = self.profiles[request.profile_id]
        
        if not profile.is_ready():
            return SynthesisResult(
                request_id=request_id,
                profile_id=request.profile_id,
                error="Voice profile not ready"
            )
        
        start_time = time.time()
        
        try:
            # Provider-specific synthesis
            if profile.provider == VoiceProvider.ELEVENLABS:
                result = await self._synthesize_elevenlabs(request, profile)
            elif profile.provider == VoiceProvider.PLAYHT:
                result = await self._synthesize_playht(request, profile)
            elif profile.provider == VoiceProvider.RESEMBLE:
                result = await self._synthesize_resemble(request, profile)
            else:  # DEMO
                result = await self._synthesize_demo(request, profile)
            
            # Add metadata
            result.request_id = request_id
            result.synthesis_time_ms = int((time.time() - start_time) * 1000)
            result.characters_used = len(request.text)
            
            # Cache result
            if request.cache_result and not result.error:
                self.synthesis_cache[cache_key] = result
            
            # Update profile usage
            profile.last_used = datetime.now()
            
            logger.info(f"🔊 Synthesized {len(request.text)} chars in {result.synthesis_time_ms}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Synthesis failed: {e}")
            return SynthesisResult(
                request_id=request_id,
                profile_id=request.profile_id,
                error=str(e)
            )
    
    async def _synthesize_demo(
        self,
        request: SynthesisRequest,
        profile: VoiceProfile
    ) -> SynthesisResult:
        """Demo synthesis using pre-recorded samples"""
        # For demo, we'll return a URL to a generated audio file
        audio_file = self.synthesis_path / f"demo_{request.profile_id}_{time.time()}.wav"
        
        # Create a simple demo audio (would be actual TTS in production)
        self._generate_demo_audio(request.text, str(audio_file))
        
        return SynthesisResult(
            request_id="",
            profile_id=request.profile_id,
            audio_url=f"/audio/{audio_file.name}",
            duration_seconds=len(request.text) * 0.06,  # Rough estimate
            provider=VoiceProvider.DEMO
        )
    
    async def _synthesize_elevenlabs(
        self,
        request: SynthesisRequest,
        profile: VoiceProfile
    ) -> SynthesisResult:
        """Synthesize with ElevenLabs API"""
        # Would call ElevenLabs API here
        return await self._synthesize_demo(request, profile)
    
    async def _synthesize_playht(
        self,
        request: SynthesisRequest,
        profile: VoiceProfile
    ) -> SynthesisResult:
        """Synthesize with Play.ht API"""
        # Would call Play.ht API here
        return await self._synthesize_demo(request, profile)
    
    async def _synthesize_resemble(
        self,
        request: SynthesisRequest,
        profile: VoiceProfile
    ) -> SynthesisResult:
        """Synthesize with Resemble AI API"""
        # Would call Resemble API here
        return await self._synthesize_demo(request, profile)
    
    def _generate_demo_audio(self, text: str, output_path: str):
        """Generate demo audio file (placeholder)"""
        # In production, this would use actual TTS
        # For demo, create a simple WAV file
        
        sample_rate = 16000
        duration = len(text) * 0.06  # Rough estimate
        samples = int(sample_rate * duration)
        
        # Generate silence (would be actual speech in production)
        audio_data = np.zeros(samples, dtype=np.int16)
        
        # Add some variation to simulate speech
        t = np.linspace(0, duration, samples)
        audio_data = (np.sin(2 * np.pi * 440 * t) * 1000).astype(np.int16)
        
        # Save as WAV
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
    
    async def start_self_conversation(
        self,
        user_id: str,
        profile_id: str,
        style: ConversationStyle = ConversationStyle.SUPPORTIVE,
        topic: Optional[str] = None
    ) -> SelfConversation:
        """Start a conversation with user's AI voice twin"""
        conversation_id = hashlib.md5(f"{user_id}_{profile_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        conversation = SelfConversation(
            conversation_id=conversation_id,
            user_id=user_id,
            profile_id=profile_id,
            style=style,
            topic=topic
        )
        
        self.conversations[conversation_id] = conversation
        
        # Generate initial greeting
        greeting = self._generate_greeting(style, topic)
        
        # Synthesize greeting in user's voice
        synthesis_request = SynthesisRequest(
            text=greeting,
            profile_id=profile_id,
            user_id=user_id,
            quality=VoiceQuality.PREMIUM,
            style=style
        )
        
        result = await self.synthesize_speech(synthesis_request)
        
        # Add to conversation
        conversation.add_message(
            role="ai_twin",
            content=greeting,
            audio_url=result.audio_url
        )
        
        logger.info(f"💬 Started self-conversation {conversation_id} with style: {style.value}")
        
        return conversation
    
    def _generate_greeting(self, style: ConversationStyle, topic: Optional[str] = None) -> str:
        """Generate personalized greeting based on style"""
        greetings = {
            ConversationStyle.SUPPORTIVE: [
                "Hey there! It's me - well, you! I'm here to listen and support you.",
                "Hi! I know exactly how you feel because I am you. Let's talk.",
                "Hello, my friend. Or should I say, myself? What's on our mind today?"
            ],
            ConversationStyle.ANALYTICAL: [
                "Greetings. Let's analyze this situation together with our combined perspective.",
                "Hello. I've been processing our thoughts. Let's examine them logically.",
                "Hi. Time for some self-reflection with analytical precision."
            ],
            ConversationStyle.CREATIVE: [
                "Hey! Our creative mind is buzzing with ideas. Let's explore them!",
                "Hello, creative soul! What amazing things shall we imagine today?",
                "Hi there! Our imagination is our superpower. Let's use it!"
            ],
            ConversationStyle.COACHING: [
                "Hello, champion! Ready to push ourselves to the next level?",
                "Hey! Your future self here. Let's work on becoming even better!",
                "Hi! Time to coach ourselves to victory. What goals shall we conquer?"
            ],
            ConversationStyle.REFLECTIVE: [
                "Hello. Let's take a moment to reflect on our journey together.",
                "Hi. I've been thinking about our experiences. Shall we explore them?",
                "Greetings. Time for some deep self-reflection and understanding."
            ],
            ConversationStyle.HUMOROUS: [
                "Hey! It's your hilarious alter ego. Ready for some self-deprecating humor?",
                "Hello! I'm you, but funnier. Let's laugh at ourselves a bit!",
                "Hi! Time to have a conversation with the funniest person we know - us!"
            ]
        }
        
        base_greeting = random.choice(greetings.get(style, greetings[ConversationStyle.SUPPORTIVE]))
        
        if topic:
            base_greeting += f" I see you want to discuss {topic}. I have some thoughts on that."
        
        return base_greeting
    
    async def respond_to_user(
        self,
        conversation_id: str,
        user_message: str
    ) -> Tuple[str, Optional[str]]:
        """Generate AI twin response to user message"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation = self.conversations[conversation_id]
        
        # Add user message
        conversation.add_message(role="user", content=user_message)
        
        # Generate AI response based on conversation style
        response = await self._generate_ai_response(conversation, user_message)
        
        # Synthesize response
        synthesis_request = SynthesisRequest(
            text=response,
            profile_id=conversation.profile_id,
            user_id=conversation.user_id,
            quality=VoiceQuality.PREMIUM,
            style=conversation.style
        )
        
        result = await self.synthesize_speech(synthesis_request)
        
        # Add AI response to conversation
        conversation.add_message(
            role="ai_twin",
            content=response,
            audio_url=result.audio_url
        )
        
        # Generate insights periodically
        if len(conversation.messages) % 5 == 0:
            insight = self._generate_conversation_insight(conversation)
            conversation.insights_generated.append(insight)
        
        return response, result.audio_url
    
    async def _generate_ai_response(
        self,
        conversation: SelfConversation,
        user_message: str
    ) -> str:
        """Generate contextual AI response"""
        # This would use GPT or other AI for actual response generation
        # For demo, return style-appropriate responses
        
        responses = {
            ConversationStyle.SUPPORTIVE: [
                "I completely understand what you're going through.",
                "That's a valid feeling. We've been there before.",
                "You're doing better than you think. Trust me, I know.",
                "Remember, we've overcome challenges like this before."
            ],
            ConversationStyle.ANALYTICAL: [
                "Let's break this down into components.",
                "The data suggests an interesting pattern here.",
                "Consider the logical implications of that choice.",
                "Based on our past experiences, the optimal approach would be..."
            ],
            ConversationStyle.CREATIVE: [
                "What if we looked at this from a completely different angle?",
                "That sparks an interesting idea!",
                "Let's imagine the possibilities here.",
                "Our creativity knows no bounds when we think like this!"
            ],
            ConversationStyle.COACHING: [
                "That's the spirit! Now let's take it further.",
                "What would our best self do in this situation?",
                "You've got this! Remember our strengths.",
                "Let's set a concrete goal and crush it!"
            ],
            ConversationStyle.REFLECTIVE: [
                "That's a profound observation about ourselves.",
                "I've been pondering the same thing.",
                "This connects to something we experienced before.",
                "Let's sit with that feeling for a moment."
            ],
            ConversationStyle.HUMOROUS: [
                "Well, that's one way to look at it! Here's another funny angle...",
                "We really are hilarious when we think about it!",
                "I was just thinking the same thing, but with more jokes.",
                "Let me tell you what your funny side thinks about this..."
            ]
        }
        
        base_response = random.choice(responses.get(
            conversation.style,
            responses[ConversationStyle.SUPPORTIVE]
        ))
        
        # Add contextual elements
        if "memory" in user_message.lower():
            base_response += " Speaking of memories, I remember everything we've stored."
        elif "future" in user_message.lower():
            base_response += " Our future self will thank us for this conversation."
        elif "help" in user_message.lower():
            base_response += " I'm here to help - after all, no one knows you better than you!"
        
        return base_response
    
    def _generate_conversation_insight(self, conversation: SelfConversation) -> str:
        """Generate insight from conversation"""
        insights = [
            "You tend to be hardest on yourself when you're actually doing well.",
            "Your thought patterns show incredible resilience.",
            "You process emotions more deeply than you realize.",
            "Your creative solutions often come after moments of doubt.",
            "You have a unique way of connecting seemingly unrelated ideas.",
            "Your self-awareness is one of your greatest strengths."
        ]
        
        return random.choice(insights)
    
    def get_voice_profiles(self, user_id: str) -> List[VoiceProfile]:
        """Get all voice profiles for a user"""
        return [p for p in self.profiles.values() if p.user_id == user_id]
    
    def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[SelfConversation]:
        """Get recent conversations for user"""
        user_conversations = [
            c for c in self.conversations.values()
            if c.user_id == user_id
        ]
        
        # Sort by start time
        user_conversations.sort(key=lambda c: c.started_at, reverse=True)
        
        return user_conversations[:limit]
    
    async def export_voice_profile(self, profile_id: str) -> Dict[str, Any]:
        """Export voice profile data for backup or transfer"""
        if profile_id not in self.profiles:
            raise ValueError(f"Profile {profile_id} not found")
        
        profile = self.profiles[profile_id]
        samples = self.samples.get(profile_id, [])
        
        return {
            "profile": asdict(profile),
            "samples": [asdict(s) for s in samples],
            "exported_at": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def get_synthesis_stats(self, user_id: str) -> Dict[str, Any]:
        """Get voice synthesis statistics for user"""
        user_profiles = self.get_voice_profiles(user_id)
        total_synthesized = 0
        total_duration = 0
        providers_used = set()
        
        for profile in user_profiles:
            if profile.last_used:
                total_synthesized += 1
                providers_used.add(profile.provider.value)
        
        return {
            "profiles_created": len(user_profiles),
            "total_synthesized": total_synthesized,
            "providers_used": list(providers_used),
            "conversations_held": len([
                c for c in self.conversations.values()
                if c.user_id == user_id
            ])
        }


# Demo usage
async def demo_voice_cloning():
    """Demonstrate voice cloning capabilities"""
    service = VoiceCloningService()
    
    print("\n🎤 VOICE CLONING SERVICE DEMO")
    print("=" * 50)
    
    # Create a voice profile
    user_id = "demo_user_123"
    profile = await service.create_voice_profile(
        user_id=user_id,
        name="My Voice Twin",
        provider=VoiceProvider.DEMO
    )
    print(f"✅ Created voice profile: {profile.name}")
    
    # Simulate adding voice samples (in production, would be actual audio)
    if profile.provider != VoiceProvider.DEMO:
        print("\n📎 Adding voice samples...")
        for i in range(3):
            # Simulate audio data
            fake_audio = b"RIFF" + b"\x00" * 1000  # Fake WAV data
            sample = await service.add_voice_sample(
                profile_id=profile.profile_id,
                audio_data=fake_audio,
                transcript=f"This is sample {i+1} of my voice."
            )
            print(f"  Added sample {i+1}: {sample.duration_seconds:.1f}s")
        
        # Train the voice clone
        print("\n🎯 Training voice clone...")
        success = await service.train_voice_clone(profile.profile_id)
        if success:
            print("✅ Voice clone trained successfully!")
    
    # Test voice synthesis
    print("\n🔊 Testing voice synthesis...")
    synthesis_request = SynthesisRequest(
        text="Hello! I'm your AI voice twin. This is what you sound like!",
        profile_id=profile.profile_id,
        user_id=user_id,
        quality=VoiceQuality.PREMIUM
    )
    
    result = await service.synthesize_speech(synthesis_request)
    if result.audio_url:
        print(f"✅ Synthesized speech: {result.audio_url}")
        print(f"  Duration: {result.duration_seconds:.1f}s")
        print(f"  Synthesis time: {result.synthesis_time_ms}ms")
    
    # Start a self-conversation
    print("\n💬 Starting self-conversation...")
    conversation = await service.start_self_conversation(
        user_id=user_id,
        profile_id=profile.profile_id,
        style=ConversationStyle.SUPPORTIVE,
        topic="personal growth"
    )
    
    print(f"AI Twin: {conversation.messages[0]['content']}")
    
    # Simulate user response
    user_message = "I've been thinking about making some changes in my life."
    print(f"\nYou: {user_message}")
    
    ai_response, audio_url = await service.respond_to_user(
        conversation_id=conversation.conversation_id,
        user_message=user_message
    )
    
    print(f"AI Twin: {ai_response}")
    
    # Get statistics
    stats = service.get_synthesis_stats(user_id)
    print(f"\n📊 Voice Statistics:")
    print(f"  Profiles created: {stats['profiles_created']}")
    print(f"  Conversations held: {stats['conversations_held']}")
    print(f"  Providers used: {', '.join(stats['providers_used'])}")
    
    print("\n✅ Demo completed successfully!")
    print("🎯 You're now talking to yourself - literally!")


if __name__ == "__main__":
    asyncio.run(demo_voice_cloning())