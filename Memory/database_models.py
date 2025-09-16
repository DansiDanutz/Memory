"""
Database Models for Gamified Voice Avatar System
================================================
SQLAlchemy models for PostgreSQL database
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum, JSON, Text, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import enum
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


# Enums
class UserTierEnum(enum.Enum):
    FREE = "free"
    INVITED = "invited"
    PREMIUM = "premium"


class VoiceServiceEnum(enum.Enum):
    NONE = "none"
    COQUI = "coqui"
    ELEVENLABS = "elevenlabs"
    FISH = "fish"


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REWARDED = "rewarded"


# Database Models

class User(Base):
    """User model with voice avatar profile"""
    __tablename__ = 'users'

    # Primary fields
    id = Column(String(50), primary_key=True)
    phone_number = Column(String(20), unique=True, nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Tier and subscription
    tier = Column(Enum(UserTierEnum), default=UserTierEnum.FREE, nullable=False)
    is_paying = Column(Boolean, default=False)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)

    # Voice avatar fields
    voice_service = Column(Enum(VoiceServiceEnum), default=VoiceServiceEnum.NONE)
    voice_id = Column(String(100), nullable=True)
    avatar_created_at = Column(DateTime, nullable=True)
    voice_settings = Column(JSON, nullable=True)  # Service-specific settings

    # Invitation tracking
    invitations_sent = Column(Integer, default=0)
    successful_invites = Column(Integer, default=0)
    invitation_code = Column(String(20), unique=True, nullable=True)
    invited_by_id = Column(String(50), ForeignKey('users.id'), nullable=True)

    # Usage tracking
    total_speech_generations = Column(Integer, default=0)
    total_characters_generated = Column(Integer, default=0)
    last_active = Column(DateTime, default=datetime.utcnow)

    # Preferences
    preferences = Column(JSON, default={})
    notifications_enabled = Column(Boolean, default=True)
    language = Column(String(10), default="en")

    # Relationships
    sent_invitations = relationship("Invitation", foreign_keys="Invitation.inviter_id", back_populates="inviter")
    received_invitation = relationship("Invitation", foreign_keys="Invitation.invited_id", uselist=False)
    invited_by = relationship("User", remote_side=[id], foreign_keys=[invited_by_id])
    voice_samples = relationship("VoiceSample", back_populates="user", cascade="all, delete-orphan")
    speech_generations = relationship("SpeechGeneration", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False)

    # Indexes
    __table_args__ = (
        Index('idx_user_tier', 'tier'),
        Index('idx_user_phone', 'phone_number'),
        Index('idx_user_invitation_code', 'invitation_code'),
    )


class Invitation(Base):
    """Invitation tracking model"""
    __tablename__ = 'invitations'

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)

    # Users involved
    inviter_id = Column(String(50), ForeignKey('users.id'), nullable=False)
    invited_id = Column(String(50), ForeignKey('users.id'), nullable=True)

    # Status tracking
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)

    # Tracking
    app_installed = Column(Boolean, default=False)
    reward_claimed = Column(Boolean, default=False)
    reward_claimed_at = Column(DateTime, nullable=True)

    # Sharing info
    share_method = Column(String(50), nullable=True)  # whatsapp, sms, email, link
    share_message = Column(Text, nullable=True)

    # Relationships
    inviter = relationship("User", foreign_keys=[inviter_id], back_populates="sent_invitations")
    invited = relationship("User", foreign_keys=[invited_id])

    __table_args__ = (
        Index('idx_invitation_status', 'status'),
        Index('idx_invitation_inviter', 'inviter_id'),
    )


class VoiceSample(Base):
    """Voice samples for avatar creation"""
    __tablename__ = 'voice_samples'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), ForeignKey('users.id'), nullable=False)

    # File info
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # bytes
    duration = Column(Float)  # seconds
    format = Column(String(10))  # wav, mp3, etc.

    # Quality metrics
    quality_score = Column(Float, nullable=True)
    noise_level = Column(Float, nullable=True)
    clarity_score = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)

    # Service-specific IDs
    elevenlabs_sample_id = Column(String(100), nullable=True)
    coqui_sample_id = Column(String(100), nullable=True)
    fish_sample_id = Column(String(100), nullable=True)

    # Relationship
    user = relationship("User", back_populates="voice_samples")


class SpeechGeneration(Base):
    """Track speech generation requests"""
    __tablename__ = 'speech_generations'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), ForeignKey('users.id'), nullable=False)

    # Request details
    text = Column(Text, nullable=False)
    text_length = Column(Integer)
    voice_id = Column(String(100))
    service_used = Column(Enum(VoiceServiceEnum))

    # Options
    emotion = Column(String(50), nullable=True)
    speed = Column(Float, default=1.0)
    pitch = Column(Float, default=1.0)

    # Response
    audio_url = Column(String(500), nullable=True)
    audio_duration = Column(Float, nullable=True)  # seconds
    format = Column(String(10))  # mp3, wav, etc.

    # Performance
    latency_ms = Column(Integer)
    cached = Column(Boolean, default=False)

    # Cost tracking
    cost = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="speech_generations")

    __table_args__ = (
        Index('idx_generation_user', 'user_id'),
        Index('idx_generation_created', 'created_at'),
    )


class Subscription(Base):
    """User subscription management"""
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), ForeignKey('users.id'), unique=True, nullable=False)

    # Plan details
    plan_name = Column(String(50), nullable=False)  # starter, premium, enterprise
    tier = Column(Enum(UserTierEnum), nullable=False)

    # Billing
    stripe_subscription_id = Column(String(100), unique=True, nullable=True)
    price_cents = Column(Integer)  # Price in cents
    currency = Column(String(3), default="USD")
    billing_period = Column(String(20))  # monthly, yearly

    # Status
    status = Column(String(20), nullable=False)  # active, canceled, past_due
    started_at = Column(DateTime, nullable=False)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    canceled_at = Column(DateTime, nullable=True)

    # Usage limits
    monthly_character_limit = Column(Integer, nullable=True)
    monthly_generation_limit = Column(Integer, nullable=True)
    voice_avatar_slots = Column(Integer, default=1)

    # Current usage
    current_month_characters = Column(Integer, default=0)
    current_month_generations = Column(Integer, default=0)

    # Relationship
    user = relationship("User", back_populates="subscription")


class VoiceAvatarSlot(Base):
    """Manage voice avatar slots for users with limits"""
    __tablename__ = 'voice_avatar_slots'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), ForeignKey('users.id'), nullable=False)

    # Slot info
    slot_number = Column(Integer, nullable=False)
    voice_id = Column(String(100), nullable=False)
    service = Column(Enum(VoiceServiceEnum), nullable=False)

    # Avatar details
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)

    # Usage
    total_uses = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'slot_number', name='unique_user_slot'),
        Index('idx_slot_user', 'user_id'),
        Index('idx_slot_active', 'is_active'),
    )


class UsageAnalytics(Base):
    """Analytics and usage tracking"""
    __tablename__ = 'usage_analytics'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), ForeignKey('users.id'), nullable=False)

    # Time period
    date = Column(DateTime, nullable=False)
    hour = Column(Integer)  # 0-23

    # Metrics
    speech_generations = Column(Integer, default=0)
    characters_generated = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    errors = Column(Integer, default=0)

    # Performance
    avg_latency_ms = Column(Float)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)

    # Cost
    total_cost = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint('user_id', 'date', 'hour', name='unique_user_date_hour'),
        Index('idx_analytics_user', 'user_id'),
        Index('idx_analytics_date', 'date'),
    )


class SystemMetrics(Base):
    """System-wide metrics"""
    __tablename__ = 'system_metrics'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # User metrics
    total_users = Column(Integer, default=0)
    free_users = Column(Integer, default=0)
    invited_users = Column(Integer, default=0)
    premium_users = Column(Integer, default=0)

    # Invitation metrics
    total_invitations = Column(Integer, default=0)
    accepted_invitations = Column(Integer, default=0)
    pending_invitations = Column(Integer, default=0)

    # Voice metrics
    total_avatars = Column(Integer, default=0)
    coqui_avatars = Column(Integer, default=0)
    elevenlabs_avatars = Column(Integer, default=0)

    # Usage metrics
    daily_generations = Column(Integer, default=0)
    daily_characters = Column(Integer, default=0)
    daily_active_users = Column(Integer, default=0)

    # Financial metrics
    monthly_revenue = Column(Float, default=0.0)
    daily_cost = Column(Float, default=0.0)

    __table_args__ = (
        Index('idx_metrics_timestamp', 'timestamp'),
    )


# Database initialization

def init_database():
    """Initialize database with tables"""
    # Get database URL from environment
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/voice_avatar_db"
    )

    # Create engine
    engine = create_engine(database_url)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    Session = sessionmaker(bind=engine)

    return engine, Session


def get_session():
    """Get database session"""
    _, Session = init_database()
    return Session()


# Query helpers

class DatabaseQueries:
    """Common database queries"""

    @staticmethod
    def get_user_by_id(session, user_id: str):
        """Get user by ID"""
        return session.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_invitation_code(session, code: str):
        """Get user who owns invitation code"""
        return session.query(User).filter(User.invitation_code == code).first()

    @staticmethod
    def count_successful_invites(session, user_id: str):
        """Count successful invitations for user"""
        return session.query(Invitation).filter(
            Invitation.inviter_id == user_id,
            Invitation.status == InvitationStatus.ACCEPTED
        ).count()

    @staticmethod
    def get_leaderboard(session, limit: int = 10):
        """Get top inviters"""
        return session.query(User).order_by(
            User.successful_invites.desc()
        ).limit(limit).all()

    @staticmethod
    def get_user_usage_today(session, user_id: str):
        """Get user's usage for today"""
        from datetime import date
        today = date.today()

        return session.query(UsageAnalytics).filter(
            UsageAnalytics.user_id == user_id,
            UsageAnalytics.date == today
        ).all()

    @staticmethod
    def get_pending_invitations(session, user_id: str):
        """Get pending invitations for user"""
        return session.query(Invitation).filter(
            Invitation.inviter_id == user_id,
            Invitation.status == InvitationStatus.PENDING
        ).all()

    @staticmethod
    def get_active_subscriptions(session):
        """Get all active subscriptions"""
        return session.query(Subscription).filter(
            Subscription.status == "active"
        ).all()


if __name__ == "__main__":
    # Initialize database
    print("Initializing database...")
    engine, Session = init_database()
    print("Database initialized successfully!")

    # Create sample data
    session = Session()

    # Create test user
    test_user = User(
        id="test_user_123",
        phone_number="+1234567890",
        tier=UserTierEnum.FREE,
        invitation_code="TEST123"
    )

    session.add(test_user)
    session.commit()

    print(f"Created test user: {test_user.id}")
    session.close()