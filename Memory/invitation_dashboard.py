"""
Invitation Tracking Dashboard for Gamified Voice Avatar System
==============================================================
Real-time monitoring and analytics for the invitation reward system
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from gamified_voice_avatar import GamifiedVoiceAvatarSystem, UserTier
from database_models import get_session, DatabaseQueries, User, Invitation, SystemMetrics

load_dotenv()

# Initialize FastAPI app for dashboard
dashboard_app = FastAPI(
    title="Memory Bot Invitation Dashboard",
    description="Monitor and manage the gamified invitation system"
)

# Initialize systems
voice_system = GamifiedVoiceAvatarSystem()


# Dashboard HTML Template (embedded for simplicity)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memory Bot - Invitation Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #667eea;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 18px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #999;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 1px;
        }

        .stat-change {
            color: #4caf50;
            font-size: 14px;
            margin-top: 10px;
        }

        .stat-change.negative {
            color: #f44336;
        }

        .chart-container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }

        .leaderboard {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }

        .leaderboard h2 {
            color: #667eea;
            margin-bottom: 20px;
        }

        .leaderboard-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            transition: background 0.3s ease;
        }

        .leaderboard-item:hover {
            background: #f8f9fa;
        }

        .rank {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 15px;
        }

        .rank.gold {
            background: linear-gradient(135deg, #FFD700, #FFA500);
        }

        .rank.silver {
            background: linear-gradient(135deg, #C0C0C0, #808080);
        }

        .rank.bronze {
            background: linear-gradient(135deg, #CD7F32, #8B4513);
        }

        .user-info {
            flex: 1;
        }

        .user-name {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .user-tier {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 600;
        }

        .tier-free {
            background: #e0e0e0;
            color: #666;
        }

        .tier-invited {
            background: #e3f2fd;
            color: #1976d2;
        }

        .tier-premium {
            background: #fff3e0;
            color: #f57c00;
        }

        .invite-count {
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .tab {
            padding: 10px 20px;
            background: #f0f0f0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .tab.active {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }

        .realtime-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #4caf50;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-left: 10px;
        }

        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
            }
        }

        .activity-feed {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-top: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }

        .activity-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border-left: 3px solid #667eea;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 5px;
        }

        .activity-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: #667eea;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
        }

        .activity-content {
            flex: 1;
        }

        .activity-time {
            color: #999;
            font-size: 12px;
        }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Memory Bot Invitation Dashboard <span class="realtime-indicator"></span></h1>
            <p>Real-time monitoring of the gamified voice avatar system</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="total-users">0</div>
                <div class="stat-label">Total Users</div>
                <div class="stat-change">+0% today</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-invitations">0</div>
                <div class="stat-label">Total Invitations</div>
                <div class="stat-change">+0 this hour</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="voice-avatars">0</div>
                <div class="stat-label">Voice Avatars</div>
                <div class="stat-change">0 ElevenLabs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="conversion-rate">0%</div>
                <div class="stat-label">Conversion Rate</div>
                <div class="stat-change">Invites → Users</div>
            </div>
        </div>

        <div class="chart-container">
            <h2>User Distribution by Tier</h2>
            <div class="tabs">
                <div class="tab active" onclick="switchTab('distribution')">Distribution</div>
                <div class="tab" onclick="switchTab('growth')">Growth</div>
                <div class="tab" onclick="switchTab('activity')">Activity</div>
            </div>
            <canvas id="tierChart" width="400" height="200"></canvas>
        </div>

        <div class="leaderboard">
            <h2>Top Inviters 🏆</h2>
            <div id="leaderboard-list">
                <!-- Dynamically populated -->
            </div>
        </div>

        <div class="activity-feed">
            <h2>Recent Activity</h2>
            <div id="activity-list">
                <!-- Dynamically populated -->
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh data every 5 seconds
        setInterval(fetchDashboardData, 5000);

        // Initial load
        fetchDashboardData();

        async function fetchDashboardData() {
            try {
                const response = await fetch('/api/dashboard/stats');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error fetching dashboard data:', error);
            }
        }

        function updateDashboard(data) {
            // Update stats
            document.getElementById('total-users').textContent = data.total_users || 0;
            document.getElementById('total-invitations').textContent = data.total_invitations || 0;
            document.getElementById('voice-avatars').textContent = data.voice_avatars || 0;
            document.getElementById('conversion-rate').textContent =
                Math.round((data.conversion_rate || 0) * 100) + '%';

            // Update leaderboard
            updateLeaderboard(data.leaderboard || []);

            // Update activity feed
            updateActivityFeed(data.recent_activity || []);

            // Update chart
            updateTierChart(data.tier_distribution || {});
        }

        function updateLeaderboard(leaderboard) {
            const container = document.getElementById('leaderboard-list');
            container.innerHTML = '';

            leaderboard.forEach((user, index) => {
                const rankClass = index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'bronze' : '';
                const tierClass = 'tier-' + user.tier.toLowerCase();

                const item = document.createElement('div');
                item.className = 'leaderboard-item';
                item.innerHTML = `
                    <div class="rank ${rankClass}">${index + 1}</div>
                    <div class="user-info">
                        <div class="user-name">${user.user_id}</div>
                        <span class="user-tier ${tierClass}">${user.tier}</span>
                    </div>
                    <div class="invite-count">${user.invites}</div>
                `;
                container.appendChild(item);
            });
        }

        function updateActivityFeed(activities) {
            const container = document.getElementById('activity-list');
            container.innerHTML = '';

            activities.forEach(activity => {
                const item = document.createElement('div');
                item.className = 'activity-item';
                item.innerHTML = `
                    <div class="activity-icon">${getActivityIcon(activity.type)}</div>
                    <div class="activity-content">
                        <div>${activity.message}</div>
                        <div class="activity-time">${formatTime(activity.timestamp)}</div>
                    </div>
                `;
                container.appendChild(item);
            });
        }

        function updateTierChart(distribution) {
            // Simple bar chart visualization
            const canvas = document.getElementById('tierChart');
            const ctx = canvas.getContext('2d');

            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw bars
            const tiers = ['FREE', 'INVITED', 'PREMIUM'];
            const colors = ['#e0e0e0', '#1976d2', '#f57c00'];
            const values = [
                distribution.free || 0,
                distribution.invited || 0,
                distribution.premium || 0
            ];

            const maxValue = Math.max(...values, 1);
            const barWidth = canvas.width / (tiers.length * 2);
            const barSpacing = barWidth;

            tiers.forEach((tier, index) => {
                const x = index * (barWidth + barSpacing) + barSpacing;
                const height = (values[index] / maxValue) * (canvas.height - 40);
                const y = canvas.height - height - 20;

                // Draw bar
                ctx.fillStyle = colors[index];
                ctx.fillRect(x, y, barWidth, height);

                // Draw label
                ctx.fillStyle = '#333';
                ctx.font = '12px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(tier, x + barWidth/2, canvas.height - 5);

                // Draw value
                ctx.fillText(values[index], x + barWidth/2, y - 5);
            });
        }

        function getActivityIcon(type) {
            const icons = {
                'invitation_sent': '📤',
                'invitation_accepted': '✅',
                'avatar_created': '🎤',
                'user_upgraded': '⭐',
                'reward_claimed': '🎁'
            };
            return icons[type] || '📌';
        }

        function formatTime(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            if (diff < 60000) return 'Just now';
            if (diff < 3600000) return Math.floor(diff / 60000) + ' minutes ago';
            if (diff < 86400000) return Math.floor(diff / 3600000) + ' hours ago';
            return date.toLocaleDateString();
        }

        function switchTab(tab) {
            // Update active tab
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            // Load different data based on tab
            // Implementation would vary based on requirements
        }
    </script>
</body>
</html>
"""


