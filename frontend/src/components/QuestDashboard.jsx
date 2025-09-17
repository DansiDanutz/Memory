import React, { useState, useEffect } from 'react';
import {
  Target,
  Trophy,
  Clock,
  Zap,
  Calendar,
  ChevronRight,
  Star,
  Gift,
  AlertCircle,
  Flame,
  CheckCircle2,
  Lock,
  TrendingUp
} from 'lucide-react';
import CountdownTimer from './CountdownTimer';
import './QuestDashboard.css';

const QuestDashboard = ({ userId, theme, questService, wsService }) => {
  const [activeTab, setActiveTab] = useState('daily');
  const [quests, setQuests] = useState({
    daily: [],
    weekly: [],
    flash: [],
    event: []
  });
  const [loading, setLoading] = useState(true);
  const [claimingQuest, setClaimingQuest] = useState(null);
  const [showCompletionEffect, setShowCompletionEffect] = useState(false);
  const [completedQuestInfo, setCompletedQuestInfo] = useState(null);

  // Quest type configurations
  const questTypeConfig = {
    daily: {
      icon: Calendar,
      color: '#4caf50',
      title: 'Daily Quests',
      description: 'Reset every day at midnight',
      emptyMessage: 'New daily quests will be available soon!'
    },
    weekly: {
      icon: Trophy,
      color: '#2196f3',
      title: 'Weekly Challenges',
      description: 'Bigger rewards for dedicated players',
      emptyMessage: 'Weekly challenges reset on Monday'
    },
    flash: {
      icon: Zap,
      color: '#ff9800',
      title: 'Flash Quests',
      description: 'Limited time - Act fast!',
      emptyMessage: 'Flash quests appear randomly. Check back often!',
      urgent: true
    },
    event: {
      icon: Star,
      color: '#9c27b0',
      title: 'Special Events',
      description: 'Seasonal and special occasions',
      emptyMessage: 'No active events right now'
    }
  };

  // Difficulty colors
  const difficultyColors = {
    easy: '#4caf50',
    medium: '#ff9800',
    hard: '#f44336',
    epic: '#9c27b0'
  };

  useEffect(() => {
    loadQuests();
    
    // Set up WebSocket listeners
    if (wsService) {
      wsService.on('quest_completed', handleQuestCompleted);
      wsService.on('flash_quest_available', handleFlashQuestAvailable);
      wsService.on('quest_expired', handleQuestExpired);
    }
    
    // Check for flash quests periodically
    const flashCheckInterval = setInterval(checkFlashQuests, 60000); // Every minute
    
    return () => {
      clearInterval(flashCheckInterval);
      if (wsService) {
        wsService.off('quest_completed', handleQuestCompleted);
        wsService.off('flash_quest_available', handleFlashQuestAvailable);
        wsService.off('quest_expired', handleQuestExpired);
      }
    };
  }, [userId]);

  const loadQuests = async () => {
    try {
      setLoading(true);
      
      // Generate daily quests if needed
      await questService.generateDailyQuests(userId);
      
      // Get all active quests
      const activeQuests = await questService.getActiveQuests(userId);
      setQuests(activeQuests);
      
      // Check if there's a flash quest tab with active quests
      if (activeQuests.flash && activeQuests.flash.length > 0) {
        setActiveTab('flash'); // Auto-switch to flash tab for urgency
      }
    } catch (error) {
      console.error('Error loading quests:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkFlashQuests = async () => {
    try {
      const flashQuest = await questService.checkFlashQuest(userId);
      if (flashQuest && flashQuest.available) {
        // Add new flash quest to state
        setQuests(prev => ({
          ...prev,
          flash: [flashQuest.quest, ...prev.flash]
        }));
        
        // Switch to flash tab and show notification
        setActiveTab('flash');
        showFlashQuestNotification(flashQuest.quest);
      }
    } catch (error) {
      console.error('Error checking flash quests:', error);
    }
  };

  const handleQuestCompleted = (questData) => {
    setShowCompletionEffect(true);
    setCompletedQuestInfo(questData);
    
    setTimeout(() => {
      setShowCompletionEffect(false);
      setCompletedQuestInfo(null);
      loadQuests(); // Reload to update UI
    }, 3000);
  };

  const handleFlashQuestAvailable = (questData) => {
    setQuests(prev => ({
      ...prev,
      flash: [questData, ...prev.flash]
    }));
    setActiveTab('flash');
  };

  const handleQuestExpired = (questId) => {
    // Remove expired quest from state
    setQuests(prev => {
      const newQuests = { ...prev };
      for (const type in newQuests) {
        newQuests[type] = newQuests[type].filter(q => q.id !== questId);
      }
      return newQuests;
    });
  };

  const showFlashQuestNotification = (quest) => {
    // This would trigger a toast or modal notification
    console.log('Flash quest available!', quest);
  };

  const handleClaimReward = async (quest) => {
    if (claimingQuest === quest.id) return;
    
    try {
      setClaimingQuest(quest.id);
      const result = await questService.claimQuestRewards(userId, quest.id);
      
      if (result) {
        handleQuestCompleted({
          quest: quest.name,
          rewards: result.rewards
        });
      }
    } catch (error) {
      console.error('Error claiming quest reward:', error);
    } finally {
      setClaimingQuest(null);
    }
  };

  const calculateProgress = (quest) => {
    const progress = quest.current_progress || 0;
    const target = quest.target || 1;
    return Math.min((progress / target) * 100, 100);
  };

  const renderQuestCard = (quest) => {
    const progress = calculateProgress(quest);
    const isComplete = quest.completed || progress >= 100;
    const isClaimed = quest.claimed;
    const isExpiringSoon = quest.expires_at && 
      new Date(quest.expires_at) - new Date() < 3600000; // Less than 1 hour
    
    return (
      <div 
        key={quest.id}
        className={`quest-card ${isComplete ? 'complete' : ''} ${isExpiringSoon ? 'expiring-soon' : ''} ${quest.is_flash ? 'flash-quest' : ''}`}
        style={{
          '--quest-color': difficultyColors[quest.difficulty] || '#666'
        }}
      >
        <div className="quest-header">
          <div className="quest-info">
            <h3 className="quest-name">
              {quest.is_flash && <Zap className="flash-icon" />}
              {quest.name}
            </h3>
            <p className="quest-description">{quest.description}</p>
          </div>
          <div className="quest-difficulty">
            <span className={`difficulty-badge ${quest.difficulty}`}>
              {quest.difficulty}
            </span>
          </div>
        </div>
        
        <div className="quest-progress">
          <div className="progress-info">
            <span className="progress-text">
              {quest.current_progress || 0} / {quest.target}
            </span>
            <span className="progress-percentage">{Math.round(progress)}%</span>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        
        <div className="quest-footer">
          <div className="quest-rewards">
            <div className="reward">
              <Trophy size={16} />
              <span>{quest.rewards?.xp || 0} XP</span>
            </div>
            {quest.rewards?.points && (
              <div className="reward">
                <Star size={16} />
                <span>{quest.rewards.points} Points</span>
              </div>
            )}
            {quest.is_flash && quest.rewards?.xp && (
              <div className="reward bonus">
                <Flame size={16} />
                <span>1.5x Bonus!</span>
              </div>
            )}
          </div>
          
          <div className="quest-actions">
            {quest.expires_at && !isClaimed && (
              <CountdownTimer 
                endTime={quest.expires_at}
                onExpire={() => handleQuestExpired(quest.id)}
                urgent={isExpiringSoon}
                compact
              />
            )}
            
            {isComplete && !isClaimed && (
              <button 
                className="claim-button"
                onClick={() => handleClaimReward(quest)}
                disabled={claimingQuest === quest.id}
              >
                {claimingQuest === quest.id ? (
                  <span className="claiming">Claiming...</span>
                ) : (
                  <>
                    <Gift size={16} />
                    Claim Reward
                  </>
                )}
              </button>
            )}
            
            {isClaimed && (
              <div className="claimed-badge">
                <CheckCircle2 size={16} />
                Claimed
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderQuestSection = (type) => {
    const config = questTypeConfig[type];
    const TypeIcon = config.icon;
    const questList = quests[type] || [];
    
    return (
      <div className="quest-section">
        <div className="section-header">
          <TypeIcon size={24} style={{ color: config.color }} />
          <div className="section-info">
            <h2>{config.title}</h2>
            <p>{config.description}</p>
          </div>
          {type === 'flash' && questList.length > 0 && (
            <div className="urgency-indicator">
              <AlertCircle className="pulse" />
              <span>Limited Time!</span>
            </div>
          )}
        </div>
        
        {questList.length > 0 ? (
          <div className="quest-grid">
            {questList.map(quest => renderQuestCard(quest))}
          </div>
        ) : (
          <div className="empty-state">
            <Lock size={48} />
            <p>{config.emptyMessage}</p>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="quest-dashboard loading">
        <div className="loading-spinner" />
        <p>Loading quests...</p>
      </div>
    );
  }

  return (
    <div className={`quest-dashboard ${theme}`}>
      <div className="dashboard-header">
        <h1>
          <Target size={28} />
          Quest Center
        </h1>
        <div className="quest-stats">
          <div className="stat">
            <span className="stat-label">Active</span>
            <span className="stat-value">
              {Object.values(quests).flat().filter(q => !q.completed).length}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Completed</span>
            <span className="stat-value">
              {Object.values(quests).flat().filter(q => q.completed && !q.claimed).length}
            </span>
          </div>
        </div>
      </div>
      
      <div className="quest-tabs">
        {Object.keys(questTypeConfig).map(type => {
          const config = questTypeConfig[type];
          const TypeIcon = config.icon;
          const hasQuests = quests[type] && quests[type].length > 0;
          const hasUnclaimed = quests[type]?.some(q => q.completed && !q.claimed);
          
          return (
            <button
              key={type}
              className={`tab-button ${activeTab === type ? 'active' : ''} ${hasUnclaimed ? 'has-unclaimed' : ''}`}
              onClick={() => setActiveTab(type)}
              style={{
                '--tab-color': config.color
              }}
            >
              <TypeIcon size={20} />
              <span>{config.title}</span>
              {hasQuests && (
                <span className="tab-badge">{quests[type].length}</span>
              )}
              {hasUnclaimed && <span className="notification-dot" />}
            </button>
          );
        })}
      </div>
      
      <div className="quest-content">
        {renderQuestSection(activeTab)}
      </div>
      
      {showCompletionEffect && completedQuestInfo && (
        <div className="completion-overlay">
          <div className="completion-animation">
            <Trophy className="trophy-icon" />
            <h2>Quest Complete!</h2>
            <p>{completedQuestInfo.quest}</p>
            <div className="rewards-earned">
              <span>+{completedQuestInfo.rewards?.xp || 0} XP</span>
              {completedQuestInfo.rewards?.points && (
                <span>+{completedQuestInfo.rewards.points} Points</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestDashboard;