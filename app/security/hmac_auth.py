"""
HMAC-SHA256 Authentication Module for MemoApp
Enterprise-grade security implementation based on MEMORY_APP_COMPLETE_PACKAGE
"""
import hmac
import hashlib
import time
import secrets
import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer

logger = logging.getLogger(__name__)

class VerificationResult(Enum):
    """Enumeration for verification results"""
    VALID = "valid"
    INVALID_SIGNATURE = "invalid_signature"
    INVALID_TIMESTAMP = "invalid_timestamp"
    INVALID_FORMAT = "invalid_format"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"

@dataclass
class VerificationResponse:
    """Response object for verification results"""
    is_valid: bool
    result: VerificationResult
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class HMACVerifier:
    """
    Secure HMAC-SHA256 signature verifier with comprehensive security features
    Based on enterprise package implementation
    """
    
    def __init__(
        self,
        secret: str,
        max_payload_size: int = 1024 * 1024,  # 1MB default
        max_timestamp_age: int = 300,  # 5 minutes default
        algorithm: str = 'sha256'
    ):
        """
        Initialize HMAC verifier
        
        Args:
            secret: The secret key for HMAC generation
            max_payload_size: Maximum allowed payload size in bytes
            max_timestamp_age: Maximum age of timestamp in seconds
            algorithm: Hash algorithm to use (default: sha256)
        """
        if not secret:
            raise ValueError("HMAC secret cannot be empty")
        
        if len(secret) < 32:
            logger.warning("HMAC secret should be at least 32 characters for security")
        
        self.secret = secret.encode('utf-8')
        self.max_payload_size = max_payload_size
        self.max_timestamp_age = max_timestamp_age
        self.algorithm = algorithm
        
    def generate_signature(self, payload: str) -> str:
        """
        Generate HMAC-SHA256 signature for a payload
        
        Args:
            payload: The message payload to sign
            
        Returns:
            The HMAC signature as hex string
        """
        try:
            return hmac.new(
                self.secret,
                payload.encode('utf-8'),
                getattr(hashlib, self.algorithm)
            ).hexdigest()
        except Exception as e:
            logger.error(f"Error generating signature: {e}")
            raise
    
    def verify_signature(
        self,
        payload: str,
        signature: str,
        timestamp: Optional[str] = None
    ) -> VerificationResponse:
        """
        Verify HMAC-SHA256 signature with comprehensive validation
        
        Args:
            payload: The original message payload
            signature: The signature to verify (with or without prefix)
            timestamp: Optional timestamp for replay attack prevention
            
        Returns:
            VerificationResponse object with detailed results
        """
        try:
            # Check payload size
            if len(payload.encode('utf-8')) > self.max_payload_size:
                return VerificationResponse(
                    is_valid=False,
                    result=VerificationResult.PAYLOAD_TOO_LARGE,
                    error_message=f"Payload exceeds maximum size of {self.max_payload_size} bytes"
                )
            
            # Remove any signature prefix (e.g., 'sha256=')
            if '=' in signature:
                signature = signature.split('=', 1)[1]
            
            # Generate expected signature
            expected_signature = self.generate_signature(payload)
            
            # Constant-time comparison to prevent timing attacks
            is_signature_valid = hmac.compare_digest(
                expected_signature.encode('utf-8'),
                signature.encode('utf-8')
            )
            
            if not is_signature_valid:
                return VerificationResponse(
                    is_valid=False,
                    result=VerificationResult.INVALID_SIGNATURE,
                    error_message="Signature verification failed"
                )
            
            # Verify timestamp if provided
            if timestamp:
                try:
                    timestamp_int = int(timestamp)
                    current_time = int(time.time())
                    age = current_time - timestamp_int
                    
                    if age > self.max_timestamp_age:
                        return VerificationResponse(
                            is_valid=False,
                            result=VerificationResult.INVALID_TIMESTAMP,
                            error_message=f"Request timestamp is too old (age: {age}s, max: {self.max_timestamp_age}s)"
                        )
                    
                    if age < -30:  # Allow 30 seconds clock skew for future timestamps
                        return VerificationResponse(
                            is_valid=False,
                            result=VerificationResult.INVALID_TIMESTAMP,
                            error_message="Request timestamp is in the future"
                        )
                        
                except (ValueError, TypeError):
                    return VerificationResponse(
                        is_valid=False,
                        result=VerificationResult.INVALID_FORMAT,
                        error_message="Invalid timestamp format"
                    )
            
            return VerificationResponse(
                is_valid=True,
                result=VerificationResult.VALID,
                metadata={
                    "timestamp": timestamp,
                    "algorithm": self.algorithm
                }
            )
            
        except Exception as e:
            logger.error(f"Error during signature verification: {e}")
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.ERROR,
                error_message=str(e)
            )
    
    def verify_whatsapp_signature(
        self,
        payload: str,
        signature: str
    ) -> VerificationResponse:
        """
        Verify WhatsApp webhook signature (uses sha256= prefix)
        
        Args:
            payload: The webhook payload
            signature: The X-Hub-Signature-256 header value
            
        Returns:
            VerificationResponse object
        """
        # WhatsApp signatures have 'sha256=' prefix
        if not signature.startswith('sha256='):
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.INVALID_FORMAT,
                error_message="WhatsApp signature must start with 'sha256='"
            )
        
        return self.verify_signature(payload, signature)
    
    def generate_api_signature(
        self,
        method: str,
        path: str,
        body: str,
        timestamp: int
    ) -> str:
        """
        Generate API signature for outbound requests
        
        Args:
            method: HTTP method
            path: Request path
            body: Request body
            timestamp: Unix timestamp
            
        Returns:
            HMAC signature
        """
        # Create canonical request string
        canonical_request = f"{method.upper()}\n{path}\n{body}\n{timestamp}"
        return self.generate_signature(canonical_request)