# API Endpoints

@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve the main dashboard HTML"""
    return DASHBOARD_HTML


@dashboard_app.get("/api/dashboard/stats")
async def get_dashboard_stats() -> Dict[str, Any]:
    """Get real-time dashboard statistics"""
    try:
        # Get database session
        session = get_session()

        # Calculate statistics
        stats = calculate_system_stats(session)

        # Get leaderboard
        leaderboard_users = DatabaseQueries.get_leaderboard(session, limit=10)
        leaderboard = [
            {
                "user_id": anonymize_user_id(user.id),
                "invites": user.successful_invites,
                "tier": user.tier.value,
                "badge": get_badge_for_invites(user.successful_invites)
            }
            for user in leaderboard_users
        ]

        # Get recent activity
        recent_activity = get_recent_activity(session, limit=10)

        # Get tier distribution
        tier_distribution = get_tier_distribution(session)

        session.close()

        return {
            "total_users": stats["total_users"],
            "total_invitations": stats["total_invitations"],
            "voice_avatars": stats["voice_avatars"],
            "conversion_rate": stats["conversion_rate"],
            "leaderboard": leaderboard,
            "recent_activity": recent_activity,
            "tier_distribution": tier_distribution,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@dashboard_app.get("/api/dashboard/users/{user_id}")
async def get_user_details(user_id: str) -> Dict[str, Any]:
    """Get detailed user information"""
    try:
        session = get_session()
        user = DatabaseQueries.get_user_by_id(session, user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's invitations
        invitations = session.query(Invitation).filter(
            Invitation.inviter_id == user_id
        ).all()

        result = {
            "user_id": user.id,
            "tier": user.tier.value,
            "voice_service": user.voice_service.value,
            "has_avatar": user.voice_id is not None,
            "invitations_sent": user.invitations_sent,
            "successful_invites": user.successful_invites,
            "created_at": user.created_at.isoformat(),
            "last_active": user.last_active.isoformat() if user.last_active else None,
            "invitation_details": [
                {
                    "code": inv.code,
                    "status": inv.status.value,
                    "created_at": inv.created_at.isoformat(),
                    "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None
                }
                for inv in invitations
            ]
        }

        session.close()
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_app.get("/api/dashboard/metrics/hourly")
async def get_hourly_metrics() -> Dict[str, Any]:
    """Get hourly metrics for charts"""
    try:
        session = get_session()

        # Get last 24 hours of metrics
        cutoff = datetime.now() - timedelta(hours=24)

        # This would query UsageAnalytics table
        hourly_data = []  # Placeholder for actual query

        session.close()

        return {
            "hourly_metrics": hourly_data,
            "period": "24_hours",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {"error": str(e)}


@dashboard_app.get("/api/dashboard/growth")
async def get_growth_metrics() -> Dict[str, Any]:
    """Get growth metrics over time"""
    try:
        session = get_session()

        # Calculate growth metrics
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Get user counts by period
        users_today = session.query(User).filter(
            User.created_at >= today
        ).count()

        users_yesterday = session.query(User).filter(
            User.created_at >= yesterday,
            User.created_at < today
        ).count()

        users_week = session.query(User).filter(
            User.created_at >= week_ago
        ).count()

        users_month = session.query(User).filter(
            User.created_at >= month_ago
        ).count()

        session.close()

        return {
            "daily_growth": {
                "today": users_today,
                "yesterday": users_yesterday,
                "change": calculate_percentage_change(users_yesterday, users_today)
            },
            "weekly_growth": {
                "this_week": users_week,
                "change": calculate_percentage_change(users_week, users_today * 7)
            },
            "monthly_growth": {
                "this_month": users_month,
                "change": calculate_percentage_change(users_month, users_today * 30)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {"error": str(e)}


@dashboard_app.post("/api/dashboard/broadcast")
async def send_broadcast_message(
    message: str,
    target_tier: Optional[str] = None,
    min_invites: Optional[int] = None
) -> Dict[str, Any]:
    """Send broadcast message to users (admin only)"""
    try:
        session = get_session()

        # Build query based on filters
        query = session.query(User)

        if target_tier:
            query = query.filter(User.tier == target_tier)

        if min_invites:
            query = query.filter(User.successful_invites >= min_invites)

        users = query.all()

        # In production, this would send actual messages
        broadcast_count = len(users)

        session.close()

        return {
            "success": True,
            "recipients": broadcast_count,
            "message": message,
            "filters": {
                "tier": target_tier,
                "min_invites": min_invites
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Helper Functions

def calculate_system_stats(session) -> Dict[str, Any]:
    """Calculate overall system statistics"""
    total_users = session.query(User).count()
    total_invitations = session.query(Invitation).count()
    accepted_invitations = session.query(Invitation).filter(
        Invitation.status == "accepted"
    ).count()

    voice_avatars = session.query(User).filter(
        User.voice_id.isnot(None)
    ).count()

    elevenlabs_avatars = session.query(User).filter(
        User.voice_service == "elevenlabs"
    ).count()

    conversion_rate = accepted_invitations / total_invitations if total_invitations > 0 else 0

    return {
        "total_users": total_users,
        "total_invitations": total_invitations,
        "voice_avatars": voice_avatars,
        "elevenlabs_avatars": elevenlabs_avatars,
        "conversion_rate": conversion_rate
    }


def get_tier_distribution(session) -> Dict[str, int]:
    """Get user distribution by tier"""
    distribution = {}

    for tier in ["free", "invited", "premium"]:
        count = session.query(User).filter(User.tier == tier).count()
        distribution[tier] = count

    return distribution


def get_recent_activity(session, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent system activity"""
    activities = []

    # Get recent invitations
    recent_invitations = session.query(Invitation).order_by(
        Invitation.created_at.desc()
    ).limit(limit).all()

    for inv in recent_invitations:
        activities.append({
            "type": "invitation_sent" if inv.status == "pending" else "invitation_accepted",
            "message": f"User invited someone" if inv.status == "pending" else "Invitation accepted",
            "timestamp": inv.created_at.isoformat()
        })

    # Sort by timestamp
    activities.sort(key=lambda x: x["timestamp"], reverse=True)

    return activities[:limit]


