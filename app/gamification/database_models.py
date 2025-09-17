"""
Database models for the Gamified Voice Avatar System
Uses SQLAlchemy with PostgreSQL backend
"""

import os
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, 
    ForeignKey, Enum, UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# Database connection setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/gamification")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class InvitationStatus(enum.Enum):
    """Status of an invitation"""
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"

class AvatarStatus(enum.Enum):
    """Status of a voice avatar"""
    DRAFT = "draft"
    PROCESSING = "processing"
    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"

class VoiceSampleStatus(enum.Enum):
    """Status of a voice sample"""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PROCESSING = "processing"
    USED = "used"

class VoiceCloneType(enum.Enum):
    """Type of voice clone"""
    INSTANT = "instant"  # 1-2 minutes of audio
    PROFESSIONAL = "professional"  # 30+ minutes of audio

class AccessLevel(enum.Enum):
    """Contact access levels"""
    BASIC = "basic"
    ENHANCED = "enhanced"
    PREMIUM = "premium"
    VIP = "vip"

class AchievementType(enum.Enum):
    """Types of achievements"""
    FIRST_INVITE = "first_invite"
    FIVE_INVITES = "five_invites"
    TEN_INVITES = "ten_invites"
    FIRST_AVATAR = "first_avatar"
    CONTACT_MASTER = "contact_master"
    VOICE_COLLECTOR = "voice_collector"
    TRUST_BUILDER = "trust_builder"
    COMMUNITY_LEADER = "community_leader"

class QuestType(enum.Enum):
    """Types of quests"""
    DAILY = "daily"
    WEEKLY = "weekly"
    FLASH = "flash"
    EVENT = "event"

class QuestDifficulty(enum.Enum):
    """Quest difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EPIC = "epic"

class QuestStatus(enum.Enum):
    """Quest completion status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CLAIMED = "claimed"
    EXPIRED = "expired"

class AlertType(enum.Enum):
    """Types of FOMO alerts"""
    EXPIRING_REWARD = "expiring_reward"
    FLASH_SALE = "flash_sale"
    LIMITED_SLOTS = "limited_slots"
    FRIEND_ACTIVITY = "friend_activity"
    LAST_CHANCE = "last_chance"
    STREAK_RISK = "streak_risk"
    FOMO = "fomo"

class AlertPriority(enum.Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class User(Base):
    """User profile with gamification stats"""
    __tablename__ = "gamification_users"
    
    id = Column(String, primary_key=True)  # Phone number as ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Basic info
    display_name = Column(String(100))
    avatar_url = Column(Text)
    timezone = Column(String(50), default="UTC")
    
    # Gamification stats
    total_invites_sent = Column(Integer, default=0, nullable=False)
    total_invites_accepted = Column(Integer, default=0, nullable=False)
    total_contact_slots = Column(Integer, default=0, nullable=False)
    used_contact_slots = Column(Integer, default=0, nullable=False)
    total_voice_avatars = Column(Integer, default=0, nullable=False)
    trust_score = Column(Float, default=0.0, nullable=False)
    points = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    
    # Feature flags
    is_premium = Column(Boolean, default=False, nullable=False)
    is_beta_tester = Column(Boolean, default=False, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    
    # Settings
    notification_preferences = Column(JSON, default={})
    privacy_settings = Column(JSON, default={})
    
    # Relationships
    invitations_sent = relationship("Invitation", back_populates="sender", 
                                   foreign_keys="Invitation.sender_id")
    invitations_received = relationship("Invitation", back_populates="recipient",
                                       foreign_keys="Invitation.recipient_id")
    contact_slots = relationship("ContactSlot", back_populates="owner")
    voice_avatars = relationship("VoiceAvatar", back_populates="owner")
    achievements = relationship("Achievement", back_populates="user")
    rewards = relationship("Reward", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_trust_score', 'trust_score'),
        Index('idx_user_points', 'points'),
        Index('idx_user_level', 'level'),
    )

class Invitation(Base):
    """Invitation tracking system"""
    __tablename__ = "invitations"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    
    sender_id = Column(String, ForeignKey("gamification_users.id"), nullable=False)
    recipient_id = Column(String, ForeignKey("gamification_users.id"))
    
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime)
    accepted_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)
    
    # WhatsApp message details
    whatsapp_message_id = Column(String(100))
    recipient_phone = Column(String(50))
    message_template = Column(Text)
    
    # Tracking
    clicks = Column(Integer, default=0)
    referral_source = Column(String(50))
    extra_metadata = Column(JSON, default={})
    
    # Relationships
    sender = relationship("User", back_populates="invitations_sent",
                         foreign_keys=[sender_id])
    recipient = relationship("User", back_populates="invitations_received",
                           foreign_keys=[recipient_id])
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_invitation_status', 'status'),
        Index('idx_invitation_sender', 'sender_id'),
        Index('idx_invitation_expires', 'expires_at'),
    )