class HMACAuthMiddleware:
    """
    FastAPI middleware for HMAC authentication
    """
    
    def __init__(self, secret: str, excluded_paths: Optional[list] = None):
        """
        Initialize HMAC authentication middleware
        
        Args:
            secret: HMAC secret key
            excluded_paths: List of paths to exclude from HMAC verification
        """
        self.verifier = HMACVerifier(secret)
        self.excluded_paths = excluded_paths or ['/health', '/metrics', '/docs', '/openapi.json']
        
    async def verify_request(self, request: Request) -> bool:
        """
        Verify HMAC signature for incoming request
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if verification successful
            
        Raises:
            HTTPException if verification fails
        """
        # Skip verification for excluded paths
        if request.url.path in self.excluded_paths:
            return True
        
        # Get signature and timestamp from headers
        signature = request.headers.get('X-Memo-Signature')
        timestamp = request.headers.get('X-Memo-Timestamp')
        
        if not signature:
            # Check for WhatsApp signature
            signature = request.headers.get('X-Hub-Signature-256')
            if signature:
                # Use raw body for WhatsApp webhook verification
                body = await request.body()
                result = self.verifier.verify_whatsapp_signature(
                    body.decode('utf-8'),
                    signature
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Missing HMAC signature in headers"
                )
        else:
            # Regular API signature verification
            if not timestamp:
                raise HTTPException(
                    status_code=401,
                    detail="Missing timestamp in headers"
                )
            
            # Get request body
            body = await request.body()
            
            # Create canonical request
            method = request.method
            path = request.url.path
            canonical_request = f"{method}\n{path}\n{body.decode('utf-8')}\n{timestamp}"
            
            result = self.verifier.verify_signature(
                canonical_request,
                signature,
                timestamp
            )
        
        if not result.is_valid:
            logger.warning(f"HMAC verification failed: {result.error_message}")
            raise HTTPException(
                status_code=401,
                detail=f"HMAC verification failed: {result.error_message}"
            )
        
        return True


class HMACBearer(HTTPBearer):
    """
    FastAPI security dependency for HMAC authentication
    """
    
    def __init__(self, secret: str, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.verifier = HMACVerifier(secret)
        
    async def __call__(self, request: Request) -> Optional[str]:
        """
        Verify HMAC authentication
        """
        middleware = HMACAuthMiddleware(self.verifier.secret.decode('utf-8'))
        await middleware.verify_request(request)
        return "authenticated"


def create_hmac_headers(
    secret: str,
    method: str,
    path: str,
    body: str = ""
) -> Dict[str, str]:
    """
    Create HMAC headers for outbound requests
    
    Args:
        secret: HMAC secret key
        method: HTTP method
        path: Request path
        body: Request body
        
    Returns:
        Dictionary of headers to include in request
    """
    timestamp = int(time.time())
    verifier = HMACVerifier(secret)
    signature = verifier.generate_api_signature(method, path, body, timestamp)
    
    return {
        'X-Memo-Signature': signature,
        'X-Memo-Timestamp': str(timestamp),
        'Content-Type': 'application/json'
    }