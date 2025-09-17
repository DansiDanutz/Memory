#!/usr/bin/env python3
"""
Memory Gaming Service - Gamification and Addiction Mechanics
Creates engaging, addictive games using shared memories between users
"""

import os
import json
import random
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
import logging
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
from enum import Enum
import uuid
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Game Types
class GameType(Enum):
    """Types of memory games available"""
    MEMORY_MATCH = "memory_match"           # Match shared memories between friends
    MEMORY_TIMELINE = "memory_timeline"     # Arrange memories in correct order
    GUESS_WHO = "guess_who"                 # Guess which friend shared which memory
    MEMORY_TELEPHONE = "memory_telephone"   # Pass memories between friends
    TRUTH_OR_MEMORY = "truth_or_memory"    # Share truth or reveal memory
    MEMORY_BATTLES = "memory_battles"       # Compete on memory knowledge
    DAILY_CHALLENGE = "daily_challenge"     # Daily memory challenges
    SPEED_RECALL = "speed_recall"           # Fast memory recall game
    MEMORY_TRIVIA = "memory_trivia"        # Trivia about shared memories
    EMOTIONAL_MATCH = "emotional_match"     # Match memories by emotion

class GameStatus(Enum):
    """Status of a game session"""
    WAITING = "waiting"          # Waiting for players
    IN_PROGRESS = "in_progress"  # Game active
    COMPLETED = "completed"      # Game finished
    ABANDONED = "abandoned"      # Game abandoned
    PAUSED = "paused"           # Game paused

class AchievementCategory(Enum):
    """Categories of gaming achievements"""
    GAMES_PLAYED = "games_played"
    GAMES_WON = "games_won"
    STREAKS = "streaks"
    SOCIAL = "social"
    MASTERY = "mastery"
    SPECIAL = "special"
    COLLECTOR = "collector"
    SPEED = "speed"

class RewardType(Enum):
    """Types of rewards for gaming"""
    POINTS = "points"
    BADGES = "badges"
    MEMORY_CREDITS = "memory_credits"
    UNLOCK_FEATURES = "unlock_features"
    COSMETIC = "cosmetic"
    TITLE = "title"
    BOOST = "boost"

class NotificationPriority(Enum):
    """Priority levels for gaming notifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

@dataclass
class GameSession:
    """Represents a game session between users"""
    id: str
    game_type: GameType
    creator_id: str
    players: List[str]
    status: GameStatus
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Game state
    current_round: int = 0
    max_rounds: int = 10
    turn_order: List[str] = field(default_factory=list)
    current_turn: int = 0
    
    # Scoring
    scores: Dict[str, int] = field(default_factory=dict)
    moves: List[Dict[str, Any]] = field(default_factory=list)
    
    # Game-specific data
    game_data: Dict[str, Any] = field(default_factory=dict)
    
    # Settings
    time_limit: Optional[int] = None  # Seconds per turn
    is_public: bool = False
    allow_spectators: bool = True
    
    # Rewards
    winner_id: Optional[str] = None
    rewards_distributed: bool = False
    
    def get_current_player(self) -> Optional[str]:
        """Get the current player's turn"""
        if self.turn_order and self.status == GameStatus.IN_PROGRESS:
            return self.turn_order[self.current_turn % len(self.turn_order)]
        return None
    
    def next_turn(self):
        """Move to next turn"""
        self.current_turn += 1
        if self.current_turn >= len(self.turn_order) * self.max_rounds:
            self.status = GameStatus.COMPLETED

