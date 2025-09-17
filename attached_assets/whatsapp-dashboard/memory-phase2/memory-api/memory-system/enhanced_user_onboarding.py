#!/usr/bin/env python3
"""
Enhanced User Onboarding System - Phase 2
Integrates with MD File Manager and Conversation Classifier
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import random
from dataclasses import dataclass, asdict

from md_file_manager import MDFileManager, MemoryTag
from conversation_classifier import ConversationClassifier, ConversationContext

logger = logging.getLogger(__name__)

@dataclass
class OnboardingStep:
    """Represents a step in the onboarding process"""
    step_id: str
    title: str
    description: str
    message: str
    expected_responses: List[str]
    next_step: Optional[str] = None
    completion_action: Optional[str] = None

class EnhancedUserOnboarding:
    """Enhanced User Onboarding System with MD File Integration"""
    
    def __init__(self, whatsapp_bot=None, telegram_bot=None, md_file_manager=None, 
                 conversation_classifier=None):
        """Initialize the enhanced onboarding system"""
        self.whatsapp_bot = whatsapp_bot
        self.telegram_bot = telegram_bot
        self.md_file_manager = md_file_manager or MDFileManager()
        self.conversation_classifier = conversation_classifier or ConversationClassifier()
        
        # Data directories
        self.data_dir = Path("memory-system/onboarding_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Onboarding states
        self.STATES = {
            'NEW': 'new_user',
            'PROFILE_SETUP': 'profile_setup',
            'PREFERENCES_SETUP': 'preferences_setup',
            'CONTACTS_SETUP': 'contacts_setup',
            'SECURITY_SETUP': 'security_setup',
            'WELCOME_COMPLETE': 'welcome_complete',
            'PERMISSION_REQUESTED': 'permission_requested',
            'PERMISSION_GRANTED': 'permission_granted',
            'PERMISSION_DENIED': 'permission_denied',
            'ONBOARDING_COMPLETE': 'onboarding_complete',
            'ENGAGED': 'actively_engaged',
            'DORMANT': 'dormant'
        }
        
        # Onboarding flow
        self.onboarding_steps = self._create_onboarding_flow()
        
        # User states tracking
        self.user_states = {}
        self.load_user_states()
        
        logger.info("🚀 Enhanced User Onboarding System initialized")
    
    def _create_onboarding_flow(self) -> Dict[str, OnboardingStep]:
        """Create the complete onboarding flow"""
        return {
            'welcome': OnboardingStep(
                step_id='welcome',
                title='Welcome',
                description='Initial welcome message',
                message="""👋 **Welcome to your Personal AI Memory Assistant!**

I'm your advanced memory companion, designed to help you remember everything important in your life.

🧠 **What I can do:**
• Monitor and organize your conversations intelligently
• Create secure memory files for different aspects of your life
• Remind you about important events and tasks
• Learn your preferences and adapt to your needs
• Protect sensitive information with advanced security

Let's get you set up! First, I'd like to know your name.

