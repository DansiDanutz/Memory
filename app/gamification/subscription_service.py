"""
Subscription Management Service
Handles user plans, upgrades, and premium features
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session

from .database_models import (
    User, VoiceAvatar, SessionLocal
)

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    """Available subscription tiers"""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionService:
    """
    Manages user subscriptions and premium features
    """
    
    # Feature limits per tier
    TIER_LIMITS = {
        SubscriptionTier.FREE: {
            "voice_sample_collection": True,
            "voice_avatar_creation": True,
            "voice_avatar_preview": True,
            "voice_generation": False,  # Main restriction
            "max_voice_avatars": 1,
            "max_samples_per_avatar": 3,
            "daily_memory_limit": 10,
            "contact_slots": 3,
            "invitation_limit": 1
        },
        SubscriptionTier.PREMIUM: {
            "voice_sample_collection": True,
            "voice_avatar_creation": True,
            "voice_avatar_preview": True,
            "voice_generation": True,  # Full access
            "max_voice_avatars": 5,
            "max_samples_per_avatar": 10,
            "daily_memory_limit": 100,
            "contact_slots": 20,
            "invitation_limit": 10,
            "monthly_voice_minutes": 60,
            "priority_support": True
        },
        SubscriptionTier.ENTERPRISE: {
            "voice_sample_collection": True,
            "voice_avatar_creation": True,
            "voice_avatar_preview": True,
            "voice_generation": True,
            "max_voice_avatars": -1,  # Unlimited
            "max_samples_per_avatar": 25,
            "daily_memory_limit": -1,  # Unlimited
            "contact_slots": -1,  # Unlimited
            "invitation_limit": -1,  # Unlimited
            "monthly_voice_minutes": -1,  # Unlimited
            "priority_support": True,
            "custom_branding": True,
            "api_access": True
        }
    }
    
    # Pricing (for display purposes)
    PRICING = {
        SubscriptionTier.FREE: {
            "price": 0,
            "currency": "USD",
            "billing_period": None
        },
        SubscriptionTier.PREMIUM: {
            "price": 9.99,
            "currency": "USD",
            "billing_period": "monthly",
            "features": [
                "✨ Unlock Voice Avatar Generation",
                "🎯 5 Custom Voice Avatars",
                "💬 100 Daily Memories",
                "👥 20 Contact Slots",
                "⚡ Priority Support",
                "🎵 60 Minutes Voice Generation/Month"
            ]
        },
        SubscriptionTier.ENTERPRISE: {
            "price": "Contact Sales",
            "currency": "USD",
            "billing_period": "custom",
            "features": [
                "∞ Unlimited Voice Avatars",
                "∞ Unlimited Memories",
                "∞ Unlimited Contacts",
                "🏢 Custom Branding",
                "🔑 API Access",
                "🎯 Dedicated Support"
            ]
        }
    }
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize subscription service"""
        self.db = db_session or SessionLocal()
        logger.info("✅ Subscription Service initialized")
    
    def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """Get user's current subscription tier"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return SubscriptionTier.FREE
        
        # For now, use is_premium field to determine tier
        # In production, this would check subscription status
        if user.is_premium:
            return SubscriptionTier.PREMIUM
        return SubscriptionTier.FREE
    
    def get_tier_limits(self, tier: SubscriptionTier) -> Dict[str, Any]:
        """Get feature limits for a tier"""
        return self.TIER_LIMITS.get(tier, self.TIER_LIMITS[SubscriptionTier.FREE])
    
    def can_use_feature(self, user_id: str, feature: str) -> Tuple[bool, str]:
        """
        Check if user can use a specific feature
        
        Returns:
            (can_use, message)
        """
        tier = self.get_user_tier(user_id)
        limits = self.get_tier_limits(tier)
        
        # Check boolean features
        if feature in limits:
            if isinstance(limits[feature], bool):
                if limits[feature]:
                    return True, "Feature available"
                else:
                    return False, f"🔒 This feature requires {SubscriptionTier.PREMIUM.value} subscription"
        
        # Feature not found
        return True, "Feature not restricted"
    
    def check_voice_generation_access(self, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user can generate voice (main premium gate)
        
        Returns:
            (has_access, details)
        """
        tier = self.get_user_tier(user_id)
        limits = self.get_tier_limits(tier)
        
        if tier == SubscriptionTier.FREE:
            return False, {
                "message": "🔒 Voice generation is a premium feature",
                "current_tier": tier.value,
                "upgrade_benefits": self.PRICING[SubscriptionTier.PREMIUM]["features"],
                "upgrade_cta": "Upgrade to Premium to unlock your voice avatar!",
                "teaser_available": True
            }
        
        # Check usage limits for premium users
        if tier == SubscriptionTier.PREMIUM:
            # In production, check actual usage vs limits
            remaining_minutes = limits.get("monthly_voice_minutes", 60)
            return True, {
                "message": "✅ Voice generation available",
                "current_tier": tier.value,
                "remaining_minutes": remaining_minutes
            }
        
        # Enterprise has unlimited access
        return True, {
            "message": "✅ Unlimited voice generation",
            "current_tier": tier.value
        }
    
    def get_upgrade_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Get user's upgrade eligibility and benefits"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "eligible": False,
                "message": "User not found"
            }
        
        current_tier = self.get_user_tier(user_id)
        
        # Check if user has created voice avatars (creates urgency)
        voice_avatars = self.db.query(VoiceAvatar).filter(
            VoiceAvatar.owner_id == user_id
        ).all()
        
        has_locked_avatars = len(voice_avatars) > 0 and current_tier == SubscriptionTier.FREE
        
        # Calculate potential discount based on activity
        discount = 0
        discount_reason = None
        
        if user.total_invites_accepted >= 3:
            discount = 20
            discount_reason = "Network Builder Discount"
        elif user.trust_score >= 75:
            discount = 15
            discount_reason = "Trusted User Discount"
        elif len(voice_avatars) > 0:
            discount = 10
            discount_reason = "Early Adopter Discount"
        
        # Special limited-time offers
        special_offer = None
        offer_expires = None
        
        if has_locked_avatars:
            special_offer = "🎁 Your voice avatar is ready! Unlock it now with 30% off your first month!"
            discount = max(discount, 30)
            offer_expires = (datetime.utcnow() + timedelta(hours=48)).isoformat()
        
        return {
            "eligible": current_tier != SubscriptionTier.ENTERPRISE,
            "current_tier": current_tier.value,
            "has_locked_avatars": has_locked_avatars,
            "locked_avatar_count": len(voice_avatars),
            "upgrade_options": [
                {
                    "tier": SubscriptionTier.PREMIUM.value,
                    "price": self.PRICING[SubscriptionTier.PREMIUM]["price"],
                    "discount": discount,
                    "discount_reason": discount_reason,
                    "final_price": self.PRICING[SubscriptionTier.PREMIUM]["price"] * (1 - discount/100),
                    "features": self.PRICING[SubscriptionTier.PREMIUM]["features"]
                }
            ],
            "special_offer": special_offer,
            "offer_expires": offer_expires,
            "urgency_message": "⏰ Limited time offer!" if special_offer else None
        }
    
    async def simulate_upgrade(self, user_id: str, tier: str = "premium") -> Dict[str, Any]:
        """
        Simulate user upgrade (for demo purposes)
        In production, this would handle actual payment processing
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "message": "User not found"
            }
        
        # Update user to premium
        user.is_premium = True
        self.db.commit()
        
        # Get all user's voice avatars and mark them as active
        voice_avatars = self.db.query(VoiceAvatar).filter(
            VoiceAvatar.owner_id == user_id
        ).all()
        
        unlocked_avatars = []
        for avatar in voice_avatars:
            avatar.is_locked = False
            unlocked_avatars.append({
                "id": avatar.id,
                "name": avatar.name,
                "status": "unlocked"
            })
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "🎉 Welcome to Premium!",
            "tier": tier,
            "unlocked_features": [
                "voice_generation",
                "extended_limits",
                "priority_support"
            ],
            "unlocked_avatars": unlocked_avatars,
            "next_steps": [
                "Try generating speech with your voice avatar",
                "Invite more friends to earn rewards",
                "Explore advanced memory features"
            ]
        }
    
    def generate_voice_preview(self, user_id: str, avatar_id: int) -> Dict[str, Any]:
        """
        Generate a preview/teaser for locked voice avatar
        Shows what they're missing to create FOMO
        """
        avatar = self.db.query(VoiceAvatar).filter(
            VoiceAvatar.id == avatar_id,
            VoiceAvatar.owner_id == user_id
        ).first()
        
        if not avatar:
            return {
                "success": False,
                "message": "Avatar not found"
            }
        
        tier = self.get_user_tier(user_id)
        
        if tier != SubscriptionTier.FREE:
            return {
                "success": True,
                "message": "Full access available",
                "preview_text": None
            }
        
        # Generate teaser content
        preview_messages = [
            f"🎙️ Your voice avatar '{avatar.name}' is ready to speak!",
            f"🔊 Imagine hearing your personalized AI speak in your own voice...",
            f"✨ '{avatar.name}' can bring your memories to life with your unique voice",
            f"🎯 Your voice clone is 98% ready - just one upgrade away!"
        ]
        
        return {
            "success": True,
            "avatar_name": avatar.name,
            "preview_message": preview_messages[avatar.id % len(preview_messages)],
            "locked": True,
            "upgrade_prompt": {
                "title": "🔓 Unlock Your Voice Avatar",
                "message": "Your personalized voice is ready! Upgrade now to:",
                "benefits": [
                    "Generate unlimited speech with your voice",
                    "Create up to 5 unique voice avatars",
                    "Access premium memory features",
                    "Get priority support"
                ],
                "cta": "Unlock Now",
                "urgency": "🔥 Special offer expires in 48 hours!"
            }
        }
    
    def get_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive subscription status for user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        tier = self.get_user_tier(user_id)
        limits = self.get_tier_limits(tier)
        
        # Count current usage
        voice_avatars = self.db.query(VoiceAvatar).filter(
            VoiceAvatar.owner_id == user_id
        ).all()
        
        return {
            "user_id": user_id,
            "tier": tier.value,
            "is_premium": user.is_premium,
            "limits": limits,
            "current_usage": {
                "voice_avatars": len(voice_avatars),
                "contact_slots": user.used_contact_slots,
                "invitations_sent": user.total_invites_sent
            },
            "available_upgrades": [
                SubscriptionTier.PREMIUM.value
            ] if tier == SubscriptionTier.FREE else [],
            "features": {
                "voice_generation": tier != SubscriptionTier.FREE,
                "voice_preview": True,
                "voice_collection": True,
                "premium_memories": tier != SubscriptionTier.FREE
            }
        }

# Singleton instance
_subscription_service: Optional[SubscriptionService] = None

def get_subscription_service() -> SubscriptionService:
    """Get or create subscription service singleton"""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service