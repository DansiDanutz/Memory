-- DIGITAL IMMORTALITY PLATFORM - PostgreSQL DATABASE SETUP
-- PostgreSQL-compatible version of the schema

-- ======================================
-- EXTENSIONS & INITIAL SETUP
-- ======================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ======================================
-- DROP EXISTING TABLES (if recreating)
-- ======================================
DROP TABLE IF EXISTS user_streaks CASCADE;
DROP TABLE IF EXISTS achievements CASCADE;
DROP TABLE IF EXISTS user_activity CASCADE;
DROP TABLE IF EXISTS message_monitoring CASCADE;
DROP TABLE IF EXISTS call_recordings CASCADE;
DROP TABLE IF EXISTS voice_auth CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS family_access CASCADE;
DROP TABLE IF EXISTS mutual_connections CASCADE;
DROP TABLE IF EXISTS commitments CASCADE;
DROP TABLE IF EXISTS secret_memories CASCADE;
DROP TABLE IF EXISTS contact_profiles CASCADE;
DROP TABLE IF EXISTS memories CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ======================================
-- 1. USERS TABLE - Digital Identities
-- ======================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    phone_number TEXT UNIQUE,
    display_name TEXT NOT NULL,
    voice_enrolled BOOLEAN DEFAULT FALSE,
    voice_samples JSONB DEFAULT '[]',
    voice_print BYTEA,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'basic', 'pro', 'elite')),
    credits_available INTEGER DEFAULT 50,
    credits_total INTEGER DEFAULT 50,
    credits_used INTEGER DEFAULT 0,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    telegram_user_id TEXT,
    whatsapp_user_id TEXT,
    enrollment_status TEXT DEFAULT 'pending',
    avatar_config JSONB DEFAULT '{}',
    emergency_contacts JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 2. MEMORIES TABLE - Eternal Storage
-- ======================================
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    memory_number SERIAL UNIQUE,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    subcategory TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    tags TEXT[],
    ai_insights JSONB DEFAULT '{}',
    -- Remove vector embedding for now (requires pgvector extension)
    -- embedding vector(1536),
    approved BOOLEAN DEFAULT TRUE,
    platform TEXT DEFAULT 'app',
    message_type TEXT DEFAULT 'text',
    media_urls TEXT[],
    location JSONB,
    emotional_tone TEXT,
    importance_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 3. CONTACT PROFILES - Relationships
-- ======================================
CREATE TABLE contact_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    contact_id TEXT NOT NULL,
    name TEXT NOT NULL,
    phone_number TEXT,
    email TEXT,
    relationship_type TEXT DEFAULT 'unknown',
    avatar_enabled BOOLEAN DEFAULT FALSE,
    avatar_personality JSONB DEFAULT '{}',
    trust_level INTEGER DEFAULT 5 CHECK (trust_level >= 0 AND trust_level <= 10),
    accumulated_facts JSONB DEFAULT '[]',
    conversation_history JSONB DEFAULT '[]',
    personality_profile JSONB DEFAULT '{}',
    total_messages INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    last_interaction TIMESTAMPTZ,
    interaction_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, contact_id)
);

-- ======================================
-- 4. SECRET MEMORIES - Three-tier Vault
-- ======================================
CREATE TABLE secret_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content_encrypted TEXT NOT NULL,
    encryption_key_id TEXT,
    level TEXT NOT NULL CHECK (level IN ('secret', 'confidential', 'ultra_secret')),
    authorized_contacts TEXT[],
    unlock_condition TEXT,
    unlock_date TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    auto_destroy_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 5. COMMITMENTS - Smart Reminders
-- ======================================
CREATE TABLE commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    due_date TIMESTAMPTZ,
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    completed BOOLEAN DEFAULT FALSE,
    promised_to TEXT,
    reminder_sent BOOLEAN DEFAULT FALSE,
    reminder_count INTEGER DEFAULT 0,
    snooze_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    recurring_pattern TEXT
);

-- ======================================
-- 6. MUTUAL CONNECTIONS - Social Gaming
-- ======================================
CREATE TABLE mutual_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_a UUID REFERENCES users(id) ON DELETE CASCADE,
    user_b UUID REFERENCES users(id) ON DELETE CASCADE,
    connection_type TEXT DEFAULT 'mutual_feeling',
    connection_score INTEGER DEFAULT 0,
    memories_shared INTEGER DEFAULT 0,
    mutual_match_detected BOOLEAN DEFAULT FALSE,
    match_confidence NUMERIC(3,2) CHECK (match_confidence >= 0 AND match_confidence <= 1),
    first_interaction TIMESTAMPTZ,
    last_interaction TIMESTAMPTZ,
    engagement_metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_a, user_b)
);

