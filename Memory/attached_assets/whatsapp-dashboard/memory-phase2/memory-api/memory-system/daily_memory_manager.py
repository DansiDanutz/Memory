#!/usr/bin/env python3
"""
Daily Memory Manager - Advanced Memory Organization and Digest System
Analyzes memory files, creates intelligent summaries, and delivers daily digests
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import re
import openai
from collections import defaultdict, Counter
import schedule
import threading

from md_file_manager import MDFileManager, MemoryTag
from conversation_classifier import ConversationClassifier, ConversationContext

logger = logging.getLogger(__name__)

class DigestType(Enum):
    """Types of memory digests"""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class Priority(Enum):
    """Priority levels for memories"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class MemoryInsight:
    """Represents an insight extracted from memories"""
    insight_id: str
    type: str  # pattern, trend, reminder, connection
    title: str
    description: str
    related_memories: List[str]
    confidence: float
    priority: Priority
    actionable: bool
    created_at: datetime

@dataclass
class DailyDigest:
    """Represents a daily memory digest"""
    digest_id: str
    user_phone: str
    date: datetime
    digest_type: DigestType
    summary: str
    key_memories: List[Dict[str, Any]]
    insights: List[MemoryInsight]
    reminders: List[str]
    action_items: List[str]
    mood_analysis: Dict[str, Any]
    statistics: Dict[str, Any]
    created_at: datetime

