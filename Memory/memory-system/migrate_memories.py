#!/usr/bin/env python3
"""
Migration script to move file-based memories to PostgreSQL database
"""

import os
import sys
import json
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the database client
from postgres_db_client import (
    store_memory,
    create_or_update_user,
    get_user,
    init_connection
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_memories():
    """Migrate all file-based memories to the database"""
    
    # Check database connection
    if not init_connection():
        logger.error("Failed to connect to database")
        return False
    
    logger.info("✅ Database connection successful")
    
    # Find all memory files
    memory_dir = Path("memory-system/memories")
    if not memory_dir.exists():
        logger.warning("No memories directory found")
        return False
    
    memory_files = list(memory_dir.glob("*.json"))
    logger.info(f"Found {len(memory_files)} memory files to migrate")
    
    # Track unique users
    users = {}
    memories_migrated = 0
    errors = 0
    
    for memory_file in memory_files:
        try:
            # Read memory file
            with open(memory_file, 'r') as f:
                memory_data = json.load(f)
            
            logger.info(f"Processing memory: {memory_file.name}")
            
            # Extract user info
            user_id = memory_data.get('user_id', 'unknown_user')
            
            # Create user if not exists
            if user_id not in users:
                # Check if user exists
                existing_user = await get_user(user_id)
                if not existing_user:
                    # Create new user
                    user_data = {
                        'id': user_id,
                        'display_name': user_id.replace('_', ' ').title(),
                        'email': f"{user_id}@example.com",
                        'plan': 'free',
                        'credits_available': 50,
                        'credits_total': 50,
                        'created_at': datetime.now().isoformat()
                    }
                    result = await create_or_update_user(user_data)
                    if result.get('success'):
                        logger.info(f"✅ Created user: {user_id}")
                        users[user_id] = result['data']
                    else:
                        logger.error(f"Failed to create user {user_id}: {result.get('error')}")
                        continue
                else:
                    users[user_id] = existing_user
            
            # Prepare memory data for database
            db_memory = {
                'id': memory_data.get('id', str(uuid.uuid4())),
                'user_id': user_id,
                'content': memory_data.get('content', ''),
                'category': memory_data.get('category', 'general'),
                'subcategory': memory_data.get('subcategory'),
                'timestamp': memory_data.get('timestamp', datetime.now().isoformat()),
                'tags': memory_data.get('tags', []),
                'platform': memory_data.get('platform', 'file'),
                'message_type': memory_data.get('message_type', 'text'),
                'emotional_tone': memory_data.get('emotional_tone'),
                'importance_score': memory_data.get('importance_score', 0.5),
                'created_at': memory_data.get('created_at', datetime.now().isoformat())
            }
            
            # Remove None values
            db_memory = {k: v for k, v in db_memory.items() if v is not None}
            
            # Store memory in database
            result = await store_memory(db_memory)
            if result.get('success'):
                memories_migrated += 1
                logger.info(f"✅ Migrated memory: {memory_data.get('id', 'unknown')}")
            else:
                errors += 1
                logger.error(f"Failed to migrate memory: {result.get('error')}")
                
        except Exception as e:
            errors += 1
            logger.error(f"Error processing {memory_file}: {e}")
    
    # Summary
    logger.info("=" * 50)
    logger.info("MIGRATION COMPLETE")
    logger.info(f"Total files processed: {len(memory_files)}")
    logger.info(f"Memories migrated: {memories_migrated}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Users created/found: {len(users)}")
    logger.info("=" * 50)
    
    return memories_migrated > 0

async def test_database():
    """Test database operations after migration"""
    logger.info("\n" + "=" * 50)
    logger.info("TESTING DATABASE OPERATIONS")
    logger.info("=" * 50)
    
    # Test creating a new memory
    test_user_id = "test_user_" + str(uuid.uuid4())[:8]
    
    # Create test user
    user_data = {
        'id': test_user_id,
        'display_name': 'Test User',
        'email': f'{test_user_id}@test.com',
        'plan': 'free'
    }
    
    user_result = await create_or_update_user(user_data)
    if user_result.get('success'):
        logger.info(f"✅ Test user created: {test_user_id}")
    else:
        logger.error(f"Failed to create test user: {user_result.get('error')}")
        return False
    
    # Create test memory
    test_memory = {
        'id': str(uuid.uuid4()),
        'user_id': test_user_id,
        'content': 'This is a test memory created to verify database connectivity',
        'category': 'test',
        'timestamp': datetime.now().isoformat(),
        'platform': 'migration_test'
    }
    
    memory_result = await store_memory(test_memory)
    if memory_result.get('success'):
        logger.info(f"✅ Test memory stored successfully")
        logger.info(f"   Memory ID: {test_memory['id']}")
    else:
        logger.error(f"Failed to store test memory: {memory_result.get('error')}")
        return False
    
    logger.info("\n✅ DATABASE IS WORKING CORRECTLY!")
    return True

async def main():
    """Main migration function"""
    logger.info("STARTING MEMORY MIGRATION TO POSTGRESQL DATABASE")
    logger.info("=" * 50)
    
    # Run migration
    success = await migrate_memories()
    
    if success:
        # Test database operations
        await test_database()
    else:
        logger.error("Migration failed or no memories to migrate")

if __name__ == "__main__":
    asyncio.run(main())