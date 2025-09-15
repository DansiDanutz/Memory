#!/usr/bin/env python3
"""
Supabase Client for Memory App
Handles all database operations with Supabase backend
Supports demo mode for local development without Supabase
"""

import os
import json
import asyncio
from typing import Optional, Dict, List, Any
import logging
from datetime import datetime
from urllib.parse import urlparse

# Try importing Supabase, but allow fallback if not available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    # Define placeholder types for when Supabase is not available
    Client = None  # type: ignore
    create_client = None  # type: ignore
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Supabase library not installed. Running in demo mode.")

logger = logging.getLogger(__name__)

# Get Supabase credentials from environment variables
# CRITICAL FIX: The SUPABASE_URL env var contains an API key, using correct URL
SUPABASE_URL_ENV = os.environ.get('SUPABASE_URL', '')
SUPABASE_URL = 'https://gvuuauzsucvhghmpdpxf.supabase.co' if SUPABASE_URL_ENV.startswith('eyJ') else SUPABASE_URL_ENV
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', '')

# Check if running in demo mode
DEMO_MODE = SUPABASE_URL.lower() == 'demo' or not SUPABASE_URL or not SUPABASE_KEY

# Initialize Supabase client or demo storage
supabase: Optional[Client] = None
demo_storage: Dict[str, List[Dict]] = {
    'memories': [],
    'users': [],
    'contact_profiles': [],
    'secret_memories': [],
    'commitments': [],
    'mutual_connections': [],
    'family_access': []
}

def validate_supabase_url(url: str) -> bool:
    """Validate if URL is a proper Supabase URL"""
    if not url:
        return False
    # Check if someone accidentally put API key as URL
    if url.startswith('eyJ'):
        logger.warning("⚠️ API key detected in SUPABASE_URL field")
        return False
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)
    except:
        return False

if DEMO_MODE:
    logger.info("🎮 Running in DEMO MODE - Using local storage")
    logger.info("📝 To use Supabase, set SUPABASE_URL and SUPABASE_ANON_KEY in .env")
    logger.info("📚 Instructions: https://app.supabase.com/project/_/settings/api")
elif not SUPABASE_AVAILABLE:
    logger.warning("⚠️ Supabase library not installed. Install with: pip install supabase")
    DEMO_MODE = True
elif not validate_supabase_url(SUPABASE_URL):
    if SUPABASE_URL.startswith('eyJ'):
        logger.error("❌ API key is in SUPABASE_URL field. This should be the project URL.")
        logger.info("📝 SUPABASE_URL should be: https://your-project-id.supabase.co")
        logger.info("📝 SUPABASE_ANON_KEY should be: eyJ... (the long key)")
    else:
        logger.error(f"❌ Invalid Supabase URL format")
        logger.info("📝 Expected format: https://your-project-id.supabase.co")
    DEMO_MODE = True
else:
    try:
        if create_client is not None:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Test connection
            test_result = supabase.table('users').select('id').limit(1).execute()
            logger.info("✅ Supabase client initialized and connected successfully")
        else:
            logger.error("❌ Supabase library not available for import")
            DEMO_MODE = True
            supabase = None
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        logger.info("🔄 Falling back to DEMO MODE")
        DEMO_MODE = True
        supabase = None

