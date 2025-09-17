/**
 * FOMO Service
 * Handles all FOMO-related API interactions and alert management
 */

import api from './apiService';

class FOMOService {
  constructor() {
    this.baseURL = '/gamification';
    this.activeAlerts = new Map();
    this.alertCallbacks = new Set();
    this.flashSaleActive = false;
    this.pollingInterval = null;
  }

  /**
   * Get active FOMO alerts for a user
   */
  async getActiveAlerts(userId) {
    try {
      const response = await api.get(`${this.baseURL}/fomo/alerts`, {
        params: { user_id: userId }
      });
      
      const alerts = response?.alerts || [];
      
      // Update internal cache
      alerts.forEach(alert => {
        this.activeAlerts.set(alert.id, alert);
      });
      
      return alerts;
    } catch (error) {
      console.error('Error fetching FOMO alerts:', error);
      return [];
    }
  }

  /**
   * Create a new FOMO alert
   */
  async createFOMOAlert(alertData) {
    try {
      const response = await api.post(`${this.baseURL}/fomo/alerts`, alertData);
      const alert = response?.alert;
      
      if (alert) {
        this.activeAlerts.set(alert.id, alert);
        this.notifyCallbacks(alert);
      }
      
      return alert;
    } catch (error) {
      console.error('Error creating FOMO alert:', error);
      throw error;
    }
  }

  /**
   * Dismiss a FOMO alert
   */
  async dismissAlert(userId, alertId) {
    try {
      await api.post(`${this.baseURL}/fomo/alerts/${alertId}/dismiss`, null, {
        params: { user_id: userId }
      });
      
      this.activeAlerts.delete(alertId);
      return true;
    } catch (error) {
      console.error('Error dismissing alert:', error);
      return false;
    }
  }

  /**
   * Get flash sale status
   */
  async getFlashSaleStatus(userId) {
    try {
      const response = await api.get(`${this.baseURL}/fomo/flash-sale`, {
        params: { user_id: userId }
      });
      
      this.flashSaleActive = response?.active || false;
      return response;
    } catch (error) {
      console.error('Error checking flash sale:', error);
      return { active: false };
    }
  }

  /**
   * Trigger a flash sale
   */
  async triggerFlashSale(saleData) {
    try {
      const response = await api.post(`${this.baseURL}/fomo/flash-sale`, saleData);
      
      if (response?.sale) {
        this.flashSaleActive = true;
        this.notifyFlashSale(response.sale);
      }
      
      return response?.sale;
    } catch (error) {
      console.error('Error triggering flash sale:', error);
      throw error;
    }
  }

  /**
   * Check for expiring rewards
   */
  async checkExpiringRewards(userId, timeWindow = 7200) {
    try {
      const response = await api.get(`${this.baseURL}/fomo/expiring-rewards`, {
        params: { 
          user_id: userId,
          time_window: timeWindow
        }
      });
      
      const expiringItems = response?.expiring || [];
      
      // Create alerts for expiring items
      expiringItems.forEach(item => {
        this.createExpiringAlert(userId, item);
      });
      
      return expiringItems;
    } catch (error) {
      console.error('Error checking expiring rewards:', error);
      return [];
    }
  }

  /**
   * Get friend activity alerts
   */
  async getFriendActivity(userId) {
    try {
      const response = await api.get(`${this.baseURL}/fomo/friend-activity`, {
        params: { user_id: userId }
      });
      
      const activities = response?.activities || [];
      
      // Create social proof alerts
      if (activities.length > 0) {
        this.createSocialProofAlert(userId, activities);
      }
      
      return activities;
    } catch (error) {
      console.error('Error fetching friend activity:', error);
      return [];
    }
  }

