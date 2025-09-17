#!/usr/bin/env python3
"""
Initialize gamification database tables
"""

import os
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from database_models import Base, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_gamification_database():
    """Initialize all gamification database tables"""
    try:
        # Get database URL from environment
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            logger.error("DATABASE_URL not set")
            return False
        
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Gamification tables created successfully")
        
        # Create default admin user if doesn't exist
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            admin_phone = os.getenv('ADMIN_PHONE', '+1234567890')
            admin = db.query(User).filter(User.id == admin_phone).first()
            
            if not admin:
                admin = User(
                    id=admin_phone,
                    display_name="System Admin",
                    is_premium=True,
                    is_beta_tester=True,
                    total_contact_slots=100,
                    level=99,
                    points=99999,
                    trust_score=1.0
                )
                db.add(admin)
                db.commit()
                logger.info(f"✅ Created admin user: {admin_phone}")
            else:
                logger.info(f"Admin user already exists: {admin_phone}")
                
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    if init_gamification_database():
        print("✅ Database initialization complete!")
    else:
        print("❌ Database initialization failed!")