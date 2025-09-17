#!/usr/bin/env python3
"""
Confidential Manager - Advanced Security and Privacy Management System
Handles encryption, access control, and authentication for sensitive memories
"""

import os
import json
import asyncio
import logging
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hmac
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import bcrypt
import pyotp
import qrcode
from io import BytesIO

from md_file_manager import MemoryTag

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security levels for memory access"""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"

class AuthMethod(Enum):
    """Authentication methods"""
    PASSWORD = "password"
    PIN = "pin"
    VOICE_PRINT = "voice_print"
    BIOMETRIC = "biometric"
    TOTP = "totp"
    PHRASE = "phrase"

class AccessLevel(Enum):
    """Access levels for different memory types"""
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    ULTRA_SECRET = "ultra_secret"

@dataclass
class SecurityProfile:
    """User security profile"""
    user_phone: str
    security_level: SecurityLevel
    enabled_auth_methods: List[AuthMethod]
    master_key_hash: str
    salt: str
    totp_secret: Optional[str] = None
    voice_print_hash: Optional[str] = None
    biometric_hash: Optional[str] = None
    security_phrases: List[str] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_access: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.security_phrases is None:
            self.security_phrases = []
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class AccessAttempt:
    """Record of access attempt"""
    user_phone: str
    timestamp: datetime
    method: AuthMethod
    success: bool
    access_level: AccessLevel
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    failure_reason: Optional[str] = None

class ConfidentialManager:
    """Advanced Security and Confidential Management System"""
    
    def __init__(self, base_dir: str = "memory-system/security"):
        """Initialize the confidential manager"""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Security directories
        self.profiles_dir = self.base_dir / "profiles"
        self.keys_dir = self.base_dir / "keys"
        self.logs_dir = self.base_dir / "logs"
        self.encrypted_dir = self.base_dir / "encrypted"
        
        for directory in [self.profiles_dir, self.keys_dir, self.logs_dir, self.encrypted_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Security configuration
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.session_timeout = timedelta(hours=2)
        
        # Active sessions
        self.active_sessions = {}
        
        # Security profiles cache
        self.security_profiles = {}
        self.load_security_profiles()
        
        # Access logs
        self.access_logs = []
        
        logger.info("🔐 Confidential Manager initialized")
    
    def load_security_profiles(self):
        """Load security profiles from disk"""
        try:
            for profile_file in self.profiles_dir.glob("*.json"):
                with open(profile_file, 'r') as f:
                    profile_data = json.load(f)
                    
                    # Convert to SecurityProfile object
                    profile = SecurityProfile(
                        user_phone=profile_data['user_phone'],
                        security_level=SecurityLevel(profile_data['security_level']),
                        enabled_auth_methods=[AuthMethod(method) for method in profile_data['enabled_auth_methods']],
                        master_key_hash=profile_data['master_key_hash'],
                        salt=profile_data['salt'],
                        totp_secret=profile_data.get('totp_secret'),
                        voice_print_hash=profile_data.get('voice_print_hash'),
                        biometric_hash=profile_data.get('biometric_hash'),
                        security_phrases=profile_data.get('security_phrases', []),
                        failed_attempts=profile_data.get('failed_attempts', 0),
                        locked_until=datetime.fromisoformat(profile_data['locked_until']) if profile_data.get('locked_until') else None,
                        last_access=datetime.fromisoformat(profile_data['last_access']) if profile_data.get('last_access') else None,
                        created_at=datetime.fromisoformat(profile_data['created_at'])
                    )
                    
                    self.security_profiles[profile.user_phone] = profile
            
            logger.info(f"🔑 Loaded {len(self.security_profiles)} security profiles")
            
        except Exception as e:
            logger.error(f"Failed to load security profiles: {e}")
    
    def save_security_profile(self, profile: SecurityProfile):
        """Save security profile to disk"""
        try:
            profile_file = self.profiles_dir / f"{self._sanitize_phone(profile.user_phone)}.json"
            
            profile_data = asdict(profile)
            
            # Convert enums to strings
            profile_data['security_level'] = profile.security_level.value
            profile_data['enabled_auth_methods'] = [method.value for method in profile.enabled_auth_methods]
            
            # Convert datetime objects
            if profile.locked_until:
                profile_data['locked_until'] = profile.locked_until.isoformat()
            if profile.last_access:
                profile_data['last_access'] = profile.last_access.isoformat()
            profile_data['created_at'] = profile.created_at.isoformat()
            
            with open(profile_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save security profile: {e}")
    
    def _sanitize_phone(self, phone_number: str) -> str:
        """Sanitize phone number for filename"""
        return phone_number.replace('+', '').replace('-', '').replace(' ', '')
    
    async def create_security_profile(self, user_phone: str, master_password: str, 
                                     security_level: SecurityLevel = SecurityLevel.STANDARD,
                                     auth_methods: List[AuthMethod] = None) -> Dict[str, Any]:
        """Create a new security profile for a user"""
        try:
            if user_phone in self.security_profiles:
                return {
                    'success': False,
                    'message': 'Security profile already exists'
                }
            
            if auth_methods is None:
                auth_methods = [AuthMethod.PASSWORD]
            
            # Generate salt and hash master password
            salt = secrets.token_hex(32)
            master_key_hash = self._hash_password(master_password, salt)
            
            # Create security profile
            profile = SecurityProfile(
                user_phone=user_phone,
                security_level=security_level,
                enabled_auth_methods=auth_methods,
                master_key_hash=master_key_hash,
                salt=salt
            )
            
            # Generate TOTP secret if enabled
            if AuthMethod.TOTP in auth_methods:
                profile.totp_secret = pyotp.random_base32()
            
            # Save profile
            self.security_profiles[user_phone] = profile
            self.save_security_profile(profile)
            
            # Generate encryption keys
            await self._generate_user_keys(user_phone, master_password)
            
            logger.info(f"🔐 Created security profile for {user_phone}")
            
            result = {
                'success': True,
                'message': 'Security profile created successfully',
                'security_level': security_level.value,
                'auth_methods': [method.value for method in auth_methods]
            }
            
            # Add TOTP QR code if enabled
            if AuthMethod.TOTP in auth_methods:
                qr_code = self._generate_totp_qr_code(user_phone, profile.totp_secret)
                result['totp_qr_code'] = qr_code
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create security profile: {e}")
            return {
                'success': False,
                'message': f'Failed to create security profile: {str(e)}',
                'error': str(e)
            }
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using bcrypt"""
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        # Use bcrypt for password hashing
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return base64.b64encode(hashed).decode('utf-8')
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            password_bytes = password.encode('utf-8')
            hashed_bytes = base64.b64decode(hashed_password.encode('utf-8'))
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    async def _generate_user_keys(self, user_phone: str, master_password: str):
        """Generate encryption keys for user"""
        try:
            # Generate key from master password
            password_bytes = master_password.encode('utf-8')
            salt = os.urandom(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
            
            # Save key and salt
            key_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}.key"
            salt_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}.salt"
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            with open(salt_file, 'wb') as f:
                f.write(salt)
            
            # Generate RSA key pair for advanced encryption
            if user_phone in self.security_profiles:
                profile = self.security_profiles[user_phone]
                if profile.security_level in [SecurityLevel.ENHANCED, SecurityLevel.MAXIMUM]:
                    await self._generate_rsa_keys(user_phone)
            
        except Exception as e:
            logger.error(f"Failed to generate user keys: {e}")
    
    async def _generate_rsa_keys(self, user_phone: str):
        """Generate RSA key pair for advanced encryption"""
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Get public key
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Save keys
            private_key_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}_private.pem"
            public_key_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}_public.pem"
            
            with open(private_key_file, 'wb') as f:
                f.write(private_pem)
            
            with open(public_key_file, 'wb') as f:
                f.write(public_pem)
            
        except Exception as e:
            logger.error(f"Failed to generate RSA keys: {e}")
    
    def _generate_totp_qr_code(self, user_phone: str, secret: str) -> str:
        """Generate TOTP QR code for 2FA setup"""
        try:
            # Create TOTP URI
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user_phone,
                issuer_name="Memory Assistant"
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return qr_code_base64
            
        except Exception as e:
            logger.error(f"Failed to generate TOTP QR code: {e}")
            return ""
    
    async def authenticate_user(self, user_phone: str, auth_method: AuthMethod, 
                               credentials: Dict[str, Any], 
                               access_level: AccessLevel = AccessLevel.PRIVATE) -> Dict[str, Any]:
        """Authenticate user for memory access"""
        try:
            # Check if user exists
            if user_phone not in self.security_profiles:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            profile = self.security_profiles[user_phone]
            
            # Check if user is locked
            if profile.locked_until and datetime.now() < profile.locked_until:
                return {
                    'success': False,
                    'message': f'Account locked until {profile.locked_until.strftime("%Y-%m-%d %H:%M:%S")}'
                }
            
            # Check if auth method is enabled
            if auth_method not in profile.enabled_auth_methods:
                return {
                    'success': False,
                    'message': 'Authentication method not enabled'
                }
            
            # Perform authentication based on method
            auth_success = False
            failure_reason = None
            
            if auth_method == AuthMethod.PASSWORD:
                password = credentials.get('password', '')
                auth_success = self._verify_password(password, profile.master_key_hash)
                failure_reason = 'Invalid password' if not auth_success else None
                
            elif auth_method == AuthMethod.PIN:
                pin = credentials.get('pin', '')
                # For simplicity, using same hash as password
                auth_success = self._verify_password(pin, profile.master_key_hash)
                failure_reason = 'Invalid PIN' if not auth_success else None
                
            elif auth_method == AuthMethod.TOTP:
                totp_code = credentials.get('totp_code', '')
                if profile.totp_secret:
                    totp = pyotp.TOTP(profile.totp_secret)
                    auth_success = totp.verify(totp_code)
                    failure_reason = 'Invalid TOTP code' if not auth_success else None
                else:
                    failure_reason = 'TOTP not configured'
                    
            elif auth_method == AuthMethod.PHRASE:
                phrase = credentials.get('phrase', '').lower()
                auth_success = phrase in [p.lower() for p in profile.security_phrases]
                failure_reason = 'Invalid security phrase' if not auth_success else None
                
            elif auth_method == AuthMethod.VOICE_PRINT:
                # Placeholder for voice authentication
                voice_data = credentials.get('voice_data', '')
                auth_success = self._verify_voice_print(voice_data, profile.voice_print_hash)
                failure_reason = 'Voice authentication failed' if not auth_success else None
                
            elif auth_method == AuthMethod.BIOMETRIC:
                # Placeholder for biometric authentication
                biometric_data = credentials.get('biometric_data', '')
                auth_success = self._verify_biometric(biometric_data, profile.biometric_hash)
                failure_reason = 'Biometric authentication failed' if not auth_success else None
            
            # Log access attempt
            attempt = AccessAttempt(
                user_phone=user_phone,
                timestamp=datetime.now(),
                method=auth_method,
                success=auth_success,
                access_level=access_level,
                ip_address=credentials.get('ip_address'),
                user_agent=credentials.get('user_agent'),
                failure_reason=failure_reason
            )
            
            self.access_logs.append(attempt)
            await self._save_access_log(attempt)
            
            if auth_success:
                # Reset failed attempts
                profile.failed_attempts = 0
                profile.last_access = datetime.now()
                
                # Create session
                session_token = self._create_session(user_phone, access_level)
                
                # Save updated profile
                self.save_security_profile(profile)
                
                logger.info(f"✅ Authentication successful for {user_phone} using {auth_method.value}")
                
                return {
                    'success': True,
                    'message': 'Authentication successful',
                    'session_token': session_token,
                    'access_level': access_level.value,
                    'expires_at': (datetime.now() + self.session_timeout).isoformat()
                }
            else:
                # Handle failed attempt
                profile.failed_attempts += 1
                
                # Lock account if too many failures
                if profile.failed_attempts >= self.max_failed_attempts:
                    profile.locked_until = datetime.now() + self.lockout_duration
                    logger.warning(f"🔒 Account locked for {user_phone} due to too many failed attempts")
                
                self.save_security_profile(profile)
                
                return {
                    'success': False,
                    'message': failure_reason or 'Authentication failed',
                    'failed_attempts': profile.failed_attempts,
                    'max_attempts': self.max_failed_attempts
                }
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}',
                'error': str(e)
            }
    
    def _verify_voice_print(self, voice_data: str, stored_hash: Optional[str]) -> bool:
        """Verify voice print (placeholder implementation)"""
        # This would integrate with voice recognition service
        # For now, return True if both exist
        return bool(voice_data and stored_hash)
    
    def _verify_biometric(self, biometric_data: str, stored_hash: Optional[str]) -> bool:
        """Verify biometric data (placeholder implementation)"""
        # This would integrate with biometric service
        # For now, return True if both exist
        return bool(biometric_data and stored_hash)
    
    def _create_session(self, user_phone: str, access_level: AccessLevel) -> str:
        """Create authentication session"""
        session_token = secrets.token_urlsafe(32)
        
        session_data = {
            'user_phone': user_phone,
            'access_level': access_level,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + self.session_timeout
        }
        
        self.active_sessions[session_token] = session_data
        
        return session_token
    
    def verify_session(self, session_token: str, required_access_level: AccessLevel = AccessLevel.PRIVATE) -> Dict[str, Any]:
        """Verify session token and access level"""
        try:
            if session_token not in self.active_sessions:
                return {
                    'valid': False,
                    'message': 'Invalid session token'
                }
            
            session = self.active_sessions[session_token]
            
            # Check expiration
            if datetime.now() > session['expires_at']:
                del self.active_sessions[session_token]
                return {
                    'valid': False,
                    'message': 'Session expired'
                }
            
            # Check access level
            session_level = session['access_level']
            if not self._has_sufficient_access(session_level, required_access_level):
                return {
                    'valid': False,
                    'message': 'Insufficient access level'
                }
            
            return {
                'valid': True,
                'user_phone': session['user_phone'],
                'access_level': session_level.value,
                'expires_at': session['expires_at'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
            return {
                'valid': False,
                'message': f'Session verification error: {str(e)}'
            }
    
    def _has_sufficient_access(self, session_level: AccessLevel, required_level: AccessLevel) -> bool:
        """Check if session has sufficient access level"""
        access_hierarchy = {
            AccessLevel.PUBLIC: 0,
            AccessLevel.PRIVATE: 1,
            AccessLevel.CONFIDENTIAL: 2,
            AccessLevel.SECRET: 3,
            AccessLevel.ULTRA_SECRET: 4
        }
        
        return access_hierarchy[session_level] >= access_hierarchy[required_level]
    
    async def encrypt_memory(self, user_phone: str, content: str, 
                            memory_tag: MemoryTag) -> Dict[str, Any]:
        """Encrypt memory content based on security level"""
        try:
            if user_phone not in self.security_profiles:
                return {
                    'success': False,
                    'message': 'User security profile not found'
                }
            
            profile = self.security_profiles[user_phone]
            
            # Determine encryption method based on memory tag and security level
            if memory_tag in [MemoryTag.SECRET, MemoryTag.ULTRA_SECRET]:
                if profile.security_level == SecurityLevel.MAXIMUM:
                    # Use RSA encryption for maximum security
                    encrypted_content = await self._encrypt_with_rsa(user_phone, content)
                else:
                    # Use Fernet encryption
                    encrypted_content = await self._encrypt_with_fernet(user_phone, content)
            elif memory_tag == MemoryTag.CONFIDENTIAL:
                # Use Fernet encryption
                encrypted_content = await self._encrypt_with_fernet(user_phone, content)
            else:
                # No encryption for general memories
                encrypted_content = content
            
            return {
                'success': True,
                'encrypted_content': encrypted_content,
                'encryption_method': 'rsa' if memory_tag in [MemoryTag.SECRET, MemoryTag.ULTRA_SECRET] and profile.security_level == SecurityLevel.MAXIMUM else 'fernet' if memory_tag in [MemoryTag.CONFIDENTIAL, MemoryTag.SECRET, MemoryTag.ULTRA_SECRET] else 'none'
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt memory: {e}")
            return {
                'success': False,
                'message': f'Encryption failed: {str(e)}',
                'error': str(e)
            }
    
    async def decrypt_memory(self, user_phone: str, encrypted_content: str, 
                            encryption_method: str) -> Dict[str, Any]:
        """Decrypt memory content"""
        try:
            if encryption_method == 'none':
                return {
                    'success': True,
                    'decrypted_content': encrypted_content
                }
            
            if encryption_method == 'fernet':
                decrypted_content = await self._decrypt_with_fernet(user_phone, encrypted_content)
            elif encryption_method == 'rsa':
                decrypted_content = await self._decrypt_with_rsa(user_phone, encrypted_content)
            else:
                return {
                    'success': False,
                    'message': 'Unknown encryption method'
                }
            
            return {
                'success': True,
                'decrypted_content': decrypted_content
            }
            
        except Exception as e:
            logger.error(f"Failed to decrypt memory: {e}")
            return {
                'success': False,
                'message': f'Decryption failed: {str(e)}',
                'error': str(e)
            }
    
    async def _encrypt_with_fernet(self, user_phone: str, content: str) -> str:
        """Encrypt content using Fernet symmetric encryption"""
        try:
            key_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}.key"
            
            if not key_file.exists():
                raise Exception("Encryption key not found")
            
            with open(key_file, 'rb') as f:
                key = f.read()
            
            fernet = Fernet(key)
            encrypted_bytes = fernet.encrypt(content.encode('utf-8'))
            
            return base64.b64encode(encrypted_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Fernet encryption failed: {e}")
            raise
    
    async def _decrypt_with_fernet(self, user_phone: str, encrypted_content: str) -> str:
        """Decrypt content using Fernet symmetric encryption"""
        try:
            key_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}.key"
            
            if not key_file.exists():
                raise Exception("Encryption key not found")
            
            with open(key_file, 'rb') as f:
                key = f.read()
            
            fernet = Fernet(key)
            encrypted_bytes = base64.b64decode(encrypted_content.encode('utf-8'))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Fernet decryption failed: {e}")
            raise
    
    async def _encrypt_with_rsa(self, user_phone: str, content: str) -> str:
        """Encrypt content using RSA asymmetric encryption"""
        try:
            public_key_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}_public.pem"
            
            if not public_key_file.exists():
                raise Exception("Public key not found")
            
            with open(public_key_file, 'rb') as f:
                public_key = serialization.load_pem_public_key(f.read())
            
            # RSA can only encrypt small amounts of data, so we use hybrid encryption
            # Generate a random key for Fernet
            fernet_key = Fernet.generate_key()
            fernet = Fernet(fernet_key)
            
            # Encrypt content with Fernet
            encrypted_content = fernet.encrypt(content.encode('utf-8'))
            
            # Encrypt Fernet key with RSA
            encrypted_key = public_key.encrypt(
                fernet_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Combine encrypted key and content
            combined = base64.b64encode(encrypted_key).decode('utf-8') + '|' + base64.b64encode(encrypted_content).decode('utf-8')
            
            return combined
            
        except Exception as e:
            logger.error(f"RSA encryption failed: {e}")
            raise
    
    async def _decrypt_with_rsa(self, user_phone: str, encrypted_content: str) -> str:
        """Decrypt content using RSA asymmetric encryption"""
        try:
            private_key_file = self.keys_dir / f"{self._sanitize_phone(user_phone)}_private.pem"
            
            if not private_key_file.exists():
                raise Exception("Private key not found")
            
            with open(private_key_file, 'rb') as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            
            # Split encrypted key and content
            parts = encrypted_content.split('|')
            if len(parts) != 2:
                raise Exception("Invalid encrypted content format")
            
            encrypted_key = base64.b64decode(parts[0].encode('utf-8'))
            encrypted_data = base64.b64decode(parts[1].encode('utf-8'))
            
            # Decrypt Fernet key with RSA
            fernet_key = private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt content with Fernet
            fernet = Fernet(fernet_key)
            decrypted_bytes = fernet.decrypt(encrypted_data)
            
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"RSA decryption failed: {e}")
            raise
    
    async def _save_access_log(self, attempt: AccessAttempt):
        """Save access attempt to log file"""
        try:
            log_file = self.logs_dir / f"access_{datetime.now().strftime('%Y%m')}.json"
            
            # Load existing logs
            logs = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            
            # Add new log entry
            log_entry = asdict(attempt)
            log_entry['timestamp'] = attempt.timestamp.isoformat()
            log_entry['method'] = attempt.method.value
            log_entry['access_level'] = attempt.access_level.value
            
            logs.append(log_entry)
            
            # Keep only last 1000 entries per file
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save logs
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save access log: {e}")
    
    async def get_security_stats(self, user_phone: str) -> Dict[str, Any]:
        """Get security statistics for a user"""
        try:
            if user_phone not in self.security_profiles:
                return {
                    'success': False,
                    'message': 'User not found'
                }
            
            profile = self.security_profiles[user_phone]
            
            # Count recent access attempts
            recent_attempts = [log for log in self.access_logs 
                             if log.user_phone == user_phone and 
                             log.timestamp > datetime.now() - timedelta(days=30)]
            
            successful_attempts = [log for log in recent_attempts if log.success]
            failed_attempts = [log for log in recent_attempts if not log.success]
            
            return {
                'success': True,
                'security_level': profile.security_level.value,
                'enabled_auth_methods': [method.value for method in profile.enabled_auth_methods],
                'last_access': profile.last_access.isoformat() if profile.last_access else None,
                'failed_attempts_count': profile.failed_attempts,
                'is_locked': profile.locked_until is not None and datetime.now() < profile.locked_until,
                'locked_until': profile.locked_until.isoformat() if profile.locked_until else None,
                'recent_stats': {
                    'total_attempts': len(recent_attempts),
                    'successful_attempts': len(successful_attempts),
                    'failed_attempts': len(failed_attempts),
                    'success_rate': len(successful_attempts) / len(recent_attempts) * 100 if recent_attempts else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get security stats: {e}")
            return {
                'success': False,
                'message': f'Failed to get security stats: {str(e)}',
                'error': str(e)
            }
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now()
        expired_tokens = [token for token, session in self.active_sessions.items() 
                         if session['expires_at'] < now]
        
        for token in expired_tokens:
            del self.active_sessions[token]
        
        if expired_tokens:
            logger.info(f"🧹 Cleaned up {len(expired_tokens)} expired sessions")

# Example usage and testing
async def main():
    """Test the confidential manager"""
    manager = ConfidentialManager()
    
    # Test security profile creation
    result = await manager.create_security_profile(
        user_phone="+1234567890",
        master_password="secure_password_123",
        security_level=SecurityLevel.ENHANCED,
        auth_methods=[AuthMethod.PASSWORD, AuthMethod.TOTP]
    )
    print("Security Profile Creation:", result)
    
    # Test authentication
    result = await manager.authenticate_user(
        user_phone="+1234567890",
        auth_method=AuthMethod.PASSWORD,
        credentials={'password': 'secure_password_123'},
        access_level=AccessLevel.CONFIDENTIAL
    )
    print("Authentication:", result)
    
    # Test encryption
    result = await manager.encrypt_memory(
        user_phone="+1234567890",
        content="This is a secret memory",
        memory_tag=MemoryTag.SECRET
    )
    print("Encryption:", result)
    
    # Test security stats
    result = await manager.get_security_stats("+1234567890")
    print("Security Stats:", result)

if __name__ == "__main__":
    asyncio.run(main())

