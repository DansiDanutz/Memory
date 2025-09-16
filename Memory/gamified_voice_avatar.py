"""
Gamified Voice Avatar System with Invitation Rewards
=====================================================
Free Tier: No voice avatar
5 Invites: Free Coqui TTS avatar
Paid Tier: Premium ElevenLabs avatar

This system uses voice avatars as an advertisement/growth mechanism.
"""

import os
import json
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import redis
from dotenv import load_dotenv

load_dotenv()


class UserTier(Enum):
    """User subscription tiers with voice avatar access"""
    FREE = "free"  # No voice avatar
    INVITED = "invited"  # Free Coqui avatar (earned through invites)
    PREMIUM = "premium"  # Premium ElevenLabs avatar (paid)


class VoiceService(Enum):
    """Available voice services"""
    NONE = "none"  # No voice service
    COQUI = "coqui"  # Free/open-source TTS
    ELEVENLABS = "elevenlabs"  # Premium voice cloning


@dataclass
class InvitationRecord:
    """Track user invitations"""
    inviter_id: str
    invited_id: str
    invited_at: datetime
    status: str  # pending, accepted, rewarded
    app_installed: bool = False
    reward_claimed: bool = False


@dataclass
class UserVoiceProfile:
    """User's voice avatar profile"""
    user_id: str
    tier: UserTier
    voice_service: VoiceService
    voice_id: Optional[str] = None
    avatar_created_at: Optional[datetime] = None
    invitations_sent: int = 0
    successful_invites: int = 0
    invitation_records: List[InvitationRecord] = field(default_factory=list)
    upgrade_date: Optional[datetime] = None
    is_paying: bool = False


