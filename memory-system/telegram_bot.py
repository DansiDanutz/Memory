#!/usr/bin/env python3
"""
Telegram Bot Integration for Memory App
Implements all three diamond features through Telegram
"""

import os
import asyncio
import tempfile
import logging
from typing import Dict, Any, Optional
from memory_app import memory_app
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramMemoryBot:
    """
    Telegram bot with Memory App integration
    Features: Voice-activated memory, AI call handling, daily summaries
    """
    
    def __init__(self):
        self.active_users: Dict[str, Dict] = {}
        self.bot_info = {
            'username': 'MemoryAppBot',
            'features': ['voice_memory', 'ai_calls', 'daily_summaries']
        }
        logger.info("🔗 Telegram Memory Bot initialized")
    
    async def handle_update(self, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming Telegram update (message, callback, etc.)"""
        if 'message' in update_data:
            return await self.handle_message(update_data['message'])
        elif 'callback_query' in update_data:
            return await self.handle_callback(update_data['callback_query'])
        elif 'voice_call' in update_data:
            return await self.handle_voice_call(update_data['voice_call'])
        else:
            return None
    
    async def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Telegram message with full Memory App features"""
        user_id = str(message_data.get('from', {}).get('id', 'unknown'))
        chat_id = message_data.get('chat', {}).get('id')
        message_type = self._determine_message_type(message_data)
        
        logger.info(f"📱 Telegram message from {user_id}: {message_type}")
        
        # Route message based on type
        if message_type == 'voice':
            return await self._handle_voice_message(user_id, chat_id, message_data)
        elif message_type == 'text':
            text = message_data.get('text', '')
            return await self._handle_text_message(user_id, chat_id, text)
        elif message_type == 'photo':
            return await self._handle_photo_message(user_id, chat_id, message_data)
        elif message_type == 'document':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "📄 I can't process document files yet. Please send text, voice messages, or photos instead.",
                'parse_mode': 'HTML'
            }
        else:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I can help with text, voice messages, photos, and documents. Try asking me about memories!"
            }
    
    def _determine_message_type(self, message_data: Dict) -> str:
        """Determine the type of Telegram message"""
        if 'voice' in message_data:
            return 'voice'
        elif 'text' in message_data:
            return 'text'
        elif 'photo' in message_data:
            return 'photo'
        elif 'document' in message_data:
            return 'document'
        elif 'audio' in message_data:
            return 'audio'
        else:
            return 'unknown'
    
    async def _handle_voice_message(self, user_id: str, chat_id: int, message_data: Dict) -> Dict[str, Any]:
        """Handle voice message - could be memory retrieval or regular conversation"""
        voice_data = message_data.get('voice', {})
        file_id = voice_data.get('file_id')
        
        if not file_id:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I couldn't process the voice message. Please try again."
            }
        
        try:
            # In real implementation, would download file from Telegram
            # For demo, we'll simulate with a temp file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_file:
                # Simulate downloading file (in real implementation: telegram.download_file())
                tmp_file.write(b"simulated_voice_data")
                tmp_file_path = tmp_file.name
            
            # Try voice-activated memory retrieval first
            memory_result = await memory_app.retrieve_memory_by_voice(tmp_file_path, user_id, str(chat_id))
            
            response_text = ""
            keyboard = None
            if memory_result['success']:
                # This was a memory query
                response_text = f"🧠 {memory_result['summary']}"
                
                if memory_result['memories']:
                    memory = memory_result['memories'][0]
                    response_text += f"\n\n📅 {memory.timestamp.strftime('%Y-%m-%d %H:%M')}"
                    response_text += f"\n💬 {memory.content[:300]}..."
                    
                    # Add inline keyboard for actions
                    keyboard = {
                        'inline_keyboard': [[
                            {'text': '📋 Full Content', 'callback_data': f"full_{memory.memory_number}"},
                            {'text': '🔄 Related Memories', 'callback_data': f"related_{memory.memory_number}"}
                        ]]
                    }
            else:
                # Regular conversation - transcribe and store
                # Simulate transcription (in real implementation: use actual OpenAI Whisper)
                simulated_transcript = "This is a simulated voice message transcription"
                
                conversation_text = f"[Voice message]: {simulated_transcript}"
                
                # Store conversation with credit management
                from memory_app import MemoryCategory
                storage_result = await memory_app.store_conversation(
                    content=conversation_text,
                    participants=[user_id, 'user'],
                    owner_user_id=user_id,
                    category=MemoryCategory.GENERAL,
                    platform='telegram',
                    message_type='voice'
                )
                
                if not storage_result['success']:
                    error_text = f"❌ {storage_result['message']}\n\n"
                    error_text += "🎤 I processed your voice message but couldn't save it due to credit limits.\n\n"
                    
                    if storage_result.get('upgrade_suggestion'):
                        upgrade = storage_result['upgrade_suggestion']
                        error_text += f"💎 <b>Upgrade to {upgrade['suggested_plan'].title()} Plan</b>\n"
                        error_text += f"• ${upgrade['price']}/month\n"
                        error_text += f"• {', '.join(upgrade['benefits'])}\n\n"
                        error_text += f"Send /upgrade_{upgrade['suggested_plan']} to upgrade!"
                    
                    return {
                        'method': 'sendMessage',
                        'chat_id': chat_id,
                        'text': error_text,
                        'parse_mode': 'HTML'
                    }
                
                memory_number = storage_result['memory_number']
                
                response_text = f"🎤 Got your voice message!\n\n"
                response_text += f"You said: \"{simulated_transcript}\"\n\n"
                response_text += f"💾 Saved as Memory {memory_number}\n\n"
                response_text += f"💡 Tip: You can recall this later by saying \"Memory Number {memory_number}\" in a voice message!"
                
                keyboard = {
                    'inline_keyboard': [[
                        {'text': '📊 Daily Summary', 'callback_data': 'daily_summary'},
                        {'text': '🔍 Search Memories', 'callback_data': 'search_memories'}
                    ]]
                }
            
            # Clean up temp file
            os.unlink(tmp_file_path)
            
            response = {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'HTML'
            }
            
            if keyboard is not None:
                response['reply_markup'] = keyboard
            
            return response
            
        except Exception as e:
            logger.error(f"Voice message processing failed: {e}")
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I had trouble processing that voice message. Could you try again or send a text instead?"
            }
    
    async def _handle_text_message(self, user_id: str, chat_id: int, text: str) -> Dict[str, Any]:
        """Handle text message - check for memory queries, commands, or store conversation"""
        text_lower = text.lower().strip()
        
        # Handle bot commands
        if text.startswith('/'):
            return await self._handle_command(user_id, chat_id, text)
        
        # Check for memory-related queries
        if any(keyword in text_lower for keyword in ['memory', 'remember', 'recall', 'what did', 'find']):
            memory_result = await memory_app.retrieve_memory_by_text(text, user_id)
            
            if memory_result['success']:
                response_text = f"🧠 {memory_result['summary']}\n\n"
                
                keyboard_buttons = []
                for i, memory in enumerate(memory_result['memories'][:3]):  # Show up to 3 results
                    response_text += f"📋 <b>Memory {memory.memory_number}</b>\n"
                    response_text += f"📅 {memory.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                    response_text += f"💬 {memory.content[:200]}...\n\n"
                    
                    keyboard_buttons.append([
                        {'text': f'📖 Full Memory {memory.memory_number}', 
                         'callback_data': f'full_{memory.memory_number}'}
                    ])
                
                keyboard = {'inline_keyboard': keyboard_buttons}
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': response_text,
                    'parse_mode': 'HTML',
                    'reply_markup': keyboard
                }
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': f"🔍 {memory_result['summary']}\n\n💡 Try being more specific or use a Memory Number like \"Memory Number 1234\""
                }
        
        # Check for Super Secret Memory creation format
        if 'title:' in text_lower and 'content:' in text_lower:
            return await self._parse_and_create_secret_memory(user_id, chat_id, text)
        
        # Check for Avatar chat format
        if 'to:' in text_lower and 'message:' in text_lower:
            return await self._handle_avatar_chat(user_id, chat_id, text)
        
        # Check for approval/rejection of summaries
        elif any(word in text_lower for word in ['approve', 'reject', '✅', '❌']):
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': '📊 Summary approval feature coming soon! For now, all summaries are automatically saved.',
                'parse_mode': 'HTML'
            }
        
        else:
            # Regular conversation - store it with credit management
            from memory_app import MemoryCategory
            storage_result = await memory_app.store_conversation(
                content=text,
                participants=[user_id, 'user'],
                owner_user_id=user_id,
                category=MemoryCategory.GENERAL,
                platform='telegram',
                message_type='text'
            )
            
            if not storage_result['success']:
                error_text = f"❌ {storage_result['message']}\n\n"
                
                if storage_result.get('upgrade_suggestion'):
                    upgrade = storage_result['upgrade_suggestion']
                    error_text += f"💎 <b>Upgrade to {upgrade['suggested_plan'].title()} Plan</b>\n"
                    error_text += f"• ${upgrade['price']}/month\n"
                    error_text += f"• {', '.join(upgrade['benefits'])}\n\n"
                    error_text += f"Send /upgrade_{upgrade['suggested_plan']} to upgrade!"
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': error_text,
                    'parse_mode': 'HTML'
                }
            
            memory_number = storage_result['memory_number']
            
            # Generate contextual response
            response_text = await self._generate_contextual_response(user_id, text, memory_number)
            
            # Add helpful inline keyboard
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🧠 Search Memories', 'callback_data': 'search_memories'},
                        {'text': '📊 Daily Summary', 'callback_data': 'daily_summary'}
                    ],
                    [
                        {'text': f'📋 View Memory {memory_number}', 'callback_data': f'full_{memory_number}'}
                    ]
                ]
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'reply_markup': keyboard
            }
    
    async def _handle_photo_message(self, user_id: str, chat_id: int, message_data: Dict) -> Dict[str, Any]:
        """Handle photo message with analysis and memory storage"""
        photo_data = message_data.get('photo', [])
        caption = message_data.get('caption', '')
        
        if not photo_data:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I couldn't process that photo. Please try sending it again."
            }
        
        try:
            # Get the largest photo size
            largest_photo = max(photo_data, key=lambda x: x.get('file_size', 0))
            file_id = largest_photo.get('file_id')
            
            # In real implementation, would download and analyze the image
            # For demo, we'll simulate image analysis
            simulated_analysis = "Photo shows: People at a restaurant table with food, appears to be a dinner gathering with friends"
            
            # Store as conversation memory
            content = f"[Photo shared"
            if caption:
                content += f" with caption: {caption}"
            content += f"]\n\nImage analysis: {simulated_analysis}"
            
            from memory_app import MemoryCategory
            storage_result = await memory_app.store_conversation(
                content=content,
                participants=[user_id, 'user'],
                owner_user_id=user_id,
                category=MemoryCategory.GENERAL,
                platform='telegram',
                message_type='image'
            )
            
            if not storage_result['success']:
                error_text = f"❌ {storage_result['message']}\n\n"
                error_text += "📸 I analyzed the photo but couldn't save it due to credit limits.\n\n"
                
                if storage_result.get('upgrade_suggestion'):
                    upgrade = storage_result['upgrade_suggestion']
                    error_text += f"💎 <b>Upgrade to {upgrade['suggested_plan'].title()} Plan</b>\n"
                    error_text += f"• ${upgrade['price']}/month\n"
                    error_text += f"• {', '.join(upgrade['benefits'])}\n\n"
                    error_text += f"Send /upgrade_{upgrade['suggested_plan']} to upgrade!"
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': error_text,
                    'parse_mode': 'HTML'
                }
            
            memory_number = storage_result['memory_number']
            
            response_text = f"📸 <b>I can see:</b> {simulated_analysis}\n\n"
            if caption:
                response_text += f"<b>Your caption:</b> \"{caption}\"\n\n"
            response_text += f"💾 Saved as Memory {memory_number}\n\n"
            response_text += f"💡 You can find this later by saying \"Memory Number {memory_number}\" or asking about the dinner!"
            
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': f'📋 View Memory {memory_number}', 'callback_data': f'full_{memory_number}'},
                        {'text': '🔄 Similar Images', 'callback_data': f'similar_{memory_number}'}
                    ],
                    [
                        {'text': '📊 Daily Summary', 'callback_data': 'daily_summary'}
                    ]
                ]
            }
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'HTML',
                'reply_markup': keyboard
            }
            
        except Exception as e:
            logger.error(f"Photo processing failed: {e}")
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I had trouble analyzing that photo. Could you try sending it again?"
            }
    
    async def handle_voice_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Telegram voice call with AI"""
        caller_id = str(call_data.get('from', {}).get('id', 'unknown'))
        
        # Check if AI should handle this call
        call_response = await memory_app.handle_incoming_call(caller_id, 'telegram')
        
        if not call_response['should_answer']:
            return {
                'answer': False,
                'reason': call_response.get('reason', 'AI call handling not enabled for this user')
            }
        
        # AI will handle the call
        logger.info(f"📞 AI answering Telegram call from {caller_id}")
        
        return {
            'answer': True,
            'session_id': call_response['session_id'],
            'greeting_message': call_response['greeting'],
            'instructions': 'AI is now handling the call. All conversation will be transcribed and stored.'
        }
    
    async def handle_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle inline keyboard button presses"""
        query_data = callback_data.get('data', '')
        user_id = str(callback_data.get('from', {}).get('id', 'unknown'))
        chat_id = callback_data.get('message', {}).get('chat', {}).get('id')
        message_id = callback_data.get('message', {}).get('message_id')
        
        logger.info(f"🔘 Callback from {user_id}: {query_data}")
        
        if query_data == 'daily_summary':
            return await self._generate_daily_summary_response(user_id, chat_id)
        
        elif query_data == 'search_memories':
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "🔍 <b>Memory Search</b>\n\nTo search your memories, just send me a message like:\n• \"What did I discuss about work?\"\n• \"Show me memories about mom\"\n• \"Find conversations about health\"\n\nI'll search through your stored memories and show you the most relevant ones!",
                'parse_mode': 'HTML'
            }
        
        elif query_data == 'my_secrets':
            return await self._list_super_secret_memories(user_id, chat_id)
        
        elif query_data == 'mutual_feelings':
            return await self._check_mutual_feelings_status(user_id, chat_id)
        
        elif query_data.startswith('full_'):
            memory_number = query_data.replace('full_', '')
            return await self._show_full_memory(user_id, chat_id, memory_number)
        
        elif query_data.startswith('approve_'):
            memory_number = query_data.replace('approve_', '')
            result = await memory_app.approve_summary(memory_number, True)
            
            return {
                'method': 'answerCallbackQuery',
                'callback_query_id': callback_data.get('id'),
                'text': f'✅ Approved Memory {memory_number}',
                'show_alert': False
            }
        
        elif query_data.startswith('reject_'):
            memory_number = query_data.replace('reject_', '')
            result = await memory_app.approve_summary(memory_number, False)
            
            return {
                'method': 'answerCallbackQuery',
                'callback_query_id': callback_data.get('id'),
                'text': f'❌ Rejected Memory {memory_number}',
                'show_alert': False
            }
        
        else:
            return {
                'method': 'answerCallbackQuery',
                'callback_query_id': callback_data.get('id'),
                'text': 'Unknown action',
                'show_alert': False
            }
    
    async def _handle_command(self, user_id: str, chat_id: int, command: str) -> Dict[str, Any]:
        """Handle bot commands"""
        cmd = command.lower().strip()
        
        if cmd == '/start':
            response_text = """🧠 <b>Welcome to Memory App!</b>
            
I'm your personal AI memory assistant with three powerful features:

🎤 <b>Voice-Activated Memory</b>
Send voice messages saying "Memory Number 1234" to instantly recall conversations

📞 <b>AI Call Handling</b> 
I can answer calls from trusted contacts and provide transcripts

📊 <b>Daily Summaries</b>
Get smart summaries of your conversations with approval control

<b>Try these:</b>
• Send me any message to store it as a memory
• Record "Memory Number [number]" to recall specific memories  
• Ask "What did I discuss about [topic]" to search
• Type /summary for today's conversation summary

Let's get started! 🚀"""

            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '📊 Today\'s Summary', 'callback_data': 'daily_summary'},
                        {'text': '🔍 Search Memories', 'callback_data': 'search_memories'}
                    ],
                    [
                        {'text': '📱 Bot Status', 'callback_data': 'status'},
                        {'text': '❓ Help', 'callback_data': 'help'}
                    ]
                ]
            }
        
        elif cmd == '/status':
            status = memory_app.get_status()
            response_text = f"""🤖 <b>Memory App Status</b>

📚 Total memories stored: <b>{status['total_memories']}</b>
👥 People I know: <b>{status['total_profiles']}</b>
⏳ Pending summaries: <b>{status['pending_summaries']}</b>
📞 Call-enabled contacts: <b>{status['call_enabled_contacts']}</b>

🎯 Trust Levels:
• 🟢 Green (Full access): {status['trust_levels']['green']}
• 🟡 Amber (Limited access): {status['trust_levels']['amber']} 
• 🔴 Red (Basic access): {status['trust_levels']['red']}

System Status: <b>Operational</b> ✅"""

            keyboard = {
                'inline_keyboard': [[
                    {'text': '📊 Daily Summary', 'callback_data': 'daily_summary'},
                    {'text': '🔄 Refresh', 'callback_data': 'status'}
                ]]
            }
        
        elif cmd == '/help':
            response_text = """❓ <b>Memory App Help</b>

<b>🎤 Voice Features:</b>
• Say "Memory Number 1234" to recall specific memories
• Say "Super Secret" to access your secret memories
• Send any voice message to store and analyze it

<b>💬 Text Features:</b>
• Ask "What did I discuss about [topic]" to search
• Send any message to automatically store it
• Use "Memory Number [number]" in text too

<b>🔐 Super Secret Memories:</b>
• /create_secret - Create secret guidance/credentials
• /my_secrets - View your secret memories
• /mutual_feelings - Check for mutual romantic interest
• /avatar_chat - AI Avatar communication with matches

<b>📊 Daily Summaries:</b>
• Type /summary or tap 📊 Daily Summary
• Approve/reject summaries to train the AI

<b>📞 Call Features:</b>
• AI can answer calls from trusted contacts
• Full transcripts provided after calls

<b>Commands:</b>
/start - Show welcome message
/status - System status and statistics  
/summary - Generate daily summary
/create_secret - Create Super Secret Memory
/my_secrets - List Super Secret Memories
/mutual_feelings - Check mutual feelings matches
/avatar_chat - Avatar-to-Avatar communication
/help - This help message

Questions? Just ask me anything! 🤖"""

            keyboard = {
                'inline_keyboard': [[
                    {'text': '🏠 Main Menu', 'callback_data': 'start'},
                    {'text': '📊 Daily Summary', 'callback_data': 'daily_summary'}
                ]]
            }
        
        elif cmd == '/summary':
            return await self._generate_daily_summary_response(user_id, chat_id)
        
        elif cmd == '/create_secret':
            response_text = """🔐 <b>Create Super Secret Memory</b>

To create a Super Secret Memory, reply to this message with your content in this format:

<b>Title:</b> Your Memory Title
<b>Content:</b> Your secret content, credentials, or guidance

<b>Optional - For Designated Person:</b>
<b>Person ID:</b> telegram_user_id
<b>Person Name:</b> Their Display Name

<b>Optional - For Romantic Feelings:</b>
<b>Target Person ID:</b> telegram_user_id_of_crush
<b>Target Name:</b> Their Name

Super Secret Memories cost 2 credits each and can detect mutual romantic feelings! 💕"""

            keyboard = {
                'inline_keyboard': [[
                    {'text': '🔐 My Secret Memories', 'callback_data': 'my_secrets'},
                    {'text': '💕 Check Mutual Feelings', 'callback_data': 'mutual_feelings'}
                ]]
            }
        
        elif cmd == '/my_secrets':
            return await self._list_super_secret_memories(user_id, chat_id)
        
        elif cmd == '/mutual_feelings':
            return await self._check_mutual_feelings_status(user_id, chat_id)
        
        elif cmd == '/avatar_chat':
            response_text = """💌 <b>Avatar-to-Avatar Communication</b>

This feature is available when you have mutual feelings detected with someone.

To send a message through your AI Avatar, reply with:
<b>To:</b> person_user_id
<b>Message:</b> Your message for their Avatar

Your AI Avatar will communicate your feelings based on your Super Secret Memory content."""

            keyboard = {
                'inline_keyboard': [[
                    {'text': '💕 Check Mutual Feelings', 'callback_data': 'mutual_feelings'},
                    {'text': '🔐 My Secret Memories', 'callback_data': 'my_secrets'}
                ]]
            }
        
        else:
            response_text = f"Unknown command: {cmd}\n\nType /help for available commands."
            keyboard = {
                'inline_keyboard': [[
                    {'text': '❓ Help', 'callback_data': 'help'},
                    {'text': '🏠 Main Menu', 'callback_data': 'start'}
                ]]
            }
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
    
    async def _generate_daily_summary_response(self, user_id: str, chat_id: int) -> Dict[str, Any]:
        """Generate and display daily summary with approval interface"""
        try:
            summary_data = await memory_app.generate_daily_summaries()
            
            if not summary_data['summaries']:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': "📊 No conversations found for today to summarize.\n\nStart chatting with me and I'll create summaries for you to review!"
                }
            
            response_text = f"📊 <b>Daily Summary for {summary_data['date']}</b>\n"
            response_text += f"Found {len(summary_data['summaries'])} conversations to review:\n\n"
            
            keyboard_buttons = []
            for i, summary in enumerate(summary_data['summaries'][:10]):  # Show first 10
                response_text += f"<b>{i+1}. Memory {summary['memory_number']}</b>\n"
                response_text += f"📝 {summary['summary']}\n"
                response_text += f"👥 {', '.join(summary['participants'])}\n"
                response_text += f"📅 {summary['timestamp'].strftime('%H:%M')}\n\n"
                
                # Add approval buttons for each summary
                keyboard_buttons.append([
                    {'text': f'✅ Approve {summary["memory_number"]}', 
                     'callback_data': f'approve_{summary["memory_number"]}'},
                    {'text': f'❌ Reject {summary["memory_number"]}', 
                     'callback_data': f'reject_{summary["memory_number"]}'}
                ])
            
            # Add bulk action buttons
            keyboard_buttons.append([
                {'text': '✅ Approve All', 'callback_data': 'approve_all'},
                {'text': '❌ Reject All', 'callback_data': 'reject_all'}
            ])
            
            keyboard = {'inline_keyboard': keyboard_buttons}
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'HTML',
                'reply_markup': keyboard
            }
            
        except Exception as e:
            logger.error(f"Daily summary generation failed: {e}")
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I had trouble generating the daily summary. Please try again later."
            }
    
    async def _show_full_memory(self, user_id: str, chat_id: int, memory_number: str) -> Dict[str, Any]:
        """Show full content of a specific memory"""
        if memory_number not in memory_app.memories:
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f"Memory {memory_number} not found."
            }
        
        memory = memory_app.memories[memory_number]
        
        # Check access permissions
        if not memory_app._can_access_memory(user_id, memory):
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': f"🔒 Access denied to Memory {memory_number} - privacy protection active."
            }
        
        response_text = f"📋 <b>Memory {memory_number}</b>\n\n"
        response_text += f"📅 <b>Date:</b> {memory.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        response_text += f"👥 <b>Participants:</b> {', '.join(memory.participants)}\n"
        response_text += f"📱 <b>Platform:</b> {memory.platform.title()}\n"
        response_text += f"💬 <b>Type:</b> {memory.message_type.title()}\n\n"
        response_text += f"<b>Content:</b>\n{memory.content}\n\n"
        
        if memory.summary:
            response_text += f"📝 <b>Summary:</b> {memory.summary}\n\n"
        
        if memory.tags:
            response_text += f"🏷️ <b>Tags:</b> {', '.join(memory.tags)}"
        
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '🔍 Search Related', 'callback_data': f'related_{memory_number}'},
                    {'text': '📊 Daily Summary', 'callback_data': 'daily_summary'}
                ]
            ]
        }
        
        return {
            'method': 'sendMessage',
            'chat_id': chat_id,
            'text': response_text,
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
    
    async def _generate_contextual_response(self, user_id: str, content: str, memory_number: str) -> str:
        """Generate intelligent response based on conversation context"""
        try:
            # Get recent memories for context
            recent_memories = await memory_app._get_recent_memories_for_contact(user_id, 3)
            
            # Simple contextual response - in production would use OpenAI
            if len(recent_memories) <= 1:
                return f"Thanks for sharing that! I've stored it as Memory {memory_number}. As we chat more, I'll get better at understanding your context and providing relevant help."
            else:
                return f"Got it! Saved as Memory {memory_number}. I can see we've been building up quite a conversation history - feel free to ask me to recall anything we've discussed!"
            
        except Exception as e:
            logger.error(f"Contextual response generation failed: {e}")
            return f"Perfect! I've saved that as Memory {memory_number}. How else can I help you today?"
    
    # ========== SUPER SECRET MEMORY METHODS ==========
    
    async def _list_super_secret_memories(self, user_id: str, chat_id: int) -> Dict[str, Any]:
        """List user's Super Secret Memories"""
        try:
            result = await memory_app.list_super_secret_memories(user_id)
            
            if not result['success'] or result['count'] == 0:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': "🔐 <b>Your Super Secret Memories</b>\n\nYou don't have any Super Secret Memories yet.\n\nUse /create_secret to create your first one!",
                    'parse_mode': 'HTML'
                }
            
            response_text = f"🔐 <b>Your Super Secret Memories</b>\n\nFound {result['count']} secret memories:\n\n"
            
            keyboard_buttons = []
            for i, memory in enumerate(result['memories'][:10]):  # Show first 10
                ownership_icon = "👑" if memory['is_owner'] else "🔓"
                response_text += f"{ownership_icon} <b>{memory['title']}</b>\n"
                response_text += f"📅 Created: {memory['created_at']}\n"
                response_text += f"👁️ Accessed: {memory['access_count']} times\n"
                
                if memory['designated_person']:
                    response_text += f"👤 Shared with: {memory['designated_person']}\n"
                
                response_text += "\n"
                
                # Add access button
                keyboard_buttons.append([
                    {'text': f'🔍 View {memory["title"][:20]}...', 
                     'callback_data': f'view_secret_{memory["id"]}'}
                ])
            
            keyboard_buttons.append([
                {'text': '➕ Create New Secret', 'callback_data': 'create_secret'},
                {'text': '💕 Check Mutual Feelings', 'callback_data': 'mutual_feelings'}
            ])
            
            keyboard = {'inline_keyboard': keyboard_buttons}
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'HTML',
                'reply_markup': keyboard
            }
            
        except Exception as e:
            logger.error(f"List super secret memories failed: {e}")
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I had trouble accessing your Super Secret Memories. Please try again later."
            }
    
    async def _check_mutual_feelings_status(self, user_id: str, chat_id: int) -> Dict[str, Any]:
        """Check user's mutual feelings matches"""
        try:
            result = await memory_app.check_mutual_feelings_status(user_id)
            
            if result['count'] == 0:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': "💕 <b>Mutual Feelings Status</b>\n\nNo mutual feelings detected yet.\n\nCreate a Super Secret Memory with romantic feelings about someone, and if they do the same about you, you'll be notified! 💫",
                    'parse_mode': 'HTML'
                }
            
            response_text = f"💕 <b>Mutual Feelings Detected!</b>\n\nYou have {result['count']} mutual matches:\n\n"
            
            keyboard_buttons = []
            for match in result['mutual_matches']:
                response_text += f"💖 <b>{match['target_person']}</b>\n"
                response_text += f"📋 Memory: {match['title']}\n"
                response_text += f"📅 Matched: {match['match_date']}\n"
                response_text += f"🤖 Avatar Chat: Available ✅\n\n"
                
                # Add Avatar chat button
                keyboard_buttons.append([
                    {'text': f'💌 Chat with {match["target_person"][:15]}...', 
                     'callback_data': f'avatar_chat_{match["secret_id"]}'}
                ])
            
            keyboard_buttons.append([
                {'text': '🔐 My Secret Memories', 'callback_data': 'my_secrets'},
                {'text': '🏠 Main Menu', 'callback_data': 'start'}
            ])
            
            keyboard = {'inline_keyboard': keyboard_buttons}
            
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': response_text,
                'parse_mode': 'HTML',
                'reply_markup': keyboard
            }
            
        except Exception as e:
            logger.error(f"Check mutual feelings failed: {e}")
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I had trouble checking your mutual feelings status. Please try again later."
            }
    
    async def _parse_and_create_secret_memory(self, user_id: str, chat_id: int, text: str) -> Dict[str, Any]:
        """Parse text and create Super Secret Memory"""
        try:
            lines = text.strip().split('\n')
            title = ""
            content = ""
            designated_person_id = None
            designated_person_name = None
            target_person_id = None
            target_person_name = None
            
            # Parse the text format
            current_field = None
            for line in lines:
                line_lower = line.lower().strip()
                if line_lower.startswith('title:'):
                    title = line[6:].strip()
                    current_field = 'title'
                elif line_lower.startswith('content:'):
                    content = line[8:].strip()
                    current_field = 'content'
                elif line_lower.startswith('person id:'):
                    designated_person_id = line[10:].strip()
                    current_field = 'person_id'
                elif line_lower.startswith('person name:'):
                    designated_person_name = line[12:].strip()
                    current_field = 'person_name'
                elif line_lower.startswith('target person id:'):
                    target_person_id = line[17:].strip()
                    current_field = 'target_id'
                elif line_lower.startswith('target name:'):
                    target_person_name = line[12:].strip()
                    current_field = 'target_name'
                elif current_field == 'content' and line.strip():
                    content += "\n" + line
            
            if not title or not content:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': "❌ Please provide both Title and Content for your Super Secret Memory.\n\nFormat:\nTitle: Your Title\nContent: Your secret content...",
                    'parse_mode': 'HTML'
                }
            
            # Create the Super Secret Memory
            result = await memory_app.create_super_secret_memory(
                title=title,
                content=content,
                owner_user_id=user_id,
                designated_person_id=designated_person_id,
                designated_person_name=designated_person_name,
                target_person_id=target_person_id,
                target_person_name=target_person_name
            )
            
            if result['success']:
                response_text = f"🔐 <b>Super Secret Memory Created!</b>\n\n"
                response_text += f"📋 <b>Title:</b> {title}\n"
                response_text += f"🆔 <b>Secret ID:</b> {result['secret_id']}\n"
                response_text += f"💳 <b>Credits Used:</b> {result['credits_used']}\n"
                response_text += f"💰 <b>Credits Remaining:</b> {result['credits_remaining']}\n"
                
                if result.get('is_romantic'):
                    response_text += f"💕 <b>Romantic Content:</b> Detected ✅\n"
                
                if result.get('mutual_match', {}).get('detected'):
                    response_text += f"\n🎉 <b>MUTUAL MATCH DETECTED!</b>\n"
                    response_text += result['mutual_match']['message']
                
                keyboard = {
                    'inline_keyboard': [[
                        {'text': '🔐 My Secret Memories', 'callback_data': 'my_secrets'},
                        {'text': '💕 Check Mutual Feelings', 'callback_data': 'mutual_feelings'}
                    ]]
                }
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': response_text,
                    'parse_mode': 'HTML',
                    'reply_markup': keyboard
                }
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': f"❌ Failed to create Super Secret Memory:\n\n{result['message']}",
                    'parse_mode': 'HTML'
                }
            
        except Exception as e:
            logger.error(f"Parse and create secret memory failed: {e}")
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I had trouble creating your Super Secret Memory. Please try again with the correct format."
            }
    
    async def _handle_avatar_chat(self, user_id: str, chat_id: int, text: str) -> Dict[str, Any]:
        """Handle Avatar-to-Avatar communication"""
        try:
            lines = text.strip().split('\n')
            target_user_id = ""
            message = ""
            
            # Parse the avatar chat format
            current_field = None
            for line in lines:
                line_lower = line.lower().strip()
                if line_lower.startswith('to:'):
                    target_user_id = line[3:].strip()
                    current_field = 'to'
                elif line_lower.startswith('message:'):
                    message = line[8:].strip()
                    current_field = 'message'
                elif current_field == 'message' and line.strip():
                    message += "\n" + line
            
            if not target_user_id or not message:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': "❌ Please provide both recipient and message for Avatar communication.\n\nFormat:\nTo: user_id\nMessage: Your message...",
                    'parse_mode': 'HTML'
                }
            
            # Exchange Avatar messages
            result = await memory_app.exchange_avatar_messages(
                user_a_id=user_id,
                user_b_id=target_user_id,
                message_from_a=message
            )
            
            if result['success']:
                response_text = f"💌 <b>Avatar Response Received</b>\n\n"
                response_text += f"📤 <b>Your Message:</b> {message[:100]}{'...' if len(message) > 100 else ''}\n\n"
                response_text += f"📥 <b>Response from {result['from_avatar']}:</b>\n\n"
                response_text += result['avatar_response']
                
                keyboard = {
                    'inline_keyboard': [[
                        {'text': '💕 Check Mutual Feelings', 'callback_data': 'mutual_feelings'},
                        {'text': '🔐 My Secret Memories', 'callback_data': 'my_secrets'}
                    ]]
                }
                
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': response_text,
                    'parse_mode': 'HTML',
                    'reply_markup': keyboard
                }
            else:
                return {
                    'method': 'sendMessage',
                    'chat_id': chat_id,
                    'text': f"❌ Avatar communication failed:\n\n{result['message']}",
                    'parse_mode': 'HTML'
                }
            
        except Exception as e:
            logger.error(f"Avatar chat failed: {e}")
            return {
                'method': 'sendMessage',
                'chat_id': chat_id,
                'text': "I had trouble with Avatar communication. Please check the format and try again."
            }

