import React, { useState, useEffect, useRef } from 'react';
import {
  Gift,
  Zap,
  Star,
  Trophy,
  Crown,
  Diamond,
  Heart,
  Coins,
  Volume2,
  VolumeX,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Sparkles,
  TrendingUp,
  Lock,
  Unlock,
  AlertCircle,
  History
} from 'lucide-react';
import './RewardSpinner.css';

const RewardSpinner = ({ userId, apiService, wsService, theme = 'dark' }) => {
  // State Management
  const [spinning, setSpinning] = useState(false);
  const [rewardHistory, setRewardHistory] = useState([]);
  const [currentReward, setCurrentReward] = useState(null);
  const [slotSymbols, setSlotSymbols] = useState(['❓', '❓', '❓']);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [nearMiss, setNearMiss] = useState(false);
  const [pityProgress, setPityProgress] = useState({
    rare: 0,
    epic: 0,
    legendary: 0
  });
  const [showRewardModal, setShowRewardModal] = useState(false);
  const [spinCount, setSpinCount] = useState(0);
  const [canSpin, setCanSpin] = useState(true);
  const [cooldownTime, setCooldownTime] = useState(0);
  const [animationPhase, setAnimationPhase] = useState('idle'); // idle, spinning, revealing, celebrating
  
  // Refs for animations
  const reelsRef = useRef([]);
  const audioRef = useRef({});
  const particleContainerRef = useRef(null);
  const chestRef = useRef(null);
  
  // Symbol sets for different rarities
  const SYMBOL_SETS = {
    common: ['🍒', '🍋', '🍊', '🍇', '🔔'],
    uncommon: ['💎', '🎰', '7️⃣'],
    rare: ['⭐', '🌟', '💫'],
    epic: ['👑', '🏆'],
    legendary: ['🔮', '🌈']
  };
  
  // Rarity colors and effects
  const RARITY_STYLES = {
    common: { color: '#94a3b8', glow: 'rgba(148, 163, 184, 0.5)', particles: 5 },
    uncommon: { color: '#10b981', glow: 'rgba(16, 185, 129, 0.5)', particles: 10 },
    rare: { color: '#3b82f6', glow: 'rgba(59, 130, 246, 0.5)', particles: 15 },
    epic: { color: '#a855f7', glow: 'rgba(168, 85, 247, 0.5)', particles: 25 },
    legendary: { color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.8)', particles: 50 }
  };
  
  useEffect(() => {
    loadRewardHistory();
    initializeAudio();
    
    // Set up WebSocket listeners
    if (wsService) {
      wsService.on('reward_earned', handleRewardEarned);
      wsService.on('pity_update', handlePityUpdate);
    }
    
    return () => {
      if (wsService) {
        wsService.off('reward_earned', handleRewardEarned);
        wsService.off('pity_update', handlePityUpdate);
      }
    };
  }, [userId]);
  
  useEffect(() => {
    // Handle cooldown timer
    if (cooldownTime > 0) {
      const timer = setTimeout(() => {
        setCooldownTime(cooldownTime - 1);
        if (cooldownTime - 1 === 0) {
          setCanSpin(true);
        }
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [cooldownTime]);
  
  const initializeAudio = () => {
    // Initialize sound effects
    audioRef.current = {
      spin: new Audio('/sounds/slot-spin.mp3'),
      win: new Audio('/sounds/reward-win.mp3'),
      rare: new Audio('/sounds/rare-reward.mp3'),
      epic: new Audio('/sounds/epic-reward.mp3'),
      legendary: new Audio('/sounds/legendary-reward.mp3'),
      nearMiss: new Audio('/sounds/near-miss.mp3'),
      click: new Audio('/sounds/button-click.mp3')
    };
    
    // Preload audio
    Object.values(audioRef.current).forEach(audio => {
      audio.preload = 'auto';
      audio.volume = 0.5;
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
  
  const loadRewardHistory = async () => {
    try {
      const response = await apiService.get(`/api/gamification/rewards/history/${userId}`, {
        params: { limit: 20 }
      });
      
      if (response.data.success) {
        setRewardHistory(response.data.history);
        setPityProgress({
          rare: response.data.user_state?.spins_until_pity?.rare || 0,
          epic: response.data.user_state?.spins_until_pity?.epic || 0,
          legendary: response.data.user_state?.spins_until_pity?.legendary || 0
        });
        setSpinCount(response.data.user_state?.total_spins || 0);
      }
    } catch (error) {
      console.error('Failed to load reward history:', error);
    }
  };
  
  const handleSpin = async () => {
    if (spinning || !canSpin) return;
    
    playSound('click');
    setSpinning(true);
    setNearMiss(false);
    setCurrentReward(null);
    setAnimationPhase('spinning');
    
    // Start slot animation
    animateSlots();
    playSound('spin');
    
    try {
      // Call API to get reward
      const response = await apiService.post('/api/gamification/rewards/spin', {
        user_id: userId,
        trigger_event: 'manual_spin'
      });
      
      if (response.data.success) {
        const { reward, rarity, slot_result, was_pity, near_miss, spins_until_pity } = response.data;
        
        // Update state
        setSpinCount(prev => prev + 1);
        setPityProgress(spins_until_pity);
        setNearMiss(near_miss);
        
        // Delay for dramatic effect
        setTimeout(() => {
          // Stop slots with result
          stopSlots(slot_result, rarity);
          
          // Show reward after slots stop
          setTimeout(() => {
            revealReward(reward, rarity, was_pity);
          }, 1500);
        }, 2000);
      } else {
        // Handle error or cooldown
        stopSpinning();
        if (response.data.reason === 'cooldown_active') {
          setCooldownTime(60); // 60 second cooldown
          setCanSpin(false);
        }
      }
    } catch (error) {
      console.error('Spin failed:', error);
      stopSpinning();
    }
  };
  
  const animateSlots = () => {
    // Create spinning effect
    const spinDuration = 2000;
    const symbols = [...SYMBOL_SETS.common, ...SYMBOL_SETS.uncommon, ...SYMBOL_SETS.rare];
    
    const spinInterval = setInterval(() => {
      setSlotSymbols([
        symbols[Math.floor(Math.random() * symbols.length)],
        symbols[Math.floor(Math.random() * symbols.length)],
        symbols[Math.floor(Math.random() * symbols.length)]
      ]);
    }, 100);
    
    // Store interval to clear later
    reelsRef.current.spinInterval = spinInterval;
  };
  
  const stopSlots = (finalSymbols, rarity) => {
    // Clear spinning interval
    if (reelsRef.current.spinInterval) {
      clearInterval(reelsRef.current.spinInterval);
    }
    
    // Set final symbols one by one for dramatic effect
    setAnimationPhase('revealing');
    
    finalSymbols.forEach((symbol, index) => {
      setTimeout(() => {
        setSlotSymbols(prev => {
          const newSymbols = [...prev];
          newSymbols[index] = symbol;
          return newSymbols;
        });
        
        // Add landing animation
        if (reelsRef.current[index]) {
          reelsRef.current[index].classList.add('reel-land');
        }
      }, index * 300);
    });
  };
  
  const revealReward = (reward, rarity, wasPity) => {
    setCurrentReward({ ...reward, rarity, wasPity });
    setAnimationPhase('celebrating');
    
    // Play appropriate sound
    if (rarity === 'legendary') {
      playSound('legendary');
    } else if (rarity === 'epic') {
      playSound('epic');
    } else if (rarity === 'rare') {
      playSound('rare');
    } else if (nearMiss) {
      playSound('nearMiss');
    } else {
      playSound('win');
    }
    
    // Create particle effects
    createParticleEffects(rarity);
    
    // Show reward modal
    setShowRewardModal(true);
    
    // Update history
    loadRewardHistory();
    
    // Stop spinning
    setTimeout(() => {
      stopSpinning();
    }, 3000);
  };
  
  const stopSpinning = () => {
    setSpinning(false);
    setAnimationPhase('idle');
    
    // Clear reel animations
    reelsRef.current.forEach(reel => {
      if (reel) reel.classList.remove('reel-land');
    });
  };
  
  const createParticleEffects = (rarity) => {
    const style = RARITY_STYLES[rarity];
    const container = particleContainerRef.current;
    
    if (!container) return;
    
    // Clear existing particles
    container.innerHTML = '';
    
    // Create particles based on rarity
    for (let i = 0; i < style.particles; i++) {
      const particle = document.createElement('div');
      particle.className = `particle ${rarity}`;
      particle.style.setProperty('--particle-color', style.color);
      particle.style.setProperty('--particle-delay', `${Math.random() * 2}s`);
      particle.style.setProperty('--particle-duration', `${2 + Math.random() * 2}s`);
      particle.style.setProperty('--particle-x', `${Math.random() * 400 - 200}px`);
      particle.style.setProperty('--particle-y', `${Math.random() * 400 - 200}px`);
      
      container.appendChild(particle);
      
      // Remove particle after animation
      setTimeout(() => {
        particle.remove();
      }, 4000);
    }
  };
  
  const handleRewardEarned = (data) => {
    // Handle real-time reward updates
    loadRewardHistory();
  };
  
  const handlePityUpdate = (data) => {
    setPityProgress(data);
  };
  
  const formatRewardValue = (reward) => {
    if (!reward) return '';
    
    switch (reward.type) {
      case 'xp':
        return `+${reward.value.amount} XP`;
      case 'coins':
        return `+${reward.value.amount} Coins`;
      case 'contact_slot':
        return `+${reward.value.amount} Contact Slot${reward.value.amount > 1 ? 's' : ''}`;
      case 'voice_credit':
        return `+${reward.value.amount} Voice Credit${reward.value.amount > 1 ? 's' : ''}`;
      case 'freeze_token':
        return `+${reward.value.amount} Freeze Token${reward.value.amount > 1 ? 's' : ''}`;
      case 'badge':
        return `Badge: ${reward.value.id}`;
      case 'xp_multiplier':
        return `${reward.value.multiplier}x XP for ${reward.value.duration / 3600}h`;
      case 'premium_time':
        return `${reward.value.days} days Premium`;
      default:
        return JSON.stringify(reward.value);
    }
  };
  
  const getRewardIcon = (type) => {
    switch (type) {
      case 'xp': return <Star size={20} />;
      case 'coins': return <Coins size={20} />;
      case 'contact_slot': return <Heart size={20} />;
      case 'voice_credit': return <Zap size={20} />;
      case 'freeze_token': return <Diamond size={20} />;
      case 'badge': return <Trophy size={20} />;
      case 'xp_multiplier': return <TrendingUp size={20} />;
      case 'premium_time': return <Crown size={20} />;
      default: return <Gift size={20} />;
    }
  };
  
  return (
    <div className={`reward-spinner theme-${theme}`}>
      {/* Reward Modal */}
      {showRewardModal && currentReward && (
        <div className="reward-modal-overlay" onClick={() => setShowRewardModal(false)}>
          <div className="reward-modal" onClick={e => e.stopPropagation()}>
            <div className={`reward-modal-glow ${currentReward.rarity}`} />
            
            <div className="reward-modal-content">
              <div className={`reward-rarity ${currentReward.rarity}`}>
                {currentReward.rarity.toUpperCase()}
                {currentReward.wasPity && <span className="pity-badge">Pity</span>}
              </div>
              
              <div className="reward-icon-container">
                {getRewardIcon(currentReward.type)}
              </div>
              
              <h2 className="reward-title">Reward Earned!</h2>
              <p className="reward-value">{formatRewardValue(currentReward)}</p>
              
              {currentReward.multiplier > 1 && (
                <div className="multiplier-badge">
                  {currentReward.multiplier}x Multiplier!
                </div>
              )}
              
              <button 
                className="close-modal-button"
                onClick={() => setShowRewardModal(false)}
              >
                Awesome!
              </button>
            </div>
            
            <div ref={particleContainerRef} className="particle-container" />
          </div>
        </div>
      )}
      
      {/* Main Spinner Container */}
      <div className="spinner-container">
        {/* Header */}
        <div className="spinner-header">
          <h2>
            <Gift size={24} />
            Reward Spinner
          </h2>
          
          <div className="spinner-controls">
            <button
              className="sound-toggle"
              onClick={() => setSoundEnabled(!soundEnabled)}
              title={soundEnabled ? 'Mute' : 'Unmute'}
            >
              {soundEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </button>
            
            <div className="spin-count">
              <Trophy size={16} />
              <span>Spins: {spinCount}</span>
            </div>
          </div>
        </div>
        
        {/* Slot Machine */}
        <div className={`slot-machine ${animationPhase}`}>
          <div className="slot-frame">
            <div className="reels">
              {slotSymbols.map((symbol, index) => (
                <div 
                  key={index}
                  className="reel"
                  ref={el => reelsRef.current[index] = el}
                >
                  <div className="symbol-container">
                    <span className="symbol">{symbol}</span>
                  </div>
                </div>
              ))}
            </div>
            
            {nearMiss && (
              <div className="near-miss-indicator">
                <AlertCircle size={16} />
                So close!
              </div>
            )}
          </div>
          
          {/* Spin Button */}
          <button
            className={`spin-button ${spinning ? 'spinning' : ''} ${!canSpin ? 'disabled' : ''}`}
            onClick={handleSpin}
            disabled={spinning || !canSpin}
          >
            {spinning ? (
              <RefreshCw size={32} className="spin-icon" />
            ) : cooldownTime > 0 ? (
              <span className="cooldown-timer">{cooldownTime}s</span>
            ) : (
              <>
                <Sparkles size={24} />
                <span>SPIN</span>
              </>
            )}
          </button>
        </div>
        
        {/* Pity Progress */}
        <div className="pity-progress">
          <h3 className="section-title">
            <TrendingUp size={18} />
            Pity Progress
          </h3>
          
          <div className="pity-bars">
            <div className="pity-bar">
              <div className="pity-label">
                <span>Rare</span>
                <span className="pity-count">{10 - pityProgress.rare}/10</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill rare"
                  style={{ width: `${((10 - pityProgress.rare) / 10) * 100}%` }}
                />
              </div>
            </div>
            
            <div className="pity-bar">
              <div className="pity-label">
                <span>Epic</span>
                <span className="pity-count">{25 - pityProgress.epic}/25</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill epic"
                  style={{ width: `${((25 - pityProgress.epic) / 25) * 100}%` }}
                />
              </div>
            </div>
            
            <div className="pity-bar">
              <div className="pity-label">
                <span>Legendary</span>
                <span className="pity-count">{100 - pityProgress.legendary}/100</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill legendary"
                  style={{ width: `${((100 - pityProgress.legendary) / 100) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
        
        {/* Reward History */}
        <div className="history-section">
          <button 
            className="history-toggle"
            onClick={() => setShowHistory(!showHistory)}
          >
            <History size={18} />
            <span>Recent Rewards</span>
            {showHistory ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {showHistory && (
            <div className="history-list">
              {rewardHistory.length === 0 ? (
                <div className="no-history">No rewards yet. Spin to win!</div>
              ) : (
                rewardHistory.slice(0, 10).map((item, index) => (
                  <div key={item.id || index} className={`history-item ${item.rarity}`}>
                    <div className="history-icon">
                      {getRewardIcon(item.type)}
                    </div>
                    <div className="history-details">
                      <div className="history-value">
                        {formatRewardValue(item)}
                      </div>
                      <div className="history-meta">
                        <span className={`rarity-badge ${item.rarity}`}>
                          {item.rarity}
                        </span>
                        {item.was_pity && <span className="pity-indicator">P</span>}
                        <span className="history-time">
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        
        {/* Chest Animation (Alternative to Slots) */}
        <div className="chest-container" ref={chestRef} style={{ display: 'none' }}>
          <div className="chest">
            <div className="chest-lid" />
            <div className="chest-body" />
            <div className="chest-glow" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default RewardSpinner;