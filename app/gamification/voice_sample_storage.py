"""
Voice Sample Storage Service
Comprehensive system for storing, tracking, and managing voice samples for ElevenLabs cloning
"""

import os
import json
import hashlib
import logging
import tempfile
import wave
import soundfile as sf
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .database_models import (
    VoiceAvatar, VoiceSample, User,
    AvatarStatus, SessionLocal,
    VoiceSampleStatus, VoiceCloneType
)
from .elevenlabs_service import ElevenLabsService
from pydub import AudioSegment

logger = logging.getLogger(__name__)

@dataclass
class AudioValidationResult:
    """Result of audio validation"""
    is_valid: bool
    duration_seconds: float
    sample_rate: int
    channels: int
    format: str
    file_size_bytes: int
    quality_score: float  # 0-100
    issues: List[str]
    warnings: List[str]

@dataclass
class VoiceCloneProgress:
    """Progress towards voice cloning requirements"""
    user_id: str
    total_samples: int
    total_duration_seconds: float
    total_duration_formatted: str
    instant_clone_ready: bool
    instant_clone_progress: float  # percentage
    professional_clone_ready: bool
    professional_clone_progress: float  # percentage
    quality_score: float  # average quality score
    samples_needed_instant: int
    duration_needed_instant: float
    samples_needed_professional: int
    duration_needed_professional: float
    recent_samples: List[Dict[str, Any]]
    recommendations: List[str]

