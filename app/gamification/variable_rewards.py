"""
Variable Rewards Engine
Implements slot machine mechanics with weighted probabilities for engagement
"""

import logging
import random
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from .database_models import Base, SessionLocal, RewardHistory
from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Boolean

logger = logging.getLogger(__name__)

class UserRewardState(Base):
    """Track user's reward state for pity system and cooldowns"""
    __tablename__ = "user_reward_state"
    
    user_id = Column(String, primary_key=True)
    spins_since_rare = Column(Integer, default=0, nullable=False)
    spins_since_epic = Column(Integer, default=0, nullable=False)
    spins_since_legendary = Column(Integer, default=0, nullable=False)
    total_spins = Column(Integer, default=0, nullable=False)
    last_daily_spin = Column(DateTime)
    last_free_spin = Column(DateTime)
    daily_spins_used = Column(Integer, default=0, nullable=False)
    luck_modifier = Column(Float, default=1.0, nullable=False)
    
    # Statistics
    total_rewards_earned = Column(Integer, default=0, nullable=False)
    best_reward_rarity = Column(String)
    favorite_reward_type = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class VariableRewardsEngine:
    """
    Implements variable ratio reinforcement schedule with slot machine mechanics
    """
    
    # Reward rarity tiers
    RARITY_WEIGHTS = {
        "common": 50,      # 50%
        "uncommon": 30,    # 30%
        "rare": 15,        # 15%
        "epic": 4,         # 4%
        "legendary": 1     # 1%
    }
    
    # Pity system thresholds
    PITY_THRESHOLDS = {
        "rare": 10,        # Guaranteed rare after 10 spins without
        "epic": 25,        # Guaranteed epic after 25 spins without
        "legendary": 100   # Guaranteed legendary after 100 spins without
    }
    
    # Reward pool configuration
    REWARD_POOL = {
        "common": [
            {"type": "xp", "value": {"amount": 10}, "weight": 40, "icon": "⭐"},
            {"type": "xp", "value": {"amount": 25}, "weight": 30, "icon": "✨"},
            {"type": "coins", "value": {"amount": 5}, "weight": 30, "icon": "🪙"}
        ],
        "uncommon": [
            {"type": "xp", "value": {"amount": 50}, "weight": 30, "icon": "🌟"},
            {"type": "coins", "value": {"amount": 20}, "weight": 30, "icon": "💰"},
            {"type": "freeze_token", "value": {"amount": 1}, "weight": 40, "icon": "❄️"}
        ],
        "rare": [
            {"type": "xp", "value": {"amount": 100}, "weight": 25, "icon": "💫"},
            {"type": "contact_slot", "value": {"amount": 1}, "weight": 35, "icon": "📇"},
            {"type": "freeze_token", "value": {"amount": 2}, "weight": 25, "icon": "🧊"},
            {"type": "voice_credit", "value": {"amount": 1}, "weight": 15, "icon": "🎤"}
        ],
        "epic": [
            {"type": "contact_slot", "value": {"amount": 2}, "weight": 30, "icon": "📚"},
            {"type": "voice_credit", "value": {"amount": 2}, "weight": 30, "icon": "🎙️"},
            {"type": "badge", "value": {"id": "lucky_spinner"}, "weight": 20, "icon": "🎖️"},
            {"type": "xp_multiplier", "value": {"duration": 3600, "multiplier": 2}, "weight": 20, "icon": "⚡"}
        ],
        "legendary": [
            {"type": "contact_slot", "value": {"amount": 5}, "weight": 25, "icon": "👥"},
            {"type": "voice_credit", "value": {"amount": 5}, "weight": 25, "icon": "🔊"},
            {"type": "premium_time", "value": {"days": 7}, "weight": 25, "icon": "👑"},
            {"type": "legendary_badge", "value": {"id": "fortune_master"}, "weight": 25, "icon": "🔮"}
        ]
    }
    
    # Slot machine symbols
    SLOT_SYMBOLS = {
        "common": ["🍒", "🍋", "🍊", "🍇", "🔔"],
        "uncommon": ["💎", "🎰", "7️⃣"],
        "rare": ["⭐", "🌟", "💫"],
        "epic": ["👑", "🏆"],
        "legendary": ["🔮", "🌈"]
    }
    
    # Trigger event configurations
    TRIGGER_CONFIGS = {
        "daily_login": {"cooldown_hours": 24, "guaranteed_spin": True},
        "memory_created": {"cooldown_hours": 1, "chance": 0.3},
        "invitation_sent": {"cooldown_hours": 2, "chance": 0.5},
        "invitation_accepted": {"cooldown_hours": 0, "guaranteed_spin": True},
        "streak_milestone": {"cooldown_hours": 0, "guaranteed_spin": True},
        "achievement_unlocked": {"cooldown_hours": 0, "chance": 0.7}
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize variable rewards engine"""
        self.db = db_session or SessionLocal()
        logger.info("✅ Variable Rewards Engine initialized")
    
    async def trigger_reward(
        self,
        user_id: str,
        event_type: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Trigger a potential reward based on event
        """
        try:
            # Check if event should trigger a reward
            config = self.TRIGGER_CONFIGS.get(event_type, {})
            
            # Check cooldown
            if not self._check_cooldown(user_id, event_type, config.get("cooldown_hours", 0)):
                return {
                    "success": False,
                    "reason": "cooldown_active",
                    "message": "Reward on cooldown for this event"
                }
            
            # Check probability
            if not config.get("guaranteed_spin", False):
                if random.random() > config.get("chance", 0.5):
                    return {
                        "success": False,
                        "reason": "no_luck",
                        "message": "No reward this time"
                    }
            
            # Trigger the spin
            return await self.spin_reward_wheel(user_id, event_type)
            
        except Exception as e:
            logger.error(f"Failed to trigger reward: {e}")
            return {"success": False, "error": str(e)}
    
    async def spin_reward_wheel(
        self,
        user_id: str,
        trigger_event: str = "manual_spin"
    ) -> Dict[str, Any]:
        """
        Spin the reward wheel with slot machine mechanics
        """
        try:
            # Get or create user state
            user_state = self.db.query(UserRewardState).filter_by(user_id=user_id).first()
            if not user_state:
                user_state = UserRewardState(user_id=user_id)
                self.db.add(user_state)
            
            # Increment counters
            user_state.total_spins += 1
            user_state.spins_since_rare += 1
            user_state.spins_since_epic += 1
            user_state.spins_since_legendary += 1
            
            # Determine rarity with pity system
            rarity = self._calculate_rarity_with_pity(user_state)
            
            # Generate slot machine result
            slot_result = self._generate_slot_result(rarity)
            
            # Select reward from pool
            reward = self._select_reward_from_pool(rarity)
            
            # Apply reward multipliers
            final_reward = self._apply_multipliers(reward, user_state, slot_result)
            
            # Reset pity counters based on rarity
            was_pity = False
            if rarity == "rare":
                was_pity = user_state.spins_since_rare >= self.PITY_THRESHOLDS["rare"]
                user_state.spins_since_rare = 0
            elif rarity == "epic":
                was_pity = user_state.spins_since_epic >= self.PITY_THRESHOLDS["epic"]
                user_state.spins_since_epic = 0
                user_state.spins_since_rare = 0
            elif rarity == "legendary":
                was_pity = user_state.spins_since_legendary >= self.PITY_THRESHOLDS["legendary"]
                user_state.spins_since_legendary = 0
                user_state.spins_since_epic = 0
                user_state.spins_since_rare = 0
            
            # Update best reward
            if not user_state.best_reward_rarity or self._compare_rarity(rarity, user_state.best_reward_rarity):
                user_state.best_reward_rarity = rarity
            
            # Record reward
            reward_record = RewardHistory(
                user_id=user_id,
                reward_type=final_reward["type"],
                reward_value=final_reward["value"],
                trigger_event=trigger_event,
                rarity=rarity,
                spin_result=slot_result,
                was_pity=was_pity,
                multiplier=final_reward.get("multiplier", 1.0)
            )
            self.db.add(reward_record)
            
            # Update last spin time
            if trigger_event == "daily_login":
                user_state.last_daily_spin = datetime.now(timezone.utc)
            
            user_state.total_rewards_earned += 1
            
            self.db.commit()
            
            # Check for near miss
            near_miss = self._check_near_miss(slot_result)
            
            return {
                "success": True,
                "reward": final_reward,
                "rarity": rarity,
                "slot_result": slot_result,
                "was_pity": was_pity,
                "near_miss": near_miss,
                "spins_until_pity": self._calculate_spins_until_pity(user_state),
                "total_spins": user_state.total_spins,
                "animation_data": {
                    "duration": self._get_animation_duration(rarity),
                    "effects": self._get_animation_effects(rarity)
                }
            }
            
        except Exception as e:
            logger.error(f"Spin failed for user {user_id}: {e}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _check_cooldown(self, user_id: str, event_type: str, cooldown_hours: int) -> bool:
        """Check if cooldown has passed for event type"""
        if cooldown_hours == 0:
            return True
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)
        recent_reward = self.db.query(RewardHistory).filter(
            and_(
                RewardHistory.user_id == user_id,
                RewardHistory.trigger_event == event_type,
                RewardHistory.timestamp > cutoff_time
            )
        ).first()
        
        return recent_reward is None
    
    def _calculate_rarity_with_pity(self, user_state: UserRewardState) -> str:
        """Calculate rarity considering pity system"""
        # Check pity thresholds
        if user_state.spins_since_legendary >= self.PITY_THRESHOLDS["legendary"]:
            return "legendary"
        if user_state.spins_since_epic >= self.PITY_THRESHOLDS["epic"]:
            return "epic"
        if user_state.spins_since_rare >= self.PITY_THRESHOLDS["rare"]:
            return "rare"
        
        # Calculate with luck modifier and soft pity
        weights = self.RARITY_WEIGHTS.copy()
        
        # Soft pity: gradually increase rare chances
        if user_state.spins_since_rare > 5:
            bonus = (user_state.spins_since_rare - 5) * 2
            weights["rare"] += bonus
            weights["common"] = max(10, weights["common"] - bonus)
        
        if user_state.spins_since_epic > 15:
            bonus = (user_state.spins_since_epic - 15) * 1
            weights["epic"] += bonus
            weights["common"] = max(10, weights["common"] - bonus)
        
        # Apply luck modifier
        if user_state.luck_modifier > 1.0:
            for rarity in ["rare", "epic", "legendary"]:
                weights[rarity] = int(weights[rarity] * user_state.luck_modifier)
        
        # Weighted random selection
        total = sum(weights.values())
        roll = random.randint(1, total)
        current = 0
        
        for rarity, weight in weights.items():
            current += weight
            if roll <= current:
                return rarity
        
        return "common"
    
    def _generate_slot_result(self, rarity: str) -> List[str]:
        """Generate slot machine symbols based on rarity"""
        reels = []
        
        if rarity == "legendary":
            # All matching legendary symbols
            symbol = random.choice(self.SLOT_SYMBOLS["legendary"])
            reels = [symbol, symbol, symbol]
        elif rarity == "epic":
            # Two matching epic symbols
            symbol = random.choice(self.SLOT_SYMBOLS["epic"])
            other = random.choice(self.SLOT_SYMBOLS["rare"] + self.SLOT_SYMBOLS["uncommon"])
            reels = [symbol, symbol, other]
            random.shuffle(reels)
        elif rarity == "rare":
            # Two matching rare symbols
            symbol = random.choice(self.SLOT_SYMBOLS["rare"])
            other = random.choice(self.SLOT_SYMBOLS["uncommon"] + self.SLOT_SYMBOLS["common"])
            reels = [symbol, symbol, other]
            random.shuffle(reels)
        elif rarity == "uncommon":
            # Two matching uncommon symbols
            symbol = random.choice(self.SLOT_SYMBOLS["uncommon"])
            other = random.choice(self.SLOT_SYMBOLS["common"])
            reels = [symbol, symbol, other]
            random.shuffle(reels)
        else:
            # Random common symbols
            reels = [random.choice(self.SLOT_SYMBOLS["common"]) for _ in range(3)]
        
        return reels
    
    def _select_reward_from_pool(self, rarity: str) -> Dict[str, Any]:
        """Select a specific reward from the rarity pool"""
        pool = self.REWARD_POOL[rarity]
        weights = [item["weight"] for item in pool]
        selected = random.choices(pool, weights=weights, k=1)[0]
        return selected.copy()
    
    def _apply_multipliers(
        self,
        reward: Dict[str, Any],
        user_state: UserRewardState,
        slot_result: List[str]
    ) -> Dict[str, Any]:
        """Apply multipliers based on patterns and state"""
        multiplier = 1.0
        
        # Triple match bonus
        if len(set(slot_result)) == 1:
            multiplier *= 1.5
        
        # Lucky 7s
        if "7️⃣" in slot_result:
            count = slot_result.count("7️⃣")
            multiplier *= (1 + 0.25 * count)
        
        # Apply multiplier to value
        if reward["type"] in ["xp", "coins", "contact_slot", "voice_credit"]:
            if "amount" in reward["value"]:
                original = reward["value"]["amount"]
                reward["value"]["amount"] = int(original * multiplier)
                reward["multiplier"] = multiplier
        
        return reward
    
    def _check_near_miss(self, slot_result: List[str]) -> bool:
        """Check if result was a near miss (2 matching high-value symbols)"""
        high_value_symbols = (
            self.SLOT_SYMBOLS["rare"] + 
            self.SLOT_SYMBOLS["epic"] + 
            self.SLOT_SYMBOLS["legendary"]
        )
        
        for symbol in high_value_symbols:
            if slot_result.count(symbol) == 2:
                return True
        return False
    
    def _calculate_spins_until_pity(self, user_state: UserRewardState) -> Dict[str, int]:
        """Calculate remaining spins until each pity threshold"""
        return {
            "rare": max(0, self.PITY_THRESHOLDS["rare"] - user_state.spins_since_rare),
            "epic": max(0, self.PITY_THRESHOLDS["epic"] - user_state.spins_since_epic),
            "legendary": max(0, self.PITY_THRESHOLDS["legendary"] - user_state.spins_since_legendary)
        }
    
    def _compare_rarity(self, r1: str, r2: str) -> bool:
        """Compare if r1 is better than r2"""
        order = ["common", "uncommon", "rare", "epic", "legendary"]
        return order.index(r1) > order.index(r2)
    
    def _get_animation_duration(self, rarity: str) -> int:
        """Get animation duration in milliseconds"""
        durations = {
            "common": 1500,
            "uncommon": 2000,
            "rare": 2500,
            "epic": 3000,
            "legendary": 4000
        }
        return durations.get(rarity, 1500)
    
    def _get_animation_effects(self, rarity: str) -> List[str]:
        """Get animation effects to play"""
        effects = {
            "common": ["spin"],
            "uncommon": ["spin", "sparkle"],
            "rare": ["spin", "sparkle", "glow"],
            "epic": ["spin", "sparkle", "glow", "shake"],
            "legendary": ["spin", "sparkle", "glow", "shake", "rainbow", "confetti"]
        }
        return effects.get(rarity, ["spin"])
    
    async def get_reward_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's reward history"""
        try:
            # Get total count
            total = self.db.query(func.count(RewardHistory.id)).filter_by(
                user_id=user_id
            ).scalar()
            
            # Get rewards
            rewards = self.db.query(RewardHistory).filter_by(
                user_id=user_id
            ).order_by(
                RewardHistory.timestamp.desc()
            ).limit(limit).offset(offset).all()
            
            # Get user state
            user_state = self.db.query(UserRewardState).filter_by(user_id=user_id).first()
            
            # Format rewards
            history = []
            for reward in rewards:
                history.append({
                    "id": reward.id,
                    "type": reward.reward_type,
                    "value": reward.reward_value,
                    "rarity": reward.rarity,
                    "trigger_event": reward.trigger_event,
                    "timestamp": reward.timestamp.isoformat(),
                    "slot_result": reward.spin_result,
                    "was_pity": reward.was_pity,
                    "multiplier": reward.multiplier
                })
            
            # Calculate statistics
            stats = self._calculate_reward_stats(user_id)
            
            return {
                "success": True,
                "total": total,
                "history": history,
                "stats": stats,
                "user_state": {
                    "total_spins": user_state.total_spins if user_state else 0,
                    "best_reward": user_state.best_reward_rarity if user_state else None,
                    "spins_until_pity": self._calculate_spins_until_pity(user_state) if user_state else {}
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get reward history: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_reward_stats(self, user_id: str) -> Dict[str, Any]:
        """Calculate reward statistics for user"""
        try:
            # Get all rewards
            rewards = self.db.query(RewardHistory).filter_by(user_id=user_id).all()
            
            if not rewards:
                return {
                    "total_rewards": 0,
                    "rarity_breakdown": {},
                    "type_breakdown": {},
                    "lucky_streak": 0
                }
            
            # Rarity breakdown
            rarity_counts = {}
            type_counts = {}
            
            for reward in rewards:
                rarity_counts[reward.rarity] = rarity_counts.get(reward.rarity, 0) + 1
                type_counts[reward.reward_type] = type_counts.get(reward.reward_type, 0) + 1
            
            # Calculate lucky streak
            lucky_streak = 0
            current_streak = 0
            
            for reward in reversed(rewards):
                if reward.rarity in ["rare", "epic", "legendary"]:
                    current_streak += 1
                    lucky_streak = max(lucky_streak, current_streak)
                else:
                    current_streak = 0
            
            return {
                "total_rewards": len(rewards),
                "rarity_breakdown": rarity_counts,
                "type_breakdown": type_counts,
                "lucky_streak": lucky_streak,
                "average_rarity": self._calculate_average_rarity(rarity_counts)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate stats: {e}")
            return {}
    
    def _calculate_average_rarity(self, rarity_counts: Dict[str, int]) -> float:
        """Calculate average rarity score"""
        rarity_values = {
            "common": 1,
            "uncommon": 2,
            "rare": 3,
            "epic": 4,
            "legendary": 5
        }
        
        total_score = 0
        total_count = 0
        
        for rarity, count in rarity_counts.items():
            total_score += rarity_values.get(rarity, 1) * count
            total_count += count
        
        return total_score / total_count if total_count > 0 else 1.0