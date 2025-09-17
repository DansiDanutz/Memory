"""
WebSocket Routes for Real-time Updates
Based on MEMORY_APP_COMPLETE_PACKAGE implementation
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import logging
import asyncio
from datetime import datetime
from app.security.hmac_auth import HMACVerifier
from app.sync.whatsapp_sync import whatsapp_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.user_connections[user_id] = websocket
        
        # Register with WhatsApp sync service
        await whatsapp_sync.register_ws_connection(websocket)
        
        logger.info(f"WebSocket connected for user: {user_id}")
        
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        if user_id in self.user_connections and self.user_connections[user_id] == websocket:
            del self.user_connections[user_id]
        
        # Unregister from WhatsApp sync service
        asyncio.create_task(whatsapp_sync.unregister_ws_connection(websocket))
        
        logger.info(f"WebSocket disconnected for user: {user_id}")
        
    async def send_personal_message(self, message: str, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Connection might be closed
                    pass
                    
    async def broadcast(self, message: str):
        """Broadcast message to all connected users"""
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_text(message)
                except:
                    # Connection might be closed
                    pass

# Global connection manager
manager = ConnectionManager()

@router.websocket("/connect")
async def websocket_connect(websocket: WebSocket):
    """
    WebSocket endpoint for frontend connections (no auth required)
    """
    # Get user_id from query params
    user_id = websocket.query_params.get("user_id", "anonymous")
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial connection success message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send sync status
        sync_status = whatsapp_sync.get_sync_status()
        await websocket.send_json({
            "type": "sync_status",
            "data": sync_status
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "memory_create":
                    # Handle memory creation
                    await handle_memory_create(message, user_id, websocket)
                    
                elif message.get("type") == "memory_search":
                    # Handle memory search
                    await handle_memory_search(message, user_id, websocket)
                    
                elif message.get("type") == "sync_request":
                    # Handle sync request
                    await handle_sync_request(message, user_id, websocket)
                    
                elif message.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                else:
                    # Echo unknown messages
                    await websocket.send_json({
                        "type": "echo",
                        "data": message
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

@router.websocket("/memory/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time memory updates (legacy)
    """
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial connection success message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send sync status
        sync_status = whatsapp_sync.get_sync_status()
        await websocket.send_json({
            "type": "sync_status",
            "data": sync_status
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "memory_create":
                    # Handle memory creation
                    await handle_memory_create(message, user_id, websocket)
                    
                elif message.get("type") == "memory_search":
                    # Handle memory search
                    await handle_memory_search(message, user_id, websocket)
                    
                elif message.get("type") == "sync_request":
                    # Handle sync request
                    await handle_sync_request(message, user_id, websocket)
                    
                elif message.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                else:
                    # Echo unknown messages
                    await websocket.send_json({
                        "type": "echo",
                        "data": message
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

async def handle_memory_create(message: Dict, user_id: str, websocket: WebSocket):
    """Handle memory creation via WebSocket"""
    try:
        from app.memory.storage import MemoryStorage
        from app.memory.classifier import MessageClassifier
        
        storage = MemoryStorage()
        classifier = MessageClassifier()
        
        content = message.get("content", "")
        category = classifier.classify(content)
        
        # Store memory using the correct method
        import asyncio
        memory_id = await storage.store(
            phone=user_id,
            category=category,
            content=content,
            ts=None,
            tenant_id=message.get("metadata", {}).get("tenant_id"),
            department_id=message.get("metadata", {}).get("department_id")
        )
        
        # Send success response
        await websocket.send_json({
            "type": "memory_created",
            "memory_id": memory_id,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })
        
        # Broadcast to other connections of the same user
        await manager.send_personal_message(
            json.dumps({
                "type": "new_memory",
                "memory_id": memory_id,
                "category": category,
                "content": content[:100] + "..." if len(content) > 100 else content
            }),
            user_id
        )
        
        # Sync to WhatsApp if enabled
        if message.get("sync_to_whatsapp", False):
            await whatsapp_sync.sync_message_to_whatsapp(
                user_id,
                f"Memory saved: {content[:100]}",
                {"memory_id": memory_id}
            )
            
    except Exception as e:
        logger.error(f"Error handling memory create: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to create memory: {str(e)}"
        })

async def handle_memory_search(message: Dict, user_id: str, websocket: WebSocket):
    """Handle memory search via WebSocket"""
    try:
        from app.memory.search import MemorySearch
        from app.memory.storage import MemoryStorage
        
        storage = MemoryStorage()
        searcher = MemorySearch(storage)
        query = message.get("query", "")
        
        results = await searcher.search(
            user_phone=user_id,
            query=query,
            category=None,
            start_date=None,
            end_date=None,
            limit=message.get("limit", 10)
        )
        
        # Send search results
        await websocket.send_json({
            "type": "search_results",
            "query": query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling memory search: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Search failed: {str(e)}"
        })

async def handle_sync_request(message: Dict, user_id: str, websocket: WebSocket):
    """Handle sync request via WebSocket"""
    try:
        sync_type = message.get("sync_type", "status")
        
        if sync_type == "status":
            # Send current sync status
            status = whatsapp_sync.get_sync_status()
            await websocket.send_json({
                "type": "sync_status",
                "data": status,
                "timestamp": datetime.now().isoformat()
            })
            
        elif sync_type == "force":
            # Force sync with WhatsApp
            # This would trigger a full sync process
            await websocket.send_json({
                "type": "sync_started",
                "timestamp": datetime.now().isoformat()
            })
            
            # Start sync in background
            asyncio.create_task(perform_full_sync(user_id, websocket))
            
    except Exception as e:
        logger.error(f"Error handling sync request: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Sync request failed: {str(e)}"
        })

async def perform_full_sync(user_id: str, websocket: WebSocket):
    """Perform full synchronization"""
    try:
        # This would implement full sync logic
        # For now, send a completion message
        await asyncio.sleep(2)  # Simulate sync process
        
        await websocket.send_json({
            "type": "sync_completed",
            "timestamp": datetime.now().isoformat(),
            "synced_items": 0
        })
        
    except Exception as e:
        logger.error(f"Error performing full sync: {e}")

@router.websocket("/notifications")
async def notification_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for system notifications
    """
    await websocket.accept()
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "notification",
            "message": "Connected to notification service",
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # Keep connection alive and send periodic updates
            await asyncio.sleep(30)
            
            # Send heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info("Notification WebSocket disconnected")
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")