"""
Scheduled Tasks for Gamification System
Handles automated streak resets, notifications, and maintenance tasks
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from .database_models import SessionLocal
from .streak_system import StreakSystem, UserStreak, StreakActivity
from .variable_rewards import VariableRewardsEngine, UserRewardState

logger = logging.getLogger(__name__)

class GamificationScheduler:
    """
    Manages scheduled tasks for the gamification system
    """
    
    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.streak_system = StreakSystem()
        self.rewards_engine = VariableRewardsEngine()
        self.db = SessionLocal()
        
        self._setup_scheduled_tasks()
        logger.info("✅ Gamification Scheduler initialized")
    
    def _setup_scheduled_tasks(self):
        """Configure all scheduled tasks"""
        
        # Daily reset at midnight UTC
        self.scheduler.add_job(
            self.daily_reset_task,
            CronTrigger(hour=0, minute=0, timezone="UTC"),
            id="daily_reset",
            name="Daily Reset Task",
            misfire_grace_time=300  # 5 minute grace period
        )
        
        # Streak reminder notifications
        # First reminder at 8 PM
        self.scheduler.add_job(
            self.send_streak_reminders,
            CronTrigger(hour=20, minute=0, timezone="UTC"),
            id="evening_reminder",
            name="Evening Streak Reminder"
        )
        
        # Final reminder at 11 PM
        self.scheduler.add_job(
            self.send_urgent_streak_reminders,
            CronTrigger(hour=23, minute=0, timezone="UTC"),
            id="urgent_reminder",
            name="Urgent Streak Reminder"
        )
        
        # Process milestone rewards every hour
        self.scheduler.add_job(
            self.process_milestone_rewards,
            IntervalTrigger(hours=1),
            id="milestone_rewards",
            name="Process Milestone Rewards"
        )
        
        # Clean up expired data every 6 hours
        self.scheduler.add_job(
            self.cleanup_expired_data,
            IntervalTrigger(hours=6),
            id="cleanup_task",
            name="Cleanup Expired Data"
        )
        
        # Update leaderboards every 15 minutes
        self.scheduler.add_job(
            self.update_leaderboards,
            IntervalTrigger(minutes=15),
            id="leaderboard_update",
            name="Update Leaderboards"
        )
        
        # Send weekly summary every Monday at 9 AM
        self.scheduler.add_job(
            self.send_weekly_summaries,
            CronTrigger(day_of_week=0, hour=9, minute=0, timezone="UTC"),
            id="weekly_summary",
            name="Weekly Summary"
        )
    
    async def daily_reset_task(self):
        """
        Daily reset task - runs at midnight UTC
        """
        try:
            logger.info("🔄 Starting daily reset task")
            
            # Reset daily spin limits
            self.db.query(UserRewardState).update({
                "daily_spins_used": 0,
                "last_daily_spin": None
            })
            
            # Mark users who didn't check in as missed
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            missed_users = self.db.query(UserStreak).filter(
                and_(
                    UserStreak.last_checkin < cutoff_time,
                    UserStreak.current_streak > 0,
                    UserStreak.freeze_active == False
                )
            ).all()
            
            for user_streak in missed_users:
                user_streak.missed_yesterday = True
                
                # Auto-use freeze token if available
                if user_streak.freeze_tokens > 0:
                    user_streak.freeze_tokens -= 1
                    user_streak.freeze_active = True
                    user_streak.freeze_expires = datetime.now(timezone.utc) + timedelta(hours=24)
                    user_streak.total_freezes_used += 1
                    logger.info(f"Auto-used freeze token for user {user_streak.user_id}")
            
            self.db.commit()
            
            # Log statistics
            total_active = self.db.query(func.count(UserStreak.user_id)).filter(
                UserStreak.current_streak > 0
            ).scalar()
            
            logger.info(f"✅ Daily reset completed. Active streaks: {total_active}, Auto-frozen: {len(missed_users)}")
            
        except Exception as e:
            logger.error(f"Daily reset task failed: {e}")
            self.db.rollback()
    
    async def send_streak_reminders(self):
        """
        Send evening streak reminder notifications
        """
        try:
            logger.info("📧 Sending streak reminder notifications")
            
            # Find users who haven't checked in today
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            users_to_remind = self.db.query(UserStreak).filter(
                and_(
                    UserStreak.current_streak > 0,
                    UserStreak.last_checkin < today_start
                )
            ).all()
            
            notifications = []
            for user_streak in users_to_remind:
                notification = {
                    "user_id": user_streak.user_id,
                    "type": "streak_reminder",
                    "title": f"🔥 Keep your {user_streak.current_streak}-day streak alive!",
                    "body": "Check in now to maintain your streak. You have 4 hours left!",
                    "data": {
                        "current_streak": user_streak.current_streak,
                        "hours_remaining": 4,
                        "freeze_tokens": user_streak.freeze_tokens
                    }
                }
                notifications.append(notification)
            
            # Queue notifications (implementation depends on notification service)
            await self._queue_notifications(notifications)
            
            logger.info(f"✅ Sent {len(notifications)} streak reminders")
            
        except Exception as e:
            logger.error(f"Failed to send streak reminders: {e}")
    
    async def send_urgent_streak_reminders(self):
        """
        Send urgent last-hour streak reminders
        """
        try:
            logger.info("🚨 Sending urgent streak reminders")
            
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Find users with high streaks who haven't checked in
            urgent_users = self.db.query(UserStreak).filter(
                and_(
                    UserStreak.current_streak >= 7,  # Only for 7+ day streaks
                    UserStreak.last_checkin < today_start,
                    UserStreak.freeze_active == False
                )
            ).all()
            
            notifications = []
            for user_streak in urgent_users:
                # Calculate what they'll lose
                milestone_loss = self._calculate_milestone_loss(user_streak.current_streak)
                
                notification = {
                    "user_id": user_streak.user_id,
                    "type": "urgent_streak_reminder",
                    "title": f"⚠️ URGENT: {user_streak.current_streak}-day streak ending soon!",
                    "body": f"Only 1 hour left! Don't lose your progress{milestone_loss}",
                    "priority": "high",
                    "data": {
                        "current_streak": user_streak.current_streak,
                        "minutes_remaining": 60,
                        "can_use_freeze": user_streak.freeze_tokens > 0,
                        "milestone_at_risk": milestone_loss
                    }
                }
                notifications.append(notification)
            
            await self._queue_notifications(notifications)
            
            logger.info(f"✅ Sent {len(notifications)} urgent reminders")
            
        except Exception as e:
            logger.error(f"Failed to send urgent reminders: {e}")
    
    async def process_milestone_rewards(self):
        """
        Process and distribute milestone rewards
        """
        try:
            logger.info("🎁 Processing milestone rewards")
            
            # Find users who reached milestones
            milestone_days = [3, 7, 14, 21, 30, 50, 60, 75, 100, 150, 200, 365]
            
            rewards_given = 0
            for days in milestone_days:
                users_at_milestone = self.db.query(UserStreak).filter(
                    and_(
                        UserStreak.current_streak == days,
                        ~UserStreak.milestones_reached.contains([days])
                    )
                ).all()
                
                for user_streak in users_at_milestone:
                    # Process milestone reward
                    reward_result = await self.streak_system._process_milestone(
                        user_streak,
                        days
                    )
                    
                    if reward_result:
                        # Trigger bonus spin
                        spin_result = await self.rewards_engine.spin_reward_wheel(
                            user_streak.user_id,
                            "streak_milestone"
                        )
                        
                        # Send celebration notification
                        notification = {
                            "user_id": user_streak.user_id,
                            "type": "milestone_celebration",
                            "title": f"🎉 {days}-Day Streak Milestone!",
                            "body": f"Amazing! You've earned: {reward_result['milestone_name']}",
                            "data": {
                                "milestone": days,
                                "reward": reward_result,
                                "bonus_spin": spin_result
                            }
                        }
                        await self._queue_notifications([notification])
                        
                        rewards_given += 1
            
            self.db.commit()
            
            if rewards_given > 0:
                logger.info(f"✅ Processed {rewards_given} milestone rewards")
            
        except Exception as e:
            logger.error(f"Failed to process milestone rewards: {e}")
            self.db.rollback()
    
    async def cleanup_expired_data(self):
        """
        Clean up expired freeze tokens and old data
        """
        try:
            logger.info("🧹 Starting cleanup task")
            
            now = datetime.now(timezone.utc)
            
            # Expire freeze tokens
            expired_freezes = self.db.query(UserStreak).filter(
                and_(
                    UserStreak.freeze_active == True,
                    UserStreak.freeze_expires < now
                )
            ).all()
            
            for user_streak in expired_freezes:
                user_streak.freeze_active = False
                user_streak.freeze_expires = None
            
            # Clean up old activity records (keep last 90 days)
            cutoff_date = now - timedelta(days=90)
            deleted_activities = self.db.query(StreakActivity).filter(
                StreakActivity.activity_date < cutoff_date
            ).delete()
            
            self.db.commit()
            
            logger.info(f"✅ Cleanup completed. Expired freezes: {len(expired_freezes)}, Deleted activities: {deleted_activities}")
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            self.db.rollback()
    
    async def update_leaderboards(self):
        """
        Update cached leaderboard data
        """
        try:
            # This would typically update a Redis cache or similar
            # For now, just log the action
            logger.debug("📊 Updating leaderboards")
            
            # Get top streaks
            top_streaks = self.db.query(UserStreak).order_by(
                UserStreak.current_streak.desc()
            ).limit(100).all()
            
            # Get top total checkins
            top_checkins = self.db.query(UserStreak).order_by(
                UserStreak.total_checkins.desc()
            ).limit(100).all()
            
            # Would cache these results
            logger.debug(f"✅ Updated leaderboards with {len(top_streaks)} entries")
            
        except Exception as e:
            logger.error(f"Failed to update leaderboards: {e}")
    
    async def send_weekly_summaries(self):
        """
        Send weekly progress summaries to users
        """
        try:
            logger.info("📊 Sending weekly summaries")
            
            # Get all active users
            active_users = self.db.query(UserStreak).filter(
                UserStreak.current_streak > 0
            ).all()
            
            notifications = []
            for user_streak in active_users:
                # Calculate weekly stats
                week_start = datetime.now(timezone.utc) - timedelta(days=7)
                week_activities = self.db.query(StreakActivity).filter(
                    and_(
                        StreakActivity.user_id == user_streak.user_id,
                        StreakActivity.activity_date >= week_start
                    )
                ).all()
                
                total_points = sum(a.points_earned for a in week_activities)
                active_days = len(set(a.activity_date.date() for a in week_activities))
                
                notification = {
                    "user_id": user_streak.user_id,
                    "type": "weekly_summary",
                    "title": "📈 Your Weekly Progress Report",
                    "body": f"Streak: {user_streak.current_streak} days | Points: {total_points} | Active: {active_days}/7 days",
                    "data": {
                        "current_streak": user_streak.current_streak,
                        "weekly_points": total_points,
                        "active_days": active_days,
                        "longest_streak": user_streak.longest_streak
                    }
                }
                notifications.append(notification)
            
            await self._queue_notifications(notifications)
            
            logger.info(f"✅ Sent {len(notifications)} weekly summaries")
            
        except Exception as e:
            logger.error(f"Failed to send weekly summaries: {e}")
    
    def _calculate_milestone_loss(self, current_streak: int) -> str:
        """Calculate what milestone user will lose"""
        milestones = [3, 7, 14, 21, 30, 50, 60, 75, 100, 150, 200, 365]
        
        for milestone in reversed(milestones):
            if current_streak >= milestone:
                return f" and your {milestone}-day milestone!"
        
        return ""
    
    async def _queue_notifications(self, notifications: List[Dict[str, Any]]):
        """
        Queue notifications for sending
        This would integrate with your notification service
        """
        # Placeholder for notification service integration
        # Could use Firebase, OneSignal, or custom WebSocket notifications
        for notification in notifications:
            logger.debug(f"Queued notification for user {notification['user_id']}: {notification['title']}")
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("🚀 Gamification Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("🛑 Gamification Scheduler stopped")
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get list of scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

# Global scheduler instance
_scheduler_instance: Optional[GamificationScheduler] = None

def get_scheduler() -> GamificationScheduler:
    """Get or create scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = GamificationScheduler()
    return _scheduler_instance

def start_scheduler():
    """Start the gamification scheduler"""
    scheduler = get_scheduler()
    scheduler.start()

def stop_scheduler():
    """Stop the gamification scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()