#!/usr/bin/env python3
"""
Session Management Module - Manages verification sessions with TTL
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    """Manages verification sessions with automatic expiry"""
    
    def __init__(self, ttl_minutes: int = 10):
        """
        Initialize session manager
        
        Args:
            ttl_minutes: Time-to-live for sessions in minutes (default: 10)
        """
        self.ttl_minutes = ttl_minutes
        self.sessions: Dict[str, Dict] = {}
        logger.info(f"📝 Session Manager initialized with {ttl_minutes} minute TTL")
    
    def create_session(self, phone_number: str) -> Dict:
        """
        Create or update a verification session
        
        Args:
            phone_number: Contact's phone number
            
        Returns:
            Session details
        """
        now = datetime.now()
        expiry = now + timedelta(minutes=self.ttl_minutes)
        
        session = {
            'phone_number': phone_number,
            'verified_at': now.isoformat(),
            'expires_at': expiry.isoformat(),
            'is_active': True,
            'allowed_categories': [
                'general', 
                'chronological', 
                'confidential',
                'secret',  # Unlocked after verification
                'ultra_secret'  # Unlocked after verification
            ]
        }
        
        self.sessions[phone_number] = session
        logger.info(f"🔓 Session created for {phone_number}, expires at {expiry.strftime('%H:%M:%S')}")
        
        return session
    
    def is_verified(self, phone_number: str) -> bool:
        """
        Check if a phone number has an active verification session
        
        Args:
            phone_number: Contact's phone number
            
        Returns:
            True if session is active and not expired
        """
        if phone_number not in self.sessions:
            return False
        
        session = self.sessions[phone_number]
        
        # Check if session has expired
        expires_at = datetime.fromisoformat(session['expires_at'])
        if datetime.now() > expires_at:
            # Session expired, remove it
            self.revoke_session(phone_number)
            return False
        
        return session.get('is_active', False)
    
    def get_allowed_categories(self, phone_number: str) -> List[str]:
        """
        Get allowed security categories for a phone number
        
        Args:
            phone_number: Contact's phone number
            
        Returns:
            List of allowed category names
        """
        # Default categories (no verification needed)
        default_categories = ['general', 'chronological', 'confidential']
        
        # Check if verified
        if self.is_verified(phone_number):
            session = self.sessions.get(phone_number, {})
            return session.get('allowed_categories', default_categories)
        
        return default_categories
    
    def get_session(self, phone_number: str) -> Optional[Dict]:
        """
        Get session details if active
        
        Args:
            phone_number: Contact's phone number
            
        Returns:
            Session details or None if not active
        """
        if self.is_verified(phone_number):
            return self.sessions.get(phone_number)
        return None
    
    def revoke_session(self, phone_number: str) -> bool:
        """
        Revoke a verification session
        
        Args:
            phone_number: Contact's phone number
            
        Returns:
            True if session was revoked
        """
        if phone_number in self.sessions:
            del self.sessions[phone_number]
            logger.info(f"🔒 Session revoked for {phone_number}")
            return True
        return False
    
    def get_time_remaining(self, phone_number: str) -> Optional[int]:
        """
        Get minutes remaining in session
        
        Args:
            phone_number: Contact's phone number
            
        Returns:
            Minutes remaining or None if no active session
        """
        if not self.is_verified(phone_number):
            return None
        
        session = self.sessions.get(phone_number)
        if not session:
            return None
        
        expires_at = datetime.fromisoformat(session['expires_at'])
        remaining = expires_at - datetime.now()
        
        # Return minutes (rounded up)
        minutes = int(remaining.total_seconds() / 60) + 1
        return max(0, minutes)
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up all expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        expired = []
        now = datetime.now()
        
        for phone_number, session in self.sessions.items():
            expires_at = datetime.fromisoformat(session['expires_at'])
            if now > expires_at:
                expired.append(phone_number)
        
        for phone_number in expired:
            self.revoke_session(phone_number)
        
        if expired:
            logger.info(f"🧹 Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def get_all_active_sessions(self) -> Dict[str, Dict]:
        """Get all active sessions (for debugging/monitoring)"""
        self.cleanup_expired_sessions()
        return self.sessions.copy()

# Create global instance with 10-minute TTL
session_manager = SessionManager(ttl_minutes=10)