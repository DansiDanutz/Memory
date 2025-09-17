import React, { useState, useEffect, useRef } from 'react';
import {
  Bell,
  BellOff,
  X,
  Check,
  AlertTriangle,
  Info,
  Trophy,
  Flame,
  Gift,
  Clock,
  Calendar,
  ChevronRight,
  Settings,
  Volume2,
  VolumeX,
  Sparkles,
  Shield,
  Heart
} from 'lucide-react';
import './Notifications.css';

const Notifications = ({ userId, apiService, wsService, theme = 'dark' }) => {
  // State Management
  const [notifications, setNotifications] = useState([]);
  const [permission, setPermission] = useState('default');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [settings, setSettings] = useState({
    streak_reminders: true,
    reward_alerts: true,
    milestone_celebrations: true,
    fomo_alerts: true,
    daily_digest: false,
    quiet_hours: false,
    quiet_start: '22:00',
    quiet_end: '08:00'
  });
  const [showSettings, setShowSettings] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotificationList, setShowNotificationList] = useState(false);

  // Refs
  const audioRef = useRef({});
  const toastContainerRef = useRef(null);
  const notificationQueue = useRef([]);
  const isProcessingQueue = useRef(false);

  // Notification types configuration
  const NOTIFICATION_TYPES = {
    streak_reminder: {
      icon: Flame,
      color: '#ef4444',
      sound: 'reminder',
      priority: 'high',
      duration: 10000
    },
    streak_milestone: {
      icon: Trophy,
      color: '#f59e0b',
      sound: 'achievement',
      priority: 'high',
      duration: 8000,
      celebration: true
    },
    reward_earned: {
      icon: Gift,
      color: '#8b5cf6',
      sound: 'reward',
      priority: 'medium',
      duration: 6000
    },
    urgent_streak: {
      icon: AlertTriangle,
      color: '#dc2626',
      sound: 'urgent',
      priority: 'urgent',
      duration: 15000,
      pulse: true
    },
    freeze_available: {
      icon: Shield,
      color: '#3b82f6',
      sound: 'info',
      priority: 'low',
      duration: 5000
    },
    daily_checkin: {
      icon: Calendar,
      color: '#10b981',
      sound: 'success',
      priority: 'medium',
      duration: 5000
    }
  };

  useEffect(() => {
    initializeNotifications();
    initializeAudio();
    checkPermission();

    // Set up WebSocket listeners
    if (wsService) {
      wsService.on('notification', handleIncomingNotification);
      wsService.on('streak_alert', handleStreakAlert);
      wsService.on('reward_notification', handleRewardNotification);
    }

    // Check for queued notifications every second
    const queueProcessor = setInterval(processNotificationQueue, 1000);

    return () => {
      clearInterval(queueProcessor);
      if (wsService) {
        wsService.off('notification', handleIncomingNotification);
        wsService.off('streak_alert', handleStreakAlert);
        wsService.off('reward_notification', handleRewardNotification);
      }
    };
  }, []);

  const initializeNotifications = async () => {
    // Load saved notification settings
    const savedSettings = localStorage.getItem(`notification_settings_${userId}`);
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }

    // Load notification history
    const history = localStorage.getItem(`notification_history_${userId}`);
    if (history) {
      const parsed = JSON.parse(history);
      setNotifications(parsed.slice(0, 50)); // Keep last 50
      setUnreadCount(parsed.filter(n => !n.read).length);
    }
  };

  const initializeAudio = () => {
    // Initialize notification sounds
    audioRef.current = {
      reminder: new Audio('/sounds/notification-reminder.mp3'),
      achievement: new Audio('/sounds/notification-achievement.mp3'),
      reward: new Audio('/sounds/notification-reward.mp3'),
      urgent: new Audio('/sounds/notification-urgent.mp3'),
      info: new Audio('/sounds/notification-info.mp3'),
      success: new Audio('/sounds/notification-success.mp3')
    };

    // Preload all sounds
    Object.values(audioRef.current).forEach(audio => {
      audio.preload = 'auto';
      audio.volume = 0.5;
    });
  };

  const checkPermission = async () => {
    if ('Notification' in window) {
      const perm = Notification.permission;
      setPermission(perm);
      
      if (perm === 'default') {
        // Show permission request prompt after 30 seconds
        setTimeout(() => {
          showPermissionPrompt();
        }, 30000);
      }
    }
  };

  const requestPermission = async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      setPermission(permission);
      
      if (permission === 'granted') {
        showToast({
          type: 'success',
          title: 'Notifications Enabled',
          message: 'You\'ll receive streak reminders and reward alerts!'
        });
      }
    }
  };

  const showPermissionPrompt = () => {
    if (permission !== 'default') return;

    const prompt = {
      id: 'permission-prompt',
      type: 'info',
      title: 'Enable Notifications',
      message: 'Get reminders to maintain your streak and celebrate rewards!',
      actions: [
        { label: 'Enable', action: requestPermission },
        { label: 'Not Now', action: () => {} }
      ],
      persistent: true
    };

    showToast(prompt);
  };

  const handleIncomingNotification = (data) => {
    // Check quiet hours
    if (isQuietHours()) return;

    // Check notification settings
    if (!shouldShowNotification(data.type)) return;

    // Create notification
    createNotification(data);
  };

  const handleStreakAlert = (data) => {
    if (!settings.streak_reminders) return;

    const notification = {
      type: data.urgent ? 'urgent_streak' : 'streak_reminder',
      title: data.title || `Streak Alert!`,
      message: data.message,
      data: data
    };

    createNotification(notification);
  };

  const handleRewardNotification = (data) => {
    if (!settings.reward_alerts) return;

    const notification = {
      type: 'reward_earned',
      title: 'Reward Earned!',
      message: `You earned: ${data.reward_name}`,
      data: data
    };

    createNotification(notification);
  };

  const createNotification = (data) => {
    const notification = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString(),
      read: false,
      ...data
    };

    // Add to notification history
    setNotifications(prev => {
      const updated = [notification, ...prev].slice(0, 100);
      localStorage.setItem(`notification_history_${userId}`, JSON.stringify(updated));
      return updated;
    });

    setUnreadCount(prev => prev + 1);

    // Add to queue for display
    notificationQueue.current.push(notification);
  };

  const processNotificationQueue = () => {
    if (isProcessingQueue.current || notificationQueue.current.length === 0) return;
    
    isProcessingQueue.current = true;
    const notification = notificationQueue.current.shift();
    
    // Show toast
    showToast(notification);

    // Show browser notification if permitted
    if (permission === 'granted' && document.hidden) {
      showBrowserNotification(notification);
    }

    setTimeout(() => {
      isProcessingQueue.current = false;
    }, 1000);
  };

  const showToast = (notification) => {
    const config = NOTIFICATION_TYPES[notification.type] || {
      icon: Info,
      color: '#6b7280',
      sound: 'info',
      duration: 5000
    };

    // Play sound
    if (soundEnabled && config.sound) {
      playSound(config.sound);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `notification-toast ${notification.type} ${theme}`;
    toast.style.setProperty('--notification-color', config.color);

    // Add pulse effect for urgent notifications
    if (config.pulse) {
      toast.classList.add('pulse');
    }

    // Create toast content
    const Icon = config.icon;
    toast.innerHTML = `
      <div class="toast-icon">
        ${Icon ? `<svg>...</svg>` : ''}
      </div>
      <div class="toast-content">
        <div class="toast-title">${notification.title}</div>
        <div class="toast-message">${notification.message}</div>
        ${notification.actions ? `
          <div class="toast-actions">
            ${notification.actions.map(action => 
              `<button class="toast-action" data-action="${action.label}">${action.label}</button>`
            ).join('')}
          </div>
        ` : ''}
      </div>
      <button class="toast-close">×</button>
    `;

    // Add event listeners
    toast.querySelector('.toast-close')?.addEventListener('click', () => {
      removeToast(toast);
    });

    notification.actions?.forEach(action => {
      toast.querySelector(`[data-action="${action.label}"]`)?.addEventListener('click', () => {
        action.action();
        removeToast(toast);
      });
    });

    // Add to container
    if (!toastContainerRef.current) {
      toastContainerRef.current = document.createElement('div');
      toastContainerRef.current.className = 'notification-toast-container';
      document.body.appendChild(toastContainerRef.current);
    }

    toastContainerRef.current.appendChild(toast);

    // Add celebration effect for milestones
    if (config.celebration) {
      addCelebrationEffect(toast);
    }

    // Auto remove after duration
    if (!notification.persistent) {
      setTimeout(() => {
        removeToast(toast);
      }, config.duration || 5000);
    }

    // Animate in
    requestAnimationFrame(() => {
      toast.classList.add('show');
    });
  };

  const removeToast = (toast) => {
    toast.classList.add('hide');
    setTimeout(() => {
      toast.remove();
    }, 300);
  };

  const showBrowserNotification = (notification) => {
    const config = NOTIFICATION_TYPES[notification.type] || {};
    
    new Notification(notification.title, {
      body: notification.message,
      icon: '/icons/notification-icon.png',
      badge: '/icons/badge-icon.png',
      tag: notification.id,
      requireInteraction: config.priority === 'urgent',
      silent: !soundEnabled
    });
  };

  const playSound = (soundName) => {
    if (!soundEnabled) return;

    try {
      const audio = audioRef.current[soundName];
      if (audio) {
        audio.currentTime = 0;
        audio.play().catch(e => console.log('Audio play failed:', e));
      }
    } catch (error) {
      console.error('Sound playback error:', error);
    }
  };

  const addCelebrationEffect = (toast) => {
    const confetti = document.createElement('div');
    confetti.className = 'celebration-confetti';
    
    // Create confetti particles
    for (let i = 0; i < 30; i++) {
      const particle = document.createElement('span');
      particle.style.setProperty('--x', `${Math.random() * 200 - 100}px`);
      particle.style.setProperty('--delay', `${Math.random() * 2}s`);
      confetti.appendChild(particle);
    }
    
    toast.appendChild(confetti);
    
    setTimeout(() => {
      confetti.remove();
    }, 3000);
  };

  const shouldShowNotification = (type) => {
    switch (type) {
      case 'streak_reminder':
      case 'urgent_streak':
        return settings.streak_reminders;
      case 'reward_earned':
        return settings.reward_alerts;
      case 'streak_milestone':
        return settings.milestone_celebrations;
      case 'fomo_alert':
        return settings.fomo_alerts;
      default:
        return true;
    }
  };

  const isQuietHours = () => {
    if (!settings.quiet_hours) return false;

    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    
    const [startHour, startMin] = settings.quiet_start.split(':').map(Number);
    const [endHour, endMin] = settings.quiet_end.split(':').map(Number);
    
    const quietStart = startHour * 60 + startMin;
    const quietEnd = endHour * 60 + endMin;

    if (quietStart < quietEnd) {
      return currentTime >= quietStart && currentTime < quietEnd;
    } else {
      return currentTime >= quietStart || currentTime < quietEnd;
    }
  };

  const markAsRead = (notificationId) => {
    setNotifications(prev => {
      const updated = prev.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      );
      localStorage.setItem(`notification_history_${userId}`, JSON.stringify(updated));
      return updated;
    });
    setUnreadCount(prev => Math.max(0, prev - 1));
  };

  const markAllAsRead = () => {
    setNotifications(prev => {
      const updated = prev.map(n => ({ ...n, read: true }));
      localStorage.setItem(`notification_history_${userId}`, JSON.stringify(updated));
      return updated;
    });
    setUnreadCount(0);
  };

  const clearNotifications = () => {
    setNotifications([]);
    setUnreadCount(0);
    localStorage.removeItem(`notification_history_${userId}`);
  };

  const updateSettings = (key, value) => {
    setSettings(prev => {
      const updated = { ...prev, [key]: value };
      localStorage.setItem(`notification_settings_${userId}`, JSON.stringify(updated));
      return updated;
    });
  };

  const testNotification = (type) => {
    const testData = {
      streak_reminder: {
        type: 'streak_reminder',
        title: '🔥 Keep Your Streak Alive!',
        message: 'Check in now to maintain your 7-day streak!'
      },
      reward_earned: {
        type: 'reward_earned',
        title: '🎁 Epic Reward!',
        message: 'You earned 2 Voice Credits!'
      },
      urgent_streak: {
        type: 'urgent_streak',
        title: '⚠️ Streak Ending Soon!',
        message: 'Only 1 hour left to save your 30-day streak!'
      }
    };

    createNotification(testData[type] || testData.streak_reminder);
  };

  return (
    <div className={`notifications-system theme-${theme}`}>
      {/* Notification Bell Icon */}
      <div className="notification-bell-container">
        <button
          className="notification-bell"
          onClick={() => setShowNotificationList(!showNotificationList)}
        >
          {permission === 'denied' ? <BellOff size={24} /> : <Bell size={24} />}
          {unreadCount > 0 && (
            <span className="notification-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
          )}
        </button>
      </div>

      {/* Notification List Dropdown */}
      {showNotificationList && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <h3>Notifications</h3>
            <div className="notification-actions">
              {unreadCount > 0 && (
                <button onClick={markAllAsRead} className="mark-read-button">
                  <Check size={16} />
                  Mark all read
                </button>
              )}
              <button onClick={() => setShowSettings(!showSettings)} className="settings-button">
                <Settings size={16} />
              </button>
            </div>
          </div>

          {showSettings ? (
            <div className="notification-settings">
              <h4>Notification Settings</h4>
              
              {permission === 'default' && (
                <div className="permission-request">
                  <p>Enable browser notifications to never miss a streak!</p>
                  <button onClick={requestPermission} className="enable-button">
                    Enable Notifications
                  </button>
                </div>
              )}

              <div className="settings-list">
                <label className="setting-item">
                  <input
                    type="checkbox"
                    checked={settings.streak_reminders}
                    onChange={(e) => updateSettings('streak_reminders', e.target.checked)}
                  />
                  <span>Streak Reminders</span>
                </label>

                <label className="setting-item">
                  <input
                    type="checkbox"
                    checked={settings.reward_alerts}
                    onChange={(e) => updateSettings('reward_alerts', e.target.checked)}
                  />
                  <span>Reward Alerts</span>
                </label>

                <label className="setting-item">
                  <input
                    type="checkbox"
                    checked={settings.milestone_celebrations}
                    onChange={(e) => updateSettings('milestone_celebrations', e.target.checked)}
                  />
                  <span>Milestone Celebrations</span>
                </label>

                <label className="setting-item">
                  <input
                    type="checkbox"
                    checked={settings.fomo_alerts}
                    onChange={(e) => updateSettings('fomo_alerts', e.target.checked)}
                  />
                  <span>Urgent Alerts</span>
                </label>

                <label className="setting-item">
                  <input
                    type="checkbox"
                    checked={soundEnabled}
                    onChange={(e) => setSoundEnabled(e.target.checked)}
                  />
                  <span>Sound Effects</span>
                </label>

                <label className="setting-item">
                  <input
                    type="checkbox"
                    checked={settings.quiet_hours}
                    onChange={(e) => updateSettings('quiet_hours', e.target.checked)}
                  />
                  <span>Quiet Hours</span>
                </label>

                {settings.quiet_hours && (
                  <div className="quiet-hours-config">
                    <input
                      type="time"
                      value={settings.quiet_start}
                      onChange={(e) => updateSettings('quiet_start', e.target.value)}
                    />
                    <span>to</span>
                    <input
                      type="time"
                      value={settings.quiet_end}
                      onChange={(e) => updateSettings('quiet_end', e.target.value)}
                    />
                  </div>
                )}
              </div>

              {/* Test Notifications */}
              <div className="test-notifications">
                <h5>Test Notifications</h5>
                <div className="test-buttons">
                  <button onClick={() => testNotification('streak_reminder')}>Streak</button>
                  <button onClick={() => testNotification('reward_earned')}>Reward</button>
                  <button onClick={() => testNotification('urgent_streak')}>Urgent</button>
                </div>
              </div>
            </div>
          ) : (
            <div className="notification-list">
              {notifications.length === 0 ? (
                <div className="empty-state">
                  <Bell size={48} />
                  <p>No notifications yet</p>
                  <span>Your streak updates will appear here</span>
                </div>
              ) : (
                notifications.slice(0, 20).map(notification => {
                  const config = NOTIFICATION_TYPES[notification.type] || {};
                  const Icon = config.icon || Info;
                  
                  return (
                    <div
                      key={notification.id}
                      className={`notification-item ${!notification.read ? 'unread' : ''}`}
                      onClick={() => markAsRead(notification.id)}
                    >
                      <div 
                        className="notification-icon"
                        style={{ color: config.color }}
                      >
                        <Icon size={20} />
                      </div>
                      <div className="notification-content">
                        <div className="notification-title">{notification.title}</div>
                        <div className="notification-message">{notification.message}</div>
                        <div className="notification-time">
                          {new Date(notification.timestamp).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}

              {notifications.length > 0 && (
                <button onClick={clearNotifications} className="clear-button">
                  Clear All
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* FOMO Alert Modal (Example) */}
      <div className="fomo-modal" style={{ display: 'none' }}>
        <div className="fomo-content">
          <AlertTriangle size={48} color="#dc2626" />
          <h2>Your 30-Day Streak is at Risk!</h2>
          <p>You have only 2 hours left to check in</p>
          <div className="fomo-stats">
            <div className="stat">
              <span className="value">30</span>
              <span className="label">Current Streak</span>
            </div>
            <div className="stat">
              <span className="value">450</span>
              <span className="label">Points at Risk</span>
            </div>
            <div className="stat">
              <span className="value">2</span>
              <span className="label">Hours Left</span>
            </div>
          </div>
          <button className="fomo-action">Check In Now</button>
        </div>
      </div>
    </div>
  );
};

export default Notifications;