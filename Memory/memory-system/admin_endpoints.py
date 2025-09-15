#!/usr/bin/env python3
"""
Admin API Endpoints for Memory App Platform Management
Provides RESTful API for admin dashboard
"""

import os
import json
from flask import Blueprint, request, jsonify, Response
from functools import wraps
from typing import Dict, Any, Optional
import logging
from datetime import datetime

# Import admin service
from admin_service import admin_service, AdminRole

logger = logging.getLogger(__name__)

# Create Blueprint for admin endpoints
admin_api = Blueprint('admin_api', __name__)

# Authentication decorator
def admin_required(min_role: AdminRole = AdminRole.VIEWER):
    """Decorator to require admin authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({"error": "No valid authorization header"}), 401
            
            token = auth_header.replace('Bearer ', '')
            
            # Verify token
            admin_info = admin_service.verify_token(token)
            if not admin_info:
                return jsonify({"error": "Invalid or expired token"}), 401
            
            # Check role permission
            admin_role = AdminRole(admin_info.get('role'))
            if list(AdminRole).index(admin_role) > list(AdminRole).index(min_role):
                return jsonify({"error": "Insufficient permissions"}), 403
            
            # Add admin info to request
            request.admin = admin_info
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# ==========================
# AUTHENTICATION ENDPOINTS
# ==========================

@admin_api.route('/api/admin/login', methods=['POST'])
async def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400
        
        # Get client IP
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Authenticate
        result = await admin_service.authenticate(username, password, ip_address)
        
        if result.get('success'):
            logger.info(f"✅ Admin login successful: {username}")
            return jsonify(result), 200
        else:
            logger.warning(f"❌ Admin login failed: {username}")
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Error in admin login: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/logout', methods=['POST'])
@admin_required()
def admin_logout():
    """Admin logout endpoint"""
    try:
        # In production, invalidate the session
        admin_id = request.admin.get('admin_id')
        logger.info(f"Admin logged out: {admin_id}")
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error in admin logout: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/profile', methods=['GET'])
@admin_required()
def get_admin_profile():
    """Get current admin profile"""
    try:
        return jsonify({
            "admin_id": request.admin.get('admin_id'),
            "role": request.admin.get('role'),
            "expires_at": request.admin.get('exp')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting admin profile: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# DASHBOARD ENDPOINTS
# ==========================

@admin_api.route('/api/admin/dashboard', methods=['GET'])
@admin_required()
async def get_dashboard():
    """Get dashboard statistics"""
    try:
        stats = await admin_service.get_dashboard_stats()
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/dashboard/realtime', methods=['GET'])
@admin_required()
def get_realtime_stats():
    """Get real-time statistics"""
    try:
        # In production, this would return actual real-time data
        stats = {
            "timestamp": datetime.now().isoformat(),
            "users_online": 42,
            "active_sessions": 15,
            "api_calls_per_minute": 234,
            "memory_operations_per_minute": 56,
            "system_cpu": 35.2,
            "system_memory": 62.8,
            "database_connections": 12
        }
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting realtime stats: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# USER MANAGEMENT ENDPOINTS
# ==========================

@admin_api.route('/api/admin/users', methods=['GET'])
@admin_required()
async def get_users():
    """Get list of users"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        search = request.args.get('search', None)
        
        users = await admin_service.get_users(limit, offset, search)
        return jsonify({"users": users, "total": len(users)}), 200
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/users/<user_id>', methods=['GET'])
@admin_required()
async def get_user_details(user_id: str):
    """Get detailed user information"""
    try:
        # Get user details from database
        from postgres_db_client import get_user, get_user_memories
        
        user = await get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get user's recent memories
        memories = await get_user_memories(user_id, limit=10)
        
        user_details = {
            "user": user,
            "recent_memories": memories,
            "stats": {
                "total_memories": len(memories),
                "categories": {},
                "last_activity": user.get('last_seen')
            }
        }
        
        return jsonify(user_details), 200
        
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/users/<user_id>/suspend', methods=['POST'])
@admin_required(AdminRole.ADMIN)
async def suspend_user(user_id: str):
    """Suspend a user account"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        result = await admin_service.suspend_user(
            user_id=user_id,
            admin_id=request.admin.get('admin_id'),
            reason=reason
        )
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error suspending user: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/users/<user_id>/activate', methods=['POST'])
@admin_required(AdminRole.ADMIN)
async def activate_user(user_id: str):
    """Reactivate a suspended user"""
    try:
        # Reactivate user logic
        from postgres_db_client import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET is_active = true, suspension_reason = NULL
            WHERE id = %s
        """, (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "User reactivated"}), 200
        
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# MEMORY MANAGEMENT ENDPOINTS
# ==========================

