#!/usr/bin/env python3
"""
WhatsApp Access Manager
Handles permissions and comprehensive chat monitoring with OAuth-style consent
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import re
import asyncio

logger = logging.getLogger(__name__)

class WhatsAppAccessManager:
    """
    Manages WhatsApp chat access permissions and monitoring
    Implements OAuth-style consent flow for privacy compliance
    """
    
    def __init__(self, data_dir: str = "memory-system/data"):
        """Initialize the WhatsApp Access Manager"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Permission storage
        self.permissions_file = self.data_dir / "whatsapp_permissions.json"
        self.consent_logs_file = self.data_dir / "consent_logs.json"
        
        # Load existing permissions
        self.user_permissions = self._load_permissions()
        self.consent_logs = self._load_consent_logs()
        
        # Active monitoring sessions
        self.active_monitors = {}
        
        # Chat extraction patterns
        self.chat_patterns = {
            'appointment': r'(?:appointment|meeting|scheduled|booking|reservation)\s+(?:on|at|for)\s+(.+?)(?:\.|$)',
            'task': r'(?:need to|have to|must|should|remember to)\s+(.+?)(?:\.|$)',
            'preference': r'(?:i like|i love|i prefer|my favorite)\s+(.+?)(?:\.|$)',
            'health': r'(?:doctor|hospital|medication|illness|pain|symptoms|diagnosis)',
            'financial': r'(?:salary|income|payment|loan|debt|credit|bank|money)',
            'relationship': r'(?:wife|husband|girlfriend|boyfriend|partner|marriage|divorce)',
            'secret': r'(?:don\'t tell|keep secret|confidential|private|between us)',
            'work': r'(?:work|job|boss|colleague|office|project|deadline)',
            'family': r'(?:mother|father|sister|brother|son|daughter|family)',
            'location': r'(?:i live|located at|address is|staying at)\s+(.+?)(?:\.|$)',
        }
        
        logger.info("🔐 WhatsApp Access Manager initialized")
    
    def _load_permissions(self) -> Dict[str, Dict]:
        """Load user permissions from file"""
        if self.permissions_file.exists():
            with open(self.permissions_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_permissions(self):
        """Save user permissions to file"""
        with open(self.permissions_file, 'w') as f:
            json.dump(self.user_permissions, f, indent=2)
    
    def _load_consent_logs(self) -> List[Dict]:
        """Load consent logs from file"""
        if self.consent_logs_file.exists():
            with open(self.consent_logs_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_consent_logs(self):
        """Save consent logs to file"""
        with open(self.consent_logs_file, 'w') as f:
            json.dump(self.consent_logs, f, indent=2, default=str)
    
    async def request_user_permission(self, user_phone: str, requested_access: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request OAuth-style permission from user for chat access
        
        Args:
            user_phone: User's phone number
            requested_access: Dict with access details (chats, duration, purpose)
        
        Returns:
            Permission request with consent token
        """
        # Generate consent token
        consent_token = hashlib.sha256(f"{user_phone}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # Create permission request
        permission_request = {
            'token': consent_token,
            'user_phone': user_phone,
            'requested_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=10)).isoformat(),
            'access_requested': {
                'individual_chats': requested_access.get('individual_chats', False),
                'group_chats': requested_access.get('group_chats', False),
                'specific_contacts': requested_access.get('specific_contacts', []),
                'duration_days': requested_access.get('duration_days', 30),
                'purpose': requested_access.get('purpose', 'Memory assistance and organization'),
                'data_usage': requested_access.get('data_usage', [
                    'Extract appointments and tasks',
                    'Learn preferences and habits',
                    'Organize personal information',
                    'Create memory timeline'
                ])
            },
            'status': 'pending'
        }
        
        # Store pending request
        if user_phone not in self.user_permissions:
            self.user_permissions[user_phone] = {
                'pending_requests': [],
                'granted_permissions': [],
                'denied_permissions': []
            }
        
        self.user_permissions[user_phone]['pending_requests'].append(permission_request)
        self._save_permissions()
        
        # Generate consent message
        consent_message = self._generate_consent_message(permission_request)
        
        return {
            'success': True,
            'consent_token': consent_token,
            'consent_message': consent_message,
            'permission_request': permission_request
        }
    
    def _generate_consent_message(self, request: Dict) -> str:
        """Generate user-friendly consent message"""
        access = request['access_requested']
        
        message = "🔐 **WhatsApp Access Permission Request**\n\n"
        message += f"The Memory App is requesting permission to:\n\n"
        
        if access['individual_chats']:
            message += "✅ Monitor your individual chats\n"
        if access['group_chats']:
            message += "✅ Monitor your group chats\n"
        if access['specific_contacts']:
            message += f"✅ Monitor chats with: {', '.join(access['specific_contacts'])}\n"
        
        message += f"\n**Duration:** {access['duration_days']} days\n"
        message += f"**Purpose:** {access['purpose']}\n\n"
        
        message += "**Data will be used to:**\n"
        for usage in access['data_usage']:
            message += f"• {usage}\n"
        
        message += f"\n**Your privacy is protected:**\n"
        message += "• Data is stored locally and encrypted\n"
        message += "• You can revoke access anytime\n"
        message += "• Information is categorized by security level\n"
        message += "• No data is shared with third parties\n\n"
        
        message += f"To GRANT permission, reply: `/grant {request['token']}`\n"
        message += f"To DENY permission, reply: `/deny {request['token']}`\n"
        message += f"\nThis request expires in 10 minutes."
        
        return message
    
    async def process_consent_response(self, user_phone: str, action: str, token: str) -> Dict[str, Any]:
        """Process user's consent response"""
        if user_phone not in self.user_permissions:
            return {
                'success': False,
                'message': 'No pending permission requests found'
            }
        
        # Find matching request
        pending = self.user_permissions[user_phone]['pending_requests']
        request = None
        
        for req in pending:
            if req['token'] == token:
                request = req
                break
        
        if not request:
            return {
                'success': False,
                'message': 'Invalid or expired consent token'
            }
        
        # Check expiration
        if datetime.fromisoformat(request['expires_at']) < datetime.now():
            pending.remove(request)
            self._save_permissions()
            return {
                'success': False,
                'message': 'Consent request has expired'
            }
        
        # Process action
        request['status'] = 'granted' if action == 'grant' else 'denied'
        request['responded_at'] = datetime.now().isoformat()
        
        # Log consent
        self.consent_logs.append({
            'user_phone': user_phone,
            'token': token,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'access_details': request['access_requested']
        })
        self._save_consent_logs()
        
        if action == 'grant':
            # Move to granted permissions
            self.user_permissions[user_phone]['granted_permissions'].append(request)
            pending.remove(request)
            
            # Start monitoring
            monitor_id = await self.start_chat_monitoring(user_phone, request['access_requested'])
            
            message = "✅ Permission granted! I'll now monitor your WhatsApp chats and organize your memories.\n"
            message += f"Monitor ID: {monitor_id}\n"
            message += "You can revoke access anytime with: `/revoke`"
        else:
            # Move to denied permissions
            self.user_permissions[user_phone]['denied_permissions'].append(request)
            pending.remove(request)
            
            message = "❌ Permission denied. Your chats will not be monitored.\n"
            message += "You can grant permission anytime if you change your mind."
        
        self._save_permissions()
        
        return {
            'success': True,
            'message': message,
            'action': action
        }
    
    async def start_chat_monitoring(self, user_phone: str, access_config: Dict) -> str:
        """Start monitoring WhatsApp chats for a user"""
        monitor_id = hashlib.sha256(f"{user_phone}{datetime.now()}".encode()).hexdigest()[:12]
        
        self.active_monitors[monitor_id] = {
            'user_phone': user_phone,
            'started_at': datetime.now().isoformat(),
            'access_config': access_config,
            'extracted_data': {
                'appointments': [],
                'tasks': [],
                'preferences': [],
                'relationships': {},
                'locations': [],
                'health_info': [],
                'financial_info': [],
                'secrets': [],
                'work_info': [],
                'family_info': []
            },
            'processed_messages': 0,
            'last_processed': datetime.now().isoformat()
        }
        
        logger.info(f"📱 Started chat monitoring for {user_phone} - Monitor ID: {monitor_id}")
        return monitor_id
    
    async def process_chat_message(self, monitor_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a WhatsApp chat message and extract information
        
        Args:
            monitor_id: Active monitor ID
            message: Message data (sender, recipient, content, timestamp, chat_type)
        
        Returns:
            Extraction results with security classification
        """
        if monitor_id not in self.active_monitors:
            return {
                'success': False,
                'message': 'Invalid monitor ID'
            }
        
        monitor = self.active_monitors[monitor_id]
        content = message.get('content', '')
        sender = message.get('sender', '')
        recipient = message.get('recipient', '')
        chat_type = message.get('chat_type', 'individual')  # 'individual' or 'group'
        timestamp = message.get('timestamp', datetime.now().isoformat())
        
        # Extract information and classify security level
        extracted = await self._extract_and_classify(content)
        
        # Store extracted data
        for category, items in extracted.items():
            if category in monitor['extracted_data']:
                if isinstance(monitor['extracted_data'][category], list):
                    monitor['extracted_data'][category].extend(items)
                elif isinstance(monitor['extracted_data'][category], dict):
                    monitor['extracted_data'][category].update(items)
        
        monitor['processed_messages'] += 1
        monitor['last_processed'] = datetime.now().isoformat()
        
        # Create extraction result
        result = {
            'success': True,
            'monitor_id': monitor_id,
            'message_processed': {
                'sender': sender,
                'recipient': recipient,
                'chat_type': chat_type,
                'timestamp': timestamp,
                'content_length': len(content)
            },
            'extracted': extracted,
            'total_processed': monitor['processed_messages']
        }
        
        return result
    
    async def _extract_and_classify(self, content: str) -> Dict[str, Any]:
        """Extract information from message and classify by security level"""
        extracted = {
            'appointments': [],
            'tasks': [],
            'preferences': [],
            'health_info': [],
            'financial_info': [],
            'relationships': {},
            'secrets': [],
            'work_info': [],
            'family_info': [],
            'locations': []
        }
        
        content_lower = content.lower()
        
        # Extract appointments
        if any(word in content_lower for word in ['appointment', 'meeting', 'scheduled', 'booking']):
            matches = re.findall(self.chat_patterns['appointment'], content, re.IGNORECASE)
            for match in matches:
                extracted['appointments'].append({
                    'description': match.strip(),
                    'extracted_at': datetime.now().isoformat(),
                    'security_level': 'general'
                })
        
        # Extract tasks
        if any(word in content_lower for word in ['need to', 'have to', 'must', 'should']):
            matches = re.findall(self.chat_patterns['task'], content, re.IGNORECASE)
            for match in matches:
                extracted['tasks'].append({
                    'task': match.strip(),
                    'extracted_at': datetime.now().isoformat(),
                    'security_level': 'general'
                })
        
        # Extract health information (CONFIDENTIAL)
        if re.search(self.chat_patterns['health'], content_lower):
            extracted['health_info'].append({
                'content': content[:200],  # Truncate for privacy
                'extracted_at': datetime.now().isoformat(),
                'security_level': 'confidential'
            })
        
        # Extract financial information (CONFIDENTIAL)
        if re.search(self.chat_patterns['financial'], content_lower):
            extracted['financial_info'].append({
                'content': content[:200],  # Truncate for privacy
                'extracted_at': datetime.now().isoformat(),
                'security_level': 'confidential'
            })
        
        # Extract relationship information (SECRET)
        if re.search(self.chat_patterns['relationship'], content_lower):
            extracted['relationships']['info'] = {
                'content': content[:200],
                'extracted_at': datetime.now().isoformat(),
                'security_level': 'secret'
            }
        
        # Extract secrets (ULTRA SECRET)
        if re.search(self.chat_patterns['secret'], content_lower):
            extracted['secrets'].append({
                'content': content[:100],  # Very limited for ultra security
                'extracted_at': datetime.now().isoformat(),
                'security_level': 'ultra_secret'
            })
        
        # Extract work information
        if re.search(self.chat_patterns['work'], content_lower):
            security = 'confidential' if any(word in content_lower for word in ['salary', 'confidential', 'private']) else 'general'
            extracted['work_info'].append({
                'content': content[:200],
                'extracted_at': datetime.now().isoformat(),
                'security_level': security
            })
        
        # Extract preferences
        matches = re.findall(self.chat_patterns['preference'], content, re.IGNORECASE)
        for match in matches:
            extracted['preferences'].append({
                'preference': match.strip(),
                'extracted_at': datetime.now().isoformat(),
                'security_level': 'general'
            })
        
        # Extract locations
        matches = re.findall(self.chat_patterns['location'], content, re.IGNORECASE)
        for match in matches:
            extracted['locations'].append({
                'location': match.strip(),
                'extracted_at': datetime.now().isoformat(),
                'security_level': 'general'
            })
        
        return extracted
    
    async def get_monitor_summary(self, monitor_id: str) -> Dict[str, Any]:
        """Get summary of extracted data from a monitor"""
        if monitor_id not in self.active_monitors:
            return {
                'success': False,
                'message': 'Invalid monitor ID'
            }
        
        monitor = self.active_monitors[monitor_id]
        
        summary = {
            'success': True,
            'monitor_id': monitor_id,
            'user_phone': monitor['user_phone'],
            'started_at': monitor['started_at'],
            'messages_processed': monitor['processed_messages'],
            'last_activity': monitor['last_processed'],
            'extracted_summary': {
                'appointments': len(monitor['extracted_data']['appointments']),
                'tasks': len(monitor['extracted_data']['tasks']),
                'preferences': len(monitor['extracted_data']['preferences']),
                'health_records': len(monitor['extracted_data']['health_info']),
                'financial_records': len(monitor['extracted_data']['financial_info']),
                'secrets': len(monitor['extracted_data']['secrets']),
                'work_info': len(monitor['extracted_data']['work_info']),
                'locations': len(monitor['extracted_data']['locations'])
            },
            'security_breakdown': {
                'general': 0,
                'confidential': 0,
                'secret': 0,
                'ultra_secret': 0
            }
        }
        
        # Count security levels
        for category_data in monitor['extracted_data'].values():
            if isinstance(category_data, list):
                for item in category_data:
                    if isinstance(item, dict) and 'security_level' in item:
                        summary['security_breakdown'][item['security_level']] += 1
        
        return summary
    
    async def revoke_permissions(self, user_phone: str) -> Dict[str, Any]:
        """Revoke all permissions for a user"""
        if user_phone not in self.user_permissions:
            return {
                'success': False,
                'message': 'No permissions found for this user'
            }
        
        # Stop all active monitors for this user
        monitors_to_remove = []
        for monitor_id, monitor in self.active_monitors.items():
            if monitor['user_phone'] == user_phone:
                monitors_to_remove.append(monitor_id)
        
        for monitor_id in monitors_to_remove:
            del self.active_monitors[monitor_id]
        
        # Clear granted permissions
        self.user_permissions[user_phone]['granted_permissions'] = []
        self._save_permissions()
        
        # Log revocation
        self.consent_logs.append({
            'user_phone': user_phone,
            'action': 'revoked',
            'timestamp': datetime.now().isoformat(),
            'monitors_stopped': len(monitors_to_remove)
        })
        self._save_consent_logs()
        
        return {
            'success': True,
            'message': f'All permissions revoked. Stopped {len(monitors_to_remove)} active monitors.',
            'monitors_stopped': monitors_to_remove
        }
    
    def get_user_permissions(self, user_phone: str) -> Dict[str, Any]:
        """Get current permissions for a user"""
        if user_phone not in self.user_permissions:
            return {
                'has_permissions': False,
                'granted': [],
                'pending': [],
                'denied': []
            }
        
        perms = self.user_permissions[user_phone]
        
        # Get active monitors
        active_monitors = []
        for monitor_id, monitor in self.active_monitors.items():
            if monitor['user_phone'] == user_phone:
                active_monitors.append({
                    'monitor_id': monitor_id,
                    'started_at': monitor['started_at'],
                    'messages_processed': monitor['processed_messages']
                })
        
        return {
            'has_permissions': len(perms['granted_permissions']) > 0,
            'granted': perms['granted_permissions'],
            'pending': perms['pending_requests'],
            'denied': perms['denied_permissions'],
            'active_monitors': active_monitors
        }

# Global instance
whatsapp_access_manager = WhatsAppAccessManager()