"""
Invitation Dashboard
Web-based dashboard for managing invitations and viewing stats
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json

from .gamified_voice_avatar import get_gamification_system
from .database_models import SessionLocal, User, Invitation, InvitationStatus
from .dashboard_auth import (
    dashboard_auth,
    get_current_user,
    require_admin,
    require_csrf,
    LoginRequest,
    TokenResponse
)

logger = logging.getLogger(__name__)

class InvitationDashboard:
    """
    Web dashboard for invitation management
    """
    
    def __init__(self, app: FastAPI = None):
        """Initialize dashboard"""
        self.app = app
        self.system = get_gamification_system()
        self.db = SessionLocal()
        
        # Setup routes if app provided
        if app:
            self.setup_routes(app)
        
        logger.info("✅ Invitation Dashboard initialized")
    
    def setup_routes(self, app: FastAPI):
        """Setup dashboard routes"""
        
        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Render main dashboard page"""
            return self.render_dashboard()
        
        @app.get("/dashboard/api/stats")
        async def get_stats():
            """Get overall system statistics"""
            return await self.get_system_stats()
        
        @app.get("/dashboard/api/users")
        async def list_users():
            """Get list of all users"""
            return await self.get_users_list()
        
        @app.get("/dashboard/api/invitations")
        async def list_invitations(
            status: Optional[str] = None,
            limit: int = 100
        ):
            """Get list of invitations"""
            return await self.get_invitations_list(status, limit)
        
        @app.get("/dashboard/api/leaderboard")
        async def get_leaderboard(
            metric: str = "points",
            period: str = "all_time",
            limit: int = 10
        ):
            """Get leaderboard data"""
            return await self.system.get_leaderboard(metric, period, limit)
        
        @app.post("/dashboard/api/invitations/revoke/{invitation_id}")
        async def revoke_invitation(invitation_id: int):
            """Revoke an invitation"""
            return await self.revoke_invitation(invitation_id)
    
    def render_login_page(self, error: str = None) -> str:
        """Render the login page HTML"""
        error_html = f'<div class="error-message">{error}</div>' if error else ''
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Login</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-container {{
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 500;
        }}
        input {{
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 16px;
        }}
        input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.3s ease;
        }}
        button:hover {{ opacity: 0.9; }}
        .error-message {{
            background: #fee;
            color: #c00;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .info-text {{
            text-align: center;
            color: #999;
            margin-top: 20px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🎮 Dashboard Login</h1>
        {error_html}
        <form action="/dashboard/api/login" method="POST">
            <div class="form-group">
                <label for="phone">Phone Number</label>
                <input type="tel" id="phone" name="phone" placeholder="+1234567890" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required>
            </div>
            <button type="submit">Login</button>
        </form>
        <div class="info-text">
            Admin: Use ADMIN_PHONE and ADMIN_PASSWORD<br>
            Users: Password is last 4 digits of phone
        </div>
    </div>
</body>
</html>
"""
        return html_template
    
    def render_dashboard(self, user_info: Dict[str, Any]) -> str:
        """Render the dashboard HTML with user info"""
        user_display = user_info.get('display_name', 'User')
        user_role = user_info.get('role', 'user')
        user_id = user_info.get('user_id', '')
        
        # Generate CSRF token for the session
        csrf_token = dashboard_auth.generate_csrf_token(user_id)
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gamification Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { 
            color: white; 
            font-size: 2.5rem; 
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }
        .card:hover { transform: translateY(-5px); }
        .card h2 { 
            color: #333; 
            font-size: 1.5rem; 
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .stat { 
            display: flex; 
            justify-content: space-between; 
            margin: 15px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .stat-label { 
            color: #666; 
            font-weight: 500;
        }
        .stat-value { 
            color: #333; 
            font-weight: bold;
            font-size: 1.2rem;
        }
        .leaderboard-entry {
            display: flex;
            align-items: center;
            padding: 12px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 8px;
            transition: background 0.3s ease;
        }
        .leaderboard-entry:hover { background: #e9ecef; }
        .rank { 
            width: 40px; 
            height: 40px; 
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 50%;
            font-weight: bold;
            margin-right: 15px;
        }
        .user-info { flex: 1; }
        .user-name { 
            font-weight: 600; 
            color: #333;
            margin-bottom: 3px;
        }
        .user-level { 
            color: #666; 
            font-size: 0.9rem;
        }
        .metric-value { 
            font-size: 1.3rem; 
            font-weight: bold;
            color: #667eea;
        }
        .invitation-row {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr 1fr 1fr;
            padding: 12px;
            margin: 8px 0;
            background: #f8f9fa;
            border-radius: 6px;
            align-items: center;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-pending { background: #ffc107; color: #333; }
        .status-sent { background: #17a2b8; color: white; }
        .status-accepted { background: #28a745; color: white; }
        .status-expired { background: #dc3545; color: white; }
        .btn {
            padding: 8px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: opacity 0.3s ease;
        }
        .btn:hover { opacity: 0.9; }
        .chart-container {
            height: 300px;
            margin-top: 20px;
        }
        #loading {
            text-align: center;
            padding: 40px;
            color: white;
            font-size: 1.2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 Gamification Dashboard</h1>
        
        <div id="loading">Loading dashboard data...</div>
        
        <div id="dashboard-content" style="display: none;">
            <div class="grid">
                <div class="card">
                    <h2>📊 System Stats</h2>
                    <div id="system-stats"></div>
                </div>
                
                <div class="card">
                    <h2>🏆 Top Players</h2>
                    <div id="leaderboard"></div>
                </div>
                
                <div class="card">
                    <h2>📈 Growth Metrics</h2>
                    <div id="growth-metrics"></div>
                    <div class="chart-container">
                        <canvas id="growth-chart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>📬 Recent Invitations</h2>
                <div id="invitations-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Dashboard JavaScript
        async function loadDashboard() {
            try {
                // Load system stats
                const statsResponse = await fetch('/dashboard/api/stats');
                const stats = await statsResponse.json();
                displaySystemStats(stats);
                
                // Load leaderboard
                const leaderboardResponse = await fetch('/dashboard/api/leaderboard');
                const leaderboard = await leaderboardResponse.json();
                displayLeaderboard(leaderboard);
                
                // Load invitations
                const invitationsResponse = await fetch('/dashboard/api/invitations?limit=10');
                const invitations = await invitationsResponse.json();
                displayInvitations(invitations);
                
                // Show dashboard
                document.getElementById('loading').style.display = 'none';
                document.getElementById('dashboard-content').style.display = 'block';
                
                // Auto-refresh every 30 seconds
                setInterval(loadDashboard, 30000);
                
            } catch (error) {
                console.error('Failed to load dashboard:', error);
                document.getElementById('loading').innerHTML = 
                    '<div style="color: #ff6b6b;">Failed to load dashboard data</div>';
            }
        }
        
        function displaySystemStats(stats) {
            const container = document.getElementById('system-stats');
            container.innerHTML = `
                <div class="stat">
                    <span class="stat-label">Total Users</span>
                    <span class="stat-value">${stats.total_users || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Active Users</span>
                    <span class="stat-value">${stats.active_users || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Invitations</span>
                    <span class="stat-value">${stats.total_invitations || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Acceptance Rate</span>
                    <span class="stat-value">${stats.acceptance_rate || 0}%</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Voice Avatars</span>
                    <span class="stat-value">${stats.total_avatars || 0}</span>
                </div>
            `;
        }
        
        function displayLeaderboard(leaderboard) {
            const container = document.getElementById('leaderboard');
            container.innerHTML = leaderboard.slice(0, 5).map(entry => `
                <div class="leaderboard-entry">
                    <div class="rank">${entry.rank}</div>
                    <div class="user-info">
                        <div class="user-name">${entry.user.display_name}</div>
                        <div class="user-level">Level ${entry.user.level}</div>
                    </div>
                    <div class="metric-value">${entry.metric_value}</div>
                </div>
            `).join('');
        }
        
        function displayInvitations(invitations) {
            const container = document.getElementById('invitations-list');
            
            if (invitations.length === 0) {
                container.innerHTML = '<p style="color: #666; text-align: center;">No invitations yet</p>';
                return;
            }
            
            container.innerHTML = invitations.map(inv => `
                <div class="invitation-row">
                    <div>${inv.code}</div>
                    <div>${inv.sender_name || inv.sender_id}</div>
                    <div>
                        <span class="status-badge status-${inv.status.toLowerCase()}">
                            ${inv.status}
                        </span>
                    </div>
                    <div>${new Date(inv.created_at).toLocaleDateString()}</div>
                    <div>
                        ${inv.status === 'PENDING' ? 
                            `<button class="btn" onclick="revokeInvitation(${inv.id})">Revoke</button>` : 
                            ''}
                    </div>
                </div>
            `).join('');
        }
        
        async function revokeInvitation(id) {
            if (!confirm('Are you sure you want to revoke this invitation?')) return;
            
            try {
                const response = await fetch(`/dashboard/api/invitations/revoke/${id}`, {
                    method: 'POST'
                });
                if (response.ok) {
                    loadDashboard();
                }
            } catch (error) {
                console.error('Failed to revoke invitation:', error);
            }
        }
        
        // Load dashboard on page load
        window.onload = loadDashboard;
    </script>
</body>
</html>
        """
        return html_template
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        try:
            # Query database for stats
            total_users = self.db.query(User).count()
            active_users = self.db.query(User).filter(
                User.total_invites_sent > 0
            ).count()
            
            total_invitations = self.db.query(Invitation).count()
            accepted_invitations = self.db.query(Invitation).filter(
                Invitation.status == InvitationStatus.ACCEPTED
            ).count()
            
            acceptance_rate = (
                (accepted_invitations / total_invitations * 100) 
                if total_invitations > 0 else 0
            )
            
            # Count voice avatars
            from .database_models import VoiceAvatar
            total_avatars = self.db.query(VoiceAvatar).count()
            
            # Get recent growth
            week_ago = datetime.utcnow() - timedelta(days=7)
            new_users_week = self.db.query(User).filter(
                User.created_at >= week_ago
            ).count()
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_invitations": total_invitations,
                "accepted_invitations": accepted_invitations,
                "acceptance_rate": round(acceptance_rate, 1),
                "total_avatars": total_avatars,
                "new_users_week": new_users_week,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}
    
    async def get_users_list(self) -> List[Dict[str, Any]]:
        """Get list of all users with stats"""
        try:
            users = self.db.query(User).order_by(
                User.points.desc()
            ).limit(100).all()
            
            return [
                {
                    "id": user.id,
                    "display_name": user.display_name,
                    "level": user.level,
                    "points": user.points,
                    "trust_score": round(user.trust_score, 2),
                    "invites_sent": user.total_invites_sent,
                    "invites_accepted": user.total_invites_accepted,
                    "voice_avatars": user.total_voice_avatars,
                    "is_premium": user.is_premium,
                    "created_at": user.created_at.isoformat()
                }
                for user in users
            ]
            
        except Exception as e:
            logger.error(f"Failed to get users list: {e}")
            return []
    
    async def get_invitations_list(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of invitations"""
        try:
            query = self.db.query(Invitation)
            
            if status:
                status_enum = InvitationStatus[status.upper()]
                query = query.filter(Invitation.status == status_enum)
            
            invitations = query.order_by(
                Invitation.created_at.desc()
            ).limit(limit).all()
            
            # Get sender names
            result = []
            for inv in invitations:
                sender = self.db.query(User).filter_by(id=inv.sender_id).first()
                
                result.append({
                    "id": inv.id,
                    "code": inv.code,
                    "sender_id": inv.sender_id,
                    "sender_name": sender.display_name if sender else None,
                    "recipient_id": inv.recipient_id,
                    "recipient_phone": inv.recipient_phone,
                    "status": inv.status.value,
                    "created_at": inv.created_at.isoformat(),
                    "sent_at": inv.sent_at.isoformat() if inv.sent_at else None,
                    "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
                    "expires_at": inv.expires_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get invitations: {e}")
            return []
    
    async def revoke_invitation(self, invitation_id: int) -> Dict[str, Any]:
        """Revoke an invitation"""
        try:
            invitation = self.db.query(Invitation).filter_by(id=invitation_id).first()
            
            if not invitation:
                return {"error": "Invitation not found"}
            
            if invitation.status != InvitationStatus.PENDING:
                return {"error": f"Cannot revoke invitation with status {invitation.status.value}"}
            
            invitation.status = InvitationStatus.REVOKED
            self.db.commit()
            
            return {"success": True, "message": "Invitation revoked"}
            
        except Exception as e:
            logger.error(f"Failed to revoke invitation: {e}")
            self.db.rollback()
            return {"error": str(e)}
    
    def close(self):
        """Close database connection"""
        self.db.close()

# Singleton instance
_dashboard = None

def get_invitation_dashboard(app: FastAPI = None) -> InvitationDashboard:
    """Get singleton dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = InvitationDashboard(app)
    return _dashboard