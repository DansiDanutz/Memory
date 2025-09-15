#!/usr/bin/env python3
"""
Enhanced Memory API Routes - Production Implementation
Handles advanced memory operations with background jobs, patterns, and insights
"""

import os
import sys
import json
import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify, session, g
from flask_cors import cross_origin
from functools import wraps
import logging

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import database models
from database.models import (
    DatabaseManager, HarvestedItem, DetectedPattern, BehavioralInsight,
    Job, JobStatus, JobType, AuditLog, AgreementStatus, SecurityLevel,
    SourceType, PatternType
)

# Import background jobs
from background_jobs import get_job_manager

# Import security components
try:
    from confidential_manager import ConfidentialManager
    from voice_auth import VoiceAuthManager
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    logging.warning("Security components not available")

# Import agents
try:
    from agents import (
        AgentFactory,
        MemoryHarvesterAgent,
        PatternAnalyzerAgent,
        RawMemoryInput,
        ContentType
    )
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    logging.warning("Agents not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
enhanced_memory_bp = Blueprint('enhanced_memory', __name__)

# Initialize components
db_manager = DatabaseManager()
job_manager = get_job_manager()

# Security managers
confidential_manager = ConfidentialManager() if SECURITY_AVAILABLE else None
voice_auth_manager = VoiceAuthManager() if SECURITY_AVAILABLE else None

# Rate limiting decorator
def rate_limit(max_calls=60, window=60):
    """Rate limiting decorator"""
    def decorator(f):
        calls = {}
        
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get user identifier
            user_id = session.get('user_id', request.remote_addr)
            current_time = datetime.utcnow()
            
            # Clean old entries
            calls[user_id] = [
                call_time for call_time in calls.get(user_id, [])
                if (current_time - call_time).seconds < window
            ]
            
            # Check rate limit
            if len(calls.get(user_id, [])) >= max_calls:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }), 429
            
            # Record this call
            calls.setdefault(user_id, []).append(current_time)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Voice authentication decorator
def require_voice_auth(security_level=SecurityLevel.CONFIDENTIAL):
    """Require voice authentication for sensitive operations"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not SECURITY_AVAILABLE:
                # Skip in development
                return f(*args, **kwargs)
            
            # Check voice authentication
            voice_token = request.headers.get('X-Voice-Token')
            if not voice_token:
                return jsonify({
                    'success': False,
                    'error': 'Voice authentication required',
                    'security_level': security_level.value
                }), 401
            
            # Verify voice token
            user_id = session.get('user_id')
            if not voice_auth_manager.verify_voice_token(user_id, voice_token):
                return jsonify({
                    'success': False,
                    'error': 'Invalid voice authentication'
                }), 401
            
            # Set voice verified flag
            g.voice_verified = True
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Audit logging decorator
def audit_log(action: str, resource_type: str = None):
    """Log sensitive operations for audit trail"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            # Execute function
            try:
                result = f(*args, **kwargs)
                success = True
                error_message = None
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Log the operation
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                with db_manager.get_session() as session:
                    log_entry = AuditLog(
                        user_id=session.get('user_id'),
                        action=action,
                        resource=kwargs.get('memory_id') or kwargs.get('job_id'),
                        resource_type=resource_type,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        voice_verified=g.get('voice_verified', False),
                        success=success,
                        error_message=error_message,
                        duration_ms=duration_ms
                    )
                    session.add(log_entry)
                    session.commit()
            
            return result
        return wrapper
    return decorator