class ContactSlot(Base):
    """Contact slots earned by users"""
    __tablename__ = "contact_slots"
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(String, ForeignKey("gamification_users.id"), nullable=False)
    
    # Slot details
    slot_number = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    contact_id = Column(String)  # Phone number of contact if used
    
    # Permissions and scoring
    access_level = Column(Enum(AccessLevel), default=AccessLevel.BASIC, nullable=False)
    permission_score = Column(Float, default=0.0, nullable=False)
    trust_level = Column(Float, default=0.0, nullable=False)
    
    # Metadata
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime)
    earned_from_invitation_id = Column(Integer, ForeignKey("invitations.id"))
    
    # Contact settings
    allowed_categories = Column(JSON, default=["GENERAL"])  # Memory categories allowed
    blocked_times = Column(JSON, default=[])  # Times when contact can't access
    interaction_limit = Column(Integer, default=100)  # Daily interaction limit
    
    # Relationships
    owner = relationship("User", back_populates="contact_slots")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('owner_id', 'slot_number', name='uq_owner_slot'),
        Index('idx_slot_owner', 'owner_id'),
        Index('idx_slot_used', 'is_used'),
    )

class VoiceAvatar(Base):
    """Voice avatars created by users"""
    __tablename__ = "voice_avatars"
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(String, ForeignKey("gamification_users.id"), nullable=False)
    
    # Avatar details
    name = Column(String(100), nullable=False)
    description = Column(Text)
    voice_id = Column(String(100))  # ElevenLabs voice ID
    
    # Premium gating fields
    is_locked = Column(Boolean, default=True, nullable=False)  # Locked for free users
    preview_generated = Column(Boolean, default=False, nullable=False)
    preview_text = Column(Text)  # Sample text for preview
    unlock_date = Column(DateTime)  # When avatar was unlocked
    
    # Provider details
    provider = Column(String(50), default="elevenlabs")  # elevenlabs, coqui, fish
    model_id = Column(String(100))
    
    status = Column(Enum(AvatarStatus), default=AvatarStatus.DRAFT, nullable=False)
    clone_type = Column(Enum(VoiceCloneType), default=VoiceCloneType.INSTANT)
    
    # Voice samples
    sample_urls = Column(JSON, default=[])
    training_data = Column(JSON, default={})
    voice_characteristics = Column(JSON, default={})  # pitch, speed, tone, etc.
    
    # Clone statistics
    total_samples = Column(Integer, default=0)
    total_duration = Column(Float, default=0.0)  # Total duration in seconds
    average_quality = Column(Float, default=0.0)  # Average quality score
    processing_error = Column(Text)
    
    # Usage stats
    times_used = Column(Integer, default=0, nullable=False)
    total_characters = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime)
    
    # Settings
    is_public = Column(Boolean, default=False, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    language = Column(String(10), default="en", nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="voice_avatars")
    
    # Indexes
    __table_args__ = (
        Index('idx_avatar_owner', 'owner_id'),
        Index('idx_avatar_status', 'status'),
        Index('idx_avatar_provider', 'provider'),
    )

class Achievement(Base):
    """User achievements and badges"""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("gamification_users.id"), nullable=False)
    
    type = Column(Enum(AchievementType), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(100))
    
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    progress = Column(Float, default=100.0)  # Percentage
    extra_metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="achievements")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'type', name='uq_user_achievement'),
        Index('idx_achievement_user', 'user_id'),
        Index('idx_achievement_type', 'type'),
    )

class Reward(Base):
    """Rewards earned by users"""
    __tablename__ = "rewards"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("gamification_users.id"), nullable=False)
    
    # Reward details
    type = Column(String(50), nullable=False)  # contact_slot, voice_avatar, points, etc.
    amount = Column(Integer, default=1, nullable=False)
    description = Column(Text)
    
    # Source
    source_type = Column(String(50), nullable=False)  # invitation, achievement, milestone
    source_id = Column(String(100))
    
    earned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    claimed_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    is_claimed = Column(Boolean, default=False, nullable=False)
    extra_metadata = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="rewards")
    
    # Indexes
    __table_args__ = (
        Index('idx_reward_user', 'user_id'),
        Index('idx_reward_type', 'type'),
        Index('idx_reward_claimed', 'is_claimed'),
    )

