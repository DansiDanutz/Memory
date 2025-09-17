"""
Daily Streak Tracking System
Manages user streaks, check-ins, and streak preservation mechanics
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_

from .database_models import Base, SessionLocal, UserStreak  # StreakActivity disabled
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, Float

logger = logging.getLogger(__name__)

class StreakMilestone(Base):
    """Streak milestone definitions and rewards"""
    __tablename__ = "streak_milestones"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    days = Column(Integer, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    reward_type = Column(String(50), nullable=False)
    reward_value = Column(JSON, nullable=False)
    icon = Column(String(50))
    rarity = Column(String(20), default="common", nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class StreakSystem:
    """
    Manages daily streaks, check-ins, and streak preservation
    """
    
    # Streak configuration
    GRACE_PERIOD_HOURS = 2  # Hours after midnight for grace period
    STREAK_MILESTONES = [3, 7, 14, 21, 30, 50, 60, 75, 100, 150, 200, 365]
    
    # Points for streak activities
    POINTS_DAILY_LOGIN = 10
    POINTS_STREAK_BONUS = 5  # Per day of streak
    POINTS_MILESTONE_MULTIPLIER = 10
    
    # Milestone rewards configuration
    MILESTONE_REWARDS = {
        3: {"type": "freeze_token", "value": 1, "name": "Starter", "icon": "🔥"},
        7: {"type": "points", "value": 100, "name": "Week Warrior", "icon": "📅"},
        14: {"type": "contact_slot", "value": 1, "name": "Fortnight Fighter", "icon": "🎯"},
        21: {"type": "voice_credit", "value": 1, "name": "Three Week Champion", "icon": "🏆"},
        30: {"type": "badge", "value": "monthly_streak", "name": "Monthly Master", "icon": "🌟"},
        50: {"type": "freeze_token", "value": 3, "name": "Streak Sentinel", "icon": "🛡️"},
        60: {"type": "points", "value": 500, "name": "Two Month Titan", "icon": "⚡"},
        75: {"type": "contact_slot", "value": 2, "name": "Persistent Pro", "icon": "💎"},
        100: {"type": "premium_feature", "value": "streak_shield", "name": "Century Champion", "icon": "👑"},
        150: {"type": "voice_credit", "value": 5, "name": "Dedication Deity", "icon": "🌈"},
        200: {"type": "badge", "value": "legendary_streak", "name": "Legendary", "icon": "🔮"},
        365: {"type": "lifetime_premium", "value": True, "name": "Year of Fire", "icon": "🌟"}
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize streak system"""
        self.db = db_session or SessionLocal()
        self._initialize_milestones()
        logger.info("✅ Streak System initialized")
    
    def _initialize_milestones(self):
        """Initialize milestone definitions in database"""
        try:
            for days, reward_data in self.MILESTONE_REWARDS.items():
                existing = self.db.query(StreakMilestone).filter_by(days=days).first()
                if not existing:
                    milestone = StreakMilestone(
                        days=days,
                        name=reward_data["name"],
                        description=f"Reach a {days}-day streak",
                        reward_type=reward_data["type"],
                        reward_value={"value": reward_data["value"]},
                        icon=reward_data["icon"],
                        rarity=self._get_milestone_rarity(days)
                    )
                    self.db.add(milestone)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to initialize milestones: {e}")
            self.db.rollback()
    
    def _get_milestone_rarity(self, days: int) -> str:
        """Determine milestone rarity based on days"""
        if days >= 365:
            return "legendary"
        elif days >= 100:
            return "epic"
        elif days >= 30:
            return "rare"
        elif days >= 14:
            return "uncommon"
        else:
            return "common"
    
    async def check_in(
        self,
        user_id: str,
        activity_type: str = "daily_login",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process daily check-in for a user
        Returns streak status and any rewards earned
        """
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get or create user streak record
            user_streak = self.db.query(UserStreak).filter_by(user_id=user_id).first()
            if not user_streak:
                user_streak = UserStreak(
                    user_id=user_id,
                    last_checkin=now,
                    next_reset=self._calculate_next_reset(now),
                    streak_start_date=today_start,
                    current_streak=1,
                    longest_streak=1,
                    total_checkins=1
                )
                self.db.add(user_streak)
                self.db.commit()
                
                # First check-in reward
                return {
                    "success": True,
                    "current_streak": 1,
                    "longest_streak": 1,
                    "is_new_user": True,
                    "points_earned": self.POINTS_DAILY_LOGIN,
                    "message": "Welcome! Your streak journey begins! 🔥",
                    "next_reset": user_streak.next_reset.isoformat()
                }
            
            # Check if already checked in today
            last_checkin_date = user_streak.last_checkin.date() if user_streak.last_checkin else None
            today_date = now.date()
            
            if last_checkin_date == today_date:
                return {
                    "success": False,
                    "already_checked_in": True,
                    "current_streak": user_streak.current_streak,
                    "message": "You've already checked in today! Come back tomorrow.",
                    "next_reset": user_streak.next_reset.isoformat()
                }
            
            # Calculate if streak should continue or break
            streak_continued = self._should_continue_streak(user_streak, now)
            
            if streak_continued:
                # Increment streak
                user_streak.current_streak += 1
                user_streak.last_checkin = now
                user_streak.next_reset = self._calculate_next_reset(now)
                user_streak.total_checkins += 1
                user_streak.missed_yesterday = False
                
                # Update longest streak if needed
                if user_streak.current_streak > user_streak.longest_streak:
                    user_streak.longest_streak = user_streak.current_streak
                
                # Calculate points
                points = self.POINTS_DAILY_LOGIN + (self.POINTS_STREAK_BONUS * min(user_streak.current_streak, 10))
                
                # Check for milestones
                milestone_reward = None
                if user_streak.current_streak in self.STREAK_MILESTONES:
                    milestone_reward = await self._process_milestone(
                        user_streak,
                        user_streak.current_streak
                    )
                    points += self.POINTS_MILESTONE_MULTIPLIER * user_streak.current_streak
                
                # Record activity (disabled - StreakActivity not available)
                # activity = StreakActivity(
                #     user_id=user_id,
                #     activity_date=now,
                #     activity_type=activity_type,
                #     points_earned=points
                # )
                # self.db.add(activity)
                
                # Check for perfect weeks/months
                if user_streak.current_streak % 7 == 0:
                    user_streak.perfect_weeks += 1
                if user_streak.current_streak % 30 == 0:
                    user_streak.perfect_months += 1
                
                self.db.commit()
                
                return {
                    "success": True,
                    "current_streak": user_streak.current_streak,
                    "longest_streak": user_streak.longest_streak,
                    "points_earned": points,
                    "milestone_reached": milestone_reward,
                    "freeze_tokens": user_streak.freeze_tokens,
                    "message": f"Streak continued! Day {user_streak.current_streak} 🔥",
                    "next_reset": user_streak.next_reset.isoformat()
                }
                
            else:
                # Streak broken - check for freeze token
                if user_streak.freeze_tokens > 0 and not user_streak.freeze_active:
                    # Auto-use freeze token
                    user_streak.freeze_tokens -= 1
                    user_streak.freeze_active = True
                    user_streak.freeze_expires = now + timedelta(hours=24)
                    user_streak.total_freezes_used += 1
                    user_streak.last_checkin = now
                    user_streak.next_reset = self._calculate_next_reset(now)
                    
                    self.db.commit()
                    
                    return {
                        "success": True,
                        "freeze_used": True,
                        "current_streak": user_streak.current_streak,
                        "freeze_tokens_remaining": user_streak.freeze_tokens,
                        "message": f"Freeze token used! Streak preserved at {user_streak.current_streak} days ❄️",
                        "next_reset": user_streak.next_reset.isoformat()
                    }
                else:
                    # Streak broken
                    old_streak = user_streak.current_streak
                    user_streak.current_streak = 1
                    user_streak.last_checkin = now
                    user_streak.next_reset = self._calculate_next_reset(now)
                    user_streak.streak_start_date = today_start
                    user_streak.total_checkins += 1
                    user_streak.freeze_active = False
                    
                    # Record activity (disabled - StreakActivity not available)
                    # activity = StreakActivity(
                    #     user_id=user_id,
                    #     activity_date=now,
                    #     activity_type="streak_broken",
                    #     points_earned=self.POINTS_DAILY_LOGIN
                    # )
                    # self.db.add(activity)
                    
                    self.db.commit()
                    
                    return {
                        "success": True,
                        "streak_broken": True,
                        "old_streak": old_streak,
                        "current_streak": 1,
                        "points_earned": self.POINTS_DAILY_LOGIN,
                        "message": f"Streak broken after {old_streak} days. Starting fresh! 💪",
                        "next_reset": user_streak.next_reset.isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Check-in failed for user {user_id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _should_continue_streak(self, user_streak: UserStreak, now: datetime) -> bool:
        """
        Determine if streak should continue based on last check-in and grace period
        """
        if not user_streak.last_checkin:
            return True
        
        # Calculate time since last check-in
        time_since = now - user_streak.last_checkin
        
        # Check if within grace period
        if time_since <= timedelta(hours=24 + self.GRACE_PERIOD_HOURS):
            return True
        
        # Check if freeze is active
        if user_streak.freeze_active and user_streak.freeze_expires:
            if now <= user_streak.freeze_expires:
                return True
        
        return False
    
    def _calculate_next_reset(self, now: datetime) -> datetime:
        """Calculate when the next daily reset occurs"""
        tomorrow = now + timedelta(days=1)
        next_reset = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        return next_reset + timedelta(hours=self.GRACE_PERIOD_HOURS)
    
    async def _process_milestone(
        self,
        user_streak: UserStreak,
        milestone_days: int
    ) -> Dict[str, Any]:
        """Process milestone rewards"""
        try:
            milestone = self.db.query(StreakMilestone).filter_by(days=milestone_days).first()
            if not milestone:
                return None
            
            # Track milestone
            milestones = user_streak.milestones_reached or []
            if milestone_days not in milestones:
                milestones.append(milestone_days)
                user_streak.milestones_reached = milestones
                user_streak.last_milestone = milestone_days
            
            reward_config = self.MILESTONE_REWARDS.get(milestone_days, {})
            
            # Apply milestone reward
            reward_type = reward_config.get("type")
            reward_value = reward_config.get("value")
            
            if reward_type == "freeze_token":
                user_streak.freeze_tokens += reward_value
            
            return {
                "milestone_days": milestone_days,
                "milestone_name": reward_config.get("name"),
                "reward_type": reward_type,
                "reward_value": reward_value,
                "icon": reward_config.get("icon")
            }
            
        except Exception as e:
            logger.error(f"Failed to process milestone: {e}")
            return None
    
    async def use_freeze_token(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Manually use a freeze token"""
        try:
            user_streak = self.db.query(UserStreak).filter_by(user_id=user_id).first()
            if not user_streak:
                return {"success": False, "error": "User streak not found"}
            
            if user_streak.freeze_tokens <= 0:
                return {"success": False, "error": "No freeze tokens available"}
            
            if user_streak.freeze_active:
                return {"success": False, "error": "Freeze already active"}
            
            user_streak.freeze_tokens -= 1
            user_streak.freeze_active = True
            user_streak.freeze_expires = datetime.now(timezone.utc) + timedelta(hours=24)
            user_streak.total_freezes_used += 1
            
            self.db.commit()
            
            return {
                "success": True,
                "freeze_tokens_remaining": user_streak.freeze_tokens,
                "freeze_expires": user_streak.freeze_expires.isoformat(),
                "message": "Freeze token activated! Your streak is protected for 24 hours ❄️"
            }
            
        except Exception as e:
            logger.error(f"Failed to use freeze token: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def get_streak_data(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive streak data for a user"""
        try:
            user_streak = self.db.query(UserStreak).filter_by(user_id=user_id).first()
            if not user_streak:
                return {
                    "current_streak": 0,
                    "longest_streak": 0,
                    "total_checkins": 0,
                    "freeze_tokens": 0,
                    "has_checked_in_today": False,
                    "milestones_reached": [],
                    "next_milestone": self.STREAK_MILESTONES[0]
                }
            
            # Check if already checked in today
            now = datetime.now(timezone.utc)
            has_checked_in_today = False
            if user_streak.last_checkin:
                has_checked_in_today = user_streak.last_checkin.date() == now.date()
            
            # Find next milestone
            next_milestone = None
            for milestone in self.STREAK_MILESTONES:
                if milestone > user_streak.current_streak:
                    next_milestone = milestone
                    break
            
            # Calculate time until reset
            time_until_reset = None
            if user_streak.next_reset:
                time_until_reset = (user_streak.next_reset - now).total_seconds()
            
            # Get recent activity (disabled - StreakActivity not available)
            # recent_activities = self.db.query(StreakActivity).filter_by(
            #     user_id=user_id
            # ).order_by(StreakActivity.activity_date.desc()).limit(7).all()
            
            activity_calendar = []  # Empty for now since StreakActivity is disabled
            # activity_calendar = [
            #     {
            #         "date": activity.activity_date.isoformat(),
            #         "type": activity.activity_type,
            #         "points": activity.points_earned
            #     }
            #     for activity in recent_activities
            # ]
            
            return {
                "current_streak": user_streak.current_streak,
                "longest_streak": user_streak.longest_streak,
                "total_checkins": user_streak.total_checkins,
                "freeze_tokens": user_streak.freeze_tokens,
                "freeze_active": user_streak.freeze_active,
                "freeze_expires": user_streak.freeze_expires.isoformat() if user_streak.freeze_expires else None,
                "has_checked_in_today": has_checked_in_today,
                "last_checkin": user_streak.last_checkin.isoformat() if user_streak.last_checkin else None,
                "next_reset": user_streak.next_reset.isoformat() if user_streak.next_reset else None,
                "time_until_reset": time_until_reset,
                "milestones_reached": user_streak.milestones_reached or [],
                "next_milestone": next_milestone,
                "perfect_weeks": user_streak.perfect_weeks,
                "perfect_months": user_streak.perfect_months,
                "total_freezes_used": user_streak.total_freezes_used,
                "activity_calendar": activity_calendar,
                "streak_start_date": user_streak.streak_start_date.isoformat() if user_streak.streak_start_date else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get streak data: {e}")
            return {"error": str(e)}
    
    async def get_leaderboard(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get streak leaderboard"""
        try:
            top_streaks = self.db.query(UserStreak).order_by(
                UserStreak.current_streak.desc()
            ).limit(limit).all()
            
            leaderboard = []
            for i, streak in enumerate(top_streaks, 1):
                leaderboard.append({
                    "rank": i,
                    "user_id": streak.user_id,
                    "current_streak": streak.current_streak,
                    "longest_streak": streak.longest_streak,
                    "total_checkins": streak.total_checkins,
                    "perfect_weeks": streak.perfect_weeks
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return []