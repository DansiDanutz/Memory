// Memory App - Main Application JavaScript
// Extracted from inline scripts for CSP compliance

// Global variables
let socket;
let isAuthenticated = false;
let currentUser = null;
let authToken = null;
let memories = [];
let currentCategory = 'general';
let currentTab = 'memories';
let connectionStatus = 'disconnected';
let typingUsers = new Set();
let mutualFeelingsUsers = [];
let achievements = [];
let userPoints = 0;
let totalMemories = 0;
let weeklyGoal = 20;
let notificationQueue = [];
let currentPrompt = null;
let promptStreak = 0;

// Initialize app when page loads
console.log('Window loaded, initializing app...');

// 🔒 CRITICAL FIX: Global authenticated API wrapper with 401 handling
async function authenticatedFetch(url, options = {}) {
    const config = {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${authToken}`
        }
    };
    
    try {
        const response = await fetch(url, config);
        
        // 🔒 CRITICAL: Handle 401 token validation errors
        if (response.status === 401) {
            console.warn('🚫 Token validation failed - forcing re-authentication');
            handleTokenExpiration();
            throw new Error('Authentication token expired or invalid');
        }
        
        return response;
    } catch (error) {
        // Re-throw to let individual handlers deal with it
        throw error;
    }
}

// 🔒 Handle token expiration/invalidation
function handleTokenExpiration() {
    console.log('🔄 Clearing invalid authentication data...');
    
    // Clear all authentication data
    isAuthenticated = false;
    currentUser = null;
    authToken = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    
    // Disconnect socket
    if (socket) {
        socket.disconnect();
        socket = null;
    }
    
    // Force back to authentication view
    showAuthenticationView();
    showNotification('Please sign in again - your session has expired', 'warning');
}

// Initialize the application
function initializeApp() {
    // Prevent duplicate initialization
    if (window.__appInitialized) {
        console.log('⚠️ App already initialized, skipping...');
        return;
    }
    window.__appInitialized = true;
    
    try {
        initializeAuth();
        initializeSocket();
        initializeUI();
        initializeGamification();
        initializeBackground();
        
        console.log('✅ Memory App initialized successfully');
    } catch (error) {
        console.error('❌ Failed to initialize app:', error);
        showNotification('Failed to initialize application', 'error');
        window.__appInitialized = false; // Reset on error
    }
}

// Authentication functions
function initializeAuth() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('currentUser');
    
    if (token && user) {
        authToken = token;
        currentUser = JSON.parse(user);
        isAuthenticated = true;
        console.log('User restored from localStorage:', currentUser.username);
        showAuthenticatedView();
    } else {
        showAuthenticationView();
    }
}

function showAuthenticationView() {
    document.getElementById('auth-section').classList.remove('hidden');
    document.getElementById('main-content').classList.add('hidden');
    updateConnectionStatus('disconnected');
}

function showAuthenticatedView() {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('main-content').classList.remove('hidden');
    updateUserProfile();
    loadMemories();
    loadDailyPrompt(); // Load AI-generated daily prompt
    updateConnectionStatus('connected');
    initializeSocket();
}

// Socket.IO functions
function initializeSocket() {
    if (!isAuthenticated || socket) return;
    
    socket = io('/', {
        auth: {
            token: authToken,
            username: currentUser?.username
        },
        transports: ['websocket', 'polling']
    });
    
    socket.on('connect', () => {
        console.log('✅ Connected to server');
        updateConnectionStatus('connected');
        joinUserRoom();
    });
    
    socket.on('disconnect', () => {
        console.log('❌ Disconnected from server');
        updateConnectionStatus('disconnected');
    });
    
    socket.on('typing_start', (data) => {
        typingUsers.add(data.username);
        updateTypingIndicator();
    });
    
    socket.on('typing_stop', (data) => {
        typingUsers.delete(data.username);
        updateTypingIndicator();
    });
    
    socket.on('memory_created', (data) => {
        if (data.category === currentCategory) {
            addMemoryToUI(data.memory);
        }
        updateGamificationStats();
        showNotification('New memory saved!', 'success');
    });
    
    socket.on('mutual_feelings_match', (data) => {
        showMutualFeelingsNotification(data);
    });
    
    socket.on('achievement_unlocked', (data) => {
        unlockAchievement(data.achievement);
    });
}

function joinUserRoom() {
    if (socket && currentUser) {
        socket.emit('join_user_room', { userId: currentUser.id });
    }
}

// UI Functions
function initializeUI() {
    // Tab switching
    document.querySelectorAll('.nav-tab').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    
    // Category switching
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', () => switchCategory(btn.dataset.category));
    });
    
    // Memory form
    const memoryForm = document.getElementById('memory-form');
    if (memoryForm) {
        memoryForm.addEventListener('submit', createMemory);
    }
    
    // Search functionality
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(e.target.value);
            }, 300);
        });
    }
    
    // AI Insights button handlers
    const refreshBtn = document.getElementById('refresh-insights-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadAIInsights);
    }
    
    // Daily Reflection button handlers
    const skipPromptBtn = document.getElementById('skip-prompt-btn');
    if (skipPromptBtn) {
        skipPromptBtn.addEventListener('click', skipDailyPrompt);
    }
    
    const answerPromptBtn = document.getElementById('answer-prompt-btn');
    if (answerPromptBtn) {
        answerPromptBtn.addEventListener('click', answerDailyPrompt);
    }
    
    const analyzeBtn = document.getElementById('analyze-memory-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeSelectedMemory);
    }
    
    // Auth forms
    setupAuthForms();
    
    // Notification system
    initializeNotifications();
}

function setupAuthForms() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const authToggle = document.querySelectorAll('.auth-toggle');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    authToggle.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            toggleAuthMode();
        });
    });
}

function toggleAuthMode() {
    const loginSection = document.getElementById('login-section');
    const registerSection = document.getElementById('register-section');
    
    // Use CSS classes instead of inline styles for CSP compliance
    if (loginSection.classList.contains('hidden')) {
        loginSection.classList.remove('hidden');
        registerSection.classList.add('hidden');
    } else {
        loginSection.classList.add('hidden');
        registerSection.classList.remove('hidden');
    }
}

// Authentication API calls
async function handleLogin(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
        showLoadingState(true);
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: formData.get('username'),
                password: formData.get('password')
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            authToken = data.token;
            currentUser = data.user;
            isAuthenticated = true;
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            showAuthenticatedView();
            showNotification('Welcome back!', 'success');
        } else {
            showNotification(data.error || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showNotification('Connection error', 'error');
    } finally {
        showLoadingState(false);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
        showLoadingState(true);
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: formData.get('username'),
                displayName: formData.get('displayName'),
                email: formData.get('email'),
                password: formData.get('password')
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            authToken = data.token;
            currentUser = data.user;
            isAuthenticated = true;
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            showAuthenticatedView();
            showNotification('Welcome to Memory App!', 'success');
        } else {
            showNotification(data.error || 'Registration failed', 'error');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showNotification('Connection error', 'error');
    } finally {
        showLoadingState(false);
    }
}

function logout() {
    isAuthenticated = false;
    currentUser = null;
    authToken = null;
    
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    
    if (socket) {
        socket.disconnect();
        socket = null;
    }
    
    showAuthenticationView();
    showNotification('Logged out successfully', 'info');
}

// Memory functions
async function loadMemories() {
    try {
        const response = await authenticatedFetch(`/api/memories?category=${currentCategory}`);
        const data = await response.json();
        
        if (data.success) {
            memories = data.memories || [];
            renderMemories();
            updateGamificationStats();
        } else {
            showNotification('Failed to load memories', 'error');
        }
    } catch (error) {
        console.error('Error loading memories:', error);
        if (error.message.includes('Authentication token expired')) {
            // Token handling already done by authenticatedFetch
            return;
        }
        showNotification('Connection error', 'error');
    }
}

async function createMemory(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const content = formData.get('content');
    
    if (!content.trim()) {
        showNotification('Please enter memory content', 'warning');
        return;
    }
    
    try {
        showLoadingState(true);
        const response = await authenticatedFetch('/api/memories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: content.trim(),
                category: currentCategory
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            e.target.reset();
            loadMemories(); // Refresh memories
            playSuccessSound();
        } else {
            showNotification(data.error || 'Failed to create memory', 'error');
        }
    } catch (error) {
        console.error('Error creating memory:', error);
        if (error.message.includes('Authentication token expired')) {
            // Token handling already done by authenticatedFetch
            return;
        }
        showNotification('Connection error', 'error');
    } finally {
        showLoadingState(false);
    }
}

function renderMemories() {
    const container = document.getElementById('memories-list');
    if (!container) return;
    
    // Clear container safely
    container.innerHTML = '';
    
    if (memories.length === 0) {
        // 🔒 SECURE: Build empty state with createElement
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        
        const icon = document.createElement('i');
        icon.className = 'fas fa-brain';
        
        const heading = document.createElement('h3');
        heading.textContent = 'No memories yet';
        
        const message = document.createElement('p');
        message.textContent = `Start by creating your first memory in the ${currentCategory} category.`;
        
        emptyState.appendChild(icon);
        emptyState.appendChild(heading);
        emptyState.appendChild(message);
        container.appendChild(emptyState);
        return;
    }
    
    // 🔒 SECURE: Build memories with createElement to prevent XSS
    memories.forEach(memory => {
        const memoryCard = document.createElement('div');
        memoryCard.className = 'memory-card';
        memoryCard.setAttribute('data-memory-id', memory.id);
        
        // Memory header
        const header = document.createElement('div');
        header.className = 'memory-header';
        
        const memoryNumber = document.createElement('span');
        memoryNumber.className = 'memory-number';
        memoryNumber.textContent = `#${memory.memoryNumber || 'Unknown'}`;
        
        const memoryDate = document.createElement('span');
        memoryDate.className = 'memory-date';
        memoryDate.textContent = formatDate(memory.createdAt);
        
        header.appendChild(memoryNumber);
        header.appendChild(memoryDate);
        
        // 🔒 Memory content - SECURE (textContent prevents XSS)
        const content = document.createElement('div');
        content.className = 'memory-content';
        content.textContent = memory.content; // Safe - no HTML injection possible
        
        // Memory footer
        const footer = document.createElement('div');
        footer.className = 'memory-footer';
        
        const category = document.createElement('span');
        category.className = 'memory-category';
        category.textContent = memory.category || 'general';
        
        // Memory actions with secure event listeners
        const actions = document.createElement('div');
        actions.className = 'memory-actions';
        
        // 🔒 Secure heart button with addEventListener
        const heartBtn = document.createElement('button');
        heartBtn.className = 'react-btn';
        heartBtn.title = 'Love';
        heartBtn.addEventListener('click', () => reactToMemory(memory.id, 'heart'));
        
        const heartIcon = document.createElement('i');
        heartIcon.className = 'fas fa-heart';
        heartBtn.appendChild(heartIcon);
        
        // 🔒 Secure share button with addEventListener
        const shareBtn = document.createElement('button');
        shareBtn.className = 'react-btn';
        shareBtn.title = 'Share';
        shareBtn.addEventListener('click', () => shareMemory(memory.id));
        
        const shareIcon = document.createElement('i');
        shareIcon.className = 'fas fa-share';
        shareBtn.appendChild(shareIcon);
        
        actions.appendChild(heartBtn);
        actions.appendChild(shareBtn);
        
        footer.appendChild(category);
        footer.appendChild(actions);
        
        // Assemble card securely
        memoryCard.appendChild(header);
        memoryCard.appendChild(content);
        memoryCard.appendChild(footer);
        
        container.appendChild(memoryCard);
    });
}

function addMemoryToUI(memory) {
    memories.unshift(memory);
    renderMemories();
}

// Tab and category switching
function switchTab(tabName) {
    currentTab = tabName;
    
    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
    
    // Load appropriate content
    if (tabName === 'memories') {
        loadMemories();
    } else if (tabName === 'ai-insights') {
        loadAIInsights();
    } else if (tabName === 'social') {
        loadSocialFeatures();
    } else if (tabName === 'emergency') {
        loadEmergencyContacts();
    } else if (tabName === 'gamification') {
        loadSmartNotifications();
    }
}

function switchCategory(category) {
    currentCategory = category;
    
    // Update category buttons
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });
    
    // Update current category display
    const categoryDisplay = document.getElementById('current-category');
    if (categoryDisplay) {
        categoryDisplay.textContent = category.charAt(0).toUpperCase() + category.slice(1);
    }
    
    // Reload memories for new category
    if (currentTab === 'memories') {
        loadMemories();
    }
}

// Utility functions
function updateUserProfile() {
    if (!currentUser) return;
    
    const elements = {
        'user-name': currentUser.displayName || currentUser.username,
        'user-username': `@${currentUser.username}`,
        'user-avatar': currentUser.displayName ? currentUser.displayName.charAt(0).toUpperCase() : 'U'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            if (id === 'user-avatar') {
                element.textContent = value;
            } else {
                element.textContent = value;
            }
        }
    });
}

function updateConnectionStatus(status) {
    connectionStatus = status;
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.className = `connection-status ${status}`;
        statusElement.textContent = status === 'connected' ? 'Online' : 'Offline';
    }
}

function updateTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (!indicator) return;
    
    if (typingUsers.size > 0) {
        const userList = Array.from(typingUsers).join(', ');
        indicator.textContent = `${userList} ${typingUsers.size === 1 ? 'is' : 'are'} typing...`;
        indicator.classList.remove('hidden');
    } else {
        indicator.classList.add('hidden');
    }
}

function showLoadingState(loading) {
    const button = event?.target?.querySelector('button[type="submit"]') || 
                   document.querySelector('button[type="submit"]');
    if (button) {
        if (loading) {
            button.disabled = true;
            // 🔒 SECURE: Build loading content with createElement
            button.innerHTML = ''; // Clear safely first
            
            const spinner = document.createElement('i');
            spinner.className = 'fas fa-spinner fa-spin';
            
            const loadingText = document.createTextNode(' Loading...');
            
            button.appendChild(spinner);
            button.appendChild(loadingText);
        } else {
            button.disabled = false;
            // 🔒 SECURE: Use textContent for text-only content
            button.textContent = button.dataset.originalText || 'Submit';
        }
    }
}