class GamifiedVoiceAvatarSystem:
    """
    Main system for gamified voice avatar access
    Uses invitations as growth mechanism
    """

    # Configuration
    INVITES_REQUIRED_FOR_FREE_AVATAR = 5
    INVITATION_EXPIRY_DAYS = 30

    def __init__(self):
        # Initialize Redis for tracking
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            print("[OK] Redis connected for invitation tracking")
        except:
            self.redis_client = None
            print("[WARNING] Redis not available, using in-memory tracking")

        # In-memory fallback
        self.user_profiles: Dict[str, UserVoiceProfile] = {}
        self.invitation_codes: Dict[str, str] = {}  # code -> inviter_id

        # Initialize voice services based on tier
        self._init_voice_services()

    def _init_voice_services(self):
        """Initialize voice services"""
        self.voice_services = {}

        # Coqui TTS for invited users
        try:
            from voice_services.coqui_service import CoquiService
            self.voice_services[VoiceService.COQUI] = CoquiService()
            print("[OK] Coqui TTS initialized for invited users")
        except ImportError:
            print("[ERROR] Coqui TTS not available")

        # ElevenLabs for premium users
        if os.getenv("ELEVENLABS_API_KEY"):
            from voice_services.elevenlabs_service import ElevenLabsService
            self.voice_services[VoiceService.ELEVENLABS] = ElevenLabsService()
            print("[OK] ElevenLabs initialized for premium users")
        else:
            print("[WARNING] ElevenLabs API key not configured")

    async def register_user(self, user_id: str, invitation_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Register a new user with optional invitation code

        Args:
            user_id: Unique user identifier
            invitation_code: Optional invitation code from another user

        Returns:
            Registration result with user profile
        """
        # Check if user already exists
        if user_id in self.user_profiles:
            return {
                "success": False,
                "error": "User already registered",
                "profile": self._serialize_profile(self.user_profiles[user_id])
            }

        # Create new user profile (FREE tier by default)
        profile = UserVoiceProfile(
            user_id=user_id,
            tier=UserTier.FREE,
            voice_service=VoiceService.NONE
        )

        # Process invitation if provided
        if invitation_code:
            invitation_result = await self._process_invitation(user_id, invitation_code)
            if invitation_result["success"]:
                profile.invitation_records.append(invitation_result["record"])

        # Store profile
        self.user_profiles[user_id] = profile
        self._save_profile_to_db(profile)

        return {
            "success": True,
            "profile": self._serialize_profile(profile),
            "message": self._get_welcome_message(profile),
            "next_steps": self._get_next_steps(profile)
        }

    async def generate_invitation_code(self, user_id: str) -> Dict[str, Any]:
        """
        Generate unique invitation code for user

        Args:
            user_id: User generating the invitation

        Returns:
            Invitation code and sharing message
        """
        # Verify user exists
        profile = self.user_profiles.get(user_id)
        if not profile:
            return {
                "success": False,
                "error": "User not found"
            }

        # Generate unique code
        timestamp = datetime.now().timestamp()
        raw_code = f"{user_id}:{timestamp}"
        invitation_code = hashlib.md5(raw_code.encode()).hexdigest()[:8].upper()

        # Store code mapping
        self.invitation_codes[invitation_code] = user_id
        if self.redis_client:
            self.redis_client.setex(
                f"invite:{invitation_code}",
                self.INVITATION_EXPIRY_DAYS * 86400,
                user_id
            )

        # Generate sharing message
        sharing_message = self._generate_sharing_message(invitation_code, profile)

        return {
            "success": True,
            "invitation_code": invitation_code,
            "sharing_message": sharing_message,
            "expires_in_days": self.INVITATION_EXPIRY_DAYS,
            "current_invites": profile.successful_invites,
            "invites_needed": max(0, self.INVITES_REQUIRED_FOR_FREE_AVATAR - profile.successful_invites)
        }

    async def _process_invitation(self, invited_id: str, invitation_code: str) -> Dict[str, Any]:
        """
        Process an invitation code when new user joins

        Args:
            invited_id: New user who was invited
            invitation_code: Code used to join

        Returns:
            Invitation processing result
        """
        # Validate invitation code
        inviter_id = self._get_inviter_from_code(invitation_code)
        if not inviter_id:
            return {
                "success": False,
                "error": "Invalid or expired invitation code"
            }

        # Get inviter profile
        inviter_profile = self.user_profiles.get(inviter_id)
        if not inviter_profile:
            return {
                "success": False,
                "error": "Inviter not found"
            }

        # Create invitation record
        invitation = InvitationRecord(
            inviter_id=inviter_id,
            invited_id=invited_id,
            invited_at=datetime.now(),
            status="accepted",
            app_installed=True
        )

        # Update inviter's profile
        inviter_profile.invitations_sent += 1
        inviter_profile.successful_invites += 1
        inviter_profile.invitation_records.append(invitation)

        # Check if inviter earned free avatar
        reward_result = await self._check_and_apply_invitation_reward(inviter_profile)

        # Notify inviter
        if reward_result["reward_earned"]:
            await self._notify_user_reward_earned(inviter_id, reward_result)

        return {
            "success": True,
            "record": invitation,
            "inviter_rewarded": reward_result["reward_earned"]
        }

    async def _check_and_apply_invitation_reward(self, profile: UserVoiceProfile) -> Dict[str, Any]:
        """
        Check if user has earned free avatar through invitations

        Args:
            profile: User profile to check

        Returns:
            Reward application result
        """
        # Check if already has avatar or is premium
        if profile.tier in [UserTier.INVITED, UserTier.PREMIUM]:
            return {
                "reward_earned": False,
                "reason": "User already has voice avatar access"
            }

        # Check if reached invitation threshold
        if profile.successful_invites >= self.INVITES_REQUIRED_FOR_FREE_AVATAR:
            # Upgrade to INVITED tier
            profile.tier = UserTier.INVITED
            profile.voice_service = VoiceService.COQUI

            # Create free Coqui avatar
            if VoiceService.COQUI in self.voice_services:
                # Avatar creation will happen when user provides voice samples
                pass

            self._save_profile_to_db(profile)

            return {
                "reward_earned": True,
                "tier_upgraded": UserTier.INVITED,
                "voice_service": VoiceService.COQUI,
                "message": f"Congratulations! You've unlocked your free voice avatar by inviting {self.INVITES_REQUIRED_FOR_FREE_AVATAR} friends!"
            }

        return {
            "reward_earned": False,
            "invites_remaining": self.INVITES_REQUIRED_FOR_FREE_AVATAR - profile.successful_invites
        }

    async def upgrade_to_premium(self, user_id: str, payment_verified: bool = True) -> Dict[str, Any]:
        """
        Upgrade user to premium tier with ElevenLabs avatar

        Args:
            user_id: User to upgrade
            payment_verified: Whether payment has been verified

        Returns:
            Upgrade result
        """
        profile = self.user_profiles.get(user_id)
        if not profile:
            return {
                "success": False,
                "error": "User not found"
            }

        if not payment_verified:
            return {
                "success": False,
                "error": "Payment verification required"
            }

        # Upgrade to premium
        old_tier = profile.tier
        profile.tier = UserTier.PREMIUM
        profile.voice_service = VoiceService.ELEVENLABS
        profile.is_paying = True
        profile.upgrade_date = datetime.now()

        # Handle voice avatar migration
        migration_result = await self._migrate_voice_avatar(profile, old_tier)

        self._save_profile_to_db(profile)

        return {
            "success": True,
            "message": "Upgraded to Premium with ElevenLabs voice avatar!",
            "old_tier": old_tier.value,
            "new_tier": UserTier.PREMIUM.value,
            "voice_service": VoiceService.ELEVENLABS.value,
            "migration": migration_result,
            "benefits": self._get_premium_benefits()
        }

    async def create_voice_avatar(
        self,
        user_id: str,
        audio_samples: List[str]
    ) -> Dict[str, Any]:
        """
        Create voice avatar based on user's tier

        Args:
            user_id: User creating avatar
            audio_samples: Voice samples for cloning

        Returns:
            Avatar creation result
        """
        profile = self.user_profiles.get(user_id)
        if not profile:
            return {
                "success": False,
                "error": "User not found"
            }

        # Check tier-based access
        if profile.tier == UserTier.FREE:
            return {
                "success": False,
                "error": "Voice avatars not available for free tier",
                "suggestion": f"Invite {self.INVITES_REQUIRED_FOR_FREE_AVATAR} friends to unlock your free voice avatar!",
                "current_invites": profile.successful_invites,
                "action_required": "generate_invitation_code"
            }

        # Get appropriate voice service
        voice_service = self.voice_services.get(profile.voice_service)
        if not voice_service:
            return {
                "success": False,
                "error": f"Voice service {profile.voice_service.value} not available"
            }

        # Validate samples based on tier
        validation_result = await self._validate_samples_for_tier(
            audio_samples,
            profile.tier
        )
        if not validation_result["valid"]:
            return validation_result

        # Create avatar with appropriate service
        try:
            if profile.tier == UserTier.INVITED:
                # Free Coqui avatar
                result = await voice_service.create_basic_avatar(
                    user_id,
                    audio_samples[0]  # Coqui typically needs one sample
                )
            elif profile.tier == UserTier.PREMIUM:
                # Premium ElevenLabs avatar
                result = await voice_service.create_professional_avatar(
                    user_id,
                    audio_samples  # ElevenLabs can use multiple samples
                )

            if result.get("success"):
                profile.voice_id = result["voice_id"]
                profile.avatar_created_at = datetime.now()
                self._save_profile_to_db(profile)

                return {
                    "success": True,
                    "voice_id": result["voice_id"],
                    "service": profile.voice_service.value,
                    "quality": self._get_quality_for_tier(profile.tier),
                    "message": self._get_avatar_success_message(profile.tier)
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create avatar: {str(e)}"
            }

    async def generate_speech(
        self,
        text: str,
        user_id: str,
        emotion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate speech using user's voice avatar

        Args:
            text: Text to convert to speech
            user_id: User requesting speech
            emotion: Optional emotion parameter (premium only)

        Returns:
            Speech generation result or upgrade prompt
        """
        profile = self.user_profiles.get(user_id)
        if not profile:
            return {
                "success": False,
                "error": "User not found"
            }

        # Check if user has voice avatar
        if profile.tier == UserTier.FREE:
            return {
                "success": False,
                "error": "No voice avatar available",
                "message": "Voice synthesis requires a voice avatar",
                "call_to_action": {
                    "primary": f"Invite {self.INVITES_REQUIRED_FOR_FREE_AVATAR} friends for free voice avatar",
                    "secondary": "Upgrade to Premium for ElevenLabs quality"
                }
            }

        if not profile.voice_id:
            return {
                "success": False,
                "error": "Voice avatar not created yet",
                "action_required": "create_voice_avatar"
            }

        # Get voice service
        voice_service = self.voice_services.get(profile.voice_service)
        if not voice_service:
            return {
                "success": False,
                "error": "Voice service unavailable"
            }

        # Generate speech based on tier
        try:
            if profile.tier == UserTier.INVITED:
                # Basic Coqui TTS
                result = await voice_service.synthesize_basic(
                    text,
                    profile.voice_id
                )
            elif profile.tier == UserTier.PREMIUM:
                # Premium ElevenLabs with emotions
                result = await voice_service.synthesize_advanced(
                    text,
                    profile.voice_id,
                    emotion=emotion
                )

            if result.get("success"):
                # Track usage
                self._track_usage(user_id, profile.tier, len(text))

                return {
                    **result,
                    "tier": profile.tier.value,
                    "quality": self._get_quality_for_tier(profile.tier)
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Speech generation failed: {str(e)}"
            }

    def get_invitation_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's invitation progress toward free avatar

        Args:
            user_id: User to check

        Returns:
            Invitation progress details
        """
        profile = self.user_profiles.get(user_id)
        if not profile:
            return {
                "success": False,
                "error": "User not found"
            }

        if profile.tier != UserTier.FREE:
            return {
                "success": True,
                "message": "You already have voice avatar access!",
                "tier": profile.tier.value,
                "voice_service": profile.voice_service.value
            }

        invites_needed = self.INVITES_REQUIRED_FOR_FREE_AVATAR - profile.successful_invites
        progress_percentage = (profile.successful_invites / self.INVITES_REQUIRED_FOR_FREE_AVATAR) * 100

        return {
            "success": True,
            "current_invites": profile.successful_invites,
            "invites_needed": invites_needed,
            "total_required": self.INVITES_REQUIRED_FOR_FREE_AVATAR,
            "progress_percentage": progress_percentage,
            "invitation_history": [
                {
                    "invited_user": inv.invited_id,
                    "date": inv.invited_at.isoformat(),
                    "status": inv.status
                }
                for inv in profile.invitation_records
            ],
            "motivational_message": self._get_motivational_message(invites_needed)
        }

    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get invitation leaderboard for gamification

        Args:
            limit: Number of top users to return

        Returns:
            Leaderboard data
        """
        # Sort users by successful invites
        sorted_users = sorted(
            self.user_profiles.values(),
            key=lambda p: p.successful_invites,
            reverse=True
        )[:limit]

        leaderboard = []
        for rank, profile in enumerate(sorted_users, 1):
            leaderboard.append({
                "rank": rank,
                "user_id": self._anonymize_user_id(profile.user_id),
                "invites": profile.successful_invites,
                "tier": profile.tier.value,
                "badge": self._get_badge_for_invites(profile.successful_invites)
            })

        return leaderboard

    # Helper Methods

    def _get_inviter_from_code(self, code: str) -> Optional[str]:
        """Get inviter ID from invitation code"""
        if self.redis_client:
            return self.redis_client.get(f"invite:{code}")
        return self.invitation_codes.get(code)

    def _generate_sharing_message(self, code: str, profile: UserVoiceProfile) -> str:
        """Generate invitation sharing message"""
        invites_needed = max(0, self.INVITES_REQUIRED_FOR_FREE_AVATAR - profile.successful_invites)

        if invites_needed > 0:
            return (
                f"Join me on Memory Bot! Create your AI voice avatar and never forget anything again. "
                f"Use my invite code: {code} "
                f"(I need {invites_needed} more friends to unlock my free voice avatar!)"
            )
        else:
            return (
                f"Join me on Memory Bot! I've unlocked my AI voice avatar - it sounds exactly like me! "
                f"Use my invite code: {code} and start building your perfect memory assistant."
            )

    def _get_welcome_message(self, profile: UserVoiceProfile) -> str:
        """Get tier-appropriate welcome message"""
        if profile.tier == UserTier.FREE:
            return (
                "Welcome to Memory Bot! Start building your memory assistant. "
                f"Invite {self.INVITES_REQUIRED_FOR_FREE_AVATAR} friends to unlock your free voice avatar!"
            )
        elif profile.tier == UserTier.INVITED:
            return "Welcome! You've earned a free voice avatar through invitations!"
        else:
            return "Welcome to Memory Bot Premium! Your ElevenLabs voice avatar awaits."

    def _get_next_steps(self, profile: UserVoiceProfile) -> List[str]:
        """Get next steps for user based on tier"""
        if profile.tier == UserTier.FREE:
            return [
                "Record your first memory",
                "Generate your invitation code",
                f"Share with {self.INVITES_REQUIRED_FOR_FREE_AVATAR} friends to unlock voice avatar",
                "Or upgrade to Premium for instant ElevenLabs access"
            ]
        elif profile.tier == UserTier.INVITED:
            return [
                "Record voice samples for your avatar",
                "Start using voice commands",
                "Consider upgrading for ElevenLabs quality"
            ]
        else:
            return [
                "Create your ElevenLabs voice avatar",
                "Enable voice responses",
                "Explore premium features"
            ]

    def _get_premium_benefits(self) -> List[str]:
        """Get list of premium benefits"""
        return [
            "ElevenLabs ultra-realistic voice cloning",
            "Emotion control in speech synthesis",
            "Priority processing",
            "Unlimited voice generations",
            "Advanced voice customization",
            "Multi-language support"
        ]

    def _get_quality_for_tier(self, tier: UserTier) -> str:
        """Get quality description for tier"""
        quality_map = {
            UserTier.FREE: "No voice",
            UserTier.INVITED: "Good quality (Coqui TTS)",
            UserTier.PREMIUM: "Ultra-realistic (ElevenLabs)"
        }
        return quality_map.get(tier, "Unknown")

    def _get_avatar_success_message(self, tier: UserTier) -> str:
        """Get success message for avatar creation"""
        if tier == UserTier.INVITED:
            return "Your free voice avatar is ready! It's good quality and completely free thanks to your invitations."
        elif tier == UserTier.PREMIUM:
            return "Your premium ElevenLabs voice avatar is ready! Experience ultra-realistic voice synthesis."
        return "Voice avatar created successfully!"

    def _get_motivational_message(self, invites_needed: int) -> str:
        """Get motivational message based on progress"""
        if invites_needed == self.INVITES_REQUIRED_FOR_FREE_AVATAR:
            return "Start inviting friends to unlock your voice avatar!"
        elif invites_needed == 1:
            return "Just 1 more friend and you'll have your voice avatar!"
        elif invites_needed <= 2:
            return f"Almost there! Just {invites_needed} more friends!"
        else:
            return f"Keep going! {invites_needed} more invites to your voice avatar."

    def _get_badge_for_invites(self, invite_count: int) -> str:
        """Get badge based on invitation count"""
        if invite_count >= 50:
            return "Ambassador"
        elif invite_count >= 25:
            return "Influencer"
        elif invite_count >= 10:
            return "Connector"
        elif invite_count >= 5:
            return "Friend"
        else:
            return "Starter"

    def _anonymize_user_id(self, user_id: str) -> str:
        """Anonymize user ID for leaderboard"""
        if len(user_id) > 8:
            return f"{user_id[:4]}****"
        return "User****"

    async def _validate_samples_for_tier(
        self,
        samples: List[str],
        tier: UserTier
    ) -> Dict[str, Any]:
        """Validate audio samples based on tier requirements"""
        if tier == UserTier.INVITED:
            # Coqui requirements
            if len(samples) < 1:
                return {
                    "valid": False,
                    "error": "At least 1 voice sample required"
                }
            # Add more validation as needed
        elif tier == UserTier.PREMIUM:
            # ElevenLabs requirements
            if len(samples) < 1:
                return {
                    "valid": False,
                    "error": "At least 1 voice sample required for ElevenLabs"
                }
            # Could check duration, quality, etc.

        return {"valid": True}

    async def _migrate_voice_avatar(
        self,
        profile: UserVoiceProfile,
        old_tier: UserTier
    ) -> Dict[str, Any]:
        """Migrate voice avatar when upgrading tiers"""
        if old_tier == UserTier.INVITED and profile.voice_id:
            # User had Coqui avatar, now gets ElevenLabs
            return {
                "migrated": True,
                "from": "Coqui TTS",
                "to": "ElevenLabs",
                "action": "Please record new samples for best quality"
            }
        return {"migrated": False}

    async def _notify_user_reward_earned(
        self,
        user_id: str,
        reward_result: Dict[str, Any]
    ):
        """Send notification when user earns reward"""
        # In production, send WhatsApp/email notification
        notification = {
            "user_id": user_id,
            "type": "reward_earned",
            "message": reward_result.get("message"),
            "timestamp": datetime.now().isoformat()
        }
        print(f"[NOTIFICATION] {json.dumps(notification)}")

    def _track_usage(self, user_id: str, tier: UserTier, text_length: int):
        """Track usage for analytics"""
        usage = {
            "user_id": user_id,
            "tier": tier.value,
            "text_length": text_length,
            "timestamp": datetime.now().isoformat()
        }
        # In production, send to analytics
        print(f"[USAGE] {json.dumps(usage)}")

    def _serialize_profile(self, profile: UserVoiceProfile) -> Dict[str, Any]:
        """Serialize profile for API response"""
        return {
            "user_id": profile.user_id,
            "tier": profile.tier.value,
            "voice_service": profile.voice_service.value,
            "voice_id": profile.voice_id,
            "invitations_sent": profile.invitations_sent,
            "successful_invites": profile.successful_invites,
            "has_avatar": profile.voice_id is not None,
            "is_paying": profile.is_paying
        }

    def _save_profile_to_db(self, profile: UserVoiceProfile):
        """Save profile to database"""
        # In production, save to PostgreSQL
        if self.redis_client:
            self.redis_client.set(
                f"profile:{profile.user_id}",
                json.dumps(self._serialize_profile(profile))
            )

    def _load_profile_from_db(self, user_id: str) -> Optional[UserVoiceProfile]:
        """Load profile from database"""
        # In production, load from PostgreSQL
        if self.redis_client:
            data = self.redis_client.get(f"profile:{user_id}")
            if data:
                # Deserialize and return
                pass
        return None


# Demo and Testing
async def demo():
    """Demonstrate the gamified voice avatar system"""

    print("=" * 70)
    print("GAMIFIED VOICE AVATAR SYSTEM DEMO")
    print("=" * 70)

    system = GamifiedVoiceAvatarSystem()

    # Scenario 1: New free user
    print("\n1. New user registration (FREE tier)...")
    result = await system.register_user("alice_123")
    print(f"Result: {json.dumps(result, indent=2)}")

    # Scenario 2: Generate invitation code
    print("\n2. Alice generates invitation code...")
    invite_result = await system.generate_invitation_code("alice_123")
    print(f"Invitation code: {invite_result['invitation_code']}")
    print(f"Sharing message: {invite_result['sharing_message']}")

    # Scenario 3: Friends join with Alice's code
    print("\n3. Friends joining with Alice's code...")
    friends = ["bob", "charlie", "diana", "eve", "frank"]
    for friend in friends:
        await system.register_user(friend, invite_result['invitation_code'])
        print(f"  - {friend} joined!")

    # Check Alice's progress
    print("\n4. Checking Alice's invitation progress...")
    progress = system.get_invitation_progress("alice_123")
    print(f"Progress: {json.dumps(progress, indent=2)}")

    # Alice should now have INVITED tier
    print("\n5. Alice creates her free Coqui voice avatar...")
    avatar_result = await system.create_voice_avatar(
        "alice_123",
        ["alice_voice_sample.wav"]
    )
    print(f"Avatar result: {json.dumps(avatar_result, indent=2)}")

    # Scenario 4: New premium user
    print("\n6. Premium user registration...")
    await system.register_user("premium_user")
    upgrade_result = await system.upgrade_to_premium("premium_user", payment_verified=True)
    print(f"Upgrade result: {json.dumps(upgrade_result, indent=2)}")

    # Scenario 5: Check leaderboard
    print("\n7. Invitation leaderboard...")
    leaderboard = system.get_leaderboard(limit=5)
    print("Top inviters:")
    for entry in leaderboard:
        print(f"  #{entry['rank']}: {entry['user_id']} - {entry['invites']} invites ({entry['badge']})")

    # Scenario 6: Try to use voice without avatar (free user)
    print("\n8. Free user trying to use voice...")
    await system.register_user("free_user")
    speech_result = await system.generate_speech(
        "Hello, this is a test",
        "free_user"
    )
    print(f"Result: {json.dumps(speech_result, indent=2)}")


if __name__ == "__main__":
    asyncio.run(demo())