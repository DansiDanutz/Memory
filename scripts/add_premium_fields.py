#!/usr/bin/env python3
"""
Database migration script to add premium gating fields
Run this to update the voice_avatars table with premium fields
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

def add_premium_fields():
    """Add premium gating fields to voice_avatars table"""
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return False
    
    engine = create_engine(DATABASE_URL)
    
    migrations = [
        # Add is_locked field
        """
        ALTER TABLE voice_avatars 
        ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT TRUE NOT NULL
        """,
        
        # Add preview_generated field
        """
        ALTER TABLE voice_avatars 
        ADD COLUMN IF NOT EXISTS preview_generated BOOLEAN DEFAULT FALSE NOT NULL
        """,
        
        # Add preview_text field
        """
        ALTER TABLE voice_avatars 
        ADD COLUMN IF NOT EXISTS preview_text TEXT
        """,
        
        # Add unlock_date field
        """
        ALTER TABLE voice_avatars 
        ADD COLUMN IF NOT EXISTS unlock_date TIMESTAMP WITHOUT TIME ZONE
        """,
        
        # Update existing avatars for premium users
        """
        UPDATE voice_avatars 
        SET is_locked = FALSE 
        WHERE owner_id IN (
            SELECT id FROM gamification_users WHERE is_premium = TRUE
        )
        """,
    ]
    
    with engine.connect() as conn:
        for i, migration_sql in enumerate(migrations, 1):
            try:
                conn.execute(text(migration_sql))
                conn.commit()
                logger.info(f"✅ Migration {i} applied successfully")
            except (OperationalError, ProgrammingError) as e:
                if "already exists" in str(e).lower():
                    logger.info(f"ℹ️ Migration {i} skipped - field already exists")
                else:
                    logger.error(f"❌ Migration {i} failed: {e}")
                    conn.rollback()
    
    logger.info("✅ Premium gating fields migration completed")
    return True

if __name__ == "__main__":
    success = add_premium_fields()
    sys.exit(0 if success else 1)