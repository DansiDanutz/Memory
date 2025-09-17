-- Memory App Database Schema for Supabase
-- Complete schema for all memory system features

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    display_name TEXT NOT NULL,
    voice_enrolled BOOLEAN DEFAULT FALSE,
    plan TEXT DEFAULT 'free',
    credits_available INTEGER DEFAULT 0,
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memories table
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    memory_number INTEGER,
    tags TEXT[],
    approved BOOLEAN DEFAULT FALSE,
    platform TEXT DEFAULT 'telegram',
    message_type TEXT DEFAULT 'text',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contact profiles table
CREATE TABLE IF NOT EXISTS contact_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    contact_id TEXT NOT NULL,
    name TEXT NOT NULL,
    phone_number TEXT,
    relationship_type TEXT,
    avatar_enabled BOOLEAN DEFAULT FALSE,
    trust_level TEXT DEFAULT 'general',
    accumulated_facts JSONB DEFAULT '[]',
    last_interaction TIMESTAMPTZ,
    interaction_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, contact_id)
);

-- Secret memories table
CREATE TABLE IF NOT EXISTS secret_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content_encrypted TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('secret', 'confidential', 'ultra_secret')),
    authorized_contacts TEXT[],
    unlock_condition TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Commitments table
CREATE TABLE IF NOT EXISTS commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    due_date TIMESTAMPTZ,
    completed BOOLEAN DEFAULT FALSE,
    promised_to TEXT,
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Mutual connections table
CREATE TABLE IF NOT EXISTS mutual_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_a UUID REFERENCES users(id),
    user_b UUID REFERENCES users(id),
    connection_score INTEGER DEFAULT 0,
    memories_shared INTEGER DEFAULT 0,
    mutual_match_detected BOOLEAN DEFAULT FALSE,
    match_confidence NUMERIC(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_a, user_b)
);

-- Family access table
CREATE TABLE IF NOT EXISTS family_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    family_member_id UUID REFERENCES users(id),
    relationship TEXT NOT NULL,
    permissions TEXT[],
    emergency_trigger_enabled BOOLEAN DEFAULT FALSE,
    inactivity_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Voice authentication table
CREATE TABLE IF NOT EXISTS voice_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    voice_embedding_encrypted TEXT,
    enrollment_samples INTEGER DEFAULT 0,
    last_authenticated TIMESTAMPTZ,
    failed_attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Call recordings table
CREATE TABLE IF NOT EXISTS call_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    caller_id TEXT NOT NULL,
    call_start TIMESTAMPTZ NOT NULL,
    call_end TIMESTAMPTZ,
    duration_seconds INTEGER,
    transcript TEXT,
    summary TEXT,
    ai_handled BOOLEAN DEFAULT FALSE,
    platform TEXT DEFAULT 'twilio',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily reviews table
CREATE TABLE IF NOT EXISTS daily_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    review_date DATE NOT NULL,
    memories_reviewed INTEGER DEFAULT 0,
    memories_kept INTEGER DEFAULT 0,
    memories_deleted INTEGER DEFAULT 0,
    summary TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, review_date)
);

-- Achievements table
CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    achievement_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    points INTEGER DEFAULT 0,
    unlocked BOOLEAN DEFAULT FALSE,
    unlocked_at TIMESTAMPTZ,
    progress INTEGER DEFAULT 0,
    target INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User streaks table
CREATE TABLE IF NOT EXISTS user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_activity_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    delivered BOOLEAN DEFAULT FALSE,
    read BOOLEAN DEFAULT FALSE,
    urgent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ
);

-- Subscription history table
CREATE TABLE IF NOT EXISTS subscription_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    tier TEXT NOT NULL,
    stripe_subscription_id TEXT,
    stripe_payment_intent_id TEXT,
    amount DECIMAL(10,2),
    currency TEXT DEFAULT 'USD',
    status TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_data JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    session_id TEXT,
    platform TEXT
);

-- Create indexes for performance
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_timestamp ON memories(timestamp);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_memory_number ON memories(memory_number);

CREATE INDEX idx_contact_profiles_user_id ON contact_profiles(user_id);
CREATE INDEX idx_contact_profiles_contact_id ON contact_profiles(contact_id);

CREATE INDEX idx_commitments_user_id ON commitments(user_id);
CREATE INDEX idx_commitments_due_date ON commitments(due_date);
CREATE INDEX idx_commitments_completed ON commitments(completed);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_delivered ON notifications(delivered);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

CREATE INDEX idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX idx_analytics_events_timestamp ON analytics_events(timestamp);
CREATE INDEX idx_analytics_events_event_type ON analytics_events(event_type);

-- Create views for common queries
CREATE OR REPLACE VIEW user_memory_stats AS
SELECT 
    u.id as user_id,
    u.display_name,
    COUNT(m.id) as total_memories,
    COUNT(CASE WHEN m.approved = true THEN 1 END) as approved_memories,
    COUNT(DISTINCT m.category) as categories_used,
    MAX(m.timestamp) as last_memory_date
FROM users u
LEFT JOIN memories m ON u.id = m.user_id
GROUP BY u.id, u.display_name;

CREATE OR REPLACE VIEW active_subscriptions AS
SELECT 
    u.id as user_id,
    u.display_name,
    u.plan,
    sh.tier as subscription_tier,
    sh.started_at,
    sh.amount,
    sh.status
FROM users u
JOIN subscription_history sh ON u.id = sh.user_id
WHERE sh.ended_at IS NULL OR sh.ended_at > NOW();

-- Row-level security policies (if needed for Supabase)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE secret_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_access ENABLE ROW LEVEL SECURITY;

-- Create policies for user access (adjust based on your auth setup)
CREATE POLICY "Users can view own memories" ON memories
    FOR SELECT USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can insert own memories" ON memories
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

CREATE POLICY "Users can update own memories" ON memories
    FOR UPDATE USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can delete own memories" ON memories
    FOR DELETE USING (auth.uid()::uuid = user_id);

-- Similar policies for other tables
CREATE POLICY "Users can manage own contacts" ON contact_profiles
    FOR ALL USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can manage own secrets" ON secret_memories
    FOR ALL USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can manage own commitments" ON commitments
    FOR ALL USING (auth.uid()::uuid = user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to auto-update updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contact_profiles_updated_at BEFORE UPDATE ON contact_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_voice_auth_updated_at BEFORE UPDATE ON voice_auth
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_streaks_updated_at BEFORE UPDATE ON user_streaks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mutual_connections_updated_at BEFORE UPDATE ON mutual_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();