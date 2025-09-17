"""
Secure Invitation Dashboard with Authentication
Web-based dashboard for managing invitations and viewing stats with full security
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
    LoginRequest
)

logger = logging.getLogger(__name__)

class SecureInvitationDashboard:
    """
    Secure web dashboard for invitation management with authentication
    """
    
    def __init__(self, app: FastAPI = None):
        """Initialize dashboard"""
        self.app = app
        self.system = get_gamification_system()
        self.db = SessionLocal()
        
        # Setup routes if app provided
        if app:
            self.setup_routes(app)
        
        logger.info("✅ Secure Invitation Dashboard initialized")
    
    def setup_routes(self, app: FastAPI):
        """Setup dashboard routes with authentication"""
        
        @app.get("/dashboard/login", response_class=HTMLResponse)
        async def dashboard_login_page(request: Request):
            """Render login page"""
            return self.render_login_page()
        
        @app.post("/dashboard/api/login")
        async def dashboard_login(
            phone: str = Form(...),
            password: str = Form(...)
        ):
            """Process login request"""
            try:
                login_request = LoginRequest(phone=phone, password=password)
                token_response = await dashboard_auth.login(login_request)
                
                # Create response with redirect
                response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
                
                # Set cookie with token
                response.set_cookie(
                    key="access_token",
                    value=token_response.access_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=token_response.expires_in
                )
                
                return response
                
            except HTTPException as e:
                return HTMLResponse(
                    self.render_login_page(error=e.detail),
                    status_code=200  # Return 200 to show the page with error
                )
        
        @app.post("/dashboard/api/login/json")
        async def dashboard_login_json(
            phone: str = Form(...),
            password: str = Form(...)
        ):
            """JSON API for login"""
            login_request = LoginRequest(phone=phone, password=password)
            token_response = await dashboard_auth.login(login_request)
            return token_response.dict()
        
        @app.get("/dashboard/logout")
        async def dashboard_logout():
            """Logout and clear session"""
            response = RedirectResponse(url="/dashboard/login")
            response.delete_cookie("access_token")
            return response
        
        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard_home(
            request: Request,
            current_user: Dict = Depends(get_current_user)
        ):
            """Render main dashboard page - requires authentication"""
            return self.render_dashboard(current_user)
        
        @app.get("/dashboard/api/stats")
        async def get_stats(
            current_user: Dict = Depends(require_admin)
        ):
            """Get overall system statistics - Admin only"""
            return await self.get_system_stats()
        
        @app.get("/dashboard/api/user/stats")
        async def get_user_stats(
            current_user: Dict = Depends(get_current_user)
        ):
            """Get stats for current user"""
            return await self.get_user_specific_stats(current_user['user_id'])
        
        @app.get("/dashboard/api/users")
        async def list_users(
            current_user: Dict = Depends(require_admin)
        ):
            """Get list of all users - Admin only"""
            return await self.get_users_list()
        
        @app.get("/dashboard/api/invitations")
        async def list_invitations(
            status: Optional[str] = None,
            limit: int = 100,
            current_user: Dict = Depends(get_current_user)
        ):
            """Get list of invitations"""
            # Non-admins can only see their own invitations
            user_filter = None if current_user.get("role") == "admin" else current_user["user_id"]
            return await self.get_invitations_list(status, limit, user_filter)
        
        @app.get("/dashboard/api/leaderboard")
        async def get_leaderboard(
            metric: str = "points",
            period: str = "all_time",
            limit: int = 10,
            current_user: Dict = Depends(get_current_user)
        ):
            """Get leaderboard data"""
            return await self.system.get_leaderboard(metric, period, limit)
        
        @app.post("/dashboard/api/invitations/revoke/{invitation_id}")
        async def revoke_invitation(
            invitation_id: int,
            request: Request,
            current_user: Dict = Depends(get_current_user),
            csrf_token: str = Form(...)
        ):
            """Revoke an invitation - requires CSRF token"""
            # Verify CSRF
            dashboard_auth.verify_csrf_for_request(request, current_user["user_id"], csrf_token)
            
            # Check ownership or admin
            db = SessionLocal()
            try:
                invitation = db.query(Invitation).filter(Invitation.id == invitation_id).first()
                if not invitation:
                    raise HTTPException(status_code=404, detail="Invitation not found")
                
                if current_user.get("role") != "admin" and invitation.sender_id != current_user["user_id"]:
                    raise HTTPException(status_code=403, detail="Not authorized to revoke this invitation")
                
                return await self.revoke_invitation(invitation_id)
            finally:
                db.close()
    
    def render_login_page(self, error: str = None) -> str:
        """Render the login page HTML"""
        error_html = f'<div class="error-message">{error}</div>' if error else ''
        
        # Return login page HTML without f-string issues
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 16px;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
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
        }
        button:hover { opacity: 0.9; }
        .error-message {
            background: #fee;
            color: #c00;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .info-text {
            text-align: center;
            color: #999;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🎮 Dashboard Login</h1>
        ''' + error_html + '''
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
</html>'''
        return html_template
    
    def render_dashboard(self, user_info: Dict[str, Any]) -> str:
        """Render the dashboard HTML with user info and authentication"""
        user_display = user_info.get('display_name', 'User')
        user_role = user_info.get('role', 'user')
        user_id = user_info.get('user_id', '')
        is_admin = user_role == 'admin'
        
        # Generate CSRF token for the session
        csrf_token = dashboard_auth.generate_csrf_token(user_id)
        
        # Admin-only sections
        admin_sections = '''
                <div class="card">
                    <h2>📊 System Stats</h2>
                    <div id="system-stats"></div>
                </div>
        ''' if is_admin else ''
        
        # Return dashboard HTML
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gamification Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        h1 { 
            color: white; 
            font-size: 2.5rem; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .user-info {
            color: white;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .logout-btn {
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 6px;
            text-decoration: none;
            transition: background 0.3s ease;
        }
        .logout-btn:hover {
            background: rgba(255,255,255,0.3);
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
        .user-info-card { flex: 1; }
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
        #loading {
            text-align: center;
            padding: 40px;
            color: white;
            font-size: 1.2rem;
        }
        .error-banner {
            background: #ff6b6b;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Gamification Dashboard</h1>
            <div class="user-info">
                <span>Welcome, ''' + user_display + ''' (''' + user_role + ''')</span>
                <a href="/dashboard/logout" class="logout-btn">Logout</a>
            </div>
        </div>
        
        <div id="error-banner" class="error-banner"></div>
        
        <div id="loading">Loading dashboard data...</div>
        
        <div id="dashboard-content" style="display: none;">
            <div class="grid">
                ''' + admin_sections + '''
                
                <div class="card">
                    <h2>📊 My Stats</h2>
                    <div id="user-stats"></div>
                </div>
                
                <div class="card">
                    <h2>🏆 Top Players</h2>
                    <div id="leaderboard"></div>
                </div>
            </div>
            
            <div class="card">
                <h2>📬 My Invitations</h2>
                <div id="invitations-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Store CSRF token
        const csrfToken = "''' + csrf_token + '''";
        const isAdmin = ''' + ('true' if is_admin else 'false') + ''';
        
        // Get token from cookie
        function getCookie(name) {
            const value = "; " + document.cookie;
            const parts = value.split("; " + name + "=");
            if (parts.length === 2) return parts.pop().split(";").shift();
            return null;
        }
        
        // API request with authentication
        async function authenticatedFetch(url, options = {}) {
            const token = getCookie('access_token');
            
            const headers = {
                ...options.headers,
                'Authorization': `Bearer ${token}`
            };
            
            const response = await fetch(url, { ...options, headers });
            
            if (response.status === 401) {
                // Redirect to login on authentication failure
                window.location.href = '/dashboard/login';
                return null;
            }
            
            if (!response.ok) {
                const error = await response.text();
                throw new Error(error);
            }
            
            return response;
        }
        
        // Load dashboard data
        async function loadDashboard() {
            try {
                // Load system stats (admin only)
                if (isAdmin) {
                    const statsResponse = await authenticatedFetch('/dashboard/api/stats');
                    if (statsResponse) {
                        const stats = await statsResponse.json();
                        displaySystemStats(stats);
                    }
                }
                
                // Load user stats
                const userStatsResponse = await authenticatedFetch('/dashboard/api/user/stats');
                if (userStatsResponse) {
                    const userStats = await userStatsResponse.json();
                    displayUserStats(userStats);
                }
                
                // Load leaderboard
                const leaderboardResponse = await authenticatedFetch('/dashboard/api/leaderboard');
                if (leaderboardResponse) {
                    const leaderboard = await leaderboardResponse.json();
                    displayLeaderboard(leaderboard);
                }
                
                // Load invitations
                const invitationsResponse = await authenticatedFetch('/dashboard/api/invitations?limit=10');
                if (invitationsResponse) {
                    const invitations = await invitationsResponse.json();
                    displayInvitations(invitations);
                }
                
                // Show dashboard
                document.getElementById('loading').style.display = 'none';
                document.getElementById('dashboard-content').style.display = 'block';
                
            } catch (error) {
                console.error('Failed to load dashboard:', error);
                showError('Failed to load dashboard data: ' + error.message);
            }
        }
        
        function showError(message) {
            const banner = document.getElementById('error-banner');
            banner.textContent = message;
            banner.style.display = 'block';
            setTimeout(() => {
                banner.style.display = 'none';
            }, 5000);
        }
        
        function displaySystemStats(stats) {
            const container = document.getElementById('system-stats');
            if (!container) return;
            
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
            `;
        }
        
        function displayUserStats(stats) {
            const container = document.getElementById('user-stats');
            if (!container) return;
            
            container.innerHTML = `
                <div class="stat">
                    <span class="stat-label">My Level</span>
                    <span class="stat-value">${stats.level || 1}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">My Points</span>
                    <span class="stat-value">${stats.points || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Invites Sent</span>
                    <span class="stat-value">${stats.invites_sent || 0}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Trust Score</span>
                    <span class="stat-value">${(stats.trust_score || 0).toFixed(2)}</span>
                </div>
            `;
        }
        
        function displayLeaderboard(leaderboard) {
            const container = document.getElementById('leaderboard');
            if (!container || !leaderboard) return;
            
            container.innerHTML = leaderboard.slice(0, 5).map(entry => `
                <div class="leaderboard-entry">
                    <div class="rank">${entry.rank}</div>
                    <div class="user-info-card">
                        <div class="user-name">${entry.user.display_name || 'User'}</div>
                        <div class="user-level">Level ${entry.user.level || 1}</div>
                    </div>
                    <div class="metric-value">${entry.metric_value}</div>
                </div>
            `).join('');
        }
        
        function displayInvitations(invitations) {
            const container = document.getElementById('invitations-list');
            if (!container) return;
            
            if (!invitations || invitations.length === 0) {
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
                        ${inv.status === 'pending' ? 
                            `<button class="btn" onclick="revokeInvitation(${inv.id})">Revoke</button>` : 
                            ''}
                    </div>
                </div>
            `).join('');
        }
        
        async function revokeInvitation(id) {
            if (!confirm('Are you sure you want to revoke this invitation?')) return;
            
            try {
                const formData = new FormData();
                formData.append('csrf_token', csrfToken);
                
                const response = await authenticatedFetch(`/dashboard/api/invitations/revoke/${id}`, {
                    method: 'POST',
                    body: formData
                });
                
                if (response) {
                    loadDashboard();
                }
            } catch (error) {
                showError('Failed to revoke invitation: ' + error.message);
            }
        }
        
        // Load dashboard on page load
        window.onload = () => {
            loadDashboard();
            // Auto-refresh every 60 seconds
            setInterval(loadDashboard, 60000);
        };
    </script>
</body>
</html>'''
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
    
    async def get_user_specific_stats(self, user_id: str) -> Dict[str, Any]:
        """Get stats for a specific user"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            return {
                "user_id": user.id,
                "display_name": user.display_name,
                "level": user.level,
                "points": user.points,
                "trust_score": round(user.trust_score, 2),
                "invites_sent": user.total_invites_sent,
                "invites_accepted": user.total_invites_accepted,
                "voice_avatars": user.total_voice_avatars,
                "contact_slots": user.total_contact_slots,
                "used_slots": user.used_contact_slots,
                "is_premium": user.is_premium,
                "created_at": user.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
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
        limit: int = 100,
        user_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of invitations"""
        try:
            query = self.db.query(Invitation)
            
            # Filter by user if not admin
            if user_filter:
                query = query.filter(Invitation.sender_id == user_filter)
            
            # Filter by status
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
            
            logger.info(f"Invitation {invitation_id} revoked successfully")
            
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

def get_secure_invitation_dashboard(app: FastAPI = None) -> SecureInvitationDashboard:
    """Get singleton secure dashboard instance"""
    global _dashboard
    if _dashboard is None:
        _dashboard = SecureInvitationDashboard(app)
    return _dashboard