import React, { useState, useEffect, useRef } from 'react';
import { 
  Flame, 
  Snowflake, 
  Trophy, 
  Calendar, 
  Clock, 
  Shield,
  TrendingUp,
  AlertTriangle,
  Star,
  Zap,
  Gift,
  Lock,
  Unlock,
  ChevronRight,
  CheckCircle
} from 'lucide-react';
import './StreakDisplay.css';

const StreakDisplay = ({ userId, apiService, wsService, theme = 'dark' }) => {
  // State Management
  const [streakData, setStreakData] = useState({
    current_streak: 0,
    longest_streak: 0,
    total_checkins: 0,
    freeze_tokens: 0,
    freeze_active: false,
    freeze_expires: null,
    has_checked_in_today: false,
    last_checkin: null,
    next_reset: null,
    time_until_reset: null,
    milestones_reached: [],
    next_milestone: null,
    perfect_weeks: 0,
    perfect_months: 0,
    activity_calendar: []
  });

  const [loading, setLoading] = useState(true);
  const [checkingIn, setCheckingIn] = useState(false);
  const [countdown, setCountdown] = useState('');
  const [showMilestoneAnimation, setShowMilestoneAnimation] = useState(false);
  const [currentMilestone, setCurrentMilestone] = useState(null);
  const [animateFlame, setAnimateFlame] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);
  const [usingFreeze, setUsingFreeze] = useState(false);

  // Animation refs
  const flameRef = useRef(null);
  const counterRef = useRef(null);
  const milestoneRef = useRef(null);

  // Milestone definitions
  const MILESTONES = [
    { days: 3, name: 'Starter', icon: '🔥', reward: '1 Freeze Token' },
    { days: 7, name: 'Week Warrior', icon: '📅', reward: '100 Points' },
    { days: 14, name: 'Fortnight Fighter', icon: '🎯', reward: '1 Contact Slot' },
    { days: 21, name: 'Three Week Champion', icon: '🏆', reward: '1 Voice Credit' },
    { days: 30, name: 'Monthly Master', icon: '🌟', reward: 'Special Badge' },
    { days: 50, name: 'Streak Sentinel', icon: '🛡️', reward: '3 Freeze Tokens' },
    { days: 60, name: 'Two Month Titan', icon: '⚡', reward: '500 Points' },
    { days: 75, name: 'Persistent Pro', icon: '💎', reward: '2 Contact Slots' },
    { days: 100, name: 'Century Champion', icon: '👑', reward: 'Streak Shield' },
    { days: 150, name: 'Dedication Deity', icon: '🌈', reward: '5 Voice Credits' },
    { days: 200, name: 'Legendary', icon: '🔮', reward: 'Legendary Badge' },
    { days: 365, name: 'Year of Fire', icon: '🌟', reward: 'Lifetime Premium' }
  ];

  useEffect(() => {
    loadStreakData();
    
    // Set up WebSocket listeners
    if (wsService) {
      wsService.on('streak_update', handleStreakUpdate);
      wsService.on('milestone_reached', handleMilestoneReached);
    }

    // Start countdown timer
    const timer = setInterval(updateCountdown, 1000);

    return () => {
      clearInterval(timer);
      if (wsService) {
        wsService.off('streak_update', handleStreakUpdate);
        wsService.off('milestone_reached', handleMilestoneReached);
      }
    };
  }, [userId]);

  const loadStreakData = async () => {
    try {
      setLoading(true);
      const response = await apiService.get(`/api/gamification/streak/${userId}`);
      setStreakData(response.data);
      
      // Animate flame if streak is active
      if (response.data.current_streak > 0) {
        setAnimateFlame(true);
      }
    } catch (error) {
      console.error('Failed to load streak data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIn = async () => {
    if (checkingIn || streakData.has_checked_in_today) return;
    
    try {
      setCheckingIn(true);
      
      const response = await apiService.post('/api/gamification/streak/check-in', {
        user_id: userId,
        activity_type: 'daily_login'
      });

      if (response.data.success) {
        // Update streak data
        await loadStreakData();
        
        // Show animations
        animateCheckIn(response.data);
        
        // Check for milestone
        if (response.data.milestone_reached) {
          showMilestoneReached(response.data.milestone_reached);
        }
      }
    } catch (error) {
      console.error('Check-in failed:', error);
    } finally {
      setCheckingIn(false);
    }
  };

  const handleUseFreeze = async () => {
    if (usingFreeze || streakData.freeze_tokens <= 0) return;
    
    try {
      setUsingFreeze(true);
      
      const response = await apiService.post('/api/gamification/streak/freeze', {
        user_id: userId
      });

      if (response.data.success) {
        await loadStreakData();
        
        // Show freeze animation
        animateFreezeUse();
      }
    } catch (error) {
      console.error('Failed to use freeze token:', error);
    } finally {
      setUsingFreeze(false);
    }
  };

  const animateCheckIn = (data) => {
    // Flame burst animation
    if (flameRef.current) {
      flameRef.current.classList.add('flame-burst');
      setTimeout(() => {
        flameRef.current?.classList.remove('flame-burst');
      }, 1000);
    }

    // Counter increment animation
    if (counterRef.current) {
      counterRef.current.classList.add('counter-increment');
      setTimeout(() => {
        counterRef.current?.classList.remove('counter-increment');
      }, 600);
    }
  };

  const animateFreezeUse = () => {
    // Freeze effect animation
    const freezeElement = document.createElement('div');
    freezeElement.className = 'freeze-effect';
    freezeElement.innerHTML = '❄️';
    document.body.appendChild(freezeElement);
    
    setTimeout(() => {
      freezeElement.remove();
    }, 2000);
  };

  const showMilestoneReached = (milestone) => {
    setCurrentMilestone(milestone);
    setShowMilestoneAnimation(true);
    
    setTimeout(() => {
      setShowMilestoneAnimation(false);
    }, 5000);
  };

  const handleStreakUpdate = (data) => {
    setStreakData(prevData => ({ ...prevData, ...data }));
  };

  const handleMilestoneReached = (milestone) => {
    showMilestoneReached(milestone);
  };

  const updateCountdown = () => {
    if (!streakData.next_reset) return;
    
    const now = new Date();
    const reset = new Date(streakData.next_reset);
    const diff = reset - now;
    
    if (diff <= 0) {
      setCountdown('Expired');
      loadStreakData();
      return;
    }
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    setCountdown(`${hours}h ${minutes}m ${seconds}s`);
    
    // Warning colors
    if (hours < 2) {
      document.documentElement.style.setProperty('--countdown-color', '#ef4444');
    } else if (hours < 6) {
      document.documentElement.style.setProperty('--countdown-color', '#f59e0b');
    } else {
      document.documentElement.style.setProperty('--countdown-color', '#10b981');
    }
  };

  const renderActivityCalendar = () => {
    const calendar = [];
    const today = new Date();
    
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      const activity = streakData.activity_calendar.find(
        a => a.date.split('T')[0] === dateStr
      );
      
      calendar.push(
        <div
          key={i}
          className={`calendar-day ${activity ? 'active' : ''}`}
          title={`${dateStr}: ${activity ? activity.points + ' points' : 'No activity'}`}
        >
          {activity && <Flame size={12} />}
        </div>
      );
    }
    
    return calendar;
  };

  const renderMilestones = () => {
    return MILESTONES.map(milestone => {
      const reached = streakData.milestones_reached?.includes(milestone.days);
      const isNext = milestone.days === streakData.next_milestone;
      const progress = Math.min(100, (streakData.current_streak / milestone.days) * 100);
      
      return (
        <div
          key={milestone.days}
          className={`milestone-item ${reached ? 'reached' : ''} ${isNext ? 'next' : ''}`}
        >
          <div className="milestone-icon">{milestone.icon}</div>
          <div className="milestone-info">
            <div className="milestone-name">
              {milestone.name}
              {reached && <CheckCircle size={16} className="check-icon" />}
            </div>
            <div className="milestone-days">Day {milestone.days}</div>
            <div className="milestone-reward">{milestone.reward}</div>
            {!reached && (
              <div className="milestone-progress">
                <div 
                  className="milestone-progress-bar"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
          </div>
        </div>
      );
    });
  };

  const getStreakStatus = () => {
    if (streakData.current_streak === 0) return 'broken';
    if (streakData.has_checked_in_today) return 'active';
    if (streakData.freeze_active) return 'frozen';
    if (parseInt(countdown.split('h')[0]) < 2) return 'danger';
    return 'pending';
  };

  const status = getStreakStatus();

  if (loading) {
    return (
      <div className="streak-display loading">
        <div className="loading-spinner">
          <Flame size={48} className="spinning" />
        </div>
      </div>
    );
  }

  return (
    <div className={`streak-display theme-${theme} status-${status}`}>
      {/* Milestone Animation Overlay */}
      {showMilestoneAnimation && currentMilestone && (
        <div className="milestone-animation-overlay">
          <div className="milestone-animation" ref={milestoneRef}>
            <div className="milestone-icon-large">{currentMilestone.icon}</div>
            <h2>{currentMilestone.milestone_name} Unlocked!</h2>
            <p>Day {currentMilestone.milestone_days}</p>
            <div className="milestone-reward-display">
              <Gift size={24} />
              <span>{currentMilestone.reward_type}: {currentMilestone.reward_value}</span>
            </div>
            <div className="confetti-container">
              {[...Array(50)].map((_, i) => (
                <div key={i} className="confetti" style={{
                  '--delay': `${Math.random() * 2}s`,
                  '--duration': `${2 + Math.random() * 2}s`,
                  '--x': `${Math.random() * 200 - 100}px`
                }} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Streak Display */}
      <div className="streak-header">
        <div className="streak-flame-container" ref={flameRef}>
          <Flame 
            size={64} 
            className={`streak-flame ${animateFlame ? 'animate' : ''}`}
            style={{ '--flame-intensity': Math.min(1, streakData.current_streak / 30) }}
          />
          <div className="streak-count" ref={counterRef}>
            {streakData.current_streak}
          </div>
        </div>

        <div className="streak-info">
          <h2 className="streak-title">
            {streakData.current_streak > 0 ? 'Day Streak!' : 'Start Your Streak'}
          </h2>
          
          <div className="streak-stats">
            <div className="stat">
              <Trophy size={16} />
              <span>Best: {streakData.longest_streak}</span>
            </div>
            <div className="stat">
              <Calendar size={16} />
              <span>Total: {streakData.total_checkins}</span>
            </div>
            <div className="stat">
              <TrendingUp size={16} />
              <span>Perfect Weeks: {streakData.perfect_weeks}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Countdown Timer */}
      <div className="streak-countdown">
        <Clock size={20} />
        <span>Next reset in: </span>
        <strong className={`countdown ${parseInt(countdown.split('h')[0]) < 2 ? 'urgent' : ''}`}>
          {countdown}
        </strong>
        {parseInt(countdown.split('h')[0]) < 2 && !streakData.has_checked_in_today && (
          <AlertTriangle size={16} className="warning-icon" />
        )}
      </div>

      {/* Check-in Button */}
      {!streakData.has_checked_in_today ? (
        <button 
          className="check-in-button"
          onClick={handleCheckIn}
          disabled={checkingIn}
        >
          {checkingIn ? (
            <div className="loading-dots">
              <span></span><span></span><span></span>
            </div>
          ) : (
            <>
              <Zap size={20} />
              <span>Check In Now</span>
            </>
          )}
        </button>
      ) : (
        <div className="checked-in-badge">
          <CheckCircle size={20} />
          <span>Checked in today!</span>
        </div>
      )}

      {/* Freeze Tokens */}
      <div className="freeze-tokens-section">
        <div className="freeze-header">
          <Snowflake size={20} />
          <span>Freeze Tokens: {streakData.freeze_tokens}</span>
          {streakData.freeze_active && (
            <div className="freeze-active-badge">
              <Shield size={16} />
              <span>Protected</span>
            </div>
          )}
        </div>
        
        {streakData.freeze_tokens > 0 && !streakData.freeze_active && (
          <button 
            className="use-freeze-button"
            onClick={handleUseFreeze}
            disabled={usingFreeze}
          >
            {usingFreeze ? 'Using...' : 'Use Freeze Token'}
          </button>
        )}
        
        {streakData.freeze_expires && (
          <div className="freeze-expires">
            Freeze expires: {new Date(streakData.freeze_expires).toLocaleString()}
          </div>
        )}
      </div>

      {/* Activity Calendar */}
      <div className="activity-section">
        <button 
          className="calendar-toggle"
          onClick={() => setShowCalendar(!showCalendar)}
        >
          <Calendar size={20} />
          <span>Activity History</span>
          <ChevronRight 
            size={16} 
            className={`chevron ${showCalendar ? 'rotated' : ''}`}
          />
        </button>
        
        {showCalendar && (
          <div className="activity-calendar">
            <div className="calendar-label">Last 30 Days</div>
            <div className="calendar-grid">
              {renderActivityCalendar()}
            </div>
          </div>
        )}
      </div>

      {/* Milestones */}
      <div className="milestones-section">
        <h3 className="section-title">
          <Star size={20} />
          Milestones
        </h3>
        
        <div className="milestones-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ 
                width: `${Math.min(100, (streakData.current_streak / (streakData.next_milestone || 365)) * 100)}%` 
              }}
            />
          </div>
          {streakData.next_milestone && (
            <div className="next-milestone-info">
              {streakData.current_streak}/{streakData.next_milestone} days to next milestone
            </div>
          )}
        </div>
        
        <div className="milestones-list">
          {renderMilestones()}
        </div>
      </div>

      {/* Loss Aversion Message */}
      {streakData.current_streak > 0 && !streakData.has_checked_in_today && (
        <div className="loss-aversion-message">
          <AlertTriangle size={20} />
          <div>
            <strong>Don't lose your {streakData.current_streak}-day streak!</strong>
            <p>You've invested {streakData.total_checkins} days total. Keep it going!</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default StreakDisplay;