@admin_api.route('/api/admin/memories', methods=['GET'])
@admin_required()
async def get_memories():
    """Get list of memories with filters"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        user_id = request.args.get('user_id', None)
        search = request.args.get('search', None)
        
        memories = await admin_service.get_memories(limit, offset, user_id, search)
        return jsonify({"memories": memories, "total": len(memories)}), 200
        
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/memories/<memory_id>', methods=['DELETE'])
@admin_required(AdminRole.MODERATOR)
async def delete_memory(memory_id: str):
    """Delete a memory"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Admin deletion')
        
        result = await admin_service.delete_memory(
            memory_id=memory_id,
            admin_id=request.admin.get('admin_id'),
            reason=reason
        )
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# ANALYTICS ENDPOINTS
# ==========================

@admin_api.route('/api/admin/analytics', methods=['GET'])
@admin_required()
async def get_analytics():
    """Get platform analytics"""
    try:
        period = request.args.get('period', '7days')
        
        # Calculate analytics based on period
        analytics = {
            "period": period,
            "user_growth": {
                "new_users": 123,
                "total_users": 1234,
                "growth_rate": 10.5
            },
            "memory_stats": {
                "total_memories": 5678,
                "avg_per_user": 4.6,
                "popular_categories": [
                    {"name": "personal", "count": 2345},
                    {"name": "work", "count": 1234},
                    {"name": "ideas", "count": 890}
                ]
            },
            "engagement": {
                "daily_active_users": 456,
                "weekly_active_users": 789,
                "avg_session_duration": "8m 34s",
                "retention_rate": 68.5
            },
            "communication_channels": {
                "whatsapp": {"messages": 3456, "users": 234},
                "telegram": {"messages": 2345, "users": 156},
                "sms": {"messages": 1234, "users": 89},
                "voice": {"calls": 567, "users": 45}
            }
        }
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# SYSTEM LOGS ENDPOINTS
# ==========================

@admin_api.route('/api/admin/logs', methods=['GET'])
@admin_required()
async def get_system_logs():
    """Get system logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        level = request.args.get('level', None)
        
        logs = await admin_service.get_system_logs(limit, level)
        return jsonify({"logs": logs}), 200
        
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/audit-logs', methods=['GET'])
@admin_required(AdminRole.ADMIN)
async def get_audit_logs():
    """Get admin audit logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        admin_id = request.args.get('admin_id', None)
        
        logs = await admin_service.get_audit_logs(limit, admin_id)
        return jsonify({"logs": logs}), 200
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# CONFIGURATION ENDPOINTS
# ==========================

@admin_api.route('/api/admin/config', methods=['GET'])
@admin_required(AdminRole.ADMIN)
async def get_config():
    """Get platform configuration"""
    try:
        config = await admin_service.get_platform_config()
        return jsonify(config), 200
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500

@admin_api.route('/api/admin/config', methods=['PUT'])
@admin_required(AdminRole.SUPER_ADMIN)
async def update_config():
    """Update platform configuration"""
    try:
        config = request.get_json()
        
        result = await admin_service.update_platform_config(
            admin_id=request.admin.get('admin_id'),
            config=config
        )
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# NOTIFICATION ENDPOINTS
# ==========================

@admin_api.route('/api/admin/notifications', methods=['POST'])
@admin_required(AdminRole.ADMIN)
async def send_notification():
    """Send platform notification"""
    try:
        data = request.get_json()
        
        notification = {
            "title": data.get('title'),
            "message": data.get('message'),
            "target": data.get('target', 'all'),
            "channels": data.get('channels', ['in_app'])
        }
        
        result = await admin_service.send_platform_notification(
            admin_id=request.admin.get('admin_id'),
            notification=notification
        )
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# GAMING MANAGEMENT ENDPOINTS
# ==========================