class VoiceSample(Base):
    """Voice samples for training avatars"""
    __tablename__ = "voice_samples"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("gamification_users.id"), nullable=False, index=True)
    avatar_id = Column(Integer, ForeignKey("voice_avatars.id"), nullable=True)  # Nullable until assigned to avatar
    
    # File details
    file_path = Column(Text, nullable=False)  # Local file path
    file_url = Column(Text, nullable=False)  # Public URL
    file_size_bytes = Column(Integer, default=0)
    
    # Audio details
    duration_seconds = Column(Float, nullable=False)
    sample_rate = Column(Integer, default=16000)
    channels = Column(Integer, default=1)
    format = Column(String(20), default="wav")
    
    # Transcription
    text_transcript = Column(Text)
    
    # Quality metrics
    quality_score = Column(Float, default=0.0)  # 0-100 overall quality
    audio_quality = Column(Float)  # 0-1 score
    clarity_score = Column(Float)  # 0-1 score
    noise_level = Column(Float)  # 0-1 score
    signal_to_noise = Column(Float)  # SNR in dB
    
    # Processing status
    status = Column(Enum(VoiceSampleStatus), default=VoiceSampleStatus.PENDING, nullable=False)
    is_processed = Column(Boolean, default=False, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    processing_error = Column(Text)
    
    # Validation
    validation_issues = Column(JSON, default=[])
    validation_warnings = Column(JSON, default=[])
    
    # Source and metadata
    source = Column(String(50), default="whatsapp")  # whatsapp, telegram, web, etc.
    extra_metadata = Column(JSON, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_sample_avatar', 'avatar_id'),
        Index('idx_sample_processed', 'is_processed'),
    )

class Leaderboard(Base):
    """Leaderboard entries for various metrics"""
    __tablename__ = "leaderboard"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("gamification_users.id"), nullable=False)
    
    # Metrics
    metric_type = Column(String(50), nullable=False)  # invites, avatars, trust, points
    metric_value = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    
    # Time period
    period = Column(String(20), nullable=False)  # daily, weekly, monthly, all_time
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'metric_type', 'period', 'period_start', 
                        name='uq_user_metric_period'),
        Index('idx_leaderboard_metric', 'metric_type'),
        Index('idx_leaderboard_rank', 'rank'),
        Index('idx_leaderboard_period', 'period'),
    )

# New Streak and Variable Reward Models

class UserStreak(Base):
    """User streak tracking for daily engagement"""
    __tablename__ = "user_streaks"
    
    user_id = Column(String, primary_key=True, index=True)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_checkin = Column(DateTime)
    freeze_tokens = Column(Integer, default=0, nullable=False)
    freeze_active = Column(Boolean, default=False, nullable=False)
    freeze_expires = Column(DateTime)
    total_checkins = Column(Integer, default=0, nullable=False)
    total_freezes_used = Column(Integer, default=0, nullable=False)
    missed_yesterday = Column(Boolean, default=False, nullable=False)
    milestones_reached = Column(JSON, default=list, nullable=False)
    perfect_weeks = Column(Integer, default=0, nullable=False)
    perfect_months = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_streak_checkin', 'last_checkin'),
        Index('idx_user_streak_freeze', 'freeze_active', 'freeze_expires'),
    )

# StreakActivity temporarily disabled due to foreign key constraint mismatch
# Will be re-enabled after proper data type migration
# class StreakActivity(Base):
#     """Track daily activities for streak system"""
#     __tablename__ = "streak_activities"
#     
#     id = Column(Integer, primary_key=True)
#     user_id = Column(UUID(as_uuid=True), ForeignKey('user_streaks.user_id'), nullable=False, index=True)
#     activity_type = Column(String, nullable=False)  # 'check_in', 'memory_created', 'invitation_sent'
#     activity_date = Column(DateTime, default=datetime.utcnow, nullable=False)
#     points_earned = Column(Integer, default=0, nullable=False)
#     extra_metadata = Column(JSON)
#     
#     __table_args__ = (
#         Index('idx_activity_user_date', 'user_id', 'activity_date'),
#         Index('idx_activity_type', 'activity_type'),
#     )

