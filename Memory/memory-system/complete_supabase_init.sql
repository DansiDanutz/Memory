-- DIGITAL IMMORTALITY PLATFORM - COMPLETE DATABASE SETUP
-- Supabase Project: gvuuauzsucvhghmpdpxf
-- Project URL: https://gvuuauzsucvhghmpdpxf.supabase.co
-- Run this entire script in Supabase SQL Editor

-- ======================================
-- EXTENSIONS & INITIAL SETUP
-- ======================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "vector";   -- For AI embeddings

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
    embedding vector(1536),  -- For AI semantic search
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
    discovery_context JSONB DEFAULT '{}',
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_a, user_b)
);

-- ======================================
-- 7. FAMILY ACCESS - Inheritance Control
-- ======================================
CREATE TABLE family_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    family_member_id UUID REFERENCES users(id),
    family_member_email TEXT,
    relationship TEXT NOT NULL,
    permissions TEXT[] DEFAULT ARRAY['read_only'],
    emergency_trigger_enabled BOOLEAN DEFAULT FALSE,
    inactivity_days INTEGER DEFAULT 30,
    trigger_conditions JSONB DEFAULT '{}',
    last_activity_check TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, family_member_id)
);

-- ======================================
-- 8. NOTIFICATIONS - Smart Alerts
-- ======================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    title TEXT,
    message TEXT NOT NULL,
    urgency TEXT DEFAULT 'normal' CHECK (urgency IN ('low', 'normal', 'high', 'critical')),
    delivered BOOLEAN DEFAULT FALSE,
    read BOOLEAN DEFAULT FALSE,
    scheduled_for TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    delivery_channel TEXT DEFAULT 'push',
    action_url TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 9. VOICE AUTHENTICATION
-- ======================================
CREATE TABLE voice_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    voice_print_data BYTEA NOT NULL,
    sample_count INTEGER DEFAULT 0,
    confidence_threshold FLOAT DEFAULT 0.85,
    last_verification TIMESTAMPTZ,
    verification_count INTEGER DEFAULT 0,
    failed_attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 10. CALL RECORDINGS - AI Phone Calls
-- ======================================
CREATE TABLE call_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE,
    caller_id TEXT,
    caller_name TEXT,
    recording_url TEXT,
    transcription TEXT,
    summary TEXT,
    key_points TEXT[],
    memory_id UUID REFERENCES memories(id),
    duration INTEGER,
    ai_handled BOOLEAN DEFAULT FALSE,
    sentiment_analysis JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 11. MESSAGE MONITORING
-- ======================================
CREATE TABLE message_monitoring (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    contact_id TEXT,
    platform TEXT DEFAULT 'whatsapp',
    message_count INTEGER DEFAULT 0,
    summary TEXT,
    key_facts TEXT[],
    topics TEXT[],
    sentiment_trend JSONB DEFAULT '{}',
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 12. USER ACTIVITY TRACKING
-- ======================================
CREATE TABLE user_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    activity_type TEXT NOT NULL,
    activity_data JSONB DEFAULT '{}',
    platform TEXT,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- 13. ACHIEVEMENTS & GAMIFICATION
-- ======================================
CREATE TABLE achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    achievement_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    points INTEGER DEFAULT 0,
    badge_url TEXT,
    unlocked BOOLEAN DEFAULT FALSE,
    unlocked_at TIMESTAMPTZ,
    progress INTEGER DEFAULT 0,
    target INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, achievement_type)
);

