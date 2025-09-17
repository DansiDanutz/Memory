#!/usr/bin/env python3
"""
WhatsApp Webhook Handler
Processes incoming WhatsApp messages and manages conversations
"""

import os
import json
import base64
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List

from memory.classifier import MessageClassifier
from memory.storage import MemoryStorage
from voice.azure_voice import AzureVoiceService
from voice.guard import VoiceGuard
from security.session_store import SessionStore
from security.audit import get_audit_logger, AuditAction
from tenancy import get_tenancy_manager, get_rbac_manager
from services.whatsapp_voice_collector import voice_collector
import branding

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    """Handle WhatsApp webhook messages and conversations"""
    
    def __init__(self, memory_storage: MemoryStorage, session_store: SessionStore):
        self.memory_storage = memory_storage
        self.session_store = session_store
        self.classifier = MessageClassifier()
        self.voice_service = AzureVoiceService()
        self.voice_guard = VoiceGuard()
        
        # Business features
        self.tenancy_manager = get_tenancy_manager()
        self.rbac_manager = get_rbac_manager()
        self.audit_logger = get_audit_logger()
        
        # WhatsApp Cloud API configuration
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        
        # Track active conversations and first-time users
        self.active_conversations = {}
        self.first_time_users = set()
        
        logger.info("✅ WhatsApp handler initialized")
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming WhatsApp webhook data"""
        try:
            # Extract message data from webhook
            entry = webhook_data.get("entry", [])[0] if webhook_data.get("entry") else {}
            changes = entry.get("changes", [])[0] if entry.get("changes") else {}
            value = changes.get("value", {})
            
            # Check if it's a message
            messages = value.get("messages", [])
            if not messages:
                return {"status": "no_message"}
            
            message = messages[0]
            from_number = message.get("from")
            message_id = message.get("id")
            message_type = message.get("type")
            
            # Process based on message type
            if message_type == "text":
                response = await self._handle_text_message(from_number, message)
            elif message_type == "audio":
                response = await self._handle_audio_message(from_number, message)
            elif message_type == "voice":
                response = await self._handle_voice_message(from_number, message)
            else:
                response = await self._send_reply(
                    from_number,
                    "I can process text and voice messages. Please send me a memory to save!"
                )
            
            # Mark message as read
            await self._mark_as_read(message_id)
            
            return {"status": "processed", "response": response}
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_text_message(self, from_number: str, message: Dict) -> Dict:
        """Handle text message"""
        text = message.get("text", {}).get("body", "")
        
        # Check if first-time user
        if from_number not in self.first_time_users:
            self.first_time_users.add(from_number)
            stats = await self.memory_storage.get_user_stats(from_number)
            if stats.get('total', 0) == 0:
                await self._send_reply(from_number, branding.FIRST_TIME_MESSAGE)
        
        # Check for commands
        if text.startswith("/"):
            return await self._handle_command(from_number, text)
        
        # Check if user has active session
        has_session = self.session_store.has_active_session(from_number)
        
        # Classify the message
        category = await self.classifier.classify(text, from_number)
        
        # Check if authentication needed for secret categories
        if category in ["SECRET", "ULTRA_SECRET"] and not has_session:
            await self._send_reply(
                from_number,
                branding.AUTH_REQUIRED_MESSAGE.format(category=category)
            )
            self.active_conversations[from_number] = {"awaiting_auth": True}
            return {"status": "auth_required", "category": category}
        
        # Get user context for tenancy
        user_tenant = self.tenancy_manager.get_user_tenant(from_number)
        user_dept = self.tenancy_manager.get_user_department(from_number)
        user_role = self.tenancy_manager.get_user_role(from_number)
        
        # Check RBAC permissions
        if not self.rbac_manager.check_memory_access(user_role, category, "write"):
            await self._send_reply(
                from_number,
                f"❌ Access denied. Your role ({user_role}) cannot write {category} memories."
            )
            self.audit_logger.log(
                AuditAction.ACCESS_DENIED,
                from_number,
                {"operation": "store_memory", "category": category},
                tenant_id=user_tenant.id if user_tenant else None
            )
            return {"status": "access_denied"}
        
        # Store the memory with tenant context
        memory_id = await self.memory_storage.store_memory(
            user_phone=from_number,
            content=text,
            category=category,
            timestamp=datetime.now(),
            tenant_id=user_tenant.id if user_tenant else None,
            department_id=user_dept.id if user_dept else None
        )
        
        # Audit log the storage
        self.audit_logger.log(
            AuditAction.MEMORY_STORED,
            from_number,
            {"memory_id": memory_id, "category": category},
            tenant_id=user_tenant.id if user_tenant else None,
            department_id=user_dept.id if user_dept else None,
            sensitivity=category
        )
        
        # Send confirmation
        auth_note = "\n🔓 Session active" if has_session else ""
        await self._send_reply(
            from_number,
            branding.MEMORY_SAVED_MESSAGE.format(
                category=category,
                memory_id=memory_id,
                auth_note=auth_note
            )
        )
        
        return {"status": "stored", "memory_id": memory_id, "category": category}
    
    async def _handle_audio_message(self, from_number: str, message: Dict) -> Dict:
        """Handle audio/voice message for authentication, voice collection, or memory"""
        audio = message.get("audio", {})
        media_id = audio.get("id")
        
        # First, collect the voice sample for voice cloning (if enabled)
        voice_collection_enabled = os.getenv("VOICE_COLLECTION_ENABLED", "true").lower() == "true"
        if voice_collection_enabled:
            try:
                # Process voice sample collection
                collection_result = await voice_collector.process_voice_message(
                    from_number=from_number,
                    message=message,
                    auto_clone=True
                )
                
                # Send progress update if collection was successful
                if collection_result.get("status") == "success":
                    if collection_result.get("clone_triggered"):
                        # Voice clone was triggered
                        await self._send_reply(
                            from_number,
                            collection_result.get("message", "🎉 Voice cloning started!")
                        )
                    elif collection_result.get("user_message"):
                        # Send progress message
                        await self._send_reply(
                            from_number,
                            collection_result.get("user_message")
                        )
                
                logger.info(f"Voice sample collected for {from_number}: {collection_result.get('status')}")
            except Exception as e:
                logger.error(f"Error collecting voice sample: {e}")
                # Continue with normal processing even if collection fails
        
        # Download audio file for authentication/transcription
        audio_data = await self._download_media(media_id)
        
        # Check if this is for authentication
        if from_number in self.active_conversations and \
           self.active_conversations[from_number].get("awaiting_auth"):
            
            # Perform voice authentication
            auth_result = await self.voice_guard.authenticate(from_number, audio_data)
            
            if auth_result["authenticated"]:
                # Create session
                session_token = self.session_store.create_session(from_number)
                
                await self._send_reply(
                    from_number,
                    branding.SUCCESS_MESSAGES["AUTH_SUCCESS"]
                )
                
                # Clear auth flag
                self.active_conversations[from_number]["awaiting_auth"] = False
                
                return {"status": "authenticated", "session_token": session_token}
            else:
                await self._send_reply(
                    from_number,
                    f"❌ Authentication failed: {auth_result.get('message', 'Invalid passphrase')}\n\nPlease try again."
                )
                return {"status": "auth_failed"}
        
        # Otherwise, transcribe and save as memory
        transcription = await self.voice_service.transcribe(audio_data)
        
        if transcription:
            # Process as text message
            message["text"] = {"body": transcription}
            return await self._handle_text_message(from_number, message)
        else:
            await self._send_reply(
                from_number,
                "Sorry, I couldn't transcribe your voice message. Please try again or send a text message."
            )
            return {"status": "transcription_failed"}
    
    async def _handle_voice_message(self, from_number: str, message: Dict) -> Dict:
        """Handle voice call message"""
        return await self._handle_audio_message(from_number, message)
    
    async def _handle_command(self, from_number: str, command: str) -> Dict:
        """Handle command messages"""
        cmd = command.lower().strip()
        
        if cmd == "/help":
            await self._send_reply(from_number, branding.HELP_MESSAGE)
            return {"status": "help_shown"}
        
        elif cmd in ["/start", "/begin"]:
            await self._send_reply(from_number, branding.WELCOME_MESSAGE)
            return {"status": "welcome_shown"}
        
        elif cmd == "/about":
            await self._send_reply(from_number, branding.ABOUT_MESSAGE)
            return {"status": "about_shown"}
        
        elif cmd.startswith("/search"):
            parts = command[7:].strip().split(maxsplit=1)
            if not parts:
                await self._send_reply(from_number, "Please provide a search query. Example: /search birthday")
                return {"status": "search_query_required"}
            
            # Check for category-specific search
            query = parts[0]
            category_filter = parts[1].upper() if len(parts) > 1 else None
            
            # Search memories
            from memory.search import MemorySearch
            searcher = MemorySearch(self.memory_storage)
            results = await searcher.search(from_number, query, category=category_filter)
            
            if results:
                response = branding.SEARCH_RESULTS_HEADER.format(query=query, count=len(results))
                for idx, result in enumerate(results[:5], 1):
                    response += branding.format_memory_display(result)
                if len(results) > 5:
                    response += f"\n... and {len(results) - 5} more results"
            else:
                response = branding.NO_RESULTS_MESSAGE.format(query=query)
            
            await self._send_reply(from_number, response)
            return {"status": "search_complete", "results": len(results)}
        
        elif cmd == "/recent":
            memories = await self.memory_storage.get_recent_memories(from_number, limit=5)
            
            if memories:
                response = "📝 Recent memories:\n\n"
                for idx, memory in enumerate(memories, 1):
                    response += f"{idx}. [{memory['category']}] {memory['content_preview']}...\n"
                    response += f"   📅 {memory['timestamp']}\n\n"
            else:
                response = "No memories found. Start saving memories by sending messages!"
            
            await self._send_reply(from_number, response)
            return {"status": "recent_shown"}
        
        elif cmd == "/categories":
            stats = await self.memory_storage.get_category_stats(from_number)
            
            response = "📊 *Memory Categories*\n\n"
            for category, description in branding.CATEGORY_DESCRIPTIONS.items():
                count = stats.get(category, 0)
                response += f"{description}\n"
                response += f"  └─ {count} memories stored\n\n"
            
            await self._send_reply(from_number, response)
            return {"status": "categories_shown"}
        
        elif cmd in ["/auth", "/enroll", "/authenticate"]:
            # Check if enrollment needed
            has_passphrase = await self.voice_guard.has_passphrase(from_number)
            
            if not has_passphrase and cmd == "/enroll":
                await self._send_reply(from_number, branding.ENROLLMENT_PROMPT)
                self.active_conversations[from_number] = {"awaiting_enrollment": True}
                return {"status": "awaiting_enrollment"}
            
            # Set auth flag
            if from_number not in self.active_conversations:
                self.active_conversations[from_number] = {}
            self.active_conversations[from_number]["awaiting_auth"] = True
            
            await self._send_reply(
                from_number,
                "🎤 Please send a voice message with your passphrase to authenticate.\n\nYour passphrase should be at least 10 words long."
            )
            return {"status": "awaiting_auth"}
        
        elif cmd == "/logout":
            self.session_store.invalidate_all_sessions(from_number)
            await self._send_reply(from_number, branding.SUCCESS_MESSAGES["LOGOUT_SUCCESS"])
            return {"status": "logged_out"}
        
        elif cmd == "/stats":
            stats = await self.memory_storage.get_user_stats(from_number)
            has_passphrase = await self.voice_guard.has_passphrase(from_number)
            sessions = self.session_store.get_active_session_count(from_number)
            
            stats["voice_enrolled"] = has_passphrase
            stats["active_sessions"] = sessions
            
            response = branding.format_stats_display(stats)
            await self._send_reply(from_number, response)
            return {"status": "stats_shown"}
        
        elif cmd in ["/today", "/yesterday"]:
            # Get date-specific memories
            from datetime import timedelta
            target_date = datetime.now()
            if cmd == "/yesterday":
                target_date -= timedelta(days=1)
            
            memories = await self.memory_storage.get_memories_by_date(from_number, target_date)
            
            if memories:
                response = f"📅 *Memories from {target_date.strftime('%Y-%m-%d')}*\n\n"
                for memory in memories[:10]:
                    response += branding.format_memory_display(memory)
            else:
                response = f"No memories found for {target_date.strftime('%Y-%m-%d')}"
            
            await self._send_reply(from_number, response)
            return {"status": "date_memories_shown"}
        
        elif cmd == "/status":
            has_session = self.session_store.has_active_session(from_number)
            has_passphrase = await self.voice_guard.has_passphrase(from_number)
            
            status = "🟢 Authenticated" if has_session else "🔴 Not authenticated"
            enrollment = "✅ Enrolled" if has_passphrase else "❌ Not enrolled"
            
            response = f"""*Authentication Status*\n\nSession: {status}\nVoice Enrollment: {enrollment}\n\nUse /enroll to set up voice authentication."""
            await self._send_reply(from_number, response)
            return {"status": "status_shown"}
        
        elif cmd in ["/upgrade", "/premium", "/subscription"]:
            # Check subscription status
            try:
                from gamification.subscription_service import get_subscription_service
                subscription_service = get_subscription_service()
                
                status = subscription_service.get_subscription_status(from_number)
                eligibility = subscription_service.get_upgrade_eligibility(from_number)
                
                if status.get('is_premium'):
                    response = "🌟 *Premium Status Active*\n\n"
                    response += "You have full access to:\n"
                    response += "✅ Voice Avatar Generation\n"
                    response += "✅ Extended Memory Limits\n"
                    response += "✅ Priority Support\n"
                    response += "✅ Advanced Features\n\n"
                    response += "Thank you for being a premium member!"
                else:
                    response = "🔓 *Unlock Premium Features*\n\n"
                    
                    if eligibility.get('has_locked_avatars'):
                        response += f"🎉 Your {eligibility['locked_avatar_count']} voice avatar(s) are ready!\n\n"
                    
                    response += "*Premium Benefits:*\n"
                    for feature in eligibility.get('upgrade_options', [{}])[0].get('features', []):
                        response += f"• {feature}\n"
                    
                    if eligibility.get('special_offer'):
                        response += f"\n🎁 *Special Offer:*\n{eligibility['special_offer']}\n"
                    
                    response += "\n💳 *Pricing:* $9.99/month\n"
                    response += "\n_Reply 'UPGRADE' to unlock premium features!_"
                
                await self._send_reply(from_number, response)
                return {"status": "upgrade_info_shown"}
                
            except Exception as e:
                logger.error(f"Error checking upgrade status: {e}")
                response = "Unable to check upgrade status. Please try again later."
                await self._send_reply(from_number, response)
                return {"status": "error"}
        
        elif cmd.upper() == "UPGRADE":
            # Process upgrade request (simulation for demo)
            try:
                from gamification.subscription_service import get_subscription_service
                subscription_service = get_subscription_service()
                
                result = await subscription_service.simulate_upgrade(from_number, "premium")
                
                if result.get('success'):
                    response = "🎉 *Welcome to Premium!*\n\n"
                    response += f"{result.get('message', '')}\n\n"
                    
                    if result.get('unlocked_avatars'):
                        response += f"🔓 Unlocked {len(result['unlocked_avatars'])} voice avatar(s)!\n\n"
                    
                    response += "*Next Steps:*\n"
                    for idx, step in enumerate(result.get('next_steps', []), 1):
                        response += f"{idx}. {step}\n"
                    
                    response += "\nEnjoy your premium features!"
                else:
                    response = "❌ Upgrade failed. Please try again or contact support."
                
                await self._send_reply(from_number, response)
                return {"status": "upgraded" if result.get('success') else "upgrade_failed"}
                
            except Exception as e:
                logger.error(f"Error processing upgrade: {e}")
                response = "Unable to process upgrade. Please contact support."
                await self._send_reply(from_number, response)
                return {"status": "error"}
        
        elif cmd == "/whoami":
            # Show user's tenant, department, and role information
            user_info = self.tenancy_manager.get_user_info(from_number)
            
            if user_info.get('status') == 'guest':
                response = "👤 *User Information*\n\n"
                response += "Status: Guest User\n"
                response += "Access: Personal memories only\n\n"
                response += "Contact admin to be added to an organization."
            else:
                response = "👤 *User Information*\n\n"
                response += f"📢 Organization: {user_info['tenant']['name']}\n"
                response += f"🏢 Department: {user_info['department']['name'] if user_info['department'] else 'None'}\n"
                response += f"🎭 Role: {user_info['role'].title()}\n"
                response += f"📅 Member Since: {user_info['created_at'][:10]}\n\n"
                
                # Show permissions
                permissions = self.rbac_manager.get_role_permissions(user_info['role'])
                response += f"*Permissions ({len(permissions)}):*\n"
                key_perms = [
                    p for p in permissions 
                    if any(k in p for k in ['search', 'secret', 'audit', 'manage'])
                ][:5]
                for perm in key_perms:
                    response += f"• {perm.replace(':', ' ').title()}\n"
            
            await self._send_reply(from_number, response)
            return {"status": "whoami_shown"}
        
        elif cmd.startswith("/search dept:") or cmd.startswith("/search tenant:"):
            # Department or tenant-wide search
            scope = "department" if "dept:" in cmd else "tenant"
            query = cmd.split(":", 1)[1].strip() if ":" in cmd else ""
            
            if not query:
                await self._send_reply(
                    from_number,
                    f"Please provide a search query. Example: /search {scope}:meeting notes"
                )
                return {"status": "search_query_required"}
            
            # Check permissions
            user_role = self.tenancy_manager.get_user_role(from_number)
            if not self.rbac_manager.check_search_scope(user_role, scope):
                await self._send_reply(
                    from_number,
                    f"❌ Access denied. Your role ({user_role}) cannot perform {scope}-wide searches."
                )
                self.audit_logger.log(
                    AuditAction.ACCESS_DENIED,
                    from_number,
                    {"operation": f"search_{scope}", "query": query}
                )
                return {"status": "access_denied"}
            
            # Get user context
            user_tenant = self.tenancy_manager.get_user_tenant(from_number)
            user_dept = self.tenancy_manager.get_user_department(from_number)
            
            # Perform scoped search
            from memory.search import MemorySearch
            searcher = MemorySearch(self.memory_storage)
            
            if scope == "department" and user_dept:
                results = await searcher.search_department(
                    user_dept.id,
                    user_tenant.id if user_tenant else None,
                    query
                )
            elif scope == "tenant" and user_tenant:
                results = await searcher.search_tenant(
                    user_tenant.id,
                    query
                )
            else:
                results = []
            
            # Log the search
            audit_action = AuditAction.SEARCH_DEPARTMENT if scope == "department" else AuditAction.SEARCH_TENANT
            self.audit_logger.log(
                audit_action,
                from_number,
                {"query": query, "results_count": len(results)},
                tenant_id=user_tenant.id if user_tenant else None,
                department_id=user_dept.id if user_dept and scope == "department" else None
            )
            
            # Format results
            if results:
                response = f"🔍 *{scope.title()} Search Results*\n"
                response += f"Query: '{query}'\n"
                response += f"Found: {len(results)} memories\n\n"
                
                for idx, result in enumerate(results[:5], 1):
                    response += f"{idx}. [{result['category']}] "
                    response += f"{result['content_preview'][:50]}...\n"
                    response += f"   By: {result.get('user_phone', 'Unknown')[:8]}***\n"
                    response += f"   📅 {result['timestamp'][:10]}\n\n"
                
                if len(results) > 5:
                    response += f"... and {len(results) - 5} more results"
            else:
                response = f"No results found for '{query}' in {scope}."
            
            await self._send_reply(from_number, response)
            return {"status": f"{scope}_search_complete", "results": len(results)}
        
        elif cmd == "/audit":
            # Show recent audit entries (admin only)
            user_role = self.tenancy_manager.get_user_role(from_number)
            
            if not self.rbac_manager.check_permission(user_role, self.rbac_manager.Permission.AUDIT_VIEW):
                await self._send_reply(
                    from_number,
                    f"❌ Access denied. Only administrators can view audit logs."
                )
                self.audit_logger.log(
                    AuditAction.ACCESS_DENIED,
                    from_number,
                    {"operation": "view_audit"}
                )
                return {"status": "access_denied"}
            
            # Get recent audit entries
            user_tenant = self.tenancy_manager.get_user_tenant(from_number)
            recent_events = self.audit_logger.search_logs(
                filters={'tenant_id': user_tenant.id} if user_tenant else {},
                limit=10
            )
            
            response = "📋 *Recent Audit Events*\n\n"
            
            if recent_events:
                for event in recent_events[:5]:
                    action = event['action'].replace('.', ' ').title()
                    user = event['user'][:8] + "***" if len(event['user']) > 8 else event['user']
                    timestamp = event['timestamp'][:19]
                    
                    response += f"• {action}\n"
                    response += f"  User: {user}\n"
                    response += f"  Time: {timestamp}\n"
                    
                    if event.get('details', {}).get('query'):
                        response += f"  Query: {event['details']['query'][:30]}...\n"
                    
                    response += "\n"
            else:
                response += "No recent audit events found."
            
            # Log audit view
            self.audit_logger.log(
                AuditAction.AUDIT_VIEW,
                from_number,
                {"events_viewed": len(recent_events)},
                tenant_id=user_tenant.id if user_tenant else None
            )
            
            await self._send_reply(from_number, response)
            return {"status": "audit_shown"}
        
        else:
            await self._send_reply(
                from_number,
                branding.ERROR_MESSAGES["INVALID_COMMAND"]
            )
            return {"status": "unknown_command"}
    
    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for category"""
        emojis = {
            "CHRONOLOGICAL": "📅",
            "GENERAL": "📝",
            "CONFIDENTIAL": "🔒",
            "SECRET": "🔐",
            "ULTRA_SECRET": "🛡️"
        }
        return emojis.get(category, "📌")
    
    async def _send_reply(self, to_number: str, message: str) -> Dict:
        """Send WhatsApp reply message"""
        if not self.access_token or not self.phone_number_id:
            logger.warning("WhatsApp API not configured")
            return {"status": "not_configured"}
        
        url = f"{self.api_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return {"status": "sent", "message_id": response.json().get("messages", [{}])[0].get("id")}
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _mark_as_read(self, message_id: str) -> None:
        """Mark message as read"""
        if not self.access_token or not self.phone_number_id:
            return
        
        url = f"{self.api_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            requests.post(url, headers=headers, json=data)
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
    
    async def _download_media(self, media_id: str) -> bytes:
        """Download media from WhatsApp"""
        if not self.access_token:
            raise ValueError("WhatsApp API not configured")
        
        # Get media URL
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        media_url = response.json().get("url")
        
        # Download media
        response = requests.get(media_url, headers=headers)
        response.raise_for_status()
        
        return response.content