def anonymize_user_id(user_id: str) -> str:
    """Anonymize user ID for public display"""
    if len(user_id) > 8:
        return f"{user_id[:4]}...{user_id[-2:]}"
    return "User****"


def get_badge_for_invites(invite_count: int) -> str:
    """Get badge based on invitation count"""
    if invite_count >= 50:
        return "🏆 Ambassador"
    elif invite_count >= 25:
        return "⭐ Influencer"
    elif invite_count >= 10:
        return "🎯 Connector"
    elif invite_count >= 5:
        return "👥 Friend"
    else:
        return "🌱 Starter"


def calculate_percentage_change(old_value: int, new_value: int) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 100.0 if new_value > 0 else 0.0
    return ((new_value - old_value) / old_value) * 100


# WebSocket for real-time updates (optional)
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass


manager = ConnectionManager()


@dashboard_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time dashboard updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Admin endpoints

@dashboard_app.post("/api/admin/reset-user/{user_id}")
async def reset_user_progress(user_id: str) -> Dict[str, Any]:
    """Reset user's invitation progress (admin only)"""
    try:
        session = get_session()
        user = DatabaseQueries.get_user_by_id(session, user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Reset invitation counts
        user.invitations_sent = 0
        user.successful_invites = 0
        user.tier = "free"
        user.voice_service = "none"
        user.voice_id = None

        session.commit()
        session.close()

        return {
            "success": True,
            "message": f"User {user_id} progress reset"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(dashboard_app, host="0.0.0.0", port=8001)