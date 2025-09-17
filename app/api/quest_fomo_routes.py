"""
Quest and FOMO API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.gamification.quest_system import QuestSystem
from app.gamification.fomo_system import FOMOSystem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gamification", tags=["quests", "fomo"])

# Request models
class QuestActionRequest(BaseModel):
    user_id: str
    action_type: str
    amount: int = 1

class ClaimQuestRequest(BaseModel):
    user_id: str
    quest_id: int

class DismissAlertRequest(BaseModel):
    user_id: str
    alert_id: int

# Dependencies
def get_quest_system() -> QuestSystem:
    return QuestSystem()

def get_fomo_system() -> FOMOSystem:
    return FOMOSystem()

# =============== QUEST ENDPOINTS ===============
@router.get("/quests/active")
async def get_active_quests(
    user_id: str = Query(..., description="User ID"),
    quest_system: QuestSystem = Depends(get_quest_system)
):
    """Get all active quests for a user"""
    try:
        quests = await quest_system.get_active_quests(user_id)
        return JSONResponse(content=quests, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get active quests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quests/daily/generate")
async def generate_daily_quests(
    user_id: str,
    quest_system: QuestSystem = Depends(get_quest_system)
):
    """Generate daily quests for a user"""
    try:
        quests = await quest_system.generate_daily_quests(user_id)
        return JSONResponse(content={"quests": quests}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to generate daily quests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quests/weekly/generate")
async def generate_weekly_quests(
    user_id: str,
    quest_system: QuestSystem = Depends(get_quest_system)
):
    """Generate weekly challenges for a user"""
    try:
        quests = await quest_system.generate_weekly_quests(user_id)
        return JSONResponse(content={"quests": quests}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to generate weekly quests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quests/flash")
async def check_flash_quest(
    user_id: str = Query(..., description="User ID"),
    quest_system: QuestSystem = Depends(get_quest_system)
):
    """Check for available flash quests"""
    try:
        flash_quest = await quest_system.trigger_flash_quest(user_id)
        if flash_quest:
            return JSONResponse(content={"quest": flash_quest, "available": True}, status_code=200)
        else:
            return JSONResponse(content={"available": False}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to check flash quest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quests/progress")
async def update_quest_progress(
    request: QuestActionRequest,
    quest_system: QuestSystem = Depends(get_quest_system)
):
    """Update quest progress when user performs an action"""
    try:
        completed_quests = await quest_system.update_quest_progress(
            request.user_id,
            request.action_type,
            request.amount
        )
        return JSONResponse(
            content={
                "completed_quests": completed_quests,
                "success": True
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to update quest progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quests/{quest_id}/claim")
async def claim_quest_rewards(
    quest_id: int,
    user_id: str,
    quest_system: QuestSystem = Depends(get_quest_system)
):
    """Claim rewards for a completed quest"""
    try:
        success, result = await quest_system.claim_quest_rewards(user_id, quest_id)
        if success:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
    except Exception as e:
        logger.error(f"Failed to claim quest rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============== FOMO ENDPOINTS ===============
@router.get("/fomo/alerts")
async def get_fomo_alerts(
    user_id: str = Query(..., description="User ID"),
    include_expired: bool = Query(False, description="Include expired alerts"),
    fomo_system: FOMOSystem = Depends(get_fomo_system)
):
    """Get active FOMO alerts for a user"""
    try:
        alerts = await fomo_system.get_active_alerts(user_id, include_expired)
        return JSONResponse(content={"alerts": alerts}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get FOMO alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fomo/alerts/dismiss")
async def dismiss_fomo_alert(
    request: DismissAlertRequest,
    fomo_system: FOMOSystem = Depends(get_fomo_system)
):
    """Dismiss a FOMO alert"""
    try:
        success, result = await fomo_system.dismiss_alert(request.user_id, request.alert_id)
        if success:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
    except Exception as e:
        logger.error(f"Failed to dismiss alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fomo/flash-sale")
async def get_flash_sale_status(
    user_id: str = Query(..., description="User ID"),
    fomo_system: FOMOSystem = Depends(get_fomo_system)
):
    """Get current flash sale status"""
    try:
        sale_status = await fomo_system.get_flash_sale_status(user_id)
        if sale_status:
            return JSONResponse(content={"active": True, "sale": sale_status}, status_code=200)
        else:
            return JSONResponse(content={"active": False}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get flash sale status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fomo/flash-sale/trigger")
async def trigger_flash_sale(
    user_id: Optional[str] = None,
    fomo_system: FOMOSystem = Depends(get_fomo_system)
):
    """Manually trigger a flash sale (admin/testing)"""
    try:
        sale = await fomo_system.trigger_flash_sale(user_id)
        if sale:
            return JSONResponse(content={"triggered": True, "sale": sale}, status_code=200)
        else:
            return JSONResponse(content={"triggered": False, "reason": "Already active or probability check failed"}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to trigger flash sale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fomo/check-expiring")
async def check_expiring_rewards(
    user_id: str,
    fomo_system: FOMOSystem = Depends(get_fomo_system)
):
    """Check for rewards/quests expiring soon"""
    try:
        alerts = await fomo_system.check_expiring_rewards(user_id)
        return JSONResponse(content={"alerts": alerts}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to check expiring rewards: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fomo/friend-activity")
async def check_friend_activity(
    user_id: str,
    action_type: str,
    fomo_system: FOMOSystem = Depends(get_fomo_system)
):
    """Check friend activity for social proof"""
    try:
        alert = await fomo_system.check_friend_activity(user_id, action_type)
        if alert:
            return JSONResponse(content={"alert": alert, "created": True}, status_code=200)
        else:
            return JSONResponse(content={"created": False}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to check friend activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fomo/streak-risk")
async def check_streak_risk(
    user_id: str,
    streak_days: int,
    hours_until_reset: float,
    fomo_system: FOMOSystem = Depends(get_fomo_system)
):
    """Check if user's streak is at risk"""
    try:
        alert = await fomo_system.check_streak_risk(user_id, streak_days, hours_until_reset)
        if alert:
            return JSONResponse(content={"alert": alert, "at_risk": True}, status_code=200)
        else:
            return JSONResponse(content={"at_risk": False}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to check streak risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============== EVENT ENDPOINTS ===============
@router.get("/events/current")
async def get_current_events(
    quest_system: QuestSystem = Depends(get_quest_system)
):
    """Get current special events"""
    try:
        # This would normally check for active events from database
        # For now, return mock data
        events = {
            "active_events": [],
            "upcoming_events": [
                {
                    "name": "Weekend Warrior",
                    "description": "Double XP all weekend",
                    "starts_at": "2025-01-18T00:00:00Z",
                    "ends_at": "2025-01-20T23:59:59Z",
                    "rewards": {"xp_multiplier": 2.0}
                }
            ]
        }
        return JSONResponse(content=events, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get current events: {e}")
        raise HTTPException(status_code=500, detail=str(e))