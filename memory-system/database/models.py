#!/usr/bin/env python3
"""
Database Models for Digital Immortality Platform
SQLAlchemy models for production implementation
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON, Text, Boolean, Integer, ForeignKey, Index, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
import os

Base = declarative_base()

# Enums for type safety
class SourceType(enum.Enum):
    CHAT_MESSAGE = "chat_message"
    EMAIL = "email"
    DOCUMENT = "document"
    CALENDAR_EVENT = "calendar_event"
    PHOTO = "photo"
    VOICE_MESSAGE = "voice_message"
    MANUAL_ENTRY = "manual_entry"
    WEB_CLIP = "web_clip"
    SMS = "sms"
    SOCIAL_MEDIA = "social_media"

class PatternType(enum.Enum):
    TEMPORAL = "temporal"
    BEHAVIORAL = "behavioral"
    SOCIAL = "social"
    LOCATION = "location"
    EMOTIONAL = "emotional"
    ACTIVITY = "activity"
    COMMUNICATION = "communication"
    ROUTINE = "routine"

class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(enum.Enum):
    HARVEST = "harvest"
    PATTERN_ANALYSIS = "pattern_analysis"
    INSIGHT_GENERATION = "insight_generation"
    DAILY_DIGEST = "daily_digest"
    BACKUP = "backup"

class AgreementStatus(enum.Enum):
    PENDING = "pending"
    AGREED = "agreed"
    NOT_AGREED = "not_agreed"
    REVIEW = "review"

class SecurityLevel(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    ULTRA_SECRET = "ultra_secret"

# Models
class HarvestedItem(Base):
    """Model for harvested memory items"""
    __tablename__ = 'harvested_items'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    content_type = Column(String, nullable=True)
    quality_score = Column(Float, default=0.0)
    extra_metadata = Column(JSON, default={})
    participants = Column(JSON, default=[])
    tags = Column(JSON, default=[])
    language = Column(String, default="en")
    sentiment = Column(JSON, default={})
    location = Column(JSON, nullable=True)
    attachments = Column(JSON, default=[])
    security_level = Column(Enum(SecurityLevel), default=SecurityLevel.PRIVATE)
    agreement_status = Column(Enum(AgreementStatus), default=AgreementStatus.PENDING)
    duplicate_of = Column(String, nullable=True)  # Reference to original if duplicate
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patterns = relationship("DetectedPattern", back_populates="supporting_memories_rel", secondary="pattern_memories")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_user_source', 'user_id', 'source_type'),
        Index('idx_agreement_status', 'user_id', 'agreement_status'),
    )

class DetectedPattern(Base):
    """Model for detected behavioral patterns"""
    __tablename__ = 'detected_patterns'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    pattern_type = Column(Enum(PatternType), nullable=False)
    strength = Column(Float, nullable=False)  # 0.0 to 1.0
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    description = Column(Text, nullable=False)
    frequency = Column(JSON, default={})  # Frequency details
    triggers = Column(JSON, default=[])
    participants = Column(JSON, default=[])
    locations = Column(JSON, default=[])
    time_windows = Column(JSON, default=[])
    supporting_memories = Column(JSON, default=[])  # List of memory IDs
    prediction_accuracy = Column(Float, default=0.0)
    extra_metadata = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    supporting_memories_rel = relationship("HarvestedItem", back_populates="patterns", secondary="pattern_memories")
    insights = relationship("BehavioralInsight", back_populates="pattern", secondary="insight_patterns")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_pattern_type', 'user_id', 'pattern_type'),
        Index('idx_user_strength', 'user_id', 'strength'),
        Index('idx_active_patterns', 'user_id', 'is_active'),
    )

class BehavioralInsight(Base):
    """Model for behavioral insights generated from patterns"""
    __tablename__ = 'behavioral_insights'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    insight_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    supporting_patterns = Column(JSON, default=[])  # List of pattern IDs
    recommendations = Column(JSON, default=[])  # Actionable recommendations
    impact_score = Column(Float, default=0.0)  # Potential impact of following recommendations
    extra_metadata = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    is_read = Column(Boolean, default=False)
    action_taken = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pattern = relationship("DetectedPattern", back_populates="insights", secondary="insight_patterns")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_insight_type', 'user_id', 'insight_type'),
        Index('idx_user_confidence', 'user_id', 'confidence'),
        Index('idx_unread_insights', 'user_id', 'is_read'),
    )

class Job(Base):
    """Model for background job tracking"""
    __tablename__ = 'jobs'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(Enum(JobType), nullable=False)
    user_id = Column(String, nullable=True)  # Nullable for system-wide jobs
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    extra_metadata = Column(JSON, default={})
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_user_jobs', 'user_id', 'job_type'),
        Index('idx_scheduled_jobs', 'scheduled_at', 'status'),
    )

class AuditLog(Base):
    """Model for security audit logging"""
    __tablename__ = 'audit_logs'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)  # Nullable for system events
    action = Column(String, nullable=False)  # e.g., "memory.access", "pattern.view", "insight.create"
    resource = Column(String, nullable=True)  # Resource ID being accessed
    resource_type = Column(String, nullable=True)  # Type of resource
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    voice_verified = Column(Boolean, default=False)
    security_level = Column(Enum(SecurityLevel), nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column(JSON, default={})
    duration_ms = Column(Integer, nullable=True)  # Request duration in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_audit_user', 'user_id', 'created_at'),
        Index('idx_audit_action', 'action', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource'),
        Index('idx_audit_security', 'security_level', 'voice_verified'),
    )

# Association tables for many-to-many relationships
class PatternMemories(Base):
    """Association table for patterns and memories"""
    __tablename__ = 'pattern_memories'
    
    pattern_id = Column(String, ForeignKey('detected_patterns.id'), primary_key=True)
    memory_id = Column(String, ForeignKey('harvested_items.id'), primary_key=True)
    relevance_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class InsightPatterns(Base):
    """Association table for insights and patterns"""
    __tablename__ = 'insight_patterns'
    
    insight_id = Column(String, ForeignKey('behavioral_insights.id'), primary_key=True)
    pattern_id = Column(String, ForeignKey('detected_patterns.id'), primary_key=True)
    contribution_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database connection and session management
class DatabaseManager:
    """Manage database connections and sessions"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.environ.get('DATABASE_URL', 'sqlite:///memory_system.db')
        
        # PostgreSQL specific optimizations
        if 'postgresql' in self.database_url:
            # Add connection pool settings
            self.engine = create_engine(
                self.database_url,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        else:
            self.engine = create_engine(self.database_url, echo=False)
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def init_database(self):
        """Initialize database with tables and default data"""
        self.create_tables()
        print("✅ Database initialized successfully")

# Export for use in other modules
__all__ = [
    'Base',
    'HarvestedItem',
    'DetectedPattern',
    'BehavioralInsight',
    'Job',
    'AuditLog',
    'PatternMemories',
    'InsightPatterns',
    'DatabaseManager',
    'SourceType',
    'PatternType',
    'JobStatus',
    'JobType',
    'AgreementStatus',
    'SecurityLevel'
]