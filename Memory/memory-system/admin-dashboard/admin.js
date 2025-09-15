// Admin Dashboard JavaScript

// API Configuration
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8080' 
    : `https://${window.location.hostname}:8080`;

// Global state
let authToken = localStorage.getItem('adminToken');
let currentAdmin = null;
let currentPage = 'overview';
let charts = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        verifyToken();
    } else {
        showLoginScreen();
    }
    
    initializeEventListeners();
});

// Event Listeners
function initializeEventListeners() {
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            if (page) {
                navigateToPage(page);
            }
        });
    });
    
    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // Menu toggle for mobile
    const menuToggle = document.querySelector('.menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            document.querySelector('.sidebar').classList.toggle('active');
        });
    }
    
    // User search
    const userSearch = document.getElementById('userSearch');
    if (userSearch) {
        userSearch.addEventListener('input', debounce(searchUsers, 300));
    }
    
    // Memory search
    const memorySearch = document.getElementById('memorySearch');
    if (memorySearch) {
        memorySearch.addEventListener('input', debounce(searchMemories, 300));
    }
    
    // Notification form
    const notificationForm = document.getElementById('notificationForm');
    if (notificationForm) {
        notificationForm.addEventListener('submit', handleSendNotification);
    }
    
    // Config form
    const configForm = document.getElementById('configForm');
    if (configForm) {
        configForm.addEventListener('submit', handleSaveConfig);
    }
    
    // Analytics period
    const analyticsPeriod = document.getElementById('analyticsPeriod');
    if (analyticsPeriod) {
        analyticsPeriod.addEventListener('change', loadAnalytics);
    }
    
    // Log filters
    const logLevel = document.getElementById('logLevel');
    if (logLevel) {
        logLevel.addEventListener('change', loadSystemLogs);
    }
    
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener('click', loadSystemLogs);
    }
    
    // Modal close buttons
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            closeBtn.closest('.modal').style.display = 'none';
        });
    });
}

// Authentication Functions
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('loginError');
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            authToken = data.token;
            currentAdmin = data.admin;
            localStorage.setItem('adminToken', authToken);
            showDashboard();
            loadDashboardData();
        } else {
            errorDiv.textContent = data.error || 'Login failed';
        }
    } catch (error) {
        console.error('Login error:', error);
        errorDiv.textContent = 'Connection error. Please try again.';
    }
}