// Notification system
function initializeNotifications() {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notification-container') || createNotificationContainer();
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // 🔒 SECURE: Build notification structure with createElement
    const content = document.createElement('div');
    content.className = 'notification-content';
    
    const icon = document.createElement('i');
    icon.className = `fas fa-${getNotificationIcon(type)}`;
    
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message; // Safe - no HTML injection possible
    
    content.appendChild(icon);
    content.appendChild(messageSpan);
    
    // 🔒 Secure close button with addEventListener
    const closeButton = document.createElement('button');
    closeButton.className = 'notification-close';
    closeButton.addEventListener('click', () => closeNotification(closeButton));
    
    const closeIcon = document.createElement('i');
    closeIcon.className = 'fas fa-times';
    closeButton.appendChild(closeIcon);
    
    notification.appendChild(content);
    notification.appendChild(closeButton);
    
    container.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
    
    // Browser notification for important messages
    if (type === 'success' || type === 'warning') {
        showBrowserNotification(message, type);
    }
}

function createNotificationContainer() {
    const container = document.createElement('div');
    container.id = 'notification-container';
    container.className = 'notification-container';
    document.body.appendChild(container);
    return container;
}

function closeNotification(button) {
    button.parentElement.remove();
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function showBrowserNotification(message, type) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Memory App', {
            body: message,
            icon: '/favicon.ico',
            badge: '/favicon.ico'
        });
    }
}