-- ======================================
-- 14. USER STREAKS
-- ======================================
CREATE TABLE user_streaks (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_activity_date DATE,
    total_active_days INTEGER DEFAULT 0,
    streak_freeze_available INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================================
-- INDEXES FOR PERFORMANCE
-- ======================================
-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_telegram ON users(telegram_user_id);
CREATE INDEX idx_users_whatsapp ON users(whatsapp_user_id);
CREATE INDEX idx_users_plan ON users(plan);

-- Memory indexes
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_timestamp ON memories(timestamp DESC);
CREATE INDEX idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX idx_memories_number ON memories(memory_number);
CREATE INDEX idx_memories_importance ON memories(importance_score DESC);

-- Full text search on memories
CREATE INDEX idx_memories_content_search ON memories USING GIN(to_tsvector('english', content));

-- Contact indexes
CREATE INDEX idx_contacts_user_id ON contact_profiles(user_id);
CREATE INDEX idx_contacts_phone ON contact_profiles(phone_number);
CREATE INDEX idx_contacts_trust ON contact_profiles(trust_level DESC);

-- Secret memory indexes
CREATE INDEX idx_secrets_user_id ON secret_memories(user_id);
CREATE INDEX idx_secrets_level ON secret_memories(level);
CREATE INDEX idx_secrets_unlock_date ON secret_memories(unlock_date);

-- Commitment indexes
CREATE INDEX idx_commitments_user_id ON commitments(user_id);
CREATE INDEX idx_commitments_due_date ON commitments(due_date);
CREATE INDEX idx_commitments_completed ON commitments(completed);
CREATE INDEX idx_commitments_priority ON commitments(priority);

-- Connection indexes
CREATE INDEX idx_connections_users ON mutual_connections(user_a, user_b);
CREATE INDEX idx_connections_score ON mutual_connections(connection_score DESC);
CREATE INDEX idx_connections_match ON mutual_connections(mutual_match_detected);

-- Family access indexes
CREATE INDEX idx_family_user_id ON family_access(user_id);
CREATE INDEX idx_family_member_id ON family_access(family_member_id);

-- Notification indexes
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_scheduled ON notifications(scheduled_for);
CREATE INDEX idx_notifications_delivered ON notifications(delivered);
CREATE INDEX idx_notifications_urgency ON notifications(urgency);

-- Activity indexes
CREATE INDEX idx_activity_user_id ON user_activity(user_id);
CREATE INDEX idx_activity_timestamp ON user_activity(timestamp DESC);
CREATE INDEX idx_activity_type ON user_activity(activity_type);

-- ======================================
-- ROW LEVEL SECURITY (RLS)
-- ======================================
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE secret_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE mutual_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_auth ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_recordings ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_monitoring ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_streaks ENABLE ROW LEVEL SECURITY;

-- ======================================
-- RLS POLICIES
-- ======================================
-- Users policies
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Service role full access" ON users
    FOR ALL USING (auth.role() = 'service_role');

-- Memories policies
CREATE POLICY "Users can manage own memories" ON memories
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Family can view shared memories" ON memories
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM family_access 
            WHERE family_member_id = auth.uid() 
            AND user_id = memories.user_id
            AND 'read' = ANY(permissions)
        )
    );

-- Contact profiles policies
CREATE POLICY "Users can manage own contacts" ON contact_profiles
    FOR ALL USING (auth.uid() = user_id);

-- Secret memories policies
CREATE POLICY "Users can manage own secrets" ON secret_memories
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Authorized contacts can view secrets" ON secret_memories
    FOR SELECT USING (
        auth.uid()::TEXT = ANY(authorized_contacts)
    );

-- Commitments policies
CREATE POLICY "Users can manage own commitments" ON commitments
    FOR ALL USING (auth.uid() = user_id);

-- Mutual connections policies
CREATE POLICY "Users can view their connections" ON mutual_connections
    FOR SELECT USING (auth.uid() = user_a OR auth.uid() = user_b);
CREATE POLICY "Users can create connections" ON mutual_connections
    FOR INSERT WITH CHECK (auth.uid() = user_a OR auth.uid() = user_b);

-- Family access policies
CREATE POLICY "Users can manage family access" ON family_access
    FOR ALL USING (auth.uid() = user_id OR auth.uid() = family_member_id);

-- Notifications policies
CREATE POLICY "Users can view own notifications" ON notifications
    FOR ALL USING (auth.uid() = user_id);

