# Python HMAC-SHA256 Signature Verification - Complete Guide

**Document Version**: 1.0  
**Last Updated**: December 15, 2024  
**Author**: Senior Python Developer  
**Classification**: Technical Implementation Guide  

---

## 📋 Overview

This guide provides comprehensive Python implementations for HMAC-SHA256 signature verification, specifically designed for WhatsApp webhook integration and general API security. All examples follow Python security best practices and include proper error handling.

### Requirements
```bash
pip install flask fastapi django cryptography requests pytest
```

---

## 🐍 Basic Python Implementation

### Core HMAC Verifier Class

```python
import hmac
import hashlib
import time
import secrets
import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

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
            logging.warning("HMAC secret should be at least 32 characters for security")
        
        self.secret = secret.encode('utf-8')
        self.max_payload_size = max_payload_size
        self.max_timestamp_age = max_timestamp_age
        self.algorithm = algorithm
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
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
            self.logger.error(f"Error generating signature: {e}")
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
            # Input validation
            validation_result = self._validate_inputs(payload, signature)
            if not validation_result.is_valid:
                return validation_result
            
            # Payload size check
            if len(payload.encode('utf-8')) > self.max_payload_size:
                return VerificationResponse(
                    is_valid=False,
                    result=VerificationResult.PAYLOAD_TOO_LARGE,
                    error_message=f"Payload size exceeds {self.max_payload_size} bytes"
                )
            
            # Timestamp verification (if provided)
            if timestamp:
                timestamp_result = self._verify_timestamp(timestamp)
                if not timestamp_result.is_valid:
                    return timestamp_result
            
            # Signature verification
            signature_result = self._verify_signature_internal(payload, signature)
            
            return signature_result
            
        except Exception as e:
            self.logger.error(f"Verification error: {e}")
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.ERROR,
                error_message=str(e)
            )
    
    def _validate_inputs(self, payload: str, signature: str) -> VerificationResponse:
        """Validate input parameters"""
        if not payload:
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.INVALID_FORMAT,
                error_message="Payload cannot be empty"
            )
        
        if not signature:
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.INVALID_FORMAT,
                error_message="Signature cannot be empty"
            )
        
        # Clean and validate signature format
        clean_signature = signature.replace('sha256=', '', 1)
        if not self._is_valid_hex(clean_signature, 64):
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.INVALID_FORMAT,
                error_message="Invalid signature format"
            )
        
        return VerificationResponse(is_valid=True, result=VerificationResult.VALID)
    
    def _verify_signature_internal(self, payload: str, signature: str) -> VerificationResponse:
        """Internal signature verification with constant-time comparison"""
        try:
            # Generate expected signature
            expected_signature = self.generate_signature(payload)
            
            # Clean received signature
            received_signature = signature.replace('sha256=', '', 1)
            
            # Constant-time comparison
            is_valid = hmac.compare_digest(expected_signature, received_signature)
            
            if is_valid:
                return VerificationResponse(
                    is_valid=True,
                    result=VerificationResult.VALID,
                    metadata={'algorithm': self.algorithm}
                )
            else:
                return VerificationResponse(
                    is_valid=False,
                    result=VerificationResult.INVALID_SIGNATURE,
                    error_message="Signature verification failed"
                )
                
        except Exception as e:
            self.logger.error(f"Internal verification error: {e}")
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.ERROR,
                error_message=f"Verification error: {e}"
            )
    
    def _verify_timestamp(self, timestamp: str) -> VerificationResponse:
        """Verify timestamp to prevent replay attacks"""
        try:
            # Parse timestamp
            request_time = int(timestamp)
            current_time = int(time.time())
            time_diff = abs(current_time - request_time)
            
            if time_diff > self.max_timestamp_age:
                return VerificationResponse(
                    is_valid=False,
                    result=VerificationResult.INVALID_TIMESTAMP,
                    error_message=f"Request too old: {time_diff}s > {self.max_timestamp_age}s"
                )
            
            return VerificationResponse(
                is_valid=True,
                result=VerificationResult.VALID,
                metadata={'timestamp_age': time_diff}
            )
            
        except ValueError:
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.INVALID_TIMESTAMP,
                error_message="Invalid timestamp format"
            )
    
    def _is_valid_hex(self, value: str, expected_length: int) -> bool:
        """Check if string is valid hexadecimal of expected length"""
        if len(value) != expected_length:
            return False
        
        try:
            int(value, 16)
            return True
        except ValueError:
            return False
    
    def create_test_signature(self, payload: str) -> Tuple[str, str]:
        """
        Create a test signature for development/testing
        
        Returns:
            Tuple of (payload, signature_with_prefix)
        """
        signature = self.generate_signature(payload)
        return payload, f"sha256={signature}"

# Usage Example
if __name__ == "__main__":
    # Initialize verifier
    verifier = HMACVerifier("your_secret_key_here")
    
    # Test payload
    test_payload = '{"object":"whatsapp_business_account","entry":[]}'
    
    # Generate signature for testing
    payload, signature = verifier.create_test_signature(test_payload)
    
    # Verify signature
    result = verifier.verify_signature(payload, signature)
    
    print(f"Verification result: {result.is_valid}")
    print(f"Result type: {result.result}")
    if result.error_message:
        print(f"Error: {result.error_message}")
```

