#!/usr/bin/env python3
"""
Proactive Reminder System
Monitors conversations, extracts time-based tasks, and initiates WhatsApp reminders
"""

import os
import json
import re
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import hashlib

# For sending WhatsApp messages
import aiohttp
from twilio.rest import Client

logger = logging.getLogger(__name__)

class ProactiveReminderSystem:
    """
    Intelligent system that monitors conversations and proactively sends reminders
    """
    
    def __init__(self, data_dir: str = "memory-system/reminders"):
        """Initialize the proactive reminder system"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Timeline of all scheduled reminders
        self.timeline: Dict[str, Dict[str, Any]] = {}
        
        # Conditional reminders (triggered by context)
        self.conditional_reminders: List[Dict[str, Any]] = []
        
        # Recurring reminders
        self.recurring_reminders: List[Dict[str, Any]] = []
        
        # Context tracking for users
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
        
        # Twilio client for sending WhatsApp messages
        self.twilio_client = None
        if os.environ.get('TWILIO_ACCOUNT_SID') and os.environ.get('TWILIO_AUTH_TOKEN'):
            self.twilio_client = Client(
                os.environ.get('TWILIO_ACCOUNT_SID'),
                os.environ.get('TWILIO_AUTH_TOKEN')
            )
        
        # WhatsApp number for sending
        self.whatsapp_from = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        
        # Load existing reminders
        self._load_reminders()
        
        # Start reminder monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_reminders_sync)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("⏰ Proactive Reminder System initialized")
    
    def extract_and_schedule_reminders(self, 
                                      sender_phone: str,
                                      message: str,
                                      recipient_phone: Optional[str] = None,
                                      sender_name: Optional[str] = None,
                                      recipient_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract reminders from conversation and schedule them
        
        Args:
            sender_phone: Phone number of the person speaking
            message: The message content
            recipient_phone: Phone number of the recipient
            sender_name: Name of the sender
            recipient_name: Name of the recipient
        
        Returns:
            Dict with extracted and scheduled reminders
        """
        result = {
            'time_based_reminders': [],
            'conditional_reminders': [],
            'recurring_reminders': [],
            'immediate_actions': []
        }
        
        message_lower = message.lower()
        current_time = datetime.now()
        
        # Extract time-based reminders
        time_reminders = self._extract_time_based_reminders(message_lower, current_time)
        for reminder in time_reminders:
            # Determine target user (who needs the reminder)
            target_phone = self._determine_target_user(
                message_lower, sender_phone, recipient_phone
            )
            
            # Calculate reminder time (1 hour before for appointments)
            event_time = reminder['datetime']
            reminder_time = self._calculate_reminder_time(event_time, reminder['event'])
            
            # Create reminder entry
            reminder_id = self._generate_reminder_id(target_phone, reminder_time)
            self.timeline[reminder_time.isoformat()] = {
                'id': reminder_id,
                'type': 'time_based',
                'event': reminder['event'],
                'event_time': event_time.isoformat(),
                'target_user': target_phone,
                'source': sender_name or sender_phone,
                'original_message': message,
                'created_at': current_time.isoformat(),
                'sent': False
            }
            
            result['time_based_reminders'].append({
                'event': reminder['event'],
                'scheduled_for': reminder_time.isoformat(),
                'target': target_phone
            })
        
        # Extract conditional reminders
        conditional = self._extract_conditional_reminders(message_lower)
        for cond_reminder in conditional:
            target_phone = self._determine_target_user(
                message_lower, sender_phone, recipient_phone
            )
            
            self.conditional_reminders.append({
                'id': self._generate_reminder_id(target_phone, current_time),
                'condition': cond_reminder['condition'],
                'action': cond_reminder['action'],
                'target_user': target_phone,
                'requester': sender_name or sender_phone,
                'original_message': message,
                'created_at': current_time.isoformat(),
                'triggered': False
            })
            
            result['conditional_reminders'].append({
                'condition': cond_reminder['condition'],
                'action': cond_reminder['action'],
                'target': target_phone
            })
        
        # Extract recurring reminders
        recurring = self._extract_recurring_reminders(message_lower)
        for rec_reminder in recurring:
            target_phone = self._determine_target_user(
                message_lower, sender_phone, recipient_phone
            )
            
            self.recurring_reminders.append({
                'id': self._generate_reminder_id(target_phone, current_time),
                'pattern': rec_reminder['pattern'],
                'action': rec_reminder['action'],
                'time': rec_reminder.get('time'),
                'target_user': target_phone,
                'source': sender_name or sender_phone,
                'original_message': message,
                'created_at': current_time.isoformat(),
                'last_triggered': None
            })
            
            result['recurring_reminders'].append({
                'pattern': rec_reminder['pattern'],
                'action': rec_reminder['action'],
                'target': target_phone
            })
        
        # Save reminders
        self._save_reminders()
        
        return result
    
    def _extract_time_based_reminders(self, message: str, current_time: datetime) -> List[Dict[str, Any]]:
        """Extract time-based reminders from message"""
        reminders = []
        
        # Patterns for time extraction
        time_patterns = [
            # Specific times
            (r'(?:at|by)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', 'specific_time'),
            (r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', 'specific_time'),
            
            # Relative times
            (r'in\s+(\d+)\s+(hour|minute|min)s?', 'relative_time'),
            (r'after\s+(\d+)\s+(hour|minute|min)s?', 'relative_time'),
            
            # Named times
            (r'(tomorrow|today)\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', 'named_day'),
            (r'(tomorrow|today)\s+(morning|afternoon|evening|night)', 'named_period'),
            
            # Days of week
            (r'(?:on\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', 'weekday'),
            
            # Dates
            (r'(?:on\s+)?(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)', 'date'),
        ]
        
        # Common event patterns
        event_patterns = [
            r'(hospital|doctor|appointment|meeting|call|interview|exam|test)',
            r'(buy|get|pick up|purchase)\s+(.+?)(?:\.|,|$)',
            r'(go to|visit|meet)\s+(.+?)(?:\.|,|$)',
            r'(take|drink)\s+(medicine|pills|medication)',
            r'(pay|submit|send|file)\s+(.+?)(?:\.|,|$)',
        ]
        
        # Extract events first
        events_found = []
        for pattern in event_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                event = match.group(0).strip()
                events_found.append({
                    'event': event,
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Now find times and associate with events
        for pattern, pattern_type in time_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                # Calculate the actual datetime
                event_datetime = self._parse_time_match(match, pattern_type, current_time)
                
                if event_datetime and event_datetime > current_time:
                    # Find associated event (closest event mention)
                    associated_event = None
                    min_distance = float('inf')
                    
                    for event_info in events_found:
                        distance = min(
                            abs(match.start() - event_info['end']),
                            abs(event_info['start'] - match.end())
                        )
                        if distance < min_distance and distance < 50:  # Within 50 chars
                            min_distance = distance
                            associated_event = event_info['event']
                    
                    # If no specific event found, use context
                    if not associated_event:
                        # Look for general context around the time mention
                        context_start = max(0, match.start() - 30)
                        context_end = min(len(message), match.end() + 30)
                        context = message[context_start:context_end]
                        associated_event = self._clean_event_text(context)
                    
                    reminders.append({
                        'datetime': event_datetime,
                        'event': associated_event or "Scheduled reminder",
                        'match_text': match.group(0)
                    })
        
        return reminders
    
    def _extract_conditional_reminders(self, message: str) -> List[Dict[str, Any]]:
        """Extract conditional reminders from message"""
        reminders = []
        
        # Conditional patterns
        conditional_patterns = [
            (r'when\s+(?:you\s+)?(?:get|come|arrive|reach)\s+home', 'location_home'),
            (r'when\s+(?:you\s+)?(?:get to|arrive at|reach)\s+(?:the\s+)?office', 'location_office'),
            (r'when\s+(?:you\s+)?(?:get to|arrive at|reach)\s+work', 'location_work'),
            (r'when\s+(?:you\s+)?leave\s+(?:the\s+)?(?:office|work)', 'leaving_work'),
            (r'before\s+(?:you\s+)?(?:go to\s+)?(?:sleep|bed)', 'before_sleep'),
            (r'after\s+(?:you\s+)?(?:wake up|get up)', 'after_wakeup'),
            (r'after\s+lunch', 'after_lunch'),
            (r'before\s+dinner', 'before_dinner'),
            (r'when\s+(?:you\s+)?(?:are\s+)?free', 'when_free'),
            (r'when\s+(?:you\s+)?(?:have|get)\s+(?:a\s+)?(?:chance|time)', 'when_available'),
        ]
        
        for pattern, condition_type in conditional_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                # Find the action associated with this condition
                # Look for action words before or after the condition
                action_before = message[:match.start()].strip()
                action_after = message[match.end():].strip()
                
                # Determine which action to use
                action = None
                if action_before and len(action_before) < 100:
                    # Check if there's an action verb before
                    if re.search(r'(buy|get|call|send|check|pick up|remember to)', action_before, re.IGNORECASE):
                        action = action_before
                
                if not action and action_after and len(action_after) < 100:
                    # Use the action after the condition
                    action = action_after.split('.')[0].strip()  # Take first sentence
                
                if action:
                    reminders.append({
                        'condition': condition_type,
                        'condition_text': match.group(0),
                        'action': self._clean_event_text(action)
                    })
        
        return reminders
    
    def _extract_recurring_reminders(self, message: str) -> List[Dict[str, Any]]:
        """Extract recurring reminders from message"""
        reminders = []
        
        # Recurring patterns
        recurring_patterns = [
            (r'every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', 'weekly'),
            (r'every\s+day', 'daily'),
            (r'daily', 'daily'),
            (r'every\s+morning', 'daily_morning'),
            (r'every\s+evening', 'daily_evening'),
            (r'every\s+night', 'daily_night'),
            (r'every\s+week', 'weekly'),
            (r'weekly', 'weekly'),
            (r'every\s+month', 'monthly'),
            (r'monthly', 'monthly'),
        ]
        
        for pattern, recur_type in recurring_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                # Find associated action
                context_start = max(0, match.start() - 50)
                context_end = min(len(message), match.end() + 50)
                context = message[context_start:context_end]
                
                # Extract time if specified
                time_match = re.search(r'at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', context, re.IGNORECASE)
                time_str = None
                if time_match:
                    time_str = time_match.group(0)
                
                # Clean up the action text
                action = self._clean_event_text(context)
                
                reminders.append({
                    'pattern': recur_type,
                    'pattern_text': match.group(0),
                    'action': action,
                    'time': time_str
                })
        
        return reminders
    
    def _parse_time_match(self, match: re.Match, pattern_type: str, current_time: datetime) -> Optional[datetime]:
        """Parse a time match and return datetime object"""
        try:
            if pattern_type == 'specific_time':
                # Parse hour, minute, am/pm
                groups = match.groups()
                hour = int(groups[0])
                minute = int(groups[1]) if groups[1] else 0
                ampm = groups[2] if len(groups) > 2 else None
                
                if ampm:
                    if ampm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif ampm.lower() == 'am' and hour == 12:
                        hour = 0
                
                # Assume today if time hasn't passed, tomorrow otherwise
                result = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if result <= current_time:
                    result += timedelta(days=1)
                
                return result
            
            elif pattern_type == 'relative_time':
                # Parse relative time
                amount = int(match.group(1))
                unit = match.group(2).lower()
                
                if 'hour' in unit:
                    return current_time + timedelta(hours=amount)
                elif 'min' in unit:
                    return current_time + timedelta(minutes=amount)
            
            elif pattern_type == 'named_day':
                # Parse named day with time
                day_name = match.group(1).lower()
                hour = int(match.group(2))
                minute = int(match.group(3)) if match.group(3) else 0
                ampm = match.group(4) if match.group(4) else None
                
                if ampm:
                    if ampm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif ampm.lower() == 'am' and hour == 12:
                        hour = 0
                
                if day_name == 'today':
                    result = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:  # tomorrow
                    result = (current_time + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                return result
            
            elif pattern_type == 'named_period':
                # Parse named period
                day_name = match.group(1).lower()
                period = match.group(2).lower()
                
                # Set approximate times for periods
                period_times = {
                    'morning': 9,
                    'afternoon': 14,
                    'evening': 18,
                    'night': 21
                }
                
                hour = period_times.get(period, 12)
                
                if day_name == 'today':
                    result = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                else:  # tomorrow
                    result = (current_time + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
                
                return result
            
            elif pattern_type == 'weekday':
                # Parse weekday with time
                weekday_name = match.group(1).lower()
                hour = int(match.group(2)) if match.group(2) else 12
                minute = int(match.group(3)) if match.group(3) else 0
                ampm = match.group(4) if match.group(4) else None
                
                if ampm:
                    if ampm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif ampm.lower() == 'am' and hour == 12:
                        hour = 0
                
                # Calculate next occurrence of this weekday
                weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                target_weekday = weekdays.index(weekday_name)
                current_weekday = current_time.weekday()
                
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:  # Same day
                    result = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if result <= current_time:
                        days_ahead = 7  # Next week
                
                result = (current_time + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                return result
            
        except Exception as e:
            logger.error(f"Error parsing time match: {e}")
        
        return None
    
    def _determine_target_user(self, message: str, sender_phone: str, recipient_phone: Optional[str]) -> str:
        """Determine who should receive the reminder"""
        # Look for pronouns to determine target
        if re.search(r'\b(you|your)\b', message, re.IGNORECASE):
            # "You have..." -> recipient gets reminder
            return recipient_phone if recipient_phone else sender_phone
        elif re.search(r'\b(i|my|me)\b', message, re.IGNORECASE):
            # "I have..." -> sender gets reminder
            return sender_phone
        else:
            # Default to sender if unclear
            return sender_phone
    
    def _calculate_reminder_time(self, event_time: datetime, event_description: str) -> datetime:
        """Calculate when to send the reminder based on event type"""
        # For appointments, remind 1 hour before
        if re.search(r'(appointment|meeting|interview|hospital|doctor|exam)', event_description, re.IGNORECASE):
            return event_time - timedelta(hours=1)
        
        # For daily tasks, remind 30 minutes before
        elif re.search(r'(take|drink|medicine|pills)', event_description, re.IGNORECASE):
            return event_time - timedelta(minutes=30)
        
        # For shopping/errands, remind 2 hours before
        elif re.search(r'(buy|shop|pick up|get)', event_description, re.IGNORECASE):
            return event_time - timedelta(hours=2)
        
        # Default: remind 1 hour before
        else:
            return event_time - timedelta(hours=1)
    
    def _clean_event_text(self, text: str) -> str:
        """Clean and format event text"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common filler words at the beginning
        text = re.sub(r'^(please|could you|can you|would you|remember to|don\'t forget to)\s+', '', text, flags=re.IGNORECASE)
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        # Limit length
        if len(text) > 100:
            text = text[:97] + "..."
        
        return text
    
    def _generate_reminder_id(self, user_phone: str, time: datetime) -> str:
        """Generate unique reminder ID"""
        data = f"{user_phone}_{time.isoformat()}_{datetime.now().timestamp()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def update_user_context(self, user_phone: str, context: str):
        """
        Update user context for conditional reminder triggering
        
        Args:
            user_phone: User's phone number
            context: Current context (e.g., 'going_home', 'at_work', 'waking_up')
        """
        if user_phone not in self.user_contexts:
            self.user_contexts[user_phone] = {
                'current_context': None,
                'context_history': [],
                'last_update': None
            }
        
        self.user_contexts[user_phone]['current_context'] = context
        self.user_contexts[user_phone]['context_history'].append({
            'context': context,
            'timestamp': datetime.now().isoformat()
        })
        self.user_contexts[user_phone]['last_update'] = datetime.now().isoformat()
        
        # Check conditional reminders
        self._check_conditional_reminders(user_phone, context)
    
    def _check_conditional_reminders(self, user_phone: str, context: str):
        """Check if any conditional reminders should be triggered"""
        context_mapping = {
            'going_home': 'location_home',
            'at_home': 'location_home',
            'at_office': 'location_office',
            'at_work': 'location_work',
            'leaving_work': 'leaving_work',
            'going_to_sleep': 'before_sleep',
            'waking_up': 'after_wakeup',
            'having_lunch': 'after_lunch',
            'before_dinner': 'before_dinner',
            'free_time': 'when_free',
            'available': 'when_available'
        }
        
        condition_type = context_mapping.get(context)
        if not condition_type:
            return
        
        # Find matching conditional reminders
        for reminder in self.conditional_reminders:
            if (reminder['target_user'] == user_phone and 
                reminder['condition'] == condition_type and 
                not reminder['triggered']):
                
                # Send the reminder
                asyncio.create_task(self._send_reminder_async(reminder))
                
                # Mark as triggered
                reminder['triggered'] = True
                self._save_reminders()
    
    async def _send_reminder_async(self, reminder: Dict[str, Any]):
        """Send a reminder asynchronously"""
        try:
            if not self.twilio_client:
                logger.error("Twilio client not configured for sending reminders")
                return
            
            # Format the reminder message
            if reminder['type'] == 'time_based':
                message = f"🔔 Reminder: {reminder['event']}\n"
                if 'event_time' in reminder:
                    event_dt = datetime.fromisoformat(reminder['event_time'])
                    message += f"⏰ Scheduled for: {event_dt.strftime('%I:%M %p')}\n"
                message += f"\n📝 Original message: {reminder['original_message'][:100]}"
            
            elif reminder['type'] == 'conditional':
                message = f"🔔 Conditional Reminder: {reminder['action']}\n"
                message += f"📍 Triggered by: {reminder['condition'].replace('_', ' ')}\n"
                message += f"👤 Requested by: {reminder.get('requester', 'Someone')}"
            
            elif reminder['type'] == 'recurring':
                message = f"🔔 Recurring Reminder: {reminder['action']}\n"
                message += f"🔄 Pattern: {reminder['pattern'].replace('_', ' ')}"
            
            else:
                message = f"🔔 Reminder: {reminder.get('action', reminder.get('event', 'Check your tasks'))}"
            
            # Send via Twilio WhatsApp
            to_number = f"whatsapp:+{reminder['target_user'].replace('+', '')}"
            
            twilio_message = self.twilio_client.messages.create(
                body=message,
                from_=self.whatsapp_from,
                to=to_number
            )
            
            logger.info(f"✅ Reminder sent to {reminder['target_user']}: {twilio_message.sid}")
            
            # Mark as sent
            if reminder.get('type') == 'time_based':
                reminder['sent'] = True
            
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")
    
    def _monitor_reminders_sync(self):
        """Synchronous wrapper for monitoring reminders"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._monitor_reminders())
    
    async def _monitor_reminders(self):
        """Monitor and send reminders when due"""
        logger.info("⏰ Starting reminder monitoring...")
        
        while self.monitoring:
            try:
                current_time = datetime.now()
                
                # Check time-based reminders
                for time_key in list(self.timeline.keys()):
                    reminder_time = datetime.fromisoformat(time_key)
                    
                    if reminder_time <= current_time:
                        reminder = self.timeline[time_key]
                        
                        if not reminder.get('sent', False):
                            # Send the reminder
                            await self._send_reminder_async(reminder)
                            
                            # Remove from timeline after sending
                            del self.timeline[time_key]
                            self._save_reminders()
                
                # Check recurring reminders
                for reminder in self.recurring_reminders:
                    should_trigger = False
                    last_triggered = reminder.get('last_triggered')
                    
                    if last_triggered:
                        last_dt = datetime.fromisoformat(last_triggered)
                    else:
                        last_dt = None
                    
                    pattern = reminder['pattern']
                    
                    if pattern == 'daily':
                        if not last_dt or (current_time - last_dt).days >= 1:
                            should_trigger = True
                    
                    elif pattern == 'daily_morning' and current_time.hour == 9:
                        if not last_dt or last_dt.date() != current_time.date():
                            should_trigger = True
                    
                    elif pattern == 'daily_evening' and current_time.hour == 18:
                        if not last_dt or last_dt.date() != current_time.date():
                            should_trigger = True
                    
                    elif pattern == 'daily_night' and current_time.hour == 21:
                        if not last_dt or last_dt.date() != current_time.date():
                            should_trigger = True
                    
                    elif pattern == 'weekly':
                        if not last_dt or (current_time - last_dt).days >= 7:
                            should_trigger = True
                    
                    elif pattern == 'monthly':
                        if not last_dt or (current_time.month != last_dt.month or 
                                         current_time.year != last_dt.year):
                            should_trigger = True
                    
                    if should_trigger:
                        reminder['type'] = 'recurring'
                        await self._send_reminder_async(reminder)
                        reminder['last_triggered'] = current_time.isoformat()
                        self._save_reminders()
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in reminder monitoring: {e}")
                await asyncio.sleep(60)
    
    def _save_reminders(self):
        """Save reminders to disk"""
        try:
            data = {
                'timeline': self.timeline,
                'conditional_reminders': self.conditional_reminders,
                'recurring_reminders': self.recurring_reminders,
                'user_contexts': self.user_contexts
            }
            
            reminder_file = self.data_dir / 'reminders.json'
            with open(reminder_file, 'w') as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save reminders: {e}")
    
    def _load_reminders(self):
        """Load reminders from disk"""
        try:
            reminder_file = self.data_dir / 'reminders.json'
            if reminder_file.exists():
                with open(reminder_file, 'r') as f:
                    data = json.load(f)
                
                self.timeline = data.get('timeline', {})
                self.conditional_reminders = data.get('conditional_reminders', [])
                self.recurring_reminders = data.get('recurring_reminders', [])
                self.user_contexts = data.get('user_contexts', {})
                
                logger.info(f"📂 Loaded {len(self.timeline)} time-based, "
                          f"{len(self.conditional_reminders)} conditional, "
                          f"{len(self.recurring_reminders)} recurring reminders")
        
        except Exception as e:
            logger.error(f"Failed to load reminders: {e}")
    
    def get_user_reminders(self, user_phone: str) -> Dict[str, Any]:
        """Get all reminders for a specific user"""
        result = {
            'upcoming': [],
            'conditional': [],
            'recurring': []
        }
        
        # Get upcoming time-based reminders
        for time_key, reminder in self.timeline.items():
            if reminder['target_user'] == user_phone:
                result['upcoming'].append({
                    'time': time_key,
                    'event': reminder['event'],
                    'source': reminder.get('source', 'Unknown')
                })
        
        # Get conditional reminders
        for reminder in self.conditional_reminders:
            if reminder['target_user'] == user_phone and not reminder['triggered']:
                result['conditional'].append({
                    'condition': reminder['condition'],
                    'action': reminder['action'],
                    'requester': reminder.get('requester', 'Unknown')
                })
        
        # Get recurring reminders
        for reminder in self.recurring_reminders:
            if reminder['target_user'] == user_phone:
                result['recurring'].append({
                    'pattern': reminder['pattern'],
                    'action': reminder['action'],
                    'last_triggered': reminder.get('last_triggered')
                })
        
        return result
    
    def cancel_reminder(self, user_phone: str, reminder_id: str) -> bool:
        """Cancel a specific reminder"""
        # Search in timeline
        for time_key, reminder in list(self.timeline.items()):
            if reminder.get('id') == reminder_id and reminder['target_user'] == user_phone:
                del self.timeline[time_key]
                self._save_reminders()
                return True
        
        # Search in conditional reminders
        for i, reminder in enumerate(self.conditional_reminders):
            if reminder.get('id') == reminder_id and reminder['target_user'] == user_phone:
                del self.conditional_reminders[i]
                self._save_reminders()
                return True
        
        # Search in recurring reminders
        for i, reminder in enumerate(self.recurring_reminders):
            if reminder.get('id') == reminder_id and reminder['target_user'] == user_phone:
                del self.recurring_reminders[i]
                self._save_reminders()
                return True
        
        return False
    
    def stop_monitoring(self):
        """Stop the reminder monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("⏹️ Reminder monitoring stopped")


# Global instance
proactive_reminder_system = ProactiveReminderSystem()

if __name__ == "__main__":
    # Test the reminder system
    import asyncio
    
    async def test_reminders():
        # Test extraction
        result = proactive_reminder_system.extract_and_schedule_reminders(
            sender_phone="40744602272",
            message="You have hospital at 4pm tomorrow. When you come home, buy pizza. Take medicine every day at 9am.",
            recipient_phone="40744602273",
            sender_name="Elena"
        )
        
        print("Extracted reminders:", json.dumps(result, indent=2))
        
        # Test context update
        proactive_reminder_system.update_user_context("40744602272", "going_home")
        
        # Get user reminders
        user_reminders = proactive_reminder_system.get_user_reminders("40744602272")
        print("User reminders:", json.dumps(user_reminders, indent=2))
    
    asyncio.run(test_reminders())