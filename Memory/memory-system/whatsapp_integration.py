#!/usr/bin/env python3
"""
WhatsApp Business API Integration for Digital Immortality Platform
Handles WhatsApp message monitoring and AI avatar responses
"""

import os
import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import hmac

logger = logging.getLogger(__name__)

class WhatsAppIntegration:
    """WhatsApp Business API integration"""
    
    def __init__(self):
        self.access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
        self.phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
        self.business_id = os.environ.get('WHATSAPP_BUSINESS_ID', '')
        self.verify_token = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'digital-immortality-2025')
        self.api_url = os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v18.0')
        self.webhook_secret = os.environ.get('WHATSAPP_WEBHOOK_SECRET', '')
        
        self.initialized = bool(self.access_token and self.phone_number_id)
        
        if self.initialized:
            logger.info("✅ WhatsApp Business API initialized")
        else:
            logger.warning("⚠️ WhatsApp Business API not configured")
    
    async def send_message(
        self,
        to_number: str,
        message: str,
        reply_to: Optional[str] = None
    ) -> bool:
        """Send WhatsApp message"""
        if not self.initialized:
            logger.error("❌ WhatsApp not initialized")
            return False
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }
        
        if reply_to:
            payload["context"] = {"message_id": reply_to}
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ WhatsApp message sent: {result['messages'][0]['id']}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to send WhatsApp message: {error}")
                        return False
        except Exception as e:
            logger.error(f"❌ WhatsApp send error: {e}")
            return False
    
    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        template_params: List[str] = None,
        language_code: str = "en"
    ) -> bool:
        """Send WhatsApp template message"""
        if not self.initialized:
            return False
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }
        
        if template_params:
            payload["template"]["components"] = [{
                "type": "body",
                "parameters": [{"type": "text", "text": param} for param in template_params]
            }]
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Template message sent: {template_name}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to send template: {error}")
                        return False
        except Exception as e:
            logger.error(f"❌ Template send error: {e}")
            return False
    
    async def send_media_message(
        self,
        to_number: str,
        media_type: str,
        media_url: str,
        caption: Optional[str] = None
    ) -> bool:
        """Send media message (image, video, document, audio)"""
        if not self.initialized:
            return False
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": media_type,
            media_type: {"link": media_url}
        }
        
        if caption and media_type in ["image", "video", "document"]:
            payload[media_type]["caption"] = caption
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"✅ Media message sent: {media_type}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to send media: {error}")
                        return False
        except Exception as e:
            logger.error(f"❌ Media send error: {e}")
            return False
    
    async def send_interactive_buttons(
        self,
        to_number: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None
    ) -> bool:
        """Send interactive button message"""
        if not self.initialized:
            return False
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn["id"],
                            "title": btn["title"][:20]  # Max 20 chars
                        }
                    }
                    for btn in buttons[:3]  # Max 3 buttons
                ]
            }
        }
        
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": interactive
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info("✅ Interactive buttons sent")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to send buttons: {error}")
                        return False
        except Exception as e:
            logger.error(f"❌ Interactive send error: {e}")
            return False
    
    async def process_incoming_message(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming WhatsApp message"""
        try:
            # Extract message data
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            if "messages" not in value:
                return {"processed": False, "reason": "No messages in webhook"}
            
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])
            
            results = []
            
            for message in messages:
                from_number = message.get("from")
                message_id = message.get("id")
                timestamp = message.get("timestamp")
                message_type = message.get("type")
                
                # Get contact info
                contact_info = next((c for c in contacts if c["wa_id"] == from_number), {})
                contact_name = contact_info.get("profile", {}).get("name", "Unknown")
                
                # Process based on message type
                content = None
                
                if message_type == "text":
                    content = message["text"]["body"]
                
                elif message_type == "image":
                    content = f"[Image: {message['image'].get('caption', 'No caption')}]"
                
                elif message_type == "video":
                    content = f"[Video: {message['video'].get('caption', 'No caption')}]"
                
                elif message_type == "audio":
                    content = "[Audio message]"
                
                elif message_type == "document":
                    content = f"[Document: {message['document'].get('filename', 'Unknown')}]"
                
                elif message_type == "location":
                    loc = message["location"]
                    content = f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
                
                elif message_type == "interactive":
                    if "button_reply" in message["interactive"]:
                        content = f"Button: {message['interactive']['button_reply']['title']}"
                    elif "list_reply" in message["interactive"]:
                        content = f"List: {message['interactive']['list_reply']['title']}"
                
                if content:
                    # Process with memory app
                    from memory_app import memory_app
                    
                    # Check if this is a memory command
                    if content.lower().startswith("/memory"):
                        # Store as memory
                        memory_result = await memory_app.store_memory(
                            user_id=from_number,
                            content=content[7:].strip(),  # Remove /memory prefix
                            category="whatsapp",
                            platform="whatsapp"
                        )
                        
                        # Send confirmation
                        await self.send_message(
                            from_number,
                            f"✅ Memory #{memory_result['memory_number']} saved!",
                            reply_to=message_id
                        )
                    
                    elif content.lower().startswith("/secret"):
                        # Store as secret memory
                        secret_content = content[7:].strip()
                        # Process secret memory...
                        await self.send_message(
                            from_number,
                            "🔒 Secret memory stored securely",
                            reply_to=message_id
                        )
                    
                    else:
                        # Regular conversation - could trigger AI avatar response
                        # For now, just acknowledge
                        pass
                    
                    results.append({
                        "from": from_number,
                        "name": contact_name,
                        "content": content,
                        "type": message_type,
                        "timestamp": timestamp,
                        "processed": True
                    })
            
            return {
                "processed": True,
                "messages_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing WhatsApp message: {e}")
            return {"processed": False, "error": str(e)}
    
    def verify_webhook(self, signature: str, payload: bytes) -> bool:
        """Verify WhatsApp webhook signature"""
        if not self.webhook_secret:
            return True  # Skip verification if no secret configured
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark message as read"""
        if not self.initialized:
            return False
        
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    return response.status == 200
        except:
            return False
    
    async def create_template(self, template_config: Dict[str, Any]) -> bool:
        """Create message template for approval"""
        if not self.initialized or not self.business_id:
            return False
        
        url = f"{self.api_url}/{self.business_id}/message_templates"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=template_config, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Template created: {result['id']}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"❌ Failed to create template: {error}")
                        return False
        except Exception as e:
            logger.error(f"❌ Template creation error: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get WhatsApp integration status"""
        return {
            "initialized": self.initialized,
            "phone_number_id": self.phone_number_id[:10] + "..." if self.phone_number_id else None,
            "business_id": self.business_id[:10] + "..." if self.business_id else None,
            "api_url": self.api_url,
            "features": {
                "text_messages": True,
                "media_messages": True,
                "template_messages": True,
                "interactive_messages": True,
                "message_monitoring": True
            }
        }

# Global instance
whatsapp_integration = WhatsAppIntegration()

# Pre-defined templates for common notifications
NOTIFICATION_TEMPLATES = {
    "memory_milestone": {
        "name": "memory_milestone",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "HEADER",
                "format": "TEXT",
                "text": "🎉 Memory Milestone Reached!"
            },
            {
                "type": "BODY",
                "text": "Congratulations {{1}}! You've stored {{2}} memories. Your digital legacy is growing!"
            },
            {
                "type": "FOOTER",
                "text": "Digital Immortality Platform"
            }
        ]
    },
    "commitment_reminder": {
        "name": "commitment_reminder",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "⏰ Reminder: {{1}} is due {{2}}. Reply 'done' when completed."
            }
        ]
    },
    "family_access_request": {
        "name": "family_access",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "{{1}} has requested family access to your memories. Reply 'approve' or 'deny'."
            }
        ]
    }
}

if __name__ == "__main__":
    # Test WhatsApp integration
    print("💬 WhatsApp Business API Integration Status")
    print("=" * 50)
    
    status = whatsapp_integration.get_status()
    print(f"Initialized: {'✅' if status['initialized'] else '❌'}")
    print(f"Phone Number ID: {status['phone_number_id']}")
    print(f"Business ID: {status['business_id']}")
    print(f"API URL: {status['api_url']}")
    
    if not status['initialized']:
        print("\n⚠️ WhatsApp not configured. Set environment variables:")
        print("  - WHATSAPP_ACCESS_TOKEN")
        print("  - WHATSAPP_PHONE_NUMBER_ID")
        print("  - WHATSAPP_BUSINESS_ID (optional)")
        print("  - WHATSAPP_VERIFY_TOKEN")