@dataclass
class PlayerStats:
    """Player gaming statistics"""
    user_id: str
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    games_abandoned: int = 0
    
    # Points and levels
    total_points: int = 0
    current_level: int = 1
    experience_points: int = 0
    next_level_xp: int = 100
    
    # Streaks
    current_streak: int = 0
    longest_streak: int = 0
    last_game_date: Optional[datetime] = None
    
    # Performance
    win_rate: float = 0.0
    average_score: float = 0.0
    fastest_win_time: Optional[int] = None  # Seconds
    
    # Social
    unique_opponents: Set[str] = field(default_factory=set)
    favorite_opponent: Optional[str] = None
    total_friends_challenged: int = 0
    
    # Achievements
    achievements_unlocked: List[str] = field(default_factory=list)
    badges_earned: List[str] = field(default_factory=list)
    titles_earned: List[str] = field(default_factory=list)
    
    # Game preferences
    favorite_game_type: Optional[GameType] = None
    play_times: List[int] = field(default_factory=list)  # Hours of day
    
    def update_stats(self, game_result: str, score: int, opponent_id: str):
        """Update player stats after a game"""
        self.games_played += 1
        
        if game_result == "won":
            self.games_won += 1
            self.current_streak += 1
            self.longest_streak = max(self.longest_streak, self.current_streak)
        elif game_result == "lost":
            self.games_lost += 1
            self.current_streak = 0
        elif game_result == "abandoned":
            self.games_abandoned += 1
            self.current_streak = 0
        
        # Update win rate
        if self.games_played > 0:
            self.win_rate = self.games_won / self.games_played
        
        # Track opponents
        self.unique_opponents.add(opponent_id)
        
        # Update XP
        xp_gained = score // 10
        if game_result == "won":
            xp_gained *= 2
        
        self.experience_points += xp_gained
        self.total_points += score
        
        # Level up check
        while self.experience_points >= self.next_level_xp:
            self.current_level += 1
            self.experience_points -= self.next_level_xp
            self.next_level_xp = int(self.next_level_xp * 1.5)
        
        self.last_game_date = datetime.now()

@dataclass
class DailyChallenge:
    """Daily challenge for all users"""
    id: str
    date: datetime
    challenge_type: GameType
    title: str
    description: str
    target_score: int
    
    # Participants
    participants: List[str] = field(default_factory=list)
    completions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Rewards
    base_reward: int = 100
    bonus_reward: int = 50
    
    # Leaderboard
    leaderboard: List[Tuple[str, int]] = field(default_factory=list)
    
    # Time limits
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=1))
    
    def is_active(self) -> bool:
        """Check if challenge is still active"""
        now = datetime.now()
        return self.start_time <= now <= self.end_time
    
    def add_completion(self, user_id: str, score: int, time_taken: int):
        """Add user completion"""
        self.completions[user_id] = {
            'score': score,
            'time_taken': time_taken,
            'completed_at': datetime.now()
        }
        
        # Update leaderboard
        self.leaderboard.append((user_id, score))
        self.leaderboard.sort(key=lambda x: x[1], reverse=True)
        self.leaderboard = self.leaderboard[:100]  # Keep top 100

@dataclass
class Achievement:
    """Gaming achievement definition"""
    id: str
    name: str
    description: str
    category: AchievementCategory
    icon: str
    points: int
    
    # Requirements
    requirement_type: str  # 'games_played', 'games_won', 'streak', etc.
    requirement_value: int
    
    # Rarity
    rarity: str  # 'common', 'rare', 'epic', 'legendary'
    
    # Special conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Tracking
    unlocked_by: List[str] = field(default_factory=list)
    unlock_rate: float = 0.0

@dataclass
class GameInvite:
    """Game invitation between users"""
    id: str
    from_user_id: str
    to_user_id: str
    game_type: GameType
    message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    status: str = "pending"  # 'pending', 'accepted', 'declined', 'expired'
    game_session_id: Optional[str] = None

