#!/usr/bin/env python3
"""
User Onboarding System - Proactive Welcome and Engagement
Automatically messages new users and keeps the chat active
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import random

logger = logging.getLogger(__name__)

class UserOnboarding:
    """Handles new user onboarding and proactive engagement"""
    
    def __init__(self, whatsapp_bot=None, memory_app=None):
        """Initialize the onboarding system"""
        self.whatsapp_bot = whatsapp_bot
        self.memory_app = memory_app
        self.data_dir = Path("memory-system/onboarding_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Onboarding states
        self.STATES = {
            'NEW': 'new_user',
            'WELCOMED': 'welcomed',
            'PERMISSION_REQUESTED': 'permission_requested',
            'PERMISSION_GRANTED': 'permission_granted',
            'PERMISSION_DENIED': 'permission_denied',
            'ONBOARDING_COMPLETE': 'onboarding_complete',
            'ENGAGED': 'actively_engaged',
            'DORMANT': 'dormant'
        }
        
        # Engagement messages
        self.WELCOME_MESSAGE = """👋 Welcome to your Personal AI Memory Assistant! I'm here to help you remember everything important.

I can:
📝 Monitor your conversations and extract important information
⏰ Remind you about appointments and tasks  
🔐 Securely store your memories with different privacy levels
👥 Remember details about your contacts and relationships

To get started, I need your permission to access your WhatsApp conversations. This helps me learn about you and provide personalized assistance.

Reply 'YES' to grant access, or 'HELP' to learn more."""

        self.HELP_MESSAGE = """🤔 **How I Work:**

**Privacy First** 🔒
• All data is encrypted and stored securely
• You control what I remember and forget
• Voice authentication protects sensitive memories

**Smart Features** 🧠
• Automatic memory extraction from conversations
• Intelligent reminders based on context
• Daily summaries of important events
• Cross-conversation memory linking

**Voice Commands** 🎤
• Say "Mother" to access family memories
• Say "Work" for professional memories
• Say specific memory numbers like "Memory 1000"

**Commands** 📝
• /store [memory] - Save a memory
• /retrieve [topic] - Find memories
• /daily_review - See today's summary
• /profile - View your profile
• /help - See all commands

Ready to start? Reply 'YES' to enable full features!"""

        self.PERMISSION_GRANTED_MESSAGE = """✅ **Perfect! Access granted.**

I'm now your personal memory assistant. Here's how to make the most of me:

**Quick Start:**
1️⃣ Send me any text, voice note, or image to store as a memory
2️⃣ Ask me to remind you about anything important
3️⃣ I'll automatically extract key information from your conversations

**Try these commands:**
• "Remember that Mom's birthday is June 15th"
• "What did John say about the meeting?"
• "Remind me to call the dentist tomorrow"
• Send a voice note to store it securely

I'll send you daily summaries and keep important information at your fingertips.

