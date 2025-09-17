"""
Rewards Calculation Engine
Manages reward distribution, achievement tracking, and point calculations
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from .database_models import (
    User, Invitation, Reward, Achievement, Leaderboard,
    InvitationStatus, AchievementType,
    SessionLocal
)

logger = logging.getLogger(__name__)

class RewardsEngine:
    """
    Calculates and distributes rewards for user actions
    """
    
    # Reward configuration
    INVITES_PER_CONTACT_SLOT = 5
    INVITES_PER_AVATAR_CREDIT = 5
    POINTS_PER_INVITE_SENT = 10
    POINTS_PER_INVITE_ACCEPTED = 50
    POINTS_PER_ACHIEVEMENT = 100
    
    # Level thresholds
    LEVEL_THRESHOLDS = [
        0,     # Level 1
        100,   # Level 2
        250,   # Level 3
        500,   # Level 4
        1000,  # Level 5
        2000,  # Level 6
        3500,  # Level 7
        5500,  # Level 8
        8000,  # Level 9
        11000  # Level 10+
    ]
    
    # Trust score factors
    TRUST_FACTORS = {
        "invite_acceptance_rate": 0.3,
        "avatar_creation": 0.2,
        "contact_management": 0.2,
        "community_engagement": 0.15,
        "achievement_completion": 0.15
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize rewards engine"""
        self.db = db_session or SessionLocal()
        logger.info("✅ Rewards Engine initialized")
    
    def calculate_user_level(self, points: int) -> int:
        """Calculate user level based on points"""
        for level, threshold in enumerate(self.LEVEL_THRESHOLDS, 1):
            if points < threshold:
                return level - 1
        return len(self.LEVEL_THRESHOLDS)
    
    def calculate_trust_score(
        self,
        user: User,
        detailed: bool = False
    ) -> Union[float, Tuple[float, Dict[str, float]]]:
        """
        Calculate user's trust score based on multiple factors
        """
        scores = {}
        
        # Invite acceptance rate (0-1)
        if user.total_invites_sent > 0:
            acceptance_rate = user.total_invites_accepted / user.total_invites_sent
        else:
            acceptance_rate = 0
        scores["invite_acceptance_rate"] = acceptance_rate
        
        # Avatar creation score (0-1)
        avatar_score = min(1.0, user.total_voice_avatars / 5)
        scores["avatar_creation"] = avatar_score
        
        # Contact management score (0-1)
        if user.total_contact_slots > 0:
            contact_usage = user.used_contact_slots / user.total_contact_slots
        else:
            contact_usage = 0
        scores["contact_management"] = contact_usage
        
        # Community engagement (based on invites sent)
        engagement_score = min(1.0, user.total_invites_sent / 20)
        scores["community_engagement"] = engagement_score
        
        # Achievement completion
        total_achievements = len(AchievementType)
        earned_achievements = self.db.query(Achievement).filter_by(
            user_id=user.id
        ).count()
        achievement_score = earned_achievements / total_achievements if total_achievements > 0 else 0
        scores["achievement_completion"] = achievement_score
        
        # Calculate weighted trust score
        trust_score = sum(
            scores[factor] * weight
            for factor, weight in self.TRUST_FACTORS.items()
        )
        
        if detailed:
            return trust_score, scores
        return trust_score
    
    async def process_invitation_accepted(
        self,
        sender_id: str,
        invitation_id: int
    ) -> Dict[str, Any]:
        """
        Process rewards when an invitation is accepted
        """
        try:
            # Get user
            user = self.db.query(User).filter_by(id=sender_id).first()
            if not user:
                return {"error": "User not found"}
            
            # Update accepted count
            user.total_invites_accepted += 1
            
            # Award points
            user.points += self.POINTS_PER_INVITE_ACCEPTED
            
            # Check for contact slot reward
            if user.total_invites_accepted % self.INVITES_PER_CONTACT_SLOT == 0:
                # Award contact slot
                user.total_contact_slots += 1
                
                # Create reward record
                reward = Reward(
                    user_id=sender_id,
                    type="contact_slot",
                    amount=1,
                    description=f"Earned contact slot for {self.INVITES_PER_CONTACT_SLOT} accepted invites",
                    source_type="invitation_milestone",
                    source_id=str(invitation_id),
                    earned_at=datetime.utcnow()
                )
                self.db.add(reward)
                
                logger.info(f"Awarded contact slot to user {sender_id}")
            
            # Check for avatar credit reward
            if user.total_invites_accepted % self.INVITES_PER_AVATAR_CREDIT == 0:
                # Create avatar credit reward
                reward = Reward(
                    user_id=sender_id,
                    type="voice_avatar",
                    amount=1,
                    description=f"Earned voice avatar credit for {self.INVITES_PER_AVATAR_CREDIT} accepted invites",
                    source_type="invitation_milestone",
                    source_id=str(invitation_id),
                    earned_at=datetime.utcnow()
                )
                self.db.add(reward)
                
                logger.info(f"Awarded voice avatar credit to user {sender_id}")
            
            # Update level
            new_level = self.calculate_user_level(user.points)
            if new_level > user.level:
                user.level = new_level
                
                # Create level up reward
                reward = Reward(
                    user_id=sender_id,
                    type="level_up",
                    amount=new_level,
                    description=f"Reached level {new_level}!",
                    source_type="level_milestone",
                    earned_at=datetime.utcnow()
                )
                self.db.add(reward)
            
            # Update trust score
            user.trust_score = self.calculate_trust_score(user)
            
            self.db.commit()
            
            return {
                "success": True,
                "points_awarded": self.POINTS_PER_INVITE_ACCEPTED,
                "total_points": user.points,
                "level": user.level,
                "trust_score": user.trust_score,
                "invites_accepted": user.total_invites_accepted
            }
            
        except Exception as e:
            logger.error(f"Failed to process invitation acceptance: {e}")
            self.db.rollback()
            return {"error": str(e)}
    
    async def award_achievement(
        self,
        user_id: str,
        achievement_type: AchievementType,
        description: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Award an achievement to user"""
        try:
            # Check if already earned
            existing = self.db.query(Achievement).filter_by(
                user_id=user_id,
                type=achievement_type
            ).first()
            
            if existing:
                return False, {"error": "Achievement already earned"}
            
            # Create achievement
            achievement = Achievement(
                user_id=user_id,
                type=achievement_type,
                name=achievement_type.value.replace("_", " ").title(),
                description=description,
                earned_at=datetime.utcnow()
            )
            self.db.add(achievement)
            
            # Award points
            user = self.db.query(User).filter_by(id=user_id).first()
            if user:
                user.points += self.POINTS_PER_ACHIEVEMENT
                
                # Create reward record
                reward = Reward(
                    user_id=user_id,
                    type="achievement",
                    amount=self.POINTS_PER_ACHIEVEMENT,
                    description=f"Achievement unlocked: {achievement.name}",
                    source_type="achievement",
                    source_id=achievement_type.value,
                    earned_at=datetime.utcnow()
                )
                self.db.add(reward)
            
            self.db.commit()
            
            logger.info(f"Awarded achievement {achievement_type.value} to user {user_id}")
            
            return True, {
                "achievement": achievement.name,
                "description": description,
                "points_awarded": self.POINTS_PER_ACHIEVEMENT,
                "earned_at": achievement.earned_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to award achievement: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    async def get_available_avatar_credits(self, user_id: str) -> int:
        """Get number of available voice avatar credits"""
        # Count unclaimed avatar rewards
        unclaimed = self.db.query(Reward).filter(
            and_(
                Reward.user_id == user_id,
                Reward.type == "voice_avatar",
                Reward.is_claimed == False
            )
        ).count()
        
        return unclaimed
    
    async def consume_avatar_credit(self, user_id: str) -> bool:
        """Consume one voice avatar credit"""
        # Find oldest unclaimed avatar reward
        reward = self.db.query(Reward).filter(
            and_(
                Reward.user_id == user_id,
                Reward.type == "voice_avatar",
                Reward.is_claimed == False
            )
        ).order_by(Reward.earned_at).first()
        
        if reward:
            reward.is_claimed = True
            reward.claimed_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    async def get_pending_rewards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all pending rewards for user"""
        rewards = self.db.query(Reward).filter(
            and_(
                Reward.user_id == user_id,
                Reward.is_claimed == False
            )
        ).order_by(Reward.earned_at.desc()).all()
        
        return [
            {
                "id": reward.id,
                "type": reward.type,
                "amount": reward.amount,
                "description": reward.description,
                "earned_at": reward.earned_at.isoformat(),
                "expires_at": reward.expires_at.isoformat() if reward.expires_at else None
            }
            for reward in rewards
        ]
    
    async def claim_reward(
        self,
        user_id: str,
        reward_id: int
    ) -> Tuple[bool, str]:
        """Claim a specific reward"""
        reward = self.db.query(Reward).filter(
            and_(
                Reward.id == reward_id,
                Reward.user_id == user_id,
                Reward.is_claimed == False
            )
        ).first()
        
        if not reward:
            return False, "Reward not found or already claimed"
        
        # Check expiration
        if reward.expires_at and reward.expires_at < datetime.utcnow():
            return False, "Reward has expired"
        
        # Claim the reward
        reward.is_claimed = True
        reward.claimed_at = datetime.utcnow()
        
        # Apply reward effects based on type
        user = self.db.query(User).filter_by(id=user_id).first()
        if user:
            if reward.type == "points":
                user.points += reward.amount
            elif reward.type == "contact_slot":
                user.total_contact_slots += reward.amount
        
        self.db.commit()
        
        return True, f"Reward claimed: {reward.description}"
    
    async def update_leaderboard(
        self,
        period: str = "all_time"
    ) -> None:
        """Update leaderboard entries"""
        # Determine time range
        now = datetime.utcnow()
        if period == "daily":
            period_start = now.replace(hour=0, minute=0, second=0)
            period_end = period_start + timedelta(days=1)
        elif period == "weekly":
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(hour=0, minute=0, second=0)
            period_end = period_start + timedelta(weeks=1)
        elif period == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0)
            if now.month == 12:
                period_end = period_start.replace(year=now.year + 1, month=1)
            else:
                period_end = period_start.replace(month=now.month + 1)
        else:  # all_time
            period_start = datetime(2020, 1, 1)
            period_end = datetime(2100, 1, 1)
        
        # Update different metrics
        metrics = [
            ("points", User.points),
            ("invites", User.total_invites_accepted),
            ("trust", User.trust_score),
            ("avatars", User.total_voice_avatars)
        ]
        
        for metric_type, column in metrics:
            # Get top users for this metric
            users = self.db.query(User).order_by(column.desc()).limit(100).all()
            
            for rank, user in enumerate(users, 1):
                # Check if entry exists
                entry = self.db.query(Leaderboard).filter(
                    and_(
                        Leaderboard.user_id == user.id,
                        Leaderboard.metric_type == metric_type,
                        Leaderboard.period == period,
                        Leaderboard.period_start == period_start
                    )
                ).first()
                
                if entry:
                    # Update existing entry
                    entry.metric_value = float(getattr(user, column.key))
                    entry.rank = rank
                    entry.updated_at = now
                else:
                    # Create new entry
                    entry = Leaderboard(
                        user_id=user.id,
                        metric_type=metric_type,
                        metric_value=float(getattr(user, column.key)),
                        rank=rank,
                        period=period,
                        period_start=period_start,
                        period_end=period_end,
                        updated_at=now
                    )
                    self.db.add(entry)
        
        self.db.commit()
        logger.info(f"Updated {period} leaderboard")
    
    async def calculate_reward_summary(self, user_id: str) -> Dict[str, Any]:
        """Calculate comprehensive reward summary for user"""
        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            return {}
        
        # Get all rewards
        all_rewards = self.db.query(Reward).filter_by(user_id=user_id).all()
        
        # Calculate statistics
        total_earned = len(all_rewards)
        total_claimed = sum(1 for r in all_rewards if r.is_claimed)
        pending = total_earned - total_claimed
        
        # Group by type
        reward_types = {}
        for reward in all_rewards:
            if reward.type not in reward_types:
                reward_types[reward.type] = {"earned": 0, "claimed": 0}
            reward_types[reward.type]["earned"] += 1
            if reward.is_claimed:
                reward_types[reward.type]["claimed"] += 1
        
        # Calculate next milestones
        invites_to_next_slot = (
            self.INVITES_PER_CONTACT_SLOT - 
            (user.total_invites_accepted % self.INVITES_PER_CONTACT_SLOT)
        )
        
        invites_to_next_avatar = (
            self.INVITES_PER_AVATAR_CREDIT - 
            (user.total_invites_accepted % self.INVITES_PER_AVATAR_CREDIT)
        )
        
        points_to_next_level = (
            self.LEVEL_THRESHOLDS[min(user.level, len(self.LEVEL_THRESHOLDS) - 1)] - 
            user.points
        )
        
        return {
            "total_rewards_earned": total_earned,
            "total_rewards_claimed": total_claimed,
            "pending_rewards": pending,
            "reward_types": reward_types,
            "next_milestones": {
                "contact_slot": invites_to_next_slot,
                "voice_avatar": invites_to_next_avatar,
                "level_up": points_to_next_level
            },
            "current_stats": {
                "level": user.level,
                "points": user.points,
                "trust_score": round(user.trust_score, 2),
                "invites_accepted": user.total_invites_accepted
            }
        }