async function verifyToken() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/profile`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            currentAdmin = data;
            showDashboard();
            loadDashboardData();
        } else {
            showLoginScreen();
        }
    } catch (error) {
        console.error('Token verification error:', error);
        showLoginScreen();
    }
}

function handleLogout() {
    localStorage.removeItem('adminToken');
    authToken = null;
    currentAdmin = null;
    showLoginScreen();
}

function showLoginScreen() {
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('dashboard').style.display = 'none';
}

function showDashboard() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'flex';
    
    // Update admin info
    if (currentAdmin) {
        document.getElementById('adminName').textContent = currentAdmin.username || 'Admin';
        document.getElementById('adminRole').textContent = currentAdmin.role || 'Admin';
    }
}

// Navigation
function navigateToPage(page) {
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });
    
    // Hide all pages
    document.querySelectorAll('.page-content').forEach(pageEl => {
        pageEl.style.display = 'none';
    });
    
    // Show selected page
    const pageElement = document.getElementById(`${page}Page`);
    if (pageElement) {
        pageElement.style.display = 'block';
    }
    
    // Update page title
    const titles = {
        overview: 'Dashboard Overview',
        users: 'User Management',
        memories: 'Memory Management',
        analytics: 'Analytics',
        games: 'Gaming Statistics',
        communications: 'Communications',
        logs: 'System Logs',
        config: 'Configuration'
    };
    
    document.getElementById('pageTitle').textContent = titles[page] || 'Dashboard';
    
    // Load page-specific data
    currentPage = page;
    loadPageData(page);
}

// Load page data
async function loadPageData(page) {
    switch (page) {
        case 'overview':
            loadDashboardData();
            break;
        case 'users':
            loadUsers();
            break;
        case 'memories':
            loadMemories();
            break;
        case 'analytics':
            loadAnalytics();
            break;
        case 'games':
            loadGamesStats();
            break;
        case 'communications':
            loadCommunications();
            break;
        case 'logs':
            loadSystemLogs();
            loadAuditLogs();
            break;
        case 'config':
            loadConfiguration();
            break;
    }
}

// Dashboard Overview
async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/dashboard`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateDashboardStats(data);
            updateCharts(data);
            updateRecentActivity();
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateDashboardStats(data) {
    // Update user stats
    document.getElementById('totalUsers').textContent = data.users?.total || 0;
    document.getElementById('newUsersToday').textContent = data.users?.new_today || 0;
    document.getElementById('activeUsers').textContent = data.users?.active_today || 0;
    
    // Update memory stats
    document.getElementById('totalMemories').textContent = data.memories?.total || 0;
    document.getElementById('memorieToday').textContent = data.memories?.today || 0;
    
    // Update system status
    const systemStatus = data.system?.status || 'Unknown';
    document.getElementById('systemStatus').textContent = systemStatus;
    
    // Update communication channels
    document.getElementById('whatsappCount').textContent = data.communications?.whatsapp || 0;
    document.getElementById('telegramCount').textContent = data.communications?.telegram || 0;
    document.getElementById('smsCount').textContent = data.communications?.sms || 0;
    document.getElementById('voiceCount').textContent = data.communications?.voice || 0;
}