  /**
   * Check streak risk
   */
  async checkStreakRisk(userId) {
    try {
      const response = await api.get(`${this.baseURL}/fomo/streak-risk`, {
        params: { user_id: userId }
      });
      
      if (response?.at_risk) {
        this.createStreakRiskAlert(userId, response);
      }
      
      return response;
    } catch (error) {
      console.error('Error checking streak risk:', error);
      return { at_risk: false };
    }
  }

  /**
   * Create expiring alert
   */
  createExpiringAlert(userId, item) {
    const alert = {
      user_id: userId,
      type: 'expiring_reward',
      priority: 'high',
      title: 'Reward Expiring Soon!',
      message: `Your ${item.name} expires in ${this.formatTimeRemaining(item.expires_at)}`,
      expires_at: item.expires_at,
      action_text: 'Claim Now',
      action_url: `/rewards/${item.id}`,
      metadata: item
    };
    
    return this.createFOMOAlert(alert);
  }

  /**
   * Create social proof alert
   */
  createSocialProofAlert(userId, activities) {
    const recentCount = activities.filter(a => 
      new Date(a.timestamp) > new Date(Date.now() - 3600000)
    ).length;
    
    if (recentCount > 0) {
      const alert = {
        user_id: userId,
        type: 'friend_activity',
        priority: 'medium',
        title: 'Friends Are Active!',
        message: `${recentCount} friends earned rewards in the last hour`,
        expires_at: new Date(Date.now() + 600000), // 10 minutes
        action_text: 'Join Them',
        action_url: '/quests',
        metadata: { activities }
      };
      
      return this.createFOMOAlert(alert);
    }
  }

  /**
   * Create streak risk alert
   */
  createStreakRiskAlert(userId, streakInfo) {
    const alert = {
      user_id: userId,
      type: 'streak_risk',
      priority: 'critical',
      title: `${streakInfo.current_streak} Day Streak at Risk!`,
      message: `Complete a quest in the next ${streakInfo.hours_remaining} hours to maintain your streak`,
      expires_at: streakInfo.deadline,
      action_text: 'Save Streak',
      action_url: '/quests/daily',
      metadata: streakInfo
    };
    
    return this.createFOMOAlert(alert);
  }

  /**
   * Format time remaining
   */
  formatTimeRemaining(expiresAt) {
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diff = expiry - now;
    
    if (diff <= 0) return 'expired';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days} day${days > 1 ? 's' : ''}`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes} minutes`;
    }
  }

  /**
   * Register callback for new alerts
   */
  onNewAlert(callback) {
    this.alertCallbacks.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.alertCallbacks.delete(callback);
    };
  }

  /**
   * Notify all callbacks of new alert
   */
  notifyCallbacks(alert) {
    this.alertCallbacks.forEach(callback => {
      try {
        callback(alert);
      } catch (error) {
        console.error('Error in alert callback:', error);
      }
    });
  }

  /**
   * Notify flash sale to all listeners
   */
  notifyFlashSale(sale) {
    const flashAlert = {
      id: `flash_${sale.id}`,
      type: 'flash_sale',
      priority: 'critical',
      title: 'FLASH SALE!',
      message: sale.description,
      expires_at: sale.expires_at,
      action_text: 'Shop Now',
      metadata: sale
    };
    
    this.notifyCallbacks(flashAlert);
  }

  /**
   * Start polling for alerts
   */
  startPolling(userId, interval = 60000) {
    if (this.pollingInterval) {
      this.stopPolling();
    }
    
    // Initial fetch
    this.getActiveAlerts(userId);
    this.checkExpiringRewards(userId);
    this.checkStreakRisk(userId);
    
    // Set up interval
    this.pollingInterval = setInterval(() => {
      this.getActiveAlerts(userId);
      this.checkExpiringRewards(userId);
      this.checkStreakRisk(userId);
    }, interval);
  }

  /**
   * Stop polling for alerts
   */
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  /**
   * Clear all cached data
   */
  clearCache() {
    this.activeAlerts.clear();
    this.flashSaleActive = false;
  }
}

export default new FOMOService();