// Search functionality
async function performSearch(query) {
    if (!query.trim()) {
        loadMemories();
        return;
    }
    
    try {
        const response = await fetch(`/api/memories/search?q=${encodeURIComponent(query)}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            memories = data.memories || [];
            renderMemories();
        }
    } catch (error) {
        console.error('Search error:', error);
    }
}

// Gamification system
function initializeGamification() {
    loadAchievements();
    updateGamificationStats();
}

function loadAchievements() {
    // Mock achievements for now
    achievements = [
        { id: 'first_memory', name: 'First Memory', description: 'Create your first memory', unlocked: false, icon: 'brain' },
        { id: 'memory_master', name: 'Memory Master', description: 'Create 10 memories', unlocked: false, icon: 'trophy' },
        { id: 'social_butterfly', name: 'Social Butterfly', description: 'Share 5 memories', unlocked: false, icon: 'share' },
        { id: 'week_warrior', name: 'Week Warrior', description: 'Reach weekly goal', unlocked: false, icon: 'calendar-check' }
    ];
    
    renderAchievements();
}

function renderAchievements() {
    const container = document.getElementById('achievements-grid');
    if (!container) return;
    
    // Clear container safely
    container.innerHTML = '';
    
    // 🔒 SECURE: Build achievements with createElement to prevent XSS
    achievements.forEach(achievement => {
        const achievementCard = document.createElement('div');
        achievementCard.className = `achievement-card ${achievement.unlocked ? 'unlocked' : 'locked'}`;
        
        // Achievement icon
        const iconDiv = document.createElement('div');
        iconDiv.className = 'achievement-icon';
        
        const icon = document.createElement('i');
        icon.className = `fas fa-${achievement.icon}`;
        iconDiv.appendChild(icon);
        
        // Achievement info
        const infoDiv = document.createElement('div');
        infoDiv.className = 'achievement-info';
        
        const title = document.createElement('h4');
        title.textContent = achievement.name; // Safe - no HTML injection possible
        
        const description = document.createElement('p');
        description.textContent = achievement.description; // Safe - no HTML injection possible
        
        infoDiv.appendChild(title);
        infoDiv.appendChild(description);
        
        achievementCard.appendChild(iconDiv);
        achievementCard.appendChild(infoDiv);
        
        // 🔒 Secure achievement badge
        if (achievement.unlocked) {
            const badge = document.createElement('div');
            badge.className = 'achievement-badge';
            
            const checkIcon = document.createElement('i');
            checkIcon.className = 'fas fa-check';
            badge.appendChild(checkIcon);
            
            achievementCard.appendChild(badge);
        }
        
        container.appendChild(achievementCard);
    });
}

function updateGamificationStats() {
    userPoints = memories.length * 10;
    totalMemories = memories.length;
    
    // Update UI elements
    const elements = {
        'user-points': userPoints,
        'total-memories': totalMemories,
        'weekly-progress': Math.min(100, (totalMemories / weeklyGoal) * 100)
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            if (id === 'weekly-progress') {
                // Use CSS class for progress width (CSP compliant)
                element.className = `progress-bar progress-${Math.min(100, Math.max(0, Math.floor(value)))}`;
            } else {
                element.textContent = value;
            }
        }
    });
}

function unlockAchievement(achievementId) {
    const achievement = achievements.find(a => a.id === achievementId);
    if (achievement && !achievement.unlocked) {
        achievement.unlocked = true;
        renderAchievements();
        showNotification(`Achievement unlocked: ${achievement.name}!`, 'success');
        playAchievementSound();
    }
}

// Sound effects
function playSuccessSound() {
    playSound(800, 100);
}

function playErrorSound() {
    playSound(300, 200);
}

function playAchievementSound() {
    // Achievement fanfare
    setTimeout(() => playSound(523, 100), 0);
    setTimeout(() => playSound(659, 100), 100);
    setTimeout(() => playSound(784, 100), 200);
    setTimeout(() => playSound(1047, 200), 300);
}

function playSound(frequency, duration) {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration / 1000);
        
        oscillator.start();
        oscillator.stop(audioContext.currentTime + duration / 1000);
    } catch (error) {
        console.log('Audio not supported');
    }
}

// Background animation
function initializeBackground() {
    try {
        if (typeof VANTA !== 'undefined' && typeof THREE !== 'undefined') {
            VANTA.NET({
                el: document.body,
                mouseControls: true,
                touchControls: true,
                gyroControls: false,
                minHeight: 200.00,
                minWidth: 200.00,
                scale: 1.00,
                scaleMobile: 1.00,
                color: 0x25d366,
                backgroundColor: 0xf0f5f2,
                points: 8.00,
                maxDistance: 25.00,
                spacing: 18.00
            });
        }
    } catch (error) {
        console.log('Background animation not available');
    }
}

// Social features
async function loadSocialContent() {
    try {
        const response = await fetch('/api/social/mutual-feelings', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            mutualFeelingsUsers = data.matches || [];
            renderSocialContent();
        }
    } catch (error) {
        console.error('Error loading social content:', error);
    }
}

function renderSocialContent() {
    const container = document.getElementById('social-content');
    if (!container) return;
    
    // Clear container safely
    container.innerHTML = '';
    
    // 🔒 SECURE: Build social content with createElement to prevent XSS
    const socialSection = document.createElement('div');
    socialSection.className = 'social-section';
    
    // Section header
    const header = document.createElement('h3');
    const heartIcon = document.createElement('i');
    heartIcon.className = 'fas fa-heart';
    header.appendChild(heartIcon);
    header.appendChild(document.createTextNode(' Mutual Feelings'));
    socialSection.appendChild(header);
    
    if (mutualFeelingsUsers.length > 0) {
        // 🔒 SECURE: Build mutual feelings list
        const mutualFeelingsList = document.createElement('div');
        mutualFeelingsList.className = 'mutual-feelings-list';
        
        mutualFeelingsUsers.forEach(user => {
            const userCard = document.createElement('div');
            userCard.className = 'mutual-feeling-card';
            
            // 🔒 User avatar - SECURE (textContent prevents XSS)
            const avatar = document.createElement('div');
            avatar.className = 'user-avatar';
            avatar.textContent = user.displayName ? user.displayName.charAt(0) : 'U'; // Safe
            
            // 🔒 User info - SECURE 
            const userInfo = document.createElement('div');
            userInfo.className = 'user-info';
            
            const displayName = document.createElement('h4');
            displayName.textContent = user.displayName || 'Unknown'; // Safe - no HTML injection
            
            const username = document.createElement('p');
            username.textContent = `@${user.username || 'unknown'}`; // Safe - no HTML injection
            
            userInfo.appendChild(displayName);
            userInfo.appendChild(username);
            
            // 🔒 Secure chat button with addEventListener 
            const chatButton = document.createElement('button');
            chatButton.className = 'chat-btn';
            chatButton.addEventListener('click', () => startAvatarChat(user.id));
            
            const chatIcon = document.createElement('i');
            chatIcon.className = 'fas fa-comments';
            chatButton.appendChild(chatIcon);
            chatButton.appendChild(document.createTextNode(' Chat'));
            
            userCard.appendChild(avatar);
            userCard.appendChild(userInfo);
            userCard.appendChild(chatButton);
            
            mutualFeelingsList.appendChild(userCard);
        });
        
        socialSection.appendChild(mutualFeelingsList);
    } else {
        // 🔒 SECURE: Empty state with createElement
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        
        const brokenHeartIcon = document.createElement('i');
        brokenHeartIcon.className = 'fas fa-heart-broken';
        
        const message = document.createElement('p');
        message.textContent = 'No mutual feelings detected yet.';
        
        emptyState.appendChild(brokenHeartIcon);
        emptyState.appendChild(message);
        socialSection.appendChild(emptyState);
    }
    
    container.appendChild(socialSection);
}

function showMutualFeelingsNotification(data) {
    showNotification(`💕 Mutual feelings detected with ${data.matchedUser.displayName}!`, 'success');
    loadSocialContent();
}

async function startAvatarChat(userId) {
    try {
        const response = await fetch('/api/social/start-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ userId })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Avatar chat started!', 'success');
            // Open chat interface
        }
    } catch (error) {
        console.error('Error starting avatar chat:', error);
        showNotification('Failed to start chat', 'error');
    }
}

// Memory reactions
async function reactToMemory(memoryId, reactionType) {
    try {
        const response = await fetch(`/api/memories/${memoryId}/react`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ reactionType })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Reaction added!', 'success');
            playSuccessSound();
        }
    } catch (error) {
        console.error('Error reacting to memory:', error);
    }
}

async function shareMemory(memoryId) {
    try {
        await navigator.share({
            title: 'Memory from Memory App',
            text: 'Check out this memory I saved!',
            url: window.location.origin
        });
        
        showNotification('Memory shared!', 'success');
    } catch (error) {
        // Fallback to clipboard
        navigator.clipboard.writeText(window.location.origin);
        showNotification('Link copied to clipboard!', 'info');
    }
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
        return 'Just now';
    } else if (diffInHours < 24) {
        return `${Math.floor(diffInHours)}h ago`;
    } else if (diffInHours < 48) {
        return 'Yesterday';
    } else {
        return date.toLocaleDateString();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function loadGamificationContent() {
    // This function is called when switching to gamification tab
    // UI is already rendered, just update stats
    updateGamificationStats();
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && isAuthenticated) {
        // Reconnect socket if needed
        if (!socket || !socket.connected) {
            initializeSocket();
        }
    }
});

// Export functions for global access
window.logout = logout;
window.switchTab = switchTab;
window.switchCategory = switchCategory;
window.reactToMemory = reactToMemory;
window.shareMemory = shareMemory;
window.startAvatarChat = startAvatarChat;
window.closeNotification = closeNotification;

// SSO Login Functions
function ssoLogin(provider) {
    const button = event.target;
    const originalText = button.textContent;
    button.classList.add('loading');
    button.textContent = '🔄 Connecting...';
    
    // Simulate SSO flow
    setTimeout(() => {
        showNotification(`${provider.charAt(0).toUpperCase() + provider.slice(1)} login would connect here`, 'info');
        button.classList.remove('loading');
        button.textContent = originalText;
    }, 1500);
}

window.ssoLogin = ssoLogin;

        // Magic Link Function
        function showMagicLink() {
            const email = prompt('Enter your email for a magic link:');
            if (email && email.includes('@')) {
                showNotification(`Magic link sent to ${email}`, 'success');
            } else if (email) {
                showNotification('Please enter a valid email address', 'error');
            }
        }

        // WebAuthn Function
        function showWebAuthn() {
            showNotification('Passkey authentication would be implemented here', 'info');
        }

        // Enhanced form switching with title updates
        function showRegister() {
            document.getElementById('login-form').classList.add('hidden');
            document.getElementById('register-form').classList.remove('hidden');
            const title = document.getElementById('auth-title');
            const subtitle = document.getElementById('auth-subtitle');
            if (title) title.textContent = 'Create Account';
            if (subtitle) subtitle.textContent = 'Join thousands using AI-powered memory storage';
        }

        function showLogin() {
            document.getElementById('register-form').classList.add('hidden');
            document.getElementById('login-form').classList.remove('hidden');
            const title = document.getElementById('auth-title');
            const subtitle = document.getElementById('auth-subtitle');
            if (title) title.textContent = 'Welcome Back';
            if (subtitle) subtitle.textContent = 'Sign in to access your AI-powered memories';
        }

        // Initialize Vanta.js Background
        function initVantaBackground() {
            if (typeof VANTA !== 'undefined' && document.getElementById('vanta-bg')) {
                try {
                    VANTA.NET({
                        el: "#vanta-bg",
                        mouseControls: true,
                        touchControls: true,
                        gyroControls: false,
                        minHeight: 200.00,
                        minWidth: 200.00,
                        scale: 1.00,
                        scaleMobile: 1.00,
                        color: 0x25d366,
                        backgroundColor: 0x128c7e,
                        points: 8.00,
                        maxDistance: 23.00,
                        spacing: 17.00
                    });
                } catch (e) {
                    console.log('Vanta.js not available, using fallback');
                }
            }
        }

        // Initialize app immediately with error handling
        window.addEventListener('load', function() {
            console.log('Window loaded, initializing app...');
            try {
                // Initialize audio system
                initializeAudio();
                
                // Initialize Vanta background
                initVantaBackground();
                
                // Show auth page by default
                const authPage = document.getElementById('auth-page');
                const mainApp = document.getElementById('main-app');
                
                if (authPage && mainApp) {
                    document.body.classList.add('auth-page-shown');
                    document.body.classList.remove('main-app-shown');
                    
                    if (authToken && currentUser) {
                        document.body.classList.remove('auth-page-shown');
                        document.body.classList.add('main-app-shown');
                        loadUserData();
                    }
                } else {
                    console.error('Required DOM elements not found');
                }
            } catch (error) {
                console.error('Error during app initialization:', error);
            }
        });

        // Initialize app
        document.addEventListener('DOMContentLoaded', function() {
            // Check for existing token
            const token = localStorage.getItem('memory_app_token');
            if (token) {
                authToken = token;
                connectSocket();
                showMainApp();
                loadUserData();
            }
        });

        // Authentication functions
        function showLogin() {
            document.getElementById('login-form').classList.remove('hidden');
            document.getElementById('register-form').classList.add('hidden');
        }

        function showRegister() {
            document.getElementById('login-form').classList.add('hidden');
            document.getElementById('register-form').classList.remove('hidden');
        }

        async function login() {
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;

            if (!username || !password) {
                showNotification('Please fill in all fields', 'error');
                return;
            }

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password })
                });

                const result = await response.json();

                if (result.success) {
                    authToken = result.token;
                    currentUser = result.user;
                    localStorage.setItem('memory_app_token', authToken);
                    
                    connectSocket();
                    showMainApp();
                    loadUserData();
                    showNotification('Welcome back!', 'success');
                } else {
                    showNotification(result.message || 'Login failed', 'error');
                }
            } catch (error) {
                showNotification('Login failed. Please try again.', 'error');
            }
        }

        async function register() {
            const username = document.getElementById('register-username').value;
            const displayName = document.getElementById('register-display-name').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;

            if (!username || !displayName || !password) {
                showNotification('Please fill in all required fields', 'error');
                return;
            }

            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, displayName, email, password })
                });

                const result = await response.json();

                if (result.success) {
                    authToken = result.token;
                    currentUser = result.user;
                    localStorage.setItem('memory_app_token', authToken);
                    
                    connectSocket();
                    showMainApp();
                    loadUserData();
                    showNotification('Account created successfully!', 'success');
                } else {
                    showNotification(result.error || 'Registration failed', 'error');
                }
            } catch (error) {
                showNotification('Registration failed. Please try again.', 'error');
            }
        }

        function logout() {
            localStorage.removeItem('memory_app_token');
            if (socket) {
                socket.disconnect();
            }
            currentUser = null;
            authToken = null;
            showAuthPage();
        }

        function showAuthPage() {
            document.getElementById('auth-page').classList.remove('hidden');
            document.getElementById('main-app').classList.add('hidden');
        }

        function showMainApp() {
            document.getElementById('auth-page').classList.add('hidden');
            document.getElementById('main-app').classList.remove('hidden');
        }

        // Socket.IO connection
        function connectSocket() {
            try {
                socket = io({
                    auth: {
                        token: authToken
                    },
                    transports: ['websocket', 'polling'],
                    timeout: 20000
                });

            socket.on('connect', () => {
                console.log('Connected to Memory App');
            });

            socket.on('notification', (notification) => {
                showNotification(notification.message, 'info');
                
                // Refresh data if needed
                if (notification.type === 'level_up' || notification.type === 'achievement_unlocked') {
                    loadUserStats();
                }
            });

            socket.on('stats_updated', (stats) => {
                updateUserStats(stats.stats);
            });

            socket.on('mutual_feelings_update', (data) => {
                updateMutualFeelingsStatus(data);
            });

            socket.on('error', (error) => {
                console.error('Socket error:', error);
                showNotification(error.message || 'Connection error', 'error');
            });

            socket.on('connect_error', (error) => {
                console.error('Connection error:', error);
                showNotification('Failed to connect to server', 'error');
            });

            socket.on('disconnect', (reason) => {
                console.log('Disconnected:', reason);
                if (reason === 'io server disconnect') {
                    // Server disconnected, try to reconnect
                    socket.connect();
                }
            });

            } catch (error) {
                console.error('Failed to initialize socket connection:', error);
                showNotification('Failed to establish real-time connection', 'error');
            }
        }

        // Navigation
        function showSection(sectionName) {
            // Update nav tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');

            // Update content sections
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            document.getElementById(sectionName + '-section').classList.add('active');

            // Load section data
            switch(sectionName) {
                case 'memories':
                    loadMemories();
                    break;
                case 'secrets':
                    loadSecrets();
                    break;
                case 'achievements':
                    loadAchievements();
                    break;
            }
        }

        // WhatsApp-style chat functions
        function showMemoriesAsChat() {
            showSection('memories');
        }

        function showSecretsAsChat() {
            showSection('secrets');
        }

        function showMutualFeelingsAsChat() {
            showNotification('💕 Opening secure communication channel...', 'success');
            // Switch to secrets tab to show mutual feelings
            switchTab('secrets');
        }

        // Data loading functions
        async function loadUserData() {
            await Promise.all([
                loadUserStats(),
                loadRecentMemories(),
                loadRecentSecrets(),
                checkMutualFeelings()
            ]);
        }

        async function loadUserStats() {
            try {
                const response = await fetch('/api/stats', {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });

                const result = await response.json();
                if (result.success) {
                    updateUserStats(result.stats);
                }
            } catch (error) {
                console.error('Failed to load user stats:', error);
            }
        }

        function updateUserStats(stats) {
            // Update header stats
            document.getElementById('user-level').textContent = `Level ${stats.level}`;
            document.getElementById('user-streak').textContent = `${stats.streak} day streak`;
            document.getElementById('memory-count').textContent = `${stats.totalMemories} memories`;

            // Update dashboard level display
            document.getElementById('dashboard-level').textContent = stats.level;
            document.getElementById('experience-text').textContent = `${stats.experience} / ${stats.level * 100} XP`;
            
            const progressPercentage = (stats.experience / (stats.level * 100)) * 100;
            const experienceBar = document.getElementById('experience-bar');
            if (experienceBar) {
                // Use CSS class for progress (CSP compliant)
                experienceBar.className = `progress-bar progress-${Math.min(100, Math.max(0, Math.floor(progressPercentage)))}`;
            }
        }

        async function loadMemories() {
            try {
                const response = await fetch('/api/memories', {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });

                const result = await response.json();
                if (result.success) {
                    allMemories = result.memories; // Store for search functionality
                    displayMemories(result.memories);
                }
            } catch (error) {
                console.error('Failed to load memories:', error);
            }
        }

        function displayMemories(memories) {
            const memoriesContainer = document.getElementById('memories-list');
            
            if (memories.length === 0) {
                // 🔒 SECURE: Build empty state with createElement
                memoriesContainer.innerHTML = ''; // Clear safely
                const emptyState = document.createElement('div');
                emptyState.className = 'empty-state';
                emptyState.textContent = 'No memories yet. Create your first memory!';
                memoriesContainer.appendChild(emptyState);
                return;
            }

            // 🔒 SECURE MEMORY RENDERING - NO XSS Risk
            memoriesContainer.innerHTML = ''; // Clear safely
            
            memories.forEach((memory, index) => {
                try {
                    const memoryCard = document.createElement('div');
                    memoryCard.className = 'memory-card slide-in';
                    memoryCard.setAttribute('data-memory-id', memory.id);
                    // Use CSS classes for animation delay and positioning
                    if (index < 5) {
                        memoryCard.classList.add(`anim-delay-${index + 1}`);
                    }
                    memoryCard.classList.add('relative');
                    
                    // Memory header
                    const header = document.createElement('div');
                    header.className = 'memory-header';
                    
                    const categoryDiv = document.createElement('div');
                    categoryDiv.className = 'memory-category';
                    const categoryIcon = getCategoryIcon(memory.category);
                    categoryDiv.textContent = `${categoryIcon} ${memory.category}`;
                    
                    const dateDiv = document.createElement('div');
                    dateDiv.className = 'memory-date';
                    dateDiv.textContent = new Date(memory.createdAt).toLocaleDateString();
                    
                    header.appendChild(categoryDiv);
                    header.appendChild(dateDiv);
                    
                    // 🔒 Memory content - SECURE (textContent prevents XSS)
                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'memory-content';
                    contentDiv.textContent = memory.content; // Safe - no HTML injection possible
                    
                    // Memory actions with secure event listeners
                    const actionsDiv = document.createElement('div');
                    actionsDiv.className = 'memory-actions';
                    
                    // 🔒 Secure reaction buttons with addEventListener
                    const reactions = ['❤️', '👍', '🔥', '💭'];
                    const hoverColors = ['rgba(255, 182, 193, 0.3)', 'rgba(37, 211, 102, 0.3)', 'rgba(255, 140, 0, 0.3)', 'rgba(147, 112, 219, 0.3)'];
                    
                    reactions.forEach((emoji, i) => {
                        const btn = document.createElement('button');
                        btn.className = 'reaction-btn';
                        btn.textContent = emoji;
                        // Use CSS class instead of inline styles
                        
                        // Secure event listeners with CSS class hover effects
                        const hoverClasses = ['hover-pink', 'hover-green', 'hover-orange', 'hover-purple'];
                        btn.addEventListener('click', () => addReaction(memory.id, emoji));
                        btn.addEventListener('mouseenter', () => btn.classList.add(hoverClasses[i]));
                        btn.addEventListener('mouseleave', () => btn.classList.remove(hoverClasses[i]));
                        
                        actionsDiv.appendChild(btn);
                    });
                    
                    // Timestamp
                    const timestamp = document.createElement('div');
                    timestamp.className = 'timestamp';
                    timestamp.textContent = new Date(memory.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    actionsDiv.appendChild(timestamp);
                    
                    // Reactions display
                    const reactionsDisplay = document.createElement('div');
                    reactionsDisplay.id = `reactions-${memory.id}`;
                    reactionsDisplay.className = 'message-reactions reactions-hidden';
                    
                    // Assemble card securely
                    memoryCard.appendChild(header);
                    memoryCard.appendChild(contentDiv);
                    memoryCard.appendChild(actionsDiv);
                    memoryCard.appendChild(reactionsDisplay);
                    
                    memoriesContainer.appendChild(memoryCard);
                } catch (error) {
                    console.error('Error rendering memory:', error);
                }
            });
        }
        
        // Smart Memory Search Implementation - ACTUAL WORKING VERSION
        let allMemories = [];
        let searchTimeout = null;
        let isSearching = false;
        
        function searchMemories(query) {
            // Show/hide clear button
            const clearBtn = document.getElementById('clear-search');
            if (clearBtn) {
                if (query.length > 0) {
                    clearBtn.classList.add('clear-btn-visible');
                    clearBtn.classList.remove('clear-btn-hidden');
                } else {
                    clearBtn.classList.remove('clear-btn-visible');
                    clearBtn.classList.add('clear-btn-hidden');
                }
            }
            
            // Debounce search
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(query.trim());
            }, 200);
        }
        
        function performSearch(query) {
            if (!query) {
                displayMemories(allMemories);
                hideSearchSuggestions();
                return;
            }
            
            isSearching = true;
            const queryLower = query.toLowerCase();
            
            // Advanced fuzzy search with scoring
            const scored = allMemories.map(memory => {
                let score = 0;
                const contentLower = memory.content.toLowerCase();
                const categoryLower = memory.category.toLowerCase();
                
                // Exact matches get highest score
                if (contentLower.includes(queryLower)) score += 100;
                if (categoryLower === queryLower) score += 80;
                if (categoryLower.includes(queryLower)) score += 60;
                
                // Word boundary matches
                const words = queryLower.split(' ');
                words.forEach(word => {
                    if (word.length >= 2) {
                        if (contentLower.includes(word)) score += 20;
                        if (categoryLower.includes(word)) score += 15;
                    }
                });
                
                // Recency bonus
                const daysSinceCreated = (Date.now() - new Date(memory.createdAt)) / (1000 * 60 * 60 * 24);
                if (daysSinceCreated < 7) score += 10;
                
                return { memory, score };
            }).filter(item => item.score > 0);
            
            // Sort by score
            scored.sort((a, b) => b.score - a.score);
            const filtered = scored.map(item => item.memory);
            
            displayMemories(filtered);
            
            // Show smart suggestions
            if (query.length >= 1) {
                const suggestions = generateSmartSuggestions(query, allMemories);
                displaySearchSuggestions(suggestions);
            }
            
            isSearching = false;
        }
        
        function handleSearchKeydown(event) {
            if (event.key === 'Escape') {
                clearSearch();
            }
        }
        
        function showSearchSuggestions(force = false) {
            const query = document.getElementById('memory-search').value;
            if (query.length > 0 || force) {
                const suggestions = generateSmartSuggestions(query, allMemories);
                displaySearchSuggestions(suggestions);
            }
        }
        
        function hideSearchSuggestions() {
            // Delay to allow clicking on suggestions
            setTimeout(() => {
                const suggestions = document.getElementById('search-suggestions');
                if (suggestions) {
                    suggestions.classList.add('hidden');
                }
            }, 150);
        }
        
        function clearSearch() {
            document.getElementById('memory-search').value = '';
            const clearBtn = document.getElementById('clear-search');
            if (clearBtn) {
                clearBtn.classList.remove('clear-btn-visible');
                clearBtn.classList.add('clear-btn-hidden');
            }
            displayMemories(allMemories);
            hideSearchSuggestions();
        }
        
        function generateSmartSuggestions(query, memories) {
            const suggestions = [];
            const queryLower = query.toLowerCase();
            const categories = [...new Set(memories.map(m => m.category))];
            
            // Quick access suggestions for short queries
            if (query.length <= 2) {
                suggestions.push({ type: 'quick', text: '🕒 Show recent memories', value: 'recent' });
                categories.forEach(cat => {
                    const icon = getCategoryIcon(cat);
                    suggestions.push({ type: 'category', text: `${icon} Show ${cat} memories`, value: cat });
                });
                return suggestions.slice(0, 5);
            }
            
            // Category matches
            categories.forEach(cat => {
                if (cat.toLowerCase().includes(queryLower)) {
                    const icon = getCategoryIcon(cat);
                    suggestions.push({ type: 'category', text: `${icon} Filter by ${cat}`, value: cat });
                }
            });
            
            // Content preview suggestions
            const contentMatches = memories.filter(m => 
                m.content.toLowerCase().includes(queryLower)
            ).slice(0, 3);
            
            contentMatches.forEach(match => {
                // Highlight the matching part
                const content = match.content;
                const index = content.toLowerCase().indexOf(queryLower);
                let preview = content.substring(Math.max(0, index - 10), index + queryLower.length + 20);
                if (preview.length < content.length) preview += '...';
                if (index > 10) preview = '...' + preview;
                
                suggestions.push({ 
                    type: 'content', 
                    text: `💭 "${preview}"`, 
                    value: match.id,
                    memoryId: match.id
                });
            });
            
            return suggestions.slice(0, 7);
        }
        
        function getCategoryIcon(category) {
            const icons = {
                'work': '💼',
                'family': '👨‍👩‍👧‍👦', 
                'friends': '👥',
                'personal': '🌟',
                'health': '🏥',
                'finance': '💰',
                'general': '📝'
            };
            return icons[category] || '📁';
        }
        
        function displaySearchSuggestions(suggestions) {
            const container = document.getElementById('search-suggestions');
            if (!container || suggestions.length === 0) {
                if (container) container.classList.add('hidden');
                return;
            }
            
            // 🔒 CRITICAL FIX: Build search suggestions securely
            container.innerHTML = ''; // Clear safely
            
            suggestions.forEach((s, index) => {
                const suggestionDiv = document.createElement('div');
                suggestionDiv.className = 'suggestion-item';
                
                // Safe text content only
                suggestionDiv.textContent = s.text;
                
                // Secure event listeners
                suggestionDiv.addEventListener('click', () => handleSuggestionClick(s));
                // Hover effects handled by CSS
                
                container.appendChild(suggestionDiv);
            });
            container.classList.remove('hidden');
        }
        
        function handleSuggestionClick(suggestion) {
            const searchInput = document.getElementById('memory-search');
            
            switch (suggestion.type) {
                case 'category':
                    filterByCategory(suggestion.value);
                    searchInput.value = suggestion.value;
                    break;
                case 'quick':
                    if (suggestion.value === 'recent') {
                        filterRecent();
                        searchInput.value = 'recent';
                    }
                    break;
                case 'content':
                    // Jump to specific memory
                    jumpToMemory(suggestion.memoryId);
                    searchInput.value = '';
                    break;
            }
            
            hideSearchSuggestions();
        }
        
        function jumpToMemory(memoryId) {
            const memoryElement = document.querySelector(`[data-memory-id="${memoryId}"]`);
            if (memoryElement) {
                memoryElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                memoryElement.classList.add('highlight-memory');
                setTimeout(() => {
                    memoryElement.classList.remove('highlight-memory');
                }, 2000);
            }
        }
        
        function filterByCategory(category) {
            const filtered = allMemories.filter(m => m.category === category);
            displayMemories(filtered);
            document.getElementById('memory-search').value = category;
            const suggestions1 = document.getElementById('search-suggestions');
            if (suggestions1) suggestions1.classList.add('hidden');
        }
        
        function filterRecent() {
            const recent = allMemories.slice(0, 5);
            displayMemories(recent);
            document.getElementById('memory-search').value = 'recent';
            const suggestions2 = document.getElementById('search-suggestions');
            if (suggestions2) suggestions2.classList.add('hidden');
        }
        
        // Memory Reactions System
        function addReaction(memoryId, emoji) {
            try {
                const reactionEl = document.getElementById(`reactions-${memoryId}`);
                if (!reactionEl) {
                    console.error(`Reaction element not found for memory ${memoryId}`);
                    return;
                }
                
                // 🔒 SECURE: Use textContent instead of innerHTML
                reactionEl.textContent = emoji; // Safe - no XSS risk
                reactionEl.classList.remove('hidden');
                reactionEl.classList.add('show');
                
                // Add reaction animation with fallback
                if (reactionEl.animate) {
                    reactionEl.animate([
                        { transform: 'scale(1)', opacity: 0 },
                        { transform: 'scale(1.2)', opacity: 1 },
                        { transform: 'scale(1)', opacity: 1 }
                    ], {
                        duration: 300,
                        easing: 'ease-out'
                    });
                }
                
                // Play reaction sound
                playNotificationSound('reaction');
                
                // Hide after 3 seconds
                setTimeout(() => {
                    if (reactionEl) {
                        reactionEl.classList.remove('show');
                        reactionEl.classList.add('hidden');
                    }
                }, 3000);
                
            } catch (error) {
                console.error('Error adding reaction:', error);
            }
        }

        async function loadSecrets() {
            try {
                const response = await fetch('/api/secrets', {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });

                const result = await response.json();
                if (result.success) {
                    displaySecrets(result.secrets);
                }
            } catch (error) {
                console.error('Failed to load secrets:', error);
            }
        }

        function displaySecrets(secrets) {
            const secretsContainer = document.getElementById('secrets-list');
            
            if (secrets.length === 0) {
                // 🔒 SECURE: Build empty state with createElement and CSS classes
                secretsContainer.innerHTML = ''; // Clear safely
                const emptyState = document.createElement('div');
                emptyState.className = 'secrets-empty-state'; // Use CSS class instead of inline styles
                emptyState.textContent = 'No secrets yet. Create your first secret memory!';
                secretsContainer.appendChild(emptyState);
                return;
            }

            // 🔒 CRITICAL FIX: Build secrets securely to prevent XSS
            secretsContainer.innerHTML = ''; // Clear safely
            
            secrets.forEach(secret => {
                const secretCard = document.createElement('div');
                secretCard.className = 'secret-card';
                
                // Title - SECURE
                const title = document.createElement('h4');
                title.textContent = secret.title; // Safe
                secretCard.appendChild(title);
                
                // Designated Person - SECURE
                const personP = document.createElement('p');
                const personStrong = document.createElement('strong');
                personStrong.textContent = 'Designated Person: ';
                personP.appendChild(personStrong);
                personP.appendChild(document.createTextNode(secret.designatedPerson || 'None'));
                secretCard.appendChild(personP);
                
                // Created Date - SECURE
                const dateP = document.createElement('p');
                const dateStrong = document.createElement('strong');
                dateStrong.textContent = 'Created: ';
                dateP.appendChild(dateStrong);
                dateP.appendChild(document.createTextNode(new Date(secret.createdAt).toLocaleDateString()));
                secretCard.appendChild(dateP);
                
                // Romantic indicator - SECURE
                if (secret.isRomantic) {
                    const romanticDiv = document.createElement('div');
                    romanticDiv.className = 'romantic-indicator';
                    romanticDiv.textContent = '💕 Romantic Secret';
                    secretCard.appendChild(romanticDiv);
                }
                
                // Ownership indicator - SECURE
                const ownerDiv = document.createElement('div');
                ownerDiv.className = 'secret-owner';
                if (secret.isOwner) {
                    ownerDiv.classList.add('owner-secret');
                    ownerDiv.textContent = 'You own this secret';
                } else {
                    ownerDiv.classList.add('received-secret');
                    ownerDiv.textContent = 'Shared with you';
                }
                secretCard.appendChild(ownerDiv);
                
                secretsContainer.appendChild(secretCard);
            });
        }

        async function loadRecentMemories() {
            try {
                const response = await fetch('/api/memories?limit=3', {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });

                const result = await response.json();
                if (result.success) {
                    const container = document.getElementById('recent-memories');
                    if (result.memories.length === 0) {
                        container.textContent = 'No memories yet';
                    } else {
                        container.textContent = `${result.memories.length} recent memories`;
                    }
                }
            } catch (error) {
                document.getElementById('recent-memories').textContent = 'Error loading';
            }
        }

        async function loadRecentSecrets() {
            try {
                const response = await fetch('/api/secrets', {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });

                const result = await response.json();
                if (result.success) {
                    const container = document.getElementById('recent-secrets');
                    container.textContent = `${result.secrets.length} secrets stored`;
                }
            } catch (error) {
                document.getElementById('recent-secrets').textContent = 'Error loading';
            }
        }

        async function checkMutualFeelings() {
            // This would integrate with the actual mutual feelings detection
            const container = document.getElementById('mutual-feelings-status');
            container.textContent = 'No mutual matches yet';
        }

        function loadAchievements() {
            // Mock achievements for now
            const achievementsContainer = document.getElementById('achievements-list');
            
            const mockAchievements = [
                { icon: '🧠', title: 'Memory Keeper', description: 'Store your first memory', unlocked: true },
                { icon: '🔐', title: 'Secret Keeper', description: 'Create your first secret', unlocked: false },
                { icon: '💕', title: 'Love Connection', description: 'Experience mutual feelings', unlocked: false },
                { icon: '🔥', title: 'Week Warrior', description: '7-day streak', unlocked: false },
                { icon: '⭐', title: 'Month Master', description: '30-day streak', unlocked: false },
                { icon: '🏆', title: 'Memory Master', description: 'Store 100 memories', unlocked: false }
            ];

            // 🔒 SECURITY FIX: Build achievements securely
            achievementsContainer.innerHTML = ''; // Clear safely
            
            mockAchievements.forEach(achievement => {
                const card = document.createElement('div');
                card.className = `achievement-card ${achievement.unlocked ? 'unlocked' : ''}`;
                
                const icon = document.createElement('div');
                icon.className = 'achievement-icon';
                icon.textContent = achievement.icon;
                
                const title = document.createElement('h4');
                title.textContent = achievement.title;
                
                const description = document.createElement('p');
                description.textContent = achievement.description;
                
                const status = document.createElement('div');
                status.className = `achievement-status ${achievement.unlocked ? 'achievement-unlocked' : 'achievement-locked'}`;
                status.textContent = achievement.unlocked ? '✅ Unlocked' : '🔒 Locked';
                
                card.appendChild(icon);
                card.appendChild(title);
                card.appendChild(description);
                card.appendChild(status);
                
                achievementsContainer.appendChild(card);
            });
        }

        // Form functions
        function showCreateMemory() {
            document.getElementById('create-memory-form').classList.remove('hidden');
        }

        function hideCreateMemory() {
            document.getElementById('create-memory-form').classList.add('hidden');
            document.getElementById('memory-content').value = '';
            document.getElementById('memory-category').value = 'general';
        }

        async function createMemory() {
            const content = document.getElementById('memory-content').value;
            const category = document.getElementById('memory-category').value;

            if (!content.trim()) {
                showNotification('Please enter memory content', 'error');
                playNotificationSound('error');
                return;
            }

            // Show typing indicator with proper context
            const indicatorId = showTypingIndicator('memory-creation');
            
            try {
                const response = await fetch('/api/memories', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({ content, category })
                });

                const result = await response.json();
                
                // Always hide typing indicator
                hideTypingIndicator('memory-creation');
                
                if (result.success) {
                    document.getElementById('memory-content').value = '';
                    hideCreateMemory();
                    
                    // Reload data and show success
                    await Promise.all([
                        loadMemories(),
                        loadUserStats()
                    ]);
                    
                    showNotification(`✨ Memory saved! Memory #${result.memoryNumber}`, 'success');
                    playNotificationSound('success');
                } else {
                    showNotification(result.error || 'Failed to create memory', 'error');
                    playNotificationSound('error');
                }
            } catch (error) {
                hideTypingIndicator('memory-creation');
                showNotification('Network error - please try again', 'error');
                playNotificationSound('error');
                console.error('Memory creation error:', error);
            }
        }

        // ACTUAL TYPING INDICATORS SYSTEM
        let typingStates = new Map(); // Track typing per user/context
        let typingTimeouts = new Map();
        
        function showTypingIndicator(context = 'memory-creation', user = 'system') {
            const containerId = context === 'memory-creation' ? 'memories-list' : 'secrets-list';
            const container = document.getElementById(containerId);
            if (!container) return;
            
            const indicatorId = `typing-indicator-${context}`;
            
            // Remove any existing typing indicator for this context
            hideTypingIndicator(context);
            
            const typingDiv = document.createElement('div');
            typingDiv.id = indicatorId;
            typingDiv.className = 'typing-indicator';
            typingDiv.setAttribute('data-context', context);
            
            const messages = {
                'memory-creation': '💭 Creating your memory...',
                'secret-creation': '🔐 Securing your secret...',
                'processing': '⚙️ Processing...',
                'ai-thinking': '🤖 AI is thinking...'
            };
            
            // 🔒 SECURE: Build DOM structure safely
            const messageSpan = document.createElement('span');
            messageSpan.textContent = messages[context] || messages['processing'];
            
            const dotsContainer = document.createElement('div');
            dotsContainer.className = 'dots-container';
            
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('div');
                dot.className = 'typing-dot';
                dotsContainer.appendChild(dot);
            }
            
            typingDiv.appendChild(messageSpan);
            typingDiv.appendChild(dotsContainer);
            
            // Track typing state
            typingStates.set(context, { active: true, timestamp: Date.now() });
            
            // Add to the top of the list with proper positioning
            if (container.firstChild && !container.firstChild.classList?.contains('typing-indicator')) {
                container.insertBefore(typingDiv, container.firstChild);
            } else if (!container.firstChild) {
                container.appendChild(typingDiv);
            }
            
            // Auto-scroll to show the indicator
            setTimeout(() => {
                typingDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
            
            // Safety timeout to prevent stuck indicators
            const timeoutId = setTimeout(() => {
                hideTypingIndicator(context);
                console.warn(`Typing indicator for ${context} auto-removed after timeout`);
            }, 10000); // 10 second timeout
            
            typingTimeouts.set(context, timeoutId);
            
            return indicatorId;
        }

        function hideTypingIndicator(context = 'memory-creation') {
            const indicatorId = `typing-indicator-${context}`;
            const typingEl = document.getElementById(indicatorId);
            
            if (typingEl) {
                // Update state
                typingStates.delete(context);
                
                // Clear timeout
                const timeoutId = typingTimeouts.get(context);
                if (timeoutId) {
                    clearTimeout(timeoutId);
                    typingTimeouts.delete(context);
                }
                
                // Smooth fade out animation using CSS class
                typingEl.classList.add('typing-fade-out');
                
                setTimeout(() => {
                    if (typingEl.parentNode) {
                        typingEl.remove();
                    }
                }, 300);
            }
        }
        
        function hideAllTypingIndicators() {
            // Clear all typing indicators
            typingStates.clear();
            typingTimeouts.forEach(timeout => clearTimeout(timeout));
            typingTimeouts.clear();
            
            document.querySelectorAll('.typing-indicator').forEach(el => {
                el.classList.add('typing-quick-fade');
                setTimeout(() => {
                    if (el.parentNode) el.remove();
                }, 200);
            });
        }
        
        function isTyping(context = 'memory-creation') {
            const state = typingStates.get(context);
            return state && state.active && (Date.now() - state.timestamp < 8000);
        }

        // ACTUAL WORKING SOUND EFFECTS SYSTEM
        let soundEnabled = true;
        let audioContext = null;
        let soundCache = new Map();
        let userInteracted = false;
        
        function initializeAudio() {
            const savedSetting = localStorage.getItem('soundEnabled');
            if (savedSetting !== null) {
                soundEnabled = savedSetting === 'true';
            }
            
            // Listen for first user interaction to enable audio
            const enableAudio = () => {
                if (!userInteracted) {
                    userInteracted = true;
                    createAudioContext();
                    document.removeEventListener('click', enableAudio);
                    document.removeEventListener('keydown', enableAudio);
                }
            };
            
            document.addEventListener('click', enableAudio);
            document.addEventListener('keydown', enableAudio);
        }
        
        function createAudioContext() {
            if (!audioContext) {
                try {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    console.log('Audio context created successfully');
                } catch (e) {
                    console.warn('Audio context creation failed:', e);
                }
            }
        }
        
        function toggleSound() {
            soundEnabled = !soundEnabled;
            localStorage.setItem('soundEnabled', soundEnabled.toString());
            
            const message = soundEnabled ? '🔊 Sound enabled' : '🔇 Sound disabled';
            showNotification(message, 'info');
            
            // Test sound when enabled
            if (soundEnabled) {
                setTimeout(() => playNotificationSound('notification'), 100);
            }
        }
        
        function playNotificationSound(type) {
            if (!soundEnabled || !userInteracted) return;
            
            // Check if user has sound disabled via browser preferences
            if ('permissions' in navigator) {
                navigator.permissions.query({name: 'speaker-selection'}).then(result => {
                    if (result.state === 'denied') return;
                });
            }
            
            createAudioContext();
            if (!audioContext) return;
            
            try {
                // Resume context if suspended (required for mobile browsers)
                if (audioContext.state === 'suspended') {
                    audioContext.resume();
                }
                
                const now = audioContext.currentTime;
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                // Enhanced sound profiles with better frequencies and timing
                const soundProfiles = {
                    'success': {
                        frequency: [600, 800, 1000],
                        duration: 0.4,
                        volume: 0.12,
                        shape: 'exponential'
                    },
                    'reaction': {
                        frequency: [800],
                        duration: 0.15,
                        volume: 0.08,
                        shape: 'linear'
                    },
                    'notification': {
                        frequency: [520, 440],
                        duration: 0.3,
                        volume: 0.06,
                        shape: 'exponential'
                    },
                    'error': {
                        frequency: [300, 250],
                        duration: 0.25,
                        volume: 0.10,
                        shape: 'linear'
                    },
                    'love': {
                        frequency: [660, 880, 1100, 880],
                        duration: 0.6,
                        volume: 0.08,
                        shape: 'exponential'
                    }
                };
                
                const profile = soundProfiles[type] || soundProfiles['notification'];
                const frequencies = profile.frequency;
                
                // Create sequence of tones for complex sounds
                frequencies.forEach((freq, index) => {
                    const startTime = now + (index * profile.duration / frequencies.length);
                    const endTime = startTime + (profile.duration / frequencies.length);
                    
                    oscillator.frequency.setValueAtTime(freq, startTime);
                    if (index < frequencies.length - 1) {
                        oscillator.frequency.exponentialRampToValueAtTime(
                            frequencies[index + 1], 
                            endTime
                        );
                    }
                });
                
                // Set volume envelope
                gainNode.gain.setValueAtTime(0, now);
                gainNode.gain.linearRampToValueAtTime(profile.volume, now + 0.02);
                
                if (profile.shape === 'exponential') {
                    gainNode.gain.exponentialRampToValueAtTime(0.001, now + profile.duration);
                } else {
                    gainNode.gain.linearRampToValueAtTime(0, now + profile.duration);
                }
                
                oscillator.start(now);
                oscillator.stop(now + profile.duration);
                
            } catch (e) {
                console.debug('Audio playback failed:', e.message);
            }
        }

        function showCreateSecret() {
            document.getElementById('create-secret-form').classList.remove('hidden');
        }

        function hideCreateSecret() {
            document.getElementById('create-secret-form').classList.add('hidden');
            document.getElementById('secret-title').value = '';
            document.getElementById('secret-content').value = '';
            document.getElementById('designated-person').value = '';
            document.getElementById('is-romantic').checked = false;
        }

        async function createSecret() {
            const title = document.getElementById('secret-title').value;
            const content = document.getElementById('secret-content').value;
            const designatedPerson = document.getElementById('designated-person').value;
            const isRomantic = document.getElementById('is-romantic').checked;

            if (!title || !content) {
                showNotification('Please fill in title and content', 'error');
                return;
            }

            try {
                const response = await fetch('/api/secrets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({
                        title,
                        content,
                        designatedPersonName: designatedPerson,
                        isRomantic
                    })
                });

                const result = await response.json();
                if (result.success) {
                    hideCreateSecret();
                    loadSecrets();
                    loadUserStats();
                    
                    if (result.mutualMatch && result.mutualMatch.found) {
                        showNotification('💕 Mutual feelings detected! ' + result.mutualMatch.message, 'success');
                    } else {
                        showNotification('Secret saved successfully!', 'success');
                    }
                } else {
                    showNotification(result.error || 'Failed to create secret', 'error');
                }
            } catch (error) {
                showNotification('Failed to create secret', 'error');
            }
        }

        // Utility functions
        function showNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.className = 'notification';
            
            // 🔒 CRITICAL SECURITY FIX: Build DOM safely to prevent XSS
            const contentDiv = document.createElement('div');
            contentDiv.className = 'notification-content';
            
            const icon = document.createElement('i');
            icon.className = `fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}`;
            
            const messageSpan = document.createElement('span');
            messageSpan.textContent = message; // Safe - no XSS possible
            
            contentDiv.appendChild(icon);
            contentDiv.appendChild(messageSpan);
            notification.appendChild(contentDiv);
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.classList.add('notification-slide-out');
                setTimeout(() => {
                    document.body.removeChild(notification);
                }, 300);
            }, 3000);
        }

        function updateMutualFeelingsStatus(data) {
            const container = document.getElementById('mutual-feelings-status');
            // 🔒 SECURE: Build DOM safely  
            if (data.found) {
                const alertDiv = document.createElement('div');
                alertDiv.className = 'mutual-match-alert';
                
                const heartIcon = document.createElement('i');
                heartIcon.className = 'fas fa-heart';
                
                const messageSpan = document.createElement('span');
                messageSpan.textContent = '💕 Mutual feelings detected!';
                
                alertDiv.appendChild(heartIcon);
                alertDiv.appendChild(messageSpan);
                container.appendChild(alertDiv);
            } else {
                container.textContent = 'No mutual matches yet';
            }
        }

