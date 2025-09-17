#!/usr/bin/env python3
"""
Production Configuration Manager for Digital Immortality Platform
Manages all API keys, service configurations, and environment settings
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Service availability status"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"

@dataclass
class ServiceConfig:
    """Configuration for external service"""
    name: str
    api_key: Optional[str]
    endpoint: Optional[str]
    status: ServiceStatus
    fallback_service: Optional[str] = None
    
class ProductionConfig:
    """Production configuration manager with fallback mechanisms"""
    
    def __init__(self):
        self.services = {}
        self.load_configuration()
        self.validate_services()
    
    def load_configuration(self):
        """Load all service configurations from environment"""
        
        # Supabase Configuration - Fixed mapping
        # The env vars are incorrectly named, so we need to remap them
        SUPABASE_URL_ENV = os.environ.get('SUPABASE_URL', '')
        SUPABASE_ANON_ENV = os.environ.get('SUPABASE_ANON_KEY', '')
        
        # SUPABASE_URL env actually contains anon key, SUPABASE_ANON_KEY contains URL
        if SUPABASE_URL_ENV.startswith('eyJ'):
            # Env vars are swapped
            self.SUPABASE_URL = 'https://gvuuauzsucvhghmpdpxf.supabase.co'
            self.SUPABASE_ANON_KEY = SUPABASE_URL_ENV
        else:
            # Normal mapping
            self.SUPABASE_URL = SUPABASE_URL_ENV
            self.SUPABASE_ANON_KEY = SUPABASE_ANON_ENV
            
        self.SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', self.SUPABASE_ANON_KEY)
        
        # AI Services Configuration
        self.services['openai'] = ServiceConfig(
            name="OpenAI GPT-5",
            api_key=os.environ.get('OPENAI_API_KEY'),
            endpoint="https://api.openai.com/v1",
            status=ServiceStatus.NOT_CONFIGURED,
            fallback_service="anthropic"
        )
        
        self.services['anthropic'] = ServiceConfig(
            name="Anthropic Claude",
            api_key=os.environ.get('ANTHROPIC_API_KEY'),
            endpoint="https://api.anthropic.com",
            status=ServiceStatus.NOT_CONFIGURED,
            fallback_service="xai"
        )
        
        self.services['xai'] = ServiceConfig(
            name="xAI Grok",
            api_key=os.environ.get('XAI_API_KEY'),
            endpoint="https://api.x.ai/v1",
            status=ServiceStatus.NOT_CONFIGURED,
            fallback_service="openai"
        )
        
        # Communication Services
        self.services['twilio'] = ServiceConfig(
            name="Twilio",
            api_key=os.environ.get('TWILIO_AUTH_TOKEN'),
            endpoint=os.environ.get('TWILIO_ACCOUNT_SID'),
            status=ServiceStatus.NOT_CONFIGURED
        )
        
        self.services['telegram'] = ServiceConfig(
            name="Telegram Bot",
            api_key=os.environ.get('TELEGRAM_BOT_TOKEN'),
            endpoint="https://api.telegram.org",
            status=ServiceStatus.NOT_CONFIGURED
        )
        
        self.services['whatsapp'] = ServiceConfig(
            name="WhatsApp Business",
            api_key=os.environ.get('WHATSAPP_VERIFY_TOKEN'),
            endpoint=os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v18.0'),
            status=ServiceStatus.NOT_CONFIGURED
        )
        
        # Payment Service - Check multiple env vars for Stripe key
        stripe_key = os.environ.get('STRIPE_SECRET_KEY', '')
        if stripe_key.startswith('pk_'):  # This is a publishable key, not secret
            # Try other env vars or use demo mode
            stripe_key = os.environ.get('STRIPE_API_KEY', '')
            if not stripe_key or stripe_key.startswith('pk_'):
                stripe_key = None  # Will use demo mode
                
        self.services['stripe'] = ServiceConfig(
            name="Stripe",
            api_key=stripe_key,
            endpoint="https://api.stripe.com",
            status=ServiceStatus.NOT_CONFIGURED
        )
        
        # Security & Authentication
        self.JWT_SECRET = os.environ.get('JWT_SECRET', 'digital-immortality-jwt-secret-2025')
        self.WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'webhook-secret-key-2025')
        self.MEMORY_MASTER_SECRET = os.environ.get('MEMORY_MASTER_SECRET', 'memory-encryption-master-2025')
        
        # Server Configuration
        self.SERVER_HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
        self.SERVER_PORT = int(os.environ.get('SERVER_PORT', '5000'))
        self.WEBHOOK_PORT = int(os.environ.get('WEBHOOK_PORT', '8080'))
        
        # Feature Flags
        self.ENABLE_VOICE_CALLS = os.environ.get('ENABLE_VOICE_CALLS', 'true').lower() == 'true'
        self.ENABLE_WHATSAPP = os.environ.get('ENABLE_WHATSAPP', 'true').lower() == 'true'
        self.ENABLE_TELEGRAM = os.environ.get('ENABLE_TELEGRAM', 'true').lower() == 'true'
        self.ENABLE_AI_AVATARS = os.environ.get('ENABLE_AI_AVATARS', 'true').lower() == 'true'
        
        # Pricing Tiers (in cents)
        self.PRICING_TIERS = {
            'free': {
                'price': 0,
                'credits': 50,
                'features': ['basic_memories', 'text_only'],
                'limits': {'memories_per_month': 100, 'contacts': 10}
            },
            'basic': {
                'price': 999,  # $9.99
                'credits': 200,
                'features': ['basic_memories', 'voice_notes', 'commitments'],
                'limits': {'memories_per_month': 500, 'contacts': 50}
            },
            'pro': {
                'price': 1999,  # $19.99
                'credits': 500,
                'features': ['all_features', 'ai_avatars', 'secret_vaults', 'voice_calls'],
                'limits': {'memories_per_month': 2000, 'contacts': 200}
            },
            'elite': {
                'price': 3999,  # $39.99
                'credits': 1000,
                'features': ['all_features', 'priority_support', 'custom_avatars', 'inheritance'],
                'limits': {'memories_per_month': -1, 'contacts': -1}  # Unlimited
            }
        }
        
        # Rate Limiting
        self.RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '60'))
        self.RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', '1000'))
        
        # Storage Limits
        self.MAX_MEMORY_SIZE_MB = int(os.environ.get('MAX_MEMORY_SIZE_MB', '10'))
        self.MAX_ATTACHMENT_SIZE_MB = int(os.environ.get('MAX_ATTACHMENT_SIZE_MB', '25'))
        
        # Demo Mode
        self.DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'
    
    def validate_services(self):
        """Validate and update service statuses"""
        for service_id, service in self.services.items():
            if service.api_key:
                service.status = ServiceStatus.ACTIVE
                logger.info(f"✅ {service.name} configured and active")
            else:
                service.status = ServiceStatus.NOT_CONFIGURED
                logger.warning(f"⚠️ {service.name} not configured")
    
    def get_active_ai_service(self) -> Optional[str]:
        """Get the first available AI service with fallback"""
        priority_order = ['openai', 'anthropic', 'xai']
        
        for service_id in priority_order:
            if self.services[service_id].status == ServiceStatus.ACTIVE:
                return service_id
        
        logger.error("❌ No AI service available")
        return None
    
    def get_service_config(self, service_id: str) -> Optional[ServiceConfig]:
        """Get configuration for a specific service"""
        return self.services.get(service_id)
    
    def is_production_ready(self) -> bool:
        """Check if minimum required services are configured"""
        required_services = ['openai', 'stripe']  # Minimum required
        supabase_configured = bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)
        
        for service_id in required_services:
            if self.services[service_id].status != ServiceStatus.ACTIVE:
                return False
        
        return supabase_configured
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive status report"""
        report = {
            'production_ready': self.is_production_ready(),
            'database': {
                'supabase_url': self.SUPABASE_URL,
                'configured': bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)
            },
            'services': {},
            'features': {
                'voice_calls': self.ENABLE_VOICE_CALLS,
                'whatsapp': self.ENABLE_WHATSAPP,
                'telegram': self.ENABLE_TELEGRAM,
                'ai_avatars': self.ENABLE_AI_AVATARS
            }
        }
        
        for service_id, service in self.services.items():
            report['services'][service_id] = {
                'name': service.name,
                'status': service.status.value,
                'configured': service.status == ServiceStatus.ACTIVE
            }
        
        return report
    
    def export_env_template(self) -> str:
        """Export environment variable template"""
        template = """# Digital Immortality Platform - Environment Configuration
# Copy this to .env and fill in your API keys

# Database Configuration
SUPABASE_URL=https://gvuuauzsucvhghmpdpxf.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here

# AI Services
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
XAI_API_KEY=your_xai_key_here

# Communication Services
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_PHONE_NUMBER=+1234567890
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
WHATSAPP_VERIFY_TOKEN=your_whatsapp_verify_token_here
WHATSAPP_API_URL=https://graph.facebook.com/v18.0

# Payment Processing
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here

# Security
JWT_SECRET=your_jwt_secret_here
WEBHOOK_SECRET=your_webhook_secret_here
MEMORY_MASTER_SECRET=your_encryption_secret_here

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
WEBHOOK_PORT=8080

# Feature Flags
ENABLE_VOICE_CALLS=true
ENABLE_WHATSAPP=true
ENABLE_TELEGRAM=true
ENABLE_AI_AVATARS=true
DEMO_MODE=false

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Storage Limits
MAX_MEMORY_SIZE_MB=10
MAX_ATTACHMENT_SIZE_MB=25
"""
        return template

