"""
Pattern Analyzer Agent - Advanced Behavioral Intelligence System
Analyzes user behavior patterns, identifies habits, predicts routines, and provides behavioral insights.
"""

import asyncio
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, Counter
import hashlib
import statistics
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import networkx as nx
from textblob import TextBlob
import re

# Base agent imports
from .base_agent import BaseAgent, AgentMessage, AgentCapability, AgentState

class PatternType(Enum):
    """Types of patterns that can be detected"""
    TEMPORAL = "temporal"           # Time-based patterns
    BEHAVIORAL = "behavioral"       # Behavior patterns
    SOCIAL = "social"              # Social interaction patterns
    LOCATION = "location"          # Location-based patterns
    EMOTIONAL = "emotional"        # Emotional state patterns
    ACTIVITY = "activity"          # Activity patterns
    COMMUNICATION = "communication" # Communication patterns
    ROUTINE = "routine"            # Daily/weekly routines

class PatternStrength(Enum):
    """Strength levels for detected patterns"""
    WEAK = "weak"           # 0.3-0.5
    MODERATE = "moderate"   # 0.5-0.7
    STRONG = "strong"       # 0.7-0.85
    VERY_STRONG = "very_strong"  # 0.85+

class HabitType(Enum):
    """Types of habits that can be identified"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"
    TRIGGERED = "triggered"  # Event-triggered habits

@dataclass
class DetectedPattern:
    """Represents a detected behavioral pattern"""
    id: str
    pattern_type: PatternType
    strength: PatternStrength
    confidence: float
    description: str
    frequency: Dict[str, Any]
    triggers: List[str]
    participants: List[str]
    locations: List[str]
    time_windows: List[Dict[str, Any]]
    supporting_memories: List[str]
    first_detected: datetime
    last_updated: datetime
    prediction_accuracy: float
    metadata: Dict[str, Any]

@dataclass
class BehavioralHabit:
    """Represents an identified behavioral habit"""
    id: str
    habit_type: HabitType
    name: str
    description: str
    trigger_conditions: List[str]
    typical_duration: timedelta
    frequency_pattern: Dict[str, Any]
    success_rate: float
    strength_score: float
    related_patterns: List[str]
    supporting_evidence: List[str]
    created_date: datetime
    last_occurrence: datetime
    prediction_model: Dict[str, Any]

@dataclass
class RoutinePrediction:
    """Represents a predicted routine or behavior"""
    id: str
    predicted_activity: str
    confidence: float
    predicted_time: datetime
    duration_estimate: timedelta
    trigger_events: List[str]
    context_factors: Dict[str, Any]
    historical_accuracy: float
    recommendation: str

@dataclass
class BehavioralInsight:
    """Represents an insight about user behavior"""
    id: str
    insight_type: str
    title: str
    description: str
    confidence: float
    supporting_patterns: List[str]
    actionable_recommendations: List[str]
    impact_score: float
    created_date: datetime

class PatternAnalyzerAgent(BaseAgent):
    """
    Advanced Pattern Analyzer Agent that identifies behavioral patterns,
    habits, routines, and provides predictive insights about user behavior.
    """
    
    def __init__(self, agent_id: str = "pattern_analyzer", config: Dict[str, Any] = None):
        super().__init__(agent_id, config)
        
        # Core components
        self.pattern_detectors = {}
        self.habit_analyzers = {}
        self.routine_predictors = {}
        self.insight_generators = {}
        
        # Data storage
        self.detected_patterns: Dict[str, DetectedPattern] = {}
        self.behavioral_habits: Dict[str, BehavioralHabit] = {}
        self.routine_predictions: Dict[str, RoutinePrediction] = {}
        self.behavioral_insights: Dict[str, BehavioralInsight] = {}
        
        # Analysis engines
        self.temporal_analyzer = None
        self.behavioral_analyzer = None
        self.social_analyzer = None
        self.emotional_analyzer = None
        self.activity_analyzer = None
        
        # Machine learning models
        self.clustering_models = {}
        self.prediction_models = {}
        self.classification_models = {}
        
        # Configuration
        self.analysis_config = {
            'min_pattern_strength': 0.3,
            'min_habit_occurrences': 3,
            'prediction_horizon_days': 30,
            'clustering_eps': 0.5,
            'clustering_min_samples': 3,
            'temporal_window_hours': 2,
            'social_interaction_threshold': 0.6,
            'emotional_variance_threshold': 0.4
        }
        
        # Performance tracking
        self.analysis_stats = {
            'patterns_detected': 0,
            'habits_identified': 0,
            'predictions_made': 0,
            'insights_generated': 0,
            'accuracy_scores': [],
            'processing_times': []
        }
    
    async def initialize(self) -> bool:
        """Initialize the Pattern Analyzer Agent"""
        try:
            self.logger.info("Initializing Pattern Analyzer Agent...")
            
            # Initialize pattern detectors
            await self._initialize_pattern_detectors()
            
            # Initialize habit analyzers
            await self._initialize_habit_analyzers()
            
            # Initialize routine predictors
            await self._initialize_routine_predictors()
            
            # Initialize insight generators
            await self._initialize_insight_generators()
            
            # Initialize analysis engines
            await self._initialize_analysis_engines()
            
            # Load existing patterns and habits
            await self._load_existing_data()
            
            self.logger.info("Pattern Analyzer Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Pattern Analyzer Agent initialization failed: {e}")
            return False
    
    async def get_capabilities(self) -> List[AgentCapability]:
        """Return Pattern Analyzer capabilities"""
        return [
            AgentCapability(
                name="analyze_patterns",
                description="Analyze behavioral patterns from memory data",
                input_types=["processed_memories", "memory_batch"],
                output_types=["detected_patterns", "pattern_analysis"],
                dependencies=["memory_harvester"]
            ),
            AgentCapability(
                name="identify_habits",
                description="Identify and track behavioral habits",
                input_types=["behavioral_data", "temporal_data"],
                output_types=["behavioral_habits", "habit_analysis"]
            ),
            AgentCapability(
                name="predict_routines",
                description="Predict future routines and behaviors",
                input_types=["pattern_data", "context_data"],
                output_types=["routine_predictions", "behavioral_forecasts"]
            ),
            AgentCapability(
                name="generate_insights",
                description="Generate behavioral insights and recommendations",
                input_types=["pattern_data", "habit_data"],
                output_types=["behavioral_insights", "recommendations"]
            ),
            AgentCapability(
                name="analyze_trends",
                description="Analyze long-term behavioral trends",
                input_types=["historical_data", "pattern_data"],
                output_types=["trend_analysis", "behavioral_evolution"]
            )
        ]
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages"""
        
        try:
            if message.type == "analyze_patterns":
                # Analyze patterns from memory data
                memories = message.payload.get("memories", [])
                patterns = await self._analyze_patterns_from_memories(memories)
                
                return AgentMessage(
                    id=f"response_{message.id}",
                    type="patterns_analyzed",
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    payload={"detected_patterns": patterns},
                    timestamp=asyncio.get_event_loop().time()
                )
            
            elif message.type == "identify_habits":
                # Identify behavioral habits
                behavioral_data = message.payload.get("behavioral_data", {})
                habits = await self._identify_habits_from_data(behavioral_data)
                
                return AgentMessage(
                    id=f"response_{message.id}",
                    type="habits_identified",
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    payload={"behavioral_habits": habits},
                    timestamp=asyncio.get_event_loop().time()
                )
            
            elif message.type == "predict_routines":
                # Predict future routines
                context_data = message.payload.get("context_data", {})
                predictions = await self._predict_routines(context_data)
                
                return AgentMessage(
                    id=f"response_{message.id}",
                    type="routines_predicted",
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    payload={"routine_predictions": predictions},
                    timestamp=asyncio.get_event_loop().time()
                )
            
            elif message.type == "generate_insights":
                # Generate behavioral insights
                analysis_data = message.payload.get("analysis_data", {})
                insights = await self._generate_behavioral_insights(analysis_data)
                
                return AgentMessage(
                    id=f"response_{message.id}",
                    type="insights_generated",
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    payload={"behavioral_insights": insights},
                    timestamp=asyncio.get_event_loop().time()
                )
            
            elif message.type == "analyze_trends":
                # Analyze behavioral trends
                historical_data = message.payload.get("historical_data", {})
                trends = await self._analyze_behavioral_trends(historical_data)
                
                return AgentMessage(
                    id=f"response_{message.id}",
                    type="trends_analyzed",
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    payload={"trend_analysis": trends},
                    timestamp=asyncio.get_event_loop().time()
                )
            
            elif message.type == "get_pattern_stats":
                # Return pattern analysis statistics
                stats = await self._get_pattern_statistics()
                
                return AgentMessage(
                    id=f"response_{message.id}",
                    type="pattern_stats_response",
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    payload={"pattern_stats": stats},
                    timestamp=asyncio.get_event_loop().time()
                )
            
            else:
                self.logger.warning(f"Unknown message type: {message.type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error processing message {message.type}: {e}")
            return self._create_error_response(message, str(e))
    
    # ==================== PATTERN DETECTION ====================
    
    async def _analyze_patterns_from_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze patterns from processed memories"""
        
        if not memories:
            return []
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Convert memories to analysis format
            analysis_data = await self._prepare_memory_data_for_analysis(memories)
            
            # Run different pattern detection algorithms
            detected_patterns = []
            
            # Temporal pattern detection
            temporal_patterns = await self._detect_temporal_patterns(analysis_data)
            detected_patterns.extend(temporal_patterns)
            
            # Behavioral pattern detection
            behavioral_patterns = await self._detect_behavioral_patterns(analysis_data)
            detected_patterns.extend(behavioral_patterns)
            
            # Social pattern detection
            social_patterns = await self._detect_social_patterns(analysis_data)
            detected_patterns.extend(social_patterns)
            
            # Location pattern detection
            location_patterns = await self._detect_location_patterns(analysis_data)
            detected_patterns.extend(location_patterns)
            
            # Emotional pattern detection
            emotional_patterns = await self._detect_emotional_patterns(analysis_data)
            detected_patterns.extend(emotional_patterns)
            
            # Activity pattern detection
            activity_patterns = await self._detect_activity_patterns(analysis_data)
            detected_patterns.extend(activity_patterns)
            
            # Communication pattern detection
            communication_patterns = await self._detect_communication_patterns(analysis_data)
            detected_patterns.extend(communication_patterns)
            
            # Filter and rank patterns by strength
            filtered_patterns = await self._filter_and_rank_patterns(detected_patterns)
            
            # Store detected patterns
            for pattern in filtered_patterns:
                self.detected_patterns[pattern.id] = pattern
            
            # Update statistics
            self.analysis_stats['patterns_detected'] += len(filtered_patterns)
            processing_time = asyncio.get_event_loop().time() - start_time
            self.analysis_stats['processing_times'].append(processing_time)
            
            self.logger.info(f"Detected {len(filtered_patterns)} patterns from {len(memories)} memories")
            
            return [asdict(pattern) for pattern in filtered_patterns]
            
        except Exception as e:
            self.logger.error(f"Pattern analysis failed: {e}")
            return []
    
    async def _detect_temporal_patterns(self, analysis_data: Dict[str, Any]) -> List[DetectedPattern]:
        """Detect time-based patterns in user behavior"""
        
        patterns = []
        
        try:
            # Extract temporal features
            temporal_data = analysis_data.get('temporal_features', [])
            
            if not temporal_data:
                return patterns
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(temporal_data)
            
            # Daily patterns
            daily_patterns = await self._analyze_daily_patterns(df)
            patterns.extend(daily_patterns)
            
            # Weekly patterns
            weekly_patterns = await self._analyze_weekly_patterns(df)
            patterns.extend(weekly_patterns)
            
            # Hourly patterns
            hourly_patterns = await self._analyze_hourly_patterns(df)
            patterns.extend(hourly_patterns)
            
            # Seasonal patterns
            seasonal_patterns = await self._analyze_seasonal_patterns(df)
            patterns.extend(seasonal_patterns)
            
        except Exception as e:
            self.logger.error(f"Temporal pattern detection failed: {e}")
        
        return patterns
    
    async def _analyze_daily_patterns(self, df: pd.DataFrame) -> List[DetectedPattern]:
        """Analyze daily behavioral patterns"""
        
        patterns = []
        
        try:
            # Group by day of week
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.day_name()
            daily_groups = df.groupby('day_of_week')
            
            for day, group in daily_groups:
                if len(group) < 3:  # Need minimum occurrences
                    continue
                
                # Analyze activities for this day
                activities = group['activity'].value_counts()
                
                for activity, count in activities.items():
                    if count >= 3:  # Minimum frequency
                        
                        # Calculate pattern strength
                        total_days = len(group['timestamp'].dt.date.unique())
                        frequency = count / total_days if total_days > 0 else 0
                        
                        if frequency >= 0.3:  # Minimum pattern strength
                            
                            # Extract time windows
                            activity_times = group[group['activity'] == activity]['timestamp']
                            time_windows = self._extract_time_windows(activity_times)
                            
                            # Create pattern
                            pattern = DetectedPattern(
                                id=f"daily_{day}_{activity}_{hashlib.md5(f'{day}{activity}'.encode()).hexdigest()[:8]}",
                                pattern_type=PatternType.TEMPORAL,
                                strength=self._calculate_pattern_strength(frequency),
                                confidence=min(frequency, 0.95),
                                description=f"User typically does '{activity}' on {day}s",
                                frequency={'type': 'daily', 'day': day, 'rate': frequency},
                                triggers=[f"day_of_week:{day}"],
                                participants=list(group['participants'].explode().unique()) if 'participants' in group.columns else [],
                                locations=list(group['location'].unique()) if 'location' in group.columns else [],
                                time_windows=time_windows,
                                supporting_memories=list(group['memory_id'].unique()) if 'memory_id' in group.columns else [],
                                first_detected=datetime.now(),
                                last_updated=datetime.now(),
                                prediction_accuracy=0.0,  # Will be updated with feedback
                                metadata={'day_of_week': day, 'activity': activity, 'sample_size': count}
                            )
                            
                            patterns.append(pattern)
            
        except Exception as e:
            self.logger.error(f"Daily pattern analysis failed: {e}")
        
        return patterns
    
    async def _analyze_weekly_patterns(self, df: pd.DataFrame) -> List[DetectedPattern]:
        """Analyze weekly behavioral patterns"""
        
        patterns = []
        
        try:
            # Group by week
            df['week'] = pd.to_datetime(df['timestamp']).dt.isocalendar().week
            df['year'] = pd.to_datetime(df['timestamp']).dt.year
            df['year_week'] = df['year'].astype(str) + '_' + df['week'].astype(str)
            
            weekly_groups = df.groupby('year_week')
            
            # Analyze recurring weekly activities
            weekly_activities = defaultdict(list)
            
            for week, group in weekly_groups:
                activities = group['activity'].value_counts()
                for activity, count in activities.items():
                    weekly_activities[activity].append(count)
            
            # Identify consistent weekly patterns
            for activity, counts in weekly_activities.items():
                if len(counts) >= 3:  # Need multiple weeks of data
                    
                    avg_count = statistics.mean(counts)
                    consistency = 1 - (statistics.stdev(counts) / avg_count) if avg_count > 0 else 0
                    
                    if consistency >= 0.6 and avg_count >= 2:  # Consistent weekly pattern
                        
                        # Create weekly pattern
                        pattern = DetectedPattern(
                            id=f"weekly_{activity}_{hashlib.md5(activity.encode()).hexdigest()[:8]}",
                            pattern_type=PatternType.TEMPORAL,
                            strength=self._calculate_pattern_strength(consistency),
                            confidence=min(consistency, 0.95),
                            description=f"User regularly does '{activity}' weekly",
                            frequency={'type': 'weekly', 'avg_count': avg_count, 'consistency': consistency},
                            triggers=["weekly_cycle"],
                            participants=[],
                            locations=[],
                            time_windows=[],
                            supporting_memories=[],
                            first_detected=datetime.now(),
                            last_updated=datetime.now(),
                            prediction_accuracy=0.0,
                            metadata={'activity': activity, 'weekly_average': avg_count, 'weeks_analyzed': len(counts)}
                        )
                        
                        patterns.append(pattern)
            
        except Exception as e:
            self.logger.error(f"Weekly pattern analysis failed: {e}")
        
        return patterns
    
    async def _analyze_hourly_patterns(self, df: pd.DataFrame) -> List[DetectedPattern]:
        """Analyze hourly behavioral patterns"""
        
        patterns = []
        
        try:
            # Extract hour from timestamp
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            
            # Group by hour
            hourly_groups = df.groupby('hour')
            
            for hour, group in hourly_groups:
                if len(group) < 5:  # Need minimum occurrences
                    continue
                
                # Analyze activities for this hour
                activities = group['activity'].value_counts()
                
                for activity, count in activities.items():
                    if count >= 3:  # Minimum frequency
                        
                        # Calculate pattern strength
                        total_hours = len(group)
                        frequency = count / total_hours if total_hours > 0 else 0
                        
                        if frequency >= 0.4:  # Minimum pattern strength for hourly
                            
                            # Create hourly pattern
                            pattern = DetectedPattern(
                                id=f"hourly_{hour}_{activity}_{hashlib.md5(f'{hour}{activity}'.encode()).hexdigest()[:8]}",
                                pattern_type=PatternType.TEMPORAL,
                                strength=self._calculate_pattern_strength(frequency),
                                confidence=min(frequency, 0.95),
                                description=f"User typically does '{activity}' around {hour}:00",
                                frequency={'type': 'hourly', 'hour': hour, 'rate': frequency},
                                triggers=[f"hour:{hour}"],
                                participants=[],
                                locations=[],
                                time_windows=[{'start_hour': hour, 'end_hour': (hour + 1) % 24}],
                                supporting_memories=[],
                                first_detected=datetime.now(),
                                last_updated=datetime.now(),
                                prediction_accuracy=0.0,
                                metadata={'hour': hour, 'activity': activity, 'sample_size': count}
                            )
                            
                            patterns.append(pattern)
            
        except Exception as e:
            self.logger.error(f"Hourly pattern analysis failed: {e}")
        
        return patterns
    
    async def _detect_behavioral_patterns(self, analysis_data: Dict[str, Any]) -> List[DetectedPattern]:
        """Detect behavioral patterns in user activities"""
        
        patterns = []
        
        try:
            # Extract behavioral features
            behavioral_data = analysis_data.get('behavioral_features', [])
            
            if not behavioral_data:
                return patterns
            
            # Convert to DataFrame
            df = pd.DataFrame(behavioral_data)
            
            # Activity sequence patterns
            sequence_patterns = await self._analyze_activity_sequences(df)
            patterns.extend(sequence_patterns)
            
            # Trigger-response patterns
            trigger_patterns = await self._analyze_trigger_response_patterns(df)
            patterns.extend(trigger_patterns)
            
            # Context-dependent patterns
            context_patterns = await self._analyze_context_dependent_patterns(df)
            patterns.extend(context_patterns)
            
        except Exception as e:
            self.logger.error(f"Behavioral pattern detection failed: {e}")
        
        return patterns
    
    async def _analyze_activity_sequences(self, df: pd.DataFrame) -> List[DetectedPattern]:
        """Analyze sequences of activities to find behavioral patterns"""
        
        patterns = []
        
        try:
            # Sort by timestamp
            df_sorted = df.sort_values('timestamp')
            
            # Extract activity sequences
            sequences = []
            current_sequence = []
            last_timestamp = None
            
            for _, row in df_sorted.iterrows():
                current_time = pd.to_datetime(row['timestamp'])
                
                if last_timestamp is None or (current_time - last_timestamp).total_seconds() <= 3600:  # 1 hour window
                    current_sequence.append(row['activity'])
                else:
                    if len(current_sequence) >= 2:
                        sequences.append(current_sequence.copy())
                    current_sequence = [row['activity']]
                
                last_timestamp = current_time
            
            # Add final sequence
            if len(current_sequence) >= 2:
                sequences.append(current_sequence)
            
            # Find common sequences
            sequence_counts = Counter()
            for seq in sequences:
                for i in range(len(seq) - 1):
                    pair = (seq[i], seq[i + 1])
                    sequence_counts[pair] += 1
            
            # Create patterns for frequent sequences
            total_sequences = len(sequences)
            for (activity1, activity2), count in sequence_counts.items():
                if count >= 3:  # Minimum occurrences
                    frequency = count / total_sequences if total_sequences > 0 else 0
                    
                    if frequency >= 0.2:  # Minimum pattern strength
                        
                        pattern = DetectedPattern(
                            id=f"sequence_{activity1}_{activity2}_{hashlib.md5(f'{activity1}{activity2}'.encode()).hexdigest()[:8]}",
                            pattern_type=PatternType.BEHAVIORAL,
                            strength=self._calculate_pattern_strength(frequency),
                            confidence=min(frequency, 0.95),
                            description=f"User typically does '{activity2}' after '{activity1}'",
                            frequency={'type': 'sequence', 'rate': frequency, 'count': count},
                            triggers=[f"activity:{activity1}"],
                            participants=[],
                            locations=[],
                            time_windows=[],
                            supporting_memories=[],
                            first_detected=datetime.now(),
                            last_updated=datetime.now(),
                            prediction_accuracy=0.0,
                            metadata={'sequence': [activity1, activity2], 'sample_size': count}
                        )
                        
                        patterns.append(pattern)
            
        except Exception as e:
            self.logger.error(f"Activity sequence analysis failed: {e}")
        
        return patterns
    
    async def _detect_social_patterns(self, analysis_data: Dict[str, Any]) -> List[DetectedPattern]:
        """Detect social interaction patterns"""
        
        patterns = []
        
        try:
            # Extract social features
            social_data = analysis_data.get('social_features', [])
            
            if not social_data:
                return patterns
            
            # Convert to DataFrame
            df = pd.DataFrame(social_data)
            
            # Analyze interaction frequencies
            if 'participants' in df.columns:
                # Flatten participants list
                all_participants = []
                for participants in df['participants']:
                    if isinstance(participants, list):
                        all_participants.extend(participants)
                    elif participants:
                        all_participants.append(participants)
                
                # Count interactions
                participant_counts = Counter(all_participants)
                
                # Create social patterns
                total_interactions = len(df)
                for participant, count in participant_counts.items():
                    if count >= 3:  # Minimum interactions
                        frequency = count / total_interactions if total_interactions > 0 else 0
                        
                        if frequency >= 0.1:  # Minimum social pattern strength
                            
                            # Analyze interaction contexts
                            participant_data = df[df['participants'].apply(
                                lambda x: participant in x if isinstance(x, list) else participant == x
                            )]
                            
                            common_activities = participant_data['activity'].value_counts().head(3).to_dict()
                            
                            pattern = DetectedPattern(
                                id=f"social_{participant}_{hashlib.md5(participant.encode()).hexdigest()[:8]}",
                                pattern_type=PatternType.SOCIAL,
                                strength=self._calculate_pattern_strength(frequency),
                                confidence=min(frequency, 0.95),
                                description=f"User frequently interacts with {participant}",
                                frequency={'type': 'social', 'rate': frequency, 'count': count},
                                triggers=[],
                                participants=[participant],
                                locations=[],
                                time_windows=[],
                                supporting_memories=[],
                                first_detected=datetime.now(),
                                last_updated=datetime.now(),
                                prediction_accuracy=0.0,
                                metadata={
                                    'participant': participant,
                                    'interaction_count': count,
                                    'common_activities': common_activities
                                }
                            )
                            
                            patterns.append(pattern)
            
        except Exception as e:
            self.logger.error(f"Social pattern detection failed: {e}")
        
        return patterns
    
    async def _detect_emotional_patterns(self, analysis_data: Dict[str, Any]) -> List[DetectedPattern]:
        """Detect emotional state patterns"""
        
        patterns = []
        
        try:
            # Extract emotional features
            emotional_data = analysis_data.get('emotional_features', [])
            
            if not emotional_data:
                return patterns
            
            # Convert to DataFrame
            df = pd.DataFrame(emotional_data)
            
            if 'sentiment' not in df.columns:
                return patterns
            
            # Analyze emotional trends
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.day_name()
            
            # Hourly emotional patterns
            hourly_sentiment = df.groupby('hour')['sentiment'].mean()
            
            for hour, avg_sentiment in hourly_sentiment.items():
                if abs(avg_sentiment) >= 0.3:  # Significant emotional pattern
                    
                    sentiment_label = "positive" if avg_sentiment > 0 else "negative"
                    strength = abs(avg_sentiment)
                    
                    pattern = DetectedPattern(
                        id=f"emotional_hourly_{hour}_{sentiment_label}_{hashlib.md5(f'{hour}{sentiment_label}'.encode()).hexdigest()[:8]}",
                        pattern_type=PatternType.EMOTIONAL,
                        strength=self._calculate_pattern_strength(strength),
                        confidence=min(strength, 0.95),
                        description=f"User tends to be {sentiment_label} around {hour}:00",
                        frequency={'type': 'hourly_emotional', 'hour': hour, 'avg_sentiment': avg_sentiment},
                        triggers=[f"hour:{hour}"],
                        participants=[],
                        locations=[],
                        time_windows=[{'start_hour': hour, 'end_hour': (hour + 1) % 24}],
                        supporting_memories=[],
                        first_detected=datetime.now(),
                        last_updated=datetime.now(),
                        prediction_accuracy=0.0,
                        metadata={'hour': hour, 'sentiment': sentiment_label, 'avg_score': avg_sentiment}
                    )
                    
                    patterns.append(pattern)
            
            # Daily emotional patterns
            daily_sentiment = df.groupby('day_of_week')['sentiment'].mean()
            
            for day, avg_sentiment in daily_sentiment.items():
                if abs(avg_sentiment) >= 0.2:  # Significant daily emotional pattern
                    
                    sentiment_label = "positive" if avg_sentiment > 0 else "negative"
                    strength = abs(avg_sentiment)
                    
                    pattern = DetectedPattern(
                        id=f"emotional_daily_{day}_{sentiment_label}_{hashlib.md5(f'{day}{sentiment_label}'.encode()).hexdigest()[:8]}",
                        pattern_type=PatternType.EMOTIONAL,
                        strength=self._calculate_pattern_strength(strength),
                        confidence=min(strength, 0.95),
                        description=f"User tends to be {sentiment_label} on {day}s",
                        frequency={'type': 'daily_emotional', 'day': day, 'avg_sentiment': avg_sentiment},
                        triggers=[f"day_of_week:{day}"],
                        participants=[],
                        locations=[],
                        time_windows=[],
                        supporting_memories=[],
                        first_detected=datetime.now(),
                        last_updated=datetime.now(),
                        prediction_accuracy=0.0,
                        metadata={'day': day, 'sentiment': sentiment_label, 'avg_score': avg_sentiment}
                    )
                    
                    patterns.append(pattern)
            
        except Exception as e:
            self.logger.error(f"Emotional pattern detection failed: {e}")
        
        return patterns
    
    # ==================== HABIT IDENTIFICATION ====================
    
    async def _identify_habits_from_data(self, behavioral_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify behavioral habits from pattern data"""
        
        if not behavioral_data:
            return []
        
        try:
            # Extract habit candidates from patterns
            habit_candidates = await self._extract_habit_candidates(behavioral_data)
            
            # Analyze habit strength and consistency
            validated_habits = await self._validate_habit_candidates(habit_candidates)
            
            # Create habit models
            behavioral_habits = []
            for habit_data in validated_habits:
                habit = await self._create_behavioral_habit(habit_data)
                if habit:
                    self.behavioral_habits[habit.id] = habit
                    behavioral_habits.append(asdict(habit))
            
            # Update statistics
            self.analysis_stats['habits_identified'] += len(behavioral_habits)
            
            self.logger.info(f"Identified {len(behavioral_habits)} behavioral habits")
            
            return behavioral_habits
            
        except Exception as e:
            self.logger.error(f"Habit identification failed: {e}")
            return []
    
    async def _extract_habit_candidates(self, behavioral_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract potential habits from behavioral data"""
        
        candidates = []
        
        try:
            # Look for recurring patterns that could be habits
            patterns = behavioral_data.get('patterns', [])
            
            for pattern in patterns:
                # Check if pattern has habit-like characteristics
                if self._is_habit_like_pattern(pattern):
                    candidate = {
                        'pattern_id': pattern.get('id'),
                        'activity': pattern.get('description', '').split("'")[1] if "'" in pattern.get('description', '') else '',
                        'frequency': pattern.get('frequency', {}),
                        'strength': pattern.get('strength'),
                        'triggers': pattern.get('triggers', []),
                        'supporting_data': pattern
                    }
                    candidates.append(candidate)
            
        except Exception as e:
            self.logger.error(f"Habit candidate extraction failed: {e}")
        
        return candidates
    
    def _is_habit_like_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Determine if a pattern has habit-like characteristics"""
        
        try:
            # Check pattern strength
            strength = pattern.get('strength', '')
            if strength not in ['strong', 'very_strong']:
                return False
            
            # Check frequency consistency
            frequency = pattern.get('frequency', {})
            freq_type = frequency.get('type', '')
            
            # Habits are typically daily, weekly, or triggered
            if freq_type in ['daily', 'weekly', 'hourly']:
                rate = frequency.get('rate', 0)
                return rate >= 0.5  # At least 50% consistency
            
            return False
            
        except Exception:
            return False
    
    # ==================== ROUTINE PREDICTION ====================
    
    async def _predict_routines(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict future routines based on patterns and context"""
        
        predictions = []
        
        try:
            # Get current context
            current_time = datetime.now()
            current_context = {
                'hour': current_time.hour,
                'day_of_week': current_time.strftime('%A'),
                'date': current_time.date(),
                **context_data
            }
            
            # Predict based on temporal patterns
            temporal_predictions = await self._predict_from_temporal_patterns(current_context)
            predictions.extend(temporal_predictions)
            
            # Predict based on behavioral patterns
            behavioral_predictions = await self._predict_from_behavioral_patterns(current_context)
            predictions.extend(behavioral_predictions)
            
            # Predict based on habits
            habit_predictions = await self._predict_from_habits(current_context)
            predictions.extend(habit_predictions)
            
            # Rank and filter predictions
            ranked_predictions = await self._rank_predictions(predictions)
            
            # Store predictions
            for prediction in ranked_predictions:
                self.routine_predictions[prediction.id] = prediction
            
            # Update statistics
            self.analysis_stats['predictions_made'] += len(ranked_predictions)
            
            self.logger.info(f"Generated {len(ranked_predictions)} routine predictions")
            
            return [asdict(pred) for pred in ranked_predictions]
            
        except Exception as e:
            self.logger.error(f"Routine prediction failed: {e}")
            return []
    
    # ==================== INSIGHT GENERATION ====================
    
    async def _generate_behavioral_insights(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate behavioral insights from patterns and habits"""
        
        insights = []
        
        try:
            # Productivity insights
            productivity_insights = await self._generate_productivity_insights(analysis_data)
            insights.extend(productivity_insights)
            
            # Social insights
            social_insights = await self._generate_social_insights(analysis_data)
            insights.extend(social_insights)
            
            # Wellness insights
            wellness_insights = await self._generate_wellness_insights(analysis_data)
            insights.extend(wellness_insights)
            
            # Time management insights
            time_insights = await self._generate_time_management_insights(analysis_data)
            insights.extend(time_insights)
            
            # Habit insights
            habit_insights = await self._generate_habit_insights(analysis_data)
            insights.extend(habit_insights)
            
            # Store insights
            for insight in insights:
                self.behavioral_insights[insight.id] = insight
            
            # Update statistics
            self.analysis_stats['insights_generated'] += len(insights)
            
            self.logger.info(f"Generated {len(insights)} behavioral insights")
            
            return [asdict(insight) for insight in insights]
            
        except Exception as e:
            self.logger.error(f"Insight generation failed: {e}")
            return []
    
    # ==================== UTILITY METHODS ====================
    
    def _calculate_pattern_strength(self, frequency: float) -> PatternStrength:
        """Calculate pattern strength based on frequency"""
        
        if frequency >= 0.85:
            return PatternStrength.VERY_STRONG
        elif frequency >= 0.7:
            return PatternStrength.STRONG
        elif frequency >= 0.5:
            return PatternStrength.MODERATE
        else:
            return PatternStrength.WEAK
    
    def _extract_time_windows(self, timestamps) -> List[Dict[str, Any]]:
        """Extract time windows from timestamps"""
        
        try:
            times = pd.to_datetime(timestamps)
            hours = times.dt.hour
            
            if len(hours) == 0:
                return []
            
            # Find common time ranges
            hour_counts = Counter(hours)
            common_hours = [hour for hour, count in hour_counts.items() if count >= 2]
            
            windows = []
            for hour in common_hours:
                windows.append({
                    'start_hour': hour,
                    'end_hour': (hour + 1) % 24,
                    'frequency': hour_counts[hour]
                })
            
            return windows
            
        except Exception:
            return []
    
    async def _prepare_memory_data_for_analysis(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare memory data for pattern analysis"""
        
        analysis_data = {
            'temporal_features': [],
            'behavioral_features': [],
            'social_features': [],
            'emotional_features': [],
            'location_features': [],
            'activity_features': []
        }
        
        try:
            for memory in memories:
                # Extract temporal features
                temporal_feature = {
                    'memory_id': memory.get('id', ''),
                    'timestamp': memory.get('timestamp', ''),
                    'activity': memory.get('content', '')[:50],  # First 50 chars as activity
                    'participants': memory.get('participants', []),
                    'location': memory.get('metadata', {}).get('location', ''),
                }
                analysis_data['temporal_features'].append(temporal_feature)
                
                # Extract behavioral features
                behavioral_feature = {
                    'memory_id': memory.get('id', ''),
                    'timestamp': memory.get('timestamp', ''),
                    'activity': memory.get('content', '')[:50],
                    'tags': memory.get('tags', []),
                    'quality_score': memory.get('quality_score', 0),
                }
                analysis_data['behavioral_features'].append(behavioral_feature)
                
                # Extract social features
                social_feature = {
                    'memory_id': memory.get('id', ''),
                    'timestamp': memory.get('timestamp', ''),
                    'participants': memory.get('participants', []),
                    'activity': memory.get('content', '')[:50],
                }
                analysis_data['social_features'].append(social_feature)
                
                # Extract emotional features
                sentiment_data = memory.get('sentiment', {})
                emotional_feature = {
                    'memory_id': memory.get('id', ''),
                    'timestamp': memory.get('timestamp', ''),
                    'sentiment': sentiment_data.get('score', 0),
                    'emotion': sentiment_data.get('label', 'neutral'),
                }
                analysis_data['emotional_features'].append(emotional_feature)
            
        except Exception as e:
            self.logger.error(f"Data preparation failed: {e}")
        
        return analysis_data
    
    async def _filter_and_rank_patterns(self, patterns: List[DetectedPattern]) -> List[DetectedPattern]:
        """Filter and rank detected patterns by relevance and strength"""
        
        try:
            # Filter by minimum strength
            min_strength = self.analysis_config.get('min_pattern_strength', 0.3)
            filtered = [p for p in patterns if p.confidence >= min_strength]
            
            # Remove duplicates
            unique_patterns = {}
            for pattern in filtered:
                key = f"{pattern.pattern_type.value}_{pattern.description}"
                if key not in unique_patterns or pattern.confidence > unique_patterns[key].confidence:
                    unique_patterns[key] = pattern
            
            # Sort by confidence and strength
            ranked = sorted(
                unique_patterns.values(),
                key=lambda p: (p.confidence, p.strength.value),
                reverse=True
            )
            
            return ranked[:50]  # Limit to top 50 patterns
            
        except Exception as e:
            self.logger.error(f"Pattern filtering failed: {e}")
            return patterns
    
    async def _get_pattern_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pattern analysis statistics"""
        
        try:
            # Pattern type distribution
            pattern_types = Counter([p.pattern_type.value for p in self.detected_patterns.values()])
            
            # Strength distribution
            strength_dist = Counter([p.strength.value for p in self.detected_patterns.values()])
            
            # Average confidence
            confidences = [p.confidence for p in self.detected_patterns.values()]
            avg_confidence = statistics.mean(confidences) if confidences else 0
            
            # Processing performance
            avg_processing_time = statistics.mean(self.analysis_stats['processing_times']) if self.analysis_stats['processing_times'] else 0
            
            return {
                'total_patterns': len(self.detected_patterns),
                'total_habits': len(self.behavioral_habits),
                'total_predictions': len(self.routine_predictions),
                'total_insights': len(self.behavioral_insights),
                'pattern_type_distribution': dict(pattern_types),
                'strength_distribution': dict(strength_dist),
                'average_confidence': avg_confidence,
                'average_processing_time': avg_processing_time,
                'analysis_stats': self.analysis_stats
            }
            
        except Exception as e:
            self.logger.error(f"Statistics calculation failed: {e}")
            return {}
    
    def _create_error_response(self, original_message: AgentMessage, error_msg: str) -> AgentMessage:
        """Create error response message"""
        
        return AgentMessage(
            id=f"error_{original_message.id}",
            type="error_response",
            sender_id=self.agent_id,
            recipient_id=original_message.sender_id,
            payload={
                "error": error_msg,
                "original_message_type": original_message.type,
                "recoverable": True
            },
            timestamp=asyncio.get_event_loop().time()
        )
    
    # ==================== INITIALIZATION METHODS ====================
    
    async def _initialize_pattern_detectors(self):
        """Initialize pattern detection components"""
        
        self.pattern_detectors = {
            'temporal': TemporalPatternDetector(),
            'behavioral': BehavioralPatternDetector(),
            'social': SocialPatternDetector(),
            'emotional': EmotionalPatternDetector(),
            'location': LocationPatternDetector(),
            'activity': ActivityPatternDetector(),
            'communication': CommunicationPatternDetector()
        }
        
        for detector in self.pattern_detectors.values():
            await detector.initialize()
    
    async def _initialize_habit_analyzers(self):
        """Initialize habit analysis components"""
        
        self.habit_analyzers = {
            'daily': DailyHabitAnalyzer(),
            'weekly': WeeklyHabitAnalyzer(),
            'triggered': TriggeredHabitAnalyzer()
        }
        
        for analyzer in self.habit_analyzers.values():
            await analyzer.initialize()
    
    async def _initialize_routine_predictors(self):
        """Initialize routine prediction components"""
        
        self.routine_predictors = {
            'temporal': TemporalRoutinePredictor(),
            'behavioral': BehavioralRoutinePredictor(),
            'contextual': ContextualRoutinePredictor()
        }
        
        for predictor in self.routine_predictors.values():
            await predictor.initialize()
    
    async def _initialize_insight_generators(self):
        """Initialize insight generation components"""
        
        self.insight_generators = {
            'productivity': ProductivityInsightGenerator(),
            'social': SocialInsightGenerator(),
            'wellness': WellnessInsightGenerator(),
            'time_management': TimeManagementInsightGenerator()
        }
        
        for generator in self.insight_generators.values():
            await generator.initialize()
    
    async def _initialize_analysis_engines(self):
        """Initialize analysis engines"""
        
        self.temporal_analyzer = TemporalAnalysisEngine()
        self.behavioral_analyzer = BehavioralAnalysisEngine()
        self.social_analyzer = SocialAnalysisEngine()
        self.emotional_analyzer = EmotionalAnalysisEngine()
        self.activity_analyzer = ActivityAnalysisEngine()
        
        # Initialize all engines
        engines = [
            self.temporal_analyzer,
            self.behavioral_analyzer,
            self.social_analyzer,
            self.emotional_analyzer,
            self.activity_analyzer
        ]
        
        for engine in engines:
            if engine:
                await engine.initialize()
    
    async def _load_existing_data(self):
        """Load existing patterns, habits, and insights from storage"""
        
        try:
            # This would load from persistent storage
            # For now, we'll start with empty collections
            self.detected_patterns = {}
            self.behavioral_habits = {}
            self.routine_predictions = {}
            self.behavioral_insights = {}
            
            self.logger.info("Existing data loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing data: {e}")
    
    async def shutdown(self):
        """Shutdown the Pattern Analyzer Agent gracefully"""
        
        try:
            # Save current state
            await self._save_analysis_state()
            
            # Shutdown components
            for detector in self.pattern_detectors.values():
                if hasattr(detector, 'shutdown'):
                    await detector.shutdown()
            
            for analyzer in self.habit_analyzers.values():
                if hasattr(analyzer, 'shutdown'):
                    await analyzer.shutdown()
            
            # Call parent shutdown
            await super().shutdown()
            
            self.logger.info("Pattern Analyzer Agent shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Shutdown error: {e}")
    
    async def _save_analysis_state(self):
        """Save current analysis state to persistent storage"""
        
        try:
            # This would save to persistent storage
            # Implementation depends on storage backend
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis state: {e}")


# ==================== HELPER CLASSES ====================

class TemporalPatternDetector:
    """Specialized detector for temporal patterns"""
    
    async def initialize(self):
        pass

class BehavioralPatternDetector:
    """Specialized detector for behavioral patterns"""
    
    async def initialize(self):
        pass

class SocialPatternDetector:
    """Specialized detector for social patterns"""
    
    async def initialize(self):
        pass

class EmotionalPatternDetector:
    """Specialized detector for emotional patterns"""
    
    async def initialize(self):
        pass

class LocationPatternDetector:
    """Specialized detector for location patterns"""
    
    async def initialize(self):
        pass

class ActivityPatternDetector:
    """Specialized detector for activity patterns"""
    
    async def initialize(self):
        pass

class CommunicationPatternDetector:
    """Specialized detector for communication patterns"""
    
    async def initialize(self):
        pass

class DailyHabitAnalyzer:
    """Analyzer for daily habits"""
    
    async def initialize(self):
        pass

class WeeklyHabitAnalyzer:
    """Analyzer for weekly habits"""
    
    async def initialize(self):
        pass

class TriggeredHabitAnalyzer:
    """Analyzer for triggered habits"""
    
    async def initialize(self):
        pass

class TemporalRoutinePredictor:
    """Predictor for temporal routines"""
    
    async def initialize(self):
        pass

class BehavioralRoutinePredictor:
    """Predictor for behavioral routines"""
    
    async def initialize(self):
        pass

class ContextualRoutinePredictor:
    """Predictor for contextual routines"""
    
    async def initialize(self):
        pass

class ProductivityInsightGenerator:
    """Generator for productivity insights"""
    
    async def initialize(self):
        pass

class SocialInsightGenerator:
    """Generator for social insights"""
    
    async def initialize(self):
        pass

class WellnessInsightGenerator:
    """Generator for wellness insights"""
    
    async def initialize(self):
        pass

class TimeManagementInsightGenerator:
    """Generator for time management insights"""
    
    async def initialize(self):
        pass

class TemporalAnalysisEngine:
    """Engine for temporal analysis"""
    
    async def initialize(self):
        pass

class BehavioralAnalysisEngine:
    """Engine for behavioral analysis"""
    
    async def initialize(self):
        pass

class SocialAnalysisEngine:
    """Engine for social analysis"""
    
    async def initialize(self):
        pass

class EmotionalAnalysisEngine:
    """Engine for emotional analysis"""
    
    async def initialize(self):
        pass

class ActivityAnalysisEngine:
    """Engine for activity analysis"""
    
    async def initialize(self):
        pass

