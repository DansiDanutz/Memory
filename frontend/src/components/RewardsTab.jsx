import React, { useState, useEffect, useRef } from 'react';
import { 
  Trophy, 
  Flame, 
  Gift, 
  Crown,
  Star,
  Lock,
  Users,
  UserPlus,
  Target,
  Award,
  Zap,
  MessageCircle,
  Clock,
  CheckCircle,
  Calendar,
  Volume2,
  Play,
  Plus,
  ChevronUp,
  ChevronDown,
  Sparkles,
  Shield,
  Heart,
  Brain,
  Mic
} from 'lucide-react';
import './RewardsTab.css';

const RewardsTab = ({ userId, theme, gamificationService, wsService }) => {
  // State Management
  const [userStats, setUserStats] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [achievements, setAchievements] = useState([]);
  const [voiceAvatars, setVoiceAvatars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSection, setSelectedSection] = useState('overview');
  const [animateCounters, setAnimateCounters] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [subscriptionStatus, setSubscriptionStatus] = useState(null);
  const [upgradeEligibility, setUpgradeEligibility] = useState(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  
  // Refs for animations
  const streakRef = useRef(null);
  const invitationRef = useRef(null);
  const achievementsRef = useRef(null);
  
  // Mock data for demonstration - will be replaced with API calls
  const [userData, setUserData] = useState({
    dailyStreak: 7,
    maxStreak: 15,
    streakFreezeTokens: 2,
    nextResetTime: '23:45:00',
    invitesSent: 3,
    invitesAccepted: 2,
    totalInvites: 5,
    points: 4250,
    level: 12,
    rank: 34,
    rankChange: 2,
    voiceCredits: 3,
    completedAchievements: 8,
    totalAchievements: 20,
    xpToNextLevel: 750,
    totalXp: 3250
  });

  // Achievement categories
  const achievementCategories = [
    { id: 'social', name: 'Social', icon: Users, color: '#667eea' },
    { id: 'explorer', name: 'Explorer', icon: Target, color: '#10b981' },
    { id: 'memory', name: 'Memory Master', icon: Brain, color: '#f59e0b' },
    { id: 'voice', name: 'Voice Pioneer', icon: Mic, color: '#ef4444' }
  ];

  // Mock achievements data
  const mockAchievements = [
    {
      id: 1,
      category: 'social',
      name: 'First Friend',
      description: 'Add your first contact',
      icon: UserPlus,
      unlocked: true,
      progress: 100,
      maxProgress: 100,
      points: 100,
      rarity: 'common'
    },
    {
      id: 2,
      category: 'social',
      name: 'Social Butterfly',
      description: 'Add 5 contacts',
      icon: Users,
      unlocked: true,
      progress: 100,
      maxProgress: 100,
      points: 250,
      rarity: 'uncommon'
    },
    {
      id: 3,
      category: 'social',
      name: 'Network Master',
      description: 'Complete all 5 invitation cycles',
      icon: Crown,
      unlocked: false,
      progress: 3,
      maxProgress: 5,
      points: 1000,
      rarity: 'legendary'
    },
    {
      id: 4,
      category: 'explorer',
      name: 'Memory Creator',
      description: 'Store 10 memories',
      icon: Star,
      unlocked: true,
      progress: 100,
      maxProgress: 100,
      points: 150,
      rarity: 'common'
    },
    {
      id: 5,
      category: 'memory',
      name: 'Deep Thinker',
      description: 'Create memories in 5 categories',
      icon: Brain,
      unlocked: false,
      progress: 3,
      maxProgress: 5,
      points: 300,
      rarity: 'rare'
    },
    {
      id: 6,
      category: 'voice',
      name: 'Voice Pioneer',
      description: 'Create your first voice avatar',
      icon: Mic,
      unlocked: false,
      progress: 0,
      maxProgress: 1,
      points: 500,
      rarity: 'epic'
    }
  ];

  // Mock leaderboard data
  const mockLeaderboard = [
    { rank: 1, name: 'Alice M.', points: 8750, avatar: '👑', change: 0 },
    { rank: 2, name: 'Bob K.', points: 7230, avatar: '🥈', change: 1 },
    { rank: 3, name: 'Carol L.', points: 6890, avatar: '🥉', change: -1 },
    { rank: 34, name: 'You', points: 4250, avatar: '🎯', change: 2, isUser: true },
    { rank: 35, name: 'David R.', points: 4200, avatar: '👤', change: -1 }
  ];

  useEffect(() => {
    // Initialize data
    loadRewardsData();
    
    // Set up WebSocket listeners if available
    if (wsService) {
      wsService.on('achievement_unlocked', handleAchievementUnlocked);
      wsService.on('points_updated', handlePointsUpdate);
      wsService.on('leaderboard_update', handleLeaderboardUpdate);
    }
    
    // Start counter animations after component mount
    const animTimer = setTimeout(() => setAnimateCounters(true), 100);
    
    return () => {
      clearTimeout(animTimer);
      if (wsService) {
        wsService.off('achievement_unlocked', handleAchievementUnlocked);
        wsService.off('points_updated', handlePointsUpdate);
        wsService.off('leaderboard_update', handleLeaderboardUpdate);
      }
    };
  }, []);

  const loadRewardsData = async () => {
    try {
      setLoading(true);
      
      // Load data from gamification service
      if (gamificationService) {
        const [stats, lb, avs, subStatus, upgradeElig] = await Promise.all([
          gamificationService.getUserStats(userId),
          gamificationService.getLeaderboard('points', 'all_time', 5),
          gamificationService.getVoiceAvatars(userId),
          gamificationService.getSubscriptionStatus(userId),
          gamificationService.getUpgradeEligibility(userId)
        ]);
        
        if (stats) setUserStats(stats);
        if (lb) setLeaderboard(lb);
        if (avs) setVoiceAvatars(avs);
        if (subStatus) setSubscriptionStatus(subStatus);
        if (upgradeElig) setUpgradeEligibility(upgradeElig);
      } else {
        // Use mock data for demonstration
        setAchievements(mockAchievements);
        setLeaderboard(mockLeaderboard);
        setSubscriptionStatus({ tier: 'free', is_premium: false });
      }
      
    } catch (error) {
      console.error('Error loading rewards data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAchievementUnlocked = (achievement) => {
    setShowConfetti(true);
    setTimeout(() => setShowConfetti(false), 3000);
    
    // Update achievement list
    setAchievements(prev => 
      prev.map(a => a.id === achievement.id ? { ...a, unlocked: true, progress: 100 } : a)
    );
  };

  const handlePointsUpdate = (data) => {
    setUserData(prev => ({ ...prev, points: data.points, level: data.level }));
  };

  const handleLeaderboardUpdate = (data) => {
    setLeaderboard(data);
  };

  const useStreakFreeze = () => {
    if (userData.streakFreezeTokens > 0) {
      setUserData(prev => ({ ...prev, streakFreezeTokens: prev.streakFreezeTokens - 1 }));
      // Call API to use freeze token
      if (gamificationService) {
        gamificationService.useStreakFreeze(userId);
      }
    }
  };

  const createVoiceAvatar = () => {
    if (userData.voiceCredits > 0) {
      // Navigate to voice avatar creation
      console.log('Creating voice avatar...');
    }
  };

  const handleUnlockAvatar = async (avatar) => {
    // Show upgrade modal with special offer for this specific avatar
    if (upgradeEligibility && upgradeEligibility.has_locked_avatars) {
      setShowUpgradeModal(true);
    }
  };

  const handlePreviewAvatar = async (avatar) => {
    // Preview avatar functionality
    if (gamificationService) {
      const preview = await gamificationService.getAvatarPreview(avatar.id, userId);
      alert(preview.preview_message || 'Playing avatar preview...');
    }
  };

  const handleUpgradeNow = async () => {
    try {
      if (gamificationService) {
        const result = await gamificationService.upgradeSubscription(userId, 'premium');
        if (result.success) {
          setShowConfetti(true);
          setShowUpgradeModal(false);
          
          // Reload data to show unlocked avatars
          await loadRewardsData();
          
          setTimeout(() => {
            alert('🎉 Congratulations! Your voice avatars are now unlocked!');
          }, 500);
        }
      }
    } catch (error) {
      console.error('Upgrade failed:', error);
      alert('Upgrade failed. Please try again.');
    }
  };

  // Counter animation helper
  const AnimatedCounter = ({ value, duration = 1000, prefix = '', suffix = '' }) => {
    const [displayValue, setDisplayValue] = useState(0);
    
    useEffect(() => {
      if (!animateCounters) return;
      
      const startTime = Date.now();
      const endValue = parseInt(value) || 0;
      
      const updateCounter = () => {
        const now = Date.now();
        const progress = Math.min((now - startTime) / duration, 1);
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = Math.floor(easeOutQuart * endValue);
        
        setDisplayValue(current);
        
        if (progress < 1) {
          requestAnimationFrame(updateCounter);
        }
      };
      
      requestAnimationFrame(updateCounter);
    }, [value, animateCounters]);
    
    return <>{prefix}{displayValue}{suffix}</>;
  };

  // Daily Streak Section
  const renderDailyStreak = () => (
    <div className="rewards-section daily-streak-section glass-panel" ref={streakRef}>
      <div className="section-header">
        <h3>
          <Flame className="section-icon flame-icon" />
          Daily Streak
        </h3>
        {userData.dailyStreak > 0 && (
          <div className="streak-badge">
            <span className="streak-number">
              <AnimatedCounter value={userData.dailyStreak} />
            </span>
            <span className="streak-text">days</span>
          </div>
        )}
      </div>
      
      <div className="streak-content">
        <div className="streak-circle-container">
          <svg className="streak-progress-ring" viewBox="0 0 200 200">
            <circle
              className="progress-ring-bg"
              cx="100"
              cy="100"
              r="88"
              strokeWidth="12"
            />
            <circle
              className="progress-ring-fill"
              cx="100"
              cy="100"
              r="88"
              strokeWidth="12"
              strokeDasharray={`${(userData.dailyStreak / userData.maxStreak) * 553} 553`}
            />
          </svg>
          <div className="streak-center">
            <div className="streak-flame-large">🔥</div>
            <div className="streak-days">
              <AnimatedCounter value={userData.dailyStreak} />
            </div>
            <div className="streak-label">Day Streak</div>
          </div>
        </div>
        
        <div className="streak-info">
          <div className="next-reset">
            <Clock size={16} />
            <span>Reset in: {userData.nextResetTime}</span>
          </div>
          
          {userData.streakFreezeTokens > 0 && (
            <button className="freeze-token-btn glass-button" onClick={useStreakFreeze}>
              <Shield size={16} />
              Use Freeze Token ({userData.streakFreezeTokens})
            </button>
          )}
          
          <div className="streak-calendar">
            <h4>This Week</h4>
            <div className="calendar-grid">
              {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, index) => (
                <div 
                  key={index}
                  className={`calendar-day ${index < userData.dailyStreak ? 'active' : ''}`}
                >
                  <span>{day}</span>
                  {index < userData.dailyStreak && <Flame size={12} />}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Invitation Progress Section
  const renderInvitationProgress = () => (
    <div className="rewards-section invitation-section glass-panel" ref={invitationRef}>
      <div className="section-header">
        <h3>
          <Gift className="section-icon gift-icon" />
          Invitation Rewards
        </h3>
        <div className="invite-counter">
          <AnimatedCounter value={userData.invitesAccepted} />/{userData.totalInvites}
        </div>
      </div>
      
      <div className="invitation-content">
        <div className="invitation-ring-container">
          <svg className="invitation-progress-ring" viewBox="0 0 200 200">
            {[...Array(5)].map((_, index) => {
              const angle = (index * 72) - 90;
              const filled = index < userData.invitesAccepted;
              const sent = index < userData.invitesSent;
              
              return (
                <g key={index} transform={`rotate(${angle} 100 100)`}>
                  <path
                    className={`segment ${filled ? 'filled' : sent ? 'sent' : ''}`}
                    d="M 100 20 A 80 80 0 0 1 175 65 L 100 100 Z"
                    strokeWidth="2"
                  />
                  {filled && (
                    <CheckCircle 
                      className="segment-check"
                      x="130" 
                      y="45" 
                      size={16}
                    />
                  )}
                </g>
              );
            })}
          </svg>
          <div className="invitation-center">
            <div className="invite-progress-text">
              <AnimatedCounter value={userData.invitesAccepted} />
              <span className="divider">/</span>
              <span className="total">5</span>
            </div>
            <div className="invite-label">Accepted</div>
          </div>
        </div>
        
        <div className="invitation-rewards">
          <h4>Complete to Unlock:</h4>
          <div className="reward-preview">
            <div className={`reward-item ${userData.invitesAccepted >= 5 ? 'unlocked' : ''}`}>
              <Users size={20} />
              <span>+1 Contact Slot</span>
              {userData.invitesAccepted >= 5 && <Sparkles className="sparkle" size={14} />}
            </div>
            <div className={`reward-item ${userData.invitesAccepted >= 5 ? 'unlocked' : ''}`}>
              <Mic size={20} />
              <span>Voice Avatar Credit</span>
              {userData.invitesAccepted >= 5 && <Sparkles className="sparkle" size={14} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Achievements Grid Section
  const renderAchievements = () => (
    <div className="rewards-section achievements-section glass-panel" ref={achievementsRef}>
      <div className="section-header">
        <h3>
          <Trophy className="section-icon trophy-icon" />
          Achievements
        </h3>
        <div className="achievement-stats">
          <span className="completed">
            <AnimatedCounter value={userData.completedAchievements} />
            /{userData.totalAchievements}
          </span>
        </div>
      </div>
      
      <div className="achievement-categories">
        {achievementCategories.map(category => (
          <button
            key={category.id}
            className={`category-tab ${selectedSection === category.id ? 'active' : ''}`}
            onClick={() => setSelectedSection(category.id)}
            style={{ '--category-color': category.color }}
          >
            <category.icon size={16} />
            <span>{category.name}</span>
          </button>
        ))}
      </div>
      
      <div className="achievements-grid">
        {achievements
          .filter(a => selectedSection === 'overview' || a.category === selectedSection)
          .map(achievement => (
            <div 
              key={achievement.id}
              className={`achievement-card ${achievement.unlocked ? 'unlocked' : 'locked'} ${achievement.rarity}`}
            >
              <div className="achievement-icon">
                {achievement.unlocked ? (
                  <achievement.icon size={32} />
                ) : (
                  <Lock size={32} />
                )}
              </div>
              
              <div className="achievement-info">
                <h4>{achievement.unlocked ? achievement.name : '???'}</h4>
                <p>{achievement.unlocked ? achievement.description : 'Keep exploring to unlock'}</p>
                
                {!achievement.unlocked && achievement.progress > 0 && (
                  <div className="achievement-progress">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${(achievement.progress / achievement.maxProgress) * 100}%` }}
                      />
                    </div>
                    <span className="progress-text">
                      {achievement.progress}/{achievement.maxProgress}
                    </span>
                  </div>
                )}
                
                {achievement.unlocked && (
                  <div className="achievement-reward">
                    <Star size={14} />
                    <span>{achievement.points} pts</span>
                  </div>
                )}
              </div>
              
              {achievement.rarity === 'legendary' && achievement.unlocked && (
                <div className="legendary-glow" />
              )}
            </div>
          ))
        }
      </div>
    </div>
  );

  // Leaderboard Section
  const renderLeaderboard = () => (
    <div className="rewards-section leaderboard-section glass-panel">
      <div className="section-header">
        <h3>
          <Crown className="section-icon crown-icon" />
          Leaderboard
        </h3>
        <button className="view-full-btn glass-button">
          View Full
        </button>
      </div>
      
      <div className="leaderboard-podium">
        {leaderboard.slice(0, 3).map((user, index) => (
          <div 
            key={user.rank}
            className={`podium-position position-${index + 1}`}
            style={{ '--delay': `${index * 0.1}s` }}
          >
            <div className="podium-avatar">
              <span className="avatar-emoji">{user.avatar}</span>
              {index === 0 && <Crown className="crown-badge" size={20} />}
            </div>
            <div className="podium-info">
              <span className="podium-name">{user.name}</span>
              <span className="podium-points">
                <AnimatedCounter value={user.points} suffix=" pts" />
              </span>
            </div>
            <div className={`podium-stand rank-${index + 1}`}>
              <span className="rank-number">{index + 1}</span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="leaderboard-list">
        {leaderboard.slice(3).map(user => (
          <div 
            key={user.rank}
            className={`leaderboard-item ${user.isUser ? 'current-user' : ''}`}
          >
            <span className="rank-position">#{user.rank}</span>
            <div className="user-info">
              <span className="user-avatar">{user.avatar}</span>
              <span className="user-name">{user.name}</span>
            </div>
            <div className="user-stats">
              <span className="user-points">
                <AnimatedCounter value={user.points} />
              </span>
              {user.change !== 0 && (
                <span className={`rank-change ${user.change > 0 ? 'up' : 'down'}`}>
                  {user.change > 0 ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {Math.abs(user.change)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // Voice Avatar Showcase
  const renderVoiceAvatars = () => (
    <div className="rewards-section voice-avatars-section glass-panel">
      <div className="section-header">
        <h3>
          <Volume2 className="section-icon voice-icon" />
          Voice Avatars
        </h3>
        {userData.voiceCredits > 0 && (
          <button className="create-avatar-btn premium-button" onClick={createVoiceAvatar}>
            <Plus size={16} />
            Create ({userData.voiceCredits} credits)
          </button>
        )}
      </div>
      
      <div className="voice-avatars-grid">
        {voiceAvatars.length > 0 ? (
          voiceAvatars.map((avatar, index) => (
            <div key={avatar.id || index} className={`avatar-card glass-card ${avatar.is_locked ? 'locked-avatar' : ''}`}>
              {avatar.is_locked && (
                <div className="premium-badge">
                  <Crown size={14} />
                  <span>Premium</span>
                </div>
              )}
              <div className="avatar-visual">
                <div className="sound-waves">
                  {[...Array(5)].map((_, i) => (
                    <div 
                      key={i}
                      className="wave"
                      style={{ '--wave-delay': `${i * 0.1}s` }}
                    />
                  ))}
                </div>
                {avatar.is_locked ? <Lock size={24} /> : <Mic size={24} />}
              </div>
              <div className="avatar-info">
                <h4>{avatar.name || `Avatar ${index + 1}`}</h4>
                <p>{avatar.description || 'Custom voice profile'}</p>
                {avatar.is_locked && avatar.preview_generated && (
                  <p className="ready-tag">
                    <Sparkles size={12} /> Ready to use!
                  </p>
                )}
              </div>
              <button 
                className={`preview-btn ${avatar.is_locked ? 'unlock-btn premium-button' : 'glass-button'}`}
                onClick={() => avatar.is_locked ? handleUnlockAvatar(avatar) : handlePreviewAvatar(avatar)}
              >
                {avatar.is_locked ? (
                  <>
                    <Lock size={14} />
                    Unlock Now
                  </>
                ) : (
                  <>
                    <Play size={14} />
                    Preview
                  </>
                )}
              </button>
            </div>
          ))
        ) : (
          <div className="empty-avatars">
            <div className="empty-state glass-card">
              <Mic size={48} className="empty-icon" />
              <h4>No Voice Avatars Yet</h4>
              <p>Complete invitation cycles to earn voice credits</p>
              {userData.voiceCredits > 0 && (
                <button className="create-first-btn premium-button" onClick={createVoiceAvatar}>
                  Create Your First Avatar
                </button>
              )}
            </div>
          </div>
        )}
        
        {userData.voiceCredits === 0 && voiceAvatars.length < 3 && (
          <div className="avatar-card locked-card">
            <div className="locked-overlay">
              <Lock size={24} />
              <span>Complete invitations to unlock</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // Level Progress Bar
  const renderLevelProgress = () => (
    <div className="level-progress-section glass-panel">
      <div className="level-header">
        <div className="level-info">
          <span className="level-label">Level</span>
          <span className="level-number">
            <AnimatedCounter value={userData.level} />
          </span>
        </div>
        <div className="xp-info">
          <span className="xp-current">
            <AnimatedCounter value={userData.totalXp} />
          </span>
          <span className="xp-separator">/</span>
          <span className="xp-needed">{userData.totalXp + userData.xpToNextLevel} XP</span>
        </div>
      </div>
      <div className="level-progress-bar">
        <div 
          className="level-progress-fill"
          style={{ width: `${(userData.totalXp / (userData.totalXp + userData.xpToNextLevel)) * 100}%` }}
        >
          <div className="level-progress-glow" />
        </div>
      </div>
      <div className="level-rewards">
        <span className="next-reward">
          <Gift size={14} />
          Next: Voice Avatar Credit
        </span>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="rewards-tab-loading">
        <div className="loading-spinner">
          <Trophy className="spinner-icon" size={48} />
        </div>
        <p>Loading rewards...</p>
      </div>
    );
  }

  return (
    <div className={`rewards-tab ${theme}`}>
      {showConfetti && <div className="confetti-container" />}
      
      <div className="rewards-header">
        <h2 className="rewards-title">
          <Trophy className="title-icon" />
          Rewards & Achievements
        </h2>
        <div className="user-points">
          <Zap className="points-icon" />
          <AnimatedCounter value={userData.points} suffix=" pts" />
        </div>
      </div>
      
      {renderLevelProgress()}
      
      <div className="rewards-grid">
        {renderDailyStreak()}
        {renderInvitationProgress()}
        {renderAchievements()}
        {renderLeaderboard()}
        {renderVoiceAvatars()}
      </div>
    </div>
  );
};

export default RewardsTab;