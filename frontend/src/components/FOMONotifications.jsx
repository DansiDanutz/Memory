import React, { useState, useEffect, useRef } from 'react';
import {
  AlertCircle,
  Zap,
  TrendingUp,
  Users,
  Gift,
  Clock,
  X,
  ChevronRight,
  Flame,
  Bell,
  Star,
  Trophy,
  Target,
  Shield
} from 'lucide-react';
import CountdownTimer from './CountdownTimer';
import './FOMONotifications.css';

const FOMONotifications = ({ userId, fomoService, wsService, onActionClick }) => {
  const [alerts, setAlerts] = useState([]);
  const [dismissedAlerts, setDismissedAlerts] = useState(new Set());
  const [flashSale, setFlashSale] = useState(null);
  const [showFlashModal, setShowFlashModal] = useState(false);
  const notificationQueue = useRef([]);
  const displayTimer = useRef(null);

  // Alert type configurations
  const alertConfig = {
    expiring_reward: {
      icon: Clock,
      bgColor: '#ff6b6b',
      sound: 'urgent',
      priority: 4
    },
    flash_sale: {
      icon: Zap,
      bgColor: '#ffd93d',
      sound: 'exciting',
      priority: 5,
      fullScreen: true
    },
    limited_slots: {
      icon: Users,
      bgColor: '#ff9800',
      sound: 'warning',
      priority: 3
    },
    friend_activity: {
      icon: Users,
      bgColor: '#4caf50',
      sound: 'social',
      priority: 1
    },
    last_chance: {
      icon: AlertCircle,
      bgColor: '#f44336',
      sound: 'critical',
      priority: 5
    },
    streak_risk: {
      icon: Flame,
      bgColor: '#ff5722',
      sound: 'urgent',
      priority: 4
    },
    exclusive_offer: {
      icon: Star,
      bgColor: '#9c27b0',
      sound: 'special',
      priority: 3
    },
    competition_update: {
      icon: TrendingUp,
      bgColor: '#2196f3',
      sound: 'update',
      priority: 2
    },
    quest_expiring: {
      icon: Target,
      bgColor: '#ff9800',
      sound: 'warning',
      priority: 4
    },
    milestone_close: {
      icon: Trophy,
      bgColor: '#4caf50',
      sound: 'progress',
      priority: 2
    }
  };

  useEffect(() => {
    loadAlerts();
    checkFlashSale();

    // Set up WebSocket listeners
    if (wsService) {
      wsService.on('fomo_alert', handleNewAlert);
      wsService.on('flash_sale_started', handleFlashSaleStarted);
      wsService.on('flash_sale_ended', handleFlashSaleEnded);
    }

    // Check for expiring items periodically
    const expiryCheckInterval = setInterval(checkExpiringItems, 60000); // Every minute

    return () => {
      clearInterval(expiryCheckInterval);
      if (displayTimer.current) {
        clearTimeout(displayTimer.current);
      }
      if (wsService) {
        wsService.off('fomo_alert', handleNewAlert);
        wsService.off('flash_sale_started', handleFlashSaleStarted);
        wsService.off('flash_sale_ended', handleFlashSaleEnded);
      }
    };
  }, [userId]);

  const loadAlerts = async () => {
    try {
      const activeAlerts = await fomoService.getActiveAlerts(userId);
      const sortedAlerts = sortAlerts(activeAlerts);
      setAlerts(sortedAlerts);
      
      // Process high priority alerts
      const highPriorityAlerts = sortedAlerts.filter(
        alert => alertConfig[alert.type]?.priority >= 4
      );
      
      if (highPriorityAlerts.length > 0) {
        processNotificationQueue(highPriorityAlerts);
      }
    } catch (error) {
      console.error('Error loading FOMO alerts:', error);
    }
  };

  const checkFlashSale = async () => {
    try {
      const saleStatus = await fomoService.getFlashSaleStatus(userId);
      if (saleStatus && saleStatus.active) {
        setFlashSale(saleStatus.sale);
        if (!dismissedAlerts.has(`flash_${saleStatus.sale.id}`)) {
          setShowFlashModal(true);
        }
      }
    } catch (error) {
      console.error('Error checking flash sale:', error);
    }
  };

  const checkExpiringItems = async () => {
    try {
      const expiringAlerts = await fomoService.checkExpiringRewards(userId);
      if (expiringAlerts && expiringAlerts.length > 0) {
        expiringAlerts.forEach(alert => handleNewAlert(alert));
      }
    } catch (error) {
      console.error('Error checking expiring items:', error);
    }
  };

  const sortAlerts = (alertList) => {
    return alertList.sort((a, b) => {
      const aPriority = alertConfig[a.type]?.priority || 0;
      const bPriority = alertConfig[b.type]?.priority || 0;
      
      if (aPriority !== bPriority) {
        return bPriority - aPriority;
      }
      
      // Sort by expiry time if same priority
      return new Date(a.expires_at) - new Date(b.expires_at);
    });
  };

  const handleNewAlert = (alert) => {
    if (dismissedAlerts.has(alert.id)) return;
    
    const config = alertConfig[alert.type];
    
    // Add to alerts list
    setAlerts(prev => {
      const filtered = prev.filter(a => a.id !== alert.id);
      return sortAlerts([alert, ...filtered]);
    });
    
    // Handle full-screen alerts
    if (config?.fullScreen) {
      if (alert.type === 'flash_sale') {
        setFlashSale(alert.metadata);
        setShowFlashModal(true);
      }
    } else {
      // Queue for toast notification
      notificationQueue.current.push(alert);
      processNotificationQueue();
    }
    
    // Play sound if enabled
    if (config?.sound) {
      playNotificationSound(config.sound);
    }
  };

  const handleFlashSaleStarted = (saleData) => {
    setFlashSale(saleData);
    setShowFlashModal(true);
    playNotificationSound('exciting');
  };

  const handleFlashSaleEnded = () => {
    setFlashSale(null);
    setShowFlashModal(false);
  };

  const processNotificationQueue = (immediateAlerts = null) => {
    const alertsToProcess = immediateAlerts || notificationQueue.current;
    
    if (alertsToProcess.length === 0) return;
    
    const alert = alertsToProcess.shift();
    showToastNotification(alert);
    
    // Process next after delay
    displayTimer.current = setTimeout(() => {
      processNotificationQueue(alertsToProcess);
    }, 4000);
  };

  const showToastNotification = (alert) => {
    // This would trigger a toast notification component
    // For now, just log it
    console.log('Showing toast notification:', alert);
  };

  const playNotificationSound = (soundType) => {
    // Implementation would play actual sounds
    console.log(`Playing ${soundType} sound`);
  };

  const handleDismissAlert = async (alertId) => {
    try {
      await fomoService.dismissAlert(userId, alertId);
      setDismissedAlerts(prev => new Set([...prev, alertId]));
      setAlerts(prev => prev.filter(a => a.id !== alertId));
    } catch (error) {
      console.error('Error dismissing alert:', error);
    }
  };

  const handleAlertAction = (alert) => {
    if (onActionClick) {
      onActionClick(alert);
    }
    handleDismissAlert(alert.id);
  };

  const renderAlertCard = (alert) => {
    const config = alertConfig[alert.type] || {};
    const Icon = config.icon || Bell;
    
    return (
      <div 
        key={alert.id}
        className={`fomo-alert-card ${alert.priority} ${alert.type}`}
        style={{ '--alert-color': config.bgColor }}
      >
        <div className="alert-icon-wrapper">
          <Icon className="alert-icon" />
        </div>
        
        <div className="alert-content">
          <h4 className="alert-title">{alert.title}</h4>
          <p className="alert-message">{alert.message}</p>
          
          {alert.expires_at && (
            <div className="alert-timer">
              <CountdownTimer
                endTime={alert.expires_at}
                format="minimal"
                urgent={alert.priority === 'critical' || alert.priority === 'high'}
                compact
              />
            </div>
          )}
        </div>
        
        <div className="alert-actions">
          {alert.action_text && (
            <button 
              className="alert-action-btn primary"
              onClick={() => handleAlertAction(alert)}
            >
              {alert.action_text}
              <ChevronRight size={16} />
            </button>
          )}
          
          <button 
            className="alert-dismiss-btn"
            onClick={() => handleDismissAlert(alert.id)}
            aria-label="Dismiss"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    );
  };

  const renderFlashSaleModal = () => {
    if (!flashSale || !showFlashModal) return null;
    
    return (
      <div className="flash-sale-modal-overlay">
        <div className="flash-sale-modal">
          <div className="flash-sale-header">
            <div className="flash-animation">
              <Zap className="flash-icon" />
            </div>
            <h2>⚡ FLASH SALE ACTIVE! ⚡</h2>
          </div>
          
          <div className="flash-sale-content">
            <h3>{flashSale.name}</h3>
            <div className="sale-details">
              <div className="bonus-display">
                <span className="bonus-value">
                  {flashSale.bonus_type === 'xp_multiplier' && `${flashSale.bonus_value}x XP`}
                  {flashSale.bonus_type === 'points_multiplier' && `${flashSale.bonus_value}x Points`}
                  {flashSale.bonus_type === 'voice_discount' && `${(1 - flashSale.bonus_value) * 100}% OFF`}
                </span>
              </div>
              
              <div className="sale-timer">
                <p>Ends in:</p>
                <CountdownTimer
                  endTime={flashSale.expires_at}
                  format="clock"
                  urgent={true}
                  colorTransition={true}
                  onExpire={() => setShowFlashModal(false)}
                />
              </div>
              
              <p className="urgency-text">
                This bonus won't come back! Act fast to maximize your rewards!
              </p>
            </div>
          </div>
          
          <div className="flash-sale-actions">
            <button 
              className="flash-action-btn primary"
              onClick={() => {
                setShowFlashModal(false);
                if (onActionClick) {
                  onActionClick({ type: 'flash_sale', data: flashSale });
                }
              }}
            >
              Start Earning Now!
              <Flame className="action-icon" />
            </button>
            
            <button 
              className="flash-action-btn secondary"
              onClick={() => {
                setShowFlashModal(false);
                setDismissedAlerts(prev => new Set([...prev, `flash_${flashSale.id}`]));
              }}
            >
              Maybe Later
            </button>
          </div>
        </div>
      </div>
    );
  };

  const renderNotificationBadge = () => {
    const urgentCount = alerts.filter(a => 
      !dismissedAlerts.has(a.id) && 
      alertConfig[a.type]?.priority >= 4
    ).length;
    
    if (urgentCount === 0) return null;
    
    return (
      <div className="fomo-notification-badge">
        <Bell className="badge-icon" />
        <span className="badge-count">{urgentCount}</span>
      </div>
    );
  };

  return (
    <div className="fomo-notifications">
      {renderNotificationBadge()}
      
      <div className="fomo-alerts-container">
        {alerts.filter(a => !dismissedAlerts.has(a.id)).map(alert => 
          renderAlertCard(alert)
        )}
      </div>
      
      {renderFlashSaleModal()}
      
      {/* Floating action button for urgent actions */}
      {alerts.some(a => alertConfig[a.type]?.priority >= 4 && !dismissedAlerts.has(a.id)) && (
        <button 
          className="fomo-fab pulse"
          onClick={() => {
            const urgentAlert = alerts.find(a => 
              alertConfig[a.type]?.priority >= 4 && !dismissedAlerts.has(a.id)
            );
            if (urgentAlert) {
              handleAlertAction(urgentAlert);
            }
          }}
        >
          <Flame className="fab-icon" />
          <span>Urgent!</span>
        </button>
      )}
    </div>
  );
};

export default FOMONotifications;