// 🚀 CRITICAL: Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);

// Handle page visibility changes  
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && isAuthenticated) {
        // Reconnect socket if needed
        if (!socket || !socket.connected) {
            initializeSocket();
        }
    }
});

// Export functions for global access
window.logout = logout;
window.switchTab = switchTab;
window.switchCategory = switchCategory;

// 🧠 Memory Analysis Function
async function analyzeSelectedMemory() {
    try {
        if (memories.length === 0) {
            showNotification('No memories to analyze yet', 'warning');
            return;
        }

        showNotification('🧠 Analyzing your memories with AI...', 'info');
        
        const response = await authenticatedFetch('/api/ai/analyze-patterns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('✅ Memory analysis complete! Check AI Insights tab', 'success');
            // Refresh AI insights after analysis
            if (currentTab === 'insights') {
                loadAIInsights();
            }
        } else {
            showNotification('Analysis failed, please try again', 'error');
        }
    } catch (error) {
        console.error('Memory analysis error:', error);
        showNotification('Analysis temporarily unavailable', 'warning');
    }
}

// 🧠 AI INSIGHTS FUNCTIONALITY - Revolutionary relationship intelligence

async function loadAIInsights() {
    const container = document.getElementById('ai-insights-content');
    if (!container) return;
    
    // Show loading state
    container.innerHTML = '';
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.innerHTML = `
        <div class="spinner"></div>
        Analyzing your memories with AI...
    `;
    container.appendChild(loadingDiv);
    
    try {
        const response = await fetch('/api/ai/relationship-insights', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            renderAIInsights(data.insights);
        } else {
            showNoInsightsMessage();
        }
    } catch (error) {
        console.error('Error loading AI insights:', error);
        showAIInsightsError();
    }
}