-- Voice auth policies
CREATE POLICY "Users can manage own voice auth" ON voice_auth
    FOR ALL USING (auth.uid() = user_id);

-- Call recordings policies
CREATE POLICY "Users can access own recordings" ON call_recordings
    FOR ALL USING (auth.uid() = user_id);

-- Message monitoring policies
CREATE POLICY "Users can view own monitoring" ON message_monitoring
    FOR ALL USING (auth.uid() = user_id);

-- Activity policies
CREATE POLICY "Users can view own activity" ON user_activity
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "System can log activity" ON user_activity
    FOR INSERT WITH CHECK (true);

-- Achievements policies
CREATE POLICY "Users can view own achievements" ON achievements
    FOR ALL USING (auth.uid() = user_id);

-- Streaks policies
CREATE POLICY "Users can view own streaks" ON user_streaks
    FOR ALL USING (auth.uid() = user_id);

-- ======================================
-- FUNCTIONS & TRIGGERS
-- ======================================
-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contact_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_connections_updated_at BEFORE UPDATE ON mutual_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_voice_auth_updated_at BEFORE UPDATE ON voice_auth
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_monitoring_updated_at BEFORE UPDATE ON message_monitoring
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_streaks_updated_at BEFORE UPDATE ON user_streaks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ======================================
-- MEMORY SEARCH FUNCTION
-- ======================================
CREATE OR REPLACE FUNCTION search_memories(
    p_user_id UUID,
    p_query TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    category TEXT,
    timestamp TIMESTAMPTZ,
    tags TEXT[],
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.content,
        m.category,
        m.timestamp,
        m.tags,
        ts_rank(to_tsvector('english', m.content), plainto_tsquery('english', p_query)) AS rank
    FROM memories m
    WHERE m.user_id = p_user_id
    AND to_tsvector('english', m.content) @@ plainto_tsquery('english', p_query)
    ORDER BY rank DESC, m.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ======================================
-- STREAK CALCULATION FUNCTION
-- ======================================
CREATE OR REPLACE FUNCTION update_user_streak(p_user_id UUID)
RETURNS VOID AS $$
DECLARE
    v_last_activity DATE;
    v_current_streak INTEGER;
    v_today DATE := CURRENT_DATE;
BEGIN
    SELECT last_activity_date, current_streak 
    INTO v_last_activity, v_current_streak
    FROM user_streaks 
    WHERE user_id = p_user_id;
    
    IF NOT FOUND THEN
        INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_activity_date, total_active_days)
        VALUES (p_user_id, 1, 1, v_today, 1);
    ELSIF v_last_activity = v_today THEN
        -- Already updated today
        RETURN;
    ELSIF v_last_activity = v_today - INTERVAL '1 day' THEN
        -- Continuing streak
        UPDATE user_streaks 
        SET current_streak = current_streak + 1,
            longest_streak = GREATEST(longest_streak, current_streak + 1),
            last_activity_date = v_today,
            total_active_days = total_active_days + 1
        WHERE user_id = p_user_id;
    ELSE
        -- Streak broken
        UPDATE user_streaks 
        SET current_streak = 1,
            last_activity_date = v_today,
            total_active_days = total_active_days + 1
        WHERE user_id = p_user_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ======================================
-- INITIAL DATA & VERIFICATION
-- ======================================
DO $$
BEGIN
    RAISE NOTICE '✅ Digital Immortality Database Created Successfully!';
    RAISE NOTICE '📊 Created 14 tables with full indexing and RLS policies';
    RAISE NOTICE '🔒 Row Level Security enabled on all tables';
    RAISE NOTICE '🚀 Database ready for production use';
    RAISE NOTICE '';
    RAISE NOTICE '📝 Next Steps:';
    RAISE NOTICE '1. Configure Supabase Auth users';
    RAISE NOTICE '2. Set up API endpoints';
    RAISE NOTICE '3. Configure webhooks';
    RAISE NOTICE '4. Test RLS policies';
END $$;