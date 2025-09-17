import React, { useState, useEffect } from 'react';
import {
  Zap,
  Clock,
  Trophy,
  Star,
  Flame,
  X,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Gift,
  Target
} from 'lucide-react';
import CountdownTimer from './CountdownTimer';
import './FlashQuestModal.css';

const FlashQuestModal = ({ 
  quest, 
  onAccept, 
  onDecline, 
  onClose,
  autoShow = true
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isAccepted, setIsAccepted] = useState(false);
  const [showRejectWarning, setShowRejectWarning] = useState(false);
  const [animationStage, setAnimationStage] = useState('entry');

  useEffect(() => {
    if (quest && autoShow) {
      // Delay for dramatic effect
      setTimeout(() => {
        setIsVisible(true);
        setAnimationStage('active');
        playEntrySound();
      }, 100);
    }
  }, [quest, autoShow]);

  const playEntrySound = () => {
    // Would play actual sound effect
    console.log('Playing flash quest entry sound');
  };

  const handleAccept = () => {
    setIsAccepted(true);
    setAnimationStage('accepting');
    
    setTimeout(() => {
      if (onAccept) {
        onAccept(quest);
      }
      closeModal();
    }, 500);
  };

  const handleDecline = () => {
    if (!showRejectWarning) {
      setShowRejectWarning(true);
      return;
    }
    
    setAnimationStage('declining');
    
    setTimeout(() => {
      if (onDecline) {
        onDecline(quest);
      }
      closeModal();
    }, 300);
  };

  const closeModal = () => {
    setAnimationStage('exit');
    
    setTimeout(() => {
      setIsVisible(false);
      if (onClose) {
        onClose();
      }
    }, 300);
  };

  const calculateBonus = () => {
    if (!quest) return 0;
    return Math.round((quest.rewards?.xp || 0) * 1.5);
  };

  const getRarityColor = () => {
    const difficulty = quest?.difficulty || 'medium';
    const colors = {
      easy: '#4caf50',
      medium: '#ff9800',
      hard: '#f44336',
      epic: '#9c27b0'
    };
    return colors[difficulty];
  };

  if (!quest || !isVisible) {
    return null;
  }

  return (
    <div className={`flash-quest-modal-overlay ${animationStage}`}>
      <div className={`flash-quest-modal ${animationStage} ${quest.difficulty}`}>
        {/* Lightning effect background */}
        <div className="lightning-bg">
          <div className="lightning-bolt" />
          <div className="lightning-bolt" />
          <div className="lightning-bolt" />
        </div>
        
        {/* Header with flash animation */}
        <div className="modal-header">
          <div className="flash-icon-container">
            <Zap className="flash-main-icon" />
            <div className="pulse-ring" />
            <div className="pulse-ring delay" />
          </div>
          
          <h1 className="modal-title">
            <span className="flash-text">FLASH</span>
            <span className="quest-text">QUEST</span>
          </h1>
          
          <button 
            className="close-button"
            onClick={handleDecline}
            aria-label="Close"
          >
            <X size={24} />
          </button>
        </div>
        
        {/* Quest details */}
        <div className="quest-details">
          <h2 className="quest-name">{quest.name}</h2>
          <p className="quest-description">{quest.description}</p>
          
          <div className="difficulty-badge" style={{ backgroundColor: getRarityColor() }}>
            <Star size={16} />
            <span>{quest.difficulty.toUpperCase()}</span>
          </div>
        </div>
        
        {/* Timer section */}
        <div className="timer-section">
          <div className="timer-label">
            <AlertTriangle className="warning-icon pulse" />
            <span>Limited Time Only!</span>
          </div>
          
          <div className="main-timer">
            <CountdownTimer
              endTime={quest.expires_at}
              format="full"
              urgent={true}
              colorTransition={true}
              showIcon={false}
            />
          </div>
          
          <p className="urgency-message">
            This quest will disappear forever when the timer runs out!
          </p>
        </div>
        
        {/* Rewards preview */}
        <div className="rewards-section">
          <h3>
            <Gift size={20} />
            Rewards
          </h3>
          
          <div className="reward-cards">
            <div className="reward-card base">
              <Trophy className="reward-icon" />
              <span className="reward-value">{quest.rewards?.xp || 0}</span>
              <span className="reward-label">Base XP</span>
            </div>
            
            <div className="plus-sign">+</div>
            
            <div className="reward-card bonus">
              <Flame className="reward-icon flame-animated" />
              <span className="reward-value">50%</span>
              <span className="reward-label">Flash Bonus</span>
            </div>
            
            <div className="equals-sign">=</div>
            
            <div className="reward-card total">
              <Star className="reward-icon spin" />
              <span className="reward-value">{calculateBonus()}</span>
              <span className="reward-label">Total XP</span>
            </div>
          </div>
          
          {quest.rewards?.points && (
            <div className="additional-rewards">
              <span>+ {quest.rewards.points} Points</span>
            </div>
          )}
        </div>
        
        {/* Requirements */}
        <div className="requirements-section">
          <h3>
            <Target size={20} />
            Objective
          </h3>
          <div className="requirement-box">
            <CheckCircle size={18} />
            <span>{quest.description}</span>
          </div>
          <div className="progress-hint">
            Progress: 0 / {quest.target}
          </div>
        </div>
        
        {/* Action buttons */}
        <div className="action-section">
          {!showRejectWarning ? (
            <>
              <button 
                className="action-btn accept pulse-btn"
                onClick={handleAccept}
                disabled={isAccepted}
              >
                {isAccepted ? (
                  <>
                    <CheckCircle size={20} />
                    Quest Accepted!
                  </>
                ) : (
                  <>
                    <Zap size={20} />
                    Accept Quest
                  </>
                )}
              </button>
              
              <button 
                className="action-btn decline"
                onClick={handleDecline}
              >
                Maybe Later
              </button>
            </>
          ) : (
            <div className="warning-section">
              <div className="warning-message">
                <AlertTriangle size={24} />
                <p>Are you sure? This quest won't come back!</p>
              </div>
              
              <div className="warning-actions">
                <button 
                  className="action-btn accept"
                  onClick={() => {
                    setShowRejectWarning(false);
                    handleAccept();
                  }}
                >
                  I'll Take It!
                </button>
                
                <button 
                  className="action-btn decline confirm"
                  onClick={handleDecline}
                >
                  Skip Quest
                </button>
              </div>
            </div>
          )}
        </div>
        
        {/* Social proof */}
        <div className="social-proof">
          <TrendingUp size={16} />
          <span>
            {Math.floor(Math.random() * 50) + 20} players completed similar quests today
          </span>
        </div>
      </div>
    </div>
  );
};

export default FlashQuestModal;