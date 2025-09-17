#!/usr/bin/env python3
"""
Database Migration Script for Digital Immortality Platform
Initializes database tables and performs migrations
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import DatabaseManager, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with all tables"""
    try:
        # Get database URL from environment or use default
        database_url = os.environ.get('DATABASE_URL')
        
        # Initialize database manager
        db_manager = DatabaseManager(database_url)
        
        logger.info("🔨 Creating database tables...")
        
        # Create all tables
        db_manager.create_tables()
        
        logger.info("✅ Database tables created successfully!")
        
        # Verify tables were created
        with db_manager.get_session() as session:
            # Get list of tables
            inspector = session.bind.dialect.get_inspector(session.bind)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'harvested_items',
                'detected_patterns',
                'behavioral_insights',
                'jobs',
                'audit_logs',
                'pattern_memories',
                'insight_patterns'
            ]
            
            for table in expected_tables:
                if table in tables:
                    logger.info(f"  ✓ Table '{table}' created")
                else:
                    logger.warning(f"  ✗ Table '{table}' not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False

def drop_all_tables():
    """Drop all tables (use with caution!)"""
    try:
        response = input("⚠️  WARNING: This will DELETE all data. Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Operation cancelled")
            return False
        
        database_url = os.environ.get('DATABASE_URL')
        db_manager = DatabaseManager(database_url)
        
        logger.info("🗑️  Dropping all tables...")
        db_manager.drop_tables()
        logger.info("✅ All tables dropped successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        return False

def verify_database():
    """Verify database connection and tables"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        db_manager = DatabaseManager(database_url)
        
        with db_manager.get_session() as session:
            # Test connection
            session.execute("SELECT 1")
            logger.info("✅ Database connection successful")
            
            # Get table list
            inspector = session.bind.dialect.get_inspector(session.bind)
            tables = inspector.get_table_names()
            
            if tables:
                logger.info(f"📊 Found {len(tables)} tables:")
                for table in tables:
                    logger.info(f"  - {table}")
            else:
                logger.warning("⚠️  No tables found in database")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Tool")
    parser.add_argument('command', choices=['init', 'drop', 'verify'],
                       help='Command to execute')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        success = init_database()
    elif args.command == 'drop':
        success = drop_all_tables()
    elif args.command == 'verify':
        success = verify_database()
    
    sys.exit(0 if success else 1)