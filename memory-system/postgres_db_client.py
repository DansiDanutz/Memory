#!/usr/bin/env python3
"""
PostgreSQL Database Client for Memory App
Direct PostgreSQL implementation to replace Supabase client
"""

import os
import json
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List, Any, Tuple
import logging
from datetime import datetime
import uuid
import hashlib

logger = logging.getLogger(__name__)

# Get database connection from environment
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment variables")
    raise ValueError("DATABASE_URL is required")

# Connection pool
connection_pool = None

def get_connection():
    """Get a database connection from the pool"""
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def init_connection():
    """Initialize the database connection"""
    try:
        conn = get_connection()
        conn.close()
        logger.info("✅ PostgreSQL database connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize database connection: {e}")
        return False

# Initialize connection on module load
init_connection()

# UUID Normalization Functions
def normalize_user_id(platform: str, external_id: str) -> str:
    """Normalize user IDs from different platforms to valid UUIDs
    
    Args:
        platform: The platform (e.g., 'telegram', 'whatsapp', 'web')
        external_id: The platform-specific ID (numeric for Telegram, phone for WhatsApp)
    
    Returns:
        A deterministic UUID v5 based on platform and external_id
    """
    # Create a namespace UUID for our application
    NAMESPACE_MEMORY = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    
    # Normalize the platform name
    platform = platform.lower().strip()
    
    # For numeric IDs (like Telegram), ensure they're strings
    external_id = str(external_id).strip()
    
    # Create a deterministic UUID v5 from platform + external_id
    combined = f"{platform}:{external_id}"
    user_uuid = uuid.uuid5(NAMESPACE_MEMORY, combined)
    
    logger.debug(f"Normalized {platform}:{external_id} to UUID: {user_uuid}")
    return str(user_uuid)

def parse_user_id(user_id: str) -> Tuple[bool, str]:
    """Parse and validate a user ID
    
    Args:
        user_id: The user ID to parse (can be UUID or platform-specific)
    
    Returns:
        Tuple of (is_valid_uuid, normalized_id)
    """
    try:
        # Try to parse as UUID first
        uuid.UUID(user_id)
        return (True, user_id)
    except ValueError:
        # Not a valid UUID, try to detect platform and normalize
        # Check if it's a phone number (WhatsApp)
        if user_id.startswith('+') or (user_id.isdigit() and len(user_id) >= 10):
            # Likely a WhatsApp phone number
            return (False, normalize_user_id('whatsapp', user_id))
        elif user_id.isdigit():
            # Likely a Telegram ID
            return (False, normalize_user_id('telegram', user_id))
        else:
            # Unknown format, generate a generic UUID
            return (False, normalize_user_id('unknown', user_id))

def ensure_valid_uuid(value: str) -> str:
    """Ensure a value is a valid UUID string
    
    Args:
        value: The value to check/convert
    
    Returns:
        A valid UUID string
    """
    if not value:
        return str(uuid.uuid4())
    
    try:
        # Try to parse as UUID
        uuid.UUID(value)
        return value
    except ValueError:
        # Generate a deterministic UUID from the value
        NAMESPACE_MEMORY = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        return str(uuid.uuid5(NAMESPACE_MEMORY, str(value)))

