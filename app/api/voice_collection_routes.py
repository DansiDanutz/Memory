"""
FastAPI routes for Voice Sample Collection System
Comprehensive endpoints for managing voice samples and triggering cloning
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import base64
import tempfile
import os

from app.gamification.voice_sample_storage import VoiceSampleStorage
from app.gamification.voice_avatar_system import VoiceAvatarSystem
from app.gamification.database_models import SessionLocal, User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice-collection", tags=["voice-collection"])

# Pydantic models for requests/responses
class VoiceSampleUpload(BaseModel):
    user_id: str
    audio_base64: str
    source: str = "whatsapp"
    metadata: Optional[Dict[str, Any]] = {}

class BatchVoiceSampleUpload(BaseModel):
    user_id: str
    samples: List[Dict[str, Any]]  # List of {audio_base64, metadata}
    source: str = "whatsapp"

class VoiceCloneRequest(BaseModel):
    user_id: str
    clone_type: str = "instant"  # instant or professional
    avatar_name: Optional[str] = None

class SampleDeleteRequest(BaseModel):
    user_id: str
    sample_id: int

# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_voice_storage(db: Session = Depends(get_db)):
    return VoiceSampleStorage(db)

def get_avatar_system(db: Session = Depends(get_db)):
    return VoiceAvatarSystem(db)

# Endpoints

@router.post("/upload-sample")
async def upload_voice_sample(
    request: VoiceSampleUpload,
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Upload a single voice sample for a user
    """
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audio_base64)
        
        # Store the sample
        success, result = storage.store_voice_sample(
            user_id=request.user_id,
            audio_data=audio_data,
            source=request.source,
            metadata=request.metadata
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=result)
        
        # Get progress after storing
        progress = storage.get_user_progress(request.user_id)
        
        return JSONResponse({
            "status": "success",
            "sample": result,
            "progress": {
                "total_samples": progress.total_samples,
                "total_duration": progress.total_duration_formatted,
                "instant_ready": progress.instant_clone_ready,
                "instant_progress": progress.instant_clone_progress,
                "professional_ready": progress.professional_clone_ready,
                "professional_progress": progress.professional_clone_progress,
                "quality_score": progress.quality_score,
                "recommendations": progress.recommendations
            }
        })
        
    except Exception as e:
        logger.error(f"Error uploading voice sample: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-sample-file")