# Global configuration instance
config = ProductionConfig()

def get_config() -> ProductionConfig:
    """Get global configuration instance"""
    return config

if __name__ == "__main__":
    # Print status report when run directly
    print("🚀 Digital Immortality Platform - Configuration Status")
    print("=" * 60)
    
    status = config.get_status_report()
    print(f"Production Ready: {'✅ YES' if status['production_ready'] else '❌ NO'}")
    print(f"Database: {'✅ Configured' if status['database']['configured'] else '❌ Not Configured'}")
    print(f"Database URL: {status['database']['supabase_url']}")
    
    print("\n📊 Service Status:")
    for service_id, info in status['services'].items():
        icon = "✅" if info['configured'] else "❌"
        print(f"  {icon} {info['name']}: {info['status']}")
    
    print("\n🎮 Features:")
    for feature, enabled in status['features'].items():
        icon = "✅" if enabled else "❌"
        print(f"  {icon} {feature.replace('_', ' ').title()}")
    
    if not status['production_ready']:
        print("\n⚠️ Missing required configurations:")
        print("  1. Ensure OPENAI_API_KEY is set")
        print("  2. Ensure STRIPE_SECRET_KEY is set")
        print("  3. Ensure Supabase credentials are configured")
        print("\n📝 Create a .env file with the template below:")
        print(config.export_env_template())