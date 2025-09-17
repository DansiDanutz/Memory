"""
Invitation System for Gamified Voice Avatar
Manages invitation generation, tracking, and reward distribution
"""

import os
import secrets
import string
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .database_models import (
    Invitation, User, ContactSlot, Reward,
    InvitationStatus, Achievement, AchievementType
)

logger = logging.getLogger(__name__)

class InvitationSystem:
    """
    Manages the entire invitation lifecycle:
    - Generation of unique codes
    - Tracking of invitations
    - Reward distribution
    - Anti-abuse mechanisms
    """
    
    # Configuration
    CODE_LENGTH = 8
    CODE_EXPIRY_DAYS = 7
    MAX_INVITES_PER_DAY = 10
    MAX_PENDING_INVITES = 20
    INVITES_PER_REWARD = 5  # 5 accepted invites = 1 contact slot + voice avatar
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize invitation system"""
        self.db = db_session
        self.whatsapp_api_url = os.getenv("WHATSAPP_API_URL", "")
        self.whatsapp_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        
        logger.info("✅ Invitation system initialized")
    
    def _generate_unique_code(self) -> str:
        """Generate a unique invitation code"""
        # Use alphanumeric characters (excluding similar looking ones)
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        
        max_attempts = 100
        for _ in range(max_attempts):
            code = ''.join(secrets.choice(chars) for _ in range(self.CODE_LENGTH))
            
            # Check if code already exists
            if self.db:
                existing = self.db.query(Invitation).filter_by(code=code).first()
                if not existing:
                    return code
            else:
                return code
        
        raise ValueError("Failed to generate unique code after maximum attempts")
    
    async def create_invitation(
        self,
        sender_id: str,
        recipient_phone: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new invitation
        
        Args:
            sender_id: Phone number of the sender
            recipient_phone: Optional phone number of recipient
            custom_message: Optional custom invitation message
            
        Returns:
            (success, result) tuple
        """
        try:
            # Get or create sender user
            sender = self.db.query(User).filter_by(id=sender_id).first()
            if not sender:
                # Create new user
                sender = User(
                    id=sender_id,
                    display_name=f"User_{sender_id[-4:]}",
                    created_at=datetime.utcnow()
                )
                self.db.add(sender)
                self.db.commit()
            
            # Check rate limits
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
            today_invites = self.db.query(Invitation).filter(
                and_(
                    Invitation.sender_id == sender_id,
                    Invitation.created_at >= today_start
                )
            ).count()
            
            if today_invites >= self.MAX_INVITES_PER_DAY:
                return False, {
                    "error": "Daily invitation limit reached",
                    "limit": self.MAX_INVITES_PER_DAY,
                    "reset_time": (today_start + timedelta(days=1)).isoformat()
                }
            
            # Check pending invites
            pending_invites = self.db.query(Invitation).filter(
                and_(
                    Invitation.sender_id == sender_id,
                    Invitation.status == InvitationStatus.PENDING
                )
            ).count()
            
            if pending_invites >= self.MAX_PENDING_INVITES:
                return False, {
                    "error": "Too many pending invitations",
                    "limit": self.MAX_PENDING_INVITES,
                    "pending": pending_invites
                }
            
            # Generate invitation
            code = self._generate_unique_code()
            expires_at = datetime.utcnow() + timedelta(days=self.CODE_EXPIRY_DAYS)
            
            invitation = Invitation(
                code=code,
                sender_id=sender_id,
                recipient_phone=recipient_phone,
                status=InvitationStatus.PENDING,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                message_template=custom_message
            )
            
            self.db.add(invitation)
            
            # Update sender stats
            sender.total_invites_sent += 1
            
            self.db.commit()
            
            # Generate invitation link
            base_url = os.getenv("APP_BASE_URL", "https://memory.app")
            invitation_url = f"{base_url}/invite/{code}"
            
            # Send via WhatsApp if recipient provided
            if recipient_phone:
                await self._send_whatsapp_invitation(
                    recipient_phone,
                    code,
                    invitation_url,
                    custom_message
                )
                invitation.status = InvitationStatus.SENT
                invitation.sent_at = datetime.utcnow()
                self.db.commit()
            
            logger.info(f"Created invitation {code} from {sender_id}")
            
            return True, {
                "invitation_id": invitation.id,
                "code": code,
                "url": invitation_url,
                "expires_at": expires_at.isoformat(),
                "status": invitation.status.value
            }
            
        except Exception as e:
            logger.error(f"Failed to create invitation: {e}")
            if self.db:
                self.db.rollback()
            return False, {"error": str(e)}
    
    async def accept_invitation(
        self,
        code: str,
        recipient_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Accept an invitation
        
        Args:
            code: Invitation code
            recipient_id: Phone number of the recipient
            
        Returns:
            (success, result) tuple
        """
        try:
            # Find invitation
            invitation = self.db.query(Invitation).filter_by(code=code).first()
            
            if not invitation:
                return False, {"error": "Invalid invitation code"}
            
            # Check if expired
            if datetime.utcnow() > invitation.expires_at:
                invitation.status = InvitationStatus.EXPIRED
                self.db.commit()
                return False, {"error": "Invitation has expired"}
            
            # Check if already accepted
            if invitation.status == InvitationStatus.ACCEPTED:
                return False, {"error": "Invitation already accepted"}
            
            # Check if revoked
            if invitation.status == InvitationStatus.REVOKED:
                return False, {"error": "Invitation has been revoked"}
            
            # Prevent self-acceptance
            if invitation.sender_id == recipient_id:
                return False, {"error": "Cannot accept your own invitation"}
            
            # Get or create recipient user
            recipient = self.db.query(User).filter_by(id=recipient_id).first()
            if not recipient:
                recipient = User(
                    id=recipient_id,
                    display_name=f"User_{recipient_id[-4:]}",
                    created_at=datetime.utcnow()
                )
                self.db.add(recipient)
            
            # Accept invitation
            invitation.recipient_id = recipient_id
            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.utcnow()
            
            # Update sender stats
            sender = self.db.query(User).filter_by(id=invitation.sender_id).first()
            sender.total_invites_accepted += 1
            
            # Check for rewards
            rewards_earned = await self._calculate_rewards(sender)
            
            self.db.commit()
            
            logger.info(f"Invitation {code} accepted by {recipient_id}")
            
            return True, {
                "message": "Invitation accepted successfully",
                "sender_id": invitation.sender_id,
                "rewards_earned": rewards_earned
            }
            
        except Exception as e:
            logger.error(f"Failed to accept invitation: {e}")
            if self.db:
                self.db.rollback()
            return False, {"error": str(e)}
    
    async def _calculate_rewards(self, user: User) -> List[Dict[str, Any]]:
        """Calculate and distribute rewards based on accepted invitations"""
        rewards = []
        
        # Check if user qualifies for contact slot reward
        accepted_count = user.total_invites_accepted
        slots_earned = accepted_count // self.INVITES_PER_REWARD
        current_slots = user.total_contact_slots
        
        if slots_earned > current_slots:
            # Award new contact slots
            new_slots = slots_earned - current_slots
            for i in range(new_slots):
                # Create contact slot
                slot = ContactSlot(
                    owner_id=user.id,
                    slot_number=current_slots + i + 1,
                    earned_at=datetime.utcnow()
                )
                self.db.add(slot)
                
                # Create reward record
                reward = Reward(
                    user_id=user.id,
                    type="contact_slot",
                    amount=1,
                    description=f"Contact slot #{current_slots + i + 1}",
                    source_type="invitation_milestone",
                    source_id=str(accepted_count),
                    earned_at=datetime.utcnow()
                )
                self.db.add(reward)
                
                rewards.append({
                    "type": "contact_slot",
                    "slot_number": current_slots + i + 1
                })
            
            # Also award voice avatar for each slot
            for i in range(new_slots):
                voice_reward = Reward(
                    user_id=user.id,
                    type="voice_avatar",
                    amount=1,
                    description="Voice avatar creation credit",
                    source_type="invitation_milestone",
                    source_id=str(accepted_count),
                    earned_at=datetime.utcnow()
                )
                self.db.add(voice_reward)
                
                rewards.append({
                    "type": "voice_avatar",
                    "credits": 1
                })
            
            user.total_contact_slots = slots_earned
            user.total_voice_avatars += new_slots
        
        # Check for achievements
        achievements = await self._check_achievements(user)
        rewards.extend(achievements)
        
        # Update trust score
        user.trust_score = min(100.0, user.trust_score + 2.0)  # +2 per accepted invite
        
        # Award points
        points_earned = 100  # 100 points per accepted invitation
        user.points += points_earned
        rewards.append({
            "type": "points",
            "amount": points_earned
        })
        
        # Check level up
        new_level = self._calculate_level(user.points)
        if new_level > user.level:
            user.level = new_level
            rewards.append({
                "type": "level_up",
                "new_level": new_level
            })
        
        return rewards
    
    async def _check_achievements(self, user: User) -> List[Dict[str, Any]]:
        """Check and award achievements"""
        achievements = []
        accepted = user.total_invites_accepted
        
        # Achievement thresholds
        achievement_map = {
            1: (AchievementType.FIRST_INVITE, "First Steps", "Sent your first invitation"),
            5: (AchievementType.FIVE_INVITES, "Social Butterfly", "5 invitations accepted"),
            10: (AchievementType.TEN_INVITES, "Community Builder", "10 invitations accepted"),
            25: (AchievementType.COMMUNITY_LEADER, "Community Leader", "25 invitations accepted")
        }
        
        for threshold, (achievement_type, name, description) in achievement_map.items():
            if accepted >= threshold:
                # Check if already earned
                existing = self.db.query(Achievement).filter(
                    and_(
                        Achievement.user_id == user.id,
                        Achievement.type == achievement_type
                    )
                ).first()
                
                if not existing:
                    achievement = Achievement(
                        user_id=user.id,
                        type=achievement_type,
                        name=name,
                        description=description,
                        earned_at=datetime.utcnow()
                    )
                    self.db.add(achievement)
                    
                    achievements.append({
                        "type": "achievement",
                        "name": name,
                        "description": description
                    })
        
        return achievements
    
    def _calculate_level(self, points: int) -> int:
        """Calculate user level based on points"""
        # Level progression: 100, 300, 600, 1000, 1500, ...
        level = 1
        required_points = 0
        increment = 100
        
        while points >= required_points:
            level += 1
            required_points += increment * level
        
        return level - 1
    
    async def _send_whatsapp_invitation(
        self,
        recipient_phone: str,
        code: str,
        url: str,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send invitation via WhatsApp"""
        try:
            # Default message template
            default_message = f"""
🎉 You're invited to join Memory App!

Use this exclusive invitation code to get started:
📱 Code: {code}
🔗 Link: {url}

Join now and earn:
✅ Contact slots for trusted connections
🎙️ Voice avatar creation credits
🏆 Exclusive achievements

This invitation expires in 7 days.
            """
            
            message = custom_message or default_message
            
            # Send via WhatsApp API (placeholder - implement actual API call)
            # This would integrate with your existing WhatsApp handler
            logger.info(f"Sending WhatsApp invitation to {recipient_phone}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp invitation: {e}")
            return False
    
    async def get_user_invitations(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all invitations for a user"""
        try:
            query = self.db.query(Invitation).filter_by(sender_id=user_id)
            
            if not include_expired:
                query = query.filter(
                    or_(
                        Invitation.status != InvitationStatus.EXPIRED,
                        Invitation.expires_at > datetime.utcnow()
                    )
                )
            
            invitations = query.order_by(Invitation.created_at.desc()).all()
            
            return [{
                "id": inv.id,
                "code": inv.code,
                "status": inv.status.value,
                "recipient": inv.recipient_id,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat(),
                "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None
            } for inv in invitations]
            
        except Exception as e:
            logger.error(f"Failed to get user invitations: {e}")
            return []
    
    async def revoke_invitation(self, user_id: str, code: str) -> bool:
        """Revoke a pending invitation"""
        try:
            invitation = self.db.query(Invitation).filter(
                and_(
                    Invitation.code == code,
                    Invitation.sender_id == user_id,
                    Invitation.status == InvitationStatus.PENDING
                )
            ).first()
            
            if invitation:
                invitation.status = InvitationStatus.REVOKED
                self.db.commit()
                logger.info(f"Revoked invitation {code}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke invitation: {e}")
            if self.db:
                self.db.rollback()
            return False