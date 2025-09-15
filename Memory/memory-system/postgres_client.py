#!/usr/bin/env python3
"""
PostgreSQL Client for Memory App
Handles all database operations with PostgreSQL backend
Replaces Supabase functionality with PostgreSQL
"""

import os
import json
import asyncio
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List, Any
import logging
from datetime import datetime
from urllib.parse import urlparse
import uuid

logger = logging.getLogger(__name__)

# Get database connection from environment
DATABASE_URL = os.environ.get('DATABASE_URL', '')
PGHOST = os.environ.get('PGHOST', 'localhost')
PGUSER = os.environ.get('PGUSER', 'postgres')
PGPASSWORD = os.environ.get('PGPASSWORD', '')
PGDATABASE = os.environ.get('PGDATABASE', 'memory_app')
PGPORT = os.environ.get('PGPORT', '5432')

# Check database mode
DATABASE_MODE = os.environ.get('DATABASE_MODE', 'postgresql')
DEMO_MODE = DATABASE_MODE == 'demo' or not DATABASE_URL

# Demo storage for fallback
demo_storage: Dict[str, List[Dict]] = {
    'memories': [],
    'users': [],
    'contact_profiles': [],
    'secret_memories': [],
    'commitments': [],
    'mutual_connections': [],
    'family_access': []
}

