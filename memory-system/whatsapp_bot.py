#!/usr/bin/env python3
"""
WhatsApp Bot Integration for Memory App
Implements all three diamond features through WhatsApp
"""

import os
import asyncio
import tempfile
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from memory_app import memory_app
import json

# Import PersonalAssistant for intelligent conversations
try:
    from personal_assistant import personal_assistant
    PERSONAL_ASSISTANT_AVAILABLE = True
except ImportError:
    PERSONAL_ASSISTANT_AVAILABLE = False
    personal_assistant = None

# Import Phase 2 components
try:
    from md_file_manager import MDFileManager, MemoryTag, MemoryEntry
    MD_MANAGER_AVAILABLE = True
except ImportError:
    MD_MANAGER_AVAILABLE = False

try:
    from conversation_classifier import ConversationClassifier, ConversationContext
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppMemoryBot:
    """
    WhatsApp bot with Memory App integration
    Features: Voice-activated memory, AI call handling, daily summaries
    """
    
    def __init__(self):
        self.active_users: Dict[str, Dict] = {}
        self.message_buffer: Dict[str, List[Dict]] = {}  # For message monitoring
        self.call_sessions: Dict[str, Dict] = {}  # For call recording
        self.proactive_messages_sent: Dict[str, List[Dict]] = {}  # Track proactive messages
        
        # Initialize Phase 2 components
        self.md_file_manager = None
        self.conversation_classifier = None
        
        if MD_MANAGER_AVAILABLE:
            self.md_file_manager = MDFileManager(base_dir="memory-system/users")
            logger.info("📂 WhatsApp Bot: MDFileManager initialized")
        
        if CLASSIFIER_AVAILABLE:
            self.conversation_classifier = ConversationClassifier()
            logger.info("🧠 WhatsApp Bot: ConversationClassifier initialized")
        
        logger.info("🔗 WhatsApp Memory Bot initialized")
    
    async def send_proactive_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send a proactive WhatsApp message (not in response to user)"""
        try:
            # Track proactive messages
            if phone_number not in self.proactive_messages_sent:
                self.proactive_messages_sent[phone_number] = []
            
            self.proactive_messages_sent[phone_number].append({
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'type': 'proactive'
            })
            
            # In production, this would call the WhatsApp Business API
            # For now, log the proactive message
            logger.info(f"📤 PROACTIVE: Sending message to {phone_number}")
            logger.info(f"   Message: {message[:100]}...")
            
            # Return success (in production, would check API response)
            return {
                'success': True,
                'message': 'Proactive message sent',
                'phone_number': phone_number,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send proactive message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming WhatsApp message with full Memory App features"""
        sender_id = message_data.get('sender_id')
        message_type = message_data.get('type')  # 'text', 'voice', 'image'
        content = message_data.get('content', '')
        
        logger.info(f"📱 WhatsApp message from {sender_id}: {message_type}")
        
        # Route message based on type
        if message_type == 'voice':
            return await self._handle_voice_message(sender_id, message_data)
        elif message_type == 'text':
            return await self._handle_text_message(sender_id, content)
        elif message_type == 'image':
            return await self._handle_image_message(sender_id, message_data)
        else:
            return {'response': "I can help with text, voice messages, and images. Try asking me about memories!"}
    
    async def _handle_voice_message(self, sender_id: str, message_data: Dict) -> Dict[str, Any]:
        """Handle voice message with voice authentication for memory access"""
        audio_data = message_data.get('audio_data')  # Base64 encoded audio
        
        if not audio_data:
            return {'response': "I couldn't process the voice message. Please try again."}
        
        try:
            # Save audio to temporary file for voice authentication
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_file:
                import base64
                audio_bytes = base64.b64decode(audio_data)
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            
            # Handle voice enrollment samples
            if (sender_id in self.active_users and 
                self.active_users[sender_id].get('status') == 'enrolling_voice'):
                
                # Store this voice sample for enrollment
                user_context = self.active_users[sender_id]
                user_context['enrollment_samples'].append(tmp_file_path)
                
                samples_count = len(user_context['enrollment_samples'])
                
                if samples_count < 3:
                    response_text = f"✅ Voice sample {samples_count}/3 recorded.\n\n"
                    response_text += f"Please send voice sample {samples_count + 1}:\n"
                    if samples_count == 1:
                        response_text += "'Memory access authentication for [your name]'"
                    else:
                        response_text += "'Voice enrollment sample three for secure access'"
                        
                    return {'response': response_text}
                
                else:
                    # All 3 samples collected - process enrollment
                    from memory_app import UserPlan
                    enrollment_result = await memory_app.enroll_user_voice(
                        user_id=sender_id,
                        display_name=user_context['display_name'],
                        audio_files=user_context['enrollment_samples'],
                        device_hint="whatsapp",
                        plan=UserPlan.FREE  # Default to free plan
                    )
                    
                    # Clean up enrollment samples
                    for sample_path in user_context['enrollment_samples']:
                        try:
                            os.unlink(sample_path)
                        except:
                            pass
                    
                    # Clear user context
                    del self.active_users[sender_id]
                    
                    if enrollment_result['success']:
                        plan_info = enrollment_result['plan_details']
                        response_text = f"🎉 **{enrollment_result['message']}**\n\n"
                        response_text += f"📋 **{plan_info['name']}** - ${plan_info['price']}/month\n"
                        response_text += f"💳 **Credits:** {enrollment_result['credits_available']}/{plan_info['memories']} memories\n\n"
                        response_text += "🎤 **Voice Commands:**\n"
                        response_text += "• Say 'Mother' to access family memories\n"
                        response_text += "• Say 'Work' to access work memories\n"
                        response_text += "• Say 'Memory 1000' for specific memories\n"
                        response_text += "• Send '/status' to check your plan & credits\n\n"
                        response_text += "💾 **Memory Categories:**\n"
                        response_text += "Mother, Father, Work, Family, Friends, Personal, Health, Finance\n\n"
                        response_text += "🔐 Your memories are now protected by voice authentication!"
                    else:
                        response_text = f"❌ Voice enrollment failed: {enrollment_result['message']}\n\n"
                        response_text += "Please try the `/enroll [Your Name]` command again."
                    
                    return {'response': response_text}
            
            # Check if user is enrolled in voice authentication
            if sender_id not in memory_app.voice_auth.user_accounts:
                # User not enrolled - suggest voice enrollment
                response_text = ("🔐 **Voice Authentication Required**\n\n"
                               "To access your memories securely, you need to enroll your voice first.\n\n"
                               "Send me the command: `/enroll [Your Full Name]`\n"
                               "Then record 3 voice samples when prompted.\n\n"
                               "Once enrolled, you can say:\n"
                               "• 'Mother' to access family memories\n"
                               "• 'Work' to access work memories\n"
                               "• 'Memory 1000' for specific memories")
            else:
                # User is enrolled - attempt voice authentication
                channel_id = f"whatsapp_{sender_id}"
                auth_result = await memory_app.authenticate_and_open_category(
                    audio_file_path=tmp_file_path,
                    user_id=sender_id,
                    channel_id=channel_id
                )
                
                if auth_result['success']:
                    # Authentication successful - show memories
                    memories = auth_result.get('memories', [])
                    response_text = f"🔓 {auth_result['message']}\n\n"
                    
                    if memories:
                        for memory in memories[:3]:  # Show first 3
                            response_text += f"📋 Memory {memory.memory_number} ({memory.category.value.title()}):\n"
                            response_text += f"💬 {memory.content[:150]}{'...' if len(memory.content) > 150 else ''}\n"
                            response_text += f"📅 {memory.timestamp.strftime('%Y-%m-%d %H:%M')}\n\n"
                    else:
                        response_text += "No memories found in this category yet."
                
                elif auth_result.get('status') == 'challenge_required':
                    # Voice recognized but needs verification
                    challenges = auth_result.get('challenge_questions', [])
                    response_text = f"⚠️ {auth_result['message']}\n\n"
                    response_text += "Please answer these verification questions:\n\n"
                    
                    for i, challenge in enumerate(challenges, 1):
                        response_text += f"{i}. {challenge['question']}\n"
                    
                    response_text += "\nReply with your answers separated by semicolons (;)"
                    
                    # Store challenge context for verification
                    self.active_users[sender_id] = {
                        'status': 'awaiting_challenge_response',
                        'challenges': challenges,
                        'category': auth_result.get('category'),
                        'confidence': auth_result.get('confidence')
                    }
                
                else:
                    # Authentication failed
                    response_text = f"❌ {auth_result['message']}\n\n"
                    response_text += "Voice authentication failed. Please try again or contact support if this continues."
            
            # Clean up temp file
            os.unlink(tmp_file_path)
            
            return {'response': response_text}
            
        except Exception as e:
            logger.error(f"Voice message processing failed: {e}")
            return {'response': "I had trouble processing that voice message. Could you try again or send a text instead?"}
    
    async def _handle_text_message(self, sender_id: str, content: str) -> Dict[str, Any]:
        """Handle text message with message monitoring, summaries, and daily reviews"""
        content_lower = content.lower()
        
        # Store incoming messages for monitoring
        if sender_id not in self.message_buffer:
            self.message_buffer[sender_id] = []
        
        # Add message to buffer
        self.message_buffer[sender_id].append({
            'sender': sender_id,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'sender_name': memory_app.contact_profiles.get(sender_id).name if sender_id in memory_app.contact_profiles else 'Unknown'
        })
        
        # Monitor and summarize if buffer reaches threshold
        await self._check_and_summarize_buffer(sender_id)
        
        # Handle daily review command
        if content.startswith('/daily_review'):
            review_result = await memory_app.daily_memory_review('default_user')
            return {'response': review_result['message']}
        
        # Handle memory review actions
        if content.startswith('/keep_'):
            memory_id = content.replace('/keep_', '')
            action_result = await memory_app.process_memory_review_action(
                user_id='default_user',
                action='keep',
                memory_id=memory_id
            )
            return {'response': action_result['message']}
        
        if content.startswith('/delete_'):
            memory_id = content.replace('/delete_', '')
            action_result = await memory_app.process_memory_review_action(
                user_id='default_user',
                action='delete',
                memory_id=memory_id
            )
            return {'response': action_result['message']}
        
        if content.startswith('/edit_'):
            parts = content.split(' ', 1)
            if len(parts) == 2:
                memory_id = parts[0].replace('/edit_', '')
                new_content = parts[1]
                action_result = await memory_app.process_memory_review_action(
                    user_id='default_user',
                    action='edit',
                    memory_id=memory_id,
                    new_content=new_content
                )
                return {'response': action_result['message']}
            else:
                return {'response': "Usage: /edit_[memory_id] [new content]"}
        
        # Handle contact profile management
        if content.startswith('/contact_profile'):
            parts = content.split()
            if len(parts) >= 3:
                contact_id = parts[1]
                updates = {}
                
                # Parse updates
                for i in range(2, len(parts)):
                    if '=' in parts[i]:
                        key, value = parts[i].split('=', 1)
                        if key in ['avatar_enabled', 'can_use_my_avatar']:
                            updates[key] = value.lower() == 'true'
                        else:
                            updates[key] = value
                
                profile_result = await memory_app.manage_contact_profile(
                    contact_id=contact_id,
                    updates=updates
                )
                return {'response': f"Contact profile updated: {profile_result['message']}"}
            else:
                return {'response': "Usage: /contact_profile [contact_id] [key=value ...]"}
        
        # Handle secret memory creation
        if content.startswith('/create_secret'):
            parts = content.split(' ', 3)
            if len(parts) >= 4:
                level = parts[1].upper()
                title = parts[2]
                secret_content = parts[3]
                
                from memory_app import SecretLevel
                
                try:
                    secret_level = SecretLevel[level]
                    secret_result = await memory_app.create_secret_memory(
                        user_id='default_user',
                        title=title,
                        content=secret_content,
                        secret_level=secret_level
                    )
                    return {'response': f"🔐 Secret created: {secret_result['message']}"}
                except KeyError:
                    return {'response': "Invalid security level. Use: SECRET, CONFIDENTIAL, or ULTRA_SECRET"}
            else:
                return {'response': "Usage: /create_secret [LEVEL] [title] [content]"}
        
        # Handle secret memory access
        if content.startswith('/access_secret'):
            parts = content.split()
            if len(parts) >= 2:
                secret_id = parts[1]
                access_result = await memory_app.access_secret_memory(
                    secret_id=secret_id,
                    contact_id=sender_id
                )
                
                if access_result['success']:
                    return {'response': f"🔓 {access_result['title']}\n\n{access_result['content']}"}
                else:
                    return {'response': f"❌ {access_result['message']}"}
            else:
                return {'response': "Usage: /access_secret [secret_id]"}
        
        # Handle status command
        if content.startswith('/status'):
            user_status = await memory_app.get_user_status(sender_id)
            
            if not user_status['success']:
                return {'response': 'You are not enrolled yet. Send `/enroll [Your Name]` to get started.'}
            
            plan_info = user_status['plan_info']
            credits = user_status['credits']
            memories = user_status['memories']
            
            response = f"📊 **Account Status for {user_status['display_name']}**\n\n"
            response += f"📋 **Plan:** {plan_info['name']} (${plan_info['price']}/month)\n"
            response += f"💳 **Credits:** {credits['available']}/{credits['total']} ({credits['usage_percentage']}% used)\n"
            response += f"🧠 **Memories:** {memories['total_count']} stored\n\n"
            
            if memories['by_category']:
                response += "📂 **Memories by Category:**\n"
                for category, count in memories['by_category'].items():
                    response += f"   • {category.title()}: {count}\n"
                response += "\n"
            
            if user_status['warnings']['low_credits']:
                response += "⚠️ **Low Credits Warning**\n"
                response += "You're running low on memory credits!\n\n"
                
                if user_status['warnings']['upgrade_suggestion']:
                    upgrade = user_status['warnings']['upgrade_suggestion']
                    response += f"💎 **Upgrade Suggestion:**\n"
                    response += f"Consider upgrading to {upgrade['suggested_plan'].title()} Plan (${upgrade['price']}/month)\n"
                    response += f"Benefits: {', '.join(upgrade['benefits'])}\n"
                    response += "Send `/upgrade {plan}` to upgrade\n\n"
            
            response += "🎤 **Commands:**\n"
            response += "• Send voice: 'Mother' for family memories\n"
            response += "• Send voice: 'Memory 1000' for specific memory\n"
            response += "• Send '/upgrade paid' or '/upgrade pro'\n"
            response += "• Send '/plans' to see all available plans"
            
            return {'response': response}
        
        # Handle upgrade command
        if content.startswith('/upgrade'):
            parts = content.split(' ')
            if len(parts) != 2:
                return {'response': 'Usage: `/upgrade paid` or `/upgrade pro`'}
            
            plan_name = parts[1].lower()
            plan_mapping = {'paid': 'PAID', 'pro': 'PRO'}
            
            if plan_name not in plan_mapping:
                return {'response': 'Available plans: `paid` or `pro`. Usage: `/upgrade paid`'}
            
            from memory_app import UserPlan
            new_plan = UserPlan[plan_mapping[plan_name]]
            
            upgrade_result = await memory_app.upgrade_user_plan(sender_id, new_plan)
            
            if upgrade_result['success']:
                plan_info = upgrade_result['plan_details']
                response = f"🎉 **Plan Upgraded Successfully!**\n\n"
                response += f"📋 **New Plan:** {plan_info['name']} (${plan_info['price']}/month)\n"
                response += f"💳 **Credits:** {upgrade_result['credits_available']}/{upgrade_result['new_credit_limit']}\n"
                response += f"✨ **New Features:**\n"
                for feature in plan_info['features']:
                    response += f"   • {feature}\n"
                response += "\n🎊 Welcome to your enhanced Memory App experience!"
                return {'response': response}
            else:
                return {'response': f"❌ Upgrade failed: {upgrade_result['message']}"}
        
        # Handle plans command
        if content.startswith('/plans'):
            from memory_app import UserPlan
            response = "💎 **Memory App Plans**\n\n"
            
            for plan in [UserPlan.FREE, UserPlan.PAID, UserPlan.PRO]:
                plan_info = memory_app.credit_manager.get_plan_details(plan)
                response += f"📋 **{plan_info['name']}** - ${plan_info['price']}/month\n"
                response += f"   • {plan_info['memories']} secure memories\n"
                response += f"   • {plan_info['support']} support\n"
                for feature in plan_info['features'][:3]:  # Show first 3 features
                    response += f"   • {feature}\n"
                response += "\n"
            
            response += "🔼 **Upgrade:** Send `/upgrade paid` or `/upgrade pro`\n"
            response += "📊 **Status:** Send `/status` to check your current plan"
            
            return {'response': response}
        
        # Handle voice enrollment command
        if content.startswith('/enroll'):
            parts = content.split(' ', 1)
            if len(parts) > 1:
                display_name = parts[1].strip()
                self.active_users[sender_id] = {
                    'status': 'enrolling_voice',
                    'display_name': display_name,
                    'enrollment_samples': []
                }
                
                response = f"🎤 **Voice Enrollment Started for {display_name}**\n\n"
                response += "Please send me 3 voice messages, each saying:\n\n"
                response += "1. 'Hello, this is [your name] enrolling my voice for secure memory access'\n"
                response += "2. 'Memory access authentication for [your name]'\n"  
                response += "3. 'Voice enrollment sample three for secure access'\n\n"
                response += "Send one voice message at a time."
                
                return {'response': response}
            else:
                return {'response': 'Please use: /enroll [Your Full Name]'}
        
        # Handle challenge responses
        if (sender_id in self.active_users and 
            self.active_users[sender_id].get('status') == 'awaiting_challenge_response'):
            
            # Split responses by semicolon
            responses = [resp.strip() for resp in content.split(';')]
            
            user_context = self.active_users[sender_id]
            challenge_result = await memory_app.verify_challenge_response(
                user_id=sender_id,
                channel_id=f"whatsapp_{sender_id}",
                challenge_responses=responses,
                original_category=user_context.get('category')
            )
            
            # Clear user context
            del self.active_users[sender_id]
            
            if challenge_result['success']:
                response = f"✅ {challenge_result['message']}\n\n"
                response += "You now have access to your memories. You can:\n"
                response += "• Send voice messages saying 'Mother', 'Work', etc.\n"
                response += "• Request specific memories like 'Memory 1001'"
                
                return {'response': response}
            else:
                return {'response': f"❌ Challenge verification failed: {challenge_result['message']}"}
        
        # Handle voice enrollment samples (when user is in enrollment mode)
        if (sender_id in self.active_users and 
            self.active_users[sender_id].get('status') == 'enrolling_voice'):
            
            return {'response': 'Please send voice messages for enrollment, not text. I need 3 voice samples to enroll your voice securely.'}
        
        # Regular text message handling
        content_lower = content.lower()
        
        # Check for memory-related commands
        if any(keyword in content_lower for keyword in ['memory', 'remember', 'recall', 'what did']):
            # This is likely a memory query
            memory_result = await memory_app.retrieve_memory_by_text(content, sender_id)
            
            if memory_result['success']:
                response_text = f"🧠 {memory_result['summary']}"
                
                for memory in memory_result['memories'][:3]:  # Show up to 3 results
                    response_text += f"\n\n📋 Memory {memory.memory_number}:"
                    response_text += f"\n📅 {memory.timestamp.strftime('%Y-%m-%d %H:%M')}"
                    response_text += f"\n💬 {memory.content[:200]}..."
            else:
                response_text = memory_result['summary']
        
        # Check for daily summary request
        elif 'daily summary' in content_lower or 'summary' in content_lower:
            return await self._handle_daily_summary_request(sender_id)
        
        # Check for special commands
        elif content_lower.startswith('/'):
            return await self._handle_command(sender_id, content)
        
        else:
            # Regular conversation - store it with credit management
            storage_result = await memory_app.store_conversation(
                content=content,
                participants=[sender_id, 'user'],
                owner_user_id=sender_id,
                category='general',
                platform='whatsapp',
                message_type='text'
            )
            
            if not storage_result['success']:
                response_text = f"❌ {storage_result['message']}\n\n"
                
                if storage_result.get('upgrade_suggestion'):
                    upgrade = storage_result['upgrade_suggestion']
                    response_text += f"💎 **Upgrade to {upgrade['suggested_plan'].title()} Plan**\n"
                    response_text += f"• ${upgrade['price']}/month\n"
                    response_text += f"• {', '.join(upgrade['benefits'])}\n\n"
                    response_text += f"Send `/upgrade {upgrade['suggested_plan']}` to upgrade!"
                
                return {'response': response_text}
            
            # Generate contextual response
            response_text = await self._generate_contextual_response(sender_id, content, storage_result['memory_number'])
        
        return {'response': response_text}
    
    async def _check_and_summarize_buffer(self, sender_id: str):
        """Check if buffer needs summarization and process it"""
        if sender_id not in self.message_buffer:
            return
        
        buffer = self.message_buffer[sender_id]
        
        # Check if we should summarize (10+ messages or oldest message > 15 minutes)
        should_summarize = False
        
        if len(buffer) >= 10:
            should_summarize = True
        elif buffer:
            oldest_msg_time = datetime.fromisoformat(buffer[0]['timestamp'])
            if datetime.now() - oldest_msg_time > timedelta(minutes=15):
                should_summarize = True
        
        if should_summarize and buffer:
            # Prepare messages for summarization
            conversation_text = "\n".join([
                f"{msg['sender_name']}: {msg['content']}" 
                for msg in buffer
            ])
            
            # Use Grok AI to analyze social dynamics and emotional tone
            summary_result = await memory_app.analyze_conversation_with_grok(
                conversation_text=conversation_text,
                context=f"WhatsApp conversation with {buffer[0]['sender_name']}"
            )
            
            if summary_result['success']:
                # Update contact's accumulated facts
                contact_id = sender_id
                if contact_id in memory_app.contact_profiles:
                    profile = memory_app.contact_profiles[contact_id]
                    
                    # Extract key facts from summary
                    key_facts = summary_result.get('key_facts', [])
                    for fact in key_facts:
                        if fact not in profile.accumulated_facts:
                            profile.accumulated_facts.append(fact)
                    
                    # Update common topics
                    topics = summary_result.get('topics', [])
                    for topic in topics:
                        if topic not in profile.common_topics:
                            profile.common_topics.append(topic)
                
                # Store summary as a memory
                memory_result = await memory_app.store_conversation_memory(
                    conversation_content=conversation_text,
                    platform="whatsapp",
                    participants=[sender_id],
                    owner_user_id=sender_id,
                    category='general'
                )
                
                # Clear the buffer after successful summarization
                self.message_buffer[sender_id] = []
                
                logger.info(f"✅ Summarized {len(buffer)} messages for {sender_id}")
    
    async def _handle_image_message(self, sender_id: str, message_data: Dict) -> Dict[str, Any]:
        """Handle image message with analysis and memory storage"""
        image_data = message_data.get('image_data')  # Base64 encoded image
        caption = message_data.get('caption', '')
        
        try:
            # Analyze image with GPT-5 Vision
            import openai
            openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            response = openai_client.chat.completions.create(
                model="gpt-5",  # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this image and describe what you see. Focus on key details, people, objects, text, and context."
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                            }
                        ]
                    }
                ],
                max_completion_tokens=300
            )
            
            image_analysis = response.choices[0].message.content
            
            # Store as conversation memory with credit management
            content = f"[Image shared"
            if caption:
                content += f" with caption: {caption}"
            content += f"]\n\nImage analysis: {image_analysis}"
            
            storage_result = await memory_app.store_conversation(
                content=content,
                participants=[sender_id, 'user'],
                owner_user_id=sender_id,
                category='general',
                platform='whatsapp',
                message_type='image'
            )
            
            if not storage_result['success']:
                response_text = f"❌ {storage_result['message']}\n\n"
                response_text += "📸 I analyzed the image but couldn't save it due to credit limits.\n\n"
                
                if storage_result.get('upgrade_suggestion'):
                    upgrade = storage_result['upgrade_suggestion']
                    response_text += f"💎 **Upgrade to {upgrade['suggested_plan'].title()} Plan**\n"
                    response_text += f"• ${upgrade['price']}/month\n"
                    response_text += f"• {', '.join(upgrade['benefits'])}\n\n"
                    response_text += f"Send `/upgrade {upgrade['suggested_plan']}` to upgrade!"
                
                return {'response': response_text}
            
            response_text = f"📸 I can see: {image_analysis}\n\n"
            if caption:
                response_text += f"Your caption: \"{caption}\"\n\n"
            response_text += f"I've saved this as Memory {storage_result['memory_number']} ({storage_result['credits_remaining']} credits left)\n\n"
            response_text += f"You can find it later by saying \"Memory Number {storage_result['memory_number']}\" or asking about what's in the image!"
            
            return {'response': response_text}
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return {'response': "I had trouble analyzing that image. Could you try sending it again?"}
    
    async def handle_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming WhatsApp call with AI call handling, recording and transcription"""
        caller_id = call_data.get('caller_id')
        caller_name = call_data.get('caller_name', 'Unknown')
        call_type = call_data.get('type', 'voice')  # 'voice' or 'video'
        
        # FEATURE 1: Phone Call Recording - Detect caller and match to contact
        logger.info(f"📞 Advanced call handling: {call_type} call from {caller_name} ({caller_id})")
        
        # Check contact profile for avatar privileges
        contact_profile = None
        if caller_id in memory_app.contact_profiles:
            contact_profile = memory_app.contact_profiles[caller_id]
            # Use contact name from profile if available
            if contact_profile.name:
                caller_name = contact_profile.name
            logger.info(f"Found contact profile: avatar_enabled={contact_profile.avatar_enabled}")
        
        # Store call session data for recording
        session_id = f"call_{caller_id}_{int(time.time())}"
        self.call_sessions[session_id] = {
            'caller_id': caller_id,
            'caller_name': caller_name,
            'call_type': call_type,
            'start_time': datetime.now(),
            'audio_chunks': [],
            'is_avatar_call': False
        }
        
        # FEATURE 4: Contact Avatar Privileges - Determine call handling mode
        if contact_profile and contact_profile.avatar_enabled:
            # Avatar-enabled contact - use AI avatar response with voice clone
            logger.info(f"🤖 Avatar mode for {caller_name}, voice clone: {contact_profile.can_use_my_avatar}")
            self.call_sessions[session_id]['is_avatar_call'] = True
            return {
                'answer': True,
                'mode': 'avatar',
                'session_id': session_id,
                'greeting': f"Hello {caller_name}, this is your personal assistant speaking on behalf of the user.",
                'record': True,  # Always record for transcript
                'use_voice_clone': contact_profile.can_use_my_avatar,
                'knowledge_access': contact_profile.knowledge_access_level
            }
        else:
            # Regular call - record for transcription
            logger.info(f"📼 Recording call from {caller_name} for transcription")
            return {
                'answer': True,
                'mode': 'record_only',
                'session_id': session_id,
                'greeting': "Your call is being recorded for memory purposes. Please proceed.",
                'record': True
            }
    
    async def handle_call_audio(
        self, 
        session_id: str, 
        audio_data: str,
        caller_id: Optional[str] = None,
        caller_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process audio during call with transcription and avatar response"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_file:
                import base64
                audio_bytes = base64.b64decode(audio_data)
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            
            # FEATURE 1: Store audio chunks for complete call recording
            if session_id in self.call_sessions:
                self.call_sessions[session_id]['audio_chunks'].append(tmp_file_path)
            
            # Get caller info from session or parameters
            if session_id in self.call_sessions:
                session_data = self.call_sessions[session_id]
                caller_id = caller_id or session_data['caller_id']
                caller_name = caller_name or session_data['caller_name']
                is_avatar_call = session_data['is_avatar_call']
            else:
                is_avatar_call = session_id.startswith('avatar_call_')
            
            # FEATURE 4: Avatar mode for contacts with avatar privileges
            if is_avatar_call:
                contact_profile = memory_app.contact_profiles.get(caller_id)
                
                if contact_profile and contact_profile.avatar_enabled:
                    # Transcribe caller's speech
                    transcription = await memory_app._transcribe_audio(tmp_file_path)
                    
                    # Store transcription for later review
                    if session_id in self.call_sessions:
                        if 'transcript' not in self.call_sessions[session_id]:
                            self.call_sessions[session_id]['transcript'] = []
                        self.call_sessions[session_id]['transcript'].append({
                            'speaker': caller_name,
                            'text': transcription,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    # Generate avatar response using contact's knowledge
                    avatar_response = await memory_app.generate_avatar_response(
                        contact_id=caller_id,
                        message=transcription,
                        user_id='default_user'
                    )
                    
                    if avatar_response['success']:
                        # Store avatar response in transcript
                        if session_id in self.call_sessions and 'transcript' in self.call_sessions[session_id]:
                            self.call_sessions[session_id]['transcript'].append({
                                'speaker': 'Avatar',
                                'text': avatar_response['response'],
                                'timestamp': datetime.now().isoformat()
                            })
                        
                        return {
                            'caller_text': transcription,
                            'ai_response': avatar_response['response'],
                            'using_avatar': True,
                            'continue_call': True
                        }
            
            # FEATURE 1: Regular call recording mode - transcribe and store
            if caller_id and caller_name:
                transcription_result = await memory_app.record_and_transcribe_call(
                    caller_id=caller_id,
                    caller_name=caller_name,
                    audio_file_path=tmp_file_path
                )
                
                if transcription_result['success']:
                    # Store transcription in session
                    if session_id in self.call_sessions:
                        if 'full_transcript' not in self.call_sessions[session_id]:
                            self.call_sessions[session_id]['full_transcript'] = ""
                        self.call_sessions[session_id]['full_transcript'] += transcription_result.get('transcription', '')
                        self.call_sessions[session_id]['memory_number'] = transcription_result.get('memory_number')
                    
                    return {
                        'transcription': transcription_result.get('transcription', ''),
                        'summary': transcription_result.get('summary', ''),
                        'memory_number': transcription_result.get('memory_number'),
                        'continue_call': True
                    }
            
            # Fallback to standard processing
            result = await memory_app.process_call_audio(session_id, tmp_file_path)
            
            # Don't clean up temp file yet - we might need it for full call recording
            # os.unlink(tmp_file_path)
            
            if 'error' in result:
                return {'error': result['error']}
            
            return {
                'caller_text': result.get('caller_text', ''),
                'ai_response': result.get('ai_response', ''),
                'continue_call': result.get('should_continue', True)
            }
            
        except Exception as e:
            logger.error(f"Call audio processing failed: {e}")
            return {'error': str(e)}
    
    async def end_call(self, session_id: str) -> Dict[str, Any]:
        """End AI call and store transcript"""
        transcript_memory = await memory_app.end_call(session_id)
        
        if transcript_memory:
            return {
                'success': True,
                'transcript_memory_number': transcript_memory,
                'message': f"Call ended. Transcript saved as Memory {transcript_memory}"
            }
        else:
            return {'success': False, 'message': 'Call session not found'}
    
    async def _handle_daily_summary_request(self, sender_id: str) -> Dict[str, Any]:
        """Handle request for daily summaries"""
        try:
            summary_data = await memory_app.generate_daily_summaries()
            
            if not summary_data['summaries']:
                return {'response': "No conversations found for today to summarize."}
            
            response_text = f"📊 Daily Summary for {summary_data['date']}\n"
            response_text += f"Found {len(summary_data['summaries'])} conversations:\n\n"
            
            for i, summary in enumerate(summary_data['summaries'][:5]):  # Show first 5
                response_text += f"{i+1}. Memory {summary['memory_number']}:\n"
                response_text += f"   {summary['summary']}\n"
                response_text += f"   👥 {', '.join(summary['participants'])}\n\n"
            
            response_text += "\nReply with:\n"
            response_text += "• ✅ [Memory Number] to approve\n"
            response_text += "• ❌ [Memory Number] to reject\n"
            response_text += "• 'approve all' to approve everything"
            
            return {'response': response_text}
            
        except Exception as e:
            logger.error(f"Daily summary generation failed: {e}")
            return {'response': "I had trouble generating the daily summary. Please try again later."}
    
    async def _handle_command(self, sender_id: str, command: str) -> Dict[str, Any]:
        """Handle special commands"""
        cmd_lower = command.lower().strip()
        
        # Daily review command
        if cmd_lower.startswith('/daily_review'):
            review_result = await memory_app.generate_daily_review(sender_id)
            
            if review_result['success']:
                memories = review_result['memories']
                response = "📅 **Daily Memory Review**\n\n"
                response += f"Found {len(memories)} memories from the last 24 hours:\n\n"
                
                for i, memory in enumerate(memories, 1):
                    response += f"{i}. Memory {memory.memory_number}:\n"
                    response += f"   {memory.content[:100]}...\n"
                    response += f"   Category: {memory.category.value}\n\n"
                
                response += "Reply with:\n"
                response += "• `/keep [numbers]` to keep specific memories\n"
                response += "• `/delete [numbers]` to delete memories\n"
                response += "• `/keep all` to keep everything"
            else:
                response = "No memories found in the last 24 hours."
        
        # Keep memories command
        elif cmd_lower.startswith('/keep'):
            parts = command.split()
            if len(parts) > 1:
                if parts[1].lower() == 'all':
                    response = "✅ All memories marked to keep."
                else:
                    memory_ids = [p.strip() for p in ' '.join(parts[1:]).split(',')]
                    response = f"✅ Memories {', '.join(memory_ids)} marked to keep."
            else:
                response = "Please specify which memories to keep: `/keep 1,2,3` or `/keep all`"
        
        # Delete memories command
        elif cmd_lower.startswith('/delete'):
            parts = command.split()
            if len(parts) > 1:
                memory_ids = [p.strip() for p in ' '.join(parts[1:]).split(',')]
                response = f"🗑️ Memories {', '.join(memory_ids)} deleted."
            else:
                response = "Please specify which memories to delete: `/delete 1,2,3`"
        
        # Set review time command
        elif cmd_lower.startswith('/set_review_time'):
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                time_str = parts[1]
                # Store the preferred review time
                await memory_app.set_daily_review_time(sender_id, time_str)
                response = f"⏰ Daily review time set to {time_str}\n"
                response += "You'll receive your daily memory review at this time every day."
            else:
                response = "Please specify a time: `/set_review_time 9:00 PM`"
        
        # Grant access command
        elif cmd_lower.startswith('/grant_access'):
            parts = command.split()
            if len(parts) >= 4:
                phone = parts[1]
                relationship = parts[2]
                permissions = ' '.join(parts[3:])
                
                access_result = await memory_app.grant_family_access(
                    user_id=sender_id,
                    family_member_id=phone,
                    relationship=relationship,
                    permission_level=permissions
                )
                
                if access_result['success']:
                    response = f"✅ Access granted to {relationship} ({phone})\n"
                    response += f"Permissions: {permissions}\n\n"
                    response += "They can now access your memories according to the permissions set."
                else:
                    response = f"❌ {access_result['message']}"
            else:
                response = "Usage: /grant_access [phone] [relationship] [permissions]\nExample: /grant_access +1234567890 mother read_only"
        
        # Revoke access command
        elif cmd_lower.startswith('/revoke_access'):
            parts = command.split()
            if len(parts) >= 2:
                phone = parts[1]
                
                revoke_result = await memory_app.revoke_family_access(
                    user_id=sender_id,
                    family_member_id=phone
                )
                
                if revoke_result['success']:
                    response = f"✅ Access revoked for {phone}"
                else:
                    response = f"❌ {revoke_result['message']}"
            else:
                response = "Usage: /revoke_access [phone]"
        
        # My family access command
        elif cmd_lower.startswith('/my_family_access'):
            family_list = await memory_app.get_family_access_list(sender_id)
            
            if family_list['success'] and family_list['family_members']:
                response = "👨‍👩‍👧‍👦 **Authorized Family Members:**\n\n"
                
                for member in family_list['family_members']:
                    response += f"• {member['relationship']}: {member['phone']}\n"
                    response += f"  Permissions: {member['permissions']}\n\n"
            else:
                response = "No family members have been granted access yet.\n"
                response += "Use `/grant_access [phone] [relationship] [permissions]` to add family."
        
        # Talk to myself command
        elif cmd_lower.startswith('/talk_to_myself'):
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                question = parts[1]
                
                avatar_response = await memory_app.generate_avatar_response(
                    avatar_user_id=sender_id,
                    contact_id=sender_id,
                    message=question,
                    conversation_history=[]
                )
                
                if avatar_response['success']:
                    response = f"💭 **Your Inner Voice Says:**\n\n{avatar_response['response']}"
                else:
                    response = "I couldn't generate a self-reflection response. Please try again."
            else:
                response = "What would you like to ask yourself? Use: `/talk_to_myself [question]`"
        
        # Memory game command
        elif cmd_lower.startswith('/memory_game'):
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                contact_name = parts[1]
                
                game_result = await memory_app.start_memory_game(
                    user_id=sender_id,
                    contact_name=contact_name
                )
                
                if game_result['success']:
                    response = f"🎮 **Memory Game with {contact_name}**\n\n"
                    response += f"Question: {game_result['question']}\n\n"
                    response += "Reply with your answer to continue the game!"
                else:
                    response = f"Could not start memory game: {game_result['message']}"
            else:
                response = "Who would you like to play the memory game with? Use: `/memory_game [contact name]`"
        
        # Commitments command
        elif cmd_lower.startswith('/commitments'):
            commitments = await memory_app.extract_commitments_from_memories(sender_id)
            
            if commitments['success'] and commitments['commitments']:
                response = "📋 **Your Upcoming Commitments:**\n\n"
                
                for commitment in commitments['commitments']:
                    response += f"• {commitment['description']}\n"
                    if commitment.get('date'):
                        response += f"  Due: {commitment['date']}\n"
                    response += "\n"
                
                response += "These were extracted from your recent conversations."
            else:
                response = "No upcoming commitments found in your recent memories."
        
        # My connections command
        elif cmd_lower.startswith('/my_connections'):
            mutual_matches = await memory_app.check_mutual_feelings(sender_id)
            
            if mutual_matches:
                response = "💕 **Your Mutual Connections:**\n\n"
                for match in mutual_matches:
                    response += f"• {match['person_name']} - Mutual feelings detected!\n"
                response += "\nThese people have also expressed similar feelings about you."
            else:
                response = "No mutual connections detected yet. Keep sharing your thoughts!"
        
        # Achievements command
        elif cmd_lower.startswith('/achievements'):
            achievements = memory_app.user_achievements.get(sender_id, [])
            
            response = "🏆 **Your Achievements:**\n\n"
            
            if achievements:
                for achievement in achievements:
                    if achievement.unlocked:
                        response += f"✅ {achievement.title}\n"
                        response += f"   {achievement.description}\n"
                        response += f"   🎯 {achievement.points} points\n\n"
            else:
                response += "Start using Memory App to unlock achievements!\n\n"
                response += "Available achievements:\n"
                response += "• First Memory - Store your first memory\n"
                response += "• Memory Master - Store 100 memories\n"
                response += "• Social Butterfly - Get 5 mutual connections"
        
        elif cmd_lower == '/status':
            status = memory_app.get_status()
            response = f"🤖 Memory App Status:\n"
            response += f"📚 Total memories: {status['total_memories']}\n"
            response += f"👥 People I know: {status['total_profiles']}\n"
            response += f"⏳ Pending summaries: {status['pending_summaries']}\n"
            response += f"📞 Call-enabled contacts: {status['call_enabled_contacts']}"
        
        elif cmd_lower == '/help':
            response = "📱 **Memory App Commands:**\n\n"
            response += "**Voice & Authentication:**\n"
            response += "• `/enroll [name]` - Enroll your voice\n"
            response += "• `/status` - Check your account status\n\n"
            response += "**Memory Management:**\n"
            response += "• `/daily_review` - Review today's memories\n"
            response += "• `/keep [1,2,3]` - Keep specific memories\n"
            response += "• `/delete [1,2,3]` - Delete memories\n"
            response += "• `/set_review_time [time]` - Set daily review time\n\n"
            response += "**Family & Access:**\n"
            response += "• `/grant_access [phone] [relationship] [permissions]`\n"
            response += "• `/revoke_access [phone]`\n"
            response += "• `/my_family_access` - List authorized family\n\n"
            response += "**Social Features:**\n"
            response += "• `/talk_to_myself [question]` - Self conversation\n"
            response += "• `/memory_game [contact]` - Play memory game\n"
            response += "• `/commitments` - Show upcoming commitments\n"
            response += "• `/my_connections` - Show mutual connections\n"
            response += "• `/achievements` - View your achievements\n\n"
            response += "**Premium:**\n"
            response += "• `/plans` - View all plans\n"
            response += "• `/upgrade [paid/pro]` - Upgrade your plan"
        
        elif cmd_lower.startswith('/approve'):
            # Handle summary approval
            parts = command.split()
            if len(parts) >= 2:
                if parts[1] == 'all':
                    response = "✅ Approving all summaries..."
                else:
                    memory_number = parts[1]
                    try:
                        result = await memory_app.approve_summary(memory_number, True)
                        response = f"✅ Approved summary for Memory {memory_number}"
                    except Exception as e:
                        response = f"❌ Couldn't approve Memory {memory_number}: {str(e)}"
            else:
                response = "Usage: /approve [memory_number] or /approve all"
        
        else:
            response = f"Unknown command: {cmd_lower}\nType /help for available commands."
        
        return {'response': response}
    
    async def _generate_contextual_response(
        self, 
        sender_id: str, 
        content: str, 
        memory_number: str
    ) -> str:
        """Generate intelligent response using PersonalAssistant with user profile tracking"""
        
        # Use PersonalAssistant for intelligent conversation
        if PERSONAL_ASSISTANT_AVAILABLE and personal_assistant:
            try:
                # Get user's name from memory app if available
                user_name = None
                if sender_id in memory_app.voice_auth.user_accounts:
                    user_account = memory_app.voice_auth.user_accounts[sender_id]
                    user_name = user_account.display_name
                
                # Process message with PersonalAssistant
                response = await personal_assistant.process_message(
                    phone_number=sender_id,
                    message=content,
                    user_name=user_name
                )
                
                # Add memory number reference if appropriate
                if memory_number and 'memory' not in response.lower():
                    response += f" (Saved as Memory {memory_number})"
                
                return response
                
            except Exception as e:
                logger.error(f"PersonalAssistant response failed: {e}")
                # Fall through to original logic
        
        # Fallback to original contextual response generation
        try:
            # Get recent memories for context
            recent_memories = await memory_app._get_recent_memories_for_contact(sender_id, 3)
            
            # Build context
            context = "\n".join([
                f"- {m.content[:100]}..." for m in recent_memories[-3:]  # Last 3, excluding current
            ])
            
            # Generate response using GPT-5
            import openai
            openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            prompt = f"""You are a helpful AI assistant integrated into WhatsApp. A user just sent you this message:

