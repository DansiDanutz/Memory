"""
FOMO (Fear of Missing Out) System
Implements urgency mechanics and time-limited opportunities
"""

import logging
import random
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from .database_models import (
    User, SessionLocal, FOMOAlert, AlertType, AlertPriority
)

logger = logging.getLogger(__name__)

class FOMOSystem:
    """
    Manages FOMO triggers, urgency mechanics, and time-sensitive notifications
    """
    
    # FOMO configuration
    FLASH_SALE_PROBABILITY = 0.05  # 5% chance per hour
    FRIEND_ACTIVITY_THRESHOLD = 3  # Show when 3+ friends do something
    EXPIRY_WARNING_TIMES = [120, 60, 30, 10, 5]  # Minutes before expiry
    
    # FOMO templates
    FOMO_TEMPLATES = {
        "expiring_reward": {
            "title": "⏰ Reward Expiring Soon!",
            "message": "Your {reward_name} expires in {time_left}. Claim it now or lose it forever!",
            "priority": AlertPriority.HIGH,
            "action_text": "Claim Now",
            "icon": "gift",
            "color": "#ff6b6b"
        },
        "flash_sale": {
            "title": "⚡ Flash Bonus Active!",
            "message": "Get {bonus}% extra XP for the next {duration}! Don't miss out!",
            "priority": AlertPriority.CRITICAL,
            "action_text": "Get Bonus",
            "icon": "zap",
            "color": "#ffd93d"
        },
        "limited_slots": {
            "title": "🔥 Limited Slots Available!",
            "message": "Only {slots_left} {item_name} slots remaining today!",
            "priority": AlertPriority.MEDIUM,
            "action_text": "Reserve Now",
            "icon": "fire",
            "color": "#ff9800"
        },
        "friend_activity": {
            "title": "👥 Friends Are Active!",
            "message": "{friend_count} friends just {action}. Join them!",
            "priority": AlertPriority.LOW,
            "action_text": "See Activity",
            "icon": "users",
            "color": "#4caf50"
        },
        "last_chance": {
            "title": "🚨 Last Chance Alert!",
            "message": "Final {time_left} to {action}! This won't come back!",
            "priority": AlertPriority.CRITICAL,
            "action_text": "Act Now",
            "icon": "alert-triangle",
            "color": "#f44336"
        },
        "streak_risk": {
            "title": "🔥 Streak at Risk!",
            "message": "Your {streak_days} day streak ends in {time_left}!",
            "priority": AlertPriority.HIGH,
            "action_text": "Save Streak",
            "icon": "flame",
            "color": "#ff5722"
        },
        "exclusive_offer": {
            "title": "💎 Exclusive Opportunity!",
            "message": "Special offer just for you: {offer_details}. Expires in {time_left}!",
            "priority": AlertPriority.HIGH,
            "action_text": "View Offer",
            "icon": "crown",
            "color": "#9c27b0"
        },
        "competition_update": {
            "title": "📊 Leaderboard Update!",
            "message": "You're about to be overtaken! {competitor_name} is only {points_behind} points behind!",
            "priority": AlertPriority.MEDIUM,
            "action_text": "Defend Position",
            "icon": "trending-up",
            "color": "#2196f3"
        },
        "quest_expiring": {
            "title": "⏳ Quest Expiring!",
            "message": "'{quest_name}' expires in {time_left}. Complete it for {reward}!",
            "priority": AlertPriority.HIGH,
            "action_text": "Complete Quest",
            "icon": "target",
            "color": "#ff9800"
        },
        "milestone_close": {
            "title": "🎯 So Close!",
            "message": "Just {items_needed} more {action} to unlock {reward}!",
            "priority": AlertPriority.MEDIUM,
            "action_text": "Finish Now",
            "icon": "award",
            "color": "#4caf50"
        }
    }
    
    # Flash sale configurations
    FLASH_SALES = [
        {
            "name": "Double XP Hour",
            "bonus_type": "xp_multiplier",
            "bonus_value": 2.0,
            "duration_minutes": 60,
            "rarity": "common"
        },
        {
            "name": "Triple Points Rush",
            "bonus_type": "points_multiplier", 
            "bonus_value": 3.0,
            "duration_minutes": 30,
            "rarity": "rare"
        },
        {
            "name": "Voice Avatar Discount",
            "bonus_type": "voice_discount",
            "bonus_value": 0.5,  # 50% off
            "duration_minutes": 45,
            "rarity": "uncommon"
        },
        {
            "name": "Invitation Frenzy",
            "bonus_type": "invitation_bonus",
            "bonus_value": 5,  # 5x rewards
            "duration_minutes": 20,
            "rarity": "epic"
        }
    ]
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize FOMO system"""
        self.db = db_session or SessionLocal()
        self.active_sales = {}  # Track active flash sales per user
        logger.info("✅ FOMO System initialized")
    
    async def check_expiring_rewards(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Check for rewards/quests expiring soon and create alerts
        """
        try:
            alerts = []
            now = datetime.utcnow()
            
            # Check for expiring quests (example - integrate with quest system)
            # This would normally query the Quest table
            for warning_minutes in self.EXPIRY_WARNING_TIMES:
                warning_time = now + timedelta(minutes=warning_minutes)
                
                # Create expiry warning if needed
                if warning_minutes <= 30:  # Only alert for last 30 minutes
                    alert = await self._create_fomo_alert(
                        user_id=user_id,
                        template="quest_expiring",
                        data={
                            "quest_name": "Daily Memory Challenge",
                            "time_left": f"{warning_minutes} minutes",
                            "reward": "100 XP"
                        },
                        expires_at=warning_time
                    )
                    if alert:
                        alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking expiring rewards: {e}")
            return []
    
    async def trigger_flash_sale(
        self, 
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Randomly trigger a flash sale for a user or globally
        """
        try:
            # Check probability
            if random.random() > self.FLASH_SALE_PROBABILITY:
                return None
            
            # Check if user already has an active flash sale
            if user_id and user_id in self.active_sales:
                if self.active_sales[user_id]['expires_at'] > datetime.utcnow():
                    return None  # Already has active sale
            
            # Select random flash sale based on rarity
            sale = self._select_flash_sale()
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(minutes=sale['duration_minutes'])
            
            # Create flash sale record
            flash_sale_data = {
                "id": f"flash_{datetime.utcnow().timestamp()}",
                "name": sale['name'],
                "bonus_type": sale['bonus_type'],
                "bonus_value": sale['bonus_value'],
                "started_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "duration_minutes": sale['duration_minutes']
            }
            
            # Store active sale
            if user_id:
                self.active_sales[user_id] = {
                    **flash_sale_data,
                    "expires_at": expires_at  # Keep datetime for comparison
                }
            
            # Create FOMO alert
            alert = await self._create_fomo_alert(
                user_id=user_id or "global",
                template="flash_sale",
                data={
                    "bonus": int((sale['bonus_value'] - 1) * 100) if sale['bonus_value'] > 1 else int((1 - sale['bonus_value']) * 100),
                    "duration": f"{sale['duration_minutes']} minutes"
                },
                expires_at=expires_at,
                metadata=flash_sale_data
            )
            
            logger.info(f"Triggered flash sale: {sale['name']} for user {user_id}")
            return flash_sale_data
            
        except Exception as e:
            logger.error(f"Error triggering flash sale: {e}")
            return None
    
    async def check_friend_activity(
        self, 
        user_id: str,
        action_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if friends are performing similar actions and create social proof alerts
        """
        try:
            # Get user's friends (simplified - would normally query relationships)
            # For now, simulate friend activity
            friend_activity_count = random.randint(0, 10)
            
            if friend_activity_count >= self.FRIEND_ACTIVITY_THRESHOLD:
                alert = await self._create_fomo_alert(
                    user_id=user_id,
                    template="friend_activity",
                    data={
                        "friend_count": friend_activity_count,
                        "action": self._format_action_type(action_type)
                    },
                    expires_at=datetime.utcnow() + timedelta(hours=1)
                )
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking friend activity: {e}")
            return None
    
    async def check_limited_slots(
        self,
        user_id: str,
        resource_type: str,
        slots_remaining: int,
        total_slots: int
    ) -> Optional[Dict[str, Any]]:
        """
        Create alerts for limited resource availability
        """
        try:
            # Only alert when slots are running low (less than 30% remaining)
            if slots_remaining > total_slots * 0.3:
                return None
            
            alert = await self._create_fomo_alert(
                user_id=user_id,
                template="limited_slots",
                data={
                    "slots_left": slots_remaining,
                    "item_name": self._format_resource_type(resource_type)
                },
                expires_at=datetime.utcnow() + timedelta(hours=2)
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Error checking limited slots: {e}")
            return None
    
    async def check_streak_risk(
        self,
        user_id: str,
        streak_days: int,
        hours_until_reset: float
    ) -> Optional[Dict[str, Any]]:
        """
        Alert users when their streak is at risk
        """
        try:
            # Only alert if streak is significant (5+ days) and time is running out
            if streak_days < 5 or hours_until_reset > 4:
                return None
            
            time_left = self._format_time_remaining(hours_until_reset * 60)
            
            alert = await self._create_fomo_alert(
                user_id=user_id,
                template="streak_risk",
                data={
                    "streak_days": streak_days,
                    "time_left": time_left
                },
                expires_at=datetime.utcnow() + timedelta(hours=hours_until_reset)
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Error checking streak risk: {e}")
            return None
    
    async def check_competition_status(
        self,
        user_id: str,
        user_rank: int,
        user_points: int
    ) -> Optional[Dict[str, Any]]:
        """
        Alert when user's leaderboard position is threatened
        """
        try:
            # Simulate competitor catching up
            if random.random() > 0.3:  # 30% chance
                return None
            
            competitor_points_behind = random.randint(10, 50)
            
            alert = await self._create_fomo_alert(
                user_id=user_id,
                template="competition_update",
                data={
                    "competitor_name": f"Player_{random.randint(100, 999)}",
                    "points_behind": competitor_points_behind
                },
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Error checking competition status: {e}")
            return None
    
    async def get_active_alerts(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all active FOMO alerts for a user
        """
        try:
            query = self.db.query(FOMOAlert).filter(
                FOMOAlert.user_id == user_id
            )
            
            if not include_expired:
                query = query.filter(
                    and_(
                        FOMOAlert.expires_at > datetime.utcnow(),
                        FOMOAlert.dismissed_at.is_(None)
                    )
                )
            
            alerts = query.order_by(
                desc(FOMOAlert.priority),
                FOMOAlert.expires_at
            ).all()
            
            return [self._alert_to_dict(alert) for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def dismiss_alert(
        self,
        user_id: str,
        alert_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Mark an alert as dismissed
        """
        try:
            alert = self.db.query(FOMOAlert).filter(
                and_(
                    FOMOAlert.id == alert_id,
                    FOMOAlert.user_id == user_id
                )
            ).first()
            
            if not alert:
                return False, {"error": "Alert not found"}
            
            alert.dismissed_at = datetime.utcnow()
            self.db.commit()
            
            return True, {"message": "Alert dismissed"}
            
        except Exception as e:
            logger.error(f"Error dismissing alert: {e}")
            self.db.rollback()
            return False, {"error": str(e)}
    
    async def get_flash_sale_status(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current flash sale status for a user
        """
        if user_id not in self.active_sales:
            return None
        
        sale = self.active_sales[user_id]
        if sale['expires_at'] <= datetime.utcnow():
            # Sale expired, remove it
            del self.active_sales[user_id]
            return None
        
        # Calculate time remaining
        time_left = sale['expires_at'] - datetime.utcnow()
        minutes_left = int(time_left.total_seconds() / 60)
        
        return {
            **{k: v for k, v in sale.items() if k != 'expires_at'},
            "time_remaining_minutes": minutes_left,
            "time_remaining_formatted": self._format_time_remaining(minutes_left)
        }
    
    async def _create_fomo_alert(
        self,
        user_id: str,
        template: str,
        data: Dict[str, Any],
        expires_at: datetime,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a FOMO alert from template
        """
        try:
            template_data = self.FOMO_TEMPLATES.get(template, {})
            
            # Format message with data
            message = template_data.get("message", "").format(**data)
            title = template_data.get("title", "Alert")
            
            alert = FOMOAlert(
                user_id=user_id,
                type=AlertType.FOMO,
                priority=template_data.get("priority", AlertPriority.MEDIUM),
                title=title,
                message=message,
                action_text=template_data.get("action_text"),
                action_url=f"/fomo/{template}",
                icon=template_data.get("icon"),
                color=template_data.get("color"),
                alert_metadata=metadata or {},
                expires_at=expires_at,
                created_at=datetime.utcnow()
            )
            
            self.db.add(alert)
            self.db.commit()
            
            return self._alert_to_dict(alert)
            
        except Exception as e:
            logger.error(f"Error creating FOMO alert: {e}")
            self.db.rollback()
            return None
    
    def _select_flash_sale(self) -> Dict[str, Any]:
        """
        Select a flash sale based on rarity weights
        """
        rarity_weights = {
            "common": 0.5,
            "uncommon": 0.3,
            "rare": 0.15,
            "epic": 0.05
        }
        
        # Filter sales by rarity and select
        sales_by_rarity = {}
        for sale in self.FLASH_SALES:
            rarity = sale.get('rarity', 'common')
            if rarity not in sales_by_rarity:
                sales_by_rarity[rarity] = []
            sales_by_rarity[rarity].append(sale)
        
        # Weighted random selection
        rand = random.random()
        cumulative = 0
        
        for rarity, weight in rarity_weights.items():
            cumulative += weight
            if rand <= cumulative and rarity in sales_by_rarity:
                return random.choice(sales_by_rarity[rarity])
        
        # Fallback to any sale
        return random.choice(self.FLASH_SALES)
    
    def _format_time_remaining(self, minutes: float) -> str:
        """
        Format time remaining in human-readable format
        """
        if minutes < 1:
            return "less than a minute"
        elif minutes < 60:
            return f"{int(minutes)} minute{'s' if minutes != 1 else ''}"
        else:
            hours = int(minutes / 60)
            remaining_minutes = int(minutes % 60)
            if remaining_minutes > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''}"
    
    def _format_action_type(self, action_type: str) -> str:
        """
        Format action type for display
        """
        action_formats = {
            "create_memory": "created memories",
            "send_invitation": "sent invitations",
            "use_voice": "used voice features",
            "complete_quest": "completed quests",
            "login": "logged in"
        }
        return action_formats.get(action_type, action_type.replace('_', ' '))
    
    def _format_resource_type(self, resource_type: str) -> str:
        """
        Format resource type for display
        """
        resource_formats = {
            "voice_avatar": "voice avatar",
            "contact_slot": "contact slot",
            "invitation": "invitation",
            "quest_slot": "quest slot"
        }
        return resource_formats.get(resource_type, resource_type.replace('_', ' '))
    
    def _alert_to_dict(self, alert: FOMOAlert) -> Dict[str, Any]:
        """
        Convert alert object to dictionary
        """
        return {
            "id": alert.id,
            "type": alert.type.value if alert.type else "fomo",
            "priority": alert.priority.value if alert.priority else "medium",
            "title": alert.title,
            "message": alert.message,
            "action_text": alert.action_text,
            "action_url": alert.action_url,
            "icon": alert.icon,
            "color": alert.color,
            "metadata": alert.alert_metadata or {},
            "expires_at": alert.expires_at.isoformat() if alert.expires_at else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "dismissed_at": alert.dismissed_at.isoformat() if alert.dismissed_at else None
        }