# Database operations
async def store_memory(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store memory in PostgreSQL database"""
    conn = None
    cursor = None
    try:
        # Ensure required fields with UUID normalization
        if 'id' not in memory_data:
            memory_data['id'] = str(uuid.uuid4())
        else:
            # Ensure the ID is a valid UUID
            memory_data['id'] = ensure_valid_uuid(memory_data['id'])
        
        # Normalize user_id if present
        if 'user_id' in memory_data:
            is_valid, normalized_id = parse_user_id(memory_data['user_id'])
            memory_data['user_id'] = normalized_id
            
            # Store original ID for reference if needed
            if not is_valid and 'original_user_id' not in memory_data:
                memory_data['original_user_id'] = memory_data.get('user_id')
        
        # Convert datetime objects to strings
        if 'timestamp' in memory_data and isinstance(memory_data['timestamp'], datetime):
            memory_data['timestamp'] = memory_data['timestamp'].isoformat()
        if 'created_at' in memory_data and isinstance(memory_data['created_at'], datetime):
            memory_data['created_at'] = memory_data['created_at'].isoformat()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build INSERT query
        columns = list(memory_data.keys())
        values = [memory_data[col] for col in columns]
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        query = f"""
            INSERT INTO memories ({column_names})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET
            {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'id'])}
            RETURNING *
        """
        
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        
        logger.info(f"✅ Memory stored successfully: {memory_data.get('id')}")
        return {'success': True, 'data': [dict(result)]}
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to store memory: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def get_user_memories(user_id: str, limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get memories for a user with optional category filter"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if category:
            query = """
                SELECT * FROM memories 
                WHERE user_id = %s AND category = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
            """
            cursor.execute(query, (user_id, category, limit))
        else:
            query = """
                SELECT * FROM memories 
                WHERE user_id = %s 
                ORDER BY timestamp DESC 
                LIMIT %s
            """
            cursor.execute(query, (user_id, limit))
        
        results = cursor.fetchall()
        memories = [dict(row) for row in results]
        
        logger.info(f"📚 Retrieved {len(memories)} memories for user {user_id}")
        return memories
        
    except Exception as e:
        logger.error(f"❌ Failed to get memories: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def update_memory(memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing memory"""
    conn = None
    cursor = None
    try:
        # Convert datetime objects to strings
        if 'timestamp' in updates and isinstance(updates['timestamp'], datetime):
            updates['timestamp'] = updates['timestamp'].isoformat()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build UPDATE query
        set_clause = ', '.join([f"{col} = %s" for col in updates.keys()])
        values = list(updates.values()) + [memory_id]
        
        query = f"""
            UPDATE memories 
            SET {set_clause}, updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """
        
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        
        logger.info(f"✅ Memory updated: {memory_id}")
        return {'success': True, 'data': [dict(result)] if result else []}
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to update memory: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Delete a memory from the database"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
        conn.commit()
        
        logger.info(f"🗑️ Memory deleted: {memory_id}")
        return {'success': True}
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to delete memory: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def create_or_update_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a user"""
    conn = None
    try:
        if 'id' not in user_data:
            user_data['id'] = str(uuid.uuid4())
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build UPSERT query
        columns = list(user_data.keys())
        values = [user_data[col] for col in columns]
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        query = f"""
            INSERT INTO users ({column_names})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET
            {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'id'])}
            RETURNING *
        """
        
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        
        logger.info(f"✅ User created/updated: {user_data.get('id')}")
        return {'success': True, 'data': dict(result)}
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to create/update user: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get a user by ID"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"❌ Failed to get user: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def store_contact_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store or update contact profile"""
    conn = None
    try:
        if 'id' not in profile_data:
            profile_data['id'] = str(uuid.uuid4())
        
        conn = get_connection()
        cursor = conn.cursor()
        
        columns = list(profile_data.keys())
        values = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in profile_data.values()]
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        query = f"""
            INSERT INTO contact_profiles ({column_names})
            VALUES ({placeholders})
            ON CONFLICT (user_id, contact_id) DO UPDATE SET
            {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col not in ['user_id', 'contact_id']])}
            RETURNING *
        """
        
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        
        logger.info(f"✅ Contact profile stored: {profile_data.get('contact_id')}")
        return {'success': True, 'data': [dict(result)]}
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to store contact profile: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def get_contact_profile(user_id: str, contact_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific contact profile"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM contact_profiles WHERE user_id = %s AND contact_id = %s",
            (user_id, contact_id)
        )
        result = cursor.fetchone()
        
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"❌ Failed to get contact profile: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def search_memories(user_id: str, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search memories using full-text search"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM memories 
            WHERE user_id = %s 
            AND (content ILIKE %s OR category ILIKE %s OR subcategory ILIKE %s)
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (user_id, search_pattern, search_pattern, search_pattern, limit))
        
        results = cursor.fetchall()
        memories = [dict(row) for row in results]
        
        logger.info(f"🔍 Found {len(memories)} memories matching '{search_term}'")
        return memories
        
    except Exception as e:
        logger.error(f"❌ Failed to search memories: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Additional helper functions for compatibility
async def store_secret_memory(secret_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store a secret memory"""
    conn = None
    try:
        if 'id' not in secret_data:
            secret_data['id'] = str(uuid.uuid4())
        
        conn = get_connection()
        cursor = conn.cursor()
        
        columns = list(secret_data.keys())
        values = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in secret_data.values()]
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        query = f"""
            INSERT INTO secret_memories ({column_names})
            VALUES ({placeholders})
            RETURNING *
        """
        
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        
        return {'success': True, 'data': dict(result)}
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Failed to store secret memory: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def get_secret_memories(user_id: str, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get secret memories for a user"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if level:
            query = "SELECT * FROM secret_memories WHERE user_id = %s AND level = %s ORDER BY created_at DESC"
            cursor.execute(query, (user_id, level))
        else:
            query = "SELECT * FROM secret_memories WHERE user_id = %s ORDER BY created_at DESC"
            cursor.execute(query, (user_id,))
        
        results = cursor.fetchall()
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"❌ Failed to get secret memories: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Export all functions for compatibility
async def get_all_contact_profiles(user_id: str) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contact_profiles WHERE user_id = %s", (user_id,))
        results = cursor.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get contact profiles: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def get_mutual_connections(user_id: str) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM mutual_connections WHERE user_a = %s OR user_b = %s",
            (user_id, user_id)
        )
        results = cursor.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get mutual connections: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def store_mutual_connection(connection_data: Dict[str, Any]) -> Dict[str, Any]:
    return await store_generic_record('mutual_connections', connection_data)

async def store_commitment(commitment_data: Dict[str, Any]) -> Dict[str, Any]:
    return await store_generic_record('commitments', commitment_data)

async def get_commitments(user_id: str, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if completed is not None:
            cursor.execute(
                "SELECT * FROM commitments WHERE user_id = %s AND completed = %s",
                (user_id, completed)
            )
        else:
            cursor.execute("SELECT * FROM commitments WHERE user_id = %s", (user_id,))
        results = cursor.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get commitments: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def get_family_access(user_id: str) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM family_access WHERE user_id = %s", (user_id,))
        results = cursor.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get family access: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def store_family_access(access_data: Dict[str, Any]) -> Dict[str, Any]:
    return await store_generic_record('family_access', access_data)

async def store_generic_record(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Generic function to store records in any table"""
    conn = None
    try:
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        conn = get_connection()
        cursor = conn.cursor()
        
        columns = list(data.keys())
        values = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in data.values()]
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders}) RETURNING *"
        
        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()
        
        return {'success': True, 'data': dict(result)}
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to store record in {table}: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def get_memory_stats(user_id: str) -> Dict[str, Any]:
    """Get memory statistics for a user"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_memories,
                COUNT(DISTINCT category) as categories_used,
                MIN(timestamp) as first_memory,
                MAX(timestamp) as last_memory
            FROM memories 
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        return dict(result) if result else {}
        
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        return {}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def check_connection() -> bool:
    """Check if database connection is working"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return True
    except:
        return False

async def initialize_schema() -> bool:
    """Placeholder for schema initialization - already done via SQL"""
    return True

# Aliases for compatibility
supabase_store_memory = store_memory
supabase_get_memories = get_user_memories
supabase_update_memory = update_memory
supabase_delete_memory = delete_memory
supabase_store_contact = store_contact_profile
supabase_get_contact = get_contact_profile
supabase_get_all_contacts = get_all_contact_profiles
supabase_store_secret = store_secret_memory
supabase_get_secrets = get_secret_memories
supabase_get_connections = get_mutual_connections
supabase_store_connection = store_mutual_connection
supabase_store_commitment = store_commitment
supabase_get_commitments = get_commitments
supabase_get_family = get_family_access
supabase_store_family = store_family_access
supabase_upsert_user = create_or_update_user
supabase_get_user = get_user
supabase_search_memories = search_memories
supabase_get_stats = get_memory_stats
supabase_check_connection = check_connection
supabase_init_schema = initialize_schema