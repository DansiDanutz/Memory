import React, { useState, useContext, useEffect, useCallback, useRef } from 'react';
import { 
  Search, Settings, Moon, Sun, MessageCircle, Brain, Smartphone,
  RefreshCw, Send, AlertCircle, Loader, Plus, X, Trophy, Home, User, Crown,
  Zap, Sparkles, Gift, Star, TrendingUp, Award, Target, Heart, Shield,
  Volume2, Mic, Play, Pause, Download, Share2, Bookmark, Clock
} from 'lucide-react';
import { ThemeContext } from '../contexts/ThemeContext';
import { memoryService, claudeService, wsService, gamificationService } from '../services';
import whatsappService from '../services/whatsappService';
import MemoryCategories from './MemoryCategories';
import EnhancedRewardsTab from './EnhancedRewardsTab';
import BottomNav from './BottomNav';
import '../styles/enhanced-design-system.css';
import './EnhancedMemoryApp.css';

const EnhancedMemoryApp = () => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  
  // State management
  const [selectedContact, setSelectedContact] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isOnline, setIsOnline] = useState(false);
  const [view, setView] = useState('dashboard'); // 'dashboard', 'memories', 'chat', 'rewards', 'voice'
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [messageInput, setMessageInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [syncStatus, setSyncStatus] = useState('offline');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [activities, setActivities] = useState([]);
  const [isPremium, setIsPremium] = useState(false);
  const [showContactPicker, setShowContactPicker] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [contactSlots, setContactSlots] = useState(new Array(5).fill(null));
  const [whatsappStatus, setWhatsappStatus] = useState({
    isReady: false,
    isAuthenticated: false,
    contactCount: 0
  });
  
  // Enhanced UI state
  const [showNotifications, setShowNotifications] = useState([]);
  const [userStats, setUserStats] = useState({
    level: 1,
    points: 0,
    streak: 0,
    achievements: 0,
    voiceCredits: 0
  });
  const [isRecording, setIsRecording] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  
  // Animation state
  const [animationQueue, setAnimationQueue] = useState([]);
  const [counterAnimations, setCounterAnimations] = useState({});
  
  // Mobile and gesture state
  const [isMobile, setIsMobile] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isPullRefreshing, setIsPullRefreshing] = useState(false);
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  
  // Refs
  const scrollContainerRef = useRef(null);
  const notificationTimeouts = useRef(new Map());
  
  // User ID
  const userId = localStorage.getItem('userId') || 'default_user';

  // Initialize and load data
  useEffect(() => {
    initializeApp();
    loadUserStats();
    setupEventListeners();
    detectMobile();
  }, []);

  const initializeApp = async () => {
    if (!localStorage.getItem('userId')) {
      localStorage.setItem('userId', 'user_' + Date.now());
    }
    
    try {
      setLoading(true);
      await Promise.all([
        loadMemories(),
        loadActivities(),
        connectWebSocket()
      ]);
    } catch (error) {
      console.error('Failed to initialize app:', error);
      showNotification('Failed to initialize app', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadUserStats = async () => {
    try {
      const stats = await gamificationService.getUserStats(userId);
      if (stats) {
        animateCounterChange('points', userStats.points, stats.points || 0);
        animateCounterChange('level', userStats.level, stats.level || 1);
        animateCounterChange('streak', userStats.streak, stats.daily_streak || 0);
        
        setUserStats({
          level: stats.level || 1,
          points: stats.points || 0,
          streak: stats.daily_streak || 0,
          achievements: stats.achievements_unlocked || 0,
          voiceCredits: stats.voice_credits || 0
        });
      }
    } catch (error) {
      console.error('Failed to load user stats:', error);
    }
  };

  const loadMemories = async () => {
    try {
      const response = await memoryService.getMemories(userId);
      setMemories(response || []);
    } catch (error) {
      console.error('Failed to load memories:', error);
      setMemories([]);
    }
  };

  const loadActivities = async () => {
    try {
      const response = await memoryService.getActivities(userId);
      setActivities(response || []);
    } catch (error) {
      console.error('Failed to load activities:', error);
      setActivities([]);
    }
  };

  const connectWebSocket = async () => {
    try {
      await wsService.connect(userId);
      setWsConnected(true);
      setSyncStatus('connected');
      
      wsService.on('sync_status', (data) => {
        setSyncStatus(data.status);
      });
      
      wsService.on('new_memory', (data) => {
        setMemories(prev => [data.memory, ...prev]);
        showNotification('New memory added!', 'success');
        triggerConfetti();
      });
      
      wsService.on('achievement_unlocked', (data) => {
        showAchievementNotification(data.achievement);
        loadUserStats(); // Refresh stats
      });
      
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      setWsConnected(false);
      setSyncStatus('error');
    }
  };

  const setupEventListeners = () => {
    // Online/offline detection
    const handleOnline = () => {
      setIsOnline(true);
      showNotification('Back online!', 'success');
    };
    
    const handleOffline = () => {
      setIsOnline(false);
      showNotification('You are offline', 'warning');
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    setIsOnline(navigator.onLine);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  };

  const detectMobile = () => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  };

  // Notification system
  const showNotification = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now().toString();
    const notification = {
      id,
      message,
      type,
      timestamp: Date.now()
    };
    
    setShowNotifications(prev => [...prev, notification]);
    
    // Auto-remove notification
    const timeout = setTimeout(() => {
      setShowNotifications(prev => prev.filter(n => n.id !== id));
      notificationTimeouts.current.delete(id);
    }, duration);
    
    notificationTimeouts.current.set(id, timeout);
  }, []);

  const showAchievementNotification = useCallback((achievement) => {
    const notification = {
      id: `achievement_${Date.now()}`,
      type: 'achievement',
      achievement,
      timestamp: Date.now()
    };
    
    setShowNotifications(prev => [...prev, notification]);
    triggerConfetti();
    
    // Play achievement sound if available
    try {
      const audio = new Audio('/sounds/achievement.mp3');
      audio.play().catch(() => {});
    } catch (e) {}
    
    setTimeout(() => {
      setShowNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 6000);
  }, []);

  // Animation helpers
  const animateCounterChange = useCallback((key, oldValue, newValue) => {
    if (oldValue === newValue) return;
    
    setCounterAnimations(prev => ({
      ...prev,
      [key]: {
        from: oldValue,
        to: newValue,
        timestamp: Date.now()
      }
    }));
  }, []);

  const triggerConfetti = useCallback(() => {
    setShowConfetti(true);
    setTimeout(() => setShowConfetti(false), 3000);
  }, []);

  // Voice recording
  const toggleRecording = async () => {
    if (isRecording) {
      setIsRecording(false);
      showNotification('Recording stopped', 'success');
    } else {
      setIsRecording(true);
      showNotification('Recording started - speak naturally!', 'info');
    }
  };

  // Pull to refresh
  const handleTouchStart = (e) => {
    setTouchStart(e.touches[0].clientY);
  };

  const handleTouchMove = (e) => {
    if (!touchStart) return;
    
    const touchCurrent = e.touches[0].clientY;
    const diff = touchCurrent - touchStart;
    
    if (diff > 100 && scrollContainerRef.current?.scrollTop === 0) {
      setIsPullRefreshing(true);
    }
  };

  const handleTouchEnd = () => {
    if (isPullRefreshing) {
      refreshData();
    }
    setTouchStart(null);
    setIsPullRefreshing(false);
  };

  const refreshData = async () => {
    try {
      await Promise.all([
        loadMemories(),
        loadUserStats(),
        loadActivities()
      ]);
      showNotification('Data refreshed!', 'success');
    } catch (error) {
      showNotification('Failed to refresh data', 'error');
    }
  };

  // Enhanced navigation
  const navigationItems = [
    { key: 'dashboard', icon: Home, label: 'Dashboard', gradient: 'cosmic' },
    { key: 'memories', icon: Brain, label: 'Memories', gradient: 'purple' },
    { key: 'chat', icon: MessageCircle, label: 'Chat', gradient: 'pink' },
    { key: 'voice', icon: Mic, label: 'Voice', gradient: 'success', premium: true },
    { key: 'rewards', icon: Trophy, label: 'Rewards', gradient: 'warning' }
  ];

  const renderHeader = () => (
    <header className="app-header neuro-glass">
      <div className="header-content">
        <div className="header-left">
          <div className="app-logo">
            <Brain className="logo-icon" />
            <span className="neuro-heading">MemoApp</span>
          </div>
          <div className="connection-status">
            <div className={`status-dot ${wsConnected ? 'connected' : 'disconnected'}`} />
            <span className="status-text">
              {wsConnected ? 'Connected' : 'Connecting...'}
            </span>
          </div>
        </div>
        
        <div className="header-center">
          <div className="user-stats-mini">
            <div className="stat-item">
              <Crown className="stat-icon" />
              <AnimatedCounter value={userStats.level} />
            </div>
            <div className="stat-item">
              <Zap className="stat-icon" />
              <AnimatedCounter value={userStats.points} />
            </div>
            <div className="stat-item">
              <Sparkles className="stat-icon" />
              <AnimatedCounter value={userStats.streak} />
            </div>
          </div>
        </div>
        
        <div className="header-right">
          <button 
            className="icon-button"
            onClick={toggleTheme}
          >
            {theme === 'dark' ? <Sun /> : <Moon />}
          </button>
          
          {view === 'voice' && (
            <button 
              className={`record-button ${isRecording ? 'recording' : ''}`}
              onClick={toggleRecording}
            >
              <Mic />
            </button>
          )}
          
          <button className="icon-button">
            <Settings />
          </button>
        </div>
      </div>
    </header>
  );

  const renderNavigation = () => (
    <nav className="app-navigation">
      <div className="nav-items">
        {navigationItems.map((item) => (
          <button
            key={item.key}
            className={`nav-item ${activeTab === item.key ? 'active' : ''} ${item.premium && !isPremium ? 'locked' : ''}`}
            onClick={() => {
              if (item.premium && !isPremium) {
                showNotification('Upgrade to Premium to unlock Voice features!', 'warning');
                return;
              }
              setActiveTab(item.key);
              setView(item.key);
            }}
          >
            <div className={`nav-icon gradient-${item.gradient}`}>
              <item.icon />
              {item.premium && !isPremium && (
                <div className="lock-overlay">
                  <Crown size={12} />
                </div>
              )}
            </div>
            <span className="nav-label">{item.label}</span>
            {item.key === 'rewards' && userStats.achievements > 0 && (
              <div className="badge">{userStats.achievements}</div>
            )}
          </button>
        ))}
      </div>
    </nav>
  );

  const renderContent = () => {
    switch (view) {
      case 'dashboard':
        return renderDashboard();
      case 'memories':
        return <MemoryCategories userId={userId} memories={memories} />;
      case 'chat':
        return renderChat();
      case 'voice':
        return renderVoiceStudio();
      case 'rewards':
        return <EnhancedRewardsTab userId={userId} theme={theme} />;
      default:
        return renderDashboard();
    }
  };

  const renderDashboard = () => (
    <div className="dashboard-content">
      <div className="welcome-section">
        <div className="welcome-card neuro-glass">
          <div className="welcome-content">
            <h1 className="neuro-heading">Welcome back!</h1>
            <p className="neuro-text">Your personal memory guardian is ready.</p>
            <div className="quick-stats">
              <div className="quick-stat">
                <Brain className="stat-icon" />
                <div className="stat-info">
                  <AnimatedCounter value={memories.length} />
                  <span>Memories</span>
                </div>
              </div>
              <div className="quick-stat">
                <Target className="stat-icon" />
                <div className="stat-info">
                  <AnimatedCounter value={userStats.streak} />
                  <span>Day Streak</span>
                </div>
              </div>
              <div className="quick-stat">
                <Award className="stat-icon" />
                <div className="stat-info">
                  <AnimatedCounter value={userStats.achievements} />
                  <span>Achievements</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="dashboard-grid">
        <div className="dashboard-card engagement-card" onClick={() => setView('memories')}>
          <div className="card-header">
            <Brain className="card-icon" />
            <h3>Quick Memory</h3>
          </div>
          <p>Store a new memory instantly</p>
          <div className="card-action">
            <Plus className="action-icon" />
          </div>
        </div>
        
        <div className="dashboard-card engagement-card" onClick={() => setView('chat')}>
          <div className="card-header">
            <MessageCircle className="card-icon" />
            <h3>Ask Memo</h3>
          </div>
          <p>Chat with your AI memory assistant</p>
          <div className="card-action">
            <Send className="action-icon" />
          </div>
        </div>
        
        <div className="dashboard-card engagement-card" onClick={() => setView('voice')}>
          <div className="card-header">
            <Volume2 className="card-icon" />
            <h3>Voice Studio</h3>
            {!isPremium && <Crown className="premium-icon" />}
          </div>
          <p>Create your personal voice avatar</p>
          <div className="card-action">
            <Mic className="action-icon" />
          </div>
        </div>
        
        <div className="dashboard-card engagement-card" onClick={() => setView('rewards')}>
          <div className="card-header">
            <Trophy className="card-icon" />
            <h3>Achievements</h3>
          </div>
          <p>Check your progress and rewards</p>
          <div className="card-action">
            <Star className="action-icon" />
          </div>
        </div>
      </div>
      
      <div className="recent-section">
        <h3 className="section-title neuro-heading">Recent Activity</h3>
        <div className="activity-list">
          {activities.slice(0, 5).map((activity, index) => (
            <div key={index} className="activity-item neuro-glass">
              <div className="activity-icon">
                {activity.type === 'memory' ? <Brain /> : <MessageCircle />}
              </div>
              <div className="activity-content">
                <p className="activity-text">{activity.description}</p>
                <span className="activity-time">{activity.timestamp}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderVoiceStudio = () => (
    <div className="voice-studio">
      <div className="voice-header neuro-glass">
        <h2 className="neuro-heading">Voice Studio</h2>
        <p className="neuro-text">Create your personalized voice avatar</p>
        {!isPremium && (
          <div className="premium-banner">
            <Crown />
            <span>Upgrade to Premium to unlock voice features</span>
            <button className="dopamine-button">Upgrade Now</button>
          </div>
        )}
      </div>
      
      <div className="voice-progress neuro-glass">
        <h3>Voice Collection Progress</h3>
        <div className="progress-bar neuro-progress">
          <div 
            className="progress-fill neuro-progress-fill"
            style={{ width: '65%' }}
          />
        </div>
        <p>65% complete - 2 more minutes needed</p>
      </div>
      
      <div className="recording-controls">
        <button 
          className={`record-btn ${isRecording ? 'recording' : ''}`}
          onClick={toggleRecording}
          disabled={!isPremium}
        >
          <Mic />
          <span>{isRecording ? 'Stop Recording' : 'Start Recording'}</span>
        </button>
      </div>
    </div>
  );

  const renderChat = () => (
    <div className="chat-interface">
      <div className="chat-header neuro-glass">
        <div className="chat-avatar">
          <Brain />
        </div>
        <div className="chat-info">
          <h3>Memo</h3>
          <span className="status-indicator">Your Memory Assistant</span>
        </div>
      </div>
      
      <div className="chat-messages" ref={scrollContainerRef}>
        <div className="message ai-message neuro-glass">
          <div className="message-content">
            <p>Hello! I'm Memo, your personal memory guardian. How can I help you today?</p>
          </div>
          <span className="message-time">Now</span>
        </div>
      </div>
      
      <div className="chat-input neuro-glass">
        <input
          type="text"
          placeholder="Ask me about your memories..."
          value={messageInput}
          onChange={(e) => setMessageInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
        />
        <button 
          className="send-button dopamine-button"
          onClick={handleSendMessage}
          disabled={sendingMessage || !messageInput.trim()}
        >
          {sendingMessage ? <Loader className="spinning" /> : <Send />}
        </button>
      </div>
    </div>
  );

  const handleSendMessage = async () => {
    if (!messageInput.trim() || sendingMessage) return;
    
    const message = messageInput.trim();
    setMessageInput('');
    setSendingMessage(true);
    
    try {
      // Add user message to chat
      // Implementation would add to chat messages
      
      // Send to Claude AI
      const response = await claudeService.sendMessage(message, userId);
      
      // Add AI response to chat
      // Implementation would add AI response
      
    } catch (error) {
      console.error('Failed to send message:', error);
      showNotification('Failed to send message', 'error');
    } finally {
      setSendingMessage(false);
    }
  };

  // Notification component
  const renderNotifications = () => (
    <div className="notifications-container">
      {showNotifications.map((notification) => (
        <div
          key={notification.id}
          className={`notification neuro-notification ${notification.type}`}
        >
          {notification.type === 'achievement' ? (
            <div className="achievement-content">
              <Trophy className="achievement-icon" />
              <div>
                <h4>Achievement Unlocked!</h4>
                <p>{notification.achievement.name}</p>
              </div>
            </div>
          ) : (
            <p>{notification.message}</p>
          )}
          <button
            className="close-notification"
            onClick={() => setShowNotifications(prev => 
              prev.filter(n => n.id !== notification.id)
            )}
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );

  // Animated Counter component
  const AnimatedCounter = ({ value, duration = 1000 }) => {
    const [displayValue, setDisplayValue] = useState(value);
    const [isAnimating, setIsAnimating] = useState(false);
    
    useEffect(() => {
      if (displayValue !== value) {
        setIsAnimating(true);
        
        const start = displayValue;
        const end = value;
        const startTime = Date.now();
        
        const animate = () => {
          const elapsed = Date.now() - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
          
          const current = Math.floor(start + (end - start) * eased);
          setDisplayValue(current);
          
          if (progress < 1) {
            requestAnimationFrame(animate);
          } else {
            setIsAnimating(false);
          }
        };
        
        requestAnimationFrame(animate);
      }
    }, [value, duration, displayValue]);
    
    return (
      <span className={`animated-counter ${isAnimating ? 'animating' : ''}`}>
        {displayValue.toLocaleString()}
      </span>
    );
  };

  // Loading screen
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-content">
          <div className="loading-logo">
            <Brain className="loading-icon" />
          </div>
          <div className="loading-text neuro-heading">MemoApp</div>
          <div className="loading-bar neuro-progress">
            <div className="loading-fill neuro-progress-fill" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`enhanced-memory-app ${theme}`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {showConfetti && <div className="confetti-container" />}
      
      {renderHeader()}
      {renderNavigation()}
      
      <main className="app-content" ref={scrollContainerRef}>
        {isPullRefreshing && (
          <div className="pull-refresh-indicator">
            <RefreshCw className="spinning" />
            <span>Refreshing...</span>
          </div>
        )}
        
        {renderContent()}
      </main>
      
      {renderNotifications()}
      
      {isMobile && <BottomNav activeTab={activeTab} setActiveTab={setActiveTab} />}
    </div>
  );
};

export default EnhancedMemoryApp;