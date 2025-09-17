#!/usr/bin/env python3
"""
Twilio Integration for Digital Immortality Platform
Handles voice calls, SMS, and call recordings
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Record, Gather, Say
from twilio.twiml.messaging_response import MessagingResponse
import asyncio
import json

logger = logging.getLogger(__name__)

class TwilioIntegration:
    """Complete Twilio integration for voice and SMS"""
    
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        self.phone_number = os.environ.get('TWILIO_PHONE_NUMBER', '')
        self.webhook_base_url = os.environ.get('WEBHOOK_BASE_URL', 'https://your-domain.com')
        
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize Twilio client"""
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("✅ Twilio client initialized successfully")
                # Verify account
                account = self.client.api.accounts(self.account_sid).fetch()
                logger.info(f"📞 Twilio account status: {account.status}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Twilio credentials not configured")
    
    async def handle_incoming_call(self, from_number: str, to_number: str, call_sid: str) -> VoiceResponse:
        """Handle incoming voice call with AI"""
        response = VoiceResponse()
        
        # Check if user is enrolled for voice authentication
        user_enrolled = await self.check_voice_enrollment(from_number)
        
        if user_enrolled:
            # Greet the caller
            response.say(
                "Welcome to your Digital Immortality Memory System. "
                "I'm your AI assistant. How can I help you today?",
                voice='alice',
                language='en-US'
            )
            
            # Record the conversation
            response.record(
                action=f'{self.webhook_base_url}/webhook/twilio/recording-complete',
                method='POST',
                max_length=600,  # 10 minutes max
                transcribe=True,
                transcribe_callback=f'{self.webhook_base_url}/webhook/twilio/transcription',
                play_beep=False,
                recording_status_callback=f'{self.webhook_base_url}/webhook/twilio/recording-status',
                recording_status_callback_method='POST',
                recording_status_callback_event='completed'
            )
        else:
            # Voice enrollment flow
            response.say(
                "Welcome to Memory App. To get started, I need to enroll your voice. "
                "Please say your name and a brief message after the beep.",
                voice='alice'
            )
            
            response.record(
                action=f'{self.webhook_base_url}/webhook/twilio/voice-enrollment',
                method='POST',
                max_length=30,
                transcribe=True,
                play_beep=True
            )
        
        return response
    
    async def handle_voice_command(self, command: str, caller_id: str) -> VoiceResponse:
        """Process voice commands during call"""
        response = VoiceResponse()
        command_lower = command.lower()
        
        if "memory" in command_lower and "number" in command_lower:
            # Extract memory number from command
            import re
            numbers = re.findall(r'\d+', command)
            if numbers:
                memory_num = numbers[0]
                # Retrieve and speak memory
                memory_content = await self.retrieve_memory(caller_id, memory_num)
                response.say(f"Memory {memory_num}: {memory_content}", voice='alice')
            else:
                response.say("Please specify a memory number.", voice='alice')
        
        elif "save" in command_lower or "store" in command_lower:
            response.say("Please tell me what you'd like to remember.", voice='alice')
            response.record(
                action=f'{self.webhook_base_url}/webhook/twilio/save-memory',
                method='POST',
                max_length=120,
                transcribe=True
            )
        
        elif "secret" in command_lower:
            response.say("Please speak your secret memory. It will be encrypted and stored securely.", voice='alice')
            response.record(
                action=f'{self.webhook_base_url}/webhook/twilio/save-secret',
                method='POST',
                max_length=180,
                transcribe=True
            )
        
        else:
            response.say("I can help you save memories, retrieve them by number, or store secrets. What would you like to do?", voice='alice')
        
        return response
    
    async def send_sms(self, to_number: str, message: str, media_url: Optional[str] = None) -> bool:
        """Send SMS notification"""
        if not self.client:
            logger.error("❌ Twilio client not initialized")
            return False
        
        try:
            kwargs = {
                'body': message,
                'from_': self.phone_number,
                'to': to_number
            }
            
            if media_url:
                kwargs['media_url'] = [media_url]
            
            message = self.client.messages.create(**kwargs)
            logger.info(f"✅ SMS sent to {to_number}: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send SMS: {e}")
            return False
    
    async def make_outbound_call(self, to_number: str, message: str) -> bool:
        """Make outbound call with TTS message"""
        if not self.client:
            logger.error("❌ Twilio client not initialized")
            return False
        
        try:
            twiml = f'<Response><Say voice="alice">{message}</Say></Response>'
            
            call = self.client.calls.create(
                twiml=twiml,
                to=to_number,
                from_=self.phone_number
            )
            
            logger.info(f"✅ Outbound call initiated to {to_number}: {call.sid}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to make call: {e}")
            return False
    
    async def process_transcription(self, transcription_text: str, caller_id: str) -> Dict[str, Any]:
        """Process call transcription and create memory"""
        from memory_app import memory_app
        
        # Analyze transcription for key information
        analysis = {
            'caller_id': caller_id,
            'transcription': transcription_text,
            'timestamp': datetime.now().isoformat(),
            'platform': 'twilio_voice'
        }
        
        # Create memory from transcription
        memory_result = await memory_app.store_memory(
            user_id=caller_id,
            content=transcription_text,
            category='voice_call',
            platform='twilio'
        )
        
        return {
            'success': True,
            'memory_id': memory_result.get('memory_id'),
            'memory_number': memory_result.get('memory_number'),
            'analysis': analysis
        }
    
    async def check_voice_enrollment(self, phone_number: str) -> bool:
        """Check if user is enrolled for voice authentication"""
        # This would check the database for voice enrollment status
        # For now, return False to trigger enrollment flow
        return False
    
    async def retrieve_memory(self, caller_id: str, memory_number: str) -> str:
        """Retrieve memory content by number"""
        from memory_app import memory_app
        
        try:
            memory = await memory_app.get_memory_by_number(caller_id, int(memory_number))
            if memory:
                return memory.get('content', 'Memory not found')
            return "Memory not found"
        except:
            return "Unable to retrieve memory"
    
    def get_webhook_urls(self) -> Dict[str, str]:
        """Get all Twilio webhook URLs for configuration"""
        return {
            'voice_url': f'{self.webhook_base_url}/webhook/twilio/voice',
            'voice_fallback_url': f'{self.webhook_base_url}/webhook/twilio/voice-fallback',
            'voice_status_callback': f'{self.webhook_base_url}/webhook/twilio/voice-status',
            'sms_url': f'{self.webhook_base_url}/webhook/twilio/sms',
            'sms_fallback_url': f'{self.webhook_base_url}/webhook/twilio/sms-fallback',
            'sms_status_callback': f'{self.webhook_base_url}/webhook/twilio/sms-status'
        }
    
    async def configure_phone_number(self) -> bool:
        """Configure Twilio phone number with webhooks"""
        if not self.client or not self.phone_number:
            logger.error("❌ Cannot configure phone number - client not initialized")
            return False
        
        try:
            # Get phone number resource
            phone_numbers = self.client.incoming_phone_numbers.list(
                phone_number=self.phone_number
            )
            
            if not phone_numbers:
                logger.error(f"❌ Phone number {self.phone_number} not found")
                return False
            
            phone_number_sid = phone_numbers[0].sid
            webhook_urls = self.get_webhook_urls()
            
            # Update phone number configuration
            self.client.incoming_phone_numbers(phone_number_sid).update(
                voice_url=webhook_urls['voice_url'],
                voice_fallback_url=webhook_urls['voice_fallback_url'],
                status_callback=webhook_urls['voice_status_callback'],
                sms_url=webhook_urls['sms_url'],
                sms_fallback_url=webhook_urls['sms_fallback_url'],
                sms_status_callback=webhook_urls['sms_status_callback'],
                voice_method='POST',
                sms_method='POST'
            )
            
            logger.info(f"✅ Phone number {self.phone_number} configured with webhooks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to configure phone number: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Twilio integration status"""
        return {
            'configured': bool(self.client),
            'account_sid': self.account_sid[:10] + '...' if self.account_sid else None,
            'phone_number': self.phone_number,
            'webhook_base_url': self.webhook_base_url,
            'features': {
                'voice_calls': True,
                'sms': True,
                'mms': True,
                'transcription': True,
                'recording': True
            }
        }

# Global instance
twilio_integration = TwilioIntegration()

if __name__ == "__main__":
    # Test Twilio integration
    print("📞 Twilio Integration Status")
    print("=" * 50)
    
    status = twilio_integration.get_status()
    print(f"Configured: {'✅' if status['configured'] else '❌'}")
    print(f"Account SID: {status['account_sid']}")
    print(f"Phone Number: {status['phone_number']}")
    print(f"Webhook URL: {status['webhook_base_url']}")
    
    if status['configured']:
        print("\n🔧 Configuring phone number webhooks...")
        asyncio.run(twilio_integration.configure_phone_number())
    else:
        print("\n⚠️ Twilio not configured. Set environment variables:")
        print("  - TWILIO_ACCOUNT_SID")
        print("  - TWILIO_AUTH_TOKEN")
        print("  - TWILIO_PHONE_NUMBER")
        print("  - WEBHOOK_BASE_URL")