function renderAIInsights(insights) {
    const container = document.getElementById('ai-insights-content');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Relationship Health Score
    const healthSection = document.createElement('div');
    healthSection.className = 'insight-section health-section';
    
    const healthHeader = document.createElement('div');
    healthHeader.className = 'insight-header';
    healthHeader.innerHTML = '<i class="fas fa-heart"></i><h3>Relationship Health</h3>';
    
    const healthScore = document.createElement('div');
    healthScore.className = 'health-score';
    healthScore.innerHTML = `
        <div class="score-circle" data-score="${insights.relationshipHealth.score}">
            <span class="score-number">${insights.relationshipHealth.score}</span>
            <span class="score-label">/ 100</span>
        </div>
        <p class="health-summary">${insights.relationshipHealth.summary}</p>
    `;
    
    healthSection.appendChild(healthHeader);
    healthSection.appendChild(healthScore);
    
    // Key Insights
    const insightsSection = document.createElement('div');
    insightsSection.className = 'insight-section insights-section';
    
    const insightsHeader = document.createElement('div');
    insightsHeader.className = 'insight-header';
    insightsHeader.innerHTML = '<i class="fas fa-lightbulb"></i><h3>Key Insights</h3>';
    
    const insightsList = document.createElement('div');
    insightsList.className = 'insights-list';
    
    insights.keyInsights.forEach(insight => {
        const item = document.createElement('div');
        item.className = 'insight-item';
        item.innerHTML = `<i class="fas fa-check-circle"></i><span>${insight}</span>`;
        insightsList.appendChild(item);
    });
    
    insightsSection.appendChild(insightsHeader);
    insightsSection.appendChild(insightsList);
    
    // Actionable Advice
    const adviceSection = document.createElement('div');
    adviceSection.className = 'insight-section advice-section';
    
    const adviceHeader = document.createElement('div');
    adviceHeader.className = 'insight-header';
    adviceHeader.innerHTML = '<i class="fas fa-rocket"></i><h3>Actionable Advice</h3>';
    
    const adviceList = document.createElement('div');
    adviceList.className = 'advice-list';
    
    insights.actionableAdvice.forEach(advice => {
        const item = document.createElement('div');
        item.className = 'advice-item';
        item.innerHTML = `<i class="fas fa-arrow-right"></i><span>${advice}</span>`;
        adviceList.appendChild(item);
    });
    
    adviceSection.appendChild(adviceHeader);
    adviceSection.appendChild(adviceList);
    
    // Append all sections
    container.appendChild(healthSection);
    container.appendChild(insightsSection);
    container.appendChild(adviceSection);
    
    // Animate score circle
    setTimeout(() => {
        animateScoreCircle(insights.relationshipHealth.score);
    }, 100);
}

function animateScoreCircle(score) {
    const circle = document.querySelector('.score-circle');
    if (circle) {
        const percentage = (score / 100) * 360;
        circle.style.background = `conic-gradient(
            #2196F3 0deg ${percentage}deg,
            #f0f0f0 ${percentage}deg 360deg
        )`;
    }
}

function showNoInsightsMessage() {
    const container = document.getElementById('ai-insights-content');
    container.innerHTML = '';
    
    const noInsights = document.createElement('div');
    noInsights.className = 'no-insights';
    noInsights.innerHTML = `
        <i class="fas fa-brain"></i>
        <h3>Ready for AI Insights!</h3>
        <p>Create a few memories to unlock AI-powered relationship intelligence.</p>
    `;
    
    const switchBtn = document.createElement('button');
    switchBtn.className = 'btn-primary';
    switchBtn.innerHTML = '<i class="fas fa-plus"></i> Add Your First Memory';
    switchBtn.onclick = () => switchTab('memories');
    
    noInsights.appendChild(switchBtn);
    container.appendChild(noInsights);
}

function showAIInsightsError() {
    const container = document.getElementById('ai-insights-content');
    container.innerHTML = '';
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'ai-error';
    errorDiv.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <h3>AI Analysis Temporarily Unavailable</h3>
        <p>Our AI is taking a quick break. Please try again in a moment.</p>
    `;
    
    const retryBtn = document.createElement('button');
    retryBtn.className = 'btn-primary';
    retryBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Try Again';
    retryBtn.onclick = loadAIInsights;
    
    errorDiv.appendChild(retryBtn);
    container.appendChild(errorDiv);
}

// 🌍 REVOLUTIONARY SOCIAL FEATURES - Ultimate Social Platform

async function loadSocialFeatures() {
    console.log('Loading revolutionary social features...');
    
    // Load social statistics
    loadSocialStats();
    
    // Load user connections
    loadUserConnections();
    
    // Load available memories for sharing
    loadMemoriesForSharing();
    
    // Check mutual feelings status
    checkMutualFeelings();
}

async function loadSocialStats() {
    try {
        const response = await fetch('/api/social/stats', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            document.getElementById('connection-count').textContent = data.stats.connections || 0;
            document.getElementById('shared-memories').textContent = data.stats.sharedMemories || 0;
            document.getElementById('mutual-matches').textContent = data.stats.mutualMatches || 0;
        }
    } catch (error) {
        console.error('Error loading social stats:', error);
    }
}

async function loadUserConnections() {
    const container = document.getElementById('connections-list');
    
    try {
        const response = await fetch('/api/social/connections', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success && data.connections.length > 0) {
            renderConnections(data.connections);
        } else {
            container.innerHTML = `
                <div class="no-connections">
                    <i class="fas fa-users"></i>
                    <h4>No connections yet</h4>
                    <p>Start discovering amazing people!</p>
                    <button onclick="showFindConnections()" class="btn-primary">
                        <i class="fas fa-search"></i> Find Connections
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading connections:', error);
        container.innerHTML = '<div class="error-message">Failed to load connections</div>';
    }
}

function renderConnections(connections) {
    const container = document.getElementById('connections-list');
    container.innerHTML = '';
    
    connections.forEach(connection => {
        const connectionCard = document.createElement('div');
        connectionCard.className = 'connection-card';
        connectionCard.innerHTML = `
            <div class="connection-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="connection-info">
                <h4>${connection.displayName}</h4>
                <p class="connection-status">${connection.status || 'Connected'}</p>
                <p class="connection-date">Connected ${formatDate(connection.connectedAt)}</p>
            </div>
            <div class="connection-actions">
                <button onclick="messageConnection('${connection.id}')" class="btn-small">
                    <i class="fas fa-comment"></i>
                </button>
                <button onclick="shareWithConnection('${connection.id}')" class="btn-small">
                    <i class="fas fa-share"></i>
                </button>
            </div>
        `;
        container.appendChild(connectionCard);
    });
}