**Please tell me what you'd like me to call you:**""",
                expected_responses=['name'],
                next_step='profile_setup'
            ),
            
            'profile_setup': OnboardingStep(
                step_id='profile_setup',
                title='Profile Setup',
                description='Collect basic profile information',
                message="""Great to meet you, {name}! 👋

Now let's set up your profile. I'll create your personal memory files and organize them securely.

**Tell me a bit about yourself:**
• What's your timezone? (e.g., UTC, EST, PST)
• What language do you prefer? (e.g., English, Spanish, French)
• Any specific preferences for how I should communicate with you?

You can share this information in any format - I'll understand! 😊""",
                expected_responses=['profile_info'],
                next_step='preferences_setup'
            ),
            
            'preferences_setup': OnboardingStep(
                step_id='preferences_setup',
                title='Preferences Setup',
                description='Configure memory and communication preferences',
                message="""Perfect! I'm learning about your preferences. 📝

Now, let's configure how I should handle your memories:

**Memory Organization Preferences:**
1. **Automatic Classification** - Should I automatically categorize your messages?
2. **Daily Summaries** - Would you like daily memory summaries?
3. **Proactive Reminders** - Should I remind you about important things?
4. **Contact Tracking** - Should I remember details about people you mention?

**Please respond with:**
• "Yes to all" - Enable all features
• "Custom" - Let me choose specific features
• "Minimal" - Basic features only

What would you prefer?""",
                expected_responses=['yes to all', 'custom', 'minimal'],
                next_step='contacts_setup'
            ),
            
            'contacts_setup': OnboardingStep(
                step_id='contacts_setup',
                title='Contacts Setup',
                description='Set up contact management',
                message="""Excellent! Your preferences are saved. 👥

Let's set up contact management. I can create separate memory files for important people in your life.

**Would you like to add some key contacts now?**

You can mention people like:
• Family members (Mom, Dad, Sister, etc.)
• Close friends
• Work colleagues
• Anyone else important to you

**Examples:**
• "Add Mom, Dad, and my brother John"
• "Track my colleagues Sarah and Mike"
• "Remember my friend Lisa and my boss David"

**Or say "Skip" to do this later.**""",
                expected_responses=['contacts', 'skip'],
                next_step='security_setup'
            ),
            
            'security_setup': OnboardingStep(
                step_id='security_setup',
                title='Security Setup',
                description='Configure security and privacy settings',
                message="""Great! Your contacts are being set up. 🔐

Now for the important part - **Security & Privacy**.

I use different security levels for your memories:
• **General** - Basic information, easily accessible
• **Confidential** - Private info, standard security
• **Secret** - Sensitive info, elevated security
• **Ultra-Secret** - Maximum security, special authentication

**Security Options:**
1. **Standard** - Basic security for most users
2. **Enhanced** - Additional encryption and access controls
3. **Maximum** - Highest security with biometric/voice authentication

**Which security level do you prefer?**
• Type "Standard", "Enhanced", or "Maximum"
• Or ask me to explain the differences""",
                expected_responses=['standard', 'enhanced', 'maximum', 'explain'],
                next_step='permission_request'
            ),
            
            'permission_request': OnboardingStep(
                step_id='permission_request',
                title='Permission Request',
                description='Request monitoring permissions',
                message="""Perfect! Your security settings are configured. ✅

**Final Step: Monitoring Permission**

To provide the best experience, I'd like permission to:
• Monitor your conversations for important information
• Automatically create and update your memory files
• Send you proactive reminders and summaries
• Learn from your communication patterns

**Your privacy is guaranteed:**
• All data is encrypted and stored securely
• You control what I remember and forget
• You can revoke permissions anytime
• No data is shared with third parties

**Grant permission?**
• **"YES"** - Enable full features
• **"NO"** - Use basic features only
• **"HELP"** - Learn more about privacy""",
                expected_responses=['yes', 'no', 'help'],
                next_step='completion'
            ),
            
            'completion': OnboardingStep(
                step_id='completion',
                title='Onboarding Complete',
                description='Complete the onboarding process',
                message="""🎉 **Welcome aboard, {name}!**

Your Personal AI Memory Assistant is now ready!

**What's been set up:**
✅ Personal memory files created
✅ Security preferences configured
✅ Contact tracking enabled
✅ Preferences saved
✅ Monitoring permissions set

**Quick Start Guide:**
• Send me any message to store as a memory
• Ask me to remind you about anything
• I'll automatically organize important information
• Use commands like /daily_review, /search, /profile

**Try saying:**
• "Remember that Mom's birthday is June 15th"
• "What did I discuss with John yesterday?"
• "Remind me to call the dentist tomorrow"

I'm here to help you remember everything important! 🧠✨

**What would you like me to help you remember first?**""",
                expected_responses=['anything'],
                completion_action='complete_onboarding'
            )
        }
    
    def load_user_states(self):
        """Load saved user onboarding states"""
        state_file = self.data_dir / "enhanced_user_states.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    self.user_states = json.load(f)
                logger.info(f"📂 Loaded {len(self.user_states)} enhanced user states")
            except Exception as e:
                logger.error(f"Failed to load enhanced user states: {e}")
                self.user_states = {}
    
    def save_user_states(self):
        """Save user onboarding states"""
        state_file = self.data_dir / "enhanced_user_states.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(self.user_states, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save enhanced user states: {e}")
    
    async def is_new_user(self, phone_number: str) -> bool:
        """Check if this is a new user"""
        # Check our enhanced onboarding states
        if phone_number in self.user_states:
            return False
        
        # Check if user has existing MD files
        user_file_path = self.md_file_manager._get_user_file_path(phone_number)
        if user_file_path.exists():
            # Existing user but not in our tracking
            self.user_states[phone_number] = {
                'state': self.STATES['ONBOARDING_COMPLETE'],
                'current_step': 'completion',
                'joined_at': datetime.now().isoformat(),
                'last_interaction': datetime.now().isoformat(),
                'profile': {},
                'preferences': {},
                'contacts': [],
                'security_level': 'standard'
            }
            self.save_user_states()
            return False
        
        return True
    
    async def register_new_user(self, phone_number: str, initial_message: str = None) -> Dict[str, Any]:
        """Register a new user and start onboarding"""
        logger.info(f"🆕 Registering new user: {phone_number}")
        
        try:
            # Create user state
            self.user_states[phone_number] = {
                'state': self.STATES['NEW'],
                'current_step': 'welcome',
                'joined_at': datetime.now().isoformat(),
                'last_interaction': datetime.now().isoformat(),
                'profile': {},
                'preferences': {},
                'contacts': [],
                'security_level': 'standard',
                'onboarding_data': {},
                'step_history': []
            }
            
            # Send welcome message
            welcome_result = await self.send_onboarding_message(phone_number, 'welcome')
            
            # Update state
            if welcome_result['success']:
                self.user_states[phone_number]['state'] = self.STATES['PROFILE_SETUP']
                self.user_states[phone_number]['step_history'].append({
                    'step': 'welcome',
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                })
            
            self.save_user_states()
            
            return {
                'success': True,
                'message': f'New user {phone_number} registered and onboarding started',
                'welcome_sent': welcome_result['success']
            }
            
        except Exception as e:
            logger.error(f"Failed to register new user {phone_number}: {e}")
            return {
                'success': False,
                'message': f'Failed to register user: {str(e)}',
                'error': str(e)
            }
    
    async def send_onboarding_message(self, phone_number: str, step_id: str) -> Dict[str, Any]:
        """Send onboarding message for specific step"""
        try:
            if step_id not in self.onboarding_steps:
                return {'success': False, 'message': 'Invalid step ID'}
            
            step = self.onboarding_steps[step_id]
            user_state = self.user_states.get(phone_number, {})
            
            # Format message with user data
            message = step.message
            if '{name}' in message:
                name = user_state.get('profile', {}).get('name', 'there')
                message = message.format(name=name)
            
            # Send via available channels
            success = False
            
            if self.whatsapp_bot:
                result = await self.whatsapp_bot.send_proactive_message(
                    phone_number=phone_number,
                    message=message
                )
                success = result.get('success', False)
            
            if not success and self.telegram_bot:
                # Try Telegram as fallback
                result = await self.telegram_bot.send_message(
                    phone_number=phone_number,
                    message=message
                )
                success = result.get('success', False)
            
            if success:
                logger.info(f"📤 Sent onboarding step '{step_id}' to {phone_number}")
            
            return {
                'success': success,
                'step_id': step_id,
                'message': 'Onboarding message sent' if success else 'Failed to send message'
            }
            
        except Exception as e:
            logger.error(f"Failed to send onboarding message: {e}")
            return {
                'success': False,
                'message': f'Failed to send onboarding message: {str(e)}',
                'error': str(e)
            }
    
    async def handle_onboarding_response(self, phone_number: str, response: str) -> Dict[str, Any]:
        """Handle user's response during onboarding"""
        try:
            if phone_number not in self.user_states:
                # New user, start onboarding
                await self.register_new_user(phone_number, response)
                return {'response': self.onboarding_steps['welcome'].message}
            
            user_state = self.user_states[phone_number]
            current_step_id = user_state.get('current_step', 'welcome')
            
            if current_step_id not in self.onboarding_steps:
                # Invalid step, reset to welcome
                current_step_id = 'welcome'
                user_state['current_step'] = current_step_id
            
            current_step = self.onboarding_steps[current_step_id]
            
            # Process response based on current step
            processing_result = await self._process_step_response(
                phone_number, current_step_id, response
            )
            
            if processing_result['success']:
                # Move to next step
                next_step_id = processing_result.get('next_step')
                if next_step_id and next_step_id in self.onboarding_steps:
                    user_state['current_step'] = next_step_id
                    user_state['last_interaction'] = datetime.now().isoformat()
                    
                    # Add to step history
                    user_state['step_history'].append({
                        'step': current_step_id,
                        'response': response,
                        'timestamp': datetime.now().isoformat(),
                        'success': True
                    })
                    
                    self.save_user_states()
                    
                    # Send next step message
                    if next_step_id == 'completion':
                        # Complete onboarding
                        await self._complete_onboarding(phone_number)
                    
                    next_message_result = await self.send_onboarding_message(phone_number, next_step_id)
                    
                    return {
                        'response': processing_result.get('response', ''),
                        'next_step': next_step_id,
                        'onboarding_complete': next_step_id == 'completion'
                    }
                else:
                    # Onboarding complete
                    await self._complete_onboarding(phone_number)
                    return {
                        'response': processing_result.get('response', ''),
                        'onboarding_complete': True
                    }
            else:
                # Handle error or retry
                return {
                    'response': processing_result.get('response', 'I didn\'t understand that. Could you please try again?'),
                    'retry': True
                }
            
        except Exception as e:
            logger.error(f"Failed to handle onboarding response: {e}")
            return {
                'response': 'Sorry, there was an error processing your response. Let me help you continue.',
                'error': str(e)
            }
    
    async def _process_step_response(self, phone_number: str, step_id: str, response: str) -> Dict[str, Any]:
        """Process user response for specific onboarding step"""
        user_state = self.user_states[phone_number]
        response_lower = response.lower().strip()
        
        try:
            if step_id == 'welcome':
                # Extract name from response
                name = self._extract_name(response)
                user_state['profile']['name'] = name
                
                return {
                    'success': True,
                    'next_step': 'profile_setup',
                    'response': f"Nice to meet you, {name}!"
                }
            
            elif step_id == 'profile_setup':
                # Extract profile information
                profile_info = await self._extract_profile_info(response)
                user_state['profile'].update(profile_info)
                
                return {
                    'success': True,
                    'next_step': 'preferences_setup',
                    'response': "Thanks! I've saved your profile information."
                }
            
            elif step_id == 'preferences_setup':
                # Handle preference selection
                if 'yes to all' in response_lower:
                    user_state['preferences'] = {
                        'automatic_classification': True,
                        'daily_summaries': True,
                        'proactive_reminders': True,
                        'contact_tracking': True
                    }
                    response_msg = "Perfect! All features enabled."
                elif 'minimal' in response_lower:
                    user_state['preferences'] = {
                        'automatic_classification': False,
                        'daily_summaries': False,
                        'proactive_reminders': False,
                        'contact_tracking': False
                    }
                    response_msg = "Got it! Minimal features selected."
                else:
                    # Custom or default
                    user_state['preferences'] = {
                        'automatic_classification': True,
                        'daily_summaries': True,
                        'proactive_reminders': True,
                        'contact_tracking': True
                    }
                    response_msg = "I'll use smart defaults for now. You can change these later."
                
                return {
                    'success': True,
                    'next_step': 'contacts_setup',
                    'response': response_msg
                }
            
            elif step_id == 'contacts_setup':
                # Extract contacts
                if 'skip' not in response_lower:
                    contacts = self._extract_contacts(response)
                    user_state['contacts'] = contacts
                    response_msg = f"Great! I'll track {len(contacts)} contacts for you."
                else:
                    response_msg = "No problem! You can add contacts later."
                
                return {
                    'success': True,
                    'next_step': 'security_setup',
                    'response': response_msg
                }
            
            elif step_id == 'security_setup':
                # Handle security level selection
                if 'standard' in response_lower:
                    user_state['security_level'] = 'standard'
                    response_msg = "Standard security configured."
                elif 'enhanced' in response_lower:
                    user_state['security_level'] = 'enhanced'
                    response_msg = "Enhanced security configured."
                elif 'maximum' in response_lower:
                    user_state['security_level'] = 'maximum'
                    response_msg = "Maximum security configured."
                elif 'explain' in response_lower:
                    return {
                        'success': False,
                        'response': self._get_security_explanation()
                    }
                else:
                    user_state['security_level'] = 'standard'
                    response_msg = "I'll use standard security for now."
                
                return {
                    'success': True,
                    'next_step': 'permission_request',
                    'response': response_msg
                }
            
            elif step_id == 'permission_request':
                # Handle permission response
                if response_lower == 'yes':
                    user_state['permissions_granted'] = True
                    user_state['state'] = self.STATES['PERMISSION_GRANTED']
                    response_msg = "Perfect! Full features enabled."
                elif response_lower == 'help':
                    return {
                        'success': False,
                        'response': self._get_privacy_explanation()
                    }
                else:
                    user_state['permissions_granted'] = False
                    user_state['state'] = self.STATES['PERMISSION_DENIED']
                    response_msg = "No problem! Basic features are still available."
                
                return {
                    'success': True,
                    'next_step': 'completion',
                    'response': response_msg
                }
            
            else:
                return {
                    'success': False,
                    'response': 'Unknown onboarding step.'
                }
                
        except Exception as e:
            logger.error(f"Failed to process step response: {e}")
            return {
                'success': False,
                'response': 'There was an error processing your response. Please try again.'
            }
    
    async def _complete_onboarding(self, phone_number: str) -> Dict[str, Any]:
        """Complete the onboarding process"""
        try:
            user_state = self.user_states[phone_number]
            
            # Create MD files
            profile_data = user_state.get('profile', {})
            preferences = user_state.get('preferences', {})
            contacts = user_state.get('contacts', [])
            
            # Create user MD file
            md_result = await self.md_file_manager.create_user_file(
                phone_number=phone_number,
                name=profile_data.get('name'),
                initial_data={
                    'preferences': preferences,
                    'security_level': user_state.get('security_level', 'standard'),
                    'onboarding_completed': datetime.now().isoformat()
                }
            )
            
            # Create contact files
            for contact in contacts:
                await self.md_file_manager.create_contact_file(
                    contact_name=contact,
                    user_phone=phone_number,
                    initial_info={'relationship': 'Added during onboarding'}
                )
            
            # Update user state
            user_state['state'] = self.STATES['ONBOARDING_COMPLETE']
            user_state['onboarding_completed_at'] = datetime.now().isoformat()
            user_state['md_files_created'] = md_result['success']
            
            self.save_user_states()
            
            logger.info(f"✅ Onboarding completed for {phone_number}")
            
            return {
                'success': True,
                'message': 'Onboarding completed successfully',
                'md_files_created': md_result['success'],
                'contacts_created': len(contacts)
            }
            
        except Exception as e:
            logger.error(f"Failed to complete onboarding: {e}")
            return {
                'success': False,
                'message': f'Failed to complete onboarding: {str(e)}',
                'error': str(e)
            }
    
    def _extract_name(self, response: str) -> str:
        """Extract name from user response"""
        # Simple name extraction - can be enhanced
        response = response.strip()
        
        # Remove common prefixes
        prefixes = ['my name is', 'i am', 'i\'m', 'call me', 'name:', 'hi', 'hello']
        response_lower = response.lower()
        
        for prefix in prefixes:
            if response_lower.startswith(prefix):
                response = response[len(prefix):].strip()
                break
        
        # Take first word as name (can be enhanced for full names)
        name = response.split()[0] if response.split() else 'User'
        
        # Capitalize first letter
        return name.capitalize()
    
    async def _extract_profile_info(self, response: str) -> Dict[str, Any]:
        """Extract profile information from user response"""
        # Use conversation classifier to extract entities
        context = ConversationContext(
            user_phone="onboarding",
            conversation_history=[],
            known_contacts=[],
            recent_topics=[]
        )
        
        classification = await self.conversation_classifier.classify_message(response, context)
        entities = classification.extracted_entities
        
        profile_info = {}
        
        # Extract timezone
        timezone_keywords = ['utc', 'est', 'pst', 'cst', 'mst', 'gmt']
        for keyword in timezone_keywords:
            if keyword in response.lower():
                profile_info['timezone'] = keyword.upper()
                break
        
        # Extract language
        language_keywords = ['english', 'spanish', 'french', 'german', 'italian']
        for keyword in language_keywords:
            if keyword in response.lower():
                profile_info['language'] = keyword.capitalize()
                break
        
        # Default values
        if 'timezone' not in profile_info:
            profile_info['timezone'] = 'UTC'
        if 'language' not in profile_info:
            profile_info['language'] = 'English'
        
        return profile_info
    
    def _extract_contacts(self, response: str) -> List[str]:
        """Extract contact names from user response"""
        # Simple contact extraction
        contacts = []
        
        # Common relationship terms
        relationships = {
            'mom': 'Mom',
            'mother': 'Mom',
            'dad': 'Dad',
            'father': 'Dad',
            'sister': 'Sister',
            'brother': 'Brother',
            'wife': 'Wife',
            'husband': 'Husband',
            'boss': 'Boss',
            'colleague': 'Colleague'
        }
        
        response_lower = response.lower()
        
        # Look for relationship terms
        for term, formal_name in relationships.items():
            if term in response_lower:
                contacts.append(formal_name)
        
        # Look for proper names (capitalized words)
        words = response.split()
        for word in words:
            if word.isalpha() and word[0].isupper() and len(word) > 1:
                if word not in ['Add', 'Track', 'Remember', 'My', 'The', 'And']:
                    contacts.append(word)
        
        return list(set(contacts))  # Remove duplicates
    
    def _get_security_explanation(self) -> str:
        """Get detailed security explanation"""
        return """🔐 **Security Level Details:**

**Standard Security:**
• Basic encryption for all data
• Standard access controls
• Suitable for most users
• Quick and easy access

**Enhanced Security:**
• Advanced encryption algorithms
• Multi-layer access controls
• Additional authentication steps
• Audit logging of all access

**Maximum Security:**
• Military-grade encryption
• Biometric authentication required
• Voice recognition for ultra-secret data
• Complete access logging and monitoring
• Suitable for highly sensitive information

**Which level would you prefer?** (Standard/Enhanced/Maximum)"""
    
    def _get_privacy_explanation(self) -> str:
        """Get detailed privacy explanation"""
        return """🔒 **Privacy & Security Details:**

**What I Monitor:**
• Only messages you send to me directly
• Conversations where you explicitly mention me
• Information you ask me to remember

**What I DON'T Do:**
• Read private conversations without permission
• Share your data with anyone
• Store data on external servers without encryption
• Access your device beyond our conversation

**Your Control:**
• Delete any memory anytime with /forget
• View all stored data with /export
• Change permissions anytime with /settings
• Complete data deletion with /delete_all

**Security Measures:**
• End-to-end encryption
• Local data storage
• No third-party access
• Regular security audits

**Ready to enable full features?** (YES/NO)"""
    
    async def get_onboarding_stats(self) -> Dict[str, Any]:
        """Get onboarding statistics"""
        total_users = len(self.user_states)
        
        if total_users == 0:
            return {
                'total_users': 0,
                'completion_rate': 0,
                'step_distribution': {},
                'average_completion_time': 0
            }
        
        # Analyze user states
        completed = 0
        step_counts = {}
        completion_times = []
        
        for user_state in self.user_states.values():
            current_step = user_state.get('current_step', 'unknown')
            step_counts[current_step] = step_counts.get(current_step, 0) + 1
            
            if user_state.get('state') == self.STATES['ONBOARDING_COMPLETE']:
                completed += 1
                
                # Calculate completion time
                joined = datetime.fromisoformat(user_state['joined_at'])
                completed_at = user_state.get('onboarding_completed_at')
                if completed_at:
                    completed_time = datetime.fromisoformat(completed_at)
                    duration = (completed_time - joined).total_seconds() / 60  # minutes
                    completion_times.append(duration)
        
        return {
            'total_users': total_users,
            'completed_users': completed,
            'completion_rate': (completed / total_users) * 100,
            'step_distribution': step_counts,
            'average_completion_time': sum(completion_times) / len(completion_times) if completion_times else 0
        }

# Example usage and testing
async def main():
    """Test the enhanced user onboarding"""
    onboarding = EnhancedUserOnboarding()
    
    # Test new user registration
    result = await onboarding.register_new_user("+1234567890")
    print("Registration:", result)
    
    # Test onboarding responses
    test_responses = [
        "My name is John",
        "I'm in EST timezone and prefer English",
        "Yes to all",
        "Add Mom, Dad, and my friend Sarah",
        "Enhanced",
        "YES"
    ]
    
    for response in test_responses:
        result = await onboarding.handle_onboarding_response("+1234567890", response)
        print(f"Response '{response}': {result}")
    
    # Get stats
    stats = await onboarding.get_onboarding_stats()
    print("Onboarding Stats:", stats)

if __name__ == "__main__":
    asyncio.run(main())

