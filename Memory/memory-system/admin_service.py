#!/usr/bin/env python3
"""
Admin Service Module for Memory App Platform Management
Provides administrative functions, authentication, and platform management
"""

import os
import json
import hashlib
import secrets
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import asyncio
from functools import wraps
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database client
try:
    from postgres_db_client import get_connection
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    get_connection = None  # Define placeholder to avoid unbound errors
    logger.warning("⚠️ Database client not available")

# Admin roles
class AdminRole(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    VIEWER = "viewer"

# Admin permissions
ROLE_PERMISSIONS = {
    AdminRole.SUPER_ADMIN: [
        "view_all", "edit_all", "delete_all", "manage_admins",
        "manage_config", "view_logs", "send_notifications", "export_data"
    ],
    AdminRole.ADMIN: [
        "view_all", "edit_users", "delete_memories", "manage_users",
        "view_logs", "send_notifications", "export_data"
    ],
    AdminRole.MODERATOR: [
        "view_all", "edit_memories", "delete_memories", "manage_users",
        "view_logs"
    ],
    AdminRole.VIEWER: [
        "view_all", "view_logs"
    ]
}

@dataclass
class AdminUser:
    """Admin user model"""
    id: str
    username: str
    email: str
    password_hash: str
    role: AdminRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    ip_whitelist: List[str] = field(default_factory=list)

    def has_permission(self, permission: str) -> bool:
        """Check if admin has specific permission"""
        return permission in ROLE_PERMISSIONS.get(self.role, [])

class AdminService:
    """Main admin service class"""
    
    def __init__(self):
        self.jwt_secret = os.environ.get('ADMIN_JWT_SECRET', secrets.token_hex(32))
        self.session_duration = timedelta(hours=8)
        self.audit_logs = []
        self.active_sessions = {}
        
        # Initialize database schema if available
        if DATABASE_AVAILABLE:
            self._init_admin_schema()
        
        # Create default super admin if none exists
        self._ensure_super_admin()
        
        logger.info("👨‍💼 Admin Service initialized")
    
    def _init_admin_schema(self):
        """Initialize admin database schema"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Create admin_users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_login TIMESTAMPTZ,
                    is_active BOOLEAN DEFAULT true,
                    two_factor_enabled BOOLEAN DEFAULT false,
                    two_factor_secret TEXT,
                    ip_whitelist TEXT[],
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            # Create audit_logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    admin_id UUID REFERENCES admin_users(id),
                    action VARCHAR(100) NOT NULL,
                    target_type VARCHAR(50),
                    target_id VARCHAR(255),
                    details JSONB,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    timestamp TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Create admin_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    admin_id UUID REFERENCES admin_users(id),
                    token_hash TEXT UNIQUE NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL,
                    is_active BOOLEAN DEFAULT true
                )
            """)
            
            conn.commit()
            logger.info("✅ Admin database schema initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize admin schema: {e}")
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def _ensure_super_admin(self):
        """Create default super admin if none exists"""
        try:
            # Check if super admin exists
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM admin_users WHERE role = %s LIMIT 1", (AdminRole.SUPER_ADMIN.value,))
                if cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return
            
            # Create default super admin
            default_password = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'admin123!@#')
            self.create_admin(
                username='admin',
                email='admin@memoryapp.com',
                password=default_password,
                role=AdminRole.SUPER_ADMIN
            )
            logger.info("🔐 Default super admin created (username: admin)")
            
        except Exception as e:
            logger.error(f"Failed to ensure super admin: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_value = password_hash.split(':')
            test_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
            return test_hash == hash_value
        except:
            return False
    
    async def create_admin(self, username: str, email: str, password: str, 
                          role: AdminRole) -> Dict[str, Any]:
        """Create new admin user"""
        try:
            admin_id = str(uuid.uuid4())
            password_hash = self._hash_password(password)
            
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO admin_users (id, username, email, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (admin_id, username, email, password_hash, role.value))
                
                admin = cursor.fetchone()
                conn.commit()
                cursor.close()
                conn.close()
                
                await self._log_audit(
                    admin_id=admin_id,
                    action="admin_created",
                    details={"username": username, "role": role.value}
                )
                
                logger.info(f"✅ Admin created: {username} ({role.value})")
                return {"success": True, "admin_id": admin_id}
            else:
                # Fallback to in-memory storage
                return {"success": True, "admin_id": admin_id, "demo": True}
                
        except Exception as e:
            logger.error(f"❌ Failed to create admin: {e}")
            return {"success": False, "error": str(e)}
    
    async def authenticate(self, username: str, password: str, 
                           ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate admin user"""
        try:
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Get admin user
                cursor.execute("""
                    SELECT * FROM admin_users 
                    WHERE username = %s AND is_active = true
                """, (username,))
                
                admin = cursor.fetchone()
                
                if not admin:
                    return {"success": False, "error": "Invalid credentials"}
                
                # Verify password
                if not self._verify_password(password, admin['password_hash']):
                    await self._log_audit(
                        admin_id=None,
                        action="failed_login",
                        details={"username": username},
                        ip_address=ip_address
                    )
                    return {"success": False, "error": "Invalid credentials"}
                
                # Check IP whitelist if configured
                if admin['ip_whitelist'] and ip_address:
                    if ip_address not in admin['ip_whitelist']:
                        return {"success": False, "error": "IP not whitelisted"}
                
                # Generate JWT token
                token = self._generate_token(admin['id'], admin['role'])
                
                # Create session
                session_id = str(uuid.uuid4())
                expires_at = datetime.now() + self.session_duration
                
                cursor.execute("""
                    INSERT INTO admin_sessions 
                    (id, admin_id, token_hash, ip_address, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session_id, admin['id'], hashlib.sha256(token.encode()).hexdigest(), 
                      ip_address, expires_at))
                
                # Update last login
                cursor.execute("""
                    UPDATE admin_users SET last_login = NOW() WHERE id = %s
                """, (admin['id'],))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                await self._log_audit(
                    admin_id=admin['id'],
                    action="login",
                    ip_address=ip_address
                )
                
                logger.info(f"✅ Admin authenticated: {username}")
                
                return {
                    "success": True,
                    "token": token,
                    "admin": {
                        "id": admin['id'],
                        "username": admin['username'],
                        "email": admin['email'],
                        "role": admin['role']
                    }
                }
            else:
                # Demo mode authentication
                if username == "admin" and password in ["admin123!@#", "demo"]:
                    token = self._generate_token("demo-admin", AdminRole.SUPER_ADMIN.value)
                    return {
                        "success": True,
                        "token": token,
                        "admin": {
                            "id": "demo-admin",
                            "username": "admin",
                            "email": "admin@demo.com",
                            "role": AdminRole.SUPER_ADMIN.value
                        },
                        "demo": True
                    }
                return {"success": False, "error": "Invalid credentials"}
                
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_token(self, admin_id: str, role: str) -> str:
        """Generate JWT token for admin"""
        payload = {
            "admin_id": admin_id,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.session_duration
        }
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return admin info"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        try:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "users": {"total": 0, "active_today": 0, "new_today": 0},
                "memories": {"total": 0, "today": 0, "this_week": 0},
                "system": {"status": "healthy", "uptime": "0h", "api_calls": 0},
                "communications": {"whatsapp": 0, "telegram": 0, "sms": 0, "voice": 0},
                "games": {"active": 0, "completed": 0, "challenges": 0},
                "subscriptions": {"active": 0, "trial": 0, "expired": 0}
            }
            
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Get user stats
                cursor.execute("SELECT COUNT(*) as total FROM users")
                stats["users"]["total"] = cursor.fetchone()["total"]
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM users 
                    WHERE last_seen > NOW() - INTERVAL '24 hours'
                """)
                stats["users"]["active_today"] = cursor.fetchone()["count"]
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM users 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                stats["users"]["new_today"] = cursor.fetchone()["count"]
                
                # Get memory stats
                cursor.execute("SELECT COUNT(*) as total FROM memories")
                stats["memories"]["total"] = cursor.fetchone()["total"]
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM memories 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                stats["memories"]["today"] = cursor.fetchone()["count"]
                
                cursor.execute("""
                    SELECT COUNT(*) as count FROM memories 
                    WHERE created_at > NOW() - INTERVAL '7 days'
                """)
                stats["memories"]["this_week"] = cursor.fetchone()["count"]
                
                # Get communication stats
                cursor.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM memories 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY source
                """)
                for row in cursor.fetchall():
                    source = row["source"]
                    if "whatsapp" in source.lower():
                        stats["communications"]["whatsapp"] = row["count"]
                    elif "telegram" in source.lower():
                        stats["communications"]["telegram"] = row["count"]
                    elif "sms" in source.lower():
                        stats["communications"]["sms"] = row["count"]
                    elif "voice" in source.lower():
                        stats["communications"]["voice"] = row["count"]
                
                cursor.close()
                conn.close()
                
            else:
                # Demo stats
                import random
                stats["users"]["total"] = 1234
                stats["users"]["active_today"] = 456
                stats["users"]["new_today"] = 78
                stats["memories"]["total"] = 5678
                stats["memories"]["today"] = 234
                stats["memories"]["this_week"] = 890
                stats["communications"]["whatsapp"] = random.randint(50, 200)
                stats["communications"]["telegram"] = random.randint(30, 150)
                stats["communications"]["sms"] = random.randint(20, 100)
                stats["communications"]["voice"] = random.randint(10, 50)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard stats: {e}")
            return {"error": str(e)}
    
    async def get_users(self, limit: int = 100, offset: int = 0, 
                       search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of users with optional search"""
        try:
            users = []
            
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                if search:
                    query = """
                        SELECT id, phone_number, name, created_at, last_seen,
                               subscription_status, memory_count
                        FROM users 
                        WHERE phone_number ILIKE %s OR name ILIKE %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(query, (f"%{search}%", f"%{search}%", limit, offset))
                else:
                    query = """
                        SELECT id, phone_number, name, created_at, last_seen,
                               subscription_status, memory_count
                        FROM users 
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(query, (limit, offset))
                
                for row in cursor.fetchall():
                    users.append(dict(row))
                
                cursor.close()
                conn.close()
            else:
                # Demo users
                users = [
                    {
                        "id": "user-1",
                        "phone_number": "+1234567890",
                        "name": "Alice Johnson",
                        "created_at": datetime.now().isoformat(),
                        "last_seen": datetime.now().isoformat(),
                        "subscription_status": "active",
                        "memory_count": 45
                    },
                    {
                        "id": "user-2",
                        "phone_number": "+0987654321",
                        "name": "Bob Smith",
                        "created_at": datetime.now().isoformat(),
                        "last_seen": datetime.now().isoformat(),
                        "subscription_status": "trial",
                        "memory_count": 12
                    }
                ]
            
            return users
            
        except Exception as e:
            logger.error(f"❌ Failed to get users: {e}")
            return []
    
    async def get_memories(self, limit: int = 100, offset: int = 0,
                          user_id: Optional[str] = None,
                          search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of memories with optional filters"""
        try:
            memories = []
            
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                query = "SELECT * FROM memories WHERE 1=1"
                params = []
                
                if user_id:
                    query += " AND user_id = %s"
                    params.append(user_id)
                
                if search:
                    query += " AND content ILIKE %s"
                    params.append(f"%{search}%")
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    memories.append(dict(row))
                
                cursor.close()
                conn.close()
            else:
                # Demo memories
                memories = [
                    {
                        "id": "mem-1",
                        "user_id": "user-1",
                        "content": "Remember to call mom on her birthday",
                        "category": "personal",
                        "created_at": datetime.now().isoformat()
                    },
                    {
                        "id": "mem-2",
                        "user_id": "user-2",
                        "content": "Project deadline is next Friday",
                        "category": "work",
                        "created_at": datetime.now().isoformat()
                    }
                ]
            
            return memories
            
        except Exception as e:
            logger.error(f"❌ Failed to get memories: {e}")
            return []
    
    async def suspend_user(self, user_id: str, admin_id: str, reason: str) -> Dict[str, Any]:
        """Suspend a user account"""
        try:
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE users 
                    SET is_active = false, suspension_reason = %s, suspended_at = NOW()
                    WHERE id = %s
                """, (reason, user_id))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                await self._log_audit(
                    admin_id=admin_id,
                    action="user_suspended",
                    target_type="user",
                    target_id=user_id,
                    details={"reason": reason}
                )
                
                logger.info(f"⛔ User suspended: {user_id}")
                return {"success": True}
            else:
                return {"success": True, "demo": True}
                
        except Exception as e:
            logger.error(f"❌ Failed to suspend user: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_memory(self, memory_id: str, admin_id: str, reason: str) -> Dict[str, Any]:
        """Delete a memory with audit log"""
        try:
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Get memory details first for audit
                cursor.execute("SELECT * FROM memories WHERE id = %s", (memory_id,))
                memory = cursor.fetchone()
                
                if memory:
                    # Delete the memory
                    cursor.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
                    
                    conn.commit()
                    
                    await self._log_audit(
                        admin_id=admin_id,
                        action="memory_deleted",
                        target_type="memory",
                        target_id=memory_id,
                        details={"reason": reason, "user_id": memory["user_id"]}
                    )
                    
                    logger.info(f"🗑️ Memory deleted: {memory_id}")
                    return {"success": True}
                else:
                    return {"success": False, "error": "Memory not found"}
                
                cursor.close()
                conn.close()
            else:
                return {"success": True, "demo": True}
                
        except Exception as e:
            logger.error(f"❌ Failed to delete memory: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_system_logs(self, limit: int = 100, 
                             level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get system logs"""
        try:
            logs = []
            
            # Read from log files or database
            # For now, return demo logs
            import random
            levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
            
            for i in range(min(limit, 20)):
                log_level = level.upper() if level else random.choice(levels)
                logs.append({
                    "timestamp": (datetime.now() - timedelta(minutes=i*5)).isoformat(),
                    "level": log_level,
                    "module": random.choice(["memory_app", "webhook_server", "telegram_bot", "whatsapp_bot"]),
                    "message": f"Sample log message {i+1}",
                    "details": {}
                })
            
            return logs
            
        except Exception as e:
            logger.error(f"❌ Failed to get system logs: {e}")
            return []
    
    async def get_audit_logs(self, limit: int = 100, 
                            admin_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get admin audit logs"""
        try:
            logs = []
            
            if DATABASE_AVAILABLE:
                conn = get_connection()
                cursor = conn.cursor()
                
                if admin_id:
                    query = """
                        SELECT al.*, au.username 
                        FROM admin_audit_logs al
                        JOIN admin_users au ON al.admin_id = au.id
                        WHERE al.admin_id = %s
                        ORDER BY al.timestamp DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (admin_id, limit))
                else:
                    query = """
                        SELECT al.*, au.username 
                        FROM admin_audit_logs al
                        JOIN admin_users au ON al.admin_id = au.id
                        ORDER BY al.timestamp DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (limit,))
                
                for row in cursor.fetchall():
                    logs.append(dict(row))
                
                cursor.close()
                conn.close()
            else:
                # Return in-memory audit logs
                logs = self.audit_logs[-limit:]
            
            return logs
            
        except Exception as e:
            logger.error(f"❌ Failed to get audit logs: {e}")
            return []
    
    async def _log_audit(self, admin_id: Optional[str], action: str,
                        target_type: Optional[str] = None,
                        target_id: Optional[str] = None,
                        details: Optional[Dict] = None,
                        ip_address: Optional[str] = None):
        """Log admin action for audit trail"""
        try:
            audit_entry = {
                "id": str(uuid.uuid4()),
                "admin_id": admin_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "details": details or {},
                "ip_address": ip_address,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in memory
            self.audit_logs.append(audit_entry)
            
            # Store in database if available
            if DATABASE_AVAILABLE and admin_id:
                conn = get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO admin_audit_logs 
                    (admin_id, action, target_type, target_id, details, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (admin_id, action, target_type, target_id, 
                      json.dumps(details) if details else None, ip_address))
                
                conn.commit()
                cursor.close()
                conn.close()
                
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")
    
    async def send_platform_notification(self, admin_id: str, 
                                        notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send platform-wide notification"""
        try:
            # Log the action
            await self._log_audit(
                admin_id=admin_id,
                action="notification_sent",
                details=notification
            )
            
            # In production, this would send actual notifications
            # For now, just log and return success
            logger.info(f"📢 Platform notification sent: {notification.get('title')}")
            
            return {"success": True, "sent_to": "all_users"}
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
            return {"success": False, "error": str(e)}
    
    async def export_data(self, admin_id: str, data_type: str,
                         format: str = "json") -> Dict[str, Any]:
        """Export platform data"""
        try:
            # Log the action
            await self._log_audit(
                admin_id=admin_id,
                action="data_exported",
                details={"type": data_type, "format": format}
            )
            
            # Generate export file path
            export_file = f"/tmp/export_{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
            
            # In production, this would actually export data
            # For now, create a sample file
            with open(export_file, 'w') as f:
                if format == "json":
                    json.dump({"export": data_type, "timestamp": datetime.now().isoformat()}, f)
                else:
                    f.write(f"Export of {data_type} data\n")
            
            logger.info(f"📤 Data exported: {export_file}")
            
            return {"success": True, "file": export_file}
            
        except Exception as e:
            logger.error(f"❌ Failed to export data: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_platform_config(self) -> Dict[str, Any]:
        """Get platform configuration"""
        try:
            config = {
                "platform_name": "Memory App",
                "version": "1.0.0",
                "features": {
                    "whatsapp": True,
                    "telegram": True,
                    "voice_auth": True,
                    "voice_cloning": True,
                    "gaming": True,
                    "subscriptions": True
                },
                "limits": {
                    "max_memories_per_user": 1000,
                    "max_file_size_mb": 10,
                    "max_voice_duration_seconds": 120
                },
                "maintenance_mode": False
            }
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Failed to get config: {e}")
            return {"error": str(e)}
    
    async def update_platform_config(self, admin_id: str, 
                                    config: Dict[str, Any]) -> Dict[str, Any]:
        """Update platform configuration"""
        try:
            # Log the action
            await self._log_audit(
                admin_id=admin_id,
                action="config_updated",
                details=config
            )
            
            # In production, this would update actual configuration
            logger.info(f"⚙️ Platform config updated")
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"❌ Failed to update config: {e}")
            return {"success": False, "error": str(e)}

# Create singleton instance
admin_service = AdminService()

# Export for use in other modules
__all__ = ['admin_service', 'AdminRole', 'AdminUser']