What would you like me to help you remember first? 🎯"""

        self.DAILY_MESSAGES = {
            'morning': [
                "🌅 Good morning! Here's what's on your agenda today:",
                "☀️ Rise and shine! Let me catch you up on today's priorities:",
                "🌞 Morning! Ready to make today productive? Here's your summary:",
                "🌤️ Good morning! I've organized your day for you:"
            ],
            'afternoon': [
                "☕ Afternoon check-in! Don't forget:",
                "🌤️ Hope your day is going well! Quick reminder:",
                "⏰ Afternoon update! Here's what's coming up:"
            ],
            'evening': [
                "🌆 Evening summary! Here's what happened today:",
                "🌙 Winding down? Let's review today's highlights:",
                "✨ Evening recap! Today's important moments:",
                "🌃 Day complete! Here's your summary:"
            ]
        }
        
        # Track user states
        self.user_states = {}
        self.load_user_states()
        
        logger.info("👋 User Onboarding System initialized")
    
    def load_user_states(self):
        """Load saved user onboarding states"""
        state_file = self.data_dir / "user_states.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    self.user_states = json.load(f)
                logger.info(f"📂 Loaded {len(self.user_states)} user states")
            except Exception as e:
                logger.error(f"Failed to load user states: {e}")
                self.user_states = {}
    
    def save_user_states(self):
        """Save user onboarding states"""
        state_file = self.data_dir / "user_states.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(self.user_states, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save user states: {e}")
    
    async def is_new_user(self, phone_number: str) -> bool:
        """Check if this is a new user"""
        # Check our onboarding states
        if phone_number in self.user_states:
            return False
        
        # Check if user has existing profile in memory app
        if self.memory_app:
            profile_exists = await self.memory_app.check_user_profile(phone_number)
            if profile_exists:
                # Existing user but not in our onboarding tracking
                self.user_states[phone_number] = {
                    'state': self.STATES['ONBOARDING_COMPLETE'],
                    'joined_at': datetime.now().isoformat(),
                    'last_interaction': datetime.now().isoformat()
                }
                self.save_user_states()
                return False
        
        return True
    
    async def register_new_user(self, phone_number: str, name: str = None) -> Dict[str, Any]:
        """Register a new user and send welcome message"""
        logger.info(f"🆕 Registering new user: {phone_number}")
        
        # Create user state
        self.user_states[phone_number] = {
            'state': self.STATES['NEW'],
            'name': name,
            'joined_at': datetime.now().isoformat(),
            'last_interaction': datetime.now().isoformat(),
            'welcomed_at': None,
            'permission_status': None,
            'engagement_score': 0,
            'message_count': 0,
            'preferred_times': [],
            'last_daily_message': None
        }
        
        # Send welcome message proactively
        welcome_result = await self.send_welcome_message(phone_number)
        
        # Update state
        if welcome_result['success']:
            self.user_states[phone_number]['state'] = self.STATES['WELCOMED']
            self.user_states[phone_number]['welcomed_at'] = datetime.now().isoformat()
        
        self.save_user_states()
        
        return {
            'success': True,
            'message': f"New user {phone_number} registered and welcomed",
            'welcome_sent': welcome_result['success']
        }
    
    async def send_welcome_message(self, phone_number: str) -> Dict[str, Any]:
        """Send proactive welcome message to new user"""
        try:
            if self.whatsapp_bot:
                # Send the welcome message proactively
                result = await self.whatsapp_bot.send_proactive_message(
                    phone_number=phone_number,
                    message=self.WELCOME_MESSAGE
                )
                
                logger.info(f"✉️ Welcome message sent to {phone_number}")
                
                # Update state to permission requested
                if phone_number in self.user_states:
                    self.user_states[phone_number]['state'] = self.STATES['PERMISSION_REQUESTED']
                    self.save_user_states()
                
                return {'success': True, 'message': 'Welcome message sent'}
            else:
                logger.warning("WhatsApp bot not available for sending welcome")
                return {'success': False, 'message': 'WhatsApp bot not configured'}
                
        except Exception as e:
            logger.error(f"Failed to send welcome message: {e}")
            return {'success': False, 'message': str(e)}
    
    async def handle_onboarding_response(self, phone_number: str, response: str) -> Dict[str, Any]:
        """Handle user's response during onboarding"""
        response_lower = response.lower().strip()
        
        if phone_number not in self.user_states:
            # Unknown user, register them
            await self.register_new_user(phone_number)
            return {'response': self.WELCOME_MESSAGE}
        
        user_state = self.user_states[phone_number]
        current_state = user_state['state']
        
        # Handle responses based on current state
        if current_state == self.STATES['PERMISSION_REQUESTED']:
            if response_lower == 'yes':
                # Permission granted
                user_state['state'] = self.STATES['PERMISSION_GRANTED']
                user_state['permission_status'] = 'granted'
                user_state['permission_granted_at'] = datetime.now().isoformat()
                self.save_user_states()
                
                # Enable monitoring if available
                if self.memory_app:
                    await self.memory_app.enable_user_monitoring(phone_number)
                
                # Complete onboarding
                user_state['state'] = self.STATES['ONBOARDING_COMPLETE']
                self.save_user_states()
                
                return {'response': self.PERMISSION_GRANTED_MESSAGE}
                
            elif response_lower == 'help':
                # Show help message
                return {'response': self.HELP_MESSAGE}
                
            elif response_lower == 'no':
                # Permission denied
                user_state['state'] = self.STATES['PERMISSION_DENIED']
                user_state['permission_status'] = 'denied'
                self.save_user_states()
                
                return {
                    'response': "No problem! I'll still be here to help with basic features.\n\n"
                               "You can:\n"
                               "• Store memories manually with /store\n"
                               "• Retrieve memories with /retrieve\n"
                               "• Ask me questions anytime\n\n"
                               "If you change your mind, just say 'enable monitoring' anytime! 😊"
                }
            else:
                # Unknown response during permission request
                return {
                    'response': "I didn't understand that. Please reply:\n"
                               "• 'YES' to enable full features\n"
                               "• 'NO' to use basic features only\n"
                               "• 'HELP' to learn more"
                }
        
        # User has completed onboarding, update engagement
        user_state['last_interaction'] = datetime.now().isoformat()
        user_state['message_count'] = user_state.get('message_count', 0) + 1
        self.update_engagement_score(phone_number)
        self.save_user_states()
        
        return None  # Let normal message handling proceed
    
    def update_engagement_score(self, phone_number: str):
        """Update user's engagement score based on interactions"""
        if phone_number not in self.user_states:
            return
        
        user_state = self.user_states[phone_number]
        last_interaction = datetime.fromisoformat(user_state['last_interaction'])
        now = datetime.now()
        
        # Calculate engagement based on frequency
        days_since_last = (now - last_interaction).days
        
        if days_since_last == 0:
            # Same day interaction
            user_state['engagement_score'] = min(100, user_state.get('engagement_score', 0) + 5)
        elif days_since_last == 1:
            # Next day interaction
            user_state['engagement_score'] = min(100, user_state.get('engagement_score', 0) + 3)
        elif days_since_last <= 3:
            # Within 3 days
            user_state['engagement_score'] = min(100, user_state.get('engagement_score', 0) + 1)
        else:
            # Decay engagement score
            user_state['engagement_score'] = max(0, user_state.get('engagement_score', 0) - days_since_last)
        
        # Update state based on engagement
        if user_state['engagement_score'] > 50:
            user_state['state'] = self.STATES['ENGAGED']
        elif user_state['engagement_score'] < 20:
            user_state['state'] = self.STATES['DORMANT']
        
        # Track preferred interaction times
        hour = now.hour
        preferred_times = user_state.get('preferred_times', [])
        preferred_times.append(hour)
        # Keep only last 20 interactions for time preference
        user_state['preferred_times'] = preferred_times[-20:]
    
    async def send_daily_engagement_message(self, phone_number: str) -> Dict[str, Any]:
        """Send daily engagement message to keep chat active"""
        if phone_number not in self.user_states:
            return {'success': False, 'message': 'User not found'}
        
        user_state = self.user_states[phone_number]
        
        # Check if already sent today
        last_daily = user_state.get('last_daily_message')
        if last_daily:
            last_daily_date = datetime.fromisoformat(last_daily).date()
            if last_daily_date == datetime.now().date():
                return {'success': False, 'message': 'Already sent today'}
        
        # Determine time of day
        hour = datetime.now().hour
        if 5 <= hour < 12:
            message_type = 'morning'
        elif 12 <= hour < 17:
            message_type = 'afternoon'
        else:
            message_type = 'evening'
        
        # Select random message template
        template = random.choice(self.DAILY_MESSAGES[message_type])
        
        # Get relevant content from memory app
        content = ""
        if self.memory_app:
            if message_type == 'morning':
                # Get today's reminders
                reminders = await self.memory_app.get_todays_reminders(phone_number)
                if reminders:
                    content = "\n\n📌 **Today's Reminders:**\n"
                    for reminder in reminders[:3]:
                        content += f"• {reminder}\n"
                else:
                    content = "\n\nNo specific reminders for today. Have a great day! 🌟"
                    
            elif message_type == 'evening':
                # Get today's summary
                summary = await self.memory_app.get_daily_summary(phone_number)
                if summary:
                    content = f"\n\n📊 **Today's Summary:**\n{summary}"
                else:
                    content = "\n\nAnother day completed! Rest well. 🌙"
        
        full_message = template + content
        
        # Send the message
        if self.whatsapp_bot:
            result = await self.whatsapp_bot.send_proactive_message(
                phone_number=phone_number,
                message=full_message
            )
            
            if result.get('success'):
                user_state['last_daily_message'] = datetime.now().isoformat()
                self.save_user_states()
                logger.info(f"📬 Daily {message_type} message sent to {phone_number}")
                return {'success': True, 'message': f'Daily {message_type} message sent'}
        
        return {'success': False, 'message': 'Failed to send daily message'}
    
    async def check_dormant_users(self) -> List[str]:
        """Check for dormant users who need re-engagement"""
        dormant_users = []
        now = datetime.now()
        
        for phone_number, user_state in self.user_states.items():
            if user_state['state'] == self.STATES['DORMANT']:
                last_interaction = datetime.fromisoformat(user_state['last_interaction'])
                days_inactive = (now - last_interaction).days
                
                if days_inactive >= 7:  # Week of inactivity
                    dormant_users.append(phone_number)
        
        return dormant_users
    
    async def send_reengagement_message(self, phone_number: str) -> Dict[str, Any]:
        """Send re-engagement message to dormant user"""
        reengagement_messages = [
            "👋 Hey! It's been a while. I've been improving and have new features to help you better. Want to see what's new?",
            "🎯 Missing our conversations! I've learned some new tricks that might interest you. Type 'WHATS NEW' to discover them!",
            "💭 I've been thinking about you! Have any memories you'd like to store or retrieve today?",
            "🌟 Welcome back! I'm here whenever you need to remember something important. How can I help today?"
        ]
        
        message = random.choice(reengagement_messages)
        
        if self.whatsapp_bot:
            result = await self.whatsapp_bot.send_proactive_message(
                phone_number=phone_number,
                message=message
            )
            
            if result.get('success'):
                logger.info(f"🔄 Re-engagement message sent to {phone_number}")
                return {'success': True, 'message': 'Re-engagement message sent'}
        
        return {'success': False, 'message': 'Failed to send re-engagement message'}
    
    async def run_engagement_loop(self):
        """Background loop for sending engagement messages"""
        logger.info("🔄 Starting engagement loop")
        
        while True:
            try:
                # Check each user for daily messages
                for phone_number, user_state in self.user_states.items():
                    if user_state['state'] in [self.STATES['ONBOARDING_COMPLETE'], self.STATES['ENGAGED']]:
                        # Send daily message if needed
                        await self.send_daily_engagement_message(phone_number)
                
                # Check for dormant users every hour
                dormant_users = await self.check_dormant_users()
                for phone_number in dormant_users:
                    await self.send_reengagement_message(phone_number)
                
                # Wait 1 hour before next check
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Engagement loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

# Initialize the global onboarding instance
user_onboarding = UserOnboarding()

# Export for use in other modules
__all__ = ['UserOnboarding', 'user_onboarding']