# Database operations
async def store_memory(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store memory in Supabase database or demo storage"""
    # Convert datetime objects to ISO strings for JSON serialization
    if 'timestamp' in memory_data and isinstance(memory_data['timestamp'], datetime):
        memory_data['timestamp'] = memory_data['timestamp'].isoformat()
    
    # Convert created_at if present
    if 'created_at' in memory_data and isinstance(memory_data['created_at'], datetime):
        memory_data['created_at'] = memory_data['created_at'].isoformat()
    
    if DEMO_MODE:
        # Demo mode: Store in local dictionary
        demo_storage['memories'].append(memory_data)
        logger.info(f"📝 [DEMO] Memory stored locally: {memory_data.get('id', 'unknown')}")
        return {'success': True, 'data': [memory_data]}
    
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured and not in demo mode'}
    
    try:
        result = supabase.table('memories').insert(memory_data).execute()
        logger.info(f"✅ Memory stored successfully: {memory_data.get('id', 'unknown')}")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to store memory: {e}")
        return {'success': False, 'error': str(e)}

async def get_user_memories(user_id: str, limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get memories for a user with optional category filter"""
    if DEMO_MODE:
        # Demo mode: Filter from local storage
        memories = [m for m in demo_storage['memories'] if m.get('user_id') == user_id]
        
        if category:
            memories = [m for m in memories if m.get('category') == category]
        
        # Sort by timestamp (newest first)
        memories.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        memories = memories[:limit]
        
        logger.info(f"📚 [DEMO] Retrieved {len(memories)} memories for user {user_id}")
        return memories
    
    if not supabase:
        return []
    
    try:
        query = supabase.table('memories').select('*').eq('user_id', user_id)
        
        if category:
            query = query.eq('category', category)
            
        query = query.order('timestamp', desc=True).limit(limit)
        result = query.execute()
        
        logger.info(f"📚 Retrieved {len(result.data)} memories for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get memories: {e}")
        return []

async def update_memory(memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing memory"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        # Convert datetime objects to ISO strings
        if 'timestamp' in updates and isinstance(updates['timestamp'], datetime):
            updates['timestamp'] = updates['timestamp'].isoformat()
            
        result = supabase.table('memories').update(updates).eq('id', memory_id).execute()
        logger.info(f"✅ Memory updated: {memory_id}")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to update memory: {e}")
        return {'success': False, 'error': str(e)}

async def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Delete a memory from the database"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        result = supabase.table('memories').delete().eq('id', memory_id).execute()
        logger.info(f"🗑️ Memory deleted: {memory_id}")
        return {'success': True}
    except Exception as e:
        logger.error(f"❌ Failed to delete memory: {e}")
        return {'success': False, 'error': str(e)}

async def store_contact_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store or update contact profile"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        # Convert datetime objects to ISO strings
        if 'created_at' in profile_data and isinstance(profile_data['created_at'], datetime):
            profile_data['created_at'] = profile_data['created_at'].isoformat()
        if 'updated_at' in profile_data and isinstance(profile_data['updated_at'], datetime):
            profile_data['updated_at'] = profile_data['updated_at'].isoformat()
            
        result = supabase.table('contact_profiles').upsert(profile_data).execute()
        logger.info(f"✅ Contact profile stored: {profile_data.get('contact_id', 'unknown')}")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to store contact profile: {e}")
        return {'success': False, 'error': str(e)}

async def get_contact_profile(user_id: str, contact_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific contact profile"""
    if not supabase:
        return None
    
    try:
        result = supabase.table('contact_profiles').select('*').eq('user_id', user_id).eq('contact_id', contact_id).execute()
        
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"❌ Failed to get contact profile: {e}")
        return None

async def get_all_contact_profiles(user_id: str) -> List[Dict[str, Any]]:
    """Get all contact profiles for a user"""
    if not supabase:
        return []
    
    try:
        result = supabase.table('contact_profiles').select('*').eq('user_id', user_id).execute()
        logger.info(f"📱 Retrieved {len(result.data)} contact profiles for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get contact profiles: {e}")
        return []

async def store_secret_memory(secret_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store encrypted secret memory"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        # Convert datetime objects to ISO strings
        if 'created_at' in secret_data and isinstance(secret_data['created_at'], datetime):
            secret_data['created_at'] = secret_data['created_at'].isoformat()
            
        result = supabase.table('secret_memories').insert(secret_data).execute()
        logger.info(f"🔐 Secret memory stored: {secret_data.get('id', 'unknown')}")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to store secret: {e}")
        return {'success': False, 'error': str(e)}

async def get_secret_memories(user_id: str, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get secret memories for a user with optional level filter"""
    if not supabase:
        return []
    
    try:
        query = supabase.table('secret_memories').select('*').eq('user_id', user_id)
        
        if level:
            query = query.eq('level', level)
            
        result = query.execute()
        logger.info(f"🔐 Retrieved {len(result.data)} secret memories for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get secret memories: {e}")
        return []

async def get_mutual_connections(user_id: str) -> List[Dict[str, Any]]:
    """Get mutual memory connections for a user"""
    if not supabase:
        return []
    
    try:
        # Get connections where user is either user_a or user_b
        result = supabase.table('mutual_connections').select('*').or_(f'user_a.eq.{user_id},user_b.eq.{user_id}').execute()
        logger.info(f"💕 Retrieved {len(result.data)} mutual connections for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get connections: {e}")
        return []

async def store_mutual_connection(connection_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store or update a mutual connection"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        # Convert datetime objects to ISO strings
        if 'created_at' in connection_data and isinstance(connection_data['created_at'], datetime):
            connection_data['created_at'] = connection_data['created_at'].isoformat()
            
        result = supabase.table('mutual_connections').upsert(connection_data).execute()
        logger.info(f"💕 Mutual connection stored")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to store mutual connection: {e}")
        return {'success': False, 'error': str(e)}

async def store_commitment(commitment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store a commitment/promise"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        # Convert datetime objects to ISO strings
        if 'due_date' in commitment_data and isinstance(commitment_data['due_date'], datetime):
            commitment_data['due_date'] = commitment_data['due_date'].isoformat()
        if 'created_at' in commitment_data and isinstance(commitment_data['created_at'], datetime):
            commitment_data['created_at'] = commitment_data['created_at'].isoformat()
            
        result = supabase.table('commitments').insert(commitment_data).execute()
        logger.info(f"📋 Commitment stored: {commitment_data.get('id', 'unknown')}")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to store commitment: {e}")
        return {'success': False, 'error': str(e)}

async def get_commitments(user_id: str, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Get commitments for a user with optional completion filter"""
    if not supabase:
        return []
    
    try:
        query = supabase.table('commitments').select('*').eq('user_id', user_id)
        
        if completed is not None:
            query = query.eq('completed', completed)
            
        query = query.order('due_date', desc=False)
        result = query.execute()
        
        logger.info(f"📋 Retrieved {len(result.data)} commitments for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get commitments: {e}")
        return []

async def get_family_access(user_id: str) -> List[Dict[str, Any]]:
    """Get family access permissions for a user"""
    if not supabase:
        return []
    
    try:
        result = supabase.table('family_access').select('*').eq('user_id', user_id).execute()
        logger.info(f"👨‍👩‍👧‍👦 Retrieved {len(result.data)} family access records for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get family access: {e}")
        return []

async def store_family_access(access_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store family access permissions"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        # Convert datetime objects to ISO strings
        if 'created_at' in access_data and isinstance(access_data['created_at'], datetime):
            access_data['created_at'] = access_data['created_at'].isoformat()
            
        result = supabase.table('family_access').insert(access_data).execute()
        logger.info(f"👨‍👩‍👧‍👦 Family access stored")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to store family access: {e}")
        return {'success': False, 'error': str(e)}

async def create_or_update_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update user account"""
    if not supabase:
        return {'success': False, 'error': 'Supabase not configured'}
    
    try:
        # Convert datetime objects to ISO strings
        if 'created_at' in user_data and isinstance(user_data['created_at'], datetime):
            user_data['created_at'] = user_data['created_at'].isoformat()
        if 'updated_at' in user_data and isinstance(user_data['updated_at'], datetime):
            user_data['updated_at'] = user_data['updated_at'].isoformat()
            
        # Use email as unique identifier for upsert
        result = supabase.table('users').upsert(user_data).execute()
        logger.info(f"👤 User account created/updated: {user_data.get('email', user_data.get('id', 'unknown'))}")
        return {'success': True, 'data': result.data}
    except Exception as e:
        logger.error(f"❌ Failed to create/update user: {e}")
        return {'success': False, 'error': str(e)}

async def get_user(user_id: Optional[str] = None, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get user by ID or email"""
    if not supabase:
        return None
    
    try:
        query = supabase.table('users').select('*')
        
        if user_id:
            query = query.eq('id', user_id)
        elif email:
            query = query.eq('email', email)
        else:
            return None
            
        result = query.execute()
        
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"❌ Failed to get user: {e}")
        return None

async def search_memories(user_id: str, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search memories by content"""
    if not supabase:
        return []
    
    try:
        # Use ilike for case-insensitive search
        result = supabase.table('memories').select('*').eq('user_id', user_id).ilike('content', f'%{search_term}%').limit(limit).execute()
        logger.info(f"🔍 Found {len(result.data)} memories matching '{search_term}' for user {user_id}")
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to search memories: {e}")
        return []

async def get_memory_stats(user_id: str) -> Dict[str, Any]:
    """Get memory statistics for a user"""
    if not supabase:
        return {'total_memories': 0, 'categories': {}}
    
    try:
        # Get all memories for the user
        result = supabase.table('memories').select('category').eq('user_id', user_id).execute()
        
        total = len(result.data)
        categories = {}
        
        for memory in result.data:
            cat = memory.get('category', 'general')
            categories[cat] = categories.get(cat, 0) + 1
            
        stats = {
            'total_memories': total,
            'categories': categories,
            'last_updated': datetime.now().isoformat()
        }
        
        logger.info(f"📊 Memory stats for user {user_id}: {total} total memories")
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get memory stats: {e}")
        return {'total_memories': 0, 'categories': {}}

# Health check function
async def check_connection() -> bool:
    """Check if Supabase connection is working"""
    if not supabase:
        return False
    
    try:
        # Try a simple query to test the connection
        result = supabase.table('users').select('id').limit(1).execute()
        logger.info("✅ Supabase connection is healthy")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase connection check failed: {e}")
        return False

# Initialize database schema (if needed)
async def initialize_schema() -> bool:
    """Initialize database schema if tables don't exist"""
    if not supabase:
        logger.warning("⚠️ Cannot initialize schema - Supabase not configured")
        return False
    
    # Note: Schema creation should typically be done through Supabase dashboard or migrations
    # This is just for checking if tables exist
    try:
        # Test if tables exist by querying them
        tables_to_check = ['users', 'memories', 'contact_profiles', 'secret_memories', 
                          'commitments', 'mutual_connections', 'family_access']
        
        for table in tables_to_check:
            try:
                supabase.table(table).select('id').limit(1).execute()
                logger.info(f"✅ Table '{table}' exists")
            except Exception as e:
                logger.error(f"❌ Table '{table}' may not exist: {e}")
                return False
                
        logger.info("✅ All database tables are available")
        return True
    except Exception as e:
        logger.error(f"❌ Schema initialization check failed: {e}")
        return False