#!/usr/bin/env python3
"""
Communication Configuration for Digital Immortality Platform
Handles all external communication service configurations
"""

import os
from typing import Dict, Any

class CommunicationConfig:
    """Central configuration for all communication channels"""
    
    def __init__(self):
        # Twilio Configuration
        self.twilio = {
            'account_sid': os.environ.get('TWILIO_ACCOUNT_SID', 'ACtest_account_sid_demo'),
            'auth_token': os.environ.get('TWILIO_AUTH_TOKEN', 'test_auth_token_demo'),
            'phone_number': os.environ.get('TWILIO_PHONE_NUMBER', '+15555551234'),
            'webhook_base_url': os.environ.get('WEBHOOK_BASE_URL', 'http://localhost:8080'),
            'demo_mode': os.environ.get('TWILIO_DEMO_MODE', 'true').lower() == 'true'
        }
        
        # WhatsApp Business API Configuration
        self.whatsapp = {
            'access_token': os.environ.get('WHATSAPP_BUSINESS_API_TOKEN', 'demo_whatsapp_token'),
            'phone_number_id': os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '590281814163767'),
            'business_id': os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', 'demo_business_id'),
            'verify_token': os.environ.get('WHATSAPP_VERIFY_TOKEN', 'MemoryApp2025'),
            'webhook_secret': os.environ.get('WHATSAPP_WEBHOOK_SECRET', 'demo_webhook_secret'),
            'api_url': 'https://graph.facebook.com/v18.0',
            'demo_mode': not bool(os.environ.get('WHATSAPP_BUSINESS_API_TOKEN'))
        }
        
        # Telegram Bot Configuration
        self.telegram = {
            'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', '6000000000:AADemo_Bot_Token_For_Testing'),
            'bot_username': os.environ.get('TELEGRAM_BOT_USERNAME', 'MemoryAppBot'),
            'webhook_url': os.environ.get('TELEGRAM_WEBHOOK_URL', 'http://localhost:8080/webhook/telegram'),
            'api_url': 'https://api.telegram.org',
            'demo_mode': not bool(os.environ.get('TELEGRAM_BOT_TOKEN'))
        }
        
        # General Webhook Configuration
        self.webhook = {
            'secret': os.environ.get('WEBHOOK_SECRET', 'secret-webhook-key'),
            'jwt_secret': os.environ.get('JWT_SECRET', 'jwt-secret-key'),
            'base_url': os.environ.get('WEBHOOK_BASE_URL', 'http://localhost:8080'),
            'allowed_origins': ['*'],  # Configure for production
            'rate_limit': {
                'calls_per_minute': 60,
                'calls_per_hour': 1000
            }
        }
        
        # Service Health Check URLs
        self.health_checks = {
            'twilio': 'https://status.twilio.com/api/v2/status.json',
            'whatsapp': 'https://graph.facebook.com/v18.0/debug_token',
            'telegram': 'https://api.telegram.org/bot{token}/getMe'
        }
        
        # Feature Flags
        self.features = {
            'twilio_voice': True,
            'twilio_sms': True,
            'whatsapp_messaging': True,
            'whatsapp_voice': True,
            'telegram_bot': True,
            'websocket_realtime': True,
            'demo_fallback': True  # Always enable demo fallback
        }
    
    def is_demo_mode(self) -> bool:
        """Check if any service is in demo mode"""
        return (self.twilio['demo_mode'] or 
                self.whatsapp['demo_mode'] or 
                self.telegram['demo_mode'])
    
    def get_active_services(self) -> Dict[str, bool]:
        """Get status of all communication services"""
        return {
            'twilio': not self.twilio['demo_mode'],
            'whatsapp': not self.whatsapp['demo_mode'],
            'telegram': not self.telegram['demo_mode'],
            'demo_mode': self.is_demo_mode()
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration and return status"""
        status = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'services': self.get_active_services()
        }
        
        # Check Twilio
        if self.features['twilio_voice'] or self.features['twilio_sms']:
            if self.twilio['demo_mode']:
                status['warnings'].append('Twilio running in DEMO mode')
            elif not self.twilio['account_sid'].startswith('AC'):
                status['errors'].append('Invalid Twilio Account SID format')
                status['valid'] = False
        
        # Check WhatsApp
        if self.features['whatsapp_messaging']:
            if self.whatsapp['demo_mode']:
                status['warnings'].append('WhatsApp running in DEMO mode')
        
        # Check Telegram
        if self.features['telegram_bot']:
            if self.telegram['demo_mode']:
                status['warnings'].append('Telegram running in DEMO mode')
            elif ':' not in self.telegram['bot_token']:
                status['errors'].append('Invalid Telegram bot token format')
                status['valid'] = False
        
        return status

# Global configuration instance
communication_config = CommunicationConfig()