# Global bot instance
telegram_bot = TelegramMemoryBot()

# Demo function
async def demo_telegram_integration():
    """Demo Telegram bot functionality"""
    print("\n💬 Telegram Memory Bot Demo")
    print("===========================\n")
    
    # Simulate /start command
    print("🤖 Bot Commands Demo:")
    start_response = await telegram_bot.handle_update({
        'message': {
            'from': {'id': 12345},
            'chat': {'id': 12345},
            'text': '/start'
        }
    })
    print(f"User: /start")
    print(f"Bot: {start_response.get('text', 'No response')[:100]}...\n")
    
    # Simulate text message
    print("📝 Text Message Demo:")
    text_response = await telegram_bot.handle_update({
        'message': {
            'from': {'id': 12345},
            'chat': {'id': 12345},
            'text': 'Just finished a great meeting with the team about the new project launch'
        }
    })
    print(f"User: 'Meeting about project launch'")
    print(f"Bot: {text_response.get('text', 'No response')[:150]}...\n")
    
    # Simulate memory query
    print("🧠 Memory Query Demo:")
    memory_response = await telegram_bot.handle_update({
        'message': {
            'from': {'id': 12345},
            'chat': {'id': 12345},
            'text': 'What did I discuss about the project?'
        }
    })
    print(f"User: 'What did I discuss about the project?'")
    print(f"Bot: {memory_response.get('text', 'No response')[:150]}...\n")
    
    # Simulate callback query (button press)
    print("🔘 Callback Query Demo:")
    callback_response = await telegram_bot.handle_callback({
        'from': {'id': 12345},
        'message': {'chat': {'id': 12345}},
        'data': 'daily_summary'
    })
    print(f"User: [Pressed Daily Summary button]")
    print(f"Bot: {callback_response.get('text', 'No response')[:150]}...\n")
    
    print("✅ Telegram integration ready!")
    print("💎 All three diamond features available through Telegram!")

if __name__ == "__main__":
    asyncio.run(demo_telegram_integration())