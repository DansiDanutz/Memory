/**
 * Quest Service
 * Handles all quest-related API interactions
 */

import api from './apiService';

class QuestService {
  constructor() {
    this.baseURL = '/gamification';
    this.cache = new Map();
    this.cacheTimeout = 30000; // 30 seconds cache
  }

  /**
   * Get all active quests for a user
   */
  async getActiveQuests(userId) {
    try {
      const response = await api.get(`${this.baseURL}/quests/active`, {
        params: { user_id: userId }
      });
      return response;
    } catch (error) {
      console.error('Error fetching active quests:', error);
      return {
        daily: [],
        weekly: [],
        flash: [],
        event: []
      };
    }
  }

  /**
   * Generate daily quests for a user
   */
  async generateDailyQuests(userId) {
    try {
      const response = await api.post(`${this.baseURL}/quests/daily/generate`, null, {
        params: { user_id: userId }
      });
      return response?.quests || [];
    } catch (error) {
      console.error('Error generating daily quests:', error);
      return [];
    }
  }

  /**
   * Generate weekly quests for a user
   */
  async generateWeeklyQuests(userId) {
    try {
      const response = await api.post(`${this.baseURL}/quests/weekly/generate`, null, {
        params: { user_id: userId }
      });
      return response?.quests || [];
    } catch (error) {
      console.error('Error generating weekly quests:', error);
      return [];
    }
  }

  /**
   * Check for flash quests
   */
  async checkFlashQuest(userId) {
    try {
      const response = await api.get(`${this.baseURL}/quests/flash`, {
        params: { user_id: userId }
      });
      return response;
    } catch (error) {
      console.error('Error checking flash quest:', error);
      return { available: false };
    }
  }

  /**
   * Update quest progress
   */
  async updateQuestProgress(userId, actionType, amount = 1) {
    try {
      const response = await api.post(`${this.baseURL}/quests/progress`, {
        user_id: userId,
        action_type: actionType,
        amount: amount
      });
      return response?.completed_quests || [];
    } catch (error) {
      console.error('Error updating quest progress:', error);
      return [];
    }
  }

  /**
   * Claim quest rewards
   */
  async claimQuestRewards(userId, questId) {
    try {
      const response = await api.post(
        `${this.baseURL}/quests/${questId}/claim`,
        null,
        { params: { user_id: userId } }
      );
      return response;
    } catch (error) {
      console.error('Error claiming quest rewards:', error);
      throw error;
    }
  }

  /**
   * Get current events
   */
  async getCurrentEvents() {
    try {
      const cached = this.cache.get('current-events');
      if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
        return cached.data;
      }

      const response = await api.get(`${this.baseURL}/events/current`);
      
      this.cache.set('current-events', {
        data: response,
        timestamp: Date.now()
      });
      
      return response;
    } catch (error) {
      console.error('Error fetching current events:', error);
      return { active_events: [], upcoming_events: [] };
    }
  }

  /**
   * Accept a flash quest
   */
  async acceptFlashQuest(userId, questId) {
    try {
      const response = await api.post(`${this.baseURL}/quests/${questId}/accept`, {
        user_id: userId
      });
      return response;
    } catch (error) {
      console.error('Error accepting flash quest:', error);
      throw error;
    }
  }

  /**
   * Decline a flash quest
   */
  async declineFlashQuest(userId, questId) {
    try {
      const response = await api.post(`${this.baseURL}/quests/${questId}/decline`, {
        user_id: userId
      });
      return response;
    } catch (error) {
      console.error('Error declining flash quest:', error);
      throw error;
    }
  }

  /**
   * Get quest statistics for a user
   */
  async getQuestStats(userId) {
    try {
      const response = await api.get(`${this.baseURL}/quests/stats`, {
        params: { user_id: userId }
      });
      return response;
    } catch (error) {
      console.error('Error fetching quest stats:', error);
      return {
        total_completed: 0,
        daily_streak: 0,
        weekly_progress: 0,
        flash_completed: 0,
        total_xp_earned: 0
      };
    }
  }

  /**
   * Get quest leaderboard
   */
  async getQuestLeaderboard(period = 'weekly', limit = 10) {
    try {
      const response = await api.get(`${this.baseURL}/quests/leaderboard`, {
        params: { period, limit }
      });
      return response?.leaderboard || [];
    } catch (error) {
      console.error('Error fetching quest leaderboard:', error);
      return [];
    }
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
  }
}

export default new QuestService();