class PostgreSQLClient:
    """PostgreSQL database client for Memory App"""
    
    def __init__(self):
        self.conn = None
        self.pool = None
        self.connected = False
        
    def connect(self):
        """Establish connection to PostgreSQL database"""
        if DEMO_MODE:
            logger.info("🎮 Running in DEMO MODE - Using local storage")
            return True
            
        try:
            # Use DATABASE_URL if available, otherwise build from components
            if DATABASE_URL:
                self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            else:
                self.conn = psycopg2.connect(
                    host=PGHOST,
                    user=PGUSER,
                    password=PGPASSWORD,
                    database=PGDATABASE,
                    port=PGPORT,
                    cursor_factory=RealDictCursor
                )
            self.conn.autocommit = True
            self.connected = True
            logger.info("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            logger.info("🔄 Falling back to DEMO MODE")
            return False
    
    def get_cursor(self):
        """Get database cursor"""
        if not self.connected:
            self.connect()
        if self.conn:
            return self.conn.cursor()
        return None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.connected = False

# Global client instance
pg_client = PostgreSQLClient()

# Initialize connection
if not DEMO_MODE:
    pg_client.connect()

# Database operations
async def store_memory(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Store memory in PostgreSQL database or demo storage"""
    
    # Ensure ID is set
    if 'id' not in memory_data:
        memory_data['id'] = str(uuid.uuid4())
    
    # Convert datetime objects to ISO strings
    if 'timestamp' in memory_data and isinstance(memory_data['timestamp'], datetime):
        memory_data['timestamp'] = memory_data['timestamp'].isoformat()
    
    if 'created_at' in memory_data and isinstance(memory_data['created_at'], datetime):
        memory_data['created_at'] = memory_data['created_at'].isoformat()
    
    if DEMO_MODE:
        # Demo mode: Store in local dictionary
        demo_storage['memories'].append(memory_data)
        logger.info(f"📝 [DEMO] Memory stored locally: {memory_data.get('id', 'unknown')}")
        return {'success': True, 'data': [memory_data]}
    
    cursor = pg_client.get_cursor()
    if not cursor:
        return {'success': False, 'error': 'Database not connected'}
    
    try:
        # Convert lists and dicts to JSON for PostgreSQL
        tags = json.dumps(memory_data.get('tags', [])) if memory_data.get('tags') else '[]'
        ai_insights = json.dumps(memory_data.get('ai_insights', {})) if memory_data.get('ai_insights') else '{}'
        media_urls = memory_data.get('media_urls', [])
        if media_urls:
            media_urls = '{' + ','.join(media_urls) + '}'
        else:
            media_urls = None
        
        location = json.dumps(memory_data.get('location', {})) if memory_data.get('location') else None
        
        query = """
            INSERT INTO memories (
                id, user_id, content, category, subcategory,
                tags, ai_insights, platform, message_type,
                media_urls, location, emotional_tone, importance_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s
            ) RETURNING *
        """
        
        cursor.execute(query, (
            memory_data['id'],
            memory_data.get('user_id'),
            memory_data.get('content', ''),
            memory_data.get('category', 'general'),
            memory_data.get('subcategory'),
            tags,
            ai_insights,
            memory_data.get('platform', 'app'),
            memory_data.get('message_type', 'text'),
            media_urls,
            location,
            memory_data.get('emotional_tone'),
            memory_data.get('importance_score', 0.5)
        ))
        
        result = cursor.fetchone()
        logger.info(f"✅ Memory stored successfully: {memory_data.get('id', 'unknown')}")
        return {'success': True, 'data': [dict(result)] if result else []}
        
    except Exception as e:
        logger.error(f"❌ Failed to store memory: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        cursor.close()

async def get_user_memories(user_id: str, limit: int = 100, category: Optional[str] = None, offset: int = 0) -> List[Dict[str, Any]]:
    """Get memories for a user with optional category filter"""
    
    if DEMO_MODE:
        # Demo mode: Filter from local storage
        memories = [m for m in demo_storage['memories'] if m.get('user_id') == user_id]
        
        if category:
            memories = [m for m in memories if m.get('category') == category]
        
        # Sort by timestamp (newest first)
        memories.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        memories = memories[offset:offset+limit]
        
        logger.info(f"📚 [DEMO] Retrieved {len(memories)} memories for user {user_id}")
        return memories
    
    cursor = pg_client.get_cursor()
    if not cursor:
        return []
    
    try:
        if category:
            query = """
                SELECT * FROM memories 
                WHERE user_id = %s AND category = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (user_id, category, limit, offset))
        else:
            query = """
                SELECT * FROM memories 
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (user_id, limit, offset))
        
        results = cursor.fetchall()
        memories = [dict(row) for row in results]
        
        logger.info(f"📚 Retrieved {len(memories)} memories for user {user_id}")
        return memories
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve memories: {e}")
        return []
    finally:
        cursor.close()

async def update_memory(memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing memory"""
    
    if DEMO_MODE:
        # Demo mode: Update in local storage
        for memory in demo_storage['memories']:
            if memory.get('id') == memory_id:
                memory.update(updates)
                logger.info(f"📝 [DEMO] Memory updated: {memory_id}")
                return {'success': True, 'data': [memory]}
        return {'success': False, 'error': 'Memory not found'}
    
    cursor = pg_client.get_cursor()
    if not cursor:
        return {'success': False, 'error': 'Database not connected'}
    
    try:
        # Build dynamic update query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key not in ['id', 'created_at']:  # Don't update these fields
                if key in ['tags', 'ai_insights', 'location']:
                    set_clauses.append(f"{key} = %s::jsonb")
                    params.append(json.dumps(value) if value else '{}')
                elif key == 'media_urls':
                    set_clauses.append(f"{key} = %s")
                    params.append('{' + ','.join(value) + '}' if value else None)
                else:
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
        
        if not set_clauses:
            return {'success': False, 'error': 'No valid updates provided'}
        
        params.append(memory_id)
        query = f"""
            UPDATE memories 
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        if result:
            logger.info(f"✅ Memory updated: {memory_id}")
            return {'success': True, 'data': [dict(result)]}
        else:
            return {'success': False, 'error': 'Memory not found'}
            
    except Exception as e:
        logger.error(f"❌ Failed to update memory: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        cursor.close()

async def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Delete a memory"""
    
    if DEMO_MODE:
        # Demo mode: Remove from local storage
        initial_count = len(demo_storage['memories'])
        demo_storage['memories'] = [m for m in demo_storage['memories'] if m.get('id') != memory_id]
        
        if len(demo_storage['memories']) < initial_count:
            logger.info(f"🗑️ [DEMO] Memory deleted: {memory_id}")
            return {'success': True}
        return {'success': False, 'error': 'Memory not found'}
    
    cursor = pg_client.get_cursor()
    if not cursor:
        return {'success': False, 'error': 'Database not connected'}
    
    try:
        query = "DELETE FROM memories WHERE id = %s RETURNING id"
        cursor.execute(query, (memory_id,))
        result = cursor.fetchone()
        
        if result:
            logger.info(f"🗑️ Memory deleted: {memory_id}")
            return {'success': True}
        else:
            return {'success': False, 'error': 'Memory not found'}
            
    except Exception as e:
        logger.error(f"❌ Failed to delete memory: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        cursor.close()

async def create_or_update_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a user"""
    
    if 'id' not in user_data:
        user_data['id'] = str(uuid.uuid4())
    
    if DEMO_MODE:
        # Demo mode: Store/update in local storage
        existing_user = None
        for i, user in enumerate(demo_storage['users']):
            if user.get('id') == user_data['id'] or user.get('email') == user_data.get('email'):
                existing_user = i
                break
        
        if existing_user is not None:
            demo_storage['users'][existing_user].update(user_data)
            logger.info(f"👤 [DEMO] User updated: {user_data['id']}")
        else:
            demo_storage['users'].append(user_data)
            logger.info(f"👤 [DEMO] User created: {user_data['id']}")
        
        return {'success': True, 'user': user_data}
    
    cursor = pg_client.get_cursor()
    if not cursor:
        return {'success': False, 'error': 'Database not connected'}
    
    try:
        # Convert JSON fields
        avatar_config = json.dumps(user_data.get('avatar_config', {}))
        emergency_contacts = json.dumps(user_data.get('emergency_contacts', []))
        voice_samples = json.dumps(user_data.get('voice_samples', []))
        
        query = """
            INSERT INTO users (
                id, email, phone_number, display_name, plan,
                credits_available, credits_total, credits_used,
                telegram_user_id, whatsapp_user_id, enrollment_status,
                avatar_config, emergency_contacts, voice_samples
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb
            )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                phone_number = EXCLUDED.phone_number,
                display_name = EXCLUDED.display_name,
                plan = EXCLUDED.plan,
                credits_available = EXCLUDED.credits_available,
                updated_at = NOW()
            RETURNING *
        """
        
        cursor.execute(query, (
            user_data['id'],
            user_data.get('email'),
            user_data.get('phone_number'),
            user_data.get('display_name', 'User'),
            user_data.get('plan', 'free'),
            user_data.get('credits_available', 50),
            user_data.get('credits_total', 50),
            user_data.get('credits_used', 0),
            user_data.get('telegram_user_id'),
            user_data.get('whatsapp_user_id'),
            user_data.get('enrollment_status', 'pending'),
            avatar_config,
            emergency_contacts,
            voice_samples
        ))
        
        result = cursor.fetchone()
        logger.info(f"✅ User created/updated: {user_data['id']}")
        return {'success': True, 'user': dict(result) if result else user_data}
        
    except Exception as e:
        logger.error(f"❌ Failed to create/update user: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        cursor.close()

async def get_user(user_id: str = None, email: str = None, phone: str = None) -> Optional[Dict[str, Any]]:
    """Get user by ID, email, or phone"""
    
    if DEMO_MODE:
        # Demo mode: Search in local storage
        for user in demo_storage['users']:
            if (user_id and user.get('id') == user_id) or \
               (email and user.get('email') == email) or \
               (phone and user.get('phone_number') == phone):
                logger.info(f"👤 [DEMO] User found: {user.get('id')}")
                return user
        return None
    
    cursor = pg_client.get_cursor()
    if not cursor:
        return None
    
    try:
        if user_id:
            query = "SELECT * FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
        elif email:
            query = "SELECT * FROM users WHERE email = %s"
            cursor.execute(query, (email,))
        elif phone:
            query = "SELECT * FROM users WHERE phone_number = %s"
            cursor.execute(query, (phone,))
        else:
            return None
        
        result = cursor.fetchone()
        if result:
            logger.info(f"👤 User found: {result.get('id')}")
            return dict(result)
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to get user: {e}")
        return None
    finally:
        cursor.close()

# Export all functions for compatibility
__all__ = [
    'pg_client',
    'store_memory',
    'get_user_memories',
    'update_memory',
    'delete_memory',
    'create_or_update_user',
    'get_user',
    'DEMO_MODE'
]