-- ======================================
-- 7. FAMILY ACCESS - Emergency System
-- ======================================
CREATE TABLE family_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    family_member_id UUID REFERENCES users(id) ON DELETE CASCADE,
    access_level TEXT DEFAULT 'view' CHECK (access_level IN ('view', 'edit', 'full')),
    relationship TEXT NOT NULL,
    emergency_contact BOOLEAN DEFAULT FALSE,
    power_of_attorney BOOLEAN DEFAULT FALSE,
    digital_will_executor BOOLEAN DEFAULT FALSE,
    access_granted_date TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ,
    auto_notify_on_absence BOOLEAN DEFAULT TRUE,
    absence_threshold_days INTEGER DEFAULT 30
);

-- ======================================
-- 8. NOTIFICATIONS - Alert System
-- ======================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    channel TEXT DEFAULT 'app' CHECK (channel IN ('app', 'email', 'sms', 'telegram', 'whatsapp', 'voice')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed')),
    scheduled_for TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 9. VOICE AUTH - Biometric Security
-- ======================================
CREATE TABLE voice_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    voice_print BYTEA NOT NULL,
    sample_quality FLOAT CHECK (sample_quality >= 0 AND sample_quality <= 1),
    enrollment_date TIMESTAMPTZ DEFAULT NOW(),
    last_verified TIMESTAMPTZ,
    verification_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    device_info JSONB DEFAULT '{}'
);

-- ======================================
-- 10. CALL RECORDINGS - Voice History
-- ======================================
CREATE TABLE call_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    caller_id TEXT NOT NULL,
    recording_url TEXT,
    transcript TEXT,
    duration_seconds INTEGER,
    call_type TEXT DEFAULT 'inbound',
    platform TEXT DEFAULT 'twilio',
    sentiment_analysis JSONB DEFAULT '{}',
    key_topics TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 11. MESSAGE MONITORING - Track Communications
-- ======================================
CREATE TABLE message_monitoring (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    message_id TEXT,
    sender_id TEXT,
    content TEXT,
    message_type TEXT DEFAULT 'text',
    processed BOOLEAN DEFAULT FALSE,
    memory_created BOOLEAN DEFAULT FALSE,
    ai_response TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 12. USER ACTIVITY - Analytics
-- ======================================
CREATE TABLE user_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    platform TEXT DEFAULT 'app',
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 13. ACHIEVEMENTS - Gamification
-- ======================================
CREATE TABLE achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    achievement_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    points_earned INTEGER DEFAULT 0,
    badge_url TEXT,
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    progress JSONB DEFAULT '{}'
);

-- ======================================
-- 14. USER STREAKS - Engagement Tracking
-- ======================================
CREATE TABLE user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_activity_date DATE,
    streak_start_date DATE,
    total_active_days INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- INDEXES FOR PERFORMANCE
-- ======================================
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_timestamp ON memories(timestamp DESC);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX idx_memories_importance ON memories(importance_score DESC);

CREATE INDEX idx_contacts_user_id ON contact_profiles(user_id);
CREATE INDEX idx_contacts_relationship ON contact_profiles(relationship_type);
CREATE INDEX idx_contacts_last_interaction ON contact_profiles(last_interaction DESC);

CREATE INDEX idx_secrets_user_id ON secret_memories(user_id);
CREATE INDEX idx_secrets_level ON secret_memories(level);
CREATE INDEX idx_secrets_unlock_date ON secret_memories(unlock_date);

CREATE INDEX idx_commitments_user_id ON commitments(user_id);
CREATE INDEX idx_commitments_due_date ON commitments(due_date);
CREATE INDEX idx_commitments_completed ON commitments(completed);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_scheduled ON notifications(scheduled_for);

CREATE INDEX idx_activity_user_id ON user_activity(user_id);
CREATE INDEX idx_activity_created ON user_activity(created_at DESC);

-- ======================================
-- TRIGGER FUNCTIONS
-- ======================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ======================================
-- TRIGGERS
-- ======================================
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contact_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_streaks_updated_at BEFORE UPDATE ON user_streaks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ======================================
-- SUCCESS MESSAGE
-- ======================================
DO $$
BEGIN
    RAISE NOTICE '✅ Digital Immortality Platform database initialized successfully!';
    RAISE NOTICE '📊 Created 14 tables with indexes and triggers';
    RAISE NOTICE '🔐 Ready for production use';
END $$;