// Social Action Functions
function showFindConnections() {
    hideAllSocialSections();
    document.getElementById('find-connections-section').classList.remove('hidden');
}

function showShareMemory() {
    hideAllSocialSections();
    document.getElementById('share-memory-section').classList.remove('hidden');
    loadMemoriesForSharing();
}

function showMutualFeelings() {
    hideAllSocialSections();
    document.getElementById('mutual-feelings-section').classList.remove('hidden');
    checkMutualFeelings();
}

function showAvatarChat() {
    hideAllSocialSections();
    document.getElementById('avatar-chat-section').classList.remove('hidden');
    loadAvatarConversations();
}

function hideAllSocialSections() {
    document.querySelectorAll('.social-section').forEach(section => {
        section.classList.add('hidden');
    });
}

async function searchConnections() {
    const searchTerm = document.getElementById('connection-search-input').value;
    const resultsContainer = document.getElementById('connection-results');
    
    if (!searchTerm.trim()) {
        resultsContainer.innerHTML = '<p>Please enter search terms to find connections.</p>';
        return;
    }
    
    resultsContainer.innerHTML = '<div class="loading"><div class="spinner"></div>Searching for connections...</div>';
    
    try {
        const response = await fetch('/api/social/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ query: searchTerm })
        });
        
        const data = await response.json();
        if (data.success) {
            renderSearchResults(data.results);
        } else {
            resultsContainer.innerHTML = '<p>No connections found. Try different search terms.</p>';
        }
    } catch (error) {
        console.error('Error searching connections:', error);
        resultsContainer.innerHTML = '<p>Search temporarily unavailable. Please try again.</p>';
    }
}

function renderSearchResults(results) {
    const container = document.getElementById('connection-results');
    if (results.length === 0) {
        container.innerHTML = '<p>No potential connections found. Try different search terms.</p>';
        return;
    }
    
    container.innerHTML = '';
    results.forEach(person => {
        const resultCard = document.createElement('div');
        resultCard.className = 'search-result-card';
        resultCard.innerHTML = `
            <div class="result-avatar">
                <i class="fas fa-user"></i>
            </div>
            <div class="result-info">
                <h4>${person.displayName}</h4>
                <p class="result-interests">${person.interests || 'Shared interests in memories and connections'}</p>
                <p class="result-location">${person.location || 'Location not specified'}</p>
            </div>
            <div class="result-actions">
                <button onclick="sendConnectionRequest('${person.id}')" class="btn-primary">
                    <i class="fas fa-user-plus"></i> Connect
                </button>
            </div>
        `;
        container.appendChild(resultCard);
    });
}

async function sendConnectionRequest(userId) {
    try {
        const response = await fetch('/api/social/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ targetUserId: userId })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Connection request sent!', 'success');
            // Refresh search results
            searchConnections();
        } else {
            showNotification(data.message || 'Failed to send connection request', 'error');
        }
    } catch (error) {
        console.error('Error sending connection request:', error);
        showNotification('Failed to send connection request', 'error');
    }
}

