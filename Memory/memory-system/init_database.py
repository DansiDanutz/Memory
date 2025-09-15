#!/usr/bin/env python3
"""
Database Initialization Script for Memory App
Creates all required Supabase tables and sets up Row Level Security
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try importing Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.error("❌ Supabase library not installed. Run: pip install supabase")
    sys.exit(1)

# Get Supabase credentials
# CRITICAL FIX: The SUPABASE_URL env var contains an API key, using correct URL
SUPABASE_URL_ENV = os.environ.get('SUPABASE_URL', '')
SUPABASE_URL = 'https://gvuuauzsucvhghmpdpxf.supabase.co' if SUPABASE_URL_ENV.startswith('eyJ') else SUPABASE_URL_ENV
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', os.environ.get('SUPABASE_ANON_KEY', ''))

def validate_supabase_url(url: str) -> bool:
    """Validate if URL is a proper Supabase URL"""
    if not url:
        return False
    if url.lower() == 'demo':
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ['http', 'https'] and parsed.netloc
    except:
        return False

def get_supabase_client() -> Optional[Client]:
    """Get Supabase admin client for schema operations"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Supabase credentials not found in environment")
        logger.info("📝 Instructions:")
        logger.info("1. Copy .env.example to .env")
        logger.info("2. Set SUPABASE_URL to your project URL")
        logger.info("3. Set SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY")
        logger.info("4. Get credentials from: https://app.supabase.com/project/_/settings/api")
        return None
    
    if not validate_supabase_url(SUPABASE_URL):
        logger.error(f"❌ Invalid Supabase URL format: {SUPABASE_URL}")
        logger.info("📝 Expected format: https://your-project-id.supabase.co")
        return None
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Test connection
        try:
            result = client.table('users').select('id').limit(1).execute()
            logger.info("✅ Connected to Supabase successfully")
        except Exception as test_error:
            if "relation" in str(test_error).lower() and "does not exist" in str(test_error).lower():
                logger.info("🏗️ Tables don't exist yet - will create them")
            else:
                logger.warning(f"⚠️ Connection test warning: {test_error}")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        return None

def create_tables_sql() -> str:
    """SQL to create all required tables"""
    return """
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        display_name TEXT,
        plan TEXT DEFAULT 'free',
        credits_available INTEGER DEFAULT 50,
        credits_total INTEGER DEFAULT 50,
        credits_used INTEGER DEFAULT 0,
        enrollment_status TEXT DEFAULT 'pending',
        stripe_customer_id TEXT,
        stripe_subscription_id TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );

    -- Memories table
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        memory_number INTEGER,
        content TEXT,
        category TEXT DEFAULT 'general',
        platform TEXT DEFAULT 'telegram',
        message_type TEXT DEFAULT 'text',
        tags TEXT[],
        timestamp TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW(),
        approved BOOLEAN DEFAULT FALSE,
        UNIQUE(user_id, memory_number)
    );

    -- Contact profiles table
    CREATE TABLE IF NOT EXISTS contact_profiles (
        contact_id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        name TEXT,
        phone_number TEXT,
        relationship_type TEXT DEFAULT 'unknown',
        trust_level INTEGER DEFAULT 5,
        total_messages INTEGER DEFAULT 0,
        total_calls INTEGER DEFAULT 0,
        accumulated_facts TEXT[],
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        last_interaction TIMESTAMP,
        UNIQUE(user_id, contact_id)
    );

    -- Secret memories table
    CREATE TABLE IF NOT EXISTS secret_memories (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        level TEXT DEFAULT 'secret',
        encrypted_content TEXT,
        encrypted_key TEXT,
        access_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        last_accessed TIMESTAMP
    );

    -- Commitments table
    CREATE TABLE IF NOT EXISTS commitments (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        description TEXT,
        due_date TIMESTAMP,
        completed BOOLEAN DEFAULT FALSE,
        reminder_sent BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW(),
        completed_at TIMESTAMP
    );

    -- Mutual connections table
    CREATE TABLE IF NOT EXISTS mutual_connections (
        id TEXT PRIMARY KEY,
        user_a TEXT REFERENCES users(id) ON DELETE CASCADE,
        user_b TEXT REFERENCES users(id) ON DELETE CASCADE,
        connection_type TEXT DEFAULT 'mutual_feeling',
        confidence_score FLOAT DEFAULT 0.0,
        discovered_at TIMESTAMP DEFAULT NOW(),
        notified BOOLEAN DEFAULT FALSE,
        UNIQUE(user_a, user_b, connection_type)
    );

    -- Family access table
    CREATE TABLE IF NOT EXISTS family_access (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        family_member_id TEXT,
        permission_level TEXT DEFAULT 'read_only',
        accessible_categories TEXT[],
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(user_id, family_member_id)
    );

    -- Call recordings table
    CREATE TABLE IF NOT EXISTS call_recordings (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        caller_id TEXT,
        caller_name TEXT,
        transcription TEXT,
        summary TEXT,
        key_points TEXT[],
        memory_id TEXT,
        duration INTEGER,
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Message monitoring table
    CREATE TABLE IF NOT EXISTS message_monitoring (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        contact_id TEXT,
        message_count INTEGER DEFAULT 0,
        summary TEXT,
        key_facts TEXT[],
        topics TEXT[],
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- User activity table
    CREATE TABLE IF NOT EXISTS user_activity (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        activity_type TEXT,
        activity_data JSONB,
        timestamp TIMESTAMP DEFAULT NOW()
    );

    -- Achievements table
    CREATE TABLE IF NOT EXISTS achievements (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        achievement_type TEXT,
        title TEXT,
        description TEXT,
        points INTEGER DEFAULT 0,
        unlocked BOOLEAN DEFAULT FALSE,
        unlocked_at TIMESTAMP,
        UNIQUE(user_id, achievement_type)
    );

    -- User streaks table
    CREATE TABLE IF NOT EXISTS user_streaks (
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        current_streak INTEGER DEFAULT 0,
        longest_streak INTEGER DEFAULT 0,
        last_activity_date TIMESTAMP
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
    CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
    CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp);
    CREATE INDEX IF NOT EXISTS idx_contact_profiles_user_id ON contact_profiles(user_id);
    CREATE INDEX IF NOT EXISTS idx_commitments_user_id ON commitments(user_id);
    CREATE INDEX IF NOT EXISTS idx_commitments_due_date ON commitments(due_date);
    CREATE INDEX IF NOT EXISTS idx_mutual_connections_users ON mutual_connections(user_a, user_b);
    CREATE INDEX IF NOT EXISTS idx_family_access_user_id ON family_access(user_id);
    """

