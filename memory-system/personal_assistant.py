#!/usr/bin/env python3
"""
Personal Assistant - Intelligent Conversation Agent
Learns about users and maintains personal profiles in MD files
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
import re

# Import Phone Directory for cross-profile memory management
from phone_directory import PhoneDirectory

# Import new Phase 2 components
try:
    from md_file_manager import MDFileManager, MemoryTag, MemoryEntry, UserProfile
    MD_MANAGER_AVAILABLE = True
except ImportError:
    MD_MANAGER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("MDFileManager not available")

try:
    from conversation_classifier import ConversationClassifier, ConversationContext
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("ConversationClassifier not available")

# Import AI services
try:
    from anthropic import AsyncAnthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class PersonalAssistant:
    """Personal AI Assistant that maintains user profiles and conversations"""
    
    def __init__(self):
        """Initialize the Personal Assistant"""
        self.profiles_dir = Path("memory-system/user_profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Phone Directory for cross-profile memory management
        self.phone_directory = PhoneDirectory(data_dir="memory-system/data")
        
        # Initialize Phase 2 components
        self.md_file_manager = None
        self.conversation_classifier = None
        
        if MD_MANAGER_AVAILABLE:
            self.md_file_manager = MDFileManager(base_dir="memory-system/users")
            logger.info("📂 MDFileManager initialized for advanced memory management")
        
        if CLASSIFIER_AVAILABLE:
            self.conversation_classifier = ConversationClassifier()
            logger.info("🧠 ConversationClassifier initialized for intelligent message processing")
        
        # Initialize AI clients
        self.claude_client = None
        self.openai_client = None
        
        if CLAUDE_AVAILABLE and os.environ.get('ANTHROPIC_API_KEY'):
            self.claude_client = AsyncAnthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
            logger.info("🤖 Claude AI initialized for Personal Assistant")
        
        if OPENAI_AVAILABLE and os.environ.get('OPENAI_API_KEY'):
            self.openai_client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            logger.info("🧠 OpenAI initialized for Personal Assistant")
        
        self.active_conversations = {}
        logger.info("🎯 Personal Assistant initialized")
    
    def _get_profile_path(self, phone_number: str) -> Path:
        """Get the MD file path for a user's profile"""
        # Clean phone number (remove + and spaces)
        clean_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        return self.profiles_dir / f"profile_{clean_number}.md"
    
    def _load_user_profile(self, phone_number: str) -> Dict[str, Any]:
        """Load user profile from MD file"""
        profile_path = self._get_profile_path(phone_number)
        
        if not profile_path.exists():
            # Create new profile
            return {
                'phone_number': phone_number,
                'name': None,
                'created_at': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'personal_info': {},
                'preferences': {},
                'conversation_history': [],
                'memories': [],
                'relationships': {},
                'interests': [],
                'important_dates': {},
                'notes': [],
                'shared_memories': []  # Memories added by others
            }
        
        # Parse existing MD file
        with open(profile_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON data from MD file
        profile = {}
        if '<!-- PROFILE_DATA_START -->' in content:
            start = content.find('<!-- PROFILE_DATA_START -->') + len('<!-- PROFILE_DATA_START -->')
            end = content.find('<!-- PROFILE_DATA_END -->')
            if end != -1:
                json_str = content[start:end].strip()
                try:
                    profile = json.loads(json_str)
                except:
                    logger.error(f"Failed to parse profile JSON for {phone_number}")
        
        return profile
    
    def _save_user_profile(self, phone_number: str, profile: Dict[str, Any]):
        """Save user profile to MD file"""
        profile_path = self._get_profile_path(phone_number)
        
        # Update last seen
        profile['last_seen'] = datetime.now().isoformat()
        
        # Create beautiful MD file
        md_content = f"""# User Profile: {profile.get('name', 'Unknown')}

## 📱 Contact Information
- **Phone**: {phone_number}
- **Name**: {profile.get('name', 'Not provided')}
- **First Contact**: {profile.get('created_at', 'Unknown')}
- **Last Seen**: {profile.get('last_seen', 'Unknown')}

## 👤 Personal Information
"""
        
        for key, value in profile.get('personal_info', {}).items():
            md_content += f"- **{key.title()}**: {value}\n"
        
        if profile.get('interests'):
            md_content += "\n## 🎯 Interests & Hobbies\n"
            for interest in profile['interests']:
                md_content += f"- {interest}\n"
        
        if profile.get('relationships'):
            md_content += "\n## 👨‍👩‍👧‍👦 Relationships\n"
            for person, relationship in profile['relationships'].items():
                md_content += f"- **{person}**: {relationship}\n"
        
        if profile.get('important_dates'):
            md_content += "\n## 📅 Important Dates\n"
            for date_name, date_value in profile['important_dates'].items():
                md_content += f"- **{date_name}**: {date_value}\n"
        
        if profile.get('preferences'):
            md_content += "\n## ⚙️ Preferences\n"
            for pref_key, pref_value in profile['preferences'].items():
                md_content += f"- **{pref_key}**: {pref_value}\n"
        
        # Add recent conversations
        md_content += "\n## 💬 Recent Conversations\n"
        recent_convos = profile.get('conversation_history', [])[-10:]  # Last 10
        for conv in recent_convos:
            md_content += f"\n### {conv.get('timestamp', 'Unknown time')}\n"
            md_content += f"**You**: {conv.get('user_message', '')}\n\n"
            md_content += f"**Assistant**: {conv.get('assistant_response', '')}\n"
        
        # Add memories
        if profile.get('memories'):
            md_content += "\n## 🧠 Memories\n"
            for memory in profile['memories'][-20:]:  # Last 20 memories
                md_content += f"- [{memory.get('date', '')}] {memory.get('content', '')}\n"
        
        # Add notes
        if profile.get('notes'):
            md_content += "\n## 📝 Notes\n"
            for note in profile['notes']:
                md_content += f"- {note}\n"
        
        # Add shared memories (memories added by others)
        if profile.get('shared_memories'):
            md_content += "\n## 🤝 Shared Memories (Added by Others)\n"
            for shared_mem in profile['shared_memories'][-20:]:  # Last 20 shared memories
                source_name = shared_mem.get('source_name', 'Someone')
                md_content += f"- [{shared_mem.get('date', '')}] **From {source_name}**: {shared_mem.get('content', '')}\n"
        
        # Embed JSON data for easy parsing
        md_content += f"\n\n<!-- PROFILE_DATA_START -->\n{json.dumps(profile, indent=2)}\n<!-- PROFILE_DATA_END -->\n"
        
        # Save to file
        with open(profile_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"💾 Saved profile for {profile.get('name', phone_number)}")
    
    async def process_message(self, phone_number: str, message: str, user_name: Optional[str] = None) -> str:
        """Process a message and generate an intelligent response"""
        
        # Load user profile
        profile = self._load_user_profile(phone_number)
        
        # Update name if provided
        if user_name and not profile.get('name'):
            profile['name'] = user_name
        
        # Check for cross-profile memory commands
        cross_profile_result = await self._check_and_handle_cross_profile_memory(phone_number, message, profile)
        if cross_profile_result:
            # Save the user's profile (may have been updated with contact info)
            self._save_user_profile(phone_number, profile)
            return cross_profile_result
        
        # Extract information from message
        self._extract_information(message, profile)
        
        # Generate contextual response
        response = await self._generate_response(message, profile)
        
        # Add to conversation history
        profile['conversation_history'].append({
            'timestamp': datetime.now().isoformat(),
            'user_message': message,
            'assistant_response': response
        })
        
        # Keep only last 100 conversations
        if len(profile['conversation_history']) > 100:
            profile['conversation_history'] = profile['conversation_history'][-100:]
        
        # Save updated profile
        self._save_user_profile(phone_number, profile)
        
        return response
    
    def _extract_information(self, message: str, profile: Dict[str, Any]):
        """Extract and store information from user messages"""
        message_lower = message.lower()
        
        # Extract name
        if 'my name is' in message_lower or "i'm " in message_lower or 'i am ' in message_lower:
            if 'my name is' in message_lower:
                name = message.split('my name is', 1)[1].split('.')[0].strip()
                profile['name'] = name.title()
            elif "i'm " in message_lower:
                name = message.split("i'm ", 1)[1].split('.')[0].split(',')[0].strip()
                if len(name.split()) <= 3:  # Likely a name
                    profile['name'] = name.title()
            elif 'i am ' in message_lower:
                name = message.split("i am ", 1)[1].split('.')[0].split(',')[0].strip()
                if len(name.split()) <= 3:  # Likely a name
                    profile['name'] = name.title()
        
        # Extract location
        if 'i live in' in message_lower or "i'm from" in message_lower or 'i am from' in message_lower:
            if 'i live in' in message_lower:
                location = message.split('i live in', 1)[1].split('.')[0].strip()
                profile['personal_info']['location'] = location.title()
            elif "i'm from" in message_lower:
                location = message.split("i'm from", 1)[1].split('.')[0].strip()
                profile['personal_info']['origin'] = location.title()
            elif 'i am from' in message_lower:
                location = message.split('i am from', 1)[1].split('.')[0].strip()
                profile['personal_info']['origin'] = location.title()
        
        # Extract relationships
        if 'my wife' in message_lower or 'my husband' in message_lower or 'my mother' in message_lower or 'my father' in message_lower:
            if 'my wife' in message_lower:
                wife_context = message.split('my wife', 1)[1].split('.')[0]
                if 'name' in wife_context or 'is' in wife_context:
                    profile['relationships']['wife'] = wife_context.strip()
            if 'my husband' in message_lower:
                husband_context = message.split('my husband', 1)[1].split('.')[0]
                if 'name' in husband_context or 'is' in husband_context:
                    profile['relationships']['husband'] = husband_context.strip()
        
        # Extract interests
        if 'i like' in message_lower or 'i love' in message_lower or 'i enjoy' in message_lower:
            for phrase in ['i like', 'i love', 'i enjoy']:
                if phrase in message_lower:
                    interest = message_lower.split(phrase, 1)[1].split('.')[0].split(',')[0].strip()
                    if interest and interest not in profile['interests']:
                        profile['interests'].append(interest)
        
        # Store as memory if it seems important
        keywords = ['remember', 'don\'t forget', 'important', 'birthday', 'anniversary', 'meeting', 'appointment']
        if any(keyword in message_lower for keyword in keywords):
            profile['memories'].append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'content': message
            })
    
    async def _generate_response(self, message: str, profile: Dict[str, Any]) -> str:
        """Generate an intelligent, contextual response"""
        
        # Build context from profile
        context = self._build_context(profile)
        
        # Create system prompt
        system_prompt = f"""You are a personal AI assistant having a conversation with {profile.get('name', 'a user')}.
You know the following about them:
{context}

Your personality:
- Friendly, warm, and genuinely interested in the person
- Remember previous conversations and reference them naturally
- Ask follow-up questions to learn more about them
- Be helpful and proactive in offering assistance
- Use a conversational, natural tone
- Show empathy and understanding

Important: 
- Keep responses concise (2-3 sentences usually)
- Be specific and personal based on what you know
- If they're sharing something new, acknowledge it and show interest
- If they need help, be practical and actionable"""
        
        # Try Claude first
        if self.claude_client:
            try:
                response = await self.claude_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_completion_tokens=200,
                    system=system_prompt,
                    messages=[{"role": "user", "content": message}]
                )
                return response.content[0].text
            except Exception as e:
                logger.error(f"Claude API error: {e}")
        
        # Fallback to OpenAI
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    max_completion_tokens=200,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
        
        # Fallback to rule-based response
        return self._generate_fallback_response(message, profile)
    
    def _build_context(self, profile: Dict[str, Any]) -> str:
        """Build context string from user profile"""
        context_parts = []
        
        if profile.get('name'):
            context_parts.append(f"Name: {profile['name']}")
        
        if profile.get('personal_info'):
            for key, value in profile['personal_info'].items():
                context_parts.append(f"{key.title()}: {value}")
        
        if profile.get('interests'):
            context_parts.append(f"Interests: {', '.join(profile['interests'][:5])}")
        
        if profile.get('relationships'):
            rel_str = ", ".join([f"{person} ({rel})" for person, rel in list(profile['relationships'].items())[:3]])
            context_parts.append(f"Important people: {rel_str}")
        
        # Add recent conversation summary
        if profile.get('conversation_history'):
            recent = profile['conversation_history'][-3:]
            if recent:
                context_parts.append("\nRecent conversations:")
                for conv in recent:
                    context_parts.append(f"- They said: {conv['user_message'][:50]}...")
        
        return "\n".join(context_parts) if context_parts else "No previous information"
    
    def _generate_fallback_response(self, message: str, profile: Dict[str, Any]) -> str:
        """Generate a simple fallback response when AI is not available"""
        message_lower = message.lower()
        name = profile.get('name', 'there')
        
        # Greetings
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            if profile.get('name'):
                return f"Hello {name}! Great to hear from you again. How can I help you today?"
            return "Hello! I'm your personal assistant. What's your name?"
        
        # Name introduction
        if 'my name is' in message_lower or "i'm " in message_lower:
            return f"Nice to meet you, {profile.get('name', 'friend')}! I'll remember that. Tell me more about yourself!"
        
        # Questions
        if message_lower.startswith(('what', 'when', 'where', 'who', 'how', 'why')):
            return f"That's a great question, {name}. Let me help you with that. Could you provide a bit more context?"
        
        # Memory storage
        if 'remember' in message_lower:
            return "I've made a note of that! I'll remember it for you."
        
        # Default
        interests = profile.get('interests', [])
        if interests:
            return f"Interesting! I remember you enjoy {interests[0]}. How's that going?"
        
        return f"Thanks for sharing that with me, {name}. Tell me more!"
    
    async def _check_and_handle_cross_profile_memory(self, sender_phone: str, message: str, sender_profile: Dict[str, Any]) -> Optional[str]:
        """
        Check if message is a cross-profile memory command and handle it
        
        Returns:
            Response string if handled, None if not a cross-profile command
        """
        # Define patterns for cross-profile memory commands
        patterns = [
            r"^(?:add memory to|remember for|note for)\s+([^:]+):\s*(.+)$",
            r"^tell\s+([^:]+)\s+to remember:\s*(.+)$",
            r"^remind\s+([^:]+):\s*(.+)$"
        ]
        
        message_lower = message.lower().strip()
        
        for pattern in patterns:
            match = re.match(pattern, message_lower, re.IGNORECASE)
            if match:
                target_name = match.group(1).strip()
                memory_content = match.group(2).strip()
                
                # Try to add the cross-profile memory
                result = await self.add_cross_profile_memory(
                    sender_phone=sender_phone,
                    sender_profile=sender_profile,
                    target_name=target_name,
                    memory_content=memory_content
                )
                
                return result
        
        return None
    
    async def add_cross_profile_memory(self, sender_phone: str, sender_profile: Dict[str, Any], 
                                      target_name: str, memory_content: str) -> str:
        """
        Add a memory to another person's profile
        
        Args:
            sender_phone: Phone number of the person adding the memory
            sender_profile: Profile of the sender
            target_name: Name or relationship of the target person
            memory_content: The memory to add
        
        Returns:
            Confirmation message or error message
        """
        sender_name = sender_profile.get('name', 'Unknown')
        
        # Check if target is a relationship keyword (wife, husband, mother, etc.)
        relationship_keywords = ['wife', 'husband', 'mother', 'father', 'dad', 'mom', 
                               'brother', 'sister', 'friend', 'colleague', 'boss']
        
        target_phone = None
        
        # First, try to find the contact in the phone directory
        target_phone = self.phone_directory.find_phone_by_name(sender_phone, target_name)
        
        if not target_phone:
            # Check if it's a relationship keyword
            for keyword in relationship_keywords:
                if keyword in target_name.lower():
                    # Look for contacts with this relationship
                    contacts = self.phone_directory.find_contacts_by_relationship(sender_phone, keyword)
                    if contacts:
                        target_phone = contacts[0]['phone']
                        target_name = contacts[0]['name']
                        break
        
        if not target_phone:
            # Contact not found - suggest registering them
            return (f"❌ I couldn't find '{target_name}' in your contacts.\n\n"
                   f"To add them, please send:\n"
                   f"'Register contact {target_name}: [phone number] as [relationship]'\n\n"
                   f"Example: 'Register contact Elena: +40744123456 as wife'")
        
        # Load the target's profile
        target_profile = self._load_user_profile(target_phone)
        
        # Initialize shared_memories if not present
        if 'shared_memories' not in target_profile:
            target_profile['shared_memories'] = []
        
        # Add the memory to the target's profile
        shared_memory = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'content': memory_content,
            'source_phone': sender_phone,
            'source_name': sender_name
        }
        
        target_profile['shared_memories'].append(shared_memory)
        
        # Keep only last 100 shared memories
        if len(target_profile['shared_memories']) > 100:
            target_profile['shared_memories'] = target_profile['shared_memories'][-100:]
        
        # Save the target's updated profile
        self._save_user_profile(target_phone, target_profile)
        
        # Log the action
        logger.info(f"📝 {sender_name} ({sender_phone}) added memory to {target_name} ({target_phone}): {memory_content}")
        
        # Return confirmation
        target_display_name = target_profile.get('name', target_name)
        return (f"✅ Memory added to {target_display_name}'s profile!\n\n"
               f"📝 **Memory**: {memory_content}\n"
               f"👤 **Added by**: {sender_name}\n"
               f"📅 **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def register_contact_from_message(self, user_phone: str, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse and register a contact from a message
        
        Expected format: "Register contact [name]: [phone] as [relationship]"
        """
        pattern = r"register contact\s+([^:]+):\s*([+\d\s-]+)\s+as\s+(.+)$"
        match = re.match(pattern, message.lower().strip(), re.IGNORECASE)
        
        if match:
            contact_name = match.group(1).strip()
            contact_phone = match.group(2).strip()
            relationship = match.group(3).strip()
            
            result = self.phone_directory.register_contact(
                user_phone=user_phone,
                contact_name=contact_name,
                contact_phone=contact_phone,
                relationship=relationship
            )
            
            return result
        
        return None

# Global instance
personal_assistant = PersonalAssistant()