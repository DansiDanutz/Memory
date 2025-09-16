"""
Gamified Contact Slots System
==============================
Earn contact slots by inviting friends - gamification for family & friends memory sharing
Every 5 invitations = 1 new contact slot to share memories with loved ones
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from dotenv import load_dotenv

load_dotenv()


class RewardType(Enum):
    """Types of rewards users can earn"""
    CONTACT_SLOT = "contact_slot"  # New contact slot for family/friends
    VOICE_AVATAR = "voice_avatar"  # Free voice avatar (Coqui)
    PREMIUM_FEATURE = "premium_feature"  # Premium feature unlock
    STORAGE_BONUS = "storage_bonus"  # Extra storage space
    PRIORITY_PROCESSING = "priority_processing"  # Faster processing


@dataclass
class ContactSlot:
    """A slot for sharing memories with a contact"""
    slot_id: str
    owner_id: str
    contact_name: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    relationship: str = "friend"  # family, friend, colleague, etc.
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    can_view_memories: bool = True
    can_add_memories: bool = False
    memory_count: int = 0
    last_interaction: Optional[datetime] = None


@dataclass
class UserRewards:
    """Track all rewards earned by a user"""
    user_id: str
    total_invitations: int = 0
    successful_invitations: int = 0

    # Contact slots
    base_contact_slots: int = 3  # Everyone starts with 3 slots
    earned_contact_slots: int = 0
    used_contact_slots: int = 0

    # Voice avatar status
    has_voice_avatar: bool = False
    voice_avatar_unlocked_at: Optional[datetime] = None

    # Other rewards
    storage_bonus_mb: int = 0
    has_priority_processing: bool = False

    # Milestones
    milestones_reached: List[str] = field(default_factory=list)
    next_milestone: Optional[str] = None
    invites_to_next_reward: int = 5


class GamifiedContactSlotsSystem:
    """
    Main system for managing contact slots through gamification
    Core concept: Every 5 invitations = 1 new contact slot
    """

    # Reward thresholds
    INVITES_PER_CONTACT_SLOT = 5
    INVITES_FOR_VOICE_AVATAR = 5  # First milestone
    INVITES_FOR_PRIORITY = 15
    INVITES_FOR_STORAGE_BONUS = 10

    # Milestones with rewards
    MILESTONES = {
        5: {
            "name": "Social Starter",
            "rewards": [RewardType.VOICE_AVATAR, RewardType.CONTACT_SLOT],
            "message": "🎉 First milestone! Voice avatar + contact slot unlocked!"
        },
        10: {
            "name": "Community Builder",
            "rewards": [RewardType.CONTACT_SLOT, RewardType.STORAGE_BONUS],
            "message": "🚀 10 friends! Extra contact slot + 500MB storage!"
        },
        15: {
            "name": "Network Pro",
            "rewards": [RewardType.CONTACT_SLOT, RewardType.PRIORITY_PROCESSING],
            "message": "⚡ Priority processing unlocked + contact slot!"
        },
        20: {
            "name": "Social Champion",
            "rewards": [RewardType.CONTACT_SLOT, RewardType.CONTACT_SLOT],
            "message": "🏆 20 friends! Double contact slots earned!"
        },
        25: {
            "name": "Memory Master",
            "rewards": [RewardType.CONTACT_SLOT, RewardType.PREMIUM_FEATURE],
            "message": "👑 Premium features unlocked + contact slot!"
        },
        50: {
            "name": "Ultimate Connector",
            "rewards": [RewardType.CONTACT_SLOT] * 3,
            "message": "🌟 LEGENDARY! Triple contact slots + lifetime perks!"
        }
    }

    def __init__(self):
        self.user_rewards: Dict[str, UserRewards] = {}
        self.contact_slots: Dict[str, List[ContactSlot]] = {}
        self.invitation_tracking: Dict[str, List[str]] = {}  # user_id -> invited_users

        print("[OK] Gamified Contact Slots System initialized")
        print("[INFO] Reward: 1 contact slot per 5 invitations")

    async def register_user(self, user_id: str) -> Dict[str, Any]:
        """
        Register a new user with base contact slots

        Args:
            user_id: Unique user identifier

        Returns:
            User's initial rewards profile
        """
        if user_id in self.user_rewards:
            return {
                "success": False,
                "error": "User already registered",
                "rewards": self._serialize_rewards(self.user_rewards[user_id])
            }

        # Create initial rewards profile
        rewards = UserRewards(user_id=user_id)
        self.user_rewards[user_id] = rewards
        self.contact_slots[user_id] = []
        self.invitation_tracking[user_id] = []

        # Create default contact slots
        for i in range(rewards.base_contact_slots):
            await self._create_default_slot(user_id, i + 1)

        return {
            "success": True,
            "message": "Welcome! You have 3 contact slots to start",
            "rewards": self._serialize_rewards(rewards),
            "tips": [
                "Add family and friends to your first 3 slots",
                "Invite 5 friends to earn an extra slot",
                "Every 5 invitations = 1 new contact slot!",
                "First 5 invites also unlock your voice avatar"
            ]
        }

    async def process_successful_invitation(
        self,
        inviter_id: str,
        invited_id: str
    ) -> Dict[str, Any]:
        """
        Process a successful invitation and distribute rewards

        Args:
            inviter_id: User who sent the invitation
            invited_id: User who accepted the invitation

        Returns:
            Rewards earned and progress update
        """
        if inviter_id not in self.user_rewards:
            await self.register_user(inviter_id)

        rewards = self.user_rewards[inviter_id]
        rewards.total_invitations += 1
        rewards.successful_invitations += 1

        # Track invitation
        if inviter_id not in self.invitation_tracking:
            self.invitation_tracking[inviter_id] = []
        self.invitation_tracking[inviter_id].append(invited_id)

        # Check for rewards
        earned_rewards = await self._check_and_apply_rewards(inviter_id)

        # Calculate progress
        progress = self._calculate_progress(rewards)

        return {
            "success": True,
            "user_id": inviter_id,
            "total_invitations": rewards.successful_invitations,
            "earned_rewards": earned_rewards,
            "progress": progress,
            "message": self._generate_progress_message(rewards, earned_rewards)
        }

    async def _check_and_apply_rewards(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Check if user has earned any rewards and apply them

        Args:
            user_id: User to check

        Returns:
            List of earned rewards
        """
        rewards = self.user_rewards[user_id]
        earned = []
        invites = rewards.successful_invitations

        # Check contact slot rewards (every 5 invitations)
        slots_earned = invites // self.INVITES_PER_CONTACT_SLOT
        if slots_earned > rewards.earned_contact_slots:
            new_slots = slots_earned - rewards.earned_contact_slots
            rewards.earned_contact_slots = slots_earned

            for _ in range(new_slots):
                slot = await self._award_contact_slot(user_id)
                earned.append({
                    "type": RewardType.CONTACT_SLOT.value,
                    "description": "New contact slot unlocked!",
                    "details": f"You can now add another family member or friend",
                    "slot_id": slot.slot_id
                })

        # Check milestone rewards
        for milestone_invites, milestone_data in self.MILESTONES.items():
            if invites >= milestone_invites and milestone_data["name"] not in rewards.milestones_reached:
                rewards.milestones_reached.append(milestone_data["name"])

                for reward_type in milestone_data["rewards"]:
                    if reward_type == RewardType.VOICE_AVATAR and not rewards.has_voice_avatar:
                        rewards.has_voice_avatar = True
                        rewards.voice_avatar_unlocked_at = datetime.now()
                        earned.append({
                            "type": RewardType.VOICE_AVATAR.value,
                            "description": "Voice Avatar Unlocked!",
                            "details": "Record your voice to create your AI avatar"
                        })

                    elif reward_type == RewardType.STORAGE_BONUS:
                        rewards.storage_bonus_mb += 500
                        earned.append({
                            "type": RewardType.STORAGE_BONUS.value,
                            "description": "Storage Bonus!",
                            "details": "+500MB for your memories"
                        })

                    elif reward_type == RewardType.PRIORITY_PROCESSING:
                        rewards.has_priority_processing = True
                        earned.append({
                            "type": RewardType.PRIORITY_PROCESSING.value,
                            "description": "Priority Processing!",
                            "details": "Your memories are processed faster"
                        })

                earned.append({
                    "type": "milestone",
                    "description": f"Milestone: {milestone_data['name']}",
                    "details": milestone_data["message"]
                })

        # Update next milestone
        rewards.next_milestone = self._get_next_milestone(invites)
        rewards.invites_to_next_reward = self._calculate_invites_to_next_reward(invites)

        return earned

    async def _award_contact_slot(self, user_id: str) -> ContactSlot:
        """Award a new contact slot to user"""
        slot_number = len(self.contact_slots.get(user_id, [])) + 1
        slot = ContactSlot(
            slot_id=f"slot_{user_id}_{slot_number}",
            owner_id=user_id,
            contact_name=f"Slot {slot_number} (Available)",
            relationship="pending"
        )

        if user_id not in self.contact_slots:
            self.contact_slots[user_id] = []
        self.contact_slots[user_id].append(slot)

        return slot

    async def add_contact_to_slot(
        self,
        user_id: str,
        slot_id: str,
        contact_name: str,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        relationship: str = "friend",
        permissions: Dict[str, bool] = None
    ) -> Dict[str, Any]:
        """
        Add a contact to an available slot

        Args:
            user_id: User adding the contact
            slot_id: Slot to use
            contact_name: Name of the contact
            contact_phone: Optional phone number
            contact_email: Optional email
            relationship: Relationship type (family, friend, etc.)
            permissions: What the contact can do

        Returns:
            Success status and slot details
        """
        if user_id not in self.contact_slots:
            return {
                "success": False,
                "error": "User not found"
            }

        # Find the slot
        slot = None
        for s in self.contact_slots[user_id]:
            if s.slot_id == slot_id:
                slot = s
                break

        if not slot:
            return {
                "success": False,
                "error": "Slot not found"
            }

        if slot.contact_name != f"Slot {slot_id.split('_')[-1]} (Available)":
            return {
                "success": False,
                "error": "Slot already occupied"
            }

        # Update slot with contact information
        slot.contact_name = contact_name
        slot.contact_phone = contact_phone
        slot.contact_email = contact_email
        slot.relationship = relationship
        slot.last_interaction = datetime.now()

        if permissions:
            slot.can_view_memories = permissions.get("view", True)
            slot.can_add_memories = permissions.get("add", False)

        # Track used slots
        rewards = self.user_rewards[user_id]
        rewards.used_contact_slots += 1

        return {
            "success": True,
            "message": f"{contact_name} added to your memory circle!",
            "slot": self._serialize_slot(slot),
            "available_slots": self._get_available_slots_count(user_id)
        }

    def get_user_slots(self, user_id: str) -> Dict[str, Any]:
        """
        Get all contact slots for a user

        Args:
            user_id: User ID

        Returns:
            All slots with their status
        """
        if user_id not in self.user_rewards:
            return {
                "success": False,
                "error": "User not found"
            }

        rewards = self.user_rewards[user_id]
        slots = self.contact_slots.get(user_id, [])

        total_slots = rewards.base_contact_slots + rewards.earned_contact_slots
        available = total_slots - rewards.used_contact_slots

        return {
            "success": True,
            "total_slots": total_slots,
            "base_slots": rewards.base_contact_slots,
            "earned_slots": rewards.earned_contact_slots,
            "used_slots": rewards.used_contact_slots,
            "available_slots": available,
            "slots": [self._serialize_slot(s) for s in slots],
            "next_slot_in": rewards.invites_to_next_reward,
            "tip": f"Invite {rewards.invites_to_next_reward} more friends for another slot!"
        }

    def get_progress_overview(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete progress overview for user

        Args:
            user_id: User ID

        Returns:
            Comprehensive progress and rewards status
        """
        if user_id not in self.user_rewards:
            return {
                "success": False,
                "error": "User not found"
            }

        rewards = self.user_rewards[user_id]
        progress = self._calculate_progress(rewards)

        return {
            "success": True,
            "user_id": user_id,
            "invitations": {
                "total": rewards.total_invitations,
                "successful": rewards.successful_invitations,
                "next_reward_at": ((rewards.successful_invitations // 5) + 1) * 5,
                "progress_to_next": progress["percentage"]
            },
            "contact_slots": {
                "total": rewards.base_contact_slots + rewards.earned_contact_slots,
                "base": rewards.base_contact_slots,
                "earned": rewards.earned_contact_slots,
                "used": rewards.used_contact_slots,
                "available": (rewards.base_contact_slots + rewards.earned_contact_slots) - rewards.used_contact_slots
            },
            "rewards": {
                "voice_avatar": rewards.has_voice_avatar,
                "priority_processing": rewards.has_priority_processing,
                "storage_bonus_mb": rewards.storage_bonus_mb,
                "milestones": rewards.milestones_reached
            },
            "next_milestone": rewards.next_milestone,
            "gamification_level": self._calculate_level(rewards.successful_invitations)
        }

    def share_memory_with_contacts(
        self,
        user_id: str,
        memory_id: str,
        slot_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Share a memory with selected contacts

        Args:
            user_id: User sharing the memory
            memory_id: Memory to share
            slot_ids: Contact slots to share with

        Returns:
            Sharing result
        """
        if user_id not in self.contact_slots:
            return {
                "success": False,
                "error": "User not found"
            }

        shared_with = []
        failed = []

        for slot_id in slot_ids:
            slot = self._get_slot_by_id(user_id, slot_id)
            if slot and slot.is_active:
                slot.memory_count += 1
                slot.last_interaction = datetime.now()
                shared_with.append({
                    "contact": slot.contact_name,
                    "relationship": slot.relationship
                })
            else:
                failed.append(slot_id)

        return {
            "success": True,
            "memory_id": memory_id,
            "shared_with": shared_with,
            "failed": failed,
            "message": f"Memory shared with {len(shared_with)} contacts"
        }

    def get_leaderboard_with_slots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get leaderboard showing users with most contact slots

        Args:
            limit: Number of top users

        Returns:
            Leaderboard data
        """
        leaderboard = []

        for user_id, rewards in self.user_rewards.items():
            total_slots = rewards.base_contact_slots + rewards.earned_contact_slots
            leaderboard.append({
                "user_id": self._anonymize_user_id(user_id),
                "invitations": rewards.successful_invitations,
                "total_slots": total_slots,
                "earned_slots": rewards.earned_contact_slots,
                "level": self._calculate_level(rewards.successful_invitations),
                "milestones": len(rewards.milestones_reached)
            })

        # Sort by earned slots, then by invitations
        leaderboard.sort(key=lambda x: (x["earned_slots"], x["invitations"]), reverse=True)

        return leaderboard[:limit]

    # Helper Methods

    def _calculate_progress(self, rewards: UserRewards) -> Dict[str, Any]:
        """Calculate progress to next reward"""
        current = rewards.successful_invitations
        next_slot_at = ((current // 5) + 1) * 5
        progress = (current % 5) / 5 * 100

        return {
            "current": current,
            "next_reward_at": next_slot_at,
            "invites_needed": next_slot_at - current,
            "percentage": progress,
            "progress_bar": self._generate_progress_bar(current % 5, 5)
        }

    def _generate_progress_bar(self, current: int, total: int) -> str:
        """Generate visual progress bar"""
        filled = int((current / total) * 10)
        empty = 10 - filled
        return "🟢" * filled + "⚪" * empty

    def _calculate_level(self, invitations: int) -> Dict[str, Any]:
        """Calculate gamification level based on invitations"""
        levels = [
            (0, "Beginner", "🌱"),
            (5, "Social", "👥"),
            (10, "Connected", "🔗"),
            (15, "Networker", "🌐"),
            (20, "Influencer", "⭐"),
            (30, "Champion", "🏆"),
            (50, "Legend", "👑"),
            (100, "Master", "🌟")
        ]

        current_level = levels[0]
        next_level = levels[1] if len(levels) > 1 else None

        for i, (req, name, icon) in enumerate(levels):
            if invitations >= req:
                current_level = (req, name, icon)
                next_level = levels[i + 1] if i + 1 < len(levels) else None

        level_progress = 0
        if next_level:
            progress_in_level = invitations - current_level[0]
            level_range = next_level[0] - current_level[0]
            level_progress = (progress_in_level / level_range) * 100

        return {
            "name": current_level[1],
            "icon": current_level[2],
            "number": levels.index(current_level) + 1,
            "next_level": next_level[1] if next_level else "MAX",
            "progress": level_progress,
            "invitations_to_next": next_level[0] - invitations if next_level else 0
        }

    def _get_next_milestone(self, current_invites: int) -> Optional[str]:
        """Get the next milestone name"""
        for invites, data in sorted(self.MILESTONES.items()):
            if current_invites < invites:
                return data["name"]
        return None

    def _calculate_invites_to_next_reward(self, current: int) -> int:
        """Calculate invites needed for next reward"""
        next_slot = ((current // 5) + 1) * 5
        return next_slot - current

    def _generate_progress_message(
        self,
        rewards: UserRewards,
        earned: List[Dict]
    ) -> str:
        """Generate encouraging progress message"""
        if earned:
            if any(r["type"] == RewardType.CONTACT_SLOT.value for r in earned):
                return f"🎉 New contact slot unlocked! You now have {rewards.base_contact_slots + rewards.earned_contact_slots} total slots!"
            elif any(r["type"] == RewardType.VOICE_AVATAR.value for r in earned):
                return "🎤 Amazing! Your voice avatar is now unlocked!"
            else:
                return f"🌟 Rewards earned! Keep inviting for more slots!"
        else:
            remaining = rewards.invites_to_next_reward
            if remaining == 1:
                return "Just 1 more invite for your next contact slot! 🎯"
            elif remaining <= 2:
                return f"So close! {remaining} more invites for a new slot! 💪"
            else:
                return f"Great progress! {remaining} invites to your next contact slot."

    def _get_available_slots_count(self, user_id: str) -> int:
        """Get number of available slots for user"""
        rewards = self.user_rewards.get(user_id)
        if not rewards:
            return 0
        return (rewards.base_contact_slots + rewards.earned_contact_slots) - rewards.used_contact_slots

    def _get_slot_by_id(self, user_id: str, slot_id: str) -> Optional[ContactSlot]:
        """Get a specific slot by ID"""
        slots = self.contact_slots.get(user_id, [])
        for slot in slots:
            if slot.slot_id == slot_id:
                return slot
        return None

    async def _create_default_slot(self, user_id: str, slot_number: int):
        """Create a default empty slot"""
        slot = ContactSlot(
            slot_id=f"slot_{user_id}_{slot_number}",
            owner_id=user_id,
            contact_name=f"Slot {slot_number} (Available)",
            relationship="pending"
        )

        if user_id not in self.contact_slots:
            self.contact_slots[user_id] = []
        self.contact_slots[user_id].append(slot)

    def _serialize_rewards(self, rewards: UserRewards) -> Dict[str, Any]:
        """Serialize rewards for API response"""
        return {
            "user_id": rewards.user_id,
            "invitations": rewards.successful_invitations,
            "contact_slots": {
                "total": rewards.base_contact_slots + rewards.earned_contact_slots,
                "available": (rewards.base_contact_slots + rewards.earned_contact_slots) - rewards.used_contact_slots
            },
            "voice_avatar": rewards.has_voice_avatar,
            "milestones": rewards.milestones_reached,
            "next_reward_in": rewards.invites_to_next_reward
        }

    def _serialize_slot(self, slot: ContactSlot) -> Dict[str, Any]:
        """Serialize contact slot for API response"""
        return {
            "slot_id": slot.slot_id,
            "contact_name": slot.contact_name,
            "relationship": slot.relationship,
            "is_available": "Available" in slot.contact_name,
            "permissions": {
                "view": slot.can_view_memories,
                "add": slot.can_add_memories
            },
            "memory_count": slot.memory_count,
            "last_interaction": slot.last_interaction.isoformat() if slot.last_interaction else None
        }

    def _anonymize_user_id(self, user_id: str) -> str:
        """Anonymize user ID for public display"""
        if len(user_id) > 8:
            return f"{user_id[:4]}****"
        return "User****"


# Demo
async def demo():
    """Demonstrate the gamified contact slots system"""
    print("=" * 70)
    print("GAMIFIED CONTACT SLOTS SYSTEM DEMO")
    print("=" * 70)
    print("Game Rule: Every 5 invitations = 1 new contact slot!")
    print("=" * 70)

    system = GamifiedContactSlotsSystem()

    # Register Alice
    print("\n1. Alice joins Memory Bot...")
    result = await system.register_user("alice_123")
    print(f"Alice starts with {result['rewards']['contact_slots']['total']} contact slots")

    # Alice adds her family to initial slots
    print("\n2. Alice adds family members to her slots...")
    await system.add_contact_to_slot(
        "alice_123",
        "slot_alice_123_1",
        "Mom",
        relationship="family",
        permissions={"view": True, "add": True}
    )
    await system.add_contact_to_slot(
        "alice_123",
        "slot_alice_123_2",
        "Dad",
        relationship="family"
    )
    await system.add_contact_to_slot(
        "alice_123",
        "slot_alice_123_3",
        "Sister Sarah",
        relationship="family"
    )

    # Show current slots
    slots = system.get_user_slots("alice_123")
    print(f"Used slots: {slots['used_slots']}/{slots['total_slots']}")

    # Alice invites friends
    print("\n3. Alice starts inviting friends...")
    invited_users = ["bob", "charlie", "diana", "eve", "frank"]

    for i, friend in enumerate(invited_users, 1):
        result = await system.process_successful_invitation("alice_123", friend)
        print(f"   Friend {i}: {friend} joined!")
        print(f"   Progress: {result['progress']['progress_bar']} ({result['total_invitations']}/5)")

        if result['earned_rewards']:
            for reward in result['earned_rewards']:
                print(f"   🎁 REWARD: {reward['description']}")

    # Check Alice's new slots
    print("\n4. Alice's updated profile...")
    overview = system.get_progress_overview("alice_123")
    print(f"Total slots: {overview['contact_slots']['total']} (earned: {overview['contact_slots']['earned']})")
    print(f"Voice avatar: {'✅ Unlocked' if overview['rewards']['voice_avatar'] else '❌ Locked'}")
    print(f"Level: {overview['gamification_level']['name']} {overview['gamification_level']['icon']}")

    # Alice adds more contacts with her earned slot
    print("\n5. Alice adds her best friend to the earned slot...")
    await system.add_contact_to_slot(
        "alice_123",
        "slot_alice_123_4",
        "Best Friend Emma",
        relationship="friend"
    )

    # Continue inviting for more slots
    print("\n6. Alice continues inviting (simulating 10 more)...")
    for i in range(10):
        await system.process_successful_invitation("alice_123", f"user_{i}")

    final_overview = system.get_progress_overview("alice_123")
    print(f"\nFinal Stats:")
    print(f"  Total invitations: {final_overview['invitations']['successful']}")
    print(f"  Total contact slots: {final_overview['contact_slots']['total']}")
    print(f"  Level: {final_overview['gamification_level']['name']} {final_overview['gamification_level']['icon']}")
    print(f"  Milestones reached: {', '.join(final_overview['rewards']['milestones'])}")

    # Show leaderboard
    print("\n7. Leaderboard...")
    leaderboard = system.get_leaderboard_with_slots(5)
    for rank, user in enumerate(leaderboard, 1):
        print(f"  #{rank}: {user['user_id']} - {user['earned_slots']} earned slots ({user['invitations']} invites)")


if __name__ == "__main__":
    asyncio.run(demo())