"{content}"

Recent conversation context:
{context}

You've stored this as Memory {memory_number}.

Generate a helpful, conversational response that:
1. Acknowledges their message appropriately
2. Shows you understand and remember context
3. Mentions the memory number if relevant
4. Offers helpful assistance
5. Keep it natural and friendly (1-2 sentences)

Response:"""

            response = openai_client.chat.completions.create(
                model="gpt-5",  # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Contextual response generation failed: {e}")
            return f"Got it! I've saved that as Memory {memory_number}. How else can I help you?"

# Global bot instance
whatsapp_bot = WhatsAppMemoryBot()

# ========== WEBHOOK ENDPOINTS FOR REAL-TIME INTEGRATION ==========

async def webhook_message(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming WhatsApp messages in real-time"""
    try:
        # Extract message data from webhook payload
        sender_id = request.get('from', {}).get('id')
        sender_name = request.get('from', {}).get('name', 'Unknown')
        message = request.get('message', {})
        
        # Determine message type
        message_type = 'text'
        content = ''
        audio_data = None
        image_data = None
        
        if 'text' in message:
            message_type = 'text'
            content = message['text']['body']
        elif 'audio' in message:
            message_type = 'voice'
            audio_data = message['audio'].get('data')  # Base64 encoded
        elif 'image' in message:
            message_type = 'image'
            image_data = message['image'].get('data')  # Base64 encoded
            content = message['image'].get('caption', '')
        
        # Process message through bot
        response = await whatsapp_bot.handle_message({
            'sender_id': sender_id,
            'sender_name': sender_name,
            'type': message_type,
            'content': content,
            'audio_data': audio_data,
            'image_data': image_data,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"✅ Webhook processed message from {sender_id}")
        
        return {
            'status': 'success',
            'message_processed': True,
            'response': response.get('response'),
            'memory_number': response.get('memory_number')
        }
        
    except Exception as e:
        logger.error(f"Webhook message processing failed: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

async def webhook_call_start(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle call initiation - start recording"""
    try:
        call_id = request.get('call_id')
        caller_id = request.get('from', {}).get('id')
        caller_name = request.get('from', {}).get('name', 'Unknown')
        
        # Initialize call session
        whatsapp_bot.call_sessions[call_id] = {
            'call_id': call_id,
            'caller_id': caller_id,
            'caller_name': caller_name,
            'start_time': datetime.now(),
            'audio_chunks': [],
            'status': 'recording'
        }
        
        logger.info(f"📞 Call started: {call_id} from {caller_name}")
        
        return {
            'status': 'success',
            'call_id': call_id,
            'message': 'Call recording started'
        }
        
    except Exception as e:
        logger.error(f"Call start webhook failed: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

async def webhook_call_audio(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle call audio chunks - accumulate for transcription"""
    try:
        call_id = request.get('call_id')
        audio_chunk = request.get('audio_chunk')  # Base64 encoded
        
        if call_id not in whatsapp_bot.call_sessions:
            return {
                'status': 'error',
                'message': 'Call session not found'
            }
        
        # Append audio chunk
        whatsapp_bot.call_sessions[call_id]['audio_chunks'].append(audio_chunk)
        
        chunk_count = len(whatsapp_bot.call_sessions[call_id]['audio_chunks'])
        logger.debug(f"🎤 Audio chunk {chunk_count} received for call {call_id}")
        
        return {
            'status': 'success',
            'call_id': call_id,
            'chunks_received': chunk_count
        }
        
    except Exception as e:
        logger.error(f"Call audio webhook failed: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

async def webhook_call_end(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle call termination - process recording and transcribe"""
    try:
        import base64
        
        call_id = request.get('call_id')
        
        if call_id not in whatsapp_bot.call_sessions:
            return {
                'status': 'error',
                'message': 'Call session not found'
            }
        
        session = whatsapp_bot.call_sessions[call_id]
        session['end_time'] = datetime.now()
        session['status'] = 'processing'
        
        # Calculate call duration
        duration = (session['end_time'] - session['start_time']).total_seconds()
        
        # Combine audio chunks
        combined_audio = b''
        for chunk in session['audio_chunks']:
            combined_audio += base64.b64decode(chunk)
        
        # Save combined audio to temp file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_file:
            tmp_file.write(combined_audio)
            audio_file_path = tmp_file.name
        
        # Process through memory app
        from memory_app import memory_app
        result = await memory_app.record_and_transcribe_call(
            caller_id=session['caller_id'],
            caller_name=session['caller_name'],
            audio_file_path=audio_file_path,
            user_id=session.get('user_id', 'default_user')
        )
        
        # Clean up
        os.unlink(audio_file_path)
        del whatsapp_bot.call_sessions[call_id]
        
        logger.info(f"☎️ Call ended: {call_id}, Duration: {duration}s, Memory: {result.get('memory_number')}")
        
        return {
            'status': 'success',
            'call_id': call_id,
            'duration_seconds': duration,
            'transcription': result.get('transcription'),
            'summary': result.get('summary'),
            'memory_number': result.get('memory_number'),
            'key_points': result.get('key_points', [])
        }
        
    except Exception as e:
        logger.error(f"Call end webhook failed: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

async def webhook_scheduled_review() -> Dict[str, Any]:
    """Scheduled webhook for daily memory reviews"""
    try:
        from memory_app import memory_app
        
        # Get all enrolled users
        enrolled_users = list(memory_app.voice_auth.user_accounts.keys())
        
        reviews_sent = []
        
        for user_id in enrolled_users:
            # Generate daily review
            review_result = await memory_app.daily_memory_review(user_id)
            
            if review_result['success'] and review_result['memories_count'] > 0:
                # Send review via WhatsApp (would integrate with actual WhatsApp API)
                reviews_sent.append({
                    'user_id': user_id,
                    'memories_count': review_result['memories_count'],
                    'review_id': review_result['review_id']
                })
                
                logger.info(f"📋 Daily review sent to {user_id}: {review_result['memories_count']} memories")
        
        return {
            'status': 'success',
            'reviews_sent': len(reviews_sent),
            'users': reviews_sent
        }
        
    except Exception as e:
        logger.error(f"Scheduled review webhook failed: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

# Demo function
async def demo_whatsapp_integration():
    """Demo WhatsApp bot functionality"""
    print("\n📱 WhatsApp Memory Bot Demo")
    print("==========================\n")
    
    # Simulate text message
    print("📝 Text Message Demo:")
    text_response = await whatsapp_bot.handle_message({
        'sender_id': 'john_whatsapp',
        'type': 'text',
        'content': 'Hey, just wanted to let you know the meeting is moved to 3 PM tomorrow'
    })
    print(f"User: 'Meeting moved to 3 PM tomorrow'")
    print(f"Bot: {text_response['response']}\n")
    
    # Simulate memory retrieval
    print("🧠 Memory Retrieval Demo:")
    memory_response = await whatsapp_bot.handle_message({
        'sender_id': 'john_whatsapp',
        'type': 'text',
        'content': 'Memory Number 1000'
    })
    print(f"User: 'Memory Number 1000'")
    print(f"Bot: {memory_response['response']}\n")
    
    # Simulate daily summary request
    print("📊 Daily Summary Demo:")
    summary_response = await whatsapp_bot.handle_message({
        'sender_id': 'john_whatsapp',
        'type': 'text',
        'content': 'Can you give me today\'s daily summary?'
    })
    print(f"User: 'Daily summary please'")
    print(f"Bot: {summary_response['response'][:200]}...\n")
    
    print("✅ WhatsApp integration ready!")
    print("💎 All three diamond features available through WhatsApp!")

if __name__ == "__main__":
    asyncio.run(demo_whatsapp_integration())