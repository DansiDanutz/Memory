"""
WhatsApp Integration for Gamified Invitation System
===================================================
Handles invitation sharing, tracking, and notifications via WhatsApp
"""

import os
import json
import re
import asyncio
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()


class WhatsAppInvitationHandler:
    """
    Manages WhatsApp-based invitations for the gamified voice avatar system
    """

    def __init__(self, voice_system=None):
        # WhatsApp API Configuration
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", os.getenv("META_ACCESS_TOKEN"))
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", os.getenv("WA_PHONE_NUMBER_ID"))
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"

        # Voice system reference
        self.voice_system = voice_system

        # Message templates
        self.templates = self._load_message_templates()

        # Track sent invitations
        self.sent_invitations = {}  # phone -> invitation_code

        print("[OK] WhatsApp Invitation Handler initialized")

    def _load_message_templates(self) -> Dict[str, str]:
        """Load message templates for different scenarios"""
        return {
            "invitation": """
🎉 *You're Invited to Memory Bot!*

{inviter_name} wants you to join Memory Bot - the AI assistant with perfect memory!

🎁 *Special Offer:*
Join with this code and help {inviter_name} unlock their FREE voice avatar!

📱 *Your Invitation Code:* `{code}`

✨ *What You Get:*
• AI assistant that never forgets
• Perfect meeting notes and summaries
• Voice commands and responses
• Invite 5 friends = FREE voice avatar!

👉 *Join Now:* {app_link}

_This invitation expires in {days} days_
            """,

            "invitation_accepted": """
🎊 *Great News!*

Your friend just joined Memory Bot using your invitation code!

✅ *Progress Update:*
• Friends invited: {successful_invites}/{required_invites}
• {remaining} more to unlock your FREE voice avatar!

{progress_bar}

Keep sharing to unlock your voice avatar! 🎯
            """,

            "reward_unlocked": """
🏆 *CONGRATULATIONS!*

You've unlocked your FREE Voice Avatar! 🎉

✅ You invited {successful_invites} friends
🎤 Your personalized AI voice is ready
🚀 Record your voice samples now!

*Next Steps:*
1. Open Memory Bot
2. Go to Voice Settings
3. Record 3-5 voice samples
4. Start using voice commands!

_Want even better quality? Upgrade to Premium for ElevenLabs ultra-realistic voice!_
            """,

            "welcome_new_user": """
👋 *Welcome to Memory Bot!*

You joined using {inviter_name}'s invitation code.

🎯 *Your Journey:*
• Start recording memories
• Invite 5 friends = FREE voice avatar
• Or upgrade for instant premium access

📱 *Your Invitation Code:* `{user_code}`

Share it with friends and unlock amazing features!
            """,

            "reminder": """
🔔 *Reminder: Unlock Your Voice Avatar!*

You're so close! Just {remaining} more friends and you'll have your FREE voice avatar.

📱 *Your Code:* `{code}`
📊 *Progress:* {successful_invites}/{required_invites}

Share now and start talking to your AI assistant! 🗣️
            """,

            "premium_upgrade": """
⭐ *Welcome to Premium!*

Your ElevenLabs voice avatar is now active!

✨ *Premium Benefits:*
• Ultra-realistic voice cloning
• Emotion control in speech
• Priority processing
• Unlimited generations
• Multi-language support

🎤 Record new voice samples for the best quality!
            """
        }

    async def send_invitation(
        self,
        inviter_id: str,
        recipient_phone: str,
        invitation_code: str,
        inviter_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send invitation via WhatsApp

        Args:
            inviter_id: User sending the invitation
            recipient_phone: WhatsApp phone number to invite
            invitation_code: Unique invitation code
            inviter_name: Optional name of inviter

        Returns:
            Send result with message ID
        """
        try:
            # Format phone number
            formatted_phone = self._format_phone_number(recipient_phone)

            # Generate invitation message
            message = self.templates["invitation"].format(
                inviter_name=inviter_name or "Your friend",
                code=invitation_code,
                app_link=self._get_app_link(invitation_code),
                days=30
            )

            # Send via WhatsApp API
            result = await self._send_whatsapp_message(
                formatted_phone,
                message,
                buttons=[
                    {"type": "reply", "reply": {"id": f"accept_{invitation_code}", "title": "Join Now"}},
                    {"type": "reply", "reply": {"id": "learn_more", "title": "Learn More"}}
                ]
            )

            if result["success"]:
                # Track sent invitation
                self.sent_invitations[formatted_phone] = invitation_code

                # Log for analytics
                self._log_invitation_sent(inviter_id, recipient_phone, invitation_code)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def notify_invitation_accepted(
        self,
        inviter_phone: str,
        inviter_id: str,
        new_user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Notify user when their invitation is accepted

        Args:
            inviter_phone: Inviter's WhatsApp number
            inviter_id: Inviter's user ID
            new_user_name: Name of new user who joined

        Returns:
            Notification result
        """
        try:
            # Get inviter's progress
            if self.voice_system:
                progress = self.voice_system.get_invitation_progress(inviter_id)
                successful = progress.get("current_invites", 0)
                required = progress.get("total_required", 5)
                remaining = required - successful
            else:
                successful, required, remaining = 1, 5, 4

            # Generate progress bar
            progress_bar = self._generate_progress_bar(successful, required)

            # Format message
            message = self.templates["invitation_accepted"].format(
                successful_invites=successful,
                required_invites=required,
                remaining=remaining,
                progress_bar=progress_bar
            )

            # Send notification
            return await self._send_whatsapp_message(inviter_phone, message)

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def notify_reward_unlocked(
        self,
        user_phone: str,
        user_id: str,
        successful_invites: int
    ) -> Dict[str, Any]:
        """
        Notify user when they unlock their free voice avatar

        Args:
            user_phone: User's WhatsApp number
            user_id: User ID
            successful_invites: Number of successful invitations

        Returns:
            Notification result
        """
        try:
            message = self.templates["reward_unlocked"].format(
                successful_invites=successful_invites
            )

            # Send with action button
            result = await self._send_whatsapp_message(
                user_phone,
                message,
                buttons=[
                    {"type": "reply", "reply": {"id": "setup_voice", "title": "Setup Voice Now"}},
                    {"type": "reply", "reply": {"id": "upgrade_premium", "title": "View Premium"}}
                ]
            )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def send_welcome_message(
        self,
        new_user_phone: str,
        user_code: str,
        inviter_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send welcome message to new user who joined via invitation

        Args:
            new_user_phone: New user's phone number
            user_code: New user's invitation code
            inviter_name: Name of person who invited them

        Returns:
            Message result
        """
        try:
            message = self.templates["welcome_new_user"].format(
                inviter_name=inviter_name or "a friend",
                user_code=user_code
            )

            return await self._send_whatsapp_message(
                new_user_phone,
                message,
                buttons=[
                    {"type": "reply", "reply": {"id": "get_started", "title": "Get Started"}},
                    {"type": "reply", "reply": {"id": "share_code", "title": "Share My Code"}}
                ]
            )

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def send_reminder(
        self,
        user_phone: str,
        user_id: str,
        invitation_code: str
    ) -> Dict[str, Any]:
        """
        Send reminder to users close to unlocking voice avatar

        Args:
            user_phone: User's phone number
            user_id: User ID
            invitation_code: User's invitation code

        Returns:
            Reminder result
        """
        try:
            # Get progress
            if self.voice_system:
                progress = self.voice_system.get_invitation_progress(user_id)
                successful = progress.get("current_invites", 0)
                required = progress.get("total_required", 5)
                remaining = required - successful
            else:
                successful, required, remaining = 3, 5, 2

            # Only send if close (2 or less remaining)
            if remaining > 2:
                return {
                    "success": False,
                    "error": "Not close enough for reminder"
                }

            message = self.templates["reminder"].format(
                remaining=remaining,
                code=invitation_code,
                successful_invites=successful,
                required_invites=required
            )

            return await self._send_whatsapp_message(
                user_phone,
                message,
                buttons=[
                    {"type": "reply", "reply": {"id": f"share_{invitation_code}", "title": "Share Now"}}
                ]
            )

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def notify_premium_upgrade(
        self,
        user_phone: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Notify user of successful premium upgrade

        Args:
            user_phone: User's phone number
            user_id: User ID

        Returns:
            Notification result
        """
        try:
            message = self.templates["premium_upgrade"]

            return await self._send_whatsapp_message(
                user_phone,
                message,
                buttons=[
                    {"type": "reply", "reply": {"id": "record_voice", "title": "Record Voice"}},
                    {"type": "reply", "reply": {"id": "view_benefits", "title": "View Benefits"}}
                ]
            )

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def process_incoming_message(
        self,
        from_phone: str,
        message_text: str,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Process incoming WhatsApp messages for invitation codes

        Args:
            from_phone: Sender's phone number
            message_text: Message content
            message_type: Type of message

        Returns:
            Processing result
        """
        try:
            # Extract invitation code from message
            code = self._extract_invitation_code(message_text)

            if code:
                # Process invitation acceptance
                if self.voice_system:
                    # Register user with invitation code
                    result = await self.voice_system.register_user(
                        user_id=self._generate_user_id(from_phone),
                        invitation_code=code
                    )

                    if result["success"]:
                        # Send welcome message
                        await self.send_welcome_message(
                            from_phone,
                            result["profile"]["invitation_code"]
                        )

                        return {
                            "success": True,
                            "action": "user_registered",
                            "code": code
                        }

                return {
                    "success": True,
                    "action": "code_received",
                    "code": code
                }

            # Check for button responses
            if message_text.startswith("accept_"):
                code = message_text.replace("accept_", "")
                return {
                    "success": True,
                    "action": "invitation_accepted",
                    "code": code
                }

            return {
                "success": False,
                "action": "no_code_found"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def share_invitation_code(
        self,
        user_phone: str,
        invitation_code: str,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Help user share their invitation code

        Args:
            user_phone: User's phone number
            invitation_code: Code to share
            custom_message: Optional custom message

        Returns:
            Share result
        """
        try:
            if custom_message:
                message = custom_message
            else:
                message = f"""
📱 *My Memory Bot Invitation Code:* `{invitation_code}`

Join and we both benefit! 🎁

{self._get_app_link(invitation_code)}
                """

            # Create shareable message
            return await self._send_whatsapp_message(
                user_phone,
                message,
                buttons=[
                    {"type": "reply", "reply": {"id": "copy_message", "title": "Copy Message"}}
                ]
            )

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # Helper Methods

    async def _send_whatsapp_message(
        self,
        to_phone: str,
        message: str,
        buttons: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Send message via WhatsApp Business API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            # Build message payload
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "text",
                "text": {"body": message}
            }

            # Add interactive buttons if provided
            if buttons:
                payload["type"] = "interactive"
                payload["interactive"] = {
                    "type": "button",
                    "body": {"text": message},
                    "action": {"buttons": buttons}
                }

            # Send request
            response = requests.post(
                f"{self.api_url}/messages",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "message_id": response.json().get("messages", [{}])[0].get("id")
                }
            else:
                return {
                    "success": False,
                    "error": response.text
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp API"""
        # Remove non-numeric characters
        phone = re.sub(r'\D', '', phone)

        # Add country code if missing
        if not phone.startswith('1') and len(phone) == 10:
            phone = '1' + phone  # US number

        return phone

    def _extract_invitation_code(self, text: str) -> Optional[str]:
        """Extract invitation code from message text"""
        # Look for patterns like "code: ABC123" or just "ABC123"
        patterns = [
            r'code[:\s]+([A-Z0-9]{6,8})',
            r'invitation[:\s]+([A-Z0-9]{6,8})',
            r'^([A-Z0-9]{6,8})$'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return None

    def _generate_progress_bar(self, current: int, total: int) -> str:
        """Generate visual progress bar"""
        filled = int((current / total) * 10)
        empty = 10 - filled
        return "🟢" * filled + "⚪" * empty

    def _get_app_link(self, invitation_code: str) -> str:
        """Generate app download/join link with code"""
        base_url = os.getenv("APP_PUBLIC_URL", "https://memorybot.ai")
        return f"{base_url}/join?code={invitation_code}"

    def _generate_user_id(self, phone: str) -> str:
        """Generate user ID from phone number"""
        return f"wa_{hashlib.md5(phone.encode()).hexdigest()[:10]}"

    def _log_invitation_sent(self, inviter_id: str, recipient: str, code: str):
        """Log invitation for analytics"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "inviter_id": inviter_id,
            "recipient": recipient,
            "code": code,
            "channel": "whatsapp"
        }
        print(f"[INVITATION] {json.dumps(log_entry)}")


# Scheduled Tasks

class InvitationScheduler:
    """Schedule invitation reminders and follow-ups"""

    def __init__(self, handler: WhatsAppInvitationHandler):
        self.handler = handler
        self.tasks = []

    async def start(self):
        """Start scheduled tasks"""
        self.tasks = [
            asyncio.create_task(self.send_daily_reminders()),
            asyncio.create_task(self.check_expired_invitations()),
            asyncio.create_task(self.send_progress_updates())
        ]

    async def send_daily_reminders(self):
        """Send daily reminders to users close to unlocking avatars"""
        while True:
            try:
                # Wait until 10 AM
                await self._wait_until_time(10, 0)

                # Get users with 1-2 invites remaining
                # This would query from database in production
                users_to_remind = []  # Get from database

                for user in users_to_remind:
                    await self.handler.send_reminder(
                        user["phone"],
                        user["id"],
                        user["invitation_code"]
                    )

                # Wait 24 hours
                await asyncio.sleep(86400)

            except Exception as e:
                print(f"[ERROR] Reminder task: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour

    async def check_expired_invitations(self):
        """Check and mark expired invitations"""
        while True:
            try:
                # Check every hour
                await asyncio.sleep(3600)

                # Mark 30+ day old pending invitations as expired
                # This would update database in production

            except Exception as e:
                print(f"[ERROR] Expiry check: {e}")

    async def send_progress_updates(self):
        """Send weekly progress updates"""
        while True:
            try:
                # Wait until Sunday 6 PM
                await self._wait_until_day_and_time(6, 18, 0)  # Sunday, 6 PM

                # Send progress updates to active users
                # This would query from database in production

                # Wait 1 week
                await asyncio.sleep(604800)

            except Exception as e:
                print(f"[ERROR] Progress updates: {e}")
                await asyncio.sleep(86400)  # Retry tomorrow

    async def _wait_until_time(self, hour: int, minute: int):
        """Wait until specific time of day"""
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if target < now:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

    async def _wait_until_day_and_time(self, day: int, hour: int, minute: int):
        """Wait until specific day and time (0=Monday, 6=Sunday)"""
        now = datetime.now()
        days_ahead = day - now.weekday()

        if days_ahead <= 0:
            days_ahead += 7

        target = now + timedelta(days=days_ahead)
        target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)

        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)


# Demo
async def demo():
    """Demonstrate WhatsApp invitation system"""
    print("=" * 60)
    print("WHATSAPP INVITATION SYSTEM DEMO")
    print("=" * 60)

    handler = WhatsAppInvitationHandler()

    # Example: Send invitation
    print("\n1. Sending invitation...")
    result = await handler.send_invitation(
        inviter_id="user_123",
        recipient_phone="+1234567890",
        invitation_code="DEMO123",
        inviter_name="Alice"
    )
    print(f"Result: {result}")

    # Example: Process incoming message with code
    print("\n2. Processing incoming message...")
    result = await handler.process_incoming_message(
        from_phone="+1234567890",
        message_text="I want to join! My code is DEMO123"
    )
    print(f"Result: {result}")

    # Example: Send progress update
    print("\n3. Sending progress notification...")
    result = await handler.notify_invitation_accepted(
        inviter_phone="+1234567890",
        inviter_id="user_123",
        new_user_name="Bob"
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(demo())