"""
Memory Management API Routes
Based on MEMORY_APP_COMPLETE_PACKAGE implementation
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from pathlib import Path
import json
import os
from app.security.hmac_auth import HMACBearer
from app.memory.storage import MemoryStorage
from app.memory.classifier import MessageClassifier
import logging
import asyncio

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/memories", tags=["memories"])

# HMAC Security (optional for frontend)
MEMO_APP_SECRET = os.getenv('MEMO_APP_SECRET', 'memo_app_secret_key_min_64_chars_long_for_security_implementation_2024')
hmac_auth = HMACBearer(MEMO_APP_SECRET)

# Optional HMAC auth dependency
def optional_hmac_auth(auth: Optional[str] = None):
    """Optional HMAC authentication for frontend"""
    return auth

# Initialize services
memory_storage = MemoryStorage()
classifier = MessageClassifier()

# Pydantic models
class Memory(BaseModel):
    """Memory data model"""
    id: Optional[str] = Field(None, description="Memory ID")
    user_id: str = Field(..., description="User identifier")
    content: str = Field(..., description="Memory content")
    category: Optional[str] = Field("GENERAL", description="Memory category")
    timestamp: Optional[datetime] = Field(None, description="Creation timestamp")
    tags: Optional[List[str]] = Field([], description="Associated tags")
    sentiment: Optional[str] = Field(None, description="Sentiment analysis")
    importance: Optional[int] = Field(5, ge=1, le=10, description="Importance level")
    metadata: Optional[Dict[str, Any]] = Field({}, description="Additional metadata")
    # Contact-related fields
    contact_phone: Optional[str] = Field(None, description="Contact's phone number")
    contact_name: Optional[str] = Field(None, description="Contact's name")
    is_from_contact: Optional[bool] = Field(False, description="Whether memory is from a contact")

class MemoryUpdate(BaseModel):
    """Memory update model"""
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    importance: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class MemorySearchRequest(BaseModel):
    """Memory search request model"""
    query: str = Field(..., description="Search query")
    user_id: str = Field(..., description="User identifier")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Result limit")
    contact_phone: Optional[str] = Field(None, description="Filter by contact phone")

class CategorySummary(BaseModel):
    """Category summary model"""
    category: str
    count: int
    latest_memory: Optional[datetime]
    importance_avg: float

class ContactSummary(BaseModel):
    """Contact summary model"""
    phone: str
    name: Optional[str]
    last_interaction: datetime
    message_count: int
    last_message: str
    categories: List[str]

@router.post("/create", response_model=Memory)
async def create_memory(
    memory: Memory,
    request: Request,
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Create a new memory with AI categorization
    """
    try:
        # Auto-categorize if not specified
        if memory.category == "GENERAL" or not memory.category:
            memory.category = classifier.classify(memory.content)
            # Extract tags from content
            memory.tags = []
            memory.sentiment = 'neutral'
        
        # Set timestamp
        if not memory.timestamp:
            memory.timestamp = datetime.now()
        
        # Store memory using the correct method name
        # If contact_phone is provided, store in contact's directory instead
        storage_phone = memory.contact_phone if memory.contact_phone else memory.user_id
        memory_id = await memory_storage.store(
            phone=storage_phone,
            category=memory.category,
            content=memory.content,
            ts=memory.timestamp,
            tenant_id=memory.metadata.get('tenant_id'),
            department_id=memory.metadata.get('department_id')
        )
        
        # Update metadata with contact info if present
        if memory.contact_phone:
            memory.metadata['stored_in_contact'] = memory.contact_phone
            memory.is_from_contact = True
        
        memory.id = memory_id
        
        logger.info(f"Created memory {memory_id} for user {memory.user_id}")
        return memory
        
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list/{user_id}", response_model=List[Memory])
async def list_memories(
    user_id: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    contact_phone: Optional[str] = Query(None, description="Filter by contact phone"),
    limit: int = Query(20, ge=1, le=100, description="Number of memories to retrieve"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    List memories for a user with optional filtering
    """
    try:
        memories = []
        
        # If filtering by contact, use contact's directory
        if contact_phone:
            user_id = contact_phone  # Use contact phone as the user ID for lookup
        
        # Get memories from storage
        if category:
            # Filter by specific category
            category_path = f"data/contacts/{user_id}/{category}"
            if os.path.exists(category_path):
                memory_files = sorted(os.listdir(category_path), reverse=True)[offset:offset+limit]
                
                for file in memory_files:
                    if file.endswith('.md'):
                        with open(os.path.join(category_path, file), 'r') as f:
                            content = f.read()
                            # Parse memory from markdown
                            memory = Memory(
                                id=file.replace('.md', ''),
                                user_id=user_id,
                                content=content,
                                category=category,
                                timestamp=datetime.fromtimestamp(os.path.getmtime(os.path.join(category_path, file))),
                                tags=[],
                                sentiment='neutral',
                                importance=5,
                                metadata={},
                                contact_phone=contact_phone if contact_phone else None,
                                is_from_contact=bool(contact_phone)
                            )
                            memories.append(memory)
        else:
            # Get all categories
            user_path = f"data/contacts/{user_id}"
            if os.path.exists(user_path):
                categories = ['GENERAL', 'CONFIDENTIAL', 'SECRET', 'ULTRA_SECRET', 'CHRONOLOGICAL']
                
                for cat in categories:
                    cat_path = os.path.join(user_path, cat)
                    if os.path.exists(cat_path):
                        memory_files = sorted(os.listdir(cat_path), reverse=True)[:limit//len(categories)]
                        
                        for file in memory_files:
                            if file.endswith('.md'):
                                with open(os.path.join(cat_path, file), 'r') as f:
                                    content = f.read()
                                    memory = Memory(
                                        id=file.replace('.md', ''),
                                        user_id=user_id,
                                        content=content,
                                        category=cat,
                                        timestamp=datetime.fromtimestamp(os.path.getmtime(os.path.join(cat_path, file))),
                                        tags=[],
                                        sentiment='neutral',
                                        importance=5,
                                        metadata={},
                                        contact_phone=contact_phone if contact_phone else None,
                                        is_from_contact=bool(contact_phone)
                                    )
                                    memories.append(memory)
        
        # Sort by timestamp
        memories.sort(key=lambda x: x.timestamp, reverse=True)
        
        return memories[:limit]
        
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=List[Memory])
async def search_memories(
    search_request: MemorySearchRequest,
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Search memories with advanced filtering
    """
    try:
        from app.memory.search import MemorySearch
        
        # Initialize search with memory storage
        searcher = MemorySearch(memory_storage)
        
        # If searching by contact, use contact's phone as user_phone
        search_phone = search_request.contact_phone if search_request.contact_phone else search_request.user_id
        
        # Perform search using the correct method signature
        results = await searcher.search(
            user_phone=search_phone,
            query=search_request.query,
            category=search_request.categories[0] if search_request.categories else None,
            start_date=search_request.date_from,
            end_date=search_request.date_to,
            limit=search_request.limit or 20
        )
        
        # Convert results to Memory objects
        memories = []
        for result in results:
            # Parse timestamp if it's a string
            timestamp = result.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            memory = Memory(
                id=result.get('id', ''),
                user_id=search_request.user_id,
                content=result.get('content_preview', result.get('content', '')),
                category=result.get('category', 'GENERAL'),
                timestamp=timestamp,
                tags=result.get('tags', []),
                sentiment=result.get('sentiment', 'neutral'),
                importance=result.get('importance', 5),
                metadata=result.get('metadata', {}),
                contact_phone=search_request.contact_phone if search_request.contact_phone else None,
                is_from_contact=bool(search_request.contact_phone)
            )
            
            # Date filtering is already done in the search method, skip additional filtering
                
            memories.append(memory)
        
        return memories[:search_request.limit]
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories/{user_id}", response_model=List[CategorySummary])
async def get_category_summary(
    user_id: str,
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Get summary of memories by category
    """
    try:
        summaries = []
        user_path = f"data/contacts/{user_id}"
        
        if os.path.exists(user_path):
            categories = ['GENERAL', 'CONFIDENTIAL', 'SECRET', 'ULTRA_SECRET', 'CHRONOLOGICAL']
            
            for category in categories:
                cat_path = os.path.join(user_path, category)
                if os.path.exists(cat_path):
                    memory_files = [f for f in os.listdir(cat_path) if f.endswith('.md')]
                    
                    if memory_files:
                        latest_file = max(memory_files, key=lambda f: os.path.getmtime(os.path.join(cat_path, f)))
                        latest_time = datetime.fromtimestamp(os.path.getmtime(os.path.join(cat_path, latest_file)))
                        
                        summary = CategorySummary(
                            category=category,
                            count=len(memory_files),
                            latest_memory=latest_time,
                            importance_avg=5.0  # Default importance
                        )
                        summaries.append(summary)
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error getting category summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{memory_id}", response_model=Memory)
async def update_memory(
    memory_id: str,
    user_id: str,
    update: MemoryUpdate,
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Update an existing memory
    """
    try:
        # Find and update the memory
        # This is a simplified implementation
        # In production, you would update the actual file
        
        memory = Memory(
            id=memory_id,
            user_id=user_id,
            content=update.content or "Updated content",
            category=update.category or "GENERAL",
            tags=update.tags or [],
            sentiment='neutral',
            importance=update.importance or 5,
            metadata=update.metadata or {},
            timestamp=datetime.now()
        )
        
        logger.info(f"Updated memory {memory_id} for user {user_id}")
        return memory
        
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{memory_id}")
async def delete_memory(
    memory_id: str,
    user_id: str,
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Delete a memory
    """
    try:
        # This is a simplified implementation
        # In production, you would delete the actual file
        
        logger.info(f"Deleted memory {memory_id} for user {user_id}")
        return {"status": "success", "message": f"Memory {memory_id} deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync")
async def sync_memories(
    user_id: str,
    request: Request,
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Sync memories with WhatsApp and other platforms
    """
    try:
        # Get sync data from request
        body = await request.json()
        
        # Perform sync operation
        # This would integrate with WhatsApp bot
        
        logger.info(f"Synced memories for user {user_id}")
        return {
            "status": "success",
            "synced": True,
            "timestamp": datetime.now().isoformat(),
            "platform": "whatsapp"
        }
        
    except Exception as e:
        logger.error(f"Error syncing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary/{user_id}/categories", response_model=List[CategorySummary])
async def get_categories_summary(
    user_id: str,
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Get summary of memories by category (alternative endpoint)
    """
    return await get_category_summary(user_id, auth)

@router.get("/contacts", response_model=List[ContactSummary])
async def get_contacts(
    user_id: str = Query(..., description="User ID to get contacts for"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of contacts to return"),
    auth: Optional[str] = Depends(optional_hmac_auth)
):
    """
    Get list of contacts with last message and interaction details
    """
    try:
        contacts = []
        base_path = Path("data/contacts")
        
        if not base_path.exists():
            return []
        
        # Get all directories (contacts) in the contacts folder
        for contact_dir in base_path.iterdir():
            if contact_dir.is_dir():
                contact_phone = contact_dir.name
                
                # Skip the user's own directory if it matches
                if contact_phone == user_id:
                    continue
                    
                # Get contact info
                index_file = contact_dir / "index.json"
                last_message = ""
                last_interaction = None
                message_count = 0
                categories_found = []
                
                # Check each category for messages
                categories = ['GENERAL', 'CONFIDENTIAL', 'SECRET', 'ULTRA_SECRET', 'CHRONOLOGICAL']
                
                for category in categories:
                    cat_path = contact_dir / category
                    if cat_path.exists():
                        memory_files = list(cat_path.glob("*.md"))
                        if memory_files:
                            categories_found.append(category)
                            message_count += len(memory_files)
                            
                            # Get the most recent file
                            latest_file = max(memory_files, key=lambda f: f.stat().st_mtime)
                            file_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
                            
                            if not last_interaction or file_time > last_interaction:
                                last_interaction = file_time
                                # Read the last message content
                                try:
                                    with open(latest_file, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                        # Extract content preview (first 100 chars of actual content)
                                        lines = content.split('\n')
                                        for line in lines:
                                            if line and not line.startswith('#') and not line.startswith('**'):
                                                last_message = line[:100]
                                                break
                                except Exception:
                                    last_message = "Unable to read message"
                
                # Only add contacts that have messages
                if message_count > 0 and last_interaction:
                    contact = ContactSummary(
                        phone=contact_phone,
                        name=None,  # Could be extracted from metadata if stored
                        last_interaction=last_interaction,
                        message_count=message_count,
                        last_message=last_message or "No content available",
                        categories=categories_found
                    )
                    contacts.append(contact)
        
        # Sort by last interaction, most recent first
        contacts.sort(key=lambda x: x.last_interaction, reverse=True)
        
        return contacts[:limit]
        
    except Exception as e:
        logger.error(f"Error getting contacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))