function updateCharts(data) {
    // User Growth Chart
    const userCtx = document.getElementById('userGrowthChart');
    if (userCtx) {
        if (charts.userGrowth) {
            charts.userGrowth.destroy();
        }
        
        charts.userGrowth = new Chart(userCtx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'New Users',
                    data: [12, 19, 15, 25, 22, 30, 28],
                    borderColor: '#5e72e4',
                    backgroundColor: 'rgba(94, 114, 228, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Memory Activity Chart
    const memoryCtx = document.getElementById('memoryActivityChart');
    if (memoryCtx) {
        if (charts.memoryActivity) {
            charts.memoryActivity.destroy();
        }
        
        charts.memoryActivity = new Chart(memoryCtx, {
            type: 'bar',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Memories Created',
                    data: [65, 59, 80, 81, 56, 55, 40],
                    backgroundColor: '#2dce89'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

async function updateRecentActivity() {
    const activityList = document.getElementById('recentActivity');
    if (!activityList) return;
    
    // Sample activity data - in production, fetch from API
    const activities = [
        {
            icon: 'fa-user-plus',
            text: 'New user registered',
            detail: 'Phone: +1234567890',
            time: '2 minutes ago'
        },
        {
            icon: 'fa-memory',
            text: 'Memory created',
            detail: 'Category: Personal',
            time: '5 minutes ago'
        },
        {
            icon: 'fa-gamepad',
            text: 'Game session started',
            detail: 'Memory Challenge',
            time: '10 minutes ago'
        },
        {
            icon: 'fa-comment',
            text: 'WhatsApp message received',
            detail: 'User: Alice',
            time: '15 minutes ago'
        }
    ];
    
    activityList.innerHTML = activities.map(activity => `
        <div class="activity-item">
            <div class="activity-icon">
                <i class="fas ${activity.icon}"></i>
            </div>
            <div class="activity-details">
                <strong>${activity.text}</strong>
                <p>${activity.detail}</p>
            </div>
            <span class="activity-time">${activity.time}</span>
        </div>
    `).join('');
}

// User Management
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/users`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayUsers(data.users);
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.id || 'N/A'}</td>
            <td>${user.name || 'Unknown'}</td>
            <td>${user.phone_number || 'N/A'}</td>
            <td>${user.memory_count || 0}</td>
            <td>
                <span class="badge ${user.subscription_status === 'active' ? 'success' : 'warning'}">
                    ${user.subscription_status || 'Free'}
                </span>
            </td>
            <td>${formatDate(user.created_at)}</td>
            <td>
                <button class="btn-action" onclick="viewUserDetails('${user.id}')">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn-action danger" onclick="suspendUser('${user.id}')">
                    <i class="fas fa-ban"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function searchUsers(e) {
    const search = e.target.value;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/users?search=${encodeURIComponent(search)}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayUsers(data.users);
        }
    } catch (error) {
        console.error('Error searching users:', error);
    }
}

async function viewUserDetails(userId) {
    try {
        const response = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            showUserModal(data);
        }
    } catch (error) {
        console.error('Error loading user details:', error);
    }
}

function showUserModal(userData) {
    const modal = document.getElementById('userModal');
    const details = document.getElementById('userDetails');
    
    if (userData.user) {
        details.innerHTML = `
            <div class="user-details">
                <p><strong>ID:</strong> ${userData.user.id}</p>
                <p><strong>Name:</strong> ${userData.user.name || 'Unknown'}</p>
                <p><strong>Phone:</strong> ${userData.user.phone_number}</p>
                <p><strong>Created:</strong> ${formatDate(userData.user.created_at)}</p>
                <p><strong>Last Seen:</strong> ${formatDate(userData.user.last_seen)}</p>
                <p><strong>Total Memories:</strong> ${userData.stats?.total_memories || 0}</p>
                <h4>Recent Memories</h4>
                <div class="recent-memories">
                    ${userData.recent_memories?.map(mem => `
                        <div class="memory-preview">
                            <p>${mem.content}</p>
                            <small>${formatDate(mem.created_at)}</small>
                        </div>
                    `).join('') || '<p>No memories found</p>'}
                </div>
            </div>
        `;
    }
    
    modal.style.display = 'block';
}

async function suspendUser(userId) {
    if (!confirm('Are you sure you want to suspend this user?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/users/${userId}/suspend`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason: 'Admin suspension' })
        });
        
        if (response.ok) {
            alert('User suspended successfully');
            loadUsers();
        }
    } catch (error) {
        console.error('Error suspending user:', error);
        alert('Failed to suspend user');
    }
}