class MemoryGamingService:
    """Main service for memory gaming features"""
    
    def __init__(self):
        # Game sessions
        self.active_sessions: Dict[str, GameSession] = {}
        self.completed_sessions: List[GameSession] = []
        
        # Player data
        self.player_stats: Dict[str, PlayerStats] = {}
        self.player_sessions: Dict[str, List[str]] = defaultdict(list)  # user_id -> session_ids
        
        # Daily challenges
        self.daily_challenges: Dict[str, DailyChallenge] = {}
        self.challenge_history: List[DailyChallenge] = []
        
        # Achievements
        self.achievements: Dict[str, Achievement] = self._initialize_achievements()
        self.player_achievements: Dict[str, List[str]] = defaultdict(list)
        
        # Invitations
        self.game_invites: Dict[str, GameInvite] = {}
        
        # Leaderboards
        self.global_leaderboard: List[Tuple[str, int]] = []
        self.weekly_leaderboard: List[Tuple[str, int]] = []
        self.friends_leaderboards: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        
        # Addiction mechanics
        self.streak_bonuses = {
            3: 50,    # 3-day streak
            7: 150,   # Week streak
            14: 350,  # Two weeks
            30: 1000, # Month
            100: 5000 # 100 days
        }
        
        # Notification queue
        self.notification_queue: List[Dict[str, Any]] = []
        
        # Initialize daily challenge
        self._create_daily_challenge()
        
        logger.info("🎮 Memory Gaming Service initialized")
    
    def _initialize_achievements(self) -> Dict[str, Achievement]:
        """Initialize all available achievements"""
        achievements = {}
        
        # Games played achievements
        for count in [1, 10, 50, 100, 500, 1000]:
            achievement = Achievement(
                id=f"games_played_{count}",
                name=f"Played {count} Games",
                description=f"Play {count} memory games",
                category=AchievementCategory.GAMES_PLAYED,
                icon="🎮",
                points=count * 10,
                requirement_type="games_played",
                requirement_value=count,
                rarity="common" if count < 50 else "rare" if count < 500 else "epic"
            )
            achievements[achievement.id] = achievement
        
        # Win achievements
        for count in [1, 10, 25, 50, 100]:
            achievement = Achievement(
                id=f"games_won_{count}",
                name=f"Won {count} Games",
                description=f"Win {count} memory games",
                category=AchievementCategory.GAMES_WON,
                icon="🏆",
                points=count * 20,
                requirement_type="games_won",
                requirement_value=count,
                rarity="common" if count < 25 else "rare" if count < 100 else "legendary"
            )
            achievements[achievement.id] = achievement
        
        # Streak achievements
        for days in [3, 7, 14, 30, 100]:
            achievement = Achievement(
                id=f"streak_{days}",
                name=f"{days}-Day Streak",
                description=f"Play games for {days} consecutive days",
                category=AchievementCategory.STREAKS,
                icon="🔥",
                points=days * 30,
                requirement_type="streak",
                requirement_value=days,
                rarity="rare" if days < 14 else "epic" if days < 100 else "legendary"
            )
            achievements[achievement.id] = achievement
        
        # Special achievements
        achievements["first_blood"] = Achievement(
            id="first_blood",
            name="First Blood",
            description="Win your first game",
            category=AchievementCategory.SPECIAL,
            icon="🩸",
            points=50,
            requirement_type="games_won",
            requirement_value=1,
            rarity="common"
        )
        
        achievements["social_butterfly"] = Achievement(
            id="social_butterfly",
            name="Social Butterfly",
            description="Play with 10 different friends",
            category=AchievementCategory.SOCIAL,
            icon="🦋",
            points=200,
            requirement_type="unique_opponents",
            requirement_value=10,
            rarity="rare"
        )
        
        achievements["night_owl"] = Achievement(
            id="night_owl",
            name="Night Owl",
            description="Play 10 games between midnight and 5 AM",
            category=AchievementCategory.SPECIAL,
            icon="🦉",
            points=150,
            requirement_type="special",
            requirement_value=10,
            rarity="rare",
            conditions={"time_range": (0, 5)}
        )
        
        achievements["speed_demon"] = Achievement(
            id="speed_demon",
            name="Speed Demon",
            description="Win a game in under 60 seconds",
            category=AchievementCategory.SPEED,
            icon="⚡",
            points=300,
            requirement_type="speed_win",
            requirement_value=60,
            rarity="epic"
        )
        
        achievements["memory_master"] = Achievement(
            id="memory_master",
            name="Memory Master",
            description="Achieve 100% accuracy in Memory Match",
            category=AchievementCategory.MASTERY,
            icon="🧠",
            points=500,
            requirement_type="perfect_game",
            requirement_value=1,
            rarity="legendary"
        )
        
        return achievements
    
    async def create_game_session(
        self,
        creator_id: str,
        game_type: GameType,
        players: List[str],
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new game session"""
        try:
            session_id = f"game_{uuid.uuid4().hex[:12]}"
            
            # Create session
            session = GameSession(
                id=session_id,
                game_type=game_type,
                creator_id=creator_id,
                players=players,
                status=GameStatus.WAITING,
                scores={player: 0 for player in players}
            )
            
            # Apply settings if provided
            if settings:
                session.time_limit = settings.get('time_limit')
                session.max_rounds = settings.get('max_rounds', 10)
                session.is_public = settings.get('is_public', False)
            
            # Initialize game-specific data
            if game_type == GameType.MEMORY_MATCH:
                session.game_data = await self._initialize_memory_match(players)
            elif game_type == GameType.MEMORY_TIMELINE:
                session.game_data = await self._initialize_timeline_game(players)
            elif game_type == GameType.GUESS_WHO:
                session.game_data = await self._initialize_guess_who(players)
            elif game_type == GameType.TRUTH_OR_MEMORY:
                session.game_data = await self._initialize_truth_or_memory(players)
            
            # Set turn order
            session.turn_order = players.copy()
            random.shuffle(session.turn_order)
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Track for players
            for player_id in players:
                self.player_sessions[player_id].append(session_id)
            
            # Create notification
            self._queue_notification(
                user_ids=players,
                title="🎮 New Game Started!",
                message=f"A {game_type.value.replace('_', ' ').title()} game has been created",
                priority=NotificationPriority.HIGH,
                data={'session_id': session_id, 'game_type': game_type.value}
            )
            
            logger.info(f"🎮 Game session created: {session_id} ({game_type.value})")
            
            return {
                'success': True,
                'session_id': session_id,
                'game_type': game_type.value,
                'players': players,
                'status': session.status.value
            }
            
        except Exception as e:
            logger.error(f"Failed to create game session: {e}")
            return {'success': False, 'error': str(e)}
    
    async def join_game_session(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Join an existing game session"""
        if session_id not in self.active_sessions:
            return {'success': False, 'error': 'Session not found'}
        
        session = self.active_sessions[session_id]
        
        if session.status != GameStatus.WAITING:
            return {'success': False, 'error': 'Game already started'}
        
        if user_id in session.players:
            return {'success': False, 'error': 'Already in game'}
        
        # Add player
        session.players.append(user_id)
        session.scores[user_id] = 0
        self.player_sessions[user_id].append(session_id)
        
        # Check if ready to start
        if len(session.players) >= 2:
            session.status = GameStatus.IN_PROGRESS
            session.started_at = datetime.now()
            
            # Notify all players
            self._queue_notification(
                user_ids=session.players,
                title="🎮 Game Starting!",
                message="All players ready. Game is starting now!",
                priority=NotificationPriority.URGENT,
                data={'session_id': session_id}
            )
        
        return {
            'success': True,
            'session_id': session_id,
            'players': session.players,
            'status': session.status.value
        }
    
    async def play_turn(
        self,
        session_id: str,
        user_id: str,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Play a turn in the game"""
        if session_id not in self.active_sessions:
            return {'success': False, 'error': 'Session not found'}
        
        session = self.active_sessions[session_id]
        
        if session.status != GameStatus.IN_PROGRESS:
            return {'success': False, 'error': 'Game not in progress'}
        
        if user_id not in session.players:
            return {'success': False, 'error': 'Not a player in this game'}
        
        current_player = session.get_current_player()
        if current_player != user_id:
            return {'success': False, 'error': 'Not your turn'}
        
        # Process move based on game type
        result = {}
        if session.game_type == GameType.MEMORY_MATCH:
            result = await self._process_memory_match_move(session, user_id, move_data)
        elif session.game_type == GameType.MEMORY_TIMELINE:
            result = await self._process_timeline_move(session, user_id, move_data)
        elif session.game_type == GameType.GUESS_WHO:
            result = await self._process_guess_who_move(session, user_id, move_data)
        elif session.game_type == GameType.TRUTH_OR_MEMORY:
            result = await self._process_truth_or_memory_move(session, user_id, move_data)
        
        # Record move
        session.moves.append({
            'player': user_id,
            'move': move_data,
            'result': result,
            'timestamp': datetime.now()
        })
        
        # Update score
        if result.get('points'):
            session.scores[user_id] += result['points']
        
        # Move to next turn
        session.next_turn()
        
        # Check if game ended
        if session.status == GameStatus.COMPLETED:
            await self._end_game(session_id)
        
        return {
            'success': True,
            'result': result,
            'scores': session.scores,
            'current_turn': session.get_current_player(),
            'round': session.current_round,
            'status': session.status.value
        }
    
    async def _initialize_memory_match(self, players: List[str]) -> Dict[str, Any]:
        """Initialize Memory Match game data"""
        # Get shared memories between players
        # For demo, create sample memory pairs
        memory_pairs = []
        for i in range(8):  # 8 pairs = 16 cards
            memory_pairs.append({
                'id': f"mem_{i}",
                'content': f"Shared memory {i}: A wonderful moment together",
                'emotion': random.choice(['happy', 'sad', 'funny', 'nostalgic']),
                'date': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
            })
        
        # Create card deck (each memory appears twice)
        cards = []
        for idx, memory in enumerate(memory_pairs):
            cards.extend([
                {'card_id': f"card_{idx}a", 'memory_id': memory['id'], 'memory': memory, 'revealed': False},
                {'card_id': f"card_{idx}b", 'memory_id': memory['id'], 'memory': memory, 'revealed': False}
            ])
        
        # Shuffle cards
        random.shuffle(cards)
        
        return {
            'cards': cards,
            'matched_pairs': [],
            'current_selection': [],
            'attempts': 0
        }
    
    async def _initialize_timeline_game(self, players: List[str]) -> Dict[str, Any]:
        """Initialize Timeline game data"""
        # Get random memories to sort by date
        memories = []
        for i in range(10):
            memories.append({
                'id': f"timeline_mem_{i}",
                'content': f"Memory event {i}",
                'actual_date': datetime.now() - timedelta(days=random.randint(1, 1000)),
                'hint': random.choice(['summer', 'winter', 'birthday', 'holiday', 'weekend'])
            })
        
        # Shuffle for presentation
        shuffled = memories.copy()
        random.shuffle(shuffled)
        
        return {
            'memories': shuffled,
            'correct_order': sorted(memories, key=lambda x: x['actual_date']),
            'player_orders': {},
            'time_started': datetime.now()
        }
    
    async def _initialize_guess_who(self, players: List[str]) -> Dict[str, Any]:
        """Initialize Guess Who game data"""
        # Create memory-author pairs
        memory_author_pairs = []
        for player in players:
            for i in range(3):
                memory_author_pairs.append({
                    'id': f"guess_{player}_{i}",
                    'content': f"A personal memory from someone special ({i})",
                    'author': player,
                    'hints': [
                        f"This person likes {random.choice(['music', 'sports', 'reading', 'travel'])}",
                        f"They often talk about {random.choice(['family', 'work', 'hobbies', 'dreams'])}"
                    ]
                })
        
        random.shuffle(memory_author_pairs)
        
        return {
            'memory_pairs': memory_author_pairs,
            'current_memory_index': 0,
            'player_guesses': {},
            'correct_guesses': {}
        }
    
    async def _initialize_truth_or_memory(self, players: List[str]) -> Dict[str, Any]:
        """Initialize Truth or Memory game data"""
        # Create prompts
        prompts = [
            "Share your most embarrassing moment",
            "Reveal a secret crush",
            "Describe your biggest fear",
            "Tell about a time you lied",
            "Share your proudest achievement",
            "Reveal a hidden talent",
            "Describe your dream vacation",
            "Share a childhood memory"
        ]
        
        return {
            'prompts': prompts,
            'current_prompt_index': 0,
            'player_choices': {},  # 'truth' or 'memory'
            'shared_content': {},
            'votes': defaultdict(int)
        }
    
    async def _process_memory_match_move(
        self,
        session: GameSession,
        user_id: str,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a Memory Match game move"""
        game_data = session.game_data
        card_id = move_data.get('card_id')
        
        if not card_id:
            return {'success': False, 'error': 'No card selected'}
        
        # Find card
        card = None
        for c in game_data['cards']:
            if c['card_id'] == card_id:
                card = c
                break
        
        if not card:
            return {'success': False, 'error': 'Invalid card'}
        
        if card['revealed']:
            return {'success': False, 'error': 'Card already revealed'}
        
        # Reveal card
        card['revealed'] = True
        game_data['current_selection'].append(card)
        
        # Check if we have a pair
        if len(game_data['current_selection']) == 2:
            game_data['attempts'] += 1
            card1, card2 = game_data['current_selection']
            
            if card1['memory_id'] == card2['memory_id']:
                # Match found!
                game_data['matched_pairs'].append(card1['memory_id'])
                points = 100 - (game_data['attempts'] * 2)  # Bonus for fewer attempts
                
                return {
                    'success': True,
                    'match': True,
                    'points': max(points, 10),
                    'memory': card1['memory']
                }
            else:
                # No match - hide cards again
                card1['revealed'] = False
                card2['revealed'] = False
                game_data['current_selection'] = []
                
                return {
                    'success': True,
                    'match': False,
                    'points': 0
                }
        
        return {'success': True, 'card_revealed': True}
    
    async def _process_timeline_move(
        self,
        session: GameSession,
        user_id: str,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a Timeline game move"""
        game_data = session.game_data
        ordered_ids = move_data.get('ordered_memory_ids', [])
        
        if not ordered_ids:
            return {'success': False, 'error': 'No order provided'}
        
        # Store player's order
        game_data['player_orders'][user_id] = ordered_ids
        
        # Calculate score based on correctness
        correct_order_ids = [m['id'] for m in game_data['correct_order']]
        
        score = 0
        for i, mem_id in enumerate(ordered_ids):
            if i < len(correct_order_ids) and mem_id == correct_order_ids[i]:
                score += 10  # Points for correct position
        
        # Bonus for speed
        time_taken = (datetime.now() - game_data['time_started']).seconds
        if time_taken < 30:
            score += 50
        elif time_taken < 60:
            score += 25
        
        return {
            'success': True,
            'score': score,
            'correct_order': correct_order_ids,
            'time_taken': time_taken
        }
    
    async def _process_guess_who_move(
        self,
        session: GameSession,
        user_id: str,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a Guess Who game move"""
        game_data = session.game_data
        guessed_author = move_data.get('guessed_author')
        
        current_index = game_data['current_memory_index']
        if current_index >= len(game_data['memory_pairs']):
            return {'success': False, 'error': 'No more memories'}
        
        current_memory = game_data['memory_pairs'][current_index]
        
        # Check if guess is correct
        is_correct = guessed_author == current_memory['author']
        
        # Store guess
        game_data['player_guesses'][user_id] = guessed_author
        
        if is_correct:
            if user_id not in game_data['correct_guesses']:
                game_data['correct_guesses'][user_id] = 0
            game_data['correct_guesses'][user_id] += 1
            points = 50
        else:
            points = 0
        
        # Move to next memory
        game_data['current_memory_index'] += 1
        
        return {
            'success': True,
            'correct': is_correct,
            'actual_author': current_memory['author'],
            'points': points
        }
    
    async def _process_truth_or_memory_move(
        self,
        session: GameSession,
        user_id: str,
        move_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a Truth or Memory game move"""
        game_data = session.game_data
        choice = move_data.get('choice')  # 'truth' or 'memory'
        content = move_data.get('content')
        
        if choice not in ['truth', 'memory']:
            return {'success': False, 'error': 'Invalid choice'}
        
        current_prompt = game_data['prompts'][game_data['current_prompt_index']]
        
        # Store player's choice and content
        game_data['player_choices'][user_id] = choice
        game_data['shared_content'][user_id] = {
            'choice': choice,
            'content': content,
            'prompt': current_prompt
        }
        
        # Award points
        points = 30 if choice == 'truth' else 50  # More points for sharing memory
        
        # Move to next prompt
        game_data['current_prompt_index'] += 1
        
        return {
            'success': True,
            'choice': choice,
            'points': points,
            'next_prompt': game_data['prompts'][game_data['current_prompt_index']] 
                          if game_data['current_prompt_index'] < len(game_data['prompts']) else None
        }
    
    async def _end_game(self, session_id: str):
        """End a game session and distribute rewards"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session.ended_at = datetime.now()
        session.status = GameStatus.COMPLETED
        
        # Determine winner
        winner_id = max(session.scores, key=session.scores.get)
        session.winner_id = winner_id
        
        # Update player stats
        for player_id in session.players:
            if player_id not in self.player_stats:
                self.player_stats[player_id] = PlayerStats(user_id=player_id)
            
            stats = self.player_stats[player_id]
            
            # Determine result for this player
            if player_id == winner_id:
                result = "won"
            elif session.status == GameStatus.ABANDONED:
                result = "abandoned"
            else:
                result = "lost"
            
            # Update stats
            opponent_id = [p for p in session.players if p != player_id][0] if len(session.players) == 2 else "multiple"
            stats.update_stats(result, session.scores[player_id], opponent_id)
            
            # Check achievements
            await self._check_achievements(player_id)
        
        # Move to completed
        self.completed_sessions.append(session)
        del self.active_sessions[session_id]
        
        # Notify players
        self._queue_notification(
            user_ids=session.players,
            title="🏁 Game Ended!",
            message=f"Winner: Player {winner_id} with {session.scores[winner_id]} points!",
            priority=NotificationPriority.HIGH,
            data={
                'session_id': session_id,
                'winner': winner_id,
                'scores': session.scores
            }
        )
        
        logger.info(f"🏁 Game ended: {session_id}, Winner: {winner_id}")
    
    async def _check_achievements(self, user_id: str):
        """Check and award achievements for a player"""
        if user_id not in self.player_stats:
            return
        
        stats = self.player_stats[user_id]
        current_achievements = self.player_achievements.get(user_id, [])
        
        for achievement_id, achievement in self.achievements.items():
            if achievement_id in current_achievements:
                continue
            
            # Check requirement
            unlocked = False
            
            if achievement.requirement_type == "games_played":
                unlocked = stats.games_played >= achievement.requirement_value
            elif achievement.requirement_type == "games_won":
                unlocked = stats.games_won >= achievement.requirement_value
            elif achievement.requirement_type == "streak":
                unlocked = stats.longest_streak >= achievement.requirement_value
            elif achievement.requirement_type == "unique_opponents":
                unlocked = len(stats.unique_opponents) >= achievement.requirement_value
            elif achievement.requirement_type == "speed_win":
                unlocked = stats.fastest_win_time and stats.fastest_win_time <= achievement.requirement_value
            
            if unlocked:
                # Award achievement
                self.player_achievements[user_id].append(achievement_id)
                stats.achievements_unlocked.append(achievement_id)
                achievement.unlocked_by.append(user_id)
                
                # Calculate unlock rate
                total_players = len(self.player_stats)
                if total_players > 0:
                    achievement.unlock_rate = len(achievement.unlocked_by) / total_players
                
                # Notify player
                self._queue_notification(
                    user_ids=[user_id],
                    title="🏆 Achievement Unlocked!",
                    message=f"{achievement.name}: {achievement.description}",
                    priority=NotificationPriority.HIGH,
                    data={
                        'achievement_id': achievement_id,
                        'points': achievement.points,
                        'rarity': achievement.rarity
                    }
                )
                
                logger.info(f"🏆 Achievement unlocked: {user_id} - {achievement.name}")
    
    def _create_daily_challenge(self):
        """Create a new daily challenge"""
        today = datetime.now().date()
        challenge_id = f"daily_{today.isoformat()}"
        
        if challenge_id in self.daily_challenges:
            return  # Already exists
        
        # Random challenge type
        challenge_type = random.choice(list(GameType))
        
        # Create challenge
        challenge = DailyChallenge(
            id=challenge_id,
            date=datetime.now(),
            challenge_type=challenge_type,
            title=f"Daily {challenge_type.value.replace('_', ' ').title()}",
            description=f"Complete today's {challenge_type.value} challenge!",
            target_score=random.randint(100, 500)
        )
        
        self.daily_challenges[challenge_id] = challenge
        
        logger.info(f"📅 Daily challenge created: {challenge.title}")
    
    async def participate_daily_challenge(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Participate in the daily challenge"""
        today = datetime.now().date()
        challenge_id = f"daily_{today.isoformat()}"
        
        if challenge_id not in self.daily_challenges:
            self._create_daily_challenge()
        
        challenge = self.daily_challenges[challenge_id]
        
        if not challenge.is_active():
            return {'success': False, 'error': 'Challenge expired'}
        
        if user_id in challenge.participants:
            return {'success': False, 'error': 'Already participated'}
        
        challenge.participants.append(user_id)
        
        # Create a special game session for the challenge
        result = await self.create_game_session(
            creator_id=user_id,
            game_type=challenge.challenge_type,
            players=[user_id, "ai_opponent"],  # AI opponent for daily challenges
            settings={'max_rounds': 5}
        )
        
        return {
            'success': True,
            'challenge': asdict(challenge),
            'game_session': result
        }
    
    def get_leaderboard(
        self,
        leaderboard_type: str = "global",
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get leaderboard data"""
        leaderboard = []
        
        if leaderboard_type == "global":
            # Global leaderboard by total points
            player_points = [(pid, stats.total_points) 
                            for pid, stats in self.player_stats.items()]
            player_points.sort(key=lambda x: x[1], reverse=True)
            
            for rank, (pid, points) in enumerate(player_points[:limit], 1):
                stats = self.player_stats[pid]
                leaderboard.append({
                    'rank': rank,
                    'user_id': pid,
                    'points': points,
                    'level': stats.current_level,
                    'games_played': stats.games_played,
                    'win_rate': round(stats.win_rate * 100, 1)
                })
                
        elif leaderboard_type == "weekly":
            # Weekly leaderboard
            week_start = datetime.now() - timedelta(days=7)
            weekly_points = defaultdict(int)
            
            for session in self.completed_sessions:
                if session.ended_at and session.ended_at >= week_start:
                    for pid, score in session.scores.items():
                        weekly_points[pid] += score
            
            weekly_sorted = sorted(weekly_points.items(), key=lambda x: x[1], reverse=True)
            
            for rank, (pid, points) in enumerate(weekly_sorted[:limit], 1):
                stats = self.player_stats.get(pid, PlayerStats(user_id=pid))
                leaderboard.append({
                    'rank': rank,
                    'user_id': pid,
                    'points': points,
                    'level': stats.current_level
                })
                
        elif leaderboard_type == "friends" and user_id:
            # Friends leaderboard
            if user_id in self.player_stats:
                friends = list(self.player_stats[user_id].unique_opponents)
                friends.append(user_id)
                
                friend_points = [(pid, self.player_stats[pid].total_points) 
                                for pid in friends if pid in self.player_stats]
                friend_points.sort(key=lambda x: x[1], reverse=True)
                
                for rank, (pid, points) in enumerate(friend_points[:limit], 1):
                    stats = self.player_stats[pid]
                    leaderboard.append({
                        'rank': rank,
                        'user_id': pid,
                        'points': points,
                        'level': stats.current_level,
                        'is_you': pid == user_id
                    })
        
        return leaderboard
    
    def _queue_notification(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        priority: NotificationPriority,
        data: Optional[Dict[str, Any]] = None
    ):
        """Queue a notification for users"""
        notification = {
            'id': f"notif_{uuid.uuid4().hex[:8]}",
            'user_ids': user_ids,
            'title': title,
            'message': message,
            'priority': priority.value,
            'data': data or {},
            'timestamp': datetime.now().isoformat(),
            'delivered': False
        }
        
        self.notification_queue.append(notification)
        
        # In production, this would trigger WebSocket events
        logger.info(f"📬 Notification queued: {title} for {len(user_ids)} users")
    
    def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending notifications for a user"""
        user_notifications = []
        
        for notif in self.notification_queue:
            if user_id in notif['user_ids'] and not notif['delivered']:
                user_notifications.append(notif)
                notif['delivered'] = True
        
        return user_notifications
    
    async def create_game_invite(
        self,
        from_user_id: str,
        to_user_id: str,
        game_type: GameType,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a game invitation"""
        invite_id = f"invite_{uuid.uuid4().hex[:8]}"
        
        invite = GameInvite(
            id=invite_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            game_type=game_type,
            message=message
        )
        
        self.game_invites[invite_id] = invite
        
        # Notify recipient
        self._queue_notification(
            user_ids=[to_user_id],
            title="🎮 Game Invitation!",
            message=f"You've been invited to play {game_type.value.replace('_', ' ').title()}",
            priority=NotificationPriority.HIGH,
            data={'invite_id': invite_id, 'from_user': from_user_id}
        )
        
        return {
            'success': True,
            'invite_id': invite_id,
            'expires_at': invite.expires_at.isoformat()
        }
    
    async def accept_invite(
        self,
        invite_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Accept a game invitation"""
        if invite_id not in self.game_invites:
            return {'success': False, 'error': 'Invite not found'}
        
        invite = self.game_invites[invite_id]
        
        if invite.to_user_id != user_id:
            return {'success': False, 'error': 'Not your invitation'}
        
        if invite.status != "pending":
            return {'success': False, 'error': f'Invite already {invite.status}'}
        
        if datetime.now() > invite.expires_at:
            invite.status = "expired"
            return {'success': False, 'error': 'Invite expired'}
        
        # Create game session
        result = await self.create_game_session(
            creator_id=invite.from_user_id,
            game_type=invite.game_type,
            players=[invite.from_user_id, invite.to_user_id]
        )
        
        if result['success']:
            invite.status = "accepted"
            invite.game_session_id = result['session_id']
        
        return result
    
    def get_player_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive stats for a player"""
        if user_id not in self.player_stats:
            self.player_stats[user_id] = PlayerStats(user_id=user_id)
        
        stats = self.player_stats[user_id]
        
        # Calculate additional metrics
        active_games = [sid for sid in self.player_sessions[user_id] 
                       if sid in self.active_sessions]
        
        # Check streak status
        streak_active = False
        if stats.last_game_date:
            days_since = (datetime.now() - stats.last_game_date).days
            streak_active = days_since <= 1
        
        return {
            'user_id': user_id,
            'level': stats.current_level,
            'experience': stats.experience_points,
            'next_level_xp': stats.next_level_xp,
            'total_points': stats.total_points,
            'games_played': stats.games_played,
            'games_won': stats.games_won,
            'win_rate': round(stats.win_rate * 100, 1),
            'current_streak': stats.current_streak,
            'longest_streak': stats.longest_streak,
            'streak_active': streak_active,
            'achievements': stats.achievements_unlocked,
            'badges': stats.badges_earned,
            'active_games': active_games,
            'unique_opponents': len(stats.unique_opponents),
            'favorite_game': stats.favorite_game_type.value if stats.favorite_game_type else None
        }

# Global instance
memory_gaming_service = MemoryGamingService()