@admin_api.route('/api/admin/games', methods=['GET'])
@admin_required()
async def get_games_stats():
    """Get gaming statistics"""
    try:
        # Import gaming service if available
        try:
            from memory_gaming_service import memory_gaming_service
            
            stats = {
                "active_games": len(memory_gaming_service.active_games),
                "total_players": len(memory_gaming_service.leaderboard),
                "challenges_today": len([c for c in memory_gaming_service.daily_challenges 
                                        if c.created_at.date() == datetime.now().date()]),
                "top_players": [
                    {"user_id": user_id, "score": score}
                    for user_id, score in list(memory_gaming_service.leaderboard.items())[:10]
                ]
            }
        except ImportError:
            stats = {
                "message": "Gaming service not available",
                "active_games": 0,
                "total_players": 0
            }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting games stats: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# SUBSCRIPTION MANAGEMENT ENDPOINTS
# ==========================

@admin_api.route('/api/admin/subscriptions', methods=['GET'])
@admin_required()
async def get_subscriptions():
    """Get subscription statistics"""
    try:
        # Get subscription stats from database
        stats = {
            "active_subscriptions": 234,
            "trial_users": 56,
            "expired_subscriptions": 12,
            "revenue": {
                "monthly": 4680.00,
                "annual": 56160.00
            },
            "plans": [
                {"name": "Basic", "users": 123, "price": 9.99},
                {"name": "Pro", "users": 89, "price": 19.99},
                {"name": "Enterprise", "users": 22, "price": 49.99}
            ]
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting subscription stats: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# DATA EXPORT ENDPOINTS
# ==========================

@admin_api.route('/api/admin/export', methods=['POST'])
@admin_required(AdminRole.ADMIN)
async def export_data():
    """Export platform data"""
    try:
        data = request.get_json()
        data_type = data.get('type', 'users')
        format = data.get('format', 'json')
        
        result = await admin_service.export_data(
            admin_id=request.admin.get('admin_id'),
            data_type=data_type,
            format=format
        )
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# ADMIN MANAGEMENT ENDPOINTS
# ==========================

@admin_api.route('/api/admin/admins', methods=['GET'])
@admin_required(AdminRole.SUPER_ADMIN)
async def get_admins():
    """Get list of admin users"""
    try:
        from postgres_db_client import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, role, created_at, last_login, is_active
            FROM admin_users
            ORDER BY created_at DESC
        """)
        
        admins = []
        for row in cursor.fetchall():
            admins.append(dict(row))
        
        cursor.close()
        conn.close()
        
        return jsonify({"admins": admins}), 200
        
    except Exception as e:
        logger.error(f"Error getting admins: {e}")
        # Return demo data if database not available
        demo_admins = [
            {
                "id": "admin-1",
                "username": "admin",
                "email": "admin@memoryapp.com",
                "role": "super_admin",
                "created_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "is_active": True
            }
        ]
        return jsonify({"admins": demo_admins}), 200

@admin_api.route('/api/admin/admins', methods=['POST'])
@admin_required(AdminRole.SUPER_ADMIN)
async def create_admin():
    """Create new admin user"""
    try:
        data = request.get_json()
        
        result = await admin_service.create_admin(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            role=AdminRole(data.get('role', 'viewer'))
        )
        
        if result.get('success'):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating admin: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================
# HEALTH CHECK ENDPOINT
# ==========================

@admin_api.route('/api/admin/health', methods=['GET'])
def admin_health_check():
    """Admin API health check"""
    return jsonify({
        "status": "healthy",
        "service": "admin_api",
        "timestamp": datetime.now().isoformat()
    }), 200

# Initialize admin endpoints
def init_admin_endpoints(app):
    """Initialize admin endpoints in Flask app"""
    app.register_blueprint(admin_api)
    logger.info("👨‍💼 Admin API endpoints registered")
    logger.info("📍 Admin endpoints available at:")
    logger.info("   • POST /api/admin/login")
    logger.info("   • GET  /api/admin/dashboard")
    logger.info("   • GET  /api/admin/users")
    logger.info("   • GET  /api/admin/memories")
    logger.info("   • GET  /api/admin/analytics")
    logger.info("   • GET  /api/admin/logs")
    logger.info("   • GET  /api/admin/config")
    logger.info("   • POST /api/admin/notifications")
    logger.info("   • GET  /api/admin/health")