// Memory Management
async function loadMemories() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/memories`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayMemories(data.memories);
        }
    } catch (error) {
        console.error('Error loading memories:', error);
    }
}

function displayMemories(memories) {
    const grid = document.getElementById('memoriesGrid');
    if (!grid) return;
    
    grid.innerHTML = memories.map(memory => {
        const categoryColors = {
            personal: '#5e72e4',
            work: '#fb6340',
            ideas: '#2dce89',
            reminders: '#11cdef'
        };
        
        return `
            <div class="memory-card" onclick="viewMemoryDetails('${memory.id}')">
                <div class="memory-header">
                    <span class="memory-category" style="background: ${categoryColors[memory.category] || '#8898aa'}">
                        ${memory.category || 'uncategorized'}
                    </span>
                    <button class="btn-action danger" onclick="deleteMemory('${memory.id}', event)">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="memory-content">
                    ${memory.content?.substring(0, 150) || 'No content'}...
                </div>
                <div class="memory-footer">
                    <span>${memory.user_id}</span>
                    <span>${formatDate(memory.created_at)}</span>
                </div>
            </div>
        `;
    }).join('');
}

async function searchMemories(e) {
    const search = e.target.value;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/memories?search=${encodeURIComponent(search)}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayMemories(data.memories);
        }
    } catch (error) {
        console.error('Error searching memories:', error);
    }
}

async function deleteMemory(memoryId, event) {
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this memory?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/memories/${memoryId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason: 'Admin deletion' })
        });
        
        if (response.ok) {
            loadMemories();
        }
    } catch (error) {
        console.error('Error deleting memory:', error);
        alert('Failed to delete memory');
    }
}

// Analytics
async function loadAnalytics() {
    const period = document.getElementById('analyticsPeriod')?.value || '7days';
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/analytics?period=${period}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateAnalyticsCharts(data);
            updateMetrics(data);
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function updateAnalyticsCharts(data) {
    // Engagement Chart
    const engagementCtx = document.getElementById('engagementChart');
    if (engagementCtx) {
        if (charts.engagement) charts.engagement.destroy();
        
        charts.engagement = new Chart(engagementCtx, {
            type: 'line',
            data: {
                labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
                datasets: [{
                    label: 'Daily Active Users',
                    data: [120, 135, 125, 145, 160, 155, 170],
                    borderColor: '#5e72e4',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Categories Chart
    const categoriesCtx = document.getElementById('categoriesChart');
    if (categoriesCtx) {
        if (charts.categories) charts.categories.destroy();
        
        charts.categories = new Chart(categoriesCtx, {
            type: 'doughnut',
            data: {
                labels: data.memory_stats?.popular_categories?.map(c => c.name) || ['Personal', 'Work', 'Ideas'],
                datasets: [{
                    data: data.memory_stats?.popular_categories?.map(c => c.count) || [45, 30, 25],
                    backgroundColor: ['#5e72e4', '#fb6340', '#2dce89']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

function updateMetrics(data) {
    const retention = data.engagement?.retention_rate || 0;
    document.getElementById('retentionRate').textContent = `${retention}%`;
    document.getElementById('retentionProgress').style.width = `${retention}%`;
    
    document.getElementById('avgSessionDuration').textContent = 
        data.engagement?.avg_session_duration || '0m';
    
    document.getElementById('dauCount').textContent = 
        data.engagement?.daily_active_users || 0;
}

// Gaming Statistics
async function loadGamesStats() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/games`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateGameStats(data);
        }
    } catch (error) {
        console.error('Error loading game stats:', error);
    }
}

function updateGameStats(data) {
    document.getElementById('activeGames').textContent = data.active_games || 0;
    document.getElementById('totalPlayers').textContent = data.total_players || 0;
    document.getElementById('challengesToday').textContent = data.challenges_today || 0;
    
    const leaderboard = document.getElementById('gameLeaderboard');
    if (leaderboard && data.top_players) {
        leaderboard.innerHTML = data.top_players.map((player, index) => `
            <div class="leaderboard-entry">
                <span class="rank">#${index + 1}</span>
                <span class="player">${player.user_id}</span>
                <span class="score">${player.score} pts</span>
            </div>
        `).join('');
    }
}

// Communications
async function loadCommunications() {
    // Load recent communications
    // This would fetch from API in production
}

async function handleSendNotification(e) {
    e.preventDefault();
    
    const notification = {
        title: document.getElementById('notifTitle').value,
        message: document.getElementById('notifMessage').value,
        target: document.getElementById('notifTarget').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/notifications`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(notification)
        });
        
        if (response.ok) {
            alert('Notification sent successfully');
            e.target.reset();
        }
    } catch (error) {
        console.error('Error sending notification:', error);
        alert('Failed to send notification');
    }
}

// System Logs
async function loadSystemLogs() {
    const level = document.getElementById('logLevel')?.value || '';
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/logs?level=${level}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayLogs(data.logs);
        }
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

function displayLogs(logs) {
    const viewer = document.getElementById('logViewer');
    if (!viewer) return;
    
    const levelColors = {
        INFO: '#2dce89',
        WARNING: '#fb6340',
        ERROR: '#f5365c',
        DEBUG: '#8898aa'
    };
    
    viewer.innerHTML = logs.map(log => `
        <div class="log-entry">
            <span class="log-time">${formatDate(log.timestamp)}</span>
            <span class="log-level" style="color: ${levelColors[log.level]}">
                [${log.level}]
            </span>
            <span class="log-module">${log.module}</span>
            <span class="log-message">${log.message}</span>
        </div>
    `).join('');
}

async function loadAuditLogs() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/audit-logs`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayAuditLogs(data.logs);
        }
    } catch (error) {
        console.error('Error loading audit logs:', error);
    }
}

