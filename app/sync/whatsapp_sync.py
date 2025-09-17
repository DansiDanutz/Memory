"""
WhatsApp Bidirectional Sync Module
Based on MEMORY_APP_COMPLETE_PACKAGE implementation
Enables real-time synchronization between WhatsApp and Web Interface
"""
import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac

logger = logging.getLogger(__name__)

class SyncDirection(Enum):
    """Sync direction enumeration"""
    WHATSAPP_TO_WEB = "whatsapp_to_web"
    WEB_TO_WHATSAPP = "web_to_whatsapp"
    BIDIRECTIONAL = "bidirectional"

class SyncStatus(Enum):
    """Sync status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

@dataclass
class SyncMessage:
    """Message structure for synchronization"""
    id: str
    user_id: str
    content: str
    timestamp: datetime
    direction: SyncDirection
    status: SyncStatus
    metadata: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    error_message: Optional[str] = None

class WhatsAppBidirectionalSync:
    """
    WhatsApp Bidirectional Synchronization Service
    Handles real-time sync between WhatsApp and Web Interface
    """
    
    def __init__(self):
        """Initialize WhatsApp sync service"""
        self.api_key = os.getenv('WHATSAPP_API_KEY', '')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
        self.business_account_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID', '')
        self.webhook_url = os.getenv('WHATSAPP_WEBHOOK_URL', '')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', '')
        
        # Sync configuration
        self.sync_interval = 30  # seconds
        self.max_retry_attempts = 3
        self.batch_size = 50
        
        # Sync queues
        self.outbound_queue: List[SyncMessage] = []
        self.inbound_queue: List[SyncMessage] = []
        self.sync_history: List[SyncMessage] = []
        
        # WebSocket connections for real-time updates
        self.ws_connections = set()
        
        logger.info("WhatsApp Bidirectional Sync initialized")
    
    async def sync_message_to_whatsapp(
        self,
        user_phone: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Sync a message from web interface to WhatsApp
        
        Args:
            user_phone: User's WhatsApp phone number
            message: Message content
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            # Create sync message
            sync_msg = SyncMessage(
                id=self._generate_message_id(),
                user_id=user_phone,
                content=message,
                timestamp=datetime.now(),
                direction=SyncDirection.WEB_TO_WHATSAPP,
                status=SyncStatus.PENDING,
                metadata=metadata
            )
            
            # Add to outbound queue
            self.outbound_queue.append(sync_msg)
            
            # Send to WhatsApp
            success = await self._send_whatsapp_message(user_phone, message)
            
            if success:
                sync_msg.status = SyncStatus.COMPLETED
                logger.info(f"Message synced to WhatsApp: {sync_msg.id}")
            else:
                sync_msg.status = SyncStatus.FAILED
                logger.error(f"Failed to sync message to WhatsApp: {sync_msg.id}")
            
            # Update sync history
            self.sync_history.append(sync_msg)
            
            # Notify WebSocket clients
            await self._notify_ws_clients({
                'type': 'sync_update',
                'direction': 'web_to_whatsapp',
                'status': sync_msg.status.value,
                'message_id': sync_msg.id
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error syncing to WhatsApp: {e}")
            return False
    
    async def sync_message_from_whatsapp(
        self,
        webhook_data: Dict[str, Any]
    ) -> bool:
        """
        Sync a message from WhatsApp to web interface
        
        Args:
            webhook_data: WhatsApp webhook payload
            
        Returns:
            Success status
        """
        try:
            # Parse WhatsApp message
            message_data = self._parse_whatsapp_message(webhook_data)
            
            if not message_data:
                return False
            
            # Create sync message
            sync_msg = SyncMessage(
                id=message_data.get('id', self._generate_message_id()),
                user_id=message_data.get('from', ''),
                content=message_data.get('text', ''),
                timestamp=datetime.now(),
                direction=SyncDirection.WHATSAPP_TO_WEB,
                status=SyncStatus.PENDING,
                metadata=message_data
            )
            
            # Add to inbound queue
            self.inbound_queue.append(sync_msg)
            
            # Store in memory system
            from app.memory.storage import MemoryStorage
            storage = MemoryStorage()
            
            success = storage.store_memory(
                user_id=sync_msg.user_id,
                category='GENERAL',
                content=sync_msg.content,
                metadata={
                    'source': 'whatsapp',
                    'message_id': sync_msg.id,
                    'timestamp': sync_msg.timestamp.isoformat()
                }
            )
            
            if success:
                sync_msg.status = SyncStatus.COMPLETED
                logger.info(f"Message synced from WhatsApp: {sync_msg.id}")
            else:
                sync_msg.status = SyncStatus.FAILED
                logger.error(f"Failed to sync message from WhatsApp: {sync_msg.id}")
            
            # Update sync history
            self.sync_history.append(sync_msg)
            
            # Notify WebSocket clients
            await self._notify_ws_clients({
                'type': 'new_message',
                'direction': 'whatsapp_to_web',
                'user_id': sync_msg.user_id,
                'content': sync_msg.content,
                'timestamp': sync_msg.timestamp.isoformat()
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error syncing from WhatsApp: {e}")
            return False
    
    async def start_sync_worker(self):
        """
        Start the background sync worker for batch processing
        """
        logger.info("Starting WhatsApp sync worker")
        
        while True:
            try:
                # Process outbound queue
                await self._process_outbound_queue()
                
                # Process inbound queue
                await self._process_inbound_queue()
                
                # Clean up old sync history
                self._cleanup_sync_history()
                
                # Wait for next sync cycle
                await asyncio.sleep(self.sync_interval)
                
            except Exception as e:
                logger.error(f"Sync worker error: {e}")
                await asyncio.sleep(5)  # Short delay on error
    
    async def _process_outbound_queue(self):
        """Process messages in outbound queue"""
        if not self.outbound_queue:
            return
        
        # Process in batches
        batch = self.outbound_queue[:self.batch_size]
        
        for msg in batch:
            if msg.status == SyncStatus.PENDING:
                success = await self._send_whatsapp_message(
                    msg.user_id,
                    msg.content
                )
                
                if success:
                    msg.status = SyncStatus.COMPLETED
                    self.outbound_queue.remove(msg)
                else:
                    msg.retry_count += 1
                    if msg.retry_count >= self.max_retry_attempts:
                        msg.status = SyncStatus.FAILED
                        self.outbound_queue.remove(msg)
                    else:
                        msg.status = SyncStatus.RETRY
    
    async def _process_inbound_queue(self):
        """Process messages in inbound queue"""
        if not self.inbound_queue:
            return
        
        # Process in batches
        batch = self.inbound_queue[:self.batch_size]
        
        for msg in batch:
            if msg.status == SyncStatus.COMPLETED:
                self.inbound_queue.remove(msg)
    
    async def _send_whatsapp_message(
        self,
        phone_number: str,
        message: str
    ) -> bool:
        """
        Send message via WhatsApp API
        
        Args:
            phone_number: Recipient phone number
            message: Message content
            
        Returns:
            Success status
        """
        try:
            if not self.api_key or not self.phone_number_id:
                logger.warning("WhatsApp API not configured")
                return False
            
            url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': phone_number,
                'type': 'text',
                'text': {
                    'body': message
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"WhatsApp message sent: {result.get('messages', [{}])[0].get('id')}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"WhatsApp API error: {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def _parse_whatsapp_message(
        self,
        webhook_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse WhatsApp webhook message
        
        Args:
            webhook_data: Webhook payload
            
        Returns:
            Parsed message data
        """
        try:
            # Extract message from webhook structure
            entry = webhook_data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages:
                return None
            
            message = messages[0]
            
            return {
                'id': message.get('id'),
                'from': message.get('from'),
                'timestamp': message.get('timestamp'),
                'text': message.get('text', {}).get('body', ''),
                'type': message.get('type'),
                'context': message.get('context'),
                'metadata': value.get('metadata')
            }
            
        except Exception as e:
            logger.error(f"Error parsing WhatsApp message: {e}")
            return None
    
    async def _notify_ws_clients(self, data: Dict[str, Any]):
        """
        Notify WebSocket clients of sync updates
        
        Args:
            data: Update data to broadcast
        """
        if not self.ws_connections:
            return
        
        message = json.dumps(data)
        
        # Send to all connected clients
        disconnected = set()
        for ws in self.ws_connections:
            try:
                await ws.send(message)
            except:
                disconnected.add(ws)
        
        # Remove disconnected clients
        self.ws_connections -= disconnected
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID"""
        return hashlib.sha256(
            f"{datetime.now().isoformat()}{os.urandom(16).hex()}".encode()
        ).hexdigest()[:16]
    
    def _cleanup_sync_history(self):
        """Clean up old sync history entries"""
        cutoff_time = datetime.now() - timedelta(days=7)
        self.sync_history = [
            msg for msg in self.sync_history
            if msg.timestamp > cutoff_time
        ]
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current sync status
        
        Returns:
            Sync status information
        """
        return {
            'outbound_queue_size': len(self.outbound_queue),
            'inbound_queue_size': len(self.inbound_queue),
            'sync_history_size': len(self.sync_history),
            'ws_connections': len(self.ws_connections),
            'last_sync': max(
                (msg.timestamp for msg in self.sync_history),
                default=datetime.min
            ).isoformat() if self.sync_history else None,
            'status': 'active' if self.ws_connections else 'idle'
        }
    
    async def register_ws_connection(self, websocket):
        """Register a WebSocket connection for real-time updates"""
        self.ws_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.ws_connections)}")
    
    async def unregister_ws_connection(self, websocket):
        """Unregister a WebSocket connection"""
        self.ws_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.ws_connections)}")


# Global sync service instance
whatsapp_sync = WhatsAppBidirectionalSync()