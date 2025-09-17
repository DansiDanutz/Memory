#!/usr/bin/env python3
"""
Audit Logging System
Tracks all operations for compliance and security
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum
import threading
import queue

logger = logging.getLogger(__name__)

class AuditAction(Enum):
    """Audit action types"""
    # Memory operations
    MEMORY_STORED = "memory.stored"
    MEMORY_READ = "memory.read"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_SEARCHED = "memory.searched"
    MEMORY_UPDATED = "memory.updated"
    
    # Authentication
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILED = "auth.failed"
    SESSION_CREATED = "session.created"
    SESSION_EXPIRED = "session.expired"
    
    # Search operations
    SEARCH_PERSONAL = "search.personal"
    SEARCH_DEPARTMENT = "search.department"
    SEARCH_TENANT = "search.tenant"
    SEARCH_CROSS_TENANT = "search.cross_tenant"
    
    # Administrative
    USER_ADDED = "user.added"
    USER_REMOVED = "user.removed"
    ROLE_CHANGED = "role.changed"
    TENANT_ACCESSED = "tenant.accessed"
    
    # System operations
    BACKUP_CREATED = "backup.created"
    BACKUP_RESTORED = "backup.restored"
    CONFIG_CHANGED = "config.changed"
    
    # Security events
    ACCESS_DENIED = "access.denied"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    ENCRYPTION_APPLIED = "security.encrypted"
    DECRYPTION_PERFORMED = "security.decrypted"

class AuditLogger:
    """Centralized audit logging system"""
    
    def __init__(self, audit_dir: str = "data/audit"):
        """Initialize audit logger"""
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Current log file
        self.current_date = datetime.now().date()
        self.log_file = self._get_log_file()
        
        # Async queue for high-performance logging
        self.log_queue = queue.Queue()
        self.running = True
        
        # Start background writer thread
        self.writer_thread = threading.Thread(target=self._writer_worker, daemon=True)
        self.writer_thread.start()
        
        logger.info(f"📝 Audit logger initialized at {self.audit_dir}")
    
    def _get_log_file(self, date: Optional[datetime] = None) -> Path:
        """Get log file path for a specific date"""
        if not date:
            date = datetime.now()
        
        filename = f"audit_{date.strftime('%Y-%m-%d')}.jsonl"
        return self.audit_dir / filename
    
    def _writer_worker(self):
        """Background worker to write audit logs"""
        while self.running:
            try:
                # Get log entry from queue (timeout to check running flag)
                entry = self.log_queue.get(timeout=1)
                
                # Check if we need to rotate log file
                current_date = datetime.now().date()
                if current_date != self.current_date:
                    self.current_date = current_date
                    self.log_file = self._get_log_file()
                
                # Write to file
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(entry) + '\n')
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Audit writer error: {e}")
    
    def log(self, action: AuditAction, user_phone: str, 
           details: Optional[Dict[str, Any]] = None,
           tenant_id: Optional[str] = None,
           department_id: Optional[str] = None,
           sensitivity: Optional[str] = None) -> str:
        """
        Log an audit event
        
        Args:
            action: Type of action performed
            user_phone: User who performed the action
            details: Additional details about the action
            tenant_id: Tenant context
            department_id: Department context
            sensitivity: Data sensitivity level
        
        Returns:
            Audit entry ID
        """
        # Generate audit entry
        entry_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        entry = {
            'id': entry_id,
            'timestamp': datetime.now().isoformat(),
            'action': action.value,
            'user': user_phone,
            'tenant_id': tenant_id,
            'department_id': department_id,
            'sensitivity': sensitivity,
            'details': details or {},
            'ip_address': self._get_ip_address(),
            'session_id': self._get_session_id()
        }
        
        # Add to queue for async writing
        self.log_queue.put(entry)
        
        # Log critical events immediately
        if action in [AuditAction.AUTH_FAILED, AuditAction.ACCESS_DENIED, 
                     AuditAction.SUSPICIOUS_ACTIVITY]:
            logger.warning(f"Security event: {action.value} by {user_phone}")
        
        return entry_id
    
    def _get_ip_address(self) -> Optional[str]:
        """Get client IP address (placeholder for actual implementation)"""
        # In production, this would get the actual client IP
        return "127.0.0.1"
    
    def _get_session_id(self) -> Optional[str]:
        """Get current session ID (placeholder for actual implementation)"""
        # In production, this would get the actual session ID
        return None
    
    def search_logs(self, filters: Dict[str, Any], 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search audit logs with filters
        
        Args:
            filters: Filter criteria (user, action, tenant, etc.)
            start_date: Start date for search
            end_date: End date for search
            limit: Maximum results to return
        
        Returns:
            List of matching audit entries
        """
        results = []
        
        # Default date range (last 7 days)
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # Iterate through log files in date range
        current_date = start_date.date()
        while current_date <= end_date.date():
            log_file = self._get_log_file(datetime.combine(current_date, datetime.min.time()))
            
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            
                            # Apply filters
                            if self._match_filters(entry, filters):
                                results.append(entry)
                                
                                if len(results) >= limit:
                                    return results
                        
                        except json.JSONDecodeError:
                            continue
            
            current_date += timedelta(days=1)
        
        return results
    
    def _match_filters(self, entry: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if entry matches all filters"""
        for key, value in filters.items():
            if key == 'action' and isinstance(value, AuditAction):
                if entry.get('action') != value.value:
                    return False
            elif entry.get(key) != value:
                return False
        
        return True
    
    def get_user_activity(self, user_phone: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent activity for a user"""
        return self.search_logs(
            filters={'user': user_phone},
            start_date=datetime.now() - timedelta(days=days),
            limit=50
        )
    
    def get_security_events(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get recent security events"""
        security_actions = [
            AuditAction.AUTH_FAILED,
            AuditAction.ACCESS_DENIED,
            AuditAction.SUSPICIOUS_ACTIVITY
        ]
        
        results = []
        for action in security_actions:
            results.extend(self.search_logs(
                filters={'action': action},
                start_date=datetime.now() - timedelta(days=days),
                limit=20
            ))
        
        return sorted(results, key=lambda x: x['timestamp'], reverse=True)
    
    def generate_compliance_report(self, tenant_id: str, 
                                  start_date: datetime,
                                  end_date: datetime) -> Dict[str, Any]:
        """
        Generate compliance report for a tenant
        
        Args:
            tenant_id: Tenant ID
            start_date: Report start date
            end_date: Report end date
        
        Returns:
            Compliance report data
        """
        # Get all logs for tenant in date range
        logs = self.search_logs(
            filters={'tenant_id': tenant_id},
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Analyze logs
        report = {
            'tenant_id': tenant_id,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_events': len(logs),
            'users': set(),
            'actions': {},
            'sensitivity_levels': {},
            'departments': {},
            'security_events': 0
        }
        
        for log in logs:
            # Count users
            report['users'].add(log['user'])
            
            # Count actions
            action = log['action']
            report['actions'][action] = report['actions'].get(action, 0) + 1
            
            # Count sensitivity levels
            sensitivity = log.get('sensitivity')
            if sensitivity:
                report['sensitivity_levels'][sensitivity] = \
                    report['sensitivity_levels'].get(sensitivity, 0) + 1
            
            # Count departments
            dept = log.get('department_id')
            if dept:
                report['departments'][dept] = report['departments'].get(dept, 0) + 1
            
            # Count security events
            if log['action'] in ['auth.failed', 'access.denied', 'security.suspicious']:
                report['security_events'] += 1
        
        # Convert sets to lists for JSON serialization
        report['users'] = list(report['users'])
        report['user_count'] = len(report['users'])
        
        return report
    
    def rotate_logs(self, retention_days: int = 30):
        """
        Rotate old log files
        
        Args:
            retention_days: Number of days to retain logs
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for log_file in self.audit_dir.glob("audit_*.jsonl"):
            # Extract date from filename
            try:
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    # Archive or delete old log
                    archive_dir = self.audit_dir / "archive"
                    archive_dir.mkdir(exist_ok=True)
                    
                    # Move to archive
                    log_file.rename(archive_dir / log_file.name)
                    logger.info(f"Archived old audit log: {log_file.name}")
            
            except ValueError:
                continue
    
    def stop(self):
        """Stop the audit logger"""
        self.running = False
        if self.writer_thread:
            self.writer_thread.join(timeout=5)

# Singleton instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get or create audit logger singleton"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger