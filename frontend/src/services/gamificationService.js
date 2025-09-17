/**
 * Gamification Service
 * Handles all API interactions for the rewards and gamification system
 */

import api from './apiService';

class GamificationService {
  constructor() {
    this.baseURL = '/gamification';
    this.cache = new Map();
    this.cacheTimeout = 60000; // 1 minute cache
  }

  /**
   * Get cached data or fetch new data
   */
  async getCachedOrFetch(key, fetchFn) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }
    
    const data = await fetchFn();
    this.cache.set(key, { data, timestamp: Date.now() });
    return data;
  }

  /**
   * Clear cache for a specific key or all cache
   */
  clearCache(key = null) {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Get comprehensive user statistics
   */
  async getUserStats(userPhone) {
    try {
      return await this.getCachedOrFetch(
        `stats-${userPhone}`,
        async () => {
          const response = await api.get(`${this.baseURL}/users/${userPhone}/stats`);
          return response;
        }
      );
    } catch (error) {
      console.error('Error fetching user stats:', error);
      return this.getMockUserStats();
    }
  }

  /**
   * Get leaderboard data
   */
  async getLeaderboard(metric = 'points', period = 'all_time', limit = 10) {
    try {
      const response = await api.get(`${this.baseURL}/leaderboard`, {
        params: { metric, period, limit }
      });
      return response;
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
      return this.getMockLeaderboard();
    }
  }

  /**
   * Get user achievements
   */
  async getAchievements(userPhone) {
    try {
      const response = await api.get(`${this.baseURL}/achievements/${userPhone}`);
      return response;
    } catch (error) {
      console.error('Error fetching achievements:', error);
      return this.getMockAchievements();
    }
  }

  /**
   * Get voice avatars for user
   */
  async getVoiceAvatars(userPhone) {
    try {
      const response = await api.get(`${this.baseURL}/voice-avatars/${userPhone}`);
      return response;
    } catch (error) {
      console.error('Error fetching voice avatars:', error);
      return this.getMockVoiceAvatars();
    }
  }

  /**
   * Create a new invitation
   */
  async createInvitation(senderPhone, recipientPhone = null, customMessage = null) {
    try {
      this.clearCache(`stats-${senderPhone}`);
      const response = await api.post(`${this.baseURL}/invitations/create`, {
        sender_phone: senderPhone,
        recipient_phone: recipientPhone,
        custom_message: customMessage
      });
      return response;
    } catch (error) {
      console.error('Error creating invitation:', error);
      throw error;
    }
  }

  /**
   * Accept an invitation
   */
  async acceptInvitation(code, recipientPhone) {
    try {
      this.clearCache(); // Clear all cache on invitation accept
      const response = await api.post(`${this.baseURL}/invitations/accept`, {
        code: code,
        recipient_phone: recipientPhone
      });
      return response;
    } catch (error) {
      console.error('Error accepting invitation:', error);
      throw error;
    }
  }

  /**
   * Use a streak freeze token
   */
  async useStreakFreeze(userPhone) {
    try {
      this.clearCache(`stats-${userPhone}`);
      const response = await api.post(`${this.baseURL}/streak/freeze`, {
        user_phone: userPhone
      });
      return response;
    } catch (error) {
      console.error('Error using streak freeze:', error);
      throw error;
    }
  }

  /**
   * Create a voice avatar
   */
  async createVoiceAvatar(userPhone, name, description, audioSamples) {
    try {
      this.clearCache(`avatars-${userPhone}`);
      const response = await api.post(`${this.baseURL}/voice-avatars/create`, {
        user_phone: userPhone,
        name: name,
        description: description,
        audio_samples_base64: audioSamples
      });
      return response;
    } catch (error) {
      console.error('Error creating voice avatar:', error);
      throw error;
    }
  }

  /**
   * Check achievement progress
   */
  async checkAchievementProgress(userPhone, achievementId) {
    try {
      const response = await api.get(`${this.baseURL}/achievements/${userPhone}/${achievementId}`);
      return response;
    } catch (error) {
      console.error('Error checking achievement progress:', error);
      return null;
    }
  }

  /**
   * Get subscription status
   */
  async getSubscriptionStatus(userPhone) {
    try {
      const response = await api.get(`${this.baseURL}/subscription/status/${userPhone}`);
      return response;
    } catch (error) {
      console.error('Error fetching subscription status:', error);
      return {
        tier: 'free',
        is_premium: false,
        features: {
          voice_generation: false,
          voice_preview: true,
          voice_collection: true
        }
      };
    }
  }

  /**
   * Get upgrade eligibility and offers
   */
  async getUpgradeEligibility(userPhone) {
    try {
      const response = await api.get(`${this.baseURL}/subscription/upgrade-eligibility/${userPhone}`);
      return response;
    } catch (error) {
      console.error('Error fetching upgrade eligibility:', error);
      return {
        eligible: true,
        current_tier: 'free',
        upgrade_options: [{
          tier: 'premium',
          price: 9.99,
          features: [
            '✨ Unlock Voice Avatar Generation',
            '🎯 5 Custom Voice Avatars',
            '💬 100 Daily Memories'
          ]
        }]
      };
    }
  }

  /**
   * Simulate upgrade to premium (for demo)
   */
  async upgradeSubscription(userPhone, tier = 'premium') {
    try {
      const response = await api.post(`${this.baseURL}/subscription/upgrade`, null, {
        params: { user_phone: userPhone, tier: tier }
      });
      this.clearCache(); // Clear all cache after upgrade
      return response;
    } catch (error) {
      console.error('Error upgrading subscription:', error);
      throw error;
    }
  }

  /**
   * Get voice avatar preview
   */
  async getAvatarPreview(avatarId, userPhone) {
    try {
      const response = await api.get(`${this.baseURL}/voice-avatars/preview/${avatarId}`, {
        params: { user_phone: userPhone }
      });
      return response;
    } catch (error) {
      console.error('Error fetching avatar preview:', error);
      return {
        locked: true,
        preview_message: '🎙️ Your voice avatar is ready!',
        upgrade_prompt: {
          title: '🔓 Unlock Your Voice Avatar',
          message: 'Upgrade now to use your personalized voice',
          cta: 'Unlock Now'
        }
      };
    }
  }

  /**
   * Claim achievement reward
   */
  async claimReward(userPhone, achievementId) {
    try {
      this.clearCache(`stats-${userPhone}`);
      const response = await api.post(`${this.baseURL}/achievements/${userPhone}/${achievementId}/claim`);
      return response;
    } catch (error) {
      console.error('Error claiming reward:', error);
      throw error;
    }
  }

  /**
   * Get daily streak information
   */
  async getStreakInfo(userPhone) {
    try {
      const response = await api.get(`${this.baseURL}/streak/${userPhone}`);
      return response;
    } catch (error) {
      console.error('Error fetching streak info:', error);
      return this.getMockStreakInfo();
    }
  }

  /**
   * Record daily check-in
   */
  async recordCheckIn(userPhone) {
    try {
      this.clearCache(`stats-${userPhone}`);
      const response = await api.post(`${this.baseURL}/checkin`, {
        user_phone: userPhone
      });
      return response;
    } catch (error) {
      console.error('Error recording check-in:', error);
      throw error;
    }
  }

  // Mock data methods for development/fallback
  getMockUserStats() {
    return {
      user_id: 'mock_user',
      points: 4250,
      level: 12,
      daily_streak: 7,
      max_streak: 15,
      streak_freeze_tokens: 2,
      invites_sent: 3,
      invites_accepted: 2,
      total_contact_slots: 5,
      used_contact_slots: 3,
      voice_credits: 3,
      achievements_unlocked: 8,
      total_achievements: 20,
      rank: 34,
      xp_to_next_level: 750,
      total_xp: 3250,
      is_premium: false,
      badges: ['early_adopter', 'social_butterfly'],
      recent_activity: [
        { type: 'achievement', name: 'First Friend', points: 100, timestamp: new Date() },
        { type: 'streak', days: 7, points: 50, timestamp: new Date() }
      ]
    };
  }

  getMockLeaderboard() {
    return [
      { rank: 1, name: 'Alice M.', points: 8750, avatar: '👑', change: 0, user_id: 'alice' },
      { rank: 2, name: 'Bob K.', points: 7230, avatar: '🥈', change: 1, user_id: 'bob' },
      { rank: 3, name: 'Carol L.', points: 6890, avatar: '🥉', change: -1, user_id: 'carol' },
      { rank: 34, name: 'You', points: 4250, avatar: '🎯', change: 2, isUser: true, user_id: 'current' },
      { rank: 35, name: 'David R.', points: 4200, avatar: '👤', change: -1, user_id: 'david' }
    ];
  }

  getMockAchievements() {
    const categories = {
      social: { name: 'Social', icon: 'Users', color: '#667eea' },
      explorer: { name: 'Explorer', icon: 'Target', color: '#10b981' },
      memory: { name: 'Memory Master', icon: 'Brain', color: '#f59e0b' },
      voice: { name: 'Voice Pioneer', icon: 'Mic', color: '#ef4444' }
    };

    return [
      {
        id: 'first_friend',
        category: 'social',
        name: 'First Friend',
        description: 'Add your first contact',
        icon: 'UserPlus',
        unlocked: true,
        progress: 100,
        maxProgress: 100,
        points: 100,
        rarity: 'common',
        unlockedAt: new Date('2024-01-15')
      },
      {
        id: 'social_butterfly',
        category: 'social',
        name: 'Social Butterfly',
        description: 'Add 5 contacts',
        icon: 'Users',
        unlocked: true,
        progress: 100,
        maxProgress: 100,
        points: 250,
        rarity: 'uncommon',
        unlockedAt: new Date('2024-01-20')
      },
      {
        id: 'network_master',
        category: 'social',
        name: 'Network Master',
        description: 'Complete all 5 invitation cycles',
        icon: 'Crown',
        unlocked: false,
        progress: 3,
        maxProgress: 5,
        points: 1000,
        rarity: 'legendary'
      },
      {
        id: 'memory_creator',
        category: 'explorer',
        name: 'Memory Creator',
        description: 'Store 10 memories',
        icon: 'Star',
        unlocked: true,
        progress: 100,
        maxProgress: 100,
        points: 150,
        rarity: 'common',
        unlockedAt: new Date('2024-01-10')
      },
      {
        id: 'deep_thinker',
        category: 'memory',
        name: 'Deep Thinker',
        description: 'Create memories in 5 categories',
        icon: 'Brain',
        unlocked: false,
        progress: 3,
        maxProgress: 5,
        points: 300,
        rarity: 'rare'
      },
      {
        id: 'voice_pioneer',
        category: 'voice',
        name: 'Voice Pioneer',
        description: 'Create your first voice avatar',
        icon: 'Mic',
        unlocked: false,
        progress: 0,
        maxProgress: 1,
        points: 500,
        rarity: 'epic'
      },
      {
        id: 'streak_warrior',
        category: 'explorer',
        name: 'Streak Warrior',
        description: 'Maintain a 30-day streak',
        icon: 'Flame',
        unlocked: false,
        progress: 7,
        maxProgress: 30,
        points: 750,
        rarity: 'epic'
      },
      {
        id: 'memory_sage',
        category: 'memory',
        name: 'Memory Sage',
        description: 'Store 100 memories',
        icon: 'ScrollText',
        unlocked: false,
        progress: 23,
        maxProgress: 100,
        points: 500,
        rarity: 'rare'
      }
    ];
  }

  getMockVoiceAvatars() {
    return [
      {
        id: 1,
        name: 'Professional Voice',
        description: 'Clear and confident for business calls',
        created_at: new Date('2024-01-10'),
        samples_count: 5,
        quality_score: 0.92,
        usage_count: 23,
        is_active: true
      },
      {
        id: 2,
        name: 'Casual Tone',
        description: 'Relaxed voice for friends and family',
        created_at: new Date('2024-01-15'),
        samples_count: 3,
        quality_score: 0.88,
        usage_count: 45,
        is_active: false
      }
    ];
  }

  getMockStreakInfo() {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    
    const timeUntilReset = tomorrow - now;
    const hours = Math.floor(timeUntilReset / (1000 * 60 * 60));
    const minutes = Math.floor((timeUntilReset % (1000 * 60 * 60)) / (1000 * 60));
    
    return {
      current_streak: 7,
      max_streak: 15,
      last_checkin: new Date().toISOString(),
      next_reset_time: `${hours}:${minutes.toString().padStart(2, '0')}:00`,
      freeze_tokens: 2,
      streak_calendar: this.generateStreakCalendar()
    };
  }

  generateStreakCalendar() {
    const calendar = [];
    const today = new Date();
    
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      
      calendar.push({
        date: date.toISOString().split('T')[0],
        day: ['S', 'M', 'T', 'W', 'T', 'F', 'S'][date.getDay()],
        completed: i <= 6, // Last 7 days are completed
        is_today: i === 0
      });
    }
    
    return calendar;
  }

  /**
   * Subscribe to real-time updates via WebSocket
   */
  subscribeToUpdates(wsService, callbacks) {
    if (!wsService) return;
    
    // Subscribe to achievement unlocks
    if (callbacks.onAchievementUnlocked) {
      wsService.on('achievement_unlocked', callbacks.onAchievementUnlocked);
    }
    
    // Subscribe to points updates
    if (callbacks.onPointsUpdate) {
      wsService.on('points_updated', callbacks.onPointsUpdate);
    }
    
    // Subscribe to leaderboard changes
    if (callbacks.onLeaderboardUpdate) {
      wsService.on('leaderboard_update', callbacks.onLeaderboardUpdate);
    }
    
    // Subscribe to invitation updates
    if (callbacks.onInvitationUpdate) {
      wsService.on('invitation_update', callbacks.onInvitationUpdate);
    }
    
    // Subscribe to streak updates
    if (callbacks.onStreakUpdate) {
      wsService.on('streak_update', callbacks.onStreakUpdate);
    }
  }

  /**
   * Unsubscribe from real-time updates
   */
  unsubscribeFromUpdates(wsService) {
    if (!wsService) return;
    
    wsService.off('achievement_unlocked');
    wsService.off('points_updated');
    wsService.off('leaderboard_update');
    wsService.off('invitation_update');
    wsService.off('streak_update');
  }
}

// Create singleton instance
const gamificationService = new GamificationService();

export default gamificationService;