class UserRewardState(Base):
    """Track user reward state for variable rewards"""
    __tablename__ = "user_reward_states"
    
    user_id = Column(String, primary_key=True, index=True)
    total_spins = Column(Integer, default=0, nullable=False)
    spins_since_rare = Column(Integer, default=0, nullable=False)
    spins_since_epic = Column(Integer, default=0, nullable=False)
    spins_since_legendary = Column(Integer, default=0, nullable=False)
    daily_spins_used = Column(Integer, default=0, nullable=False)
    last_daily_spin = Column(DateTime)
    last_free_spin = Column(DateTime)
    xp_multiplier = Column(Float, default=1.0, nullable=False)
    xp_multiplier_expires = Column(DateTime)
    total_rewards_earned = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class RewardHistory(Base):
    """History of all rewards earned"""
    __tablename__ = "reward_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('user_reward_states.user_id'), nullable=False, index=True)
    reward_type = Column(String, nullable=False)  # 'xp', 'coins', 'contact_slot', 'voice_credit'
    reward_value = Column(JSON, nullable=False)  # Store reward details as JSON
    trigger_event = Column(String, nullable=False)  # 'daily_spin', 'streak_milestone', 'invitation'
    rarity = Column(String, nullable=False)  # 'common', 'uncommon', 'rare', 'epic', 'legendary'
    slot_result = Column(JSON)  # Store the slot machine result symbols
    was_pity = Column(Boolean, default=False, nullable=False)
    was_jackpot = Column(Boolean, default=False, nullable=False)
    multiplier_applied = Column(Float, default=1.0, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_reward_history_user_time', 'user_id', 'timestamp'),
        Index('idx_reward_history_type', 'reward_type'),
        Index('idx_reward_history_rarity', 'rarity'),
    )

class Quest(Base):
    """Comprehensive quest system for all quest types"""
    __tablename__ = "quests"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('gamification_users.id'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    type = Column(Enum(QuestType), nullable=False)
    difficulty = Column(Enum(QuestDifficulty), nullable=False)
    requirement_type = Column(String(100), nullable=False)  # 'create_memory', 'send_invitation', etc.
    target = Column(Integer, nullable=False)  # Target count to complete
    rewards = Column(JSON, nullable=False)  # {xp: 100, points: 50, items: [...]}
    status = Column(Enum(QuestStatus), default=QuestStatus.ACTIVE, nullable=False)
    is_flash = Column(Boolean, default=False, nullable=False)  # Is this a flash quest?
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    progress = relationship("UserQuestProgress", back_populates="quest", uselist=False)
    
    __table_args__ = (
        Index('idx_quest_user_type', 'user_id', 'type'),
        Index('idx_quest_status', 'status'),
        Index('idx_quest_expires', 'expires_at'),
        Index('idx_quest_flash', 'is_flash'),
    )

class UserQuestProgress(Base):
    """Track user progress on quests"""
    __tablename__ = "user_quest_progress"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('gamification_users.id'), nullable=False)
    quest_id = Column(Integer, ForeignKey('quests.id'), nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    completed_at = Column(DateTime)
    claimed_at = Column(DateTime)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    quest = relationship("Quest", back_populates="progress")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'quest_id', name='unique_user_quest'),
        Index('idx_quest_progress_user', 'user_id'),
        Index('idx_quest_progress_status', 'completed_at', 'claimed_at'),
    )

class FOMOAlert(Base):
    """FOMO alerts and urgency notifications"""
    __tablename__ = "fomo_alerts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('gamification_users.id'), nullable=False, index=True)
    type = Column(Enum(AlertType), nullable=False)
    priority = Column(Enum(AlertPriority), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    action_text = Column(String(100))
    action_url = Column(String(500))
    icon = Column(String(50))
    color = Column(String(20))  # Hex color for urgency
    alert_metadata = Column(JSON, default={})  # Additional alert data
    expires_at = Column(DateTime, nullable=False)
    dismissed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_fomo_alert_user', 'user_id', 'expires_at'),
        Index('idx_fomo_alert_type', 'type'),
        Index('idx_fomo_alert_priority', 'priority'),
    )

class ProgressiveJackpot(Base):
    """Progressive jackpot for slot machine"""
    __tablename__ = "progressive_jackpots"
    
    id = Column(Integer, primary_key=True)
    jackpot_type = Column(String, unique=True, nullable=False)  # 'daily', 'weekly', 'mega'
    current_value = Column(Integer, default=0, nullable=False)
    base_value = Column(Integer, nullable=False)
    increment_rate = Column(Float, default=0.01, nullable=False)  # % of each spin added to jackpot
    last_won_by = Column(String)
    last_won_at = Column(DateTime)
    total_contributions = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# Create tables
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

# Database session management
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()