---

## 🌐 Flask Implementation

### Flask Webhook Verifier

```python
from flask import Flask, request, jsonify, abort
from functools import wraps
import json
import logging
from typing import Dict, Any, Optional
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlaskWebhookVerifier:
    """Flask-specific webhook verifier with middleware support"""
    
    def __init__(
        self, 
        app_secret: str, 
        verify_token: str,
        max_payload_size: int = 1024 * 1024,
        rate_limit_per_minute: int = 60
    ):
        self.hmac_verifier = HMACVerifier(app_secret, max_payload_size)
        self.verify_token = verify_token
        self.rate_limit_per_minute = rate_limit_per_minute
        
        # Simple in-memory rate limiting (use Redis in production)
        self.rate_limit_store: Dict[str, list] = {}
    
    def verify_webhook(self, require_timestamp: bool = True):
        """
        Decorator for Flask routes to verify webhook signatures
        
        Args:
            require_timestamp: Whether to require timestamp verification
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    # Rate limiting check
                    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
                    if not self._check_rate_limit(client_ip):
                        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                        return jsonify({'error': 'Rate limit exceeded'}), 429
                    
                    # Get signature from header
                    signature = request.headers.get('X-Hub-Signature-256')
                    if not signature:
                        logger.warning("Missing signature header")
                        return jsonify({'error': 'Missing signature header'}), 401
                    
                    # Get raw payload (important: use raw data)
                    payload = request.get_data(as_text=True)
                    if not payload:
                        logger.warning("Empty payload received")
                        return jsonify({'error': 'Empty payload'}), 400
                    
                    # Get timestamp if required
                    timestamp = None
                    if require_timestamp:
                        timestamp = request.headers.get('X-Timestamp')
                    
                    # Verify signature
                    verification_result = self.hmac_verifier.verify_signature(
                        payload, signature, timestamp
                    )
                    
                    if not verification_result.is_valid:
                        logger.warning(
                            f"Webhook verification failed: {verification_result.result} - "
                            f"{verification_result.error_message}"
                        )
                        return jsonify({
                            'error': 'Webhook verification failed',
                            'reason': verification_result.result.value
                        }), 401
                    
                    # Add verification info to request
                    request.webhook_verified = True
                    request.verification_metadata = verification_result.metadata
                    
                    logger.info("Webhook verified successfully")
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Webhook verification error: {e}")
                    return jsonify({'error': 'Internal verification error'}), 500
            
            return decorated_function
        return decorator
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Simple rate limiting implementation"""
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Clean old entries
        if client_ip in self.rate_limit_store:
            self.rate_limit_store[client_ip] = [
                timestamp for timestamp in self.rate_limit_store[client_ip]
                if timestamp > minute_ago
            ]
        else:
            self.rate_limit_store[client_ip] = []
        
        # Check rate limit
        if len(self.rate_limit_store[client_ip]) >= self.rate_limit_per_minute:
            return False
        
        # Add current request
        self.rate_limit_store[client_ip].append(current_time)
        return True

# Flask Application Setup
app = Flask(__name__)

# Initialize webhook verifier
webhook_verifier = FlaskWebhookVerifier(
    app_secret="your_whatsapp_app_secret",
    verify_token="your_verify_token"
)

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Webhook verification endpoint for initial setup"""
    try:
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode == 'subscribe' and token == webhook_verifier.verify_token:
            logger.info("Webhook verification successful")
            return challenge, 200
        else:
            logger.warning(f"Webhook verification failed: mode={mode}, token={token}")
            return 'Forbidden', 403
            
    except Exception as e:
        logger.error(f"Webhook verification error: {e}")
        return 'Internal Server Error', 500

@app.route('/webhook', methods=['POST'])
@webhook_verifier.verify_webhook(require_timestamp=True)
def handle_webhook():
    """Handle verified webhook messages"""
    try:
        # Get JSON data (already verified)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Process webhook data
        result = process_whatsapp_webhook(data)
        
        logger.info(f"Webhook processed successfully: {result}")
        return jsonify({'status': 'success', 'result': result}), 200
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': 'Processing failed'}), 500

def process_whatsapp_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process WhatsApp webhook data"""
    processed_messages = []
    
    try:
        # Validate WhatsApp webhook structure
        if data.get('object') != 'whatsapp_business_account':
            raise ValueError("Invalid webhook object type")
        
        entries = data.get('entry', [])
        
        for entry in entries:
            entry_id = entry.get('id')
            changes = entry.get('changes', [])
            
            for change in changes:
                if change.get('field') == 'messages':
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    contacts = value.get('contacts', [])
                    
                    for message in messages:
                        processed_message = {
                            'message_id': message.get('id'),
                            'from': message.get('from'),
                            'timestamp': message.get('timestamp'),
                            'type': message.get('type'),
                            'content': extract_message_content(message),
                            'contact_info': get_contact_info(message.get('from'), contacts)
                        }
                        processed_messages.append(processed_message)
        
        return {
            'processed_messages': processed_messages,
            'total_messages': len(processed_messages)
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook data: {e}")
        raise

def extract_message_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """Extract content based on message type"""
    message_type = message.get('type')
    content = {}
    
    if message_type == 'text':
        content = message.get('text', {})
    elif message_type == 'image':
        content = message.get('image', {})
    elif message_type == 'audio':
        content = message.get('audio', {})
    elif message_type == 'document':
        content = message.get('document', {})
    elif message_type == 'location':
        content = message.get('location', {})
    
    return content

def get_contact_info(phone_number: str, contacts: list) -> Optional[Dict[str, Any]]:
    """Get contact information for phone number"""
    for contact in contacts:
        if contact.get('wa_id') == phone_number:
            return contact.get('profile', {})
    return None

# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

---

## ⚡ FastAPI Implementation

### FastAPI Async Webhook Verifier

```python
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import aioredis
from typing import Dict, Any, Optional
import json
import logging
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Pydantic models
class WebhookVerificationQuery(BaseModel):
    hub_mode: str = None
    hub_verify_token: str = None
    hub_challenge: str = None

