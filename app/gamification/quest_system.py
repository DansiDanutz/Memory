"""
Quest System for Gamification
Implements time-limited quests and challenges to drive engagement
"""

import logging
import random
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .database_models import (
    User, SessionLocal, Quest, UserQuestProgress,
    QuestType, QuestDifficulty, QuestStatus
)
from .rewards_engine import RewardsEngine

logger = logging.getLogger(__name__)

class QuestSystem:
    """
    Manages quests, challenges, and time-limited events
    """
    
    # Quest configuration
    DAILY_QUEST_COUNT = 3
    WEEKLY_QUEST_COUNT = 2
    FLASH_QUEST_PROBABILITY = 0.15  # 15% chance per hour
    
    # Quest templates by type
    QUEST_TEMPLATES = {
        QuestType.DAILY: [
            {
                "name": "Memory Maker",
                "description": "Create {target} new memories today",
                "requirement_type": "create_memory",
                "base_target": 3,
                "base_reward_xp": 50,
                "base_reward_points": 30,
                "difficulty": QuestDifficulty.EASY
            },
            {
                "name": "Social Connector",
                "description": "Send {target} invitation(s) to friends",
                "requirement_type": "send_invitation",
                "base_target": 2,
                "base_reward_xp": 75,
                "base_reward_points": 50,
                "difficulty": QuestDifficulty.MEDIUM
            },
            {
                "name": "Voice Explorer",
                "description": "Use voice features {target} time(s)",
                "requirement_type": "use_voice",
                "base_target": 2,
                "base_reward_xp": 100,
                "base_reward_points": 60,
                "difficulty": QuestDifficulty.MEDIUM
            },
            {
                "name": "Conversation Starter",
                "description": "Have {target} chat conversation(s)",
                "requirement_type": "chat_conversation",
                "base_target": 5,
                "base_reward_xp": 40,
                "base_reward_points": 25,
                "difficulty": QuestDifficulty.EASY
            },
            {
                "name": "Login Streak",
                "description": "Maintain your daily login streak",
                "requirement_type": "daily_login",
                "base_target": 1,
                "base_reward_xp": 30,
                "base_reward_points": 20,
                "difficulty": QuestDifficulty.EASY
            }
        ],
        QuestType.WEEKLY: [
            {
                "name": "Memory Marathon",
                "description": "Create {target} memories this week",
                "requirement_type": "create_memory",
                "base_target": 20,
                "base_reward_xp": 500,
                "base_reward_points": 300,
                "difficulty": QuestDifficulty.HARD
            },
            {
                "name": "Voice Avatar Creator",
                "description": "Create {target} voice avatar(s)",
                "requirement_type": "create_voice_avatar",
                "base_target": 1,
                "base_reward_xp": 750,
                "base_reward_points": 500,
                "difficulty": QuestDifficulty.HARD
            },
            {
                "name": "Network Builder",
                "description": "Get {target} invitations accepted",
                "requirement_type": "invitations_accepted",
                "base_target": 3,
                "base_reward_xp": 600,
                "base_reward_points": 400,
                "difficulty": QuestDifficulty.HARD
            },
            {
                "name": "Perfect Week",
                "description": "Login every day this week",
                "requirement_type": "weekly_login_streak",
                "base_target": 7,
                "base_reward_xp": 400,
                "base_reward_points": 250,
                "difficulty": QuestDifficulty.MEDIUM
            }
        ],
        QuestType.FLASH: [
            {
                "name": "Speed Memory",
                "description": "Create {target} memory in the next hour",
                "requirement_type": "create_memory",
                "base_target": 1,
                "base_reward_xp": 150,
                "base_reward_points": 100,
                "difficulty": QuestDifficulty.MEDIUM,
                "duration_hours": 1
            },
            {
                "name": "Quick Connect",
                "description": "Send {target} invitations in 30 minutes",
                "requirement_type": "send_invitation",
                "base_target": 3,
                "base_reward_xp": 200,
                "base_reward_points": 150,
                "difficulty": QuestDifficulty.HARD,
                "duration_hours": 0.5
            },
            {
                "name": "Voice Sprint",
                "description": "Record {target} voice samples in 2 hours",
                "requirement_type": "record_voice",
                "base_target": 3,
                "base_reward_xp": 250,
                "base_reward_points": 175,
                "difficulty": QuestDifficulty.HARD,
                "duration_hours": 2
            },
            {
                "name": "Lightning Round",
                "description": "Complete any {target} actions in 15 minutes",
                "requirement_type": "any_action",
                "base_target": 5,
                "base_reward_xp": 100,
                "base_reward_points": 75,
                "difficulty": QuestDifficulty.MEDIUM,
                "duration_hours": 0.25
            }
        ],
        QuestType.EVENT: [
            {
                "name": "Weekend Warrior",
                "description": "Login on Saturday and Sunday",
                "requirement_type": "weekend_login",
                "base_target": 2,
                "base_reward_xp": 300,
                "base_reward_points": 200,
                "difficulty": QuestDifficulty.EASY
            },
            {
                "name": "Holiday Special",
                "description": "Create {target} holiday-themed memories",
                "requirement_type": "themed_memory",
                "base_target": 5,
                "base_reward_xp": 1000,
                "base_reward_points": 750,
                "difficulty": QuestDifficulty.HARD
            }
        ]
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize quest system"""
        self.db = db_session or SessionLocal()
        self.rewards_engine = RewardsEngine(self.db)
        logger.info("✅ Quest System initialized")
    
    async def generate_daily_quests(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Generate daily quests for a user
        """
        try:
            # Check if user already has daily quests for today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            existing_dailies = self.db.query(Quest).filter(
                and_(
                    Quest.user_id == user_id,
                    Quest.type == QuestType.DAILY,
                    Quest.created_at >= today_start,
                    Quest.created_at < today_end
                )
            ).all()
            
            if len(existing_dailies) >= self.DAILY_QUEST_COUNT:
                return [self._quest_to_dict(q) for q in existing_dailies]
            
            # Generate new daily quests
            templates = random.sample(
                self.QUEST_TEMPLATES[QuestType.DAILY],
                min(self.DAILY_QUEST_COUNT, len(self.QUEST_TEMPLATES[QuestType.DAILY]))
            )
            
            quests = []
            for template in templates:
                quest = self._create_quest_from_template(
                    user_id, 
                    template, 
                    QuestType.DAILY,
                    expires_at=today_end
                )
                quests.append(quest)
                
            self.db.commit()
            
            logger.info(f"Generated {len(quests)} daily quests for user {user_id}")
            return [self._quest_to_dict(q) for q in quests]
            
        except Exception as e:
            logger.error(f"Error generating daily quests: {e}")
            self.db.rollback()
            return []
    
    async def generate_weekly_quests(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Generate weekly challenges for a user
        """
        try:
            # Check if user already has weekly quests for this week
            today = datetime.utcnow()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            
            existing_weeklies = self.db.query(Quest).filter(
                and_(
                    Quest.user_id == user_id,
                    Quest.type == QuestType.WEEKLY,
                    Quest.created_at >= week_start,
                    Quest.created_at < week_end
                )
            ).all()
            
            if len(existing_weeklies) >= self.WEEKLY_QUEST_COUNT:
                return [self._quest_to_dict(q) for q in existing_weeklies]
            
            # Generate new weekly quests
            templates = random.sample(
                self.QUEST_TEMPLATES[QuestType.WEEKLY],
                min(self.WEEKLY_QUEST_COUNT, len(self.QUEST_TEMPLATES[QuestType.WEEKLY]))
            )
            
            quests = []
            for template in templates:
                quest = self._create_quest_from_template(
                    user_id,
                    template,
                    QuestType.WEEKLY,
                    expires_at=week_end
                )
                quests.append(quest)
                
            self.db.commit()
            
            logger.info(f"Generated {len(quests)} weekly quests for user {user_id}")
            return [self._quest_to_dict(q) for q in quests]
            
        except Exception as e:
            logger.error(f"Error generating weekly quests: {e}")
            self.db.rollback()
            return []
    
    async def trigger_flash_quest(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Randomly trigger a flash quest for a user
        """
        try:
            # Check probability
            if random.random() > self.FLASH_QUEST_PROBABILITY:
                return None
            
            # Check if user already has an active flash quest
            active_flash = self.db.query(Quest).filter(
                and_(
                    Quest.user_id == user_id,
                    Quest.type == QuestType.FLASH,
                    Quest.status == QuestStatus.ACTIVE,
                    Quest.expires_at > datetime.utcnow()
                )
            ).first()
            
            if active_flash:
                return None  # User already has an active flash quest
            
            # Select random flash quest template
            template = random.choice(self.QUEST_TEMPLATES[QuestType.FLASH])
            
            # Calculate expiration based on template duration
            duration_hours = template.get('duration_hours', 1)
            expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
            
            # Create flash quest
            quest = self._create_quest_from_template(
                user_id,
                template,
                QuestType.FLASH,
                expires_at=expires_at,
                is_flash=True
            )
            
            self.db.commit()
            
            logger.info(f"Triggered flash quest for user {user_id}: {quest.name}")
            return self._quest_to_dict(quest)
            
        except Exception as e:
            logger.error(f"Error triggering flash quest: {e}")
            self.db.rollback()
            return None
    
    async def update_quest_progress(
        self, 
        user_id: str,
        action_type: str,
        amount: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Update progress for all relevant quests when user performs an action
        """
        try:
            completed_quests = []
            
            # Get all active quests for user
            active_quests = self.db.query(Quest).filter(
                and_(
                    Quest.user_id == user_id,
                    Quest.status == QuestStatus.ACTIVE,
                    Quest.expires_at > datetime.utcnow()
                )
            ).all()
            
            for quest in active_quests:
                # Check if action matches quest requirement
                if self._action_matches_requirement(action_type, quest.requirement_type):
                    # Get or create progress record
                    progress = self.db.query(UserQuestProgress).filter(
                        and_(
                            UserQuestProgress.user_id == user_id,
                            UserQuestProgress.quest_id == quest.id
                        )
                    ).first()
                    
                    if not progress:
                        progress = UserQuestProgress(
                            user_id=user_id,
                            quest_id=quest.id,
                            progress=0
                        )
                        self.db.add(progress)
                    
                    # Update progress
                    progress.progress = min(progress.progress + amount, quest.target)
                    progress.last_update = datetime.utcnow()
                    
                    # Check if quest is completed
                    if progress.progress >= quest.target and not progress.completed_at:
                        progress.completed_at = datetime.utcnow()
                        quest.status = QuestStatus.COMPLETED
                        completed_quests.append(self._quest_to_dict(quest))
                        
                        logger.info(f"Quest completed: {quest.name} for user {user_id}")
            
            self.db.commit()
            
            return completed_quests
            
        except Exception as e:
            logger.error(f"Error updating quest progress: {e}")
            self.db.rollback()
            return []
    
    async def claim_quest_rewards(
        self, 
        user_id: str,
        quest_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Claim rewards for a completed quest
        """
        try:
            # Get quest
            quest = self.db.query(Quest).filter(
                and_(
                    Quest.id == quest_id,
                    Quest.user_id == user_id,
                    Quest.status == QuestStatus.COMPLETED
                )
            ).first()
            
            if not quest:
                return False, {"error": "Quest not found or not completed"}
            
            # Check if already claimed
            progress = self.db.query(UserQuestProgress).filter(
                and_(
                    UserQuestProgress.user_id == user_id,
                    UserQuestProgress.quest_id == quest_id
                )
            ).first()
            
            if progress and progress.claimed_at:
                return False, {"error": "Rewards already claimed"}
            
            # Get user
            user = self.db.query(User).filter_by(id=user_id).first()
            if not user:
                return False, {"error": "User not found"}
            
            # Award rewards
            rewards = quest.rewards or {}
            if rewards.get('xp', 0) > 0:
                user.points += rewards['xp']
            
            if rewards.get('points', 0) > 0:
                # Add points logic here
                pass
            
            # Bonus rewards for flash quests
            bonus_multiplier = 1.5 if quest.is_flash else 1.0
            actual_xp = int(rewards.get('xp', 0) * bonus_multiplier)
            
            # Mark as claimed
            quest.status = QuestStatus.CLAIMED
            if progress:
                progress.claimed_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Rewards claimed for quest {quest.name} by user {user_id}")
            
            return True, {
                "quest": quest.name,
                "rewards": {
                    "xp": actual_xp,
                    "points": rewards.get('points', 0),
                    "bonus_multiplier": bonus_multiplier
                }
            }
            
        except Exception as e:
            logger.error(f"Error claiming quest rewards: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    async def get_active_quests(self, user_id: str) -> Dict[str, List[Dict]]:
        """
        Get all active quests for a user, organized by type
        """
        try:
            quests = {
                "daily": [],
                "weekly": [],
                "flash": [],
                "event": []
            }
            
            # Get all active quests
            active_quests = self.db.query(Quest).filter(
                and_(
                    Quest.user_id == user_id,
                    Quest.status.in_([QuestStatus.ACTIVE, QuestStatus.COMPLETED]),
                    Quest.expires_at > datetime.utcnow()
                )
            ).all()
            
            # Get progress for all quests
            quest_ids = [q.id for q in active_quests]
            progress_records = self.db.query(UserQuestProgress).filter(
                and_(
                    UserQuestProgress.user_id == user_id,
                    UserQuestProgress.quest_id.in_(quest_ids)
                )
            ).all()
            
            progress_map = {p.quest_id: p for p in progress_records}
            
            # Organize by type
            for quest in active_quests:
                quest_data = self._quest_to_dict(quest)
                
                # Add progress info
                progress = progress_map.get(quest.id)
                if progress:
                    quest_data['current_progress'] = progress.progress
                    quest_data['completed'] = progress.completed_at is not None
                    quest_data['claimed'] = progress.claimed_at is not None
                else:
                    quest_data['current_progress'] = 0
                    quest_data['completed'] = False
                    quest_data['claimed'] = False
                
                # Add to appropriate category
                if quest.type == QuestType.DAILY:
                    quests['daily'].append(quest_data)
                elif quest.type == QuestType.WEEKLY:
                    quests['weekly'].append(quest_data)
                elif quest.type == QuestType.FLASH:
                    quests['flash'].append(quest_data)
                elif quest.type == QuestType.EVENT:
                    quests['event'].append(quest_data)
            
            return quests
            
        except Exception as e:
            logger.error(f"Error getting active quests: {e}")
            return {"daily": [], "weekly": [], "flash": [], "event": []}
    
    def _create_quest_from_template(
        self,
        user_id: str,
        template: Dict[str, Any],
        quest_type: QuestType,
        expires_at: datetime,
        is_flash: bool = False
    ) -> Quest:
        """
        Create a quest from a template
        """
        # Adjust target based on user level (could be more sophisticated)
        user = self.db.query(User).filter_by(id=user_id).first()
        level_multiplier = 1 + (user.level - 1) * 0.1 if user else 1
        
        target = int(template['base_target'] * level_multiplier)
        
        quest = Quest(
            user_id=user_id,
            name=template['name'],
            description=template['description'].format(target=target),
            type=quest_type,
            difficulty=template['difficulty'],
            requirement_type=template['requirement_type'],
            target=target,
            rewards={
                'xp': int(template['base_reward_xp'] * level_multiplier),
                'points': int(template['base_reward_points'] * level_multiplier)
            },
            expires_at=expires_at,
            is_flash=is_flash,
            status=QuestStatus.ACTIVE
        )
        
        self.db.add(quest)
        return quest
    
    def _action_matches_requirement(self, action_type: str, requirement_type: str) -> bool:
        """
        Check if an action type matches a quest requirement
        """
        # Direct match
        if action_type == requirement_type:
            return True
        
        # Special cases
        if requirement_type == "any_action":
            return True
        
        if requirement_type == "daily_login" and action_type == "login":
            return True
        
        if requirement_type == "weekly_login_streak" and action_type == "login":
            return True
        
        if requirement_type == "weekend_login" and action_type == "login":
            # Check if it's weekend
            return datetime.utcnow().weekday() >= 5
        
        return False
    
    def _quest_to_dict(self, quest: Quest) -> Dict[str, Any]:
        """
        Convert quest object to dictionary
        """
        return {
            "id": quest.id,
            "name": quest.name,
            "description": quest.description,
            "type": quest.type.value if quest.type else "daily",
            "difficulty": quest.difficulty.value if quest.difficulty else "easy",
            "requirement_type": quest.requirement_type,
            "target": quest.target,
            "rewards": quest.rewards,
            "expires_at": quest.expires_at.isoformat() if quest.expires_at else None,
            "is_flash": quest.is_flash,
            "status": quest.status.value if quest.status else "active",
            "created_at": quest.created_at.isoformat() if quest.created_at else None
        }