def run_async(coro):
    """Helper to run async functions in Flask"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# ============= HARVEST ENDPOINTS =============

@enhanced_memory_bp.route('/api/harvest', methods=['POST'])
@cross_origin()
@rate_limit(max_calls=10, window=60)
@audit_log('memory.harvest', 'job')
def enqueue_harvest():
    """Enqueue a harvest job for the current user"""
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Prepare harvest metadata
        metadata = {
            'sources': data.get('sources', ['chat_message', 'email', 'calendar_event']),
            'time_range': data.get('time_range', {'days': 1}),
            'manual_trigger': True
        }
        
        # Enqueue the job
        job_id = run_async(job_manager.enqueue_job(
            JobType.HARVEST,
            user_id=user_id,
            extra_metadata=metadata
        ))
        
        logger.info(f"Harvest job {job_id} enqueued for user {user_id}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Harvest job enqueued successfully'
        })
        
    except Exception as e:
        logger.error(f"Error enqueueing harvest job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= PATTERN ENDPOINTS =============

@enhanced_memory_bp.route('/api/patterns', methods=['GET'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
def get_patterns():
    """Get detected patterns for the current user"""
    try:
        user_id = request.args.get('user_id') or session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        pattern_type = request.args.get('pattern_type')
        min_strength = float(request.args.get('min_strength', 0.0))
        
        with db_manager.get_session() as session:
            # Build query
            query = session.query(DetectedPattern).filter_by(
                user_id=user_id,
                is_active=True
            )
            
            # Apply filters
            if pattern_type:
                query = query.filter_by(pattern_type=PatternType[pattern_type.upper()])
            
            query = query.filter(DetectedPattern.strength >= min_strength)
            
            # Order by strength
            query = query.order_by(DetectedPattern.strength.desc())
            
            # Paginate
            total = query.count()
            patterns = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Format response
            pattern_list = []
            for pattern in patterns:
                pattern_list.append({
                    'id': pattern.id,
                    'type': pattern.pattern_type.value,
                    'strength': pattern.strength,
                    'confidence': pattern.confidence,
                    'description': pattern.description,
                    'frequency': pattern.frequency,
                    'triggers': pattern.triggers,
                    'participants': pattern.participants,
                    'locations': pattern.locations,
                    'time_windows': pattern.time_windows,
                    'supporting_memories': pattern.supporting_memories,
                    'prediction_accuracy': pattern.prediction_accuracy,
                    'first_detected': pattern.first_detected.isoformat() if pattern.first_detected else None,
                    'last_updated': pattern.last_updated.isoformat() if pattern.last_updated else None
                })
        
        return jsonify({
            'success': True,
            'patterns': pattern_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching patterns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= INSIGHTS ENDPOINTS =============

@enhanced_memory_bp.route('/api/insights', methods=['GET'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
def get_insights():
    """Get behavioral insights for the current user"""
    try:
        user_id = request.args.get('user_id') or session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        insight_type = request.args.get('insight_type')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        with db_manager.get_session() as session:
            # Build query
            query = session.query(BehavioralInsight).filter_by(
                user_id=user_id,
                is_active=True
            )
            
            # Apply filters
            if insight_type:
                query = query.filter_by(insight_type=insight_type)
            
            if unread_only:
                query = query.filter_by(is_read=False)
            
            # Order by confidence and recency
            query = query.order_by(
                BehavioralInsight.confidence.desc(),
                BehavioralInsight.created_at.desc()
            )
            
            # Paginate
            total = query.count()
            insights = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Format response
            insight_list = []
            for insight in insights:
                insight_list.append({
                    'id': insight.id,
                    'type': insight.insight_type,
                    'title': insight.title,
                    'description': insight.description,
                    'confidence': insight.confidence,
                    'supporting_patterns': insight.supporting_patterns,
                    'recommendations': insight.recommendations,
                    'impact_score': insight.impact_score,
                    'is_read': insight.is_read,
                    'action_taken': insight.action_taken,
                    'created_at': insight.created_at.isoformat() if insight.created_at else None
                })
            
            # Mark insights as read
            if not unread_only:
                query.update({'is_read': True})
                session.commit()
        
        return jsonify({
            'success': True,
            'insights': insight_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= JOB STATUS ENDPOINTS =============

@enhanced_memory_bp.route('/api/jobs/<job_id>', methods=['GET'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
def get_job_status(job_id):
    """Get status of a specific job"""
    try:
        status = job_manager.get_job_status(job_id)
        
        if not status:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        return jsonify({
            'success': True,
            'job': status
        })
        
    except Exception as e:
        logger.error(f"Error fetching job status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_memory_bp.route('/api/jobs', methods=['GET'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
def get_active_jobs():
    """Get list of active jobs"""
    try:
        user_id = session.get('user_id')
        jobs = job_manager.get_active_jobs()
        
        # Filter by user if not admin
        if user_id and not session.get('is_admin'):
            jobs = [j for j in jobs if j.get('user_id') == user_id]
        
        return jsonify({
            'success': True,
            'jobs': jobs
        })
        
    except Exception as e:
        logger.error(f"Error fetching active jobs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= REVIEW ENDPOINTS =============

@enhanced_memory_bp.route('/api/review/<memory_id>/agree', methods=['POST'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
@audit_log('memory.review.agree', 'memory')
def mark_memory_agreed(memory_id):
    """Mark a memory as agreed"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        with db_manager.get_session() as session:
            # Get the memory
            memory = session.query(HarvestedItem).filter_by(
                id=memory_id,
                user_id=user_id
            ).first()
            
            if not memory:
                return jsonify({'success': False, 'error': 'Memory not found'}), 404
            
            # Update agreement status
            memory.agreement_status = AgreementStatus.AGREED
            memory.updated_at = datetime.utcnow()
            session.commit()
        
        logger.info(f"Memory {memory_id} marked as agreed by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Memory marked as agreed'
        })
        
    except Exception as e:
        logger.error(f"Error marking memory as agreed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_memory_bp.route('/api/review/<memory_id>/disagree', methods=['POST'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
@audit_log('memory.review.disagree', 'memory')
def mark_memory_not_agreed(memory_id):
    """Mark a memory as not agreed"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        with db_manager.get_session() as session:
            # Get the memory
            memory = session.query(HarvestedItem).filter_by(
                id=memory_id,
                user_id=user_id
            ).first()
            
            if not memory:
                return jsonify({'success': False, 'error': 'Memory not found'}), 404
            
            # Update agreement status
            memory.agreement_status = AgreementStatus.NOT_AGREED
            memory.updated_at = datetime.utcnow()
            session.commit()
        
        logger.info(f"Memory {memory_id} marked as not agreed by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Memory marked as not agreed'
        })
        
    except Exception as e:
        logger.error(f"Error marking memory as not agreed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_memory_bp.route('/api/review/queue', methods=['GET'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
def get_review_queue():
    """Get pending memories for review"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        with db_manager.get_session() as session:
            # Query pending memories
            query = session.query(HarvestedItem).filter_by(
                user_id=user_id,
                agreement_status=AgreementStatus.PENDING
            ).order_by(HarvestedItem.created_at.desc())
            
            # Paginate
            total = query.count()
            memories = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Format response
            memory_list = []
            for memory in memories:
                memory_list.append({
                    'id': memory.id,
                    'content': memory.content,
                    'source_type': memory.source_type.value,
                    'quality_score': memory.quality_score,
                    'tags': memory.tags,
                    'participants': memory.participants,
                    'created_at': memory.created_at.isoformat() if memory.created_at else None,
                    'metadata': memory.extra_metadata
                })
        
        return jsonify({
            'success': True,
            'memories': memory_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching review queue: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= CONFIDENTIAL ENDPOINTS =============

@enhanced_memory_bp.route('/api/confidential/<memory_id>', methods=['GET'])
@cross_origin()
@require_voice_auth(SecurityLevel.CONFIDENTIAL)
@audit_log('memory.confidential.access', 'memory')
def get_confidential_memory(memory_id):
    """Get a confidential memory (requires voice auth)"""
    try:
        user_id = session.get('user_id')
        
        with db_manager.get_session() as session:
            memory = session.query(HarvestedItem).filter_by(
                id=memory_id,
                user_id=user_id,
                security_level=SecurityLevel.CONFIDENTIAL
            ).first()
            
            if not memory:
                return jsonify({'success': False, 'error': 'Memory not found'}), 404
            
            return jsonify({
                'success': True,
                'memory': {
                    'id': memory.id,
                    'content': memory.content,
                    'metadata': memory.extra_metadata,
                    'created_at': memory.created_at.isoformat()
                }
            })
        
    except Exception as e:
        logger.error(f"Error accessing confidential memory: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_memory_bp.route('/api/secret/<memory_id>', methods=['GET'])
@cross_origin()
@require_voice_auth(SecurityLevel.SECRET)
@audit_log('memory.secret.access', 'memory')
def get_secret_memory(memory_id):
    """Get a secret memory (requires voice auth)"""
    try:
        user_id = session.get('user_id')
        
        with db_manager.get_session() as session:
            memory = session.query(HarvestedItem).filter_by(
                id=memory_id,
                user_id=user_id,
                security_level=SecurityLevel.SECRET
            ).first()
            
            if not memory:
                return jsonify({'success': False, 'error': 'Memory not found'}), 404
            
            return jsonify({
                'success': True,
                'memory': {
                    'id': memory.id,
                    'content': memory.content,
                    'metadata': memory.extra_metadata,
                    'created_at': memory.created_at.isoformat()
                }
            })
        
    except Exception as e:
        logger.error(f"Error accessing secret memory: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= STATS ENDPOINTS =============

@enhanced_memory_bp.route('/api/stats', methods=['GET'])
@cross_origin()
@rate_limit(max_calls=100, window=60)
def get_user_stats():
    """Get user statistics"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        with db_manager.get_session() as session:
            # Get counts
            total_memories = session.query(HarvestedItem).filter_by(user_id=user_id).count()
            agreed_memories = session.query(HarvestedItem).filter_by(
                user_id=user_id,
                agreement_status=AgreementStatus.AGREED
            ).count()
            pending_memories = session.query(HarvestedItem).filter_by(
                user_id=user_id,
                agreement_status=AgreementStatus.PENDING
            ).count()
            
            total_patterns = session.query(DetectedPattern).filter_by(
                user_id=user_id,
                is_active=True
            ).count()
            
            total_insights = session.query(BehavioralInsight).filter_by(
                user_id=user_id,
                is_active=True
            ).count()
            
            unread_insights = session.query(BehavioralInsight).filter_by(
                user_id=user_id,
                is_active=True,
                is_read=False
            ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_memories': total_memories,
                'agreed_memories': agreed_memories,
                'pending_memories': pending_memories,
                'total_patterns': total_patterns,
                'total_insights': total_insights,
                'unread_insights': unread_insights
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Export blueprint
__all__ = ['enhanced_memory_bp']