class DailyMemoryManager:
    """Advanced Daily Memory Manager and Digest System"""
    
    def __init__(self, md_file_manager=None, conversation_classifier=None, 
                 whatsapp_bot=None, telegram_bot=None, openai_api_key=None):
        """Initialize the daily memory manager"""
        self.md_file_manager = md_file_manager or MDFileManager()
        self.conversation_classifier = conversation_classifier or ConversationClassifier()
        self.whatsapp_bot = whatsapp_bot
        self.telegram_bot = telegram_bot
        
        self.openai_client = openai.OpenAI(
            api_key=openai_api_key or os.getenv('OPENAI_API_KEY')
        )
        
        # Data directories
        self.data_dir = Path("memory-system/daily_manager_data")
        self.digests_dir = self.data_dir / "digests"
        self.insights_dir = self.data_dir / "insights"
        self.analytics_dir = self.data_dir / "analytics"
        
        for directory in [self.data_dir, self.digests_dir, self.insights_dir, self.analytics_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.digest_schedules = {
            DigestType.MORNING: time(8, 0),    # 8:00 AM
            DigestType.AFTERNOON: time(14, 0), # 2:00 PM
            DigestType.EVENING: time(20, 0)    # 8:00 PM
        }
        
        # Analysis prompts
        self.analysis_prompts = self._load_analysis_prompts()
        
        # User preferences
        self.user_preferences = {}
        self.load_user_preferences()
        
        # Scheduler
        self.scheduler_thread = None
        self.running = False
        
        logger.info("📊 Daily Memory Manager initialized")
    
    def _load_analysis_prompts(self) -> Dict[str, str]:
        """Load analysis prompts for different scenarios"""
        return {
            'daily_summary': """
Analyze the following memories from today and create a comprehensive daily summary:

Memories: {memories}

Create a summary that includes:
1. Key events and conversations
2. Important information learned
3. Emotional tone and mood
4. Patterns or trends noticed
5. Action items or follow-ups needed

Format as a friendly, personal summary in 2-3 paragraphs.
""",
            
            'insight_extraction': """
Analyze these memories and extract meaningful insights:

Memories: {memories}
Historical Context: {context}

Look for:
1. Patterns in behavior or communication
2. Recurring themes or topics
3. Relationship dynamics
4. Personal growth or changes
5. Potential concerns or opportunities

Return insights in JSON format:
{{
    "insights": [
        {{
            "type": "pattern|trend|reminder|connection",
            "title": "Brief insight title",
            "description": "Detailed description",
            "confidence": 0.0-1.0,
            "priority": "low|medium|high|urgent",
            "actionable": true/false
        }}
    ]
}}
""",
            
            'mood_analysis': """
Analyze the emotional tone and mood from these memories:

Memories: {memories}

Determine:
1. Overall mood (positive, negative, neutral)
2. Emotional intensity (low, medium, high)
3. Dominant emotions present
4. Mood changes throughout the day
5. Factors influencing mood

Return analysis in JSON format:
{{
    "overall_mood": "positive|negative|neutral",
    "intensity": "low|medium|high",
    "dominant_emotions": ["emotion1", "emotion2"],
    "mood_progression": "description of how mood changed",
    "influencing_factors": ["factor1", "factor2"]
}}
""",
            
            'reminder_extraction': """
Extract reminders and action items from these memories:

Memories: {memories}

Find:
1. Explicit reminders ("remind me to...")
2. Implicit tasks or commitments
3. Upcoming events or deadlines
4. Follow-up actions needed
5. Time-sensitive items

Return in JSON format:
{{
    "reminders": [
        {{
            "text": "reminder text",
            "priority": "low|medium|high|urgent",
            "due_date": "YYYY-MM-DD or null",
            "category": "personal|work|health|family"
        }}
    ]
}}
""",
            
            'relationship_analysis': """
Analyze relationship dynamics from these memories:

Memories: {memories}
Known Contacts: {contacts}

Analyze:
1. Communication patterns with each contact
2. Relationship quality indicators
3. Changes in relationship dynamics
4. Potential relationship issues or strengths
5. Social network insights

Return analysis in JSON format:
{{
    "relationships": [
        {{
            "contact": "contact name",
            "interaction_frequency": "high|medium|low",
            "relationship_quality": "excellent|good|neutral|concerning",
            "recent_changes": "description",
            "insights": ["insight1", "insight2"]
        }}
    ]
}}
"""
        }
    
    def load_user_preferences(self):
        """Load user preferences for digest delivery"""
        prefs_file = self.data_dir / "user_preferences.json"
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r') as f:
                    self.user_preferences = json.load(f)
                logger.info(f"📂 Loaded preferences for {len(self.user_preferences)} users")
            except Exception as e:
                logger.error(f"Failed to load user preferences: {e}")
                self.user_preferences = {}
    
    def save_user_preferences(self):
        """Save user preferences"""
        prefs_file = self.data_dir / "user_preferences.json"
        try:
            with open(prefs_file, 'w') as f:
                json.dump(self.user_preferences, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
    
    async def analyze_daily_memories(self, phone_number: str, date: datetime = None) -> Dict[str, Any]:
        """Analyze memories for a specific day"""
        try:
            if date is None:
                date = datetime.now()
            
            # Get memories for the day
            memories_result = await self.md_file_manager.get_user_memories(
                phone_number=phone_number,
                limit=100
            )
            
            if not memories_result['success']:
                return {
                    'success': False,
                    'message': 'Failed to retrieve memories'
                }
            
            all_memories = memories_result['memories']
            
            # Filter memories for the specific date
            date_str = date.strftime('%Y-%m-%d')
            daily_memories = []
            
            for memory in all_memories:
                memory_date = memory.get('metadata', {}).get('time', '')
                if date_str in memory_date:
                    daily_memories.append(memory)
            
            if not daily_memories:
                return {
                    'success': True,
                    'message': 'No memories found for this date',
                    'memories_count': 0
                }
            
            # Perform various analyses
            analysis_results = {}
            
            # 1. Create daily summary
            summary_result = await self._create_daily_summary(daily_memories)
            analysis_results['summary'] = summary_result
            
            # 2. Extract insights
            insights_result = await self._extract_insights(daily_memories, phone_number)
            analysis_results['insights'] = insights_result
            
            # 3. Analyze mood
            mood_result = await self._analyze_mood(daily_memories)
            analysis_results['mood'] = mood_result
            
            # 4. Extract reminders
            reminders_result = await self._extract_reminders(daily_memories)
            analysis_results['reminders'] = reminders_result
            
            # 5. Analyze relationships
            relationships_result = await self._analyze_relationships(daily_memories, phone_number)
            analysis_results['relationships'] = relationships_result
            
            # 6. Generate statistics
            stats = self._generate_daily_statistics(daily_memories)
            analysis_results['statistics'] = stats
            
            logger.info(f"📊 Analyzed {len(daily_memories)} memories for {phone_number}")
            
            return {
                'success': True,
                'date': date.isoformat(),
                'memories_count': len(daily_memories),
                'analysis': analysis_results
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze daily memories: {e}")
            return {
                'success': False,
                'message': f'Failed to analyze memories: {str(e)}',
                'error': str(e)
            }
    
    async def _create_daily_summary(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a daily summary from memories"""
        try:
            if not memories:
                return {'summary': 'No significant activities recorded today.'}
            
            # Prepare memories text
            memories_text = []
            for memory in memories:
                content = memory.get('content', '').strip()
                time_info = memory.get('metadata', {}).get('time', '')
                memories_text.append(f"[{time_info}] {content}")
            
            prompt = self.analysis_prompts['daily_summary'].format(
                memories='\n'.join(memories_text[:20])  # Limit to avoid token limits
            )
            
            response = await self._call_openai(prompt, max_tokens=400)
            
            return {
                'summary': response,
                'memories_analyzed': len(memories)
            }
            
        except Exception as e:
            logger.error(f"Failed to create daily summary: {e}")
            return {
                'summary': 'Unable to generate summary at this time.',
                'error': str(e)
            }
    
    async def _extract_insights(self, memories: List[Dict[str, Any]], phone_number: str) -> Dict[str, Any]:
        """Extract insights from memories"""
        try:
            if not memories:
                return {'insights': []}
            
            # Get historical context
            historical_memories = await self.md_file_manager.get_user_memories(
                phone_number=phone_number,
                limit=50
            )
            
            historical_context = []
            if historical_memories['success']:
                for memory in historical_memories['memories'][-10:]:  # Last 10 for context
                    historical_context.append(memory.get('content', ''))
            
            # Prepare current memories
            current_memories_text = []
            for memory in memories:
                content = memory.get('content', '').strip()
                current_memories_text.append(content)
            
            prompt = self.analysis_prompts['insight_extraction'].format(
                memories='\n'.join(current_memories_text[:15]),
                context='\n'.join(historical_context)
            )
            
            response = await self._call_openai(prompt, max_tokens=500)
            
            try:
                insights_data = json.loads(response)
                insights = []
                
                for insight_data in insights_data.get('insights', []):
                    insight = MemoryInsight(
                        insight_id=f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(insights)}",
                        type=insight_data.get('type', 'pattern'),
                        title=insight_data.get('title', ''),
                        description=insight_data.get('description', ''),
                        related_memories=[m.get('id', '') for m in memories],
                        confidence=insight_data.get('confidence', 0.5),
                        priority=Priority(insight_data.get('priority', 'medium')),
                        actionable=insight_data.get('actionable', False),
                        created_at=datetime.now()
                    )
                    insights.append(insight)
                
                return {
                    'insights': [asdict(insight) for insight in insights],
                    'insights_count': len(insights)
                }
                
            except json.JSONDecodeError:
                return {
                    'insights': [],
                    'error': 'Failed to parse insights JSON'
                }
                
        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")
            return {
                'insights': [],
                'error': str(e)
            }
    
    async def _analyze_mood(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze mood from memories"""
        try:
            if not memories:
                return {
                    'overall_mood': 'neutral',
                    'intensity': 'low',
                    'dominant_emotions': [],
                    'mood_progression': 'No data available',
                    'influencing_factors': []
                }
            
            # Prepare memories text
            memories_text = []
            for memory in memories:
                content = memory.get('content', '').strip()
                memories_text.append(content)
            
            prompt = self.analysis_prompts['mood_analysis'].format(
                memories='\n'.join(memories_text[:20])
            )
            
            response = await self._call_openai(prompt, max_tokens=300)
            
            try:
                mood_data = json.loads(response)
                return mood_data
            except json.JSONDecodeError:
                # Fallback analysis
                return self._fallback_mood_analysis(memories_text)
                
        except Exception as e:
            logger.error(f"Failed to analyze mood: {e}")
            return {
                'overall_mood': 'neutral',
                'intensity': 'medium',
                'error': str(e)
            }
    
    def _fallback_mood_analysis(self, memories_text: List[str]) -> Dict[str, Any]:
        """Fallback mood analysis using keyword matching"""
        positive_words = ['happy', 'good', 'great', 'excellent', 'wonderful', 'amazing', 'love', 'excited']
        negative_words = ['sad', 'bad', 'terrible', 'awful', 'hate', 'angry', 'frustrated', 'worried']
        
        positive_count = 0
        negative_count = 0
        
        for text in memories_text:
            text_lower = text.lower()
            positive_count += sum(1 for word in positive_words if word in text_lower)
            negative_count += sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            overall_mood = 'positive'
        elif negative_count > positive_count:
            overall_mood = 'negative'
        else:
            overall_mood = 'neutral'
        
        intensity = 'high' if (positive_count + negative_count) > 5 else 'medium' if (positive_count + negative_count) > 2 else 'low'
        
        return {
            'overall_mood': overall_mood,
            'intensity': intensity,
            'dominant_emotions': ['content', 'neutral'],
            'mood_progression': 'Stable throughout the day',
            'influencing_factors': ['daily activities', 'conversations']
        }
    
    async def _extract_reminders(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract reminders and action items"""
        try:
            if not memories:
                return {'reminders': []}
            
            # Prepare memories text
            memories_text = []
            for memory in memories:
                content = memory.get('content', '').strip()
                memories_text.append(content)
            
            prompt = self.analysis_prompts['reminder_extraction'].format(
                memories='\n'.join(memories_text[:20])
            )
            
            response = await self._call_openai(prompt, max_tokens=400)
            
            try:
                reminders_data = json.loads(response)
                return reminders_data
            except json.JSONDecodeError:
                # Fallback extraction
                return self._fallback_reminder_extraction(memories_text)
                
        except Exception as e:
            logger.error(f"Failed to extract reminders: {e}")
            return {
                'reminders': [],
                'error': str(e)
            }
    
    def _fallback_reminder_extraction(self, memories_text: List[str]) -> Dict[str, Any]:
        """Fallback reminder extraction using pattern matching"""
        reminders = []
        
        reminder_patterns = [
            r'remind me to (.+)',
            r'don\'t forget to (.+)',
            r'need to (.+)',
            r'have to (.+)',
            r'should (.+)',
            r'appointment (.+)',
            r'meeting (.+)'
        ]
        
        for text in memories_text:
            text_lower = text.lower()
            for pattern in reminder_patterns:
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    reminders.append({
                        'text': match.strip(),
                        'priority': 'medium',
                        'due_date': None,
                        'category': 'personal'
                    })
        
        return {'reminders': reminders}
    
    async def _analyze_relationships(self, memories: List[Dict[str, Any]], phone_number: str) -> Dict[str, Any]:
        """Analyze relationship dynamics"""
        try:
            if not memories:
                return {'relationships': []}
            
            # Get user's contacts
            stats_result = await self.md_file_manager.get_file_stats(phone_number)
            contacts = []
            
            if stats_result['success']:
                # This is a simplified approach - in reality, we'd parse contact files
                contacts = ['Mom', 'Dad', 'John', 'Sarah']  # Placeholder
            
            # Prepare memories text
            memories_text = []
            for memory in memories:
                content = memory.get('content', '').strip()
                memories_text.append(content)
            
            prompt = self.analysis_prompts['relationship_analysis'].format(
                memories='\n'.join(memories_text[:15]),
                contacts=json.dumps(contacts)
            )
            
            response = await self._call_openai(prompt, max_tokens=400)
            
            try:
                relationships_data = json.loads(response)
                return relationships_data
            except json.JSONDecodeError:
                return {'relationships': []}
                
        except Exception as e:
            logger.error(f"Failed to analyze relationships: {e}")
            return {
                'relationships': [],
                'error': str(e)
            }
    
    def _generate_daily_statistics(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate daily statistics from memories"""
        if not memories:
            return {
                'total_memories': 0,
                'memories_by_tag': {},
                'memories_by_hour': {},
                'average_length': 0,
                'most_active_hour': None
            }
        
        # Count by tag
        tag_counts = Counter()
        hour_counts = Counter()
        lengths = []
        
        for memory in memories:
            # Count by tag
            tag = memory.get('metadata', {}).get('tag', 'unknown')
            tag_counts[tag] += 1
            
            # Count by hour
            time_str = memory.get('metadata', {}).get('time', '')
            if time_str:
                try:
                    # Extract hour from timestamp
                    hour = datetime.fromisoformat(time_str.replace('Z', '+00:00')).hour
                    hour_counts[hour] += 1
                except:
                    pass
            
            # Calculate length
            content = memory.get('content', '')
            lengths.append(len(content.split()))
        
        most_active_hour = hour_counts.most_common(1)[0][0] if hour_counts else None
        
        return {
            'total_memories': len(memories),
            'memories_by_tag': dict(tag_counts),
            'memories_by_hour': dict(hour_counts),
            'average_length': sum(lengths) / len(lengths) if lengths else 0,
            'most_active_hour': most_active_hour
        }
    
    async def create_daily_digest(self, phone_number: str, digest_type: DigestType, 
                                 date: datetime = None) -> Dict[str, Any]:
        """Create a comprehensive daily digest"""
        try:
            if date is None:
                date = datetime.now()
            
            # Analyze daily memories
            analysis_result = await self.analyze_daily_memories(phone_number, date)
            
            if not analysis_result['success']:
                return analysis_result
            
            analysis = analysis_result.get('analysis', {})
            
            # Create digest
            digest = DailyDigest(
                digest_id=f"digest_{phone_number}_{date.strftime('%Y%m%d')}_{digest_type.value}",
                user_phone=phone_number,
                date=date,
                digest_type=digest_type,
                summary=analysis.get('summary', {}).get('summary', ''),
                key_memories=analysis_result.get('memories', [])[:5],  # Top 5 memories
                insights=[MemoryInsight(**insight) for insight in analysis.get('insights', {}).get('insights', [])],
                reminders=analysis.get('reminders', {}).get('reminders', []),
                action_items=[],  # Extracted from reminders
                mood_analysis=analysis.get('mood', {}),
                statistics=analysis.get('statistics', {}),
                created_at=datetime.now()
            )
            
            # Format digest message
            digest_message = self._format_digest_message(digest)
            
            # Save digest
            await self._save_digest(digest)
            
            logger.info(f"📋 Created {digest_type.value} digest for {phone_number}")
            
            return {
                'success': True,
                'digest': asdict(digest),
                'message': digest_message
            }
            
        except Exception as e:
            logger.error(f"Failed to create daily digest: {e}")
            return {
                'success': False,
                'message': f'Failed to create digest: {str(e)}',
                'error': str(e)
            }
    
    def _format_digest_message(self, digest: DailyDigest) -> str:
        """Format digest into a user-friendly message"""
        date_str = digest.date.strftime('%B %d, %Y')
        
        # Choose greeting based on digest type
        greetings = {
            DigestType.MORNING: f"🌅 Good morning! Here's your memory summary for {date_str}:",
            DigestType.AFTERNOON: f"☀️ Afternoon update! Here's what's been happening:",
            DigestType.EVENING: f"🌙 Evening recap for {date_str}:"
        }
        
        greeting = greetings.get(digest.digest_type, f"📋 Memory digest for {date_str}:")
        
        message_parts = [greeting, ""]
        
        # Add summary
        if digest.summary:
            message_parts.extend([
                "📝 **Daily Summary:**",
                digest.summary,
                ""
            ])
        
        # Add key insights
        if digest.insights:
            message_parts.append("💡 **Key Insights:**")
            for insight in digest.insights[:3]:  # Top 3 insights
                priority_emoji = {"low": "🔵", "medium": "🟡", "high": "🟠", "urgent": "🔴"}
                emoji = priority_emoji.get(insight.priority.value, "🔵")
                message_parts.append(f"{emoji} {insight.title}")
            message_parts.append("")
        
        # Add reminders
        if digest.reminders:
            message_parts.append("⏰ **Reminders:**")
            for reminder in digest.reminders[:5]:  # Top 5 reminders
                if isinstance(reminder, dict):
                    text = reminder.get('text', str(reminder))
                else:
                    text = str(reminder)
                message_parts.append(f"• {text}")
            message_parts.append("")
        
        # Add mood analysis
        if digest.mood_analysis:
            mood = digest.mood_analysis.get('overall_mood', 'neutral')
            mood_emoji = {"positive": "😊", "negative": "😔", "neutral": "😐"}
            emoji = mood_emoji.get(mood, "😐")
            message_parts.extend([
                f"🎭 **Mood Today:** {emoji} {mood.title()}",
                ""
            ])
        
        # Add statistics
        if digest.statistics:
            total_memories = digest.statistics.get('total_memories', 0)
            most_active_hour = digest.statistics.get('most_active_hour')
            
            stats_text = f"📊 **Activity:** {total_memories} memories recorded"
            if most_active_hour is not None:
                stats_text += f", most active at {most_active_hour}:00"
            
            message_parts.extend([stats_text, ""])
        
        # Add footer
        message_parts.extend([
            "---",
            "💬 Reply with questions about any of these memories!",
            "🔍 Use /search to find specific information",
            "⚙️ Use /settings to customize your digests"
        ])
        
        return '\n'.join(message_parts)
    
    async def _save_digest(self, digest: DailyDigest):
        """Save digest to file"""
        try:
            digest_file = self.digests_dir / f"{digest.digest_id}.json"
            
            # Convert digest to serializable format
            digest_data = asdict(digest)
            
            # Handle datetime serialization
            digest_data['date'] = digest.date.isoformat()
            digest_data['created_at'] = digest.created_at.isoformat()
            
            # Handle insights serialization
            for insight in digest_data['insights']:
                if isinstance(insight, dict) and 'created_at' in insight:
                    insight['created_at'] = insight['created_at'].isoformat() if hasattr(insight['created_at'], 'isoformat') else str(insight['created_at'])
            
            with open(digest_file, 'w') as f:
                json.dump(digest_data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save digest: {e}")
    
    async def send_digest(self, phone_number: str, digest_type: DigestType) -> Dict[str, Any]:
        """Create and send a digest to user"""
        try:
            # Check user preferences
            user_prefs = self.user_preferences.get(phone_number, {})
            digest_enabled = user_prefs.get('digests_enabled', True)
            
            if not digest_enabled:
                return {
                    'success': False,
                    'message': 'Digests disabled for this user'
                }
            
            # Create digest
            digest_result = await self.create_daily_digest(phone_number, digest_type)
            
            if not digest_result['success']:
                return digest_result
            
            digest_message = digest_result['message']
            
            # Send via available channels
            sent = False
            
            if self.whatsapp_bot:
                result = await self.whatsapp_bot.send_proactive_message(
                    phone_number=phone_number,
                    message=digest_message
                )
                sent = result.get('success', False)
            
            if not sent and self.telegram_bot:
                result = await self.telegram_bot.send_message(
                    phone_number=phone_number,
                    message=digest_message
                )
                sent = result.get('success', False)
            
            if sent:
                logger.info(f"📤 Sent {digest_type.value} digest to {phone_number}")
            
            return {
                'success': sent,
                'message': 'Digest sent successfully' if sent else 'Failed to send digest',
                'digest_id': digest_result['digest']['digest_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to send digest: {e}")
            return {
                'success': False,
                'message': f'Failed to send digest: {str(e)}',
                'error': str(e)
            }
    
    async def _call_openai(self, prompt: str, max_tokens: int = 300) -> str:
        """Call OpenAI API with error handling"""
        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert AI assistant for personal memory analysis and insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def start_scheduler(self):
        """Start the digest scheduler"""
        if self.running:
            return
        
        self.running = True
        
        # Schedule daily digests
        schedule.every().day.at("08:00").do(self._schedule_morning_digests)
        schedule.every().day.at("14:00").do(self._schedule_afternoon_digests)
        schedule.every().day.at("20:00").do(self._schedule_evening_digests)
        
        # Schedule weekly digests
        schedule.every().sunday.at("09:00").do(self._schedule_weekly_digests)
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("⏰ Daily Memory Manager scheduler started")
    
    def stop_scheduler(self):
        """Stop the digest scheduler"""
        self.running = False
        schedule.clear()
        logger.info("⏸️ Daily Memory Manager scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            asyncio.sleep(60)  # Check every minute
    
    def _schedule_morning_digests(self):
        """Schedule morning digests for all users"""
        asyncio.create_task(self._send_digests_to_all_users(DigestType.MORNING))
    
    def _schedule_afternoon_digests(self):
        """Schedule afternoon digests for all users"""
        asyncio.create_task(self._send_digests_to_all_users(DigestType.AFTERNOON))
    
    def _schedule_evening_digests(self):
        """Schedule evening digests for all users"""
        asyncio.create_task(self._send_digests_to_all_users(DigestType.EVENING))
    
    def _schedule_weekly_digests(self):
        """Schedule weekly digests for all users"""
        asyncio.create_task(self._send_digests_to_all_users(DigestType.WEEKLY))
    
    async def _send_digests_to_all_users(self, digest_type: DigestType):
        """Send digests to all users who have them enabled"""
        try:
            # Get all users with preferences
            for phone_number, prefs in self.user_preferences.items():
                if prefs.get('digests_enabled', True):
                    digest_types_enabled = prefs.get('digest_types', [digest_type.value])
                    
                    if digest_type.value in digest_types_enabled:
                        await self.send_digest(phone_number, digest_type)
                        
                        # Add delay between sends to avoid rate limiting
                        await asyncio.sleep(1)
            
            logger.info(f"📬 Completed {digest_type.value} digest delivery cycle")
            
        except Exception as e:
            logger.error(f"Failed to send digests to all users: {e}")
    
    async def get_digest_history(self, phone_number: str, days: int = 7) -> Dict[str, Any]:
        """Get digest history for a user"""
        try:
            digests = []
            
            # Search for digest files
            for digest_file in self.digests_dir.glob(f"digest_{phone_number}_*.json"):
                try:
                    with open(digest_file, 'r') as f:
                        digest_data = json.load(f)
                        digests.append(digest_data)
                except Exception as e:
                    logger.error(f"Failed to load digest file {digest_file}: {e}")
            
            # Filter by date range
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_digests = []
            
            for digest in digests:
                try:
                    digest_date = datetime.fromisoformat(digest['date'])
                    if digest_date >= cutoff_date:
                        recent_digests.append(digest)
                except:
                    pass
            
            # Sort by date
            recent_digests.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            return {
                'success': True,
                'digests': recent_digests,
                'count': len(recent_digests)
            }
            
        except Exception as e:
            logger.error(f"Failed to get digest history: {e}")
            return {
                'success': False,
                'message': f'Failed to get digest history: {str(e)}',
                'error': str(e)
            }

# Example usage and testing
async def main():
    """Test the daily memory manager"""
    manager = DailyMemoryManager()
    
    # Test daily analysis
    result = await manager.analyze_daily_memories("+1234567890")
    print("Daily Analysis:", result)
    
    # Test digest creation
    result = await manager.create_daily_digest("+1234567890", DigestType.MORNING)
    print("Digest Creation:", result)
    
    # Test digest history
    result = await manager.get_digest_history("+1234567890")
    print("Digest History:", result)

if __name__ == "__main__":
    asyncio.run(main())

