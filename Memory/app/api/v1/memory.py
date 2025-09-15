"""
Memory API endpoints v1
Handles memory CRUD operations with validation and caching
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query, Depends, Request
from app.schemas.validation import (
    MemoryCreateRequest,
    MemorySearchRequest,
    ErrorResponse
)
from app.memory.search_optimized import get_search_service, OptimizedMemorySearch
from app.middleware.rate_limiter import rate_limit
from app.security.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create", response_model=Dict[str, str])
@rate_limit(requests=50, window=60)
async def create_memory(
    request: MemoryCreateRequest,
    search_service: OptimizedMemorySearch = Depends(get_search_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new memory entry

    - **user_id**: User identifier
    - **content**: Memory content (max 10000 chars)
    - **category**: Optional category
    - **tags**: Optional list of tags
    """
    try:
        memory_id = await search_service.add_memory(
            user_id=request.user_id,
            content=request.content,
            category=request.category or "GENERAL",
            tags=request.tags or []
        )

        logger.info(f"Created memory {memory_id} for user {request.user_id}")

        return {
            "memory_id": memory_id,
            "status": "created",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create memory: {str(e)}"
        )


@router.get("/search", response_model=List[Dict[str, Any]])
@rate_limit(requests=50, window=60)
async def search_memories(
    query: str = Query(..., min_length=1, max_length=500),
    user_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search_service: OptimizedMemorySearch = Depends(get_search_service),
    current_user: Dict = Depends(get_current_user)
):
    """
    Search memories with advanced filtering

    - **query**: Search query text
    - **user_id**: Filter by user
    - **category**: Filter by category
    - **tags**: Filter by tags
    - **limit**: Max results (1-100)
    - **offset**: Pagination offset
    """
    try:
        # Validate user access
        if user_id and user_id != current_user.get("user_id"):
            if not current_user.get("is_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access other user's memories"
                )

        results = await search_service.search(
            query=query,
            user_id=user_id or current_user.get("user_id"),
            category=category,
            tags=tags,
            limit=limit,
            use_cache=True
        )

        logger.info(f"Search returned {len(results)} results for query: {query}")

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/{memory_id}", response_model=Dict[str, Any])
async def get_memory(
    memory_id: str,
    search_service: OptimizedMemorySearch = Depends(get_search_service),
    current_user: Dict = Depends(get_current_user)
):
    """Get specific memory by ID"""
    try:
        # This would need to be implemented in search_optimized.py
        memory = search_service.index.memories.get(memory_id)

        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        # Check access
        if memory.user_id != current_user.get("user_id"):
            if not current_user.get("is_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

        return memory.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}"
        )


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    search_service: OptimizedMemorySearch = Depends(get_search_service),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a memory"""
    try:
        memory = search_service.index.memories.get(memory_id)

        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        # Check access
        if memory.user_id != current_user.get("user_id"):
            if not current_user.get("is_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

        # Delete from index
        del search_service.index.memories[memory_id]

        # Invalidate cache
        await search_service._invalidate_user_cache(memory.user_id)

        logger.info(f"Deleted memory {memory_id}")

        return {
            "status": "deleted",
            "memory_id": memory_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_memory_stats(
    search_service: OptimizedMemorySearch = Depends(get_search_service),
    current_user: Dict = Depends(get_current_user)
):
    """Get memory statistics"""
    try:
        stats = await search_service.get_stats()

        # Add user-specific stats if not admin
        if not current_user.get("is_admin"):
            user_id = current_user.get("user_id")
            user_memories = search_service.index.user_to_memories.get(user_id, set())
            stats["user_memory_count"] = len(user_memories)

        return stats

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )