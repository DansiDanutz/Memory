"""
Main Gamified Voice Avatar System Coordinator
Orchestrates all gamification components and provides unified interface
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from .database_models import (
    User, Invitation, ContactSlot, VoiceAvatar, Achievement, Reward,
    InvitationStatus, AvatarStatus, AccessLevel, AchievementType,
    SessionLocal, init_db
)
from .invitation_system import InvitationSystem
from .voice_avatar_system import VoiceAvatarSystem
from .contact_permissions import ContactPermissionManager
from .rewards_engine import RewardsEngine
from .elevenlabs_service import ElevenLabsService

logger = logging.getLogger(__name__)

class GamifiedVoiceAvatarSystem:
    """
    Main coordinator for the gamified voice avatar system
    Integrates all components and provides unified API
    """
    
    def __init__(self):
        """Initialize the gamification system"""
        # Initialize database
        init_db()
        
        # Initialize components
        self.db_session = SessionLocal()
        self.invitation_system = InvitationSystem(self.db_session)
        self.voice_avatar_system = VoiceAvatarSystem(self.db_session)
        self.permission_manager = ContactPermissionManager(self.db_session)
        self.rewards_engine = RewardsEngine(self.db_session)
        self.elevenlabs = ElevenLabsService()
        
        # Cache for user data
        self.user_cache = {}
        
        logger.info("✅ Gamified Voice Avatar System initialized")
    
    async def get_or_create_user(self, phone_number: str) -> User:
        """Get or create a user profile"""
        # Check cache first
        if phone_number in self.user_cache:
            return self.user_cache[phone_number]
        
        # Check database
        user = self.db_session.query(User).filter_by(id=phone_number).first()
        if not user:
            # Create new user
            user = User(
                id=phone_number,
                display_name=f"User_{phone_number[-4:]}",
                created_at=datetime.utcnow(),
                total_contact_slots=3  # Start with 3 free slots
            )
            self.db_session.add(user)
            self.db_session.commit()
            
            # Award first-time achievement
            await self.rewards_engine.award_achievement(
                user.id,
                AchievementType.FIRST_INVITE,
                "Welcome to the community!"
            )
        
        # Cache the user
        self.user_cache[phone_number] = user
        return user
    
    async def create_invitation(
        self,
        sender_phone: str,
        recipient_phone: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create and send an invitation
        """
        # Get or create sender
        sender = await self.get_or_create_user(sender_phone)
        
        # Create invitation
        success, result = await self.invitation_system.create_invitation(
            sender_phone,
            recipient_phone,
            custom_message
        )
        
        if success:
            # Check for invitation milestones
            if sender.total_invites_sent == 1:
                await self.rewards_engine.award_achievement(
                    sender.id,
                    AchievementType.FIRST_INVITE,
                    "Sent your first invitation!"
                )
            elif sender.total_invites_sent == 5:
                await self.rewards_engine.award_achievement(
                    sender.id,
                    AchievementType.FIVE_INVITES,
                    "Community builder - 5 invitations sent!"
                )
            elif sender.total_invites_sent == 10:
                await self.rewards_engine.award_achievement(
                    sender.id,
                    AchievementType.TEN_INVITES,
                    "Ambassador - 10 invitations sent!"
                )
        
        return success, result
    
    async def accept_invitation(
        self,
        invitation_code: str,
        recipient_phone: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Accept an invitation and trigger rewards
        """
        success, result = await self.invitation_system.accept_invitation(
            invitation_code,
            recipient_phone
        )
        
        if success:
            # Trigger reward calculation
            invitation = self.db_session.query(Invitation).filter_by(
                code=invitation_code
            ).first()
            
            if invitation:
                await self.rewards_engine.process_invitation_accepted(
                    invitation.sender_id,
                    invitation.id
                )
        
        return success, result
    
    async def create_voice_avatar(
        self,
        user_phone: str,
        name: str,
        audio_samples: List[bytes],
        description: str = ""
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a voice avatar for a user
        """
        # Check if user has available avatar credits
        user = await self.get_or_create_user(user_phone)
        available_avatars = await self.rewards_engine.get_available_avatar_credits(user.id)
        
        if available_avatars <= 0:
            return False, {
                "error": "No voice avatar credits available",
                "hint": "Invite 5 friends to earn a voice avatar credit"
            }
        
        # Create the avatar
        success, result = await self.voice_avatar_system.create_avatar(
            user.id,
            name,
            audio_samples,
            description
        )
        
        if success:
            # Consume avatar credit
            await self.rewards_engine.consume_avatar_credit(user.id)
            
            # Check for first avatar achievement
            if user.total_voice_avatars == 1:
                await self.rewards_engine.award_achievement(
                    user.id,
                    AchievementType.FIRST_AVATAR,
                    "Created your first voice avatar!"
                )
        
        return success, result
    
    async def add_contact(
        self,
        user_phone: str,
        contact_phone: str,
        access_level: AccessLevel = AccessLevel.BASIC
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Add a contact to user's contact list
        """
        user = await self.get_or_create_user(user_phone)
        
        # Check available slots
        available_slots = user.total_contact_slots - user.used_contact_slots
        if available_slots <= 0:
            return False, {
                "error": "No available contact slots",
                "hint": "Invite friends to earn more contact slots",
                "total_slots": user.total_contact_slots,
                "used_slots": user.used_contact_slots
            }
        
        # Add contact
        success, contact_slot = await self.permission_manager.add_contact(
            user.id,
            contact_phone,
            access_level
        )
        
        if success:
            # Update used slots
            user.used_contact_slots += 1
            self.db_session.commit()
            
            # Check for contact master achievement
            if user.used_contact_slots >= 10:
                await self.rewards_engine.award_achievement(
                    user.id,
                    AchievementType.CONTACT_MASTER,
                    "Contact Master - Managing 10+ contacts!"
                )
        
        return success, {"contact_slot": contact_slot, "remaining_slots": available_slots - 1}
    
    async def get_user_stats(self, user_phone: str) -> Dict[str, Any]:
        """
        Get comprehensive user statistics
        """
        user = await self.get_or_create_user(user_phone)
        
        # Get achievements
        achievements = self.db_session.query(Achievement).filter_by(
            user_id=user.id
        ).all()
        
        # Get pending rewards
        pending_rewards = self.db_session.query(Reward).filter_by(
            user_id=user.id,
            is_claimed=False
        ).all()
        
        # Get active invitations
        active_invitations = self.db_session.query(Invitation).filter_by(
            sender_id=user.id,
            status=InvitationStatus.PENDING
        ).all()
        
        # Get voice avatars
        voice_avatars = self.db_session.query(VoiceAvatar).filter_by(
            owner_id=user.id
        ).all()
        
        return {
            "user": {
                "id": user.id,
                "display_name": user.display_name,
                "level": user.level,
                "points": user.points,
                "trust_score": user.trust_score,
                "is_premium": user.is_premium
            },
            "invitations": {
                "total_sent": user.total_invites_sent,
                "total_accepted": user.total_invites_accepted,
                "pending": len(active_invitations),
                "acceptance_rate": (
                    user.total_invites_accepted / user.total_invites_sent 
                    if user.total_invites_sent > 0 else 0
                ) * 100
            },
            "contacts": {
                "total_slots": user.total_contact_slots,
                "used_slots": user.used_contact_slots,
                "available_slots": user.total_contact_slots - user.used_contact_slots
            },
            "voice_avatars": {
                "total_created": user.total_voice_avatars,
                "active": len([a for a in voice_avatars if a.status == AvatarStatus.ACTIVE]),
                "available_credits": await self.rewards_engine.get_available_avatar_credits(user.id)
            },
            "achievements": [
                {
                    "type": a.type.value,
                    "name": a.name,
                    "description": a.description,
                    "earned_at": a.earned_at.isoformat()
                }
                for a in achievements
            ],
            "pending_rewards": [
                {
                    "type": r.type,
                    "amount": r.amount,
                    "description": r.description,
                    "earned_at": r.earned_at.isoformat()
                }
                for r in pending_rewards
            ]
        }
    
    async def get_leaderboard(
        self,
        metric: str = "points",
        period: str = "all_time",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get leaderboard for a specific metric
        """
        # Query users based on metric
        query = self.db_session.query(User)
        
        if metric == "points":
            query = query.order_by(User.points.desc())
        elif metric == "invites":
            query = query.order_by(User.total_invites_accepted.desc())
        elif metric == "trust":
            query = query.order_by(User.trust_score.desc())
        elif metric == "avatars":
            query = query.order_by(User.total_voice_avatars.desc())
        else:
            query = query.order_by(User.points.desc())
        
        users = query.limit(limit).all()
        
        return [
            {
                "rank": idx + 1,
                "user": {
                    "id": user.id,
                    "display_name": user.display_name,
                    "level": user.level,
                    "is_premium": user.is_premium
                },
                "metric_value": getattr(user, {
                    "points": "points",
                    "invites": "total_invites_accepted",
                    "trust": "trust_score",
                    "avatars": "total_voice_avatars"
                }.get(metric, "points"))
            }
            for idx, user in enumerate(users)
        ]
    
    async def process_whatsapp_command(
        self,
        phone_number: str,
        command: str,
        args: List[str]
    ) -> str:
        """
        Process WhatsApp commands for gamification
        """
        if command == "/invite":
            # Generate invitation
            recipient = args[0] if args else None
            success, result = await self.create_invitation(phone_number, recipient)
            
            if success:
                return (
                    f"🎉 Invitation created!\n"
                    f"📱 Code: {result['code']}\n"
                    f"🔗 Link: {result['url']}\n"
                    f"⏰ Expires: {result['expires_at'][:10]}\n\n"
                    f"Share this link with your friends!"
                )
            else:
                return f"❌ {result.get('error', 'Failed to create invitation')}"
        
        elif command == "/stats":
            # Get user statistics
            stats = await self.get_user_stats(phone_number)
            
            return (
                f"📊 Your Statistics\n"
                f"═══════════════════\n"
                f"🏆 Level: {stats['user']['level']}\n"
                f"⭐ Points: {stats['user']['points']}\n"
                f"🤝 Trust Score: {stats['user']['trust_score']:.1f}\n\n"
                f"📬 Invitations:\n"
                f"  • Sent: {stats['invitations']['total_sent']}\n"
                f"  • Accepted: {stats['invitations']['total_accepted']}\n"
                f"  • Success Rate: {stats['invitations']['acceptance_rate']:.0f}%\n\n"
                f"👥 Contacts:\n"
                f"  • Slots: {stats['contacts']['used_slots']}/{stats['contacts']['total_slots']}\n"
                f"  • Available: {stats['contacts']['available_slots']}\n\n"
                f"🎭 Voice Avatars:\n"
                f"  • Created: {stats['voice_avatars']['total_created']}\n"
                f"  • Active: {stats['voice_avatars']['active']}\n"
                f"  • Credits: {stats['voice_avatars']['available_credits']}\n\n"
                f"🏅 Achievements: {len(stats['achievements'])}\n"
                f"🎁 Pending Rewards: {len(stats['pending_rewards'])}"
            )
        
        elif command == "/leaderboard":
            # Get leaderboard
            metric = args[0] if args else "points"
            leaderboard = await self.get_leaderboard(metric, limit=5)
            
            emoji_map = {
                1: "🥇",
                2: "🥈",
                3: "🥉",
                4: "4️⃣",
                5: "5️⃣"
            }
            
            response = f"🏆 Leaderboard - {metric.title()}\n"
            response += "═══════════════════\n"
            
            for entry in leaderboard:
                emoji = emoji_map.get(entry['rank'], "")
                response += (
                    f"{emoji} {entry['user']['display_name']} "
                    f"(Lvl {entry['user']['level']}): {entry['metric_value']}\n"
                )
            
            return response
        
        elif command == "/accept":
            # Accept invitation
            if not args:
                return "❌ Please provide invitation code: /accept CODE"
            
            code = args[0]
            success, result = await self.accept_invitation(code, phone_number)
            
            if success:
                return (
                    f"✅ Invitation accepted!\n"
                    f"🎉 Welcome to the community!\n"
                    f"🎁 Check /stats for your rewards"
                )
            else:
                return f"❌ {result.get('error', 'Failed to accept invitation')}"
        
        else:
            return (
                "📱 Gamification Commands:\n"
                "════════════════════\n"
                "/invite [phone] - Create invitation\n"
                "/accept CODE - Accept invitation\n"
                "/stats - View your statistics\n"
                "/leaderboard [metric] - View rankings\n"
                "\nMetrics: points, invites, trust, avatars"
            )
    
    def close(self):
        """Close database connections"""
        self.db_session.close()
        logger.info("Gamification system closed")

# Singleton instance
_instance = None

def get_gamification_system() -> GamifiedVoiceAvatarSystem:
    """Get singleton instance of gamification system"""
    global _instance
    if _instance is None:
        _instance = GamifiedVoiceAvatarSystem()
    return _instance