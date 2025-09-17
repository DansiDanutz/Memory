"""
FastAPI routes for Gamification System
Provides API endpoints for invitations, rewards, and leaderboards
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.gamification import (
    GamifiedVoiceAvatarSystem,
    get_gamification_system
)
from app.gamification.database_models import AccessLevel
from app.gamification.streak_system import StreakSystem
from app.gamification.variable_rewards import VariableRewardsEngine
from app.gamification.quest_system import QuestSystem
from app.gamification.fomo_system import FOMOSystem
from app.gamification.subscription_service import SubscriptionService, get_subscription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gamification", tags=["gamification"])

# Pydantic models for requests/responses
class InvitationRequest(BaseModel):
    sender_phone: str
    recipient_phone: Optional[str] = None
    custom_message: Optional[str] = None

class InvitationAcceptRequest(BaseModel):
    code: str
    recipient_phone: str

class VoiceAvatarRequest(BaseModel):
    user_phone: str
    name: str
    description: str = ""
    audio_samples_base64: List[str]  # Base64 encoded audio

class ContactAddRequest(BaseModel):
    user_phone: str
    contact_phone: str
    access_level: str = "basic"

class SpeechGenerationRequest(BaseModel):
    avatar_id: int
    text: str
    user_phone: Optional[str] = None

class StreakCheckInRequest(BaseModel):
    user_id: str
    activity_type: Optional[str] = "daily_login"
    metadata: Optional[Dict[str, Any]] = None

class FreezeTokenRequest(BaseModel):
    user_id: str

class RewardSpinRequest(BaseModel):
    user_id: str
    trigger_event: Optional[str] = "manual_spin"

class RewardTriggerRequest(BaseModel):
    user_id: str
    event_type: str
    metadata: Optional[Dict[str, Any]] = None

# Dependency to get gamification system
def get_system() -> GamifiedVoiceAvatarSystem:
    return get_gamification_system()

# Dependency to get streak system
def get_streak_system() -> StreakSystem:
    return StreakSystem()

# Dependency to get rewards engine
def get_rewards_engine() -> VariableRewardsEngine:
    return VariableRewardsEngine()

# Dependency to get quest system
def get_quest_system() -> QuestSystem:
    return QuestSystem()

# Dependency to get FOMO system
def get_fomo_system() -> FOMOSystem:
    return FOMOSystem()

# Dependency to get subscription service
def get_subscription() -> SubscriptionService:
    return get_subscription_service()

@router.post("/invitations/create")
async def create_invitation(
    request: InvitationRequest,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Create a new invitation"""
    try:
        success, result = await system.create_invitation(
            request.sender_phone,
            request.recipient_phone,
            request.custom_message
        )
        
        if success:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        logger.error(f"Failed to create invitation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/invitations/accept")