function displayAuditLogs(logs) {
    const container = document.getElementById('auditLogs');
    if (!container) return;
    
    container.innerHTML = logs.map(log => `
        <div class="audit-entry">
            <div class="audit-header">
                <strong>${log.username || 'Unknown'}</strong>
                <span>${formatDate(log.timestamp)}</span>
            </div>
            <div class="audit-action">
                ${log.action}
                ${log.target_type ? ` - ${log.target_type}` : ''}
                ${log.target_id ? ` (${log.target_id})` : ''}
            </div>
        </div>
    `).join('');
}

// Configuration
async function loadConfiguration() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/config`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const config = await response.json();
            updateConfigForm(config);
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
    }
}

function updateConfigForm(config) {
    document.getElementById('platformName').value = config.platform_name || 'Memory App';
    document.getElementById('maintenanceMode').checked = config.maintenance_mode || false;
    document.getElementById('maxMemories').value = config.limits?.max_memories_per_user || 1000;
    document.getElementById('maxFileSize').value = config.limits?.max_file_size_mb || 10;
    
    // Feature toggles
    document.getElementById('whatsappEnabled').checked = config.features?.whatsapp !== false;
    document.getElementById('telegramEnabled').checked = config.features?.telegram !== false;
    document.getElementById('voiceAuthEnabled').checked = config.features?.voice_auth !== false;
    document.getElementById('gamingEnabled').checked = config.features?.gaming !== false;
}

async function handleSaveConfig(e) {
    e.preventDefault();
    
    const config = {
        platform_name: document.getElementById('platformName').value,
        maintenance_mode: document.getElementById('maintenanceMode').checked,
        limits: {
            max_memories_per_user: parseInt(document.getElementById('maxMemories').value),
            max_file_size_mb: parseInt(document.getElementById('maxFileSize').value)
        },
        features: {
            whatsapp: document.getElementById('whatsappEnabled').checked,
            telegram: document.getElementById('telegramEnabled').checked,
            voice_auth: document.getElementById('voiceAuthEnabled').checked,
            gaming: document.getElementById('gamingEnabled').checked
        }
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/config`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            alert('Configuration saved successfully');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        alert('Failed to save configuration');
    }
}

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-refresh dashboard data
setInterval(() => {
    if (authToken && currentPage === 'overview') {
        loadDashboardData();
    }
}, 30000); // Refresh every 30 seconds

// Additional styles for action buttons
const style = document.createElement('style');
style.textContent = `
    .btn-action {
        padding: 5px 10px;
        margin: 0 2px;
        border: none;
        border-radius: 4px;
        background: #5e72e4;
        color: white;
        cursor: pointer;
        font-size: 12px;
    }
    
    .btn-action:hover {
        background: #4c63d2;
    }
    
    .btn-action.danger {
        background: #f5365c;
    }
    
    .btn-action.danger:hover {
        background: #ec0c38;
    }
    
    .badge.success {
        background: #2dce89;
    }
    
    .badge.warning {
        background: #fb6340;
    }
    
    .log-entry {
        font-family: monospace;
        font-size: 12px;
        padding: 5px;
        border-bottom: 1px solid #e9ecef;
    }
    
    .audit-entry {
        padding: 10px;
        background: #f7fafc;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    
    .leaderboard-entry {
        display: flex;
        justify-content: space-between;
        padding: 10px;
        background: #f7fafc;
        border-radius: 5px;
        margin-bottom: 5px;
    }
`;
document.head.appendChild(style);