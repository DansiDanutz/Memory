"""
FastAPI Endpoints for Gamified Voice Avatar System
===================================================
RESTful API for managing invitations, voice avatars, and tier upgrades
"""

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import io
import os
from dotenv import load_dotenv

from gamified_voice_avatar import (
    GamifiedVoiceAvatarSystem,
    UserTier,
    VoiceService
)

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Memory Bot Voice Avatar API",
    description="Gamified voice avatar system with invitation rewards",
    version="1.0.0"
)

# Initialize the gamified system
voice_system = GamifiedVoiceAvatarSystem()


# Pydantic Models for Request/Response

class UserRegistration(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    invitation_code: Optional[str] = Field(None, description="Optional invitation code")
    phone_number: Optional[str] = Field(None, description="WhatsApp phone number")


class InvitationRequest(BaseModel):
    user_id: str = Field(..., description="User requesting invitation code")


class VoiceAvatarCreation(BaseModel):
    user_id: str = Field(..., description="User creating avatar")
    audio_samples: List[str] = Field(..., description="List of audio file paths or base64 data")
    sample_format: str = Field("path", description="Format: 'path' or 'base64'")


class SpeechGeneration(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    user_id: str = Field(..., description="User requesting speech")
    emotion: Optional[str] = Field(None, description="Emotion (premium only)")
    format: str = Field("mp3", description="Audio format: mp3, wav, pcm")
    streaming: bool = Field(False, description="Enable streaming response")


class UpgradeRequest(BaseModel):
    user_id: str = Field(..., description="User to upgrade")
    payment_token: str = Field(..., description="Payment verification token")
    plan: str = Field("premium", description="Subscription plan")


class InvitationValidation(BaseModel):
    code: str = Field(..., description="Invitation code to validate")


# Authentication dependency
async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key for protected endpoints"""
    valid_key = os.getenv("API_KEY", "memory-bot-api-key")
    if x_api_key != valid_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# API Endpoints

@app.get("/")
async def root():
    """API root endpoint with service information"""
    return {
        "service": "Memory Bot Voice Avatar API",
        "version": "1.0.0",
        "features": [
            "Gamified voice avatars",
            "Invitation rewards",
            "Tiered access (Free -> Invited -> Premium)",
            "ElevenLabs integration for premium users",
            "Coqui TTS for invited users"
        ],
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Check system health"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "voice_system": "operational",
            "redis": "operational" if voice_system.redis_client else "unavailable"
        }
    }


@app.post("/users/register")
async def register_user(registration: UserRegistration):
    """
    Register a new user

    - Creates user profile (FREE tier by default)
    - Processes invitation code if provided
    - Returns user profile and next steps
    """
    try:
        result = await voice_system.register_user(
            user_id=registration.user_id,
            invitation_code=registration.invitation_code
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return JSONResponse(
            status_code=201,
            content=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user profile and voice avatar status"""
    profile = voice_system.user_profiles.get(user_id)

    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": profile.user_id,
        "tier": profile.tier.value,
        "voice_service": profile.voice_service.value,
        "has_avatar": profile.voice_id is not None,
        "avatar_created_at": profile.avatar_created_at.isoformat() if profile.avatar_created_at else None,
        "invitations_sent": profile.invitations_sent,
        "successful_invites": profile.successful_invites,
        "is_paying": profile.is_paying,
        "upgrade_date": profile.upgrade_date.isoformat() if profile.upgrade_date else None
    }


@app.post("/invitations/generate")
async def generate_invitation(request: InvitationRequest):
    """
    Generate invitation code for user

    - Creates unique invitation code
    - Returns sharing message
    - Shows progress toward free avatar
    """
    try:
        result = await voice_system.generate_invitation_code(request.user_id)

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/invitations/validate")
async def validate_invitation(validation: InvitationValidation):
    """Check if invitation code is valid"""
    inviter_id = voice_system._get_inviter_from_code(validation.code)

    if not inviter_id:
        return {
            "valid": False,
            "message": "Invalid or expired invitation code"
        }

    inviter_profile = voice_system.user_profiles.get(inviter_id)
    if not inviter_profile:
        return {
            "valid": False,
            "message": "Inviter not found"
        }

    return {
        "valid": True,
        "inviter_id": inviter_id,
        "inviter_tier": inviter_profile.tier.value,
        "message": "Valid invitation code"
    }


@app.get("/users/{user_id}/invitation-progress")
async def get_invitation_progress(user_id: str):
    """
    Get user's progress toward free voice avatar

    - Shows current invite count
    - Calculates remaining invites needed
    - Returns invitation history
    """
    result = voice_system.get_invitation_progress(user_id)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@app.post("/voice/avatar/create")
async def create_voice_avatar(
    request: VoiceAvatarCreation,
    background_tasks: BackgroundTasks
):
    """
    Create voice avatar based on user tier

    - FREE tier: Returns invitation prompt
    - INVITED tier: Creates Coqui TTS avatar
    - PREMIUM tier: Creates ElevenLabs avatar
    """
    try:
        # Process audio samples based on format
        if request.sample_format == "base64":
            # Convert base64 to files
            audio_paths = await _process_base64_samples(
                request.audio_samples,
                request.user_id
            )
        else:
            audio_paths = request.audio_samples

        result = await voice_system.create_voice_avatar(
            user_id=request.user_id,
            audio_samples=audio_paths
        )

        if not result["success"]:
            if "suggestion" in result:
                # User needs to invite friends
                return JSONResponse(
                    status_code=403,
                    content=result
                )
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Schedule cleanup of temporary files
        if request.sample_format == "base64":
            background_tasks.add_task(_cleanup_temp_files, audio_paths)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/generate")
async def generate_speech(request: SpeechGeneration):
    """
    Generate speech using user's voice avatar

    - Checks user tier and avatar availability
    - Returns audio or upgrade prompt
    - Supports streaming for long text
    """
    try:
        result = await voice_system.generate_speech(
            text=request.text,
            user_id=request.user_id,
            emotion=request.emotion
        )

        if not result["success"]:
            if "call_to_action" in result:
                # User needs avatar or upgrade
                return JSONResponse(
                    status_code=403,
                    content=result
                )
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Return audio based on format
        if request.streaming and result.get("audio_stream"):
            return StreamingResponse(
                result["audio_stream"],
                media_type=f"audio/{request.format}"
            )
        elif result.get("audio_data"):
            return JSONResponse(content={
                **result,
                "format": request.format
            })
        else:
            return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/users/upgrade")
async def upgrade_to_premium(
    request: UpgradeRequest,
    background_tasks: BackgroundTasks
):
    """
    Upgrade user to premium tier

    - Verifies payment
    - Upgrades to ElevenLabs avatar
    - Migrates existing avatar if needed
    """
    try:
        # Verify payment token (integrate with payment provider)
        payment_verified = await _verify_payment(
            request.payment_token,
            request.user_id,
            request.plan
        )

        if not payment_verified:
            raise HTTPException(status_code=402, detail="Payment verification failed")

        result = await voice_system.upgrade_to_premium(
            user_id=request.user_id,
            payment_verified=True
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))

        # Send upgrade confirmation via WhatsApp
        background_tasks.add_task(
            _send_upgrade_confirmation,
            request.user_id,
            result
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    """
    Get invitation leaderboard

    - Shows top inviters
    - Displays badges and tiers
    - Encourages competition
    """
    return {
        "leaderboard": voice_system.get_leaderboard(limit=limit),
        "updated_at": datetime.now().isoformat()
    }


@app.get("/stats/voice-usage")
async def get_voice_usage_stats(x_api_key: str = Depends(verify_api_key)):
    """
    Get system-wide voice usage statistics (protected)

    - Total users by tier
    - Voice avatars created
    - Speech generations
    """
    stats = {
        "total_users": len(voice_system.user_profiles),
        "users_by_tier": {},
        "total_avatars": 0,
        "total_invitations": 0
    }

    for profile in voice_system.user_profiles.values():
        tier = profile.tier.value
        stats["users_by_tier"][tier] = stats["users_by_tier"].get(tier, 0) + 1
        if profile.voice_id:
            stats["total_avatars"] += 1
        stats["total_invitations"] += profile.successful_invites

    return stats


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(data: Dict[str, Any]):
    """
    Handle WhatsApp webhooks for invitations

    - Process invitation shares
    - Track app installations
    - Send notifications
    """
    # Process WhatsApp events
    if data.get("type") == "message":
        # Check for invitation code in message
        message = data.get("message", {})
        text = message.get("text", "")

        # Extract invitation code if present
        if "invite code:" in text.lower():
            # Process invitation
            pass

    return {"status": "processed"}


# Helper Functions

async def _process_base64_samples(
    base64_samples: List[str],
    user_id: str
) -> List[str]:
    """Convert base64 audio samples to files"""
    import base64
    import tempfile

    paths = []
    for i, sample in enumerate(base64_samples):
        # Decode base64
        audio_data = base64.b64decode(sample)

        # Save to temp file
        temp_path = f"/tmp/voice_sample_{user_id}_{i}.wav"
        with open(temp_path, "wb") as f:
            f.write(audio_data)

        paths.append(temp_path)

    return paths


async def _cleanup_temp_files(paths: List[str]):
    """Clean up temporary audio files"""
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass


async def _verify_payment(
    payment_token: str,
    user_id: str,
    plan: str
) -> bool:
    """Verify payment with payment provider"""
    # Integrate with Stripe, PayPal, etc.
    # For demo, just check token format
    return len(payment_token) > 10


async def _send_upgrade_confirmation(user_id: str, upgrade_result: Dict):
    """Send upgrade confirmation via WhatsApp"""
    # Integrate with WhatsApp Business API
    print(f"[WHATSAPP] Sending upgrade confirmation to {user_id}")
    print(f"Benefits: {upgrade_result.get('benefits')}")


# Exception handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)