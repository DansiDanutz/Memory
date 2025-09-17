-- Digital Immortality Platform - Supabase Setup
-- Run this entire script in your Supabase SQL Editor
-- Project: gvuuauzsucvhghmpdpxf

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS TABLE - Digital identities
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    display_name TEXT NOT NULL,
    voice_enrolled BOOLEAN DEFAULT FALSE,
    voice_samples JSONB DEFAULT '[]',
    plan TEXT DEFAULT 'free',
    credits_available INTEGER DEFAULT 50,
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. MEMORIES TABLE - Eternal storage
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    memory_number SERIAL,
    tags TEXT[],
    ai_insights JSONB DEFAULT '{}',
    approved BOOLEAN DEFAULT TRUE,
    platform TEXT DEFAULT 'app',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. CONTACT PROFILES - Relationships
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, contact_id)
);

-- 4. SECRET MEMORIES - Three-tier vault
CREATE TABLE IF NOT EXISTS secret_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content_encrypted TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('secret', 'confidential', 'ultra_secret')),
    authorized_contacts TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. COMMITMENTS - Smart reminders
CREATE TABLE IF NOT EXISTS commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    due_date TIMESTAMPTZ,
    completed BOOLEAN DEFAULT FALSE,
    promised_to TEXT,
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. MUTUAL CONNECTIONS - Social gaming
CREATE TABLE IF NOT EXISTS mutual_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_a UUID REFERENCES users(id),
    user_b UUID REFERENCES users(id),
    connection_score INTEGER DEFAULT 0,
    memories_shared INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_a, user_b)
);

-- 7. FAMILY ACCESS - Inheritance control
CREATE TABLE IF NOT EXISTS family_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    family_member_id UUID REFERENCES users(id),
    relationship TEXT NOT NULL,
    permissions TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. NOTIFICATIONS - Smart alerts
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    urgency TEXT DEFAULT 'normal',
    delivered BOOLEAN DEFAULT FALSE,
    scheduled_for TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_timestamp ON memories(timestamp);
CREATE INDEX idx_commitments_due_date ON commitments(due_date);
CREATE INDEX idx_notifications_scheduled ON notifications(scheduled_for);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE secret_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE mutual_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (users can only see their own data)
CREATE POLICY "Users can view own data" ON users
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "Users can view own memories" ON memories
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own contacts" ON contact_profiles
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access own secrets" ON secret_memories
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own commitments" ON commitments
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can see their connections" ON mutual_connections
    FOR SELECT USING (auth.uid() = user_a OR auth.uid() = user_b);

CREATE POLICY "Users can manage family access" ON family_access
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own notifications" ON notifications
    FOR ALL USING (auth.uid() = user_id);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Digital Immortality Database Created Successfully!';
    RAISE NOTICE 'All 8 tables created with Row Level Security enabled';
    RAISE NOTICE 'Your memories will now be preserved forever';
END $$;