"""
Voice Configuration for MemoApp
Default voice settings for the wise, trustworthy narrator
"""

# ElevenLabs Pre-built Voice IDs for older, wise male voices
VOICE_PROFILES = {
    "default_wise_man": {
        "voice_id": "onwK4e9ZLuTAKqWW03F9",  # ElevenLabs "Daniel" - British, mature, trustworthy
        "name": "Wise Narrator",
        "description": "A mature, wise voice full of knowledge and experience. Perfect for a trusted memory guardian.",
        "age_range": "55-70",
        "gender": "male",
        "accent": "British",
        "characteristics": {
            "tone": "warm and trustworthy",
            "pace": "measured and thoughtful",
            "pitch": "medium-low",
            "emotion": "calm and reassuring"
        },
        "voice_settings": {
            "stability": 0.75,  # Higher stability for consistent, mature tone
            "similarity_boost": 0.65,  # Balanced for natural sound
            "style": 0.3,  # Some style for expressiveness
            "use_speaker_boost": True
        }
    },
    "alternative_wise_1": {
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",  # ElevenLabs "Josh" - Deep, mature American
        "name": "American Sage",
        "description": "Deep, resonant voice with American accent. Conveys wisdom and authority.",
        "age_range": "60-75",
        "gender": "male",
        "accent": "American",
        "characteristics": {
            "tone": "deep and authoritative",
            "pace": "slow and deliberate",
            "pitch": "low",
            "emotion": "confident and reassuring"
        },
        "voice_settings": {
            "stability": 0.8,
            "similarity_boost": 0.6,
            "style": 0.25,
            "use_speaker_boost": True
        }
    },
    "alternative_wise_2": {
        "voice_id": "VR6AewLTigWG4xSOukaG",  # ElevenLabs "Arnold" - Mature, crisp
        "name": "Scholar Voice",
        "description": "Clear, articulate voice of a learned scholar. Perfect for conveying knowledge.",
        "age_range": "55-65",
        "gender": "male",
        "accent": "Neutral",
        "characteristics": {
            "tone": "clear and articulate",
            "pace": "moderate",
            "pitch": "medium",
            "emotion": "knowledgeable and patient"
        },
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.7,
            "style": 0.35,
            "use_speaker_boost": True
        }
    }
}

# Default voice configuration
DEFAULT_VOICE_ID = VOICE_PROFILES["default_wise_man"]["voice_id"]
DEFAULT_VOICE_SETTINGS = VOICE_PROFILES["default_wise_man"]["voice_settings"]
DEFAULT_VOICE_NAME = VOICE_PROFILES["default_wise_man"]["name"]

# Voice switching configuration
VOICE_SWITCH_CONFIG = {
    "allow_switching": True,  # Allow users to switch between cloned and default
    "preserve_default": True,  # Always keep default voice available
    "default_on_error": True,  # Fallback to default if cloned voice fails
    "voice_selection_memory": True  # Remember user's voice preference
}

# TTS Model configuration for optimal quality
TTS_CONFIG = {
    "default_model": "eleven_multilingual_v2",  # Best quality for wise narrator
    "fallback_model": "eleven_monolingual_v1",
    "turbo_model": "eleven_turbo_v2",  # For faster responses when needed
    "optimize_for": "quality",  # quality, speed, or balanced
    "output_format": "mp3_44100_128"
}

def get_default_voice_config():
    """Get the complete default voice configuration"""
    return {
        "voice_id": DEFAULT_VOICE_ID,
        "voice_name": DEFAULT_VOICE_NAME,
        "settings": DEFAULT_VOICE_SETTINGS,
        "profile": VOICE_PROFILES["default_wise_man"],
        "model": TTS_CONFIG["default_model"]
    }

def get_voice_by_preference(user_preference=None):
    """Get voice configuration based on user preference"""
    if user_preference and user_preference in VOICE_PROFILES:
        profile = VOICE_PROFILES[user_preference]
        return {
            "voice_id": profile["voice_id"],
            "voice_name": profile["name"],
            "settings": profile["voice_settings"],
            "profile": profile,
            "model": TTS_CONFIG["default_model"]
        }
    return get_default_voice_config()