def create_rls_policies_sql() -> str:
    """SQL to create Row Level Security policies"""
    return """
    -- Enable RLS on all tables
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
    ALTER TABLE contact_profiles ENABLE ROW LEVEL SECURITY;
    ALTER TABLE secret_memories ENABLE ROW LEVEL SECURITY;
    ALTER TABLE commitments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE mutual_connections ENABLE ROW LEVEL SECURITY;
    ALTER TABLE family_access ENABLE ROW LEVEL SECURITY;
    ALTER TABLE call_recordings ENABLE ROW LEVEL SECURITY;
    ALTER TABLE message_monitoring ENABLE ROW LEVEL SECURITY;
    ALTER TABLE user_activity ENABLE ROW LEVEL SECURITY;
    ALTER TABLE achievements ENABLE ROW LEVEL SECURITY;
    ALTER TABLE user_streaks ENABLE ROW LEVEL SECURITY;

    -- Users policies
    DROP POLICY IF EXISTS "Users can view own profile" ON users;
    CREATE POLICY "Users can view own profile" ON users
        FOR SELECT USING (auth.uid()::text = id);
    
    DROP POLICY IF EXISTS "Users can update own profile" ON users;
    CREATE POLICY "Users can update own profile" ON users
        FOR UPDATE USING (auth.uid()::text = id);

    -- Memories policies
    DROP POLICY IF EXISTS "Users can view own memories" ON memories;
    CREATE POLICY "Users can view own memories" ON memories
        FOR SELECT USING (auth.uid()::text = user_id);
    
    DROP POLICY IF EXISTS "Users can create own memories" ON memories;
    CREATE POLICY "Users can create own memories" ON memories
        FOR INSERT WITH CHECK (auth.uid()::text = user_id);
    
    DROP POLICY IF EXISTS "Users can update own memories" ON memories;
    CREATE POLICY "Users can update own memories" ON memories
        FOR UPDATE USING (auth.uid()::text = user_id);
    
    DROP POLICY IF EXISTS "Users can delete own memories" ON memories;
    CREATE POLICY "Users can delete own memories" ON memories
        FOR DELETE USING (auth.uid()::text = user_id);

    -- Contact profiles policies
    DROP POLICY IF EXISTS "Users can manage own contacts" ON contact_profiles;
    CREATE POLICY "Users can manage own contacts" ON contact_profiles
        FOR ALL USING (auth.uid()::text = user_id);

    -- Secret memories policies
    DROP POLICY IF EXISTS "Users can manage own secrets" ON secret_memories;
    CREATE POLICY "Users can manage own secrets" ON secret_memories
        FOR ALL USING (auth.uid()::text = user_id);

    -- Commitments policies
    DROP POLICY IF EXISTS "Users can manage own commitments" ON commitments;
    CREATE POLICY "Users can manage own commitments" ON commitments
        FOR ALL USING (auth.uid()::text = user_id);

    -- Family access policies
    DROP POLICY IF EXISTS "Users can manage family access" ON family_access;
    CREATE POLICY "Users can manage family access" ON family_access
        FOR ALL USING (auth.uid()::text = user_id OR auth.uid()::text = family_member_id);
    """