async def upload_voice_sample_file(
    user_id: str = Form(...),
    source: str = Form("web"),
    file: UploadFile = File(...),
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Upload a voice sample file (for web interface)
    """
    try:
        # Read file data
        audio_data = await file.read()
        
        # Store the sample
        success, result = storage.store_voice_sample(
            user_id=user_id,
            audio_data=audio_data,
            source=source,
            metadata={"filename": file.filename}
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=result)
        
        # Get progress
        progress = storage.get_user_progress(user_id)
        
        return JSONResponse({
            "status": "success",
            "sample": result,
            "progress": {
                "total_samples": progress.total_samples,
                "total_duration": progress.total_duration_formatted,
                "instant_ready": progress.instant_clone_ready,
                "instant_progress": progress.instant_clone_progress,
                "professional_ready": progress.professional_clone_ready,
                "professional_progress": progress.professional_clone_progress,
                "recommendations": progress.recommendations
            }
        })
        
    except Exception as e:
        logger.error(f"Error uploading voice sample file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-upload")
async def batch_upload_samples(
    request: BatchVoiceSampleUpload,
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Upload multiple voice samples at once
    """
    try:
        results = []
        failed = []
        
        for idx, sample_data in enumerate(request.samples):
            try:
                # Decode audio
                audio_data = base64.b64decode(sample_data["audio_base64"])
                
                # Store sample
                success, result = storage.store_voice_sample(
                    user_id=request.user_id,
                    audio_data=audio_data,
                    source=request.source,
                    metadata=sample_data.get("metadata", {})
                )
                
                if success:
                    results.append(result)
                else:
                    failed.append({"index": idx, "error": result})
                    
            except Exception as e:
                failed.append({"index": idx, "error": str(e)})
        
        # Get final progress
        progress = storage.get_user_progress(request.user_id)
        
        return JSONResponse({
            "status": "success",
            "uploaded": len(results),
            "failed": len(failed),
            "samples": results,
            "errors": failed,
            "progress": {
                "total_samples": progress.total_samples,
                "total_duration": progress.total_duration_formatted,
                "instant_ready": progress.instant_clone_ready,
                "professional_ready": progress.professional_clone_ready,
                "recommendations": progress.recommendations
            }
        })
        
    except Exception as e:
        logger.error(f"Error in batch upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{user_id}")
async def get_voice_collection_progress(
    user_id: str,
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Get detailed progress towards voice cloning requirements
    """
    try:
        progress = storage.get_user_progress(user_id)
        
        return JSONResponse({
            "user_id": progress.user_id,
            "total_samples": progress.total_samples,
            "total_duration_seconds": progress.total_duration_seconds,
            "total_duration_formatted": progress.total_duration_formatted,
            "instant_clone": {
                "ready": progress.instant_clone_ready,
                "progress": progress.instant_clone_progress,
                "samples_needed": progress.samples_needed_instant,
                "duration_needed": progress.duration_needed_instant,
                "minimum_duration": VoiceSampleStorage.INSTANT_CLONE_MIN_DURATION,
                "optimal_duration": VoiceSampleStorage.INSTANT_CLONE_OPTIMAL_DURATION
            },
            "professional_clone": {
                "ready": progress.professional_clone_ready,
                "progress": progress.professional_clone_progress,
                "samples_needed": progress.samples_needed_professional,
                "duration_needed": progress.duration_needed_professional,
                "minimum_duration": VoiceSampleStorage.PROFESSIONAL_CLONE_MIN_DURATION,
                "optimal_duration": VoiceSampleStorage.PROFESSIONAL_CLONE_OPTIMAL_DURATION
            },
            "quality_score": progress.quality_score,
            "recent_samples": progress.recent_samples,
            "recommendations": progress.recommendations
        })
        
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/samples/{user_id}")
async def get_user_samples(
    user_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Get list of user's voice samples
    """
    try:
        samples = storage.get_user_samples(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status_filter=status
        )
        
        return JSONResponse({
            "user_id": user_id,
            "samples": samples,
            "count": len(samples),
            "limit": limit,
            "offset": offset
        })
        
    except Exception as e:
        logger.error(f"Error getting samples: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-clone")
async def trigger_voice_cloning(
    request: VoiceCloneRequest,
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Manually trigger voice cloning when requirements are met
    """
    try:
        # Check requirements first
        progress = storage.get_user_progress(request.user_id)
        
        if request.clone_type == "instant" and not progress.instant_clone_ready:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Not ready for instant cloning",
                    "current_duration": progress.total_duration_seconds,
                    "required_duration": VoiceSampleStorage.INSTANT_CLONE_MIN_DURATION,
                    "samples_needed": progress.samples_needed_instant
                }
            )
        
        if request.clone_type == "professional" and not progress.professional_clone_ready:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Not ready for professional cloning",
                    "current_duration": progress.total_duration_seconds,
                    "required_duration": VoiceSampleStorage.PROFESSIONAL_CLONE_MIN_DURATION,
                    "samples_needed": progress.samples_needed_professional
                }
            )
        
        # Trigger cloning
        success, result = await storage.trigger_voice_cloning(
            user_id=request.user_id,
            clone_type=request.clone_type,
            avatar_name=request.avatar_name
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=result)
        
        return JSONResponse({
            "status": "success",
            "clone": result,
            "message": f"Voice cloning initiated successfully!"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering clone: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-readiness/{user_id}")
async def check_cloning_readiness(
    user_id: str,
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Check if user is ready for voice cloning (simplified endpoint)
    """
    try:
        progress = storage.get_user_progress(user_id)
        
        readiness = {
            "instant_clone": {
                "ready": progress.instant_clone_ready,
                "percentage": progress.instant_clone_progress,
                "message": "Ready for instant voice cloning!" if progress.instant_clone_ready 
                          else f"Need {progress.samples_needed_instant} more samples"
            },
            "professional_clone": {
                "ready": progress.professional_clone_ready,
                "percentage": progress.professional_clone_progress,
                "message": "Ready for professional voice cloning!" if progress.professional_clone_ready
                          else f"Need {progress.duration_needed_professional / 60:.0f} more minutes of audio"
            }
        }
        
        # Auto-trigger if ready
        auto_triggered = False
        if progress.instant_clone_ready and not auto_triggered:
            # Check if not already cloned
            should_clone, clone_type = storage._check_cloning_readiness(user_id)
            if should_clone:
                readiness["auto_trigger"] = {
                    "type": clone_type,
                    "message": "Voice cloning can be triggered automatically!"
                }
                auto_triggered = True
        
        return JSONResponse(readiness)
        
    except Exception as e:
        logger.error(f"Error checking readiness: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sample/{sample_id}")
async def delete_voice_sample(
    sample_id: int,
    user_id: str = Query(...),
    storage: VoiceSampleStorage = Depends(get_voice_storage)
):
    """
    Delete a specific voice sample
    """
    try:
        success = storage.delete_sample(sample_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Sample not found or unauthorized")
        
        # Get updated progress
        progress = storage.get_user_progress(user_id)
        
        return JSONResponse({
            "status": "success",
            "message": "Sample deleted successfully",
            "updated_progress": {
                "total_samples": progress.total_samples,
                "total_duration": progress.total_duration_formatted,
                "instant_ready": progress.instant_clone_ready,
                "professional_ready": progress.professional_clone_ready
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting sample: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/requirements")
async def get_cloning_requirements():
    """
    Get voice cloning requirements documentation
    """
    return JSONResponse({
        "instant_clone": {
            "name": "Instant Voice Cloning",
            "minimum_duration": 60,  # seconds
            "optimal_duration": 120,
            "maximum_duration": 180,
            "description": "Quick voice cloning with 1-2 minutes of audio",
            "quality": "Good quality, suitable for most use cases",
            "processing_time": "1-2 minutes"
        },
        "professional_clone": {
            "name": "Professional Voice Cloning",
            "minimum_duration": 1800,  # 30 minutes
            "optimal_duration": 10800,  # 3 hours
            "maximum_duration": 14400,  # 4 hours
            "description": "High-fidelity voice cloning with extensive training",
            "quality": "Highest quality, indistinguishable from original",
            "processing_time": "30-60 minutes depending on queue"
        },
        "audio_requirements": {
            "format": ["WAV", "MP3", "OGG", "OPUS"],
            "sample_rate": "Minimum 16kHz, optimal 44.1kHz",
            "channels": "Mono preferred, stereo accepted",
            "quality": {
                "no_background_noise": "Critical",
                "consistent_voice": "Important",
                "clear_speech": "Essential",
                "single_speaker": "Required"
            }
        },
        "best_practices": [
            "Record in a quiet environment",
            "Speak clearly and naturally",
            "Maintain consistent tone and pace",
            "Avoid background music or noise",
            "Use a good quality microphone if possible",
            "Keep samples between 5-30 seconds each"
        ]
    })

@router.get("/stats")
async def get_voice_collection_stats(
    db: Session = Depends(get_db)
):
    """
    Get overall voice collection statistics
    """
    try:
        from sqlalchemy import func
        from app.gamification.database_models import VoiceSample, VoiceAvatar
        
        # Get statistics
        total_users = db.query(func.count(func.distinct(VoiceSample.user_id))).scalar() or 0
        total_samples = db.query(func.count(VoiceSample.id)).scalar() or 0
        total_duration = db.query(func.sum(VoiceSample.duration_seconds)).scalar() or 0.0
        avg_quality = db.query(func.avg(VoiceSample.quality_score)).scalar() or 0.0
        
        total_clones = db.query(func.count(VoiceAvatar.id)).scalar() or 0
        instant_clones = db.query(VoiceAvatar).filter_by(clone_type="instant").count()
        professional_clones = db.query(VoiceAvatar).filter_by(clone_type="professional").count()
        
        return JSONResponse({
            "users": {
                "total": total_users,
                "with_samples": total_users
            },
            "samples": {
                "total": total_samples,
                "total_duration_seconds": total_duration,
                "total_duration_hours": total_duration / 3600,
                "average_quality": avg_quality
            },
            "clones": {
                "total": total_clones,
                "instant": instant_clones,
                "professional": professional_clones
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))