async def accept_invitation(
    request: InvitationAcceptRequest,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Accept an invitation"""
    try:
        success, result = await system.accept_invitation(
            request.code,
            request.recipient_phone
        )
        
        if success:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        logger.error(f"Failed to accept invitation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_phone}/stats")
async def get_user_stats(
    user_phone: str,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Get comprehensive user statistics"""
    try:
        stats = await system.get_user_stats(user_phone)
        return JSONResponse(content=stats, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leaderboard")
async def get_leaderboard(
    metric: str = Query("points", description="Metric to rank by"),
    period: str = Query("all_time", description="Time period"),
    limit: int = Query(10, description="Number of entries"),
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Get leaderboard for specified metric"""
    try:
        leaderboard = await system.get_leaderboard(metric, period, limit)
        return JSONResponse(content=leaderboard, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice-avatars/create")
async def create_voice_avatar(
    request: VoiceAvatarRequest,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Create a new voice avatar"""
    try:
        # Decode base64 audio samples
        import base64
        audio_samples = [
            base64.b64decode(sample) 
            for sample in request.audio_samples_base64
        ]
        
        success, result = await system.create_voice_avatar(
            request.user_phone,
            request.name,
            audio_samples,
            request.description
        )
        
        if success:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        logger.error(f"Failed to create voice avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice-avatars/{user_phone}")
async def list_voice_avatars(
    user_phone: str,
    include_archived: bool = Query(False),
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """List all voice avatars for a user"""
    try:
        avatars = await system.voice_avatar_system.list_user_avatars(
            user_phone,
            include_archived
        )
        return JSONResponse(content=avatars, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to list avatars: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice-avatars/generate-speech")
async def generate_speech(
    request: SpeechGenerationRequest,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Generate speech using a voice avatar or default wise man voice"""
    try:
        # Use the new generate_speech_with_fallback method for wise man voice
        success, result = await system.voice_avatar_system.generate_speech_with_fallback(
            text=request.text,
            user_id=request.user_phone,
            avatar_id=request.avatar_id if hasattr(request, 'avatar_id') and request.avatar_id else None
        )
        
        if success:
            # Encode audio as base64 for JSON response
            import base64
            result["audio_base64"] = base64.b64encode(
                result["audio_data"]
            ).decode('utf-8')
            del result["audio_data"]
            
            # Add voice information
            result["voice_info"] = {
                "name": result.get("voice_name", "Wise Narrator"),
                "is_cloned": result.get("is_cloned", False),
                "used_fallback": result.get("fallback", False)
            }
            
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        logger.error(f"Failed to generate speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contacts/add")
async def add_contact(
    request: ContactAddRequest,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Add a contact to user's contact list"""
    try:
        # Convert string to AccessLevel enum
        access_level = AccessLevel[request.access_level.upper()]
        
        success, result = await system.add_contact(
            request.user_phone,
            request.contact_phone,
            access_level
        )
        
        if success:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid access level: {request.access_level}"
        )
    except Exception as e:
        logger.error(f"Failed to add contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/contacts/{user_phone}/{contact_phone}")
async def remove_contact(
    user_phone: str,
    contact_phone: str,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Remove a contact from user's list"""
    try:
        success, message = await system.permission_manager.remove_contact(
            user_phone,
            contact_phone
        )
        
        if success:
            return JSONResponse(
                content={"message": message},
                status_code=200
            )
        else:
            return JSONResponse(
                content={"error": message},
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Failed to remove contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contacts/{user_phone}")
async def list_contacts(
    user_phone: str,
    include_empty_slots: bool = Query(False),
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Get all contacts for a user"""
    try:
        contacts = await system.permission_manager.get_user_contacts(
            user_phone,
            include_empty_slots
        )
        return JSONResponse(content=contacts, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to list contacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rewards/{user_phone}")
async def get_pending_rewards(
    user_phone: str,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Get pending rewards for a user"""
    try:
        rewards = await system.rewards_engine.get_pending_rewards(user_phone)
        return JSONResponse(content=rewards, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rewards/{user_phone}/claim/{reward_id}")
async def claim_reward(
    user_phone: str,
    reward_id: int,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Claim a specific reward"""
    try:
        success, message = await system.rewards_engine.claim_reward(
            user_phone,
            reward_id
        )
        
        if success:
            return JSONResponse(
                content={"message": message},
                status_code=200
            )
        else:
            return JSONResponse(
                content={"error": message},
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Failed to claim reward: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/achievements/{user_phone}")
async def get_achievements(
    user_phone: str,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Get all achievements for a user"""
    try:
        stats = await system.get_user_stats(user_phone)
        achievements = stats.get("achievements", [])
        return JSONResponse(content=achievements, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get achievements: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice-providers")
async def get_voice_providers(
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Get available voice providers and their status"""
    try:
        providers = await system.voice_avatar_system.get_voice_providers()
        return JSONResponse(content=providers, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get voice providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice-preference/{user_phone}")
async def set_voice_preference(
    user_phone: str,
    preference: str = Query(..., description="'default' for wise narrator or avatar ID"),
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Set user's voice preference (default wise man or cloned avatar)"""
    try:
        success, message = await system.voice_avatar_system.set_voice_preference(
            user_id=user_phone,
            preference=preference
        )
        
        if success:
            return JSONResponse(
                content={"message": message, "preference": preference},
                status_code=200
            )
        else:
            return JSONResponse(
                content={"error": message},
                status_code=400
            )
            
    except Exception as e:
        logger.error(f"Failed to set voice preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice-preference/{user_phone}")
async def get_voice_preference(
    user_phone: str,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """Get user's current voice configuration"""
    try:
        voice_config = await system.voice_avatar_system.get_or_default_voice(user_phone)
        return JSONResponse(
            content={
                "voice_name": voice_config["voice_name"],
                "is_cloned": voice_config.get("is_cloned", False),
                "voice_id": voice_config.get("voice_id"),
                "description": "Wise, trustworthy narrator with years of wisdom" if not voice_config.get("is_cloned") else "Your personalized voice avatar"
            },
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Failed to get voice preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/ws/{user_phone}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_phone: str,
    system: GamifiedVoiceAvatarSystem = Depends(get_system)
):
    """WebSocket for real-time gamification updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send periodic updates
            stats = await system.get_user_stats(user_phone)
            await websocket.send_json({
                "type": "stats_update",
                "data": stats
            })
            
            # Wait for messages or timeout
            import asyncio
            await asyncio.sleep(30)  # Update every 30 seconds
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_phone}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

# Health check endpoint
@router.get("/health")
async def health_check():
    """Check gamification system health"""
    try:
        system = get_gamification_system()
        return {
            "status": "healthy",
            "components": {
                "database": "connected",
                "elevenlabs": system.elevenlabs.is_available(),
                "invitation_system": True,
                "rewards_engine": True,
                "voice_avatars": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )

# =============== STREAK SYSTEM ENDPOINTS ===============
@router.post("/streak/check-in")
async def streak_check_in(
    request: StreakCheckInRequest,
    streak_system: StreakSystem = Depends(get_streak_system)
):
    """Process daily check-in for a user"""
    try:
        result = await streak_system.check_in(
            request.user_id,
            request.activity_type,
            request.metadata
        )
        return JSONResponse(content=result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        logger.error(f"Failed to process check-in: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streak/{user_id}")
async def get_streak_data(
    user_id: str,
    streak_system: StreakSystem = Depends(get_streak_system)
):
    """Get comprehensive streak data for a user"""
    try:
        data = await streak_system.get_streak_data(user_id)
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get streak data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/streak/freeze")
async def use_freeze_token(
    request: FreezeTokenRequest,
    streak_system: StreakSystem = Depends(get_streak_system)
):
    """Use a freeze token to preserve streak"""
    try:
        result = await streak_system.use_freeze_token(request.user_id)
        return JSONResponse(content=result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        logger.error(f"Failed to use freeze token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streak/leaderboard")
async def get_streak_leaderboard(
    limit: int = Query(10, description="Number of entries"),
    streak_system: StreakSystem = Depends(get_streak_system)
):
    """Get streak leaderboard"""
    try:
        leaderboard = await streak_system.get_leaderboard(limit)
        return JSONResponse(content={"leaderboard": leaderboard}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get streak leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============== VARIABLE REWARDS ENDPOINTS ===============
@router.post("/rewards/spin")
async def spin_reward_wheel(
    request: RewardSpinRequest,
    rewards_engine: VariableRewardsEngine = Depends(get_rewards_engine)
):
    """Spin the reward wheel for a chance at variable rewards"""
    try:
        result = await rewards_engine.spin_reward_wheel(
            request.user_id,
            request.trigger_event
        )
        return JSONResponse(content=result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        logger.error(f"Failed to spin reward wheel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rewards/trigger")
async def trigger_reward(
    request: RewardTriggerRequest,
    rewards_engine: VariableRewardsEngine = Depends(get_rewards_engine)
):
    """Trigger a potential reward based on event"""
    try:
        result = await rewards_engine.trigger_reward(
            request.user_id,
            request.event_type,
            request.metadata
        )
        return JSONResponse(content=result, status_code=200 if result.get("success") else 400)
    except Exception as e:
        logger.error(f"Failed to trigger reward: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rewards/history/{user_id}")
async def get_reward_history(
    user_id: str,
    limit: int = Query(50, description="Number of records"),
    offset: int = Query(0, description="Offset for pagination"),
    rewards_engine: VariableRewardsEngine = Depends(get_rewards_engine)
):
    """Get reward history for a user"""
    try:
        history = await rewards_engine.get_reward_history(user_id, limit, offset)
        return JSONResponse(content=history, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get reward history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============== SUBSCRIPTION/PREMIUM ENDPOINTS ===============
@router.get("/subscription/status/{user_phone}")
async def get_subscription_status(
    user_phone: str,
    subscription: SubscriptionService = Depends(get_subscription)
):
    """Get user's current subscription status"""
    try:
        status = subscription.get_subscription_status(user_phone)
        return JSONResponse(content=status, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscription/upgrade-eligibility/{user_phone}")
async def get_upgrade_eligibility(
    user_phone: str,
    subscription: SubscriptionService = Depends(get_subscription)
):
    """Check user's upgrade eligibility and offers"""
    try:
        eligibility = subscription.get_upgrade_eligibility(user_phone)
        return JSONResponse(content=eligibility, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get upgrade eligibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscription/upgrade")
async def upgrade_subscription(
    user_phone: str = Query(..., description="User's phone number"),
    tier: str = Query("premium", description="Target subscription tier"),
    subscription: SubscriptionService = Depends(get_subscription)
):
    """Simulate user upgrade (for demo purposes)"""
    try:
        result = await subscription.simulate_upgrade(user_phone, tier)
        
        if result.get("success"):
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        logger.error(f"Failed to upgrade subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voice-avatars/preview/{avatar_id}")
async def get_avatar_preview(
    avatar_id: int,
    user_phone: str = Query(..., description="User's phone number"),
    subscription: SubscriptionService = Depends(get_subscription)
):
    """Get preview/teaser for locked voice avatar"""
    try:
        preview = subscription.generate_voice_preview(user_phone, avatar_id)
        return JSONResponse(content=preview, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to get avatar preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))