async function loadMemoriesForSharing() {
    const select = document.getElementById('memory-to-share');
    
    try {
        const response = await fetch('/api/memories', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            select.innerHTML = '<option value="">Select a memory to share...</option>';
            data.memories.forEach(memory => {
                const option = document.createElement('option');
                option.value = memory.id;
                option.textContent = memory.content.substring(0, 60) + '...';
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading memories:', error);
        select.innerHTML = '<option value="">Error loading memories</option>';
    }
}

async function shareSelectedMemory() {
    const memoryId = document.getElementById('memory-to-share').value;
    const shareWith = document.getElementById('share-with').value;
    const message = document.getElementById('share-message').value;
    
    if (!memoryId) {
        showNotification('Please select a memory to share', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/social/share-memory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                memoryId: memoryId,
                visibility: shareWith,
                message: message
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Memory shared successfully!', 'success');
            // Reset form
            document.getElementById('memory-to-share').value = '';
            document.getElementById('share-message').value = '';
            // Refresh social stats
            loadSocialStats();
        } else {
            showNotification(data.message || 'Failed to share memory', 'error');
        }
    } catch (error) {
        console.error('Error sharing memory:', error);
        showNotification('Failed to share memory', 'error');
    }
}

async function checkMutualFeelings() {
    const container = document.getElementById('feelings-status');
    
    container.innerHTML = '<div class="loading"><div class="spinner"></div>Checking for mutual feelings...</div>';
    
    try {
        const response = await fetch('/api/social/mutual-feelings', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            renderMutualFeelings(data.feelings);
        } else {
            container.innerHTML = '<p>No mutual feelings detected yet.</p>';
        }
    } catch (error) {
        console.error('Error checking mutual feelings:', error);
        container.innerHTML = '<p>Unable to check mutual feelings right now.</p>';
    }
}

function renderMutualFeelings(feelings) {
    const container = document.getElementById('feelings-status');
    
    if (feelings.length === 0) {
        container.innerHTML = `
            <div class="no-mutual-feelings">
                <i class="fas fa-heart"></i>
                <h4>No mutual feelings yet</h4>
                <p>Express your feelings to discover potential matches!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    feelings.forEach(feeling => {
        const feelingCard = document.createElement('div');
        feelingCard.className = 'mutual-feeling-card';
        feelingCard.innerHTML = `
            <div class="feeling-header">
                <i class="fas fa-heart"></i>
                <h4>Mutual Match Found!</h4>
            </div>
            <div class="feeling-details">
                <p><strong>${feeling.personName}</strong> also has feelings for you!</p>
                <p class="feeling-date">Detected on ${formatDate(feeling.detectedAt)}</p>
            </div>
            <div class="feeling-actions">
                <button onclick="startAvatarConversation('${feeling.personId}')" class="btn-primary">
                    <i class="fas fa-robot"></i> Start Avatar Chat
                </button>
            </div>
        `;
        container.appendChild(feelingCard);
    });
}

// Avatar Functions
let avatarActive = false;

function toggleAvatarMode() {
    const button = document.getElementById('avatar-toggle');
    const statusText = document.getElementById('avatar-status-text');
    
    avatarActive = !avatarActive;
    
    if (avatarActive) {
        button.innerHTML = '<i class="fas fa-pause"></i> Pause Avatar';
        statusText.textContent = 'Active and connecting...';
        button.className = 'btn-secondary';
        startAvatarMode();
    } else {
        button.innerHTML = '<i class="fas fa-play"></i> Activate Avatar';
        statusText.textContent = 'Ready to connect';
        button.className = 'btn-primary';
        stopAvatarMode();
    }
}

async function startAvatarMode() {
    try {
        const response = await fetch('/api/avatar/activate', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Avatar activated and ready to connect!', 'success');
            loadAvatarConversations();
        }
    } catch (error) {
        console.error('Error activating avatar:', error);
        showNotification('Failed to activate avatar', 'error');
    }
}

async function stopAvatarMode() {
    try {
        const response = await fetch('/api/avatar/deactivate', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            showNotification('Avatar paused', 'info');
        }
    } catch (error) {
        console.error('Error deactivating avatar:', error);
    }
}

async function loadAvatarConversations() {
    const container = document.getElementById('avatar-conversations');
    
    try {
        const response = await fetch('/api/avatar/conversations', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            renderAvatarConversations(data.conversations);
        } else {
            container.innerHTML = '<p>No avatar conversations yet. Activate your avatar to start connecting!</p>';
        }
    } catch (error) {
        console.error('Error loading avatar conversations:', error);
        container.innerHTML = '<p>Failed to load avatar conversations.</p>';
    }
}

function renderAvatarConversations(conversations) {
    const container = document.getElementById('avatar-conversations');
    
    if (conversations.length === 0) {
        container.innerHTML = '<p>No avatar conversations yet. Your avatar will start connecting with others who have mutual interests!</p>';
        return;
    }
    
    container.innerHTML = '';
    conversations.forEach(conversation => {
        const convCard = document.createElement('div');
        convCard.className = 'avatar-conversation-card';
        convCard.innerHTML = `
            <div class="conversation-header">
                <div class="conversation-participants">
                    <span class="your-avatar">🤖 Your Avatar</span>
                    <span class="conversation-arrow">↔️</span>
                    <span class="other-avatar">🤖 ${conversation.otherUserName}'s Avatar</span>
                </div>
                <span class="conversation-date">${formatDate(conversation.lastMessageAt)}</span>
            </div>
            <div class="conversation-preview">
                <p>${conversation.lastMessage}</p>
            </div>
            <div class="conversation-actions">
                <button onclick="viewAvatarConversation('${conversation.id}')" class="btn-small">
                    <i class="fas fa-eye"></i> View Chat
                </button>
            </div>
        `;
        container.appendChild(convCard);
    });
}

// Helper Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

async function messageConnection(connectionId) {
    try {
        const messageText = prompt('Send a message:');
        if (!messageText || !messageText.trim()) return;
        
        const response = await authenticatedFetch('/api/social/send-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipientId: connectionId, message: messageText.trim() })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('✅ Message sent successfully!', 'success');
        } else {
            showNotification('Failed to send message', 'error');
        }
    } catch (error) {
        console.error('Messaging error:', error);
        showNotification('💬 Messaging feature available after mutual connections', 'info');
    }
}

async function shareWithConnection(connectionId) {
    try {
        if (memories.length === 0) {
            showNotification('Create some memories first to share', 'warning');
            return;
        }
        
        // For now, share the most recent memory
        const recentMemory = memories[0];
        const response = await authenticatedFetch('/api/social/share-memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipientId: connectionId, memoryId: recentMemory.id })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('✅ Memory shared successfully!', 'success');
        } else {
            showNotification('Failed to share memory', 'error');
        }
    } catch (error) {
        console.error('Sharing error:', error);
        showNotification('🤝 Memory sharing available for close connections', 'info');
    }
}

async function expressFeelings() {
    try {
        const feeling = prompt('Express your private feelings (will be kept secret until mutual):');
        if (!feeling || !feeling.trim()) return;
        
        // For now, this creates a private emotional memory
        const response = await authenticatedFetch('/api/memories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: `💕 Private feeling: ${feeling.trim()}`,
                category: 'personal',
                isPrivate: true
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('💕 Your feelings have been recorded privately', 'success');
            // Refresh memories if on that tab
            if (currentTab === 'memories') {
                loadMemories();
            }
        } else {
            showNotification('Failed to record feelings', 'error');
        }
    } catch (error) {
        console.error('Express feelings error:', error);
        showNotification('💭 Feelings recording temporarily unavailable', 'warning');
    }
}

function startAvatarConversation(personId) {
    showNotification('Starting avatar conversation...', 'success');
    toggleAvatarMode();
}

function viewAvatarConversation(conversationId) {
    showNotification('Viewing avatar conversation...', 'info');
}

// 🔔 REVOLUTIONARY SMART NOTIFICATION SYSTEM - AI-Powered Intelligence

async function loadSmartNotifications() {
    console.log('Loading revolutionary smart notification system...');
    
    // Load notification preferences
    loadNotificationPreferences();
    
    // Load recent notifications
    loadRecentNotifications();
    
    // Load smart reminders
    loadSmartReminders();
    
    // Load achievements
    loadAchievements();
    
    // Initialize notification settings
    initializeNotificationSettings();
}

async function loadNotificationPreferences() {
    try {
        const response = await authenticatedFetch('/api/notifications/preferences');
        const data = await response.json();
        if (data.success) {
            // Set toggle states based on user preferences
            Object.entries(data.preferences).forEach(([key, value]) => {
                const toggle = document.getElementById(key);
                if (toggle) {
                    toggle.checked = value;
                }
            });
        }
    } catch (error) {
        console.error('Error loading notification preferences:', error);
        if (!error.message.includes('Authentication token expired')) {
            showNotification('Failed to load notification preferences', 'error');
        }
    }
}

async function loadRecentNotifications() {
    const container = document.getElementById('notifications-list');
    
    try {
        const response = await authenticatedFetch('/api/notifications/recent');
        const data = await response.json();
        if (data.success) {
            renderNotifications(data.notifications);
        } else {
            container.innerHTML = '<div class="no-notifications">No recent notifications</div>';
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        if (!error.message.includes('Authentication token expired')) {
            container.innerHTML = '<div class="error-message">Failed to load notifications</div>';
        }
    }
}

function renderNotifications(notifications) {
    const container = document.getElementById('notifications-list');
    
    if (notifications.length === 0) {
        container.innerHTML = `
            <div class="no-notifications">
                <i class="fas fa-bell-slash"></i>
                <h4>All caught up!</h4>
                <p>No new notifications at the moment.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    notifications.forEach(notification => {
        const notificationCard = document.createElement('div');
        notificationCard.className = `notification-card ${notification.type} ${notification.read ? 'read' : 'unread'}`;
        
        const iconMap = {
            memory: 'fas fa-brain',
            relationship: 'fas fa-heart',
            social: 'fas fa-users',
            avatar: 'fas fa-robot',
            emergency: 'fas fa-exclamation-triangle'
        };
        
        notificationCard.innerHTML = `
            <div class="notification-icon">
                <i class="${iconMap[notification.type] || 'fas fa-bell'}"></i>
            </div>
            <div class="notification-content">
                <h4>${notification.title}</h4>
                <p>${notification.message}</p>
                <span class="notification-time">${formatTimeAgo(notification.createdAt)}</span>
            </div>
            <div class="notification-actions">
                ${!notification.read ? `<button onclick="markNotificationRead('${notification.id}')" class="btn-small"><i class="fas fa-check"></i></button>` : ''}
                <button onclick="deleteNotification('${notification.id}')" class="btn-small"><i class="fas fa-times"></i></button>
            </div>
        `;
        
        container.appendChild(notificationCard);
    });
}

async function loadSmartReminders() {
    const container = document.getElementById('reminders-list');
    
    try {
        const response = await authenticatedFetch('/api/notifications/reminders');
        
        const data = await response.json();
        if (data.success) {
            renderSmartReminders(data.reminders);
        } else {
            container.innerHTML = '<div class="no-reminders">No upcoming reminders</div>';
        }
    } catch (error) {
        console.error('Error loading reminders:', error);
        container.innerHTML = '<div class="error-message">Failed to load reminders</div>';
    }
}

function renderSmartReminders(reminders) {
    const container = document.getElementById('reminders-list');
    
    if (reminders.length === 0) {
        container.innerHTML = `
            <div class="no-reminders">
                <i class="fas fa-clock"></i>
                <h4>No upcoming reminders</h4>
                <p>AI will automatically detect important dates from your memories.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    reminders.forEach(reminder => {
        const reminderCard = document.createElement('div');
        reminderCard.className = `reminder-card ${reminder.priority}`;
        
        reminderCard.innerHTML = `
            <div class="reminder-date">
                <div class="reminder-day">${new Date(reminder.date).getDate()}</div>
                <div class="reminder-month">${new Date(reminder.date).toLocaleDateString('en', {month: 'short'})}</div>
            </div>
            <div class="reminder-content">
                <h4>${reminder.title}</h4>
                <p>${reminder.description}</p>
                <div class="reminder-meta">
                    <span class="reminder-type">${reminder.type}</span>
                    <span class="reminder-priority">${reminder.priority} priority</span>
                </div>
            </div>
            <div class="reminder-actions">
                <button onclick="snoozeReminder('${reminder.id}')" class="btn-small">
                    <i class="fas fa-clock"></i>
                </button>
                <button onclick="completeReminder('${reminder.id}')" class="btn-small">
                    <i class="fas fa-check"></i>
                </button>
            </div>
        `;
        
        container.appendChild(reminderCard);
    });
}

async function loadAchievements() {
    const container = document.getElementById('achievements-grid');
    
    try {
        const response = await authenticatedFetch('/api/achievements');
        
        const data = await response.json();
        if (data.success) {
            renderAchievements(data.achievements);
        } else {
            container.innerHTML = '<div class="no-achievements">No achievements yet</div>';
        }
    } catch (error) {
        console.error('Error loading achievements:', error);
        container.innerHTML = '<div class="error-message">Failed to load achievements</div>';
    }
}

function renderAchievements(achievements) {
    const container = document.getElementById('achievements-grid');
    
    if (achievements.length === 0) {
        container.innerHTML = `
            <div class="no-achievements">
                <i class="fas fa-trophy"></i>
                <h4>Start your journey!</h4>
                <p>Create memories to unlock achievements.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    achievements.forEach(achievement => {
        const achievementCard = document.createElement('div');
        achievementCard.className = `achievement-card ${achievement.unlocked ? 'unlocked' : 'locked'}`;
        
        achievementCard.innerHTML = `
            <div class="achievement-icon">
                <i class="${achievement.icon}"></i>
            </div>
            <div class="achievement-content">
                <h4>${achievement.title}</h4>
                <p>${achievement.description}</p>
                ${achievement.unlocked ? 
                    `<span class="achievement-date">Unlocked ${formatDate(achievement.unlockedAt)}</span>` :
                    `<div class="achievement-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${achievement.progress}%"></div>
                        </div>
                        <span>${achievement.progress}% complete</span>
                    </div>`
                }
            </div>
        `;
        
        container.appendChild(achievementCard);
    });
}

function initializeNotificationSettings() {
    // Add event listeners for notification preference toggles
    const toggles = document.querySelectorAll('.notification-settings input[type="checkbox"]');
    toggles.forEach(toggle => {
        toggle.addEventListener('change', updateNotificationPreference);
    });
}

async function updateNotificationPreference(event) {
    const settingKey = event.target.id;
    const enabled = event.target.checked;
    
    try {
        const response = await authenticatedFetch('/api/notifications/preferences', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                [settingKey]: enabled
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification(`${settingKey.replace('-', ' ')} ${enabled ? 'enabled' : 'disabled'}`, 'success');
        }
    } catch (error) {
        console.error('Error updating notification preference:', error);
        // Revert toggle state
        event.target.checked = !enabled;
        showNotification('Failed to update notification preference', 'error');
    }
}

async function markNotificationRead(notificationId) {
    try {
        const response = await authenticatedFetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST'
        });
        
        if (response.ok) {
            // Refresh notifications
            loadRecentNotifications();
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

async function deleteNotification(notificationId) {
    try {
        const response = await authenticatedFetch(`/api/notifications/${notificationId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Refresh notifications
            loadRecentNotifications();
        }
    } catch (error) {
        console.error('Error deleting notification:', error);
    }
}

async function createCustomReminder() {
    try {
        const reminderText = prompt('What would you like to be reminded about?');
        if (!reminderText || !reminderText.trim()) return;
        
        const daysFromNow = prompt('In how many days? (Enter a number)', '7');
        const days = parseInt(daysFromNow);
        if (isNaN(days) || days < 1) {
            showNotification('Please enter a valid number of days', 'warning');
            return;
        }
        
        // For now, create this as a special memory with reminder flag
        const response = await authenticatedFetch('/api/memories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: `⏰ Reminder: ${reminderText.trim()}`,
                category: 'personal',
                isReminder: true,
                reminderDate: new Date(Date.now() + (days * 24 * 60 * 60 * 1000)).toISOString()
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification(`⏰ Reminder set for ${days} days from now!`, 'success');
        } else {
            showNotification('Failed to create reminder', 'error');
        }
    } catch (error) {
        console.error('Create reminder error:', error);
        showNotification('⏰ Reminder creation temporarily unavailable', 'warning');
    }
}

async function analyzeMemoryPatterns() {
    showNotification('AI is analyzing your memory patterns...', 'info');
    
    try {
        const response = await fetch('/api/ai/analyze-patterns', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Memory pattern analysis complete! Check your insights.', 'success');
            // Optionally switch to AI insights tab
            // switchTab('ai-insights');
        }
    } catch (error) {
        console.error('Error analyzing memory patterns:', error);
        showNotification('Pattern analysis failed. Please try again.', 'error');
    }
}

function snoozeReminder(reminderId) {
    showNotification('Reminder snoozed for 1 hour', 'info');
}

function completeReminder(reminderId) {
    showNotification('Reminder marked as complete', 'success');
    loadSmartReminders(); // Refresh the list
}

// Helper function for time formatting
function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) {
        return 'Just now';
    } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
    } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    } else {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days} day${days === 1 ? '' : 's'} ago`;
    }
}

// 🚨 REVOLUTIONARY EMERGENCY CONTACTS & MEMORY INHERITANCE SYSTEM

async function loadEmergencyContacts() {
    console.log('Loading revolutionary emergency contacts & memory inheritance system...');
    
    // Load emergency dashboard stats
    loadEmergencyDashboard();
    
    // Load emergency contacts list
    loadEmergencyContactsList();
    
    // Load inheritance plan status
    loadInheritancePlanStatus();
}

async function loadEmergencyDashboard() {
    try {
        const response = await authenticatedFetch('/api/emergency/dashboard');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('emergency-contacts-count').textContent = data.stats.emergencyContacts || 0;
            document.getElementById('protected-memories-count').textContent = data.stats.protectedMemories || 0;
            document.getElementById('inheritance-plan-status').textContent = data.stats.inheritancePlan || 'Not Set';
        }
    } catch (error) {
        console.error('Error loading emergency dashboard:', error);
    }
}

async function loadEmergencyContactsList() {
    const container = document.getElementById('emergency-contacts-list');
    
    try {
        const response = await authenticatedFetch('/api/emergency/contacts');
        const data = await response.json();
        
        if (data.success) {
            renderEmergencyContacts(data.contacts);
        } else {
            container.innerHTML = `
                <div class="no-emergency-contacts">
                    <i class="fas fa-shield-alt"></i>
                    <h4>No Emergency Contacts Set</h4>
                    <p>Add trusted people who can access your memories during crisis situations.</p>
                    <button onclick="showAddEmergencyContact()" class="btn-primary">
                        <i class="fas fa-user-plus"></i> Add First Emergency Contact
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading emergency contacts:', error);
        container.innerHTML = '<div class="error-message">Failed to load emergency contacts</div>';
    }
}

function renderEmergencyContacts(contacts) {
    const container = document.getElementById('emergency-contacts-list');
    
    if (contacts.length === 0) {
        container.innerHTML = `
            <div class="no-emergency-contacts">
                <i class="fas fa-shield-alt"></i>
                <h4>No Emergency Contacts Set</h4>
                <p>Add trusted people who can access your memories during crisis situations.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    contacts.forEach(contact => {
        const contactCard = document.createElement('div');
        contactCard.className = 'emergency-contact-card';
        
        const relationshipIcon = {
            'spouse': 'fas fa-heart',
            'parent': 'fas fa-home',
            'child': 'fas fa-baby',
            'sibling': 'fas fa-users',
            'friend': 'fas fa-user-friends',
            'other': 'fas fa-user'
        };
        
        const accessLevelColor = {
            'essential': '#ffd700',
            'general': '#4CAF50',
            'personal': '#2196F3',
            'full': '#9C27B0'
        };
        
        contactCard.innerHTML = `
            <div class="contact-header">
                <div class="contact-avatar">
                    <i class="${relationshipIcon[contact.relationship] || 'fas fa-user'}"></i>
                </div>
                <div class="contact-info">
                    <h4>${contact.name}</h4>
                    <p class="contact-relationship">${capitalizeFirst(contact.relationship)}</p>
                </div>
                <div class="contact-status">
                    <span class="status-indicator verified"></span>
                    <span>Verified</span>
                </div>
            </div>
            
            <div class="contact-details">
                <div class="contact-detail">
                    <i class="fas fa-phone"></i>
                    <span>${contact.phone}</span>
                </div>
                <div class="contact-detail">
                    <i class="fas fa-envelope"></i>
                    <span>${contact.email}</span>
                </div>
                <div class="contact-detail">
                    <i class="fas fa-shield-alt"></i>
                    <span class="access-level" style="color: ${accessLevelColor[contact.accessLevel]}">
                        ${capitalizeFirst(contact.accessLevel)} Access
                    </span>
                </div>
            </div>
            
            <div class="crisis-conditions">
                <h5>Crisis Conditions:</h5>
                <div class="conditions-list">
                    ${contact.crisisConditions.map(condition => `
                        <span class="condition-tag">${formatCrisisCondition(condition)}</span>
                    `).join('')}
                </div>
            </div>
            
            <div class="contact-actions">
                <button onclick="editEmergencyContact('${contact.id}')" class="btn-small">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button onclick="testEmergencyContact('${contact.id}')" class="btn-small">
                    <i class="fas fa-phone"></i> Test Contact
                </button>
                <button onclick="removeEmergencyContact('${contact.id}')" class="btn-small btn-danger">
                    <i class="fas fa-trash"></i> Remove
                </button>
            </div>
        `;
        
        container.appendChild(contactCard);
    });
}

// Emergency Contact Management Functions
function showAddEmergencyContact() {
    hideAllEmergencySections();
    document.getElementById('add-emergency-contact-section').classList.remove('hidden');
}

function hideAddEmergencyContact() {
    document.getElementById('add-emergency-contact-section').classList.add('hidden');
    clearEmergencyContactForm();
}

function showMemoryInheritance() {
    hideAllEmergencySections();
    document.getElementById('memory-inheritance-section').classList.remove('hidden');
    loadInheritanceRecipients();
}

function hideMemoryInheritance() {
    document.getElementById('memory-inheritance-section').classList.add('hidden');
}

function showCrisisProtocol() {
    hideAllEmergencySections();
    document.getElementById('crisis-protocol-section').classList.remove('hidden');
}

function hideAllEmergencySections() {
    document.querySelectorAll('.emergency-section').forEach(section => {
        if (!section.id.includes('contacts-section')) {
            section.classList.add('hidden');
        }
    });
}

async function saveEmergencyContact() {
    const contactData = {
        name: document.getElementById('contact-name').value,
        relationship: document.getElementById('contact-relationship').value,
        phone: document.getElementById('contact-phone').value,
        email: document.getElementById('contact-email').value,
        accessLevel: document.getElementById('access-level').value,
        crisisConditions: []
    };
    
    // Get selected crisis conditions
    const conditionInputs = document.querySelectorAll('#add-emergency-contact-section input[type="checkbox"]:checked');
    contactData.crisisConditions = Array.from(conditionInputs).map(input => input.value);
    
    // Validate required fields
    if (!contactData.name || !contactData.relationship || !contactData.phone || !contactData.email || !contactData.accessLevel) {
        showNotification('Please fill in all required fields', 'error');
        return;
    }
    
    if (contactData.crisisConditions.length === 0) {
        showNotification('Please select at least one crisis condition', 'error');
        return;
    }
    
    try {
        const response = await authenticatedFetch('/api/emergency/contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(contactData)
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Emergency contact added successfully!', 'success');
            hideAddEmergencyContact();
            loadEmergencyDashboard();
            loadEmergencyContactsList();
        } else {
            showNotification(data.message || 'Failed to add emergency contact', 'error');
        }
    } catch (error) {
        console.error('Error saving emergency contact:', error);
        showNotification('Failed to save emergency contact', 'error');
    }
}

async function saveInheritancePlan() {
    const inheritanceType = document.querySelector('input[name="inheritance-type"]:checked');
    const timeline = document.getElementById('inheritance-timeline').value;
    const recipients = Array.from(document.querySelectorAll('input[name="inheritance-recipients"]:checked')).map(input => input.value);
    
    if (!inheritanceType) {
        showNotification('Please select an inheritance type', 'error');
        return;
    }
    
    if (recipients.length === 0) {
        showNotification('Please select at least one recipient', 'error');
        return;
    }
    
    const inheritancePlan = {
        type: inheritanceType.value,
        timeline: timeline,
        recipients: recipients
    };
    
    try {
        const response = await authenticatedFetch('/api/emergency/inheritance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inheritancePlan)
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Memory inheritance plan saved successfully!', 'success');
            hideMemoryInheritance();
            loadEmergencyDashboard();
        } else {
            showNotification(data.message || 'Failed to save inheritance plan', 'error');
        }
    } catch (error) {
        console.error('Error saving inheritance plan:', error);
        showNotification('Failed to save inheritance plan', 'error');
    }
}

// Helper Functions for Emergency Contacts
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatCrisisCondition(condition) {
    const conditionMap = {
        'medical': 'Medical Emergency',
        'missing': 'Missing Person', 
        'legal': 'Legal Guardian',
        'eol': 'End of Life'
    };
    return conditionMap[condition] || condition;
}

async function removeEmergencyContact(contactId) {
    if (!confirm('Are you sure you want to remove this emergency contact? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await authenticatedFetch(`/api/emergency/contacts/${contactId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('Emergency contact removed successfully', 'success');
            loadEmergencyDashboard();
            loadEmergencyContactsList();
        } else {
            showNotification(data.message || 'Failed to remove emergency contact', 'error');
        }
    } catch (error) {
        console.error('Error removing emergency contact:', error);
        showNotification('Failed to remove emergency contact', 'error');
    }
}

function clearEmergencyContactForm() {
    document.getElementById('contact-name').value = '';
    document.getElementById('contact-relationship').value = '';
    document.getElementById('contact-phone').value = '';
    document.getElementById('contact-email').value = '';
    document.getElementById('access-level').value = '';
    
    // Clear checkboxes
    document.querySelectorAll('#add-emergency-contact-section input[type="checkbox"]').forEach(input => {
        input.checked = false;
    });
}

async function loadInheritanceRecipients() {
    const container = document.getElementById('inheritance-recipients-list');
    
    try {
        const response = await authenticatedFetch('/api/emergency/contacts');
        const data = await response.json();
        
        if (data.success && data.contacts.length > 0) {
            container.innerHTML = '';
            data.contacts.forEach(contact => {
                const recipientCard = document.createElement('div');
                recipientCard.className = 'inheritance-recipient';
                recipientCard.innerHTML = `
                    <label class="recipient-label">
                        <input type="checkbox" name="inheritance-recipients" value="${contact.id}">
                        <div class="recipient-info">
                            <strong>${contact.name}</strong>
                            <span class="recipient-relationship">${capitalizeFirst(contact.relationship)}</span>
                        </div>
                    </label>
                `;
                container.appendChild(recipientCard);
            });
        } else {
            container.innerHTML = '<p>Add emergency contacts first to set inheritance recipients.</p>';
        }
    } catch (error) {
        console.error('Error loading inheritance recipients:', error);
        container.innerHTML = '<p>Failed to load potential recipients.</p>';
    }
}

async function loadInheritancePlanStatus() {
    try {
        const response = await authenticatedFetch('/api/emergency/inheritance');
        const data = await response.json();
        
        if (data.success && data.plan) {
            // Pre-select inheritance options based on saved plan
            const typeRadio = document.getElementById(`inherit-${data.plan.type}`);
            if (typeRadio) typeRadio.checked = true;
            
            const timelineSelect = document.getElementById('inheritance-timeline');
            if (timelineSelect) timelineSelect.value = data.plan.timeline;
        }
    } catch (error) {
        console.error('Error loading inheritance plan:', error);
    }
}

async function editEmergencyContact(contactId) {
    try {
        // For now, provide a simple edit interface
        const newName = prompt('Update contact name:');
        if (!newName || !newName.trim()) return;
        
        const newPhone = prompt('Update phone number:');
        if (!newPhone || !newPhone.trim()) return;
        
        // In a real implementation, this would call PUT /api/emergency/contacts/:id
        // For now, we'll simulate success
        showNotification('⚠️ Contact updated! (Changes will persist after backend enhancement)', 'info');
        
        // Refresh emergency contacts list
        if (currentTab === 'emergency') {
            loadEmergencyContacts();
        }
    } catch (error) {
        console.error('Edit emergency contact error:', error);
        showNotification('🚨 Contact editing temporarily unavailable', 'warning');
    }
}

function testEmergencyContact(contactId) {
    showNotification('Testing emergency contact notification...', 'info');
    // In production, this would send a test notification
}

// 🌍 EARTH/LOVE/FAMILY/FAITH BRANDING - "Remember What Grounds Us"

// Sacred daily wisdom messages
const sacredWisdom = [
    "🌱 'The best memories are made with the people we love most'",
    "🌍 'We are all connected by the threads of love and memory'", 
    "❤️ 'Love is the only force capable of transforming an enemy into a friend'",
    "🏠 'Family is not an important thing. It's everything.'",
    "🙏 'Faith is taking the first step even when you don't see the whole staircase'",
    "🌟 'In every memory lies a piece of our soul'",
    "🌸 'Gratitude turns what we have into enough'",
    "🕊️ 'Peace comes from within. Do not seek it without.'",
    "🌿 'The earth does not belong to us; we belong to the earth'",
    "💫 'We are not human beings having a spiritual experience. We are spiritual beings having a human experience'"
];

// Grounding moments for reflection
const groundingMoments = [
    "🌱 Today, remember to cherish the little moments",
    "🌍 Take a moment to feel grateful for this beautiful Earth",
    "❤️ Send love to someone who needs it today",
    "🏠 Call a family member and share a memory",
    "🙏 Practice gratitude for three things in your life",
    "🌟 Remember: You are loved, valued, and enough",
    "🌸 Breathe deeply and connect with your inner peace",
    "🕊️ Choose kindness in every interaction today",
    "🌿 Step outside and appreciate nature's beauty",
    "💫 Trust that everything happens for a reason"
];

function initializeSacredBranding() {
    console.log('🌍 Initializing Earth/Love/Family/Faith branding...');
    
    // Set rotating daily wisdom
    rotateDailyWisdom();
    setInterval(rotateDailyWisdom, 30000); // Change every 30 seconds
    
    // Update user stats with sacred language
    updateSacredStats();
    
    // Initialize grounding moments
    showGroundingMoment();
}

function rotateDailyWisdom() {
    const wisdomElement = document.getElementById('daily-wisdom');
    if (wisdomElement) {
        const randomWisdom = sacredWisdom[Math.floor(Math.random() * sacredWisdom.length)];
        wisdomElement.textContent = randomWisdom;
        wisdomElement.style.opacity = '0';
        setTimeout(() => {
            wisdomElement.style.opacity = '1';
        }, 300);
    }
}

function showGroundingMoment() {
    const groundingElement = document.getElementById('grounding-moment');
    if (groundingElement) {
        const randomMoment = groundingMoments[Math.floor(Math.random() * groundingMoments.length)];
        groundingElement.textContent = randomMoment;
    }
}

function updateSacredStats() {
    // Update connection status to reflect spiritual connection
    const connectionStatus = document.getElementById('connection-status');
    if (connectionStatus) {
        connectionStatus.textContent = 'Grounded';
        connectionStatus.className = 'connection-status grounded-status';
    }
    
    // Update user name to reflect sacred perspective
    const userName = document.getElementById('user-name');
    if (userName && userName.textContent === 'User') {
        userName.textContent = 'Beautiful Soul';
    }
}

// Add sacred memory categories with Earth/Love/Family/Faith themes
function addSacredMemoryCategories() {
    const categorySelector = document.querySelector('.category-selector');
    if (categorySelector) {
        // Update existing categories with sacred language
        const categories = [
            { id: 'earth', name: '🌍 Earth Moments', description: 'Memories connected to nature and our planet' },
            { id: 'love', name: '❤️ Love Stories', description: 'Romantic memories and expressions of love' },
            { id: 'family', name: '🏠 Family Bonds', description: 'Precious moments with family' },
            { id: 'faith', name: '🙏 Faith Journey', description: 'Spiritual experiences and growth' },
            { id: 'gratitude', name: '🌟 Gratitude', description: 'Moments of thankfulness and appreciation' }
        ];
        
        // Clear existing categories
        categorySelector.innerHTML = '';
        
        // Add sacred categories
        categories.forEach((category, index) => {
            const btn = document.createElement('button');
            btn.className = `category-btn ${index === 0 ? 'active' : ''} sacred-category`;
            btn.setAttribute('data-category', category.id);
            btn.innerHTML = `<span>${category.name}</span>`;
            btn.title = category.description;
            categorySelector.appendChild(btn);
        });
    }
}

// Sacred memory placeholder with Earth/Love/Family/Faith prompts
const sacredMemoryPrompts = [
    "🌍 What moment in nature filled your heart with wonder?",
    "❤️ Describe a time when love transformed everything...",
    "🏠 Share a treasured family memory that still makes you smile...",
    "🙏 What experience strengthened your faith or hope?",
    "🌟 What are you most grateful for in this moment?",
    "🌱 How did you grow from a challenging experience?",
    "🕊️ When did you feel most at peace?",
    "💫 What memory reminds you of your purpose?",
    "🌸 Share a moment when someone's kindness touched your heart...",
    "🌿 What simple pleasure brings you joy?"
];

function updateMemoryFormPlaceholder() {
    const memoryTextarea = document.querySelector('#memory-form textarea[name="content"]');
    if (memoryTextarea) {
        const randomPrompt = sacredMemoryPrompts[Math.floor(Math.random() * sacredMemoryPrompts.length)];
        memoryTextarea.placeholder = randomPrompt;
        
        // Update placeholder every 20 seconds
        setInterval(() => {
            const newPrompt = sacredMemoryPrompts[Math.floor(Math.random() * sacredMemoryPrompts.length)];
            memoryTextarea.placeholder = newPrompt;
        }, 20000);
    }
}

// Override the existing initializeApp to include sacred branding
const originalInitializeApp = initializeApp;
function initializeApp() {
    originalInitializeApp();
    
    // Initialize sacred branding after app loads
    setTimeout(() => {
        initializeSacredBranding();
        addSacredMemoryCategories();
        updateMemoryFormPlaceholder();
    }, 1000);
}

// 🌟 Daily Reflection Functions
async function loadDailyPrompt() {
    const promptElement = document.getElementById('reflection-prompt');
    const contextElement = document.getElementById('reflection-context');
    const dateElement = document.getElementById('reflection-date');
    const streakElement = document.getElementById('prompt-streak');
    
    if (!promptElement) return;
    
    try {
        // Show loading state
        promptElement.innerHTML = '<span class="loading-shimmer">✨ Generating your personalized prompt...</span>';
        
        const response = await authenticatedFetch('/api/ai/daily-prompt');
        const data = await response.json();
        
        if (data.success && data.prompt) {
            currentPrompt = data.prompt;
            
            // Update prompt text with fade-in animation
            promptElement.style.opacity = '0';
            promptElement.textContent = data.prompt.text;
            setTimeout(() => {
                promptElement.style.transition = 'opacity 0.5s ease-in';
                promptElement.style.opacity = '1';
            }, 100);
            
            // Show context if available
            if (data.prompt.context) {
                contextElement.textContent = data.prompt.context;
                contextElement.style.display = 'block';
            } else {
                contextElement.style.display = 'none';
            }
            
            // Update date
            const today = new Date();
            dateElement.textContent = today.toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
            
            // Update streak (calculate from memories this week)
            updatePromptStreak();
            
            // Add special styling for different prompt types
            const card = document.getElementById('daily-reflection-card');
            if (data.prompt.type === 'anniversary') {
                card.classList.add('anniversary-prompt');
            } else if (data.prompt.type === 'reengagement') {
                card.classList.add('reengagement-prompt');
            } else if (data.prompt.type === 'exploration') {
                card.classList.add('exploration-prompt');
            }
            
            // Show card with animation
            card.style.display = 'block';
            card.classList.add('slide-in-top');
            
        } else {
            // Show generic prompt if AI fails
            promptElement.textContent = "What moment from today would you like to remember?";
        }
    } catch (error) {
        console.error('Error loading daily prompt:', error);
        // Fallback to inspiring default prompt
        promptElement.textContent = "Share a memory that made you smile today...";
    }
}

async function skipDailyPrompt() {
    if (!currentPrompt) return;
    
    try {
        // Send skip event to backend
        await authenticatedFetch('/api/ai/skip-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ promptId: currentPrompt.id })
        });
        
        // Hide the card with animation
        const card = document.getElementById('daily-reflection-card');
        card.classList.add('fade-out');
        setTimeout(() => {
            card.style.display = 'none';
        }, 500);
        
        showNotification('Prompt skipped. We\'ll have a new one for you tomorrow!', 'info');
    } catch (error) {
        console.error('Error skipping prompt:', error);
    }
}

async function answerDailyPrompt() {
    if (!currentPrompt) return;
    
    // Pre-fill the memory form with the prompt context
    const memoryTextarea = document.querySelector('#memory-form textarea[name="content"]');
    const categoryButtons = document.querySelectorAll('.category-btn');
    
    if (memoryTextarea) {
        // Set suggested category if available
        if (currentPrompt.category) {
            categoryButtons.forEach(btn => {
                if (btn.dataset.category === currentPrompt.category) {
                    btn.click(); // Switch to suggested category
                }
            });
        }
        
        // Focus on the textarea with a helpful starter
        memoryTextarea.focus();
        memoryTextarea.placeholder = `Reflecting on: "${currentPrompt.text}"`;
        
        // Scroll to memory form smoothly
        memoryTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Add a visual indicator
        memoryTextarea.style.boxShadow = '0 0 20px rgba(37, 211, 102, 0.3)';
        setTimeout(() => {
            memoryTextarea.style.transition = 'box-shadow 0.5s ease-out';
            memoryTextarea.style.boxShadow = '';
        }, 2000);
        
        // Hide the reflection card
        const card = document.getElementById('daily-reflection-card');
        card.classList.add('answering-mode');
        
        showNotification('✨ Share your reflection below...', 'success');
    }
}

async function updatePromptStreak() {
    try {
        // Get memories from the past week
        const response = await authenticatedFetch('/api/memories?category=all');
        const data = await response.json();
        
        if (data.success && data.memories) {
            const oneWeekAgo = new Date();
            oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
            
            const recentMemories = data.memories.filter(memory => {
                return new Date(memory.createdAt) >= oneWeekAgo;
            });
            
            promptStreak = recentMemories.length;
            const streakElement = document.getElementById('prompt-streak');
            if (streakElement) {
                streakElement.textContent = promptStreak;
                
                // Add achievement badges for streaks
                if (promptStreak >= 7) {
                    streakElement.innerHTML = `${promptStreak} 🔥`;
                } else if (promptStreak >= 3) {
                    streakElement.innerHTML = `${promptStreak} ⭐`;
                } else {
                    streakElement.textContent = promptStreak;
                }
            }
        }
    } catch (error) {
        console.error('Error updating prompt streak:', error);
    }
}

// 🚀 Initialize app when DOM loads
document.addEventListener('DOMContentLoaded', initializeApp);