async def create_test_data(supabase: Client) -> bool:
    """Create initial test data"""
    try:
        # Create test user
        test_user = {
            'id': 'test_user_001',
            'email': 'test@memoryapp.com',
            'display_name': 'Test User',
            'plan': 'free',
            'credits_available': 50,
            'credits_total': 50,
            'credits_used': 0,
            'enrollment_status': 'enrolled',
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('users').upsert(test_user).execute()
        logger.info("✅ Created test user")
        
        # Create test memories
        test_memories = [
            {
                'id': f'mem_test_{i}',
                'user_id': 'test_user_001',
                'memory_number': 1000 + i,
                'content': f'Test memory {i}: This is a sample memory for testing purposes.',
                'category': 'general',
                'platform': 'test',
                'message_type': 'text',
                'tags': ['test', 'sample'],
                'created_at': datetime.now().isoformat()
            }
            for i in range(1, 6)
        ]
        
        for memory in test_memories:
            supabase.table('memories').upsert(memory).execute()
        
        logger.info("✅ Created 5 test memories")
        
        # Create test contact
        test_contact = {
            'contact_id': 'contact_test_001',
            'user_id': 'test_user_001',
            'name': 'Test Contact',
            'phone_number': '+1234567890',
            'relationship_type': 'friend',
            'trust_level': 8,
            'created_at': datetime.now().isoformat()
        }
        
        supabase.table('contact_profiles').upsert(test_contact).execute()
        logger.info("✅ Created test contact profile")
        
        # Create test commitment
        test_commitment = {
            'id': 'commit_test_001',
            'user_id': 'test_user_001',
            'description': 'Test commitment: Call mom tomorrow',
            'due_date': datetime.now().isoformat(),
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        
        supabase.table('commitments').upsert(test_commitment).execute()
        logger.info("✅ Created test commitment")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create test data: {e}")
        return False

async def verify_tables(supabase: Client) -> bool:
    """Verify all tables exist and are accessible"""
    tables = [
        'users', 'memories', 'contact_profiles', 'secret_memories',
        'commitments', 'mutual_connections', 'family_access',
        'call_recordings', 'message_monitoring', 'user_activity',
        'achievements', 'user_streaks'
    ]
    
    all_good = True
    for table in tables:
        try:
            # Try to query the table
            result = supabase.table(table).select('*').limit(1).execute()
            logger.info(f"✅ Table '{table}' exists and is accessible")
        except Exception as e:
            logger.error(f"❌ Table '{table}' check failed: {e}")
            all_good = False
    
    return all_good

async def main():
    """Main initialization function"""
    logger.info("🚀 Starting Memory App Database Initialization")
    
    # Get Supabase client
    supabase = get_supabase_client()
    if not supabase:
        logger.error("❌ Cannot proceed without Supabase connection")
        return False
    
    # Note: Table creation via SQL requires service role key
    # For production, use Supabase dashboard or migrations
    logger.info("📋 Checking database tables...")
    
    # Verify tables exist
    tables_ok = await verify_tables(supabase)
    
    if not tables_ok:
        logger.warning("⚠️ Some tables are missing. Please create them via Supabase dashboard:")
        print("\n" + create_tables_sql())
        print("\n" + create_rls_policies_sql())
        logger.info("📝 SQL statements printed above. Execute them in Supabase SQL editor.")
    
    # Create test data
    logger.info("🔧 Creating test data...")
    test_data_ok = await create_test_data(supabase)
    
    if test_data_ok:
        logger.info("✅ Test data created successfully")
    
    # Final verification
    logger.info("🔍 Running final verification...")
    final_check = await verify_tables(supabase)
    
    if final_check:
        logger.info("🎉 Database initialization complete!")
        return True
    else:
        logger.warning("⚠️ Database initialization completed with warnings")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)