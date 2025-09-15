#!/usr/bin/env python3
"""
WhatsApp Conversation Monitor
Monitors conversations between users and intelligently extracts memories, tasks, and requests
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class WhatsAppConversationMonitor:
    """
    Monitors WhatsApp conversations and extracts important information
    Creates person-specific memory sections for each user
    """
    
    def __init__(self, profiles_dir: str = "memory-system/user_profiles"):
        """Initialize the conversation monitor"""
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Patterns for intelligent extraction
        self.request_patterns = [
            r"(?:can you|could you|please|would you)\s+(?:buy|get|pick up|purchase)\s+(.+?)(?:\?|$|\.)",
            r"(?:don't forget to|remember to|need to)\s+(?:buy|get|pick up)\s+(.+?)(?:\?|$|\.)",
            r"(?:we need|i need you to)\s+(?:buy|get|pick up)\s+(.+?)(?:\?|$|\.)",
        ]
        
        self.task_patterns = [
            r"(?:remember to|don't forget to|please)\s+(.+?)(?:\?|$|\.)",
            r"(?:you need to|you should|you must)\s+(.+?)(?:\?|$|\.)",
            r"(?:can you|could you|would you)\s+(.+?)(?:\?|$|\.)",
        ]
        
        self.important_info_patterns = [
            r"(?:my|his|her|their)\s+(?:birthday|anniversary|graduation)\s+(?:is|on)\s+(.+?)(?:\.|$)",
            r"(?:i'm|i am|he's|she's|they're)\s+(?:allergic to|afraid of)\s+(.+?)(?:\.|$)",
            r"(?:my|our|his|her)\s+favorite\s+(.+?)\s+(?:is|are)\s+(.+?)(?:\.|$)",
            r"(?:i|we|they)\s+(?:like|love|enjoy|hate|dislike)\s+(.+?)(?:\.|$)",
        ]
        
        self.date_patterns = [
            r"(?:today|tomorrow|next week|next month)",
            r"(?:on\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}",
            r"\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)",
            r"at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?",
        ]
        
        logger.info("📱 WhatsApp Conversation Monitor initialized")
    
    def monitor_conversation(self, sender_phone: str, recipient_phone: str, 
                           message: str, sender_name: Optional[str] = None,
                           recipient_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Monitor a conversation and extract important information
        Updates both sender and recipient profiles if they exist
        
        Args:
            sender_phone: Phone number of the sender
            recipient_phone: Phone number of the recipient
            message: The message content
            sender_name: Optional name of the sender
            recipient_name: Optional name of the recipient
        
        Returns:
            Dict with extracted information and update status
        """
        result = {
            'extracted_requests': [],
            'extracted_tasks': [],
            'extracted_info': [],
            'sender_updated': False,
            'recipient_updated': False
        }
        
        # Extract information from the message
        message_lower = message.lower()
        
        # Extract requests (shopping, errands, etc.)
        for pattern in self.request_patterns:
            matches = re.findall(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                item = match.strip()
                if len(item) < 100:  # Sanity check
                    result['extracted_requests'].append({
                        'request': item,
                        'date': datetime.now().isoformat(),
                        'completed': False,
                        'expires': (datetime.now() + timedelta(days=1)).isoformat()
                    })
        
        # Extract tasks
        for pattern in self.task_patterns:
            matches = re.findall(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                task = match.strip()
                # Skip if already captured as request
                if not any(req['request'] in task for req in result['extracted_requests']):
                    if len(task) < 150:  # Sanity check
                        result['extracted_tasks'].append({
                            'task': task,
                            'date': datetime.now().isoformat(),
                            'completed': False,
                            'expires': (datetime.now() + timedelta(days=2)).isoformat()
                        })
        
        # Extract important information
        for pattern in self.important_info_patterns:
            matches = re.findall(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    info = ' '.join(match).strip()
                else:
                    info = match.strip()
                if len(info) < 200:  # Sanity check
                    result['extracted_info'].append(info)
        
        # Update sender's profile
        if result['extracted_requests'] or result['extracted_tasks'] or result['extracted_info']:
            sender_update = self._update_user_conversation_memory(
                sender_phone, recipient_phone, recipient_name,
                result['extracted_requests'], result['extracted_tasks'], 
                result['extracted_info'], message, is_sender=True
            )
            result['sender_updated'] = sender_update['success']
        
        # Update recipient's profile if they exist
        recipient_profile_path = self._get_profile_path(recipient_phone)
        if recipient_profile_path.exists():
            recipient_update = self._update_user_conversation_memory(
                recipient_phone, sender_phone, sender_name,
                result['extracted_requests'], result['extracted_tasks'],
                result['extracted_info'], message, is_sender=False
            )
            result['recipient_updated'] = recipient_update['success']
        
        return result
    
    def _get_profile_path(self, phone_number: str) -> Path:
        """Get the profile path for a user"""
        clean_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        return self.profiles_dir / f"profile_{clean_number}.md"
    
    def _update_user_conversation_memory(self, user_phone: str, other_phone: str,
                                        other_name: Optional[str], requests: List[Dict],
                                        tasks: List[Dict], info: List[str], 
                                        message: str, is_sender: bool) -> Dict[str, Any]:
        """
        Update a user's conversation memory with extracted information
        
        Args:
            user_phone: Phone number of the user to update
            other_phone: Phone number of the other person
            other_name: Name of the other person
            requests: List of extracted requests
            tasks: List of extracted tasks
            info: List of extracted important information
            message: The original message
            is_sender: Whether the user is the sender or recipient
        
        Returns:
            Dict with success status and message
        """
        try:
            # Load user profile
            profile = self._load_user_profile(user_phone)
            
            # Initialize conversation_memories if not exists
            if 'conversation_memories' not in profile:
                profile['conversation_memories'] = {}
            
            # Get or create conversation memory for this person
            memory_key = other_name.lower() if other_name else other_phone
            if memory_key not in profile['conversation_memories']:
                profile['conversation_memories'][memory_key] = {
                    'name': other_name or 'Unknown',
                    'phone': other_phone,
                    'relationship': 'contact',
                    'recent_requests': [],
                    'recent_tasks': [],
                    'important_info': [],
                    'conversation_history': [],
                    'last_conversation': datetime.now().isoformat()
                }
            
            conv_memory = profile['conversation_memories'][memory_key]
            
            # Update last conversation time
            conv_memory['last_conversation'] = datetime.now().isoformat()
            
            # Add requests (from their perspective)
            if is_sender:
                # User sent the message - they made the requests
                for req in requests:
                    req['from'] = 'me'
                    req['to'] = other_name or other_phone
                    conv_memory['recent_requests'].append(req)
            else:
                # User received the message - requests are for them
                for req in requests:
                    req['from'] = other_name or other_phone
                    req['to'] = 'me'
                    conv_memory['recent_requests'].append(req)
            
            # Add tasks
            if is_sender:
                for task in tasks:
                    task['assigned_by'] = 'me'
                    task['assigned_to'] = other_name or other_phone
                    conv_memory['recent_tasks'].append(task)
            else:
                for task in tasks:
                    task['assigned_by'] = other_name or other_phone
                    task['assigned_to'] = 'me'
                    conv_memory['recent_tasks'].append(task)
            
            # Add important info (deduplicate)
            for item in info:
                if item not in conv_memory['important_info']:
                    conv_memory['important_info'].append(item)
            
            # Add to conversation history
            conv_memory['conversation_history'].append({
                'timestamp': datetime.now().isoformat(),
                'message': message[:500],  # Truncate long messages
                'sender': 'me' if is_sender else other_name or other_phone,
                'extracted_items': len(requests) + len(tasks) + len(info)
            })
            
            # Cleanup old data
            self._cleanup_conversation_memory(conv_memory)
            
            # Save updated profile
            self._save_user_profile(user_phone, profile)
            
            logger.info(f"✅ Updated conversation memory for {user_phone} with {memory_key}")
            return {'success': True, 'message': 'Conversation memory updated'}
            
        except Exception as e:
            logger.error(f"Failed to update conversation memory: {e}")
            return {'success': False, 'message': str(e)}
    
    def _cleanup_conversation_memory(self, conv_memory: Dict[str, Any]):
        """
        Clean up old data from conversation memory
        - Remove completed tasks older than 7 days
        - Keep only last 20 requests
        - Keep only last 50 conversation history items
        """
        now = datetime.now()
        
        # Clean up old completed tasks
        if 'recent_tasks' in conv_memory:
            conv_memory['recent_tasks'] = [
                task for task in conv_memory['recent_tasks']
                if not (task.get('completed') and 
                       (now - datetime.fromisoformat(task['date'])).days > 7)
            ]
            # Keep only last 20 tasks
            conv_memory['recent_tasks'] = conv_memory['recent_tasks'][-20:]
        
        # Clean up old completed requests
        if 'recent_requests' in conv_memory:
            conv_memory['recent_requests'] = [
                req for req in conv_memory['recent_requests']
                if not (req.get('completed') and 
                       (now - datetime.fromisoformat(req['date'])).days > 7)
            ]
            # Keep only last 20 requests
            conv_memory['recent_requests'] = conv_memory['recent_requests'][-20:]
        
        # Keep only last 50 conversation history items
        if 'conversation_history' in conv_memory:
            conv_memory['conversation_history'] = conv_memory['conversation_history'][-50:]
        
        # Keep only last 100 important info items
        if 'important_info' in conv_memory:
            conv_memory['important_info'] = conv_memory['important_info'][-100:]
    
    def query_conversation_memory(self, user_phone: str, query: str) -> str:
        """
        Query a user's conversation memories based on natural language
        
        Args:
            user_phone: Phone number of the user
            query: Natural language query
        
        Returns:
            Response string with relevant information
        """
        profile = self._load_user_profile(user_phone)
        query_lower = query.lower()
        
        if 'conversation_memories' not in profile:
            return "No conversation memories found."
        
        response_parts = []
        
        # Check for specific person mentions
        for person_key, conv_memory in profile['conversation_memories'].items():
            person_name = conv_memory.get('name', person_key).lower()
            
            # Check if this person is mentioned in the query
            if person_name in query_lower or person_key in query_lower:
                
                # Check for request queries
                if any(word in query_lower for word in ['buy', 'purchase', 'get', 'shopping', 'request']):
                    pending_requests = [
                        req for req in conv_memory.get('recent_requests', [])
                        if not req.get('completed')
                    ]
                    if pending_requests:
                        response_parts.append(f"📝 {conv_memory['name']}'s pending requests:")
                        for req in pending_requests[:5]:
                            response_parts.append(f"  • {req['request']} (from {req['date'][:10]})")
                
                # Check for task queries
                elif any(word in query_lower for word in ['task', 'todo', 'do', 'need']):
                    pending_tasks = [
                        task for task in conv_memory.get('recent_tasks', [])
                        if not task.get('completed')
                    ]
                    if pending_tasks:
                        response_parts.append(f"📋 {conv_memory['name']}'s pending tasks:")
                        for task in pending_tasks[:5]:
                            response_parts.append(f"  • {task['task']} (from {task['date'][:10]})")
                
                # Check for birthday/important info queries
                elif any(word in query_lower for word in ['birthday', 'anniversary', 'favorite', 'allergic', 'like']):
                    important_info = conv_memory.get('important_info', [])
                    matching_info = [
                        info for info in important_info
                        if any(word in info.lower() for word in query_lower.split())
                    ]
                    if matching_info:
                        response_parts.append(f"ℹ️ {conv_memory['name']}'s information:")
                        for info in matching_info[:5]:
                            response_parts.append(f"  • {info}")
                
                # General conversation query
                elif any(word in query_lower for word in ['talk', 'conversation', 'said', 'discussed']):
                    history = conv_memory.get('conversation_history', [])
                    if history:
                        recent = history[-3:]  # Last 3 conversations
                        response_parts.append(f"💬 Recent conversations with {conv_memory['name']}:")
                        for conv in recent:
                            response_parts.append(f"  • {conv['timestamp'][:16]}: {conv['message'][:100]}...")
        
        # If no specific person mentioned, show general overview
        if not response_parts:
            if 'what' in query_lower and 'asked' in query_lower:
                # Show all pending requests from everyone
                all_requests = []
                for person_key, conv_memory in profile['conversation_memories'].items():
                    for req in conv_memory.get('recent_requests', []):
                        if not req.get('completed'):
                            all_requests.append(f"{conv_memory['name']}: {req['request']}")
                
                if all_requests:
                    response_parts.append("📝 All pending requests:")
                    for req in all_requests[:10]:
                        response_parts.append(f"  • {req}")
                else:
                    response_parts.append("No pending requests found.")
        
        return '\n'.join(response_parts) if response_parts else "No relevant information found for your query."
    
    def _load_user_profile(self, phone_number: str) -> Dict[str, Any]:
        """Load user profile from MD file"""
        profile_path = self._get_profile_path(phone_number)
        
        if not profile_path.exists():
            return {}
        
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
        
        # Add conversation memories section
        if profile.get('conversation_memories'):
            md_content += "\n## 💬 Conversation Memories\n"
            for person_key, conv_mem in profile['conversation_memories'].items():
                md_content += f"\n### {conv_mem['name']} ({conv_mem.get('relationship', 'contact')})\n"
                md_content += f"- **Phone**: {conv_mem.get('phone', 'Unknown')}\n"
                md_content += f"- **Last Conversation**: {conv_mem.get('last_conversation', 'Never')[:16]}\n"
                
                # Show pending requests
                pending_requests = [r for r in conv_mem.get('recent_requests', []) if not r.get('completed')]
                if pending_requests:
                    md_content += "\n**Pending Requests:**\n"
                    for req in pending_requests[:5]:
                        md_content += f"  • {req['request']} ({req['date'][:10]})\n"
                
                # Show pending tasks  
                pending_tasks = [t for t in conv_mem.get('recent_tasks', []) if not t.get('completed')]
                if pending_tasks:
                    md_content += "\n**Pending Tasks:**\n"
                    for task in pending_tasks[:5]:
                        md_content += f"  • {task['task']} ({task['date'][:10]})\n"
                
                # Show important info
                if conv_mem.get('important_info'):
                    md_content += "\n**Important Information:**\n"
                    for info in conv_mem['important_info'][:10]:
                        md_content += f"  • {info}\n"
        
        # Add other existing sections
        if profile.get('interests'):
            md_content += "\n## 🎯 Interests & Hobbies\n"
            for interest in profile['interests']:
                md_content += f"- {interest}\n"
        
        if profile.get('memories'):
            md_content += "\n## 🧠 Memories\n"
            for memory in profile['memories'][-20:]:
                md_content += f"- [{memory.get('date', '')}] {memory.get('content', '')}\n"
        
        # Embed JSON data for easy parsing
        md_content += f"\n\n<!-- PROFILE_DATA_START -->\n{json.dumps(profile, indent=2)}\n<!-- PROFILE_DATA_END -->\n"
        
        # Save to file
        with open(profile_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"💾 Saved profile with conversation memories for {profile.get('name', phone_number)}")

# Create global instance
whatsapp_monitor = WhatsAppConversationMonitor()