class VoiceSampleStorage:
    """
    Comprehensive voice sample storage and management system
    Handles validation, storage, tracking, and automatic cloning triggers
    """
    
    # ElevenLabs Requirements (from research)
    INSTANT_CLONE_MIN_DURATION = 60.0  # 1 minute minimum
    INSTANT_CLONE_OPTIMAL_DURATION = 120.0  # 2 minutes optimal
    INSTANT_CLONE_MAX_DURATION = 180.0  # 3 minutes max (diminishing returns)
    
    PROFESSIONAL_CLONE_MIN_DURATION = 1800.0  # 30 minutes minimum
    PROFESSIONAL_CLONE_OPTIMAL_DURATION = 10800.0  # 3 hours optimal
    PROFESSIONAL_CLONE_MAX_DURATION = 14400.0  # 4 hours max
    
    # Quality requirements
    MIN_SAMPLE_RATE = 16000  # 16kHz minimum
    OPTIMAL_SAMPLE_RATE = 44100  # 44.1kHz optimal
    MIN_DURATION_PER_SAMPLE = 3.0  # 3 seconds minimum per sample
    MAX_DURATION_PER_SAMPLE = 60.0  # 60 seconds maximum per sample
    MAX_SAMPLE_SIZE = 10 * 1024 * 1024  # 10MB max per file
    
    # Quality thresholds
    MIN_QUALITY_SCORE = 60.0  # Minimum acceptable quality
    OPTIMAL_QUALITY_SCORE = 80.0  # Good quality for cloning
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize voice sample storage"""
        self.db = db_session or SessionLocal()
        self.elevenlabs = ElevenLabsService()
        
        # Storage paths
        self.storage_base = Path("data/voice_samples")
        self.storage_base.mkdir(parents=True, exist_ok=True)
        
        # Cache for progress tracking
        self.progress_cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
        logger.info("✅ Voice Sample Storage Service initialized")
        logger.info(f"📁 Storage path: {self.storage_base}")
    
    def _calculate_quality_score(
        self,
        sample_rate: int,
        duration: float,
        channels: int,
        signal_to_noise: Optional[float] = None
    ) -> float:
        """
        Calculate quality score for audio sample (0-100)
        """
        score = 0.0
        
        # Sample rate scoring (40 points)
        if sample_rate >= self.OPTIMAL_SAMPLE_RATE:
            score += 40
        elif sample_rate >= 22050:
            score += 30
        elif sample_rate >= self.MIN_SAMPLE_RATE:
            score += 20
        else:
            score += 10
        
        # Duration scoring (30 points)
        if self.MIN_DURATION_PER_SAMPLE <= duration <= self.MAX_DURATION_PER_SAMPLE:
            if duration >= 10:
                score += 30
            elif duration >= 5:
                score += 20
            else:
                score += 15
        elif duration < self.MIN_DURATION_PER_SAMPLE:
            score += 5
        
        # Mono is preferred (10 points)
        if channels == 1:
            score += 10
        elif channels == 2:
            score += 5
        
        # Signal-to-noise ratio (20 points)
        if signal_to_noise:
            if signal_to_noise >= 40:  # Excellent
                score += 20
            elif signal_to_noise >= 30:  # Good
                score += 15
            elif signal_to_noise >= 20:  # Acceptable
                score += 10
            else:
                score += 5
        else:
            # Default medium score if SNR not calculated
            score += 10
        
        return min(100.0, score)
    
    def _estimate_signal_to_noise(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """
        Estimate signal-to-noise ratio (simplified)
        """
        try:
            # Simple estimation: compare signal power to noise floor
            # This is a simplified approach - proper SNR would require noise profile
            
            # Calculate RMS of the signal
            rms = np.sqrt(np.mean(audio_data**2))
            
            # Estimate noise floor (bottom 10% of sorted absolute values)
            sorted_abs = np.sort(np.abs(audio_data))
            noise_floor = np.mean(sorted_abs[:len(sorted_abs)//10])
            
            if noise_floor > 0:
                snr_db = 20 * np.log10(rms / noise_floor)
                return max(0, min(60, snr_db))  # Clamp to reasonable range
            
            return 40.0  # Default good SNR if calculation fails
            
        except Exception as e:
            logger.warning(f"Could not calculate SNR: {e}")
            return 30.0  # Default acceptable SNR
    
    def validate_audio_sample(
        self,
        audio_data: bytes,
        expected_format: str = "wav"
    ) -> AudioValidationResult:
        """
        Comprehensive audio validation
        """
        issues = []
        warnings = []
        
        # Check file size
        file_size = len(audio_data)
        if file_size > self.MAX_SAMPLE_SIZE:
            issues.append(f"File too large ({file_size / 1024 / 1024:.1f}MB, max {self.MAX_SAMPLE_SIZE / 1024 / 1024}MB)")
        
        # Try to load and analyze audio
        try:
            # Save to temporary file for analysis
            with tempfile.NamedTemporaryFile(suffix=f'.{expected_format}', delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            
            # Load audio with soundfile for analysis
            audio_array, sample_rate = sf.read(tmp_path)
            
            # Get audio info
            info = sf.info(tmp_path)
            duration = info.duration
            channels = info.channels
            format_type = info.format
            
            # Duration validation
            if duration < self.MIN_DURATION_PER_SAMPLE:
                issues.append(f"Sample too short ({duration:.1f}s, min {self.MIN_DURATION_PER_SAMPLE}s)")
            elif duration > self.MAX_DURATION_PER_SAMPLE:
                warnings.append(f"Sample very long ({duration:.1f}s), consider splitting")
            
            # Sample rate validation
            if sample_rate < self.MIN_SAMPLE_RATE:
                issues.append(f"Sample rate too low ({sample_rate}Hz, min {self.MIN_SAMPLE_RATE}Hz)")
            elif sample_rate < self.OPTIMAL_SAMPLE_RATE:
                warnings.append(f"Higher sample rate recommended ({sample_rate}Hz vs {self.OPTIMAL_SAMPLE_RATE}Hz)")
            
            # Channels validation
            if channels > 2:
                issues.append(f"Too many channels ({channels}), stereo or mono required")
            elif channels == 2:
                warnings.append("Mono audio preferred for voice cloning")
            
            # Calculate signal-to-noise ratio
            if channels == 1:
                snr = self._estimate_signal_to_noise(audio_array, sample_rate)
            else:
                # Use first channel for SNR estimation
                snr = self._estimate_signal_to_noise(audio_array[:, 0], sample_rate)
            
            if snr < 20:
                issues.append(f"Poor signal-to-noise ratio ({snr:.1f}dB)")
            elif snr < 30:
                warnings.append(f"Audio quality could be improved (SNR: {snr:.1f}dB)")
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(
                sample_rate, duration, channels, snr
            )
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            # Determine if valid
            is_valid = len(issues) == 0 and quality_score >= self.MIN_QUALITY_SCORE
            
            return AudioValidationResult(
                is_valid=is_valid,
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=channels,
                format=format_type,
                file_size_bytes=file_size,
                quality_score=quality_score,
                issues=issues,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Audio validation error: {e}")
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return AudioValidationResult(
                is_valid=False,
                duration_seconds=0,
                sample_rate=0,
                channels=0,
                format="unknown",
                file_size_bytes=file_size,
                quality_score=0,
                issues=[f"Could not analyze audio: {str(e)}"],
                warnings=[]
            )
    
    def store_voice_sample(
        self,
        user_id: str,
        audio_data: bytes,
        source: str = "whatsapp",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Store a voice sample for a user
        """
        try:
            # Validate audio
            validation = self.validate_audio_sample(audio_data)
            
            if not validation.is_valid:
                return False, {
                    "error": "Audio validation failed",
                    "issues": validation.issues,
                    "warnings": validation.warnings,
                    "quality_score": validation.quality_score
                }
            
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            audio_hash = hashlib.sha256(audio_data).hexdigest()[:12]
            filename = f"{user_id}_{timestamp}_{audio_hash}.wav"
            
            # Create user directory
            user_dir = self.storage_base / user_id
            user_dir.mkdir(exist_ok=True)
            
            # Save audio file
            file_path = user_dir / filename
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            # Create database record
            sample = VoiceSample(
                user_id=user_id,
                file_path=str(file_path),
                file_url=f"/voice_samples/{user_id}/{filename}",
                duration_seconds=validation.duration_seconds,
                sample_rate=validation.sample_rate,
                channels=validation.channels,
                format=validation.format,
                file_size_bytes=validation.file_size_bytes,
                quality_score=validation.quality_score,
                source=source,
                status=VoiceSampleStatus.VALIDATED,
                validation_issues=validation.issues,
                validation_warnings=validation.warnings,
                extra_metadata=metadata or {},
                created_at=datetime.utcnow()
            )
            
            self.db.add(sample)
            
            # Update user stats
            user = self.db.query(User).filter_by(id=user_id).first()
            if not user:
                # Create user if doesn't exist
                user = User(
                    id=user_id,
                    created_at=datetime.utcnow()
                )
                self.db.add(user)
            
            # Commit to database
            self.db.commit()
            
            logger.info(f"✅ Stored voice sample for {user_id}: {filename} ({validation.duration_seconds:.1f}s, quality: {validation.quality_score:.0f})")
            
            # Check if automatic cloning should be triggered
            should_clone, clone_type = self._check_cloning_readiness(user_id)
            
            result = {
                "sample_id": sample.id,
                "filename": filename,
                "duration": validation.duration_seconds,
                "quality_score": validation.quality_score,
                "warnings": validation.warnings,
                "stored_at": sample.created_at.isoformat()
            }
            
            if should_clone:
                result["clone_ready"] = True
                result["clone_type"] = clone_type
                result["message"] = f"Congratulations! You have enough samples for {clone_type} voice cloning!"
            
            return True, result
            
        except Exception as e:
            logger.error(f"Failed to store voice sample: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    def _check_cloning_readiness(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user has enough samples for cloning
        Returns (should_clone, clone_type)
        """
        # Get total duration of valid samples
        total_duration = self.db.query(
            func.sum(VoiceSample.duration_seconds)
        ).filter(
            and_(
                VoiceSample.user_id == user_id,
                VoiceSample.status == VoiceSampleStatus.VALIDATED,
                VoiceSample.quality_score >= self.MIN_QUALITY_SCORE
            )
        ).scalar() or 0.0
        
        # Check for existing clones
        existing_instant = self.db.query(VoiceAvatar).filter(
            and_(
                VoiceAvatar.owner_id == user_id,
                VoiceAvatar.clone_type == VoiceCloneType.INSTANT,
                VoiceAvatar.status.in_([AvatarStatus.ACTIVE, AvatarStatus.PROCESSING])
            )
        ).first()
        
        existing_professional = self.db.query(VoiceAvatar).filter(
            and_(
                VoiceAvatar.owner_id == user_id,
                VoiceAvatar.clone_type == VoiceCloneType.PROFESSIONAL,
                VoiceAvatar.status.in_([AvatarStatus.ACTIVE, AvatarStatus.PROCESSING])
            )
        ).first()
        
        # Check readiness
        if not existing_professional and total_duration >= self.PROFESSIONAL_CLONE_MIN_DURATION:
            return True, "professional"
        elif not existing_instant and total_duration >= self.INSTANT_CLONE_MIN_DURATION:
            return True, "instant"
        
        return False, None
    
    def get_user_progress(self, user_id: str) -> VoiceCloneProgress:
        """
        Get detailed progress towards voice cloning
        """
        # Get all valid samples
        samples = self.db.query(VoiceSample).filter(
            and_(
                VoiceSample.user_id == user_id,
                VoiceSample.status == VoiceSampleStatus.VALIDATED
            )
        ).order_by(VoiceSample.created_at.desc()).all()
        
        # Calculate totals
        total_samples = len(samples)
        total_duration = sum(s.duration_seconds for s in samples if s.quality_score >= self.MIN_QUALITY_SCORE)
        avg_quality = np.mean([s.quality_score for s in samples]) if samples else 0.0
        
        # Format duration
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        seconds = int(total_duration % 60)
        duration_formatted = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
        
        # Calculate progress
        instant_progress = min(100.0, (total_duration / self.INSTANT_CLONE_OPTIMAL_DURATION) * 100)
        professional_progress = min(100.0, (total_duration / self.PROFESSIONAL_CLONE_OPTIMAL_DURATION) * 100)
        
        # Check readiness
        instant_ready = total_duration >= self.INSTANT_CLONE_MIN_DURATION
        professional_ready = total_duration >= self.PROFESSIONAL_CLONE_MIN_DURATION
        
        # Calculate needs
        instant_needed = max(0, self.INSTANT_CLONE_MIN_DURATION - total_duration)
        professional_needed = max(0, self.PROFESSIONAL_CLONE_MIN_DURATION - total_duration)
        
        # Estimate samples needed (assuming 10s average)
        avg_sample_duration = (total_duration / total_samples) if total_samples > 0 else 10.0
        samples_needed_instant = int(np.ceil(instant_needed / avg_sample_duration)) if instant_needed > 0 else 0
        samples_needed_professional = int(np.ceil(professional_needed / avg_sample_duration)) if professional_needed > 0 else 0
        
        # Get recent samples
        recent_samples = [
            {
                "id": s.id,
                "duration": s.duration_seconds,
                "quality_score": s.quality_score,
                "created_at": s.created_at.isoformat(),
                "source": s.source
            }
            for s in samples[:5]  # Last 5 samples
        ]
        
        # Generate recommendations
        recommendations = []
        
        if total_samples == 0:
            recommendations.append("Start by sending voice messages - aim for clear speech in a quiet environment")
        elif avg_quality < self.OPTIMAL_QUALITY_SCORE:
            recommendations.append(f"Try recording in a quieter environment for better quality (current avg: {avg_quality:.0f}/100)")
        
        if instant_ready and not professional_ready:
            recommendations.append(f"You can create an instant voice clone now! Need {professional_needed/60:.0f} more minutes for professional cloning")
        elif not instant_ready:
            recommendations.append(f"Send {samples_needed_instant} more voice messages ({instant_needed:.0f} seconds) to enable instant voice cloning")
        
        if total_duration > 0 and total_duration < self.INSTANT_CLONE_MIN_DURATION:
            recommendations.append("Keep your messages between 5-30 seconds for optimal results")
        
        if professional_ready:
            recommendations.append("You have enough samples for professional voice cloning - highest quality available!")
        
        return VoiceCloneProgress(
            user_id=user_id,
            total_samples=total_samples,
            total_duration_seconds=total_duration,
            total_duration_formatted=duration_formatted,
            instant_clone_ready=instant_ready,
            instant_clone_progress=instant_progress,
            professional_clone_ready=professional_ready,
            professional_clone_progress=professional_progress,
            quality_score=avg_quality,
            samples_needed_instant=samples_needed_instant,
            duration_needed_instant=instant_needed,
            samples_needed_professional=samples_needed_professional,
            duration_needed_professional=professional_needed,
            recent_samples=recent_samples,
            recommendations=recommendations
        )
    
    async def trigger_voice_cloning(
        self,
        user_id: str,
        clone_type: str = "instant",
        avatar_name: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Trigger voice cloning for a user
        """
        try:
            # Validate clone type
            if clone_type not in ["instant", "professional"]:
                return False, {"error": "Invalid clone type. Use 'instant' or 'professional'"}
            
            # Check if user has enough samples
            progress = self.get_user_progress(user_id)
            
            if clone_type == "instant" and not progress.instant_clone_ready:
                return False, {
                    "error": "Not enough samples for instant cloning",
                    "current_duration": progress.total_duration_seconds,
                    "required_duration": self.INSTANT_CLONE_MIN_DURATION,
                    "samples_needed": progress.samples_needed_instant
                }
            
            if clone_type == "professional" and not progress.professional_clone_ready:
                return False, {
                    "error": "Not enough samples for professional cloning",
                    "current_duration": progress.total_duration_seconds,
                    "required_duration": self.PROFESSIONAL_CLONE_MIN_DURATION,
                    "samples_needed": progress.samples_needed_professional
                }
            
            # Get the best quality samples up to the optimal duration
            optimal_duration = (
                self.INSTANT_CLONE_OPTIMAL_DURATION if clone_type == "instant"
                else min(self.PROFESSIONAL_CLONE_OPTIMAL_DURATION, progress.total_duration_seconds)
            )
            
            samples = self.db.query(VoiceSample).filter(
                and_(
                    VoiceSample.user_id == user_id,
                    VoiceSample.status == VoiceSampleStatus.VALIDATED,
                    VoiceSample.quality_score >= self.MIN_QUALITY_SCORE
                )
            ).order_by(
                VoiceSample.quality_score.desc(),
                VoiceSample.duration_seconds.desc()
            ).all()
            
            # Select samples up to optimal duration
            selected_samples = []
            total_duration = 0.0
            
            for sample in samples:
                if total_duration >= optimal_duration:
                    break
                selected_samples.append(sample)
                total_duration += sample.duration_seconds
            
            # Load audio data
            audio_samples = []
            for sample in selected_samples:
                try:
                    with open(sample.file_path, 'rb') as f:
                        audio_samples.append(f.read())
                except Exception as e:
                    logger.warning(f"Could not load sample {sample.id}: {e}")
            
            if len(audio_samples) < 1:
                return False, {"error": "Could not load audio samples"}
            
            # Generate avatar name if not provided
            if not avatar_name:
                avatar_name = f"{user_id}_voice_{clone_type}_{datetime.utcnow().strftime('%Y%m%d')}"
            
            # Create avatar record
            avatar = VoiceAvatar(
                owner_id=user_id,
                name=avatar_name,
                description=f"{clone_type.capitalize()} voice clone with {len(selected_samples)} samples ({total_duration:.0f}s)",
                clone_type=VoiceCloneType.INSTANT if clone_type == "instant" else VoiceCloneType.PROFESSIONAL,
                status=AvatarStatus.PROCESSING,
                total_samples=len(selected_samples),
                total_duration=total_duration,
                average_quality=progress.quality_score,
                created_at=datetime.utcnow()
            )
            self.db.add(avatar)
            self.db.commit()
            
            # Link samples to avatar
            for sample in selected_samples:
                sample.avatar_id = avatar.id
            self.db.commit()
            
            # Trigger ElevenLabs cloning
            if self.elevenlabs.is_available():
                try:
                    # Clone with ElevenLabs
                    voice_id = await self.elevenlabs.clone_voice(
                        name=avatar_name,
                        audio_samples=audio_samples[:25],  # ElevenLabs max is 25 samples
                        description=f"Cloned from {len(audio_samples)} WhatsApp voice messages"
                    )
                    
                    if voice_id:
                        avatar.voice_id = voice_id
                        avatar.status = AvatarStatus.ACTIVE
                        avatar.provider = "elevenlabs"
                        logger.info(f"✅ Successfully cloned voice for {user_id}: {voice_id}")
                    else:
                        avatar.status = AvatarStatus.FAILED
                        avatar.processing_error = "ElevenLabs cloning failed"
                        logger.error(f"❌ ElevenLabs cloning failed for {user_id}")
                    
                except Exception as e:
                    avatar.status = AvatarStatus.FAILED
                    avatar.processing_error = str(e)
                    logger.error(f"❌ Error during cloning: {e}")
            else:
                avatar.status = AvatarStatus.FAILED
                avatar.processing_error = "ElevenLabs service not available"
            
            self.db.commit()
            
            if avatar.status == AvatarStatus.ACTIVE:
                return True, {
                    "avatar_id": avatar.id,
                    "voice_id": avatar.voice_id,
                    "name": avatar.name,
                    "clone_type": clone_type,
                    "samples_used": len(selected_samples),
                    "duration_used": total_duration,
                    "status": "active",
                    "message": f"Successfully created {clone_type} voice clone!"
                }
            else:
                return False, {
                    "avatar_id": avatar.id,
                    "error": avatar.processing_error,
                    "status": "failed"
                }
            
        except Exception as e:
            logger.error(f"Failed to trigger cloning: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    def get_user_samples(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of user's voice samples
        """
        query = self.db.query(VoiceSample).filter_by(user_id=user_id)
        
        if status_filter:
            query = query.filter_by(status=VoiceSampleStatus[status_filter.upper()])
        
        samples = query.order_by(
            VoiceSample.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return [
            {
                "id": s.id,
                "file_url": s.file_url,
                "duration": s.duration_seconds,
                "quality_score": s.quality_score,
                "sample_rate": s.sample_rate,
                "channels": s.channels,
                "format": s.format,
                "file_size": s.file_size_bytes,
                "source": s.source,
                "status": s.status.value,
                "avatar_id": s.avatar_id,
                "created_at": s.created_at.isoformat(),
                "validation_issues": s.validation_issues,
                "validation_warnings": s.validation_warnings
            }
            for s in samples
        ]
    
    def delete_sample(self, sample_id: int, user_id: str) -> bool:
        """
        Delete a voice sample
        """
        try:
            sample = self.db.query(VoiceSample).filter_by(
                id=sample_id,
                user_id=user_id
            ).first()
            
            if not sample:
                return False
            
            # Delete file
            if os.path.exists(sample.file_path):
                os.unlink(sample.file_path)
            
            # Delete database record
            self.db.delete(sample)
            self.db.commit()
            
            logger.info(f"Deleted sample {sample_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete sample: {e}")
            self.db.rollback()
            return False