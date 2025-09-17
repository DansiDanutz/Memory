# Memory Gaming System Documentation

## Table of Contents
1. [Overview](#overview)
2. [Game Types](#game-types)
3. [API Endpoints](#api-endpoints)
4. [Addiction Mechanics](#addiction-mechanics)
5. [WebSocket Events](#websocket-events)
6. [Integration Guide](#integration-guide)
7. [Scoring System](#scoring-system)
8. [Achievements](#achievements)

---

## Overview

The Memory Gaming System transforms personal memories into engaging, addictive multiplayer games. It leverages shared memories between friends and family to create meaningful gaming experiences that increase platform engagement and retention.

### Key Features
- **10 Different Game Types** - Variety keeps users engaged
- **Real-time Multiplayer** - WebSocket-powered instant gameplay
- **Achievement System** - 50+ achievements to unlock
- **Daily Challenges** - Fresh content every day
- **Leaderboards** - Global, weekly, and friends rankings
- **Addiction Mechanics** - Psychology-based retention features

---

## Game Types

### 1. Memory Match 🎯
**Description:** Classic memory card matching game using shared memories
- **Players:** 2-4
- **Duration:** 5-10 minutes
- **Scoring:** Points for matches, bonus for speed
- **Addiction Hook:** Perfect score achievements, time challenges

**How to Play:**
1. Cards are placed face down with memory pairs
2. Players take turns revealing two cards
3. Match memories to score points
4. Player with most matches wins

### 2. Memory Timeline ⏰
**Description:** Arrange memories in chronological order
- **Players:** 1-4
- **Duration:** 3-5 minutes
- **Scoring:** Points for correct order, speed bonus
- **Addiction Hook:** Beat your best time, perfect ordering

**How to Play:**
1. Random memories are presented
2. Players arrange them by date
3. Points awarded for accuracy
4. Fastest accurate player wins

### 3. Guess Who 🤔
**Description:** Guess which friend shared which memory
- **Players:** 2-6
- **Duration:** 10-15 minutes
- **Scoring:** Points for correct guesses
- **Addiction Hook:** Learn about friends, social discovery

**How to Play:**
1. Anonymous memories are shown
2. Players guess the author
3. Hints available for fewer points
4. Most correct guesses wins

### 4. Memory Telephone 📞
**Description:** Pass memories between friends with modifications
- **Players:** 3-8
- **Duration:** 15-20 minutes
- **Scoring:** Points for accuracy retention
- **Addiction Hook:** Hilarious transformations, social sharing

**How to Play:**
1. First player shares a memory
2. Each player adds/modifies slightly
3. Compare final to original
4. Points for maintaining accuracy

### 5. Truth or Memory 🎭
**Description:** Choose to share truth or reveal a memory
- **Players:** 2-8
- **Duration:** 20-30 minutes
- **Scoring:** Points for sharing, votes from others
- **Addiction Hook:** Social validation, deep connections

**How to Play:**
1. Players receive prompts
2. Choose truth or share memory
3. Others vote on authenticity
4. Points for participation and votes

### 6. Memory Battles ⚔️
**Description:** Compete on memory knowledge and recall
- **Players:** 2
- **Duration:** 5-10 minutes
- **Scoring:** Points for correct answers, speed
- **Addiction Hook:** Head-to-head competition, rankings

### 7. Daily Challenge 📅
**Description:** New memory challenge every day
- **Players:** Solo with leaderboard
- **Duration:** 5 minutes
- **Scoring:** Points accumulate monthly
- **Addiction Hook:** Don't break the streak!

### 8. Speed Recall ⚡
**Description:** Quick-fire memory recognition
- **Players:** 1-4
- **Duration:** 2-3 minutes
- **Scoring:** Points for speed and accuracy
- **Addiction Hook:** Beat high scores, perfect runs

### 9. Memory Trivia 🧠
**Description:** Trivia questions about shared memories
- **Players:** 2-8
- **Duration:** 10-15 minutes
- **Scoring:** Points for correct answers
- **Addiction Hook:** Learn about friends, knowledge mastery

### 10. Emotional Match 💖
**Description:** Match memories by emotional content
- **Players:** 2-4
- **Duration:** 5-10 minutes
- **Scoring:** Points for emotional intelligence
- **Addiction Hook:** Emotional connections, empathy building

---

## API Endpoints

### Game Management

#### Create Game
```http
POST /api/games/create
```
```json
{
  "creator_id": "user123",
  "game_type": "memory_match",
  "players": ["user123", "user456"],
  "settings": {
    "time_limit": 60,
    "max_rounds": 10,
    "is_public": false
  }
}
```

#### Join Game
```http
POST /api/games/join
```
```json
{
  "session_id": "game_abc123",
  "user_id": "user789"
}
```

#### Play Turn
```http
POST /api/games/play
```
```json
{
  "session_id": "game_abc123",
  "user_id": "user123",
  "move": {
    "card_id": "card_5",
    "action": "reveal"
  }
}
```

### Statistics & Leaderboards

#### Get Leaderboard
```http
GET /api/games/scores?type=global&limit=100
```
Types: `global`, `weekly`, `friends`

#### Get User Stats
```http
GET /api/games/stats?user_id=user123
```

#### Get Achievements
```http
GET /api/games/achievements?user_id=user123
```

### Daily Challenges

#### Get Current Challenge
```http
GET /api/games/challenges
```

#### Participate in Challenge
```http
POST /api/games/challenges/participate
```
```json
{
  "user_id": "user123"
}
```

### Social Features

#### Create Invite
```http
POST /api/games/invite
```
```json
{
  "from_user_id": "user123",
  "to_user_id": "user456",
  "game_type": "memory_match",
  "message": "Let's play!"
}
```

#### Accept Invite
```http
POST /api/games/invite/accept
```
```json
{
  "invite_id": "invite_xyz",
  "user_id": "user456"
}
```

#### Get Notifications
```http
GET /api/games/notifications?user_id=user123
```

---

## Addiction Mechanics

### 1. Variable Reward Schedules 🎰
- **Random bonus points** (10-100) after games
- **Mystery boxes** after certain milestones
- **Surprise achievements** not listed publicly
- **Lucky streaks** with multiplier bonuses

### 2. Streak Systems 🔥
- **Daily Login Streak:** Play at least one game daily
  - 3 days: 50 bonus points
  - 7 days: 150 bonus points
  - 14 days: 350 bonus points
  - 30 days: 1000 bonus points
  - 100 days: 5000 bonus points + exclusive badge
- **Memory Sharing Streak:** Share memories daily
- **Friend Challenge Streak:** Challenge friends daily

### 3. FOMO Triggers ⏱️
- **Limited Time Events:** 24-hour special challenges
- **Flash Tournaments:** 1-hour competitive events
- **Exclusive Memories:** Unlock special content
- **Expiring Rewards:** Use or lose mechanics

### 4. Social Competition 👥
- **Friend Leaderboards:** See where you rank
- **Weekly Tournaments:** Compete for top spots
- **Team Challenges:** Group competitions
- **Social Sharing:** Brag about achievements

### 5. Progress Mechanics 📊
- **Experience Points (XP):** Level up system
- **Progress Bars:** Visual progression
- **Milestone Rewards:** Unlock at levels
- **Collection Completion:** Collect all achievements

### 6. Notification Strategy 📱
```javascript
// Optimal notification times (based on user behavior)
const notificationSchedule = {
  morning: "09:00",      // Daily challenge reminder
  lunch: "12:30",        // Friend activity update
  evening: "19:00",      // Prime gaming time
  night: "21:00"         // Streak protection
};

// Dynamic triggers
- Friend started playing
- Someone beat your score
- Streak about to break
- New achievement nearby
- Challenge ending soon
```

### 7. Psychological Hooks 🧠
- **Completion Desire:** 98% achievement completion shown
- **Social Proof:** "5 friends playing now"
- **Loss Aversion:** "Don't lose your 29-day streak!"
- **Reciprocity:** Friend sent you a challenge
- **Scarcity:** "Only 2 hours left!"

---

## WebSocket Events

### Client → Server Events

#### Join Game Room
```javascript
socket.emit('join_game_room', {
  session_id: 'game_abc123',
  user_id: 'user123'
});
```

#### Leave Game Room
```javascript
socket.emit('leave_game_room', {
  session_id: 'game_abc123',
  user_id: 'user123'
});
```

#### Game Chat
```javascript
socket.emit('game_chat', {
  session_id: 'game_abc123',
  user_id: 'user123',
  message: 'Great move!'
});
```

#### Game Emoji
```javascript
socket.emit('game_emoji', {
  session_id: 'game_abc123',
  user_id: 'user123',
  emoji: '🎉'
});
```

### Server → Client Events

#### Game Created
```javascript
socket.on('game_created', (data) => {
  console.log('New game:', data.session_id);
});
```

#### Game Update
```javascript
socket.on('game_update', (data) => {
  updateGameState(data);
});
```

#### Player Joined
```javascript
socket.on('player_joined', (data) => {
  showNotification(`${data.user_id} joined the game`);
});
```

#### Game Invite
```javascript
socket.on('game_invite', (data) => {
  showInviteModal(data);
});
```

---

## Integration Guide

### Quick Start

1. **Import the Gaming Service**
```python
from memory_gaming_service import (
    memory_gaming_service,
    GameType,
    GameStatus
)
```

2. **Create a Game Session**
```python
result = await memory_gaming_service.create_game_session(
    creator_id="user123",
    game_type=GameType.MEMORY_MATCH,
    players=["user123", "user456"],
    settings={"max_rounds": 10}
)
```

3. **Handle Game Turns**
```python
move_result = await memory_gaming_service.play_turn(
    session_id="game_abc123",
    user_id="user123",
    move_data={"card_id": "card_5"}
)
```

4. **Track Achievements**
```python
stats = memory_gaming_service.get_player_stats("user123")
achievements = memory_gaming_service.player_achievements.get("user123", [])
```

### Frontend Integration

```javascript
// Initialize WebSocket connection
const socket = io('ws://localhost:8080', {
  auth: {
    token: 'jwt_token_here'
  }
});

// Join a game
async function joinGame(sessionId) {
  const response = await fetch('/api/games/join', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      session_id: sessionId,
      user_id: currentUserId
    })
  });
  
  if (response.ok) {
    socket.emit('join_game_room', {
      session_id: sessionId,
      user_id: currentUserId
    });
  }
}

// Listen for game updates
socket.on('game_update', (data) => {
  updateGameUI(data);
});
```

---

## Scoring System

### Base Points
- **Memory Match:** 10 points per match
- **Timeline:** 10 points per correct position
- **Guess Who:** 50 points per correct guess
- **Truth or Memory:** 30 points for truth, 50 for memory
- **Speed Recall:** 5 points per correct, x2 for speed

### Multipliers
- **Perfect Game:** x2.0 multiplier
- **Speed Bonus:** x1.5 if under time limit
- **Streak Bonus:** x1.1 per day (max x2.0)
- **First Win:** x1.5 for first win of day

### Penalties
- **Wrong Answer:** -5 points (minimum 0)
- **Time Out:** -10 points
- **Abandoning:** -50 points, lose streak

---

## Achievements

### Tier System
- **Common** (Gray): Easy to obtain, <50% rarity
- **Rare** (Blue): Moderate difficulty, <25% rarity
- **Epic** (Purple): Hard to obtain, <10% rarity
- **Legendary** (Gold): Extremely rare, <1% rarity

### Achievement Categories

#### Games Played
- **First Steps** (Common): Play 1 game
- **Regular** (Common): Play 10 games
- **Dedicated** (Rare): Play 50 games
- **Veteran** (Epic): Play 100 games
- **Master** (Epic): Play 500 games
- **Legend** (Legendary): Play 1000 games

#### Wins
- **First Blood** (Common): Win your first game
- **Winner** (Common): Win 10 games
- **Champion** (Rare): Win 25 games
- **Dominator** (Epic): Win 50 games
- **Unstoppable** (Legendary): Win 100 games

#### Streaks
- **Hot Streak** (Common): 3-day streak
- **On Fire** (Rare): 7-day streak
- **Blazing** (Epic): 14-day streak
- **Inferno** (Epic): 30-day streak
- **Eternal Flame** (Legendary): 100-day streak

#### Social
- **Social Butterfly** (Rare): Play with 10 different friends
- **Popular** (Epic): Play with 25 different friends
- **Influencer** (Legendary): Play with 50 different friends

#### Special
- **Night Owl** (Rare): Play 10 games between midnight and 5 AM
- **Speed Demon** (Epic): Win a game in under 60 seconds
- **Memory Master** (Legendary): 100% accuracy in Memory Match
- **Perfect Week** (Epic): Win every day for a week
- **Comeback Kid** (Rare): Win after being 50+ points behind

---

## Best Practices

### For Developers
1. **Cache game states** for quick loading
2. **Implement retry logic** for network issues
3. **Use WebSocket heartbeat** to detect disconnections
4. **Batch notifications** to prevent spam
5. **Rate limit API calls** (100/minute recommended)

### For Game Design
1. **Keep sessions short** (5-30 minutes max)
2. **Always provide feedback** (sounds, animations)
3. **Show progress clearly** (scores, timers)
4. **Make first win easy** (hook players early)
5. **Balance difficulty** (gradual progression)

### For Retention
1. **Send smart notifications** (not too many)
2. **Reward returning players** (welcome back bonus)
3. **Create social pressure** (friend invites)
4. **Update content regularly** (new challenges)
5. **Celebrate milestones** (achievement unlocks)

---

## Troubleshooting

### Common Issues

**Game Won't Start**
- Check all players have joined
- Verify game session exists
- Ensure WebSocket connected

**Moves Not Registering**
- Check it's your turn
- Verify move data format
- Ensure game in progress

**Achievements Not Unlocking**
- Stats update after game ends
- Some have hidden requirements
- Check achievement conditions

**WebSocket Disconnections**
- Implement auto-reconnect
- Store game state locally
- Use connection heartbeat

---

## Metrics to Track

### Engagement Metrics
- Daily Active Users (DAU)
- Average Session Duration
- Games Per User Per Day
- Retention Rate (D1, D7, D30)

### Game Metrics
- Most Popular Game Types
- Average Game Duration
- Completion Rate
- Abandonment Rate

### Social Metrics
- Invites Sent/Accepted
- Friend Connections Made
- Social Features Used
- Viral Coefficient

### Monetization Metrics
- Conversion to Premium
- Revenue Per User
- Lifetime Value (LTV)
- Churn Rate

---

## Future Enhancements

### Planned Features
1. **AI Opponents** - Play against smart bots
2. **Voice Integration** - Voice-activated gaming
3. **AR Games** - Augmented reality memory games
4. **Tournaments** - Large-scale competitions
5. **Clans/Teams** - Group gaming features
6. **Betting System** - Wager memory credits
7. **Custom Games** - User-created game modes
8. **Coaching** - AI tips for improvement

### Experimental Features
- **Memory NFTs** - Collectible memory cards
- **Cross-Platform** - Play across devices
- **Live Streaming** - Watch others play
- **VR Support** - Virtual reality gaming

---

## Support

For technical support or questions:
- Email: gaming@memoryapp.com
- Discord: discord.gg/memoryapp
- Documentation: docs.memoryapp.com/gaming

---

*Last Updated: September 13, 2025*
*Version: 1.0.0*