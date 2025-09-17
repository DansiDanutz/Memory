"""
Dashboard Authentication and Security Module
Provides JWT authentication, CSRF protection, and rate limiting for the gamification dashboard
"""

import os
import jwt
import secrets
import hashlib
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict

from fastapi import Request, HTTPException, Depends, Cookie, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database_models import SessionLocal, User

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv('JWT_SECRET', secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
CSRF_SECRET = os.getenv('CSRF_SECRET', secrets.token_urlsafe(32))

# Rate limiting storage
login_attempts = defaultdict(list)
api_requests = defaultdict(list)

class LoginRequest(BaseModel):
    """Login request model"""
    phone: str
    password: str
    csrf_token: Optional[str] = None

class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: Optional[str] = None

class DashboardAuth:
    """Main authentication handler for the dashboard"""
    
    def __init__(self):
        """Initialize authentication handler"""
        self.jwt_secret = JWT_SECRET
        self.jwt_algorithm = JWT_ALGORITHM
        self.csrf_secret = CSRF_SECRET
        self.bearer_scheme = HTTPBearer(auto_error=False)
        
        # Create admin user if doesn't exist (for demo purposes)
        self._ensure_admin_user()
        
        logger.info("✅ Dashboard authentication initialized")
    
    def _ensure_admin_user(self):
        """Ensure admin user exists in the database"""
        db = SessionLocal()
        try:
            admin_phone = os.getenv('ADMIN_PHONE', '+1234567890')
            admin = db.query(User).filter(User.id == admin_phone).first()
            
            if not admin:
                admin = User(
                    id=admin_phone,
                    display_name="System Admin",
                    is_premium=True,
                    is_beta_tester=True,
                    total_contact_slots=100,
                    level=99,
                    points=99999,
                    trust_score=1.0
                )
                db.add(admin)
                db.commit()
                logger.info(f"Created admin user: {admin_phone}")
                
        except Exception as e:
            logger.error(f"Error ensuring admin user: {e}")
            db.rollback()
        finally:
            db.close()
    
    # ============================================
    # JWT Token Management
    # ============================================
    
    def create_access_token(
        self, 
        user_id: str, 
        role: str = "user",
        additional_claims: Optional[Dict] = None
    ) -> str:
        """
        Create JWT access token
        
        Args:
            user_id: User's phone number/ID
            role: User role (user/admin)
            additional_claims: Additional JWT claims
            
        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        payload = {
            "sub": user_id,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16),  # JWT ID for revocation tracking
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify JWT token and return payload
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    # ============================================
    # CSRF Protection
    # ============================================
    
    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token for a session"""
        timestamp = str(int(time.time()))
        data = f"{session_id}:{timestamp}"
        signature = hashlib.sha256(
            f"{data}:{self.csrf_secret}".encode()
        ).hexdigest()
        return f"{data}:{signature}"
    
    def validate_csrf_token(
        self, 
        token: str, 
        session_id: str, 
        max_age: int = 3600
    ) -> bool:
        """
        Validate CSRF token
        
        Args:
            token: CSRF token to validate
            session_id: Session ID to validate against
            max_age: Maximum token age in seconds
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return False
            
            token_session, timestamp, signature = parts
            
            # Check session match
            if token_session != session_id:
                return False
            
            # Check age
            token_age = int(time.time()) - int(timestamp)
            if token_age > max_age:
                return False
            
            # Check signature
            expected_data = f"{token_session}:{timestamp}"
            expected_signature = hashlib.sha256(
                f"{expected_data}:{self.csrf_secret}".encode()
            ).hexdigest()
            
            return secrets.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"CSRF validation error: {e}")
            return False
    
    # ============================================
    # Rate Limiting
    # ============================================
    
    def check_login_rate_limit(self, identifier: str) -> bool:
        """
        Check if login attempt is rate limited
        
        Args:
            identifier: Phone number or IP address
            
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        window = 60  # 1 minute window
        max_attempts = 5
        
        # Clean old attempts
        cutoff = now - window
        login_attempts[identifier] = [
            t for t in login_attempts[identifier] if t > cutoff
        ]
        
        # Check limit
        if len(login_attempts[identifier]) >= max_attempts:
            logger.warning(f"Login rate limit exceeded for {identifier}")
            return False
        
        # Add current attempt
        login_attempts[identifier].append(now)
        return True
    
    def check_api_rate_limit(self, user_id: str) -> bool:
        """
        Check if API request is rate limited
        
        Args:
            user_id: User identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        window = 60  # 1 minute window
        max_requests = 100
        
        # Clean old requests
        cutoff = now - window
        api_requests[user_id] = [
            t for t in api_requests[user_id] if t > cutoff
        ]
        
        # Check limit
        if len(api_requests[user_id]) >= max_requests:
            logger.warning(f"API rate limit exceeded for {user_id}")
            return False
        
        # Add current request
        api_requests[user_id].append(now)
        return True
    
    # ============================================
    # Authentication Methods
    # ============================================
    
    def authenticate_user(self, phone: str, password: str) -> Optional[User]:
        """
        Authenticate user with phone and password
        
        Args:
            phone: User's phone number
            password: User's password
            
        Returns:
            User object if authenticated, None otherwise
        """
        # For demo purposes, use simple authentication
        # In production, use proper password hashing (bcrypt)
        
        # Admin authentication
        admin_phone = os.getenv('ADMIN_PHONE', '+1234567890')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        if phone == admin_phone and password == admin_password:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == phone).first()
                return user
            finally:
                db.close()
        
        # Regular user authentication (simplified for demo)
        # In production, implement proper password verification
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == phone).first()
            if user:
                # For demo: password is last 4 digits of phone number
                expected_password = phone[-4:]
                if password == expected_password:
                    return user
                    
        finally:
            db.close()
        
        return None
    
    async def login(self, request: LoginRequest) -> TokenResponse:
        """
        Process login request
        
        Args:
            request: Login request with credentials
            
        Returns:
            Token response with JWT and CSRF tokens
            
        Raises:
            HTTPException on authentication failure
        """
        # Check rate limiting
        if not self.check_login_rate_limit(request.phone):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later."
            )
        
        # Authenticate user
        user = self.authenticate_user(request.phone, request.password)
        if not user:
            logger.warning(f"Failed login attempt for {request.phone}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid phone number or password"
            )
        
        # Determine role
        admin_phone = os.getenv('ADMIN_PHONE', '+1234567890')
        role = "admin" if user.id == admin_phone else "user"
        
        # Create access token
        access_token = self.create_access_token(
            user_id=user.id,
            role=role,
            additional_claims={
                "display_name": user.display_name,
                "level": user.level,
                "is_premium": user.is_premium
            }
        )
        
        # Generate CSRF token
        csrf_token = self.generate_csrf_token(user.id)
        
        logger.info(f"Successful login for {user.id} with role {role}")
        
        return TokenResponse(
            access_token=access_token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            csrf_token=csrf_token
        )
    
    # ============================================
    # FastAPI Dependencies
    # ============================================
    
    async def get_current_user(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None
    ) -> Dict:
        """
        Get current authenticated user from request
        
        Args:
            request: FastAPI request
            credentials: Bearer token credentials
            
        Returns:
            User information dict
            
        Raises:
            HTTPException if not authenticated
        """
        token = None
        
        # Try to get token from Authorization header
        if credentials and credentials.credentials:
            token = credentials.credentials
        
        # Try to get token from cookie
        if not token:
            token = request.cookies.get("access_token")
        
        # Try to get token from query parameter (for SSE)
        if not token:
            token = request.query_params.get("token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Verify token
        payload = self.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Check API rate limiting
        user_id = payload.get("sub")
        if not self.check_api_rate_limit(user_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API rate limit exceeded"
            )
        
        return {
            "user_id": user_id,
            "role": payload.get("role", "user"),
            "display_name": payload.get("display_name"),
            "level": payload.get("level"),
            "is_premium": payload.get("is_premium")
        }
    
    async def require_admin(
        self,
        current_user: Dict = None
    ) -> Dict:
        """
        Require admin role for access
        
        Args:
            current_user: Current user dict
            
        Returns:
            User dict if admin
            
        Raises:
            HTTPException if not admin
        """
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        if current_user.get("role") != "admin":
            logger.warning(
                f"Non-admin user {current_user.get('user_id')} "
                f"attempted admin access"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return current_user
    
    def verify_csrf_for_request(
        self,
        request: Request,
        user_id: str,
        csrf_token: Optional[str] = None
    ) -> bool:
        """
        Verify CSRF token for state-changing operations
        
        Args:
            request: FastAPI request
            user_id: Current user ID
            csrf_token: CSRF token from request
            
        Returns:
            True if valid
            
        Raises:
            HTTPException if CSRF validation fails
        """
        # Skip CSRF for GET requests
        if request.method == "GET":
            return True
        
        # Get token from header or form
        if not csrf_token:
            csrf_token = request.headers.get("X-CSRF-Token")
        
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token required for this operation"
            )
        
        if not self.validate_csrf_token(csrf_token, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )
        
        return True

# Create global authentication instance
dashboard_auth = DashboardAuth()

# ============================================
# Dependency Injection Functions
# ============================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        dashboard_auth.bearer_scheme
    )
) -> Dict:
    """FastAPI dependency to get current user"""
    return await dashboard_auth.get_current_user(request, credentials)

async def require_admin(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """FastAPI dependency to require admin role"""
    return await dashboard_auth.require_admin(current_user)

def require_csrf(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    csrf_token: Optional[str] = Form(None)
) -> bool:
    """FastAPI dependency to verify CSRF token"""
    return dashboard_auth.verify_csrf_for_request(
        request,
        current_user["user_id"],
        csrf_token
    )