class WebhookData(BaseModel):
    object: str
    entry: list

class VerificationMetadata(BaseModel):
    verified: bool
    timestamp_age: Optional[int] = None
    algorithm: str = "sha256"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncWebhookVerifier:
    """Async webhook verifier with Redis rate limiting"""
    
    def __init__(
        self, 
        app_secret: str, 
        verify_token: str,
        redis_url: str = "redis://localhost:6379",
        rate_limit_per_minute: int = 60
    ):
        self.hmac_verifier = HMACVerifier(app_secret)
        self.verify_token = verify_token
        self.redis_url = redis_url
        self.rate_limit_per_minute = rate_limit_per_minute
        self.redis_client: Optional[aioredis.Redis] = None
    
    async def initialize_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory rate limiting.")
            self.redis_client = None
    
    async def check_rate_limit(self, client_ip: str) -> bool:
        """Async rate limiting with Redis"""
        if not self.redis_client:
            return True  # Skip rate limiting if Redis unavailable
        
        try:
            key = f"rate_limit:{client_ip}"
            current_count = await self.redis_client.incr(key)
            
            if current_count == 1:
                await self.redis_client.expire(key, 60)  # 1 minute expiry
            
            return current_count <= self.rate_limit_per_minute
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return True  # Allow request if rate limiting fails
    
    async def verify_webhook_async(
        self, 
        payload: str, 
        signature: str, 
        client_ip: str,
        timestamp: Optional[str] = None
    ) -> VerificationResponse:
        """Async webhook verification"""
        
        # Rate limiting
        if not await self.check_rate_limit(client_ip):
            return VerificationResponse(
                is_valid=False,
                result=VerificationResult.RATE_LIMITED,
                error_message="Rate limit exceeded"
            )
        
        # Delegate to sync verifier (HMAC operations are fast)
        return self.hmac_verifier.verify_signature(payload, signature, timestamp)

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await webhook_verifier.initialize_redis()
    yield
    # Shutdown
    if webhook_verifier.redis_client:
        await webhook_verifier.redis_client.close()

app = FastAPI(
    title="WhatsApp Webhook Verifier",
    description="Secure WhatsApp webhook verification service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize webhook verifier
webhook_verifier = AsyncWebhookVerifier(
    app_secret="your_whatsapp_app_secret",
    verify_token="your_verify_token"
)

async def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

async def verify_webhook_dependency(
    request: Request,
    client_ip: str = Depends(get_client_ip)
) -> VerificationMetadata:
    """Dependency for webhook verification"""
    
    # Get signature from header
    signature = request.headers.get("x-hub-signature-256")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature header"
        )
    
    # Get raw body
    body = await request.body()
    payload = body.decode('utf-8')
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty payload"
        )
    
    # Get timestamp
    timestamp = request.headers.get("x-timestamp")
    
    # Verify webhook
    result = await webhook_verifier.verify_webhook_async(
        payload, signature, client_ip, timestamp
    )
    
    if not result.is_valid:
        logger.warning(
            f"Webhook verification failed for {client_ip}: "
            f"{result.result} - {result.error_message}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Webhook verification failed: {result.result.value}"
        )
    
    return VerificationMetadata(
        verified=True,
        timestamp_age=result.metadata.get('timestamp_age') if result.metadata else None,
        algorithm=result.metadata.get('algorithm', 'sha256') if result.metadata else 'sha256'
    )

@app.get("/webhook")
async def verify_webhook_endpoint(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
):
    """Webhook verification endpoint for initial setup"""
    
    if (hub_mode == "subscribe" and 
        hub_verify_token == webhook_verifier.verify_token and 
        hub_challenge):
        
        logger.info("Webhook verification successful")
        return PlainTextResponse(hub_challenge)
    
    logger.warning(
        f"Webhook verification failed: mode={hub_mode}, "
        f"token_valid={hub_verify_token == webhook_verifier.verify_token}"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Webhook verification failed"
    )

@app.post("/webhook")
async def handle_webhook(
    request: Request,
    verification: VerificationMetadata = Depends(verify_webhook_dependency)
):
    """Handle verified webhook messages"""
    
    try:
        # Get JSON data
        body = await request.body()
        data = json.loads(body.decode('utf-8'))
        
        # Validate webhook structure
        webhook_data = WebhookData(**data)
        
        # Process webhook asynchronously
        result = await process_webhook_async(webhook_data.dict())
        
        logger.info(f"Webhook processed successfully: {len(result.get('processed_messages', []))} messages")
        
        return {
            "status": "success",
            "verification": verification.dict(),
            "result": result
        }
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

async def process_webhook_async(data: Dict[str, Any]) -> Dict[str, Any]:
    """Async webhook processing"""
    
    processed_messages = []
    
    try:
        entries = data.get('entry', [])
        
        # Process entries concurrently
        tasks = [process_entry_async(entry) for entry in entries]
        entry_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in entry_results:
            if isinstance(result, Exception):
                logger.error(f"Entry processing error: {result}")
                continue
            
            if result:
                processed_messages.extend(result)
        
        return {
            'processed_messages': processed_messages,
            'total_messages': len(processed_messages),
            'processing_time': time.time()
        }
        
    except Exception as e:
        logger.error(f"Async webhook processing error: {e}")
        raise

async def process_entry_async(entry: Dict[str, Any]) -> list:
    """Process individual webhook entry"""
    
    messages = []
    
    try:
        changes = entry.get('changes', [])
        
        for change in changes:
            if change.get('field') == 'messages':
                value = change.get('value', {})
                entry_messages = value.get('messages', [])
                contacts = value.get('contacts', [])
                
                for message in entry_messages:
                    # Simulate async processing (e.g., database operations)
                    await asyncio.sleep(0.01)  # Small delay to simulate async work
                    
                    processed_message = {
                        'message_id': message.get('id'),
                        'from': message.get('from'),
                        'timestamp': message.get('timestamp'),
                        'type': message.get('type'),
                        'content': extract_message_content(message),
                        'contact_info': get_contact_info(message.get('from'), contacts),
                        'processed_at': time.time()
                    }
                    messages.append(processed_message)
        
        return messages
        
    except Exception as e:
        logger.error(f"Entry processing error: {e}")
        return []

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "connected" if webhook_verifier.redis_client else "disconnected"
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "timestamp": time.time()
    }

@app.get("/metrics")
async def get_metrics():
    """Basic metrics endpoint"""
    if webhook_verifier.redis_client:
        try:
            info = await webhook_verifier.redis_client.info()
            redis_metrics = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception:
            redis_metrics = {"error": "Unable to fetch Redis metrics"}
    else:
        redis_metrics = {"status": "not_connected"}
    
    return {
        "redis": redis_metrics,
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 🧪 Comprehensive Testing

### Unit Tests with pytest

```python
import pytest
import hmac
import hashlib
import time
import json
from unittest.mock import patch, MagicMock
from your_module import HMACVerifier, VerificationResult, VerificationResponse

class TestHMACVerifier:
    """Comprehensive test suite for HMAC verifier"""
    
    @pytest.fixture
    def verifier(self):
        """Create verifier instance for testing"""
        return HMACVerifier("test_secret_key_12345678901234567890")
    
    @pytest.fixture
    def test_payload(self):
        """Standard test payload"""
        return json.dumps({
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "test_id",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [{
                            "id": "msg_123",
                            "from": "1234567890",
                            "timestamp": "1640995200",
                            "type": "text",
                            "text": {"body": "Test message"}
                        }]
                    }
                }]
            }]
        })
    
    def test_generate_signature_consistency(self, verifier, test_payload):
        """Test signature generation consistency"""
        signature1 = verifier.generate_signature(test_payload)
        signature2 = verifier.generate_signature(test_payload)
        
        assert signature1 == signature2
        assert len(signature1) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in signature1)
    
    def test_generate_signature_uniqueness(self, verifier):
        """Test that different payloads generate different signatures"""
        payload1 = '{"test": "data1"}'
        payload2 = '{"test": "data2"}'
        
        signature1 = verifier.generate_signature(payload1)
        signature2 = verifier.generate_signature(payload2)
        
        assert signature1 != signature2
    
    def test_verify_valid_signature(self, verifier, test_payload):
        """Test verification of valid signatures"""
        signature = verifier.generate_signature(test_payload)
        
        result = verifier.verify_signature(test_payload, signature)
        
        assert result.is_valid is True
        assert result.result == VerificationResult.VALID
        assert result.error_message is None
    
    def test_verify_signature_with_prefix(self, verifier, test_payload):
        """Test verification with sha256= prefix"""
        signature = verifier.generate_signature(test_payload)
        prefixed_signature = f"sha256={signature}"
        
        result = verifier.verify_signature(test_payload, prefixed_signature)
        
        assert result.is_valid is True
        assert result.result == VerificationResult.VALID
    
    def test_verify_invalid_signature(self, verifier, test_payload):
        """Test rejection of invalid signatures"""
        invalid_signature = "invalid_signature_123"
        
        result = verifier.verify_signature(test_payload, invalid_signature)
        
        assert result.is_valid is False
        assert result.result == VerificationResult.INVALID_FORMAT
    
    def test_verify_tampered_payload(self, verifier, test_payload):
        """Test rejection of tampered payloads"""
        signature = verifier.generate_signature(test_payload)
        tampered_payload = test_payload + "tampered"
        
        result = verifier.verify_signature(tampered_payload, signature)
        
        assert result.is_valid is False
        assert result.result == VerificationResult.INVALID_SIGNATURE
    
    def test_empty_inputs(self, verifier):
        """Test handling of empty inputs"""
        # Empty payload
        result = verifier.verify_signature("", "valid_signature")
        assert result.is_valid is False
        assert result.result == VerificationResult.INVALID_FORMAT
        
        # Empty signature
        result = verifier.verify_signature("valid_payload", "")
        assert result.is_valid is False
        assert result.result == VerificationResult.INVALID_FORMAT
    
    def test_malformed_signatures(self, verifier, test_payload):
        """Test handling of malformed signatures"""
        malformed_signatures = [
            "sha256=",  # Empty after prefix
            "sha256=not_hex",  # Invalid hex
            "sha256=" + "a" * 63,  # Wrong length
            "sha256=" + "g" * 64,  # Invalid hex characters
        ]
        
        for sig in malformed_signatures:
            result = verifier.verify_signature(test_payload, sig)
            assert result.is_valid is False
            assert result.result == VerificationResult.INVALID_FORMAT
    
    def test_timestamp_verification_valid(self, verifier, test_payload):
        """Test valid timestamp verification"""
        signature = verifier.generate_signature(test_payload)
        current_timestamp = str(int(time.time()))
        
        result = verifier.verify_signature(test_payload, signature, current_timestamp)
        
        assert result.is_valid is True
        assert result.result == VerificationResult.VALID
        assert result.metadata is not None
        assert 'timestamp_age' in result.metadata
    
    def test_timestamp_verification_expired(self, verifier, test_payload):
        """Test expired timestamp rejection"""
        signature = verifier.generate_signature(test_payload)
        expired_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        
        result = verifier.verify_signature(test_payload, signature, expired_timestamp)
        
        assert result.is_valid is False
        assert result.result == VerificationResult.INVALID_TIMESTAMP
    
    def test_timestamp_verification_invalid_format(self, verifier, test_payload):
        """Test invalid timestamp format"""
        signature = verifier.generate_signature(test_payload)
        invalid_timestamp = "not_a_number"
        
        result = verifier.verify_signature(test_payload, signature, invalid_timestamp)
        
        assert result.is_valid is False
        assert result.result == VerificationResult.INVALID_TIMESTAMP
    
    def test_payload_size_limit(self):
        """Test payload size limiting"""
        verifier = HMACVerifier("test_secret", max_payload_size=100)
        large_payload = "x" * 200  # Exceeds limit
        signature = verifier.generate_signature(large_payload)
        
        result = verifier.verify_signature(large_payload, signature)
        
        assert result.is_valid is False
        assert result.result == VerificationResult.PAYLOAD_TOO_LARGE
    
    def test_constant_time_comparison(self, verifier, test_payload):
        """Test that verification uses constant-time comparison"""
        signature = verifier.generate_signature(test_payload)
        
        # Create signatures that differ at different positions
        modified_signatures = []
        for i in range(0, len(signature), 8):
            modified = signature[:i] + ('a' if signature[i] != 'a' else 'b') + signature[i+1:]
            modified_signatures.append(modified)
        
        times = []
        for modified_sig in modified_signatures:
            start_time = time.perf_counter()
            verifier.verify_signature(test_payload, modified_sig)
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        # Check that timing variance is reasonable (not a perfect test, but indicative)
        avg_time = sum(times) / len(times)
        max_deviation = max(abs(t - avg_time) for t in times)
        
        # Allow for some variance but not excessive
        assert max_deviation < avg_time * 2
    
    def test_create_test_signature(self, verifier, test_payload):
        """Test test signature creation utility"""
        payload, signature = verifier.create_test_signature(test_payload)
        
        assert payload == test_payload
        assert signature.startswith("sha256=")
        
        # Verify the created signature
        result = verifier.verify_signature(payload, signature)
        assert result.is_valid is True
    
    def test_error_handling(self, verifier):
        """Test error handling in edge cases"""
        with patch('hmac.new') as mock_hmac:
            mock_hmac.side_effect = Exception("Crypto error")
            
            result = verifier.verify_signature("test", "sha256=" + "a" * 64)
            
            assert result.is_valid is False
            assert result.result == VerificationResult.ERROR
            assert "error" in result.error_message.lower()

class TestFlaskIntegration:
    """Integration tests for Flask webhook verifier"""
    
    @pytest.fixture
    def app(self):
        """Create Flask test app"""
        from your_flask_module import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def valid_payload(self):
        """Valid webhook payload"""
        return json.dumps({
            "object": "whatsapp_business_account",
            "entry": []
        })
    
    def create_signature(self, payload: str, secret: str = "your_whatsapp_app_secret") -> str:
        """Helper to create valid signatures"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def test_webhook_verification_get(self, client):
        """Test GET webhook verification"""
        response = client.get('/webhook', query_string={
            'hub.mode': 'subscribe',
            'hub.verify_token': 'your_verify_token',
            'hub.challenge': 'test_challenge'
        })
        
        assert response.status_code == 200
        assert response.data.decode() == 'test_challenge'
    
    def test_webhook_verification_get_invalid_token(self, client):
        """Test GET webhook verification with invalid token"""
        response = client.get('/webhook', query_string={
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong_token',
            'hub.challenge': 'test_challenge'
        })
        
        assert response.status_code == 403
    
    def test_webhook_post_valid(self, client, valid_payload):
        """Test POST webhook with valid signature"""
        signature = self.create_signature(valid_payload)
        
        response = client.post(
            '/webhook',
            data=valid_payload,
            headers={
                'X-Hub-Signature-256': signature,
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_webhook_post_invalid_signature(self, client, valid_payload):
        """Test POST webhook with invalid signature"""
        response = client.post(
            '/webhook',
            data=valid_payload,
            headers={
                'X-Hub-Signature-256': 'sha256=invalid_signature',
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_webhook_post_missing_signature(self, client, valid_payload):
        """Test POST webhook without signature header"""
        response = client.post(
            '/webhook',
            data=valid_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Missing signature header'
    
    def test_webhook_post_with_timestamp(self, client, valid_payload):
        """Test POST webhook with timestamp verification"""
        signature = self.create_signature(valid_payload)
        current_timestamp = str(int(time.time()))
        
        response = client.post(
            '/webhook',
            data=valid_payload,
            headers={
                'X-Hub-Signature-256': signature,
                'X-Timestamp': current_timestamp,
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 200
    
    def test_webhook_post_expired_timestamp(self, client, valid_payload):
        """Test POST webhook with expired timestamp"""
        signature = self.create_signature(valid_payload)
        expired_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        
        response = client.post(
            '/webhook',
            data=valid_payload,
            headers={
                'X-Hub-Signature-256': signature,
                'X-Timestamp': expired_timestamp,
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 401

# Performance tests
class TestPerformance:
    """Performance tests for HMAC verification"""
    
    def test_signature_generation_performance(self):
        """Test signature generation performance"""
        verifier = HMACVerifier("performance_test_secret")
        payload = json.dumps({"test": "data"}) * 100  # Larger payload
        
        start_time = time.perf_counter()
        
        for _ in range(1000):
            verifier.generate_signature(payload)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should handle 1000 generations in reasonable time
        assert total_time < 1.0  # Less than 1 second
        
        print(f"Generated 1000 signatures in {total_time:.3f}s")
        print(f"Rate: {1000/total_time:.0f} signatures/second")
    
    def test_signature_verification_performance(self):
        """Test signature verification performance"""
        verifier = HMACVerifier("performance_test_secret")
        payload = json.dumps({"test": "data"}) * 100
        signature = verifier.generate_signature(payload)
        
        start_time = time.perf_counter()
        
        for _ in range(1000):
            result = verifier.verify_signature(payload, signature)
            assert result.is_valid is True
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Should handle 1000 verifications in reasonable time
        assert total_time < 1.0  # Less than 1 second
        
        print(f"Verified 1000 signatures in {total_time:.3f}s")
        print(f"Rate: {1000/total_time:.0f} verifications/second")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 🔒 Security Best Practices

### Secure Configuration

```python
import os
import secrets
import logging
from cryptography.fernet import Fernet
from typing import Optional

class SecureConfig:
    """Secure configuration management for webhook verification"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = os.getenv('ENCRYPTION_KEY_FILE', '.encryption_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            return key
    
    def get_whatsapp_secret(self) -> str:
        """Get WhatsApp app secret securely"""
        encrypted_secret = os.getenv('WHATSAPP_APP_SECRET_ENCRYPTED')
        
        if encrypted_secret:
            try:
                return self._cipher.decrypt(encrypted_secret.encode()).decode()
            except Exception as e:
                self.logger.error(f"Failed to decrypt WhatsApp secret: {e}")
                raise
        
        # Fallback to plain text (not recommended for production)
        plain_secret = os.getenv('WHATSAPP_APP_SECRET')
        if not plain_secret:
            raise ValueError("WhatsApp app secret not configured")
        
        if len(plain_secret) < 32:
            self.logger.warning("WhatsApp secret is shorter than recommended 32 characters")
        
        return plain_secret
    
    def get_verify_token(self) -> str:
        """Get webhook verification token"""
        token = os.getenv('WHATSAPP_VERIFY_TOKEN')
        if not token:
            raise ValueError("WhatsApp verify token not configured")
        return token
    
    def generate_secure_secret(self, length: int = 64) -> str:
        """Generate cryptographically secure secret"""
        return secrets.token_urlsafe(length)
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt secret for storage"""
        return self._cipher.encrypt(secret.encode()).decode()

class SecurityAuditLogger:
    """Security-focused audit logger"""
    
    def __init__(self, log_file: str = "security_audit.log"):
        self.logger = logging.getLogger("security_audit")
        
        # Create file handler with restricted permissions
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Restrict log file permissions
        os.chmod(log_file, 0o600)
    
    def log_verification_attempt(
        self, 
        client_ip: str, 
        success: bool, 
        reason: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log webhook verification attempts"""
        self.logger.info(
            f"Verification attempt - IP: {client_ip}, "
            f"Success: {success}, Reason: {reason}, "
            f"User-Agent: {user_agent}"
        )
    
    def log_security_event(
        self, 
        event_type: str, 
        client_ip: str, 
        details: Optional[str] = None
    ):
        """Log security events"""
        self.logger.warning(
            f"Security event - Type: {event_type}, "
            f"IP: {client_ip}, Details: {details}"
        )
    
    def log_rate_limit_exceeded(self, client_ip: str, limit: int):
        """Log rate limit violations"""
        self.logger.warning(
            f"Rate limit exceeded - IP: {client_ip}, Limit: {limit}"
        )

class SecureWebhookProcessor:
    """Enhanced webhook processor with security features"""
    
    def __init__(self):
        self.config = SecureConfig()
        self.audit_logger = SecurityAuditLogger()
        self.verifier = HMACVerifier(self.config.get_whatsapp_secret())
        
        # Security settings
        self.max_payload_size = 1024 * 1024  # 1MB
        self.allowed_content_types = {'application/json'}
        self.suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'eval\(',
            r'exec\(',
        ]
    
    def process_webhook_securely(
        self, 
        payload: str, 
        signature: str, 
        client_ip: str,
        content_type: str,
        user_agent: Optional[str] = None
    ) -> dict:
        """Process webhook with comprehensive security checks"""
        
        try:
            # 1. Content type validation
            if content_type not in self.allowed_content_types:
                self.audit_logger.log_security_event(
                    "invalid_content_type", client_ip, content_type
                )
                raise ValueError(f"Invalid content type: {content_type}")
            
            # 2. Payload size check
            if len(payload.encode('utf-8')) > self.max_payload_size:
                self.audit_logger.log_security_event(
                    "payload_too_large", client_ip, str(len(payload))
                )
                raise ValueError("Payload too large")
            
            # 3. Suspicious pattern detection
            self._check_suspicious_patterns(payload, client_ip)
            
            # 4. HMAC verification
            result = self.verifier.verify_signature(payload, signature)
            
            # 5. Audit logging
            self.audit_logger.log_verification_attempt(
                client_ip, result.is_valid, 
                result.error_message, user_agent
            )
            
            if not result.is_valid:
                raise ValueError(f"Verification failed: {result.error_message}")
            
            # 6. Process verified payload
            return self._process_verified_payload(payload)
            
        except Exception as e:
            self.audit_logger.log_security_event(
                "processing_error", client_ip, str(e)
            )
            raise
    
    def _check_suspicious_patterns(self, payload: str, client_ip: str):
        """Check for suspicious patterns in payload"""
        import re
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, payload, re.IGNORECASE):
                self.audit_logger.log_security_event(
                    "suspicious_pattern", client_ip, pattern
                )
                raise ValueError(f"Suspicious pattern detected: {pattern}")
    
    def _process_verified_payload(self, payload: str) -> dict:
        """Process verified payload safely"""
        try:
            data = json.loads(payload)
            
            # Validate structure
            if not isinstance(data, dict):
                raise ValueError("Payload must be a JSON object")
            
            if data.get('object') != 'whatsapp_business_account':
                raise ValueError("Invalid webhook object type")
            
            # Process safely
            return {
                'status': 'processed',
                'message_count': self._count_messages(data),
                'processed_at': time.time()
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
    
    def _count_messages(self, data: dict) -> int:
        """Safely count messages in webhook data"""
        count = 0
        
        try:
            entries = data.get('entry', [])
            for entry in entries:
                changes = entry.get('changes', [])
                for change in changes:
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        messages = value.get('messages', [])
                        count += len(messages)
        except Exception:
            # Don't fail processing for counting errors
            pass
        
        return count

# Example usage with security features
if __name__ == "__main__":
    # Initialize secure processor
    processor = SecureWebhookProcessor()
    
    # Example webhook processing
    try:
        result = processor.process_webhook_securely(
            payload='{"object":"whatsapp_business_account","entry":[]}',
            signature='sha256=valid_signature_here',
            client_ip='192.168.1.1',
            content_type='application/json',
            user_agent='WhatsApp/1.0'
        )
        print(f"Processing result: {result}")
        
    except Exception as e:
        print(f"Processing failed: {e}")
```

---

## 📊 Performance Monitoring

### Performance Metrics Collection

```python
import time
import statistics
from collections import defaultdict, deque
from typing import Dict, List
import threading
from dataclasses import dataclass, field

@dataclass
class PerformanceMetrics:
    """Performance metrics for HMAC operations"""
    total_verifications: int = 0
    successful_verifications: int = 0
    failed_verifications: int = 0
    average_verification_time: float = 0.0
    min_verification_time: float = float('inf')
    max_verification_time: float = 0.0
    verification_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_verification_time(self, duration: float, success: bool):
        """Add verification timing data"""
        self.total_verifications += 1
        if success:
            self.successful_verifications += 1
        else:
            self.failed_verifications += 1
        
        self.verification_times.append(duration)
        self.min_verification_time = min(self.min_verification_time, duration)
        self.max_verification_time = max(self.max_verification_time, duration)
        
        if self.verification_times:
            self.average_verification_time = statistics.mean(self.verification_times)
    
    def get_percentiles(self) -> Dict[str, float]:
        """Get performance percentiles"""
        if not self.verification_times:
            return {}
        
        times = sorted(self.verification_times)
        return {
            'p50': statistics.median(times),
            'p95': times[int(0.95 * len(times))],
            'p99': times[int(0.99 * len(times))]
        }

class PerformanceMonitor:
    """Monitor HMAC verification performance"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.lock = threading.Lock()
    
    def time_verification(self, func, *args, **kwargs):
        """Decorator to time verification operations"""
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            success = getattr(result, 'is_valid', True)
        except Exception:
            success = False
            raise
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            with self.lock:
                self.metrics.add_verification_time(duration, success)
        
        return result
    
    def get_performance_report(self) -> Dict:
        """Get comprehensive performance report"""
        with self.lock:
            percentiles = self.metrics.get_percentiles()
            
            return {
                'total_verifications': self.metrics.total_verifications,
                'success_rate': (
                    self.metrics.successful_verifications / 
                    max(self.metrics.total_verifications, 1)
                ) * 100,
                'average_time_ms': self.metrics.average_verification_time * 1000,
                'min_time_ms': self.metrics.min_verification_time * 1000,
                'max_time_ms': self.metrics.max_verification_time * 1000,
                'percentiles_ms': {
                    k: v * 1000 for k, v in percentiles.items()
                },
                'throughput_per_second': (
                    self.metrics.total_verifications / 
                    max(self.metrics.average_verification_time * self.metrics.total_verifications, 0.001)
                )
            }

# Example usage with performance monitoring
class MonitoredHMACVerifier(HMACVerifier):
    """HMAC verifier with built-in performance monitoring"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.performance_monitor = PerformanceMonitor()
    
    def verify_signature(self, *args, **kwargs):
        """Verify signature with performance monitoring"""
        return self.performance_monitor.time_verification(
            super().verify_signature, *args, **kwargs
        )
    
    def get_performance_stats(self):
        """Get performance statistics"""
        return self.performance_monitor.get_performance_report()

# Benchmark script
def run_performance_benchmark():
    """Run comprehensive performance benchmark"""
    verifier = MonitoredHMACVerifier("benchmark_secret_key_12345678901234567890")
    
    # Test payloads of different sizes
    test_payloads = [
        '{"small": "payload"}',
        '{"medium": "' + 'x' * 1000 + '"}',
        '{"large": "' + 'x' * 10000 + '"}'
    ]
    
    print("Running HMAC verification benchmark...")
    
    for payload_type, payload in zip(['small', 'medium', 'large'], test_payloads):
        print(f"\nTesting {payload_type} payload ({len(payload)} bytes):")
        
        # Generate signature
        signature = verifier.generate_signature(payload)
        
        # Run benchmark
        iterations = 1000
        start_time = time.perf_counter()
        
        for _ in range(iterations):
            result = verifier.verify_signature(payload, signature)
            assert result.is_valid
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        print(f"  Iterations: {iterations}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average time: {(total_time/iterations)*1000:.3f}ms")
        print(f"  Throughput: {iterations/total_time:.0f} verifications/second")
    
    # Print overall performance stats
    print("\nOverall Performance Statistics:")
    stats = verifier.get_performance_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value:.3f}")
        else:
            print(f"  {key}: {value:.3f}")

if __name__ == "__main__":
    run_performance_benchmark()
```

---

**This comprehensive Python guide provides production-ready HMAC-SHA256 signature verification implementations with Flask/FastAPI integration, comprehensive testing, security best practices, and performance monitoring for WhatsApp webhook verification.**

