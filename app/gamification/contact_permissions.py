"""
Contact Permissions Management System
Handles contact slot allocation and permission scoring
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .database_models import (
    ContactSlot, User, AccessLevel,
    SessionLocal
)

logger = logging.getLogger(__name__)

class ContactPermissionManager:
    """
    Manages contact permissions and slot allocation
    """
    
    # Permission scoring weights
    PERMISSION_WEIGHTS = {
        AccessLevel.BASIC: 1.0,
        AccessLevel.ENHANCED: 2.5,
        AccessLevel.PREMIUM: 5.0,
        AccessLevel.VIP: 10.0
    }
    
    # Trust level thresholds
    TRUST_THRESHOLDS = {
        AccessLevel.BASIC: 0.0,
        AccessLevel.ENHANCED: 0.3,
        AccessLevel.PREMIUM: 0.6,
        AccessLevel.VIP: 0.85
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize permission manager"""
        self.db = db_session or SessionLocal()
        logger.info("✅ Contact Permission Manager initialized")
    
    def calculate_permission_score(
        self,
        user_trust_score: float,
        contact_interactions: int,
        relationship_duration_days: int
    ) -> float:
        """
        Calculate permission score based on various factors
        
        Args:
            user_trust_score: User's overall trust score (0-1)
            contact_interactions: Number of interactions with contact
            relationship_duration_days: Days since first interaction
            
        Returns:
            Permission score (0-1)
        """
        # Base score from trust
        base_score = user_trust_score * 0.5
        
        # Interaction score (logarithmic)
        interaction_score = min(1.0, contact_interactions / 100) * 0.3
        
        # Duration score (logarithmic)
        duration_score = min(1.0, relationship_duration_days / 365) * 0.2
        
        # Calculate final score
        permission_score = base_score + interaction_score + duration_score
        
        return min(1.0, permission_score)
    
    def determine_access_level(
        self,
        permission_score: float,
        is_premium_user: bool = False
    ) -> AccessLevel:
        """
        Determine access level based on permission score
        """
        # Premium users get one level boost
        if is_premium_user:
            permission_score = min(1.0, permission_score + 0.15)
        
        # Determine level based on thresholds
        if permission_score >= self.TRUST_THRESHOLDS[AccessLevel.VIP]:
            return AccessLevel.VIP
        elif permission_score >= self.TRUST_THRESHOLDS[AccessLevel.PREMIUM]:
            return AccessLevel.PREMIUM
        elif permission_score >= self.TRUST_THRESHOLDS[AccessLevel.ENHANCED]:
            return AccessLevel.ENHANCED
        else:
            return AccessLevel.BASIC
    
    async def add_contact(
        self,
        user_id: str,
        contact_id: str,
        initial_access_level: AccessLevel = AccessLevel.BASIC
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Add a contact to user's contact list
        """
        try:
            # Get user
            user = self.db.query(User).filter_by(id=user_id).first()
            if not user:
                return False, {"error": "User not found"}
            
            # Check available slots
            available_slots = user.total_contact_slots - user.used_contact_slots
            if available_slots <= 0:
                return False, {
                    "error": "No available contact slots",
                    "total_slots": user.total_contact_slots,
                    "used_slots": user.used_contact_slots
                }
            
            # Check if contact already exists
            existing = self.db.query(ContactSlot).filter(
                and_(
                    ContactSlot.owner_id == user_id,
                    ContactSlot.contact_id == contact_id
                )
            ).first()
            
            if existing:
                return False, {"error": "Contact already exists"}
            
            # Find next available slot number
            next_slot = user.used_contact_slots + 1
            
            # Calculate initial permission score
            permission_score = self.calculate_permission_score(
                user.trust_score,
                0,  # New contact, no interactions yet
                0   # New contact, no history
            )
            
            # Create contact slot
            contact_slot = ContactSlot(
                owner_id=user_id,
                slot_number=next_slot,
                is_used=True,
                contact_id=contact_id,
                access_level=initial_access_level,
                permission_score=permission_score,
                trust_level=user.trust_score,
                created_at=datetime.utcnow()
            )
            
            self.db.add(contact_slot)
            
            # Update user stats
            user.used_contact_slots += 1
            
            self.db.commit()
            
            logger.info(f"Added contact {contact_id} for user {user_id} in slot {next_slot}")
            
            return True, {
                "slot_id": contact_slot.id,
                "slot_number": contact_slot.slot_number,
                "contact_id": contact_id,
                "access_level": contact_slot.access_level.value,
                "permission_score": contact_slot.permission_score,
                "remaining_slots": available_slots - 1
            }
            
        except Exception as e:
            logger.error(f"Failed to add contact: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    async def remove_contact(
        self,
        user_id: str,
        contact_id: str
    ) -> Tuple[bool, str]:
        """Remove a contact from user's list"""
        try:
            contact_slot = self.db.query(ContactSlot).filter(
                and_(
                    ContactSlot.owner_id == user_id,
                    ContactSlot.contact_id == contact_id
                )
            ).first()
            
            if not contact_slot:
                return False, "Contact not found"
            
            # Free the slot
            contact_slot.is_used = False
            contact_slot.contact_id = None
            contact_slot.updated_at = datetime.utcnow()
            
            # Update user stats
            user = self.db.query(User).filter_by(id=user_id).first()
            if user:
                user.used_contact_slots = max(0, user.used_contact_slots - 1)
            
            self.db.commit()
            
            return True, "Contact removed successfully"
            
        except Exception as e:
            logger.error(f"Failed to remove contact: {e}")
            self.db.rollback()
            return False, str(e)
    
    async def update_contact_permissions(
        self,
        user_id: str,
        contact_id: str,
        interactions: int = 0,
        relationship_days: int = 0
    ) -> Tuple[bool, Dict[str, Any]]:
        """Update contact permissions based on interactions"""
        try:
            # Get contact slot
            contact_slot = self.db.query(ContactSlot).filter(
                and_(
                    ContactSlot.owner_id == user_id,
                    ContactSlot.contact_id == contact_id
                )
            ).first()
            
            if not contact_slot:
                return False, {"error": "Contact not found"}
            
            # Get user for trust score
            user = self.db.query(User).filter_by(id=user_id).first()
            if not user:
                return False, {"error": "User not found"}
            
            # Recalculate permission score
            new_score = self.calculate_permission_score(
                user.trust_score,
                interactions,
                relationship_days
            )
            
            # Determine new access level
            new_level = self.determine_access_level(
                new_score,
                user.is_premium
            )
            
            # Update contact slot
            contact_slot.permission_score = new_score
            contact_slot.access_level = new_level
            contact_slot.trust_level = user.trust_score
            contact_slot.updated_at = datetime.utcnow()
            
            # Update interaction count in metadata
            metadata = contact_slot.extra_metadata or {}
            metadata['interactions'] = interactions
            metadata['relationship_days'] = relationship_days
            metadata['last_interaction'] = datetime.utcnow().isoformat()
            contact_slot.extra_metadata = metadata
            
            self.db.commit()
            
            return True, {
                "contact_id": contact_id,
                "permission_score": new_score,
                "access_level": new_level.value,
                "previous_level": contact_slot.access_level.value,
                "trust_level": user.trust_score
            }
            
        except Exception as e:
            logger.error(f"Failed to update permissions: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    async def get_user_contacts(
        self,
        user_id: str,
        include_empty_slots: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all contacts for a user"""
        query = self.db.query(ContactSlot).filter_by(owner_id=user_id)
        
        if not include_empty_slots:
            query = query.filter(ContactSlot.is_used == True)
        
        contacts = query.order_by(ContactSlot.slot_number).all()
        
        return [
            {
                "slot_id": slot.id,
                "slot_number": slot.slot_number,
                "contact_id": slot.contact_id,
                "is_used": slot.is_used,
                "access_level": slot.access_level.value if slot.access_level else None,
                "permission_score": slot.permission_score,
                "trust_level": slot.trust_level,
                "created_at": slot.created_at.isoformat() if slot.created_at else None,
                "metadata": slot.extra_metadata
            }
            for slot in contacts
        ]
    
    async def check_contact_permission(
        self,
        user_id: str,
        contact_id: str,
        required_level: AccessLevel = AccessLevel.BASIC
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has permission to access contact at required level
        """
        contact_slot = self.db.query(ContactSlot).filter(
            and_(
                ContactSlot.owner_id == user_id,
                ContactSlot.contact_id == contact_id,
                ContactSlot.is_used == True
            )
        ).first()
        
        if not contact_slot:
            return False, "Contact not found in user's list"
        
        # Check access level
        current_weight = self.PERMISSION_WEIGHTS.get(contact_slot.access_level, 0)
        required_weight = self.PERMISSION_WEIGHTS.get(required_level, 0)
        
        if current_weight >= required_weight:
            return True, None
        else:
            return False, (
                f"Insufficient permissions. "
                f"Current: {contact_slot.access_level.value}, "
                f"Required: {required_level.value}"
            )
    
    async def allocate_bonus_slots(
        self,
        user_id: str,
        num_slots: int,
        reason: str = "reward"
    ) -> Tuple[bool, Dict[str, Any]]:
        """Allocate bonus contact slots to user"""
        try:
            user = self.db.query(User).filter_by(id=user_id).first()
            if not user:
                return False, {"error": "User not found"}
            
            # Add slots
            user.total_contact_slots += num_slots
            
            # Log in metadata
            metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "slots_added": num_slots,
                "reason": reason,
                "new_total": user.total_contact_slots
            }
            
            self.db.commit()
            
            logger.info(f"Allocated {num_slots} bonus slots to user {user_id}")
            
            return True, {
                "slots_added": num_slots,
                "total_slots": user.total_contact_slots,
                "available_slots": user.total_contact_slots - user.used_contact_slots,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Failed to allocate slots: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    async def get_contact_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get contact management statistics for user"""
        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            return {}
        
        contacts = await self.get_user_contacts(user_id)
        
        # Calculate statistics
        access_level_counts = {
            "basic": 0,
            "enhanced": 0,
            "premium": 0,
            "vip": 0
        }
        
        total_permission_score = 0
        for contact in contacts:
            if contact['access_level']:
                access_level_counts[contact['access_level']] += 1
                total_permission_score += contact['permission_score']
        
        avg_permission = (
            total_permission_score / len(contacts) 
            if contacts else 0
        )
        
        return {
            "total_slots": user.total_contact_slots,
            "used_slots": user.used_contact_slots,
            "available_slots": user.total_contact_slots - user.used_contact_slots,
            "contacts_count": len(contacts),
            "access_levels": access_level_counts,
            "average_permission_score": round(avg_permission, 2),
            "user_trust_score": round(user.trust_score, 2)
        }
    
    async def process_whatsapp_contact_command(
        self,
        user_id: str,
        command: str,
        args: List[str]
    ) -> str:
        """Process contact-related WhatsApp commands"""
        if command == "/contacts":
            stats = await self.get_contact_statistics(user_id)
            
            if not stats:
                return "❌ User profile not found"
            
            response = "👥 Contact Management\n"
            response += "═══════════════════\n"
            response += f"📊 Slots: {stats['used_slots']}/{stats['total_slots']}\n"
            response += f"✅ Available: {stats['available_slots']}\n\n"
            
            if stats['contacts_count'] > 0:
                response += "Access Levels:\n"
                for level, count in stats['access_levels'].items():
                    if count > 0:
                        emoji = {
                            "basic": "🔵",
                            "enhanced": "🟢",
                            "premium": "🟡",
                            "vip": "🔴"
                        }.get(level, "⚪")
                        response += f"  {emoji} {level.title()}: {count}\n"
                
                response += f"\n📈 Avg Permission: {stats['average_permission_score']}\n"
                response += f"🤝 Trust Score: {stats['user_trust_score']}"
            
            return response
        
        elif command == "/add_contact":
            if not args:
                return "❌ Usage: /add_contact PHONE_NUMBER"
            
            contact_phone = args[0]
            success, result = await self.add_contact(user_id, contact_phone)
            
            if success:
                return (
                    f"✅ Contact added!\n"
                    f"📱 Number: {contact_phone}\n"
                    f"🎯 Slot: #{result['slot_number']}\n"
                    f"🔐 Access: {result['access_level']}\n"
                    f"📊 Remaining: {result['remaining_slots']} slots"
                )
            else:
                return f"❌ {result.get('error', 'Failed to add contact')}"
        
        else:
            return (
                "👥 Contact Commands:\n"
                "═════════════════\n"
                "/contacts - View contact stats\n"
                "/add_contact PHONE - Add contact\n"
                "/remove_contact PHONE - Remove contact"
            )