import React, { useState, useEffect, useRef } from 'react';
import { 
  X, 
  ChevronLeft, 
  ChevronRight, 
  Info,
  Target,
  Sparkles,
  CheckCircle,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Hand
} from 'lucide-react';
import '../styles/onboarding.css';

const CoachMarks = ({ marks = [], onComplete, onSkip }) => {
  const [currentMarkIndex, setCurrentMarkIndex] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const [spotlightRect, setSpotlightRect] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const [tooltipPlacement, setTooltipPlacement] = useState('bottom');
  const [seenMarks, setSeenMarks] = useState(new Set());
  const [isAnimating, setIsAnimating] = useState(false);
  const tooltipRef = useRef(null);
  const overlayRef = useRef(null);

  // Default coach marks if none provided
  const defaultMarks = [
    {
      id: 'add-memory',
      target: '.message-input-container',
      title: 'Create Your First Memory',
      content: 'Type anything you want to remember and press Enter. Our AI will automatically categorize and tag it for you.',
      placement: 'top',
      icon: Sparkles,
      waitFor: true,
      trigger: 'immediate'
    },
    {
      id: 'contact-slot',
      target: '.empty-slot:first-child',
      title: 'Add Your Important Contacts',
      content: 'Link memories to specific people. In the free version, you can add up to 5 contacts.',
      placement: 'right',
      icon: Target,
      waitFor: false,
      trigger: 'immediate'
    },
    {
      id: 'rewards',
      target: '.rewards-button',
      title: 'Earn Rewards & Achievements',
      content: 'Complete daily challenges and maintain streaks to unlock premium features for free!',
      placement: 'left',
      icon: CheckCircle,
      waitFor: false,
      trigger: 'on-view'
    },
    {
      id: 'search',
      target: '.search-container',
      title: 'Instant Memory Search',
      content: 'Search through all your memories instantly. Use keywords, dates, or contact names.',
      placement: 'bottom',
      icon: Info,
      waitFor: false,
      trigger: 'on-action'
    },
    {
      id: 'voice-avatar',
      target: '.voice-avatar-button',
      title: 'Unlock Voice Avatars',
      content: 'Earn credits through engagement to unlock AI voice avatars that can speak your memories!',
      placement: 'bottom',
      icon: Sparkles,
      waitFor: false,
      trigger: 'on-earn'
    }
  ];

  const activeMarks = marks.length > 0 ? marks : defaultMarks;
  const currentMark = activeMarks[currentMarkIndex];

  useEffect(() => {
    // Load seen marks from localStorage
    const stored = localStorage.getItem('seenCoachMarks');
    if (stored) {
      setSeenMarks(new Set(JSON.parse(stored)));
    }

    // Check if we should show coach marks
    const onboardingCompleted = localStorage.getItem('onboardingCompleted');
    const coachMarksDisabled = localStorage.getItem('coachMarksDisabled');
    
    if (onboardingCompleted && !coachMarksDisabled) {
      // Start showing coach marks after a delay
      setTimeout(() => {
        showCurrentMark();
      }, 1000);
    }
  }, []);

  useEffect(() => {
    if (isVisible && currentMark) {
      positionSpotlight();
      positionTooltip();
      
      // Add resize listener
      window.addEventListener('resize', handleResize);
      window.addEventListener('scroll', handleScroll);
      
      return () => {
        window.removeEventListener('resize', handleResize);
        window.removeEventListener('scroll', handleScroll);
      };
    }
  }, [isVisible, currentMarkIndex]);

  const handleResize = () => {
    positionSpotlight();
    positionTooltip();
  };

  const handleScroll = () => {
    positionSpotlight();
    positionTooltip();
  };

  const showCurrentMark = () => {
    if (!currentMark || seenMarks.has(currentMark.id)) {
      // Skip already seen marks
      handleNext();
      return;
    }

    // Wait for element if needed
    if (currentMark.waitFor) {
      const checkInterval = setInterval(() => {
        const element = document.querySelector(currentMark.target);
        if (element) {
          clearInterval(checkInterval);
          setIsVisible(true);
          positionSpotlight();
          positionTooltip();
        }
      }, 100);

      // Timeout after 5 seconds
      setTimeout(() => {
        clearInterval(checkInterval);
        handleNext();
      }, 5000);
    } else {
      const element = document.querySelector(currentMark.target);
      if (element) {
        setIsVisible(true);
        positionSpotlight();
        positionTooltip();
      } else {
        // Element not found, skip to next
        handleNext();
      }
    }
  };

  const positionSpotlight = () => {
    if (!currentMark) return;
    
    const element = document.querySelector(currentMark.target);
    if (!element) {
      setSpotlightRect(null);
      return;
    }

    const rect = element.getBoundingClientRect();
    const padding = 10; // Add some padding around the element

    setSpotlightRect({
      top: rect.top - padding,
      left: rect.left - padding,
      width: rect.width + (padding * 2),
      height: rect.height + (padding * 2)
    });
  };

  const positionTooltip = () => {
    if (!currentMark || !spotlightRect || !tooltipRef.current) return;

    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const placement = currentMark.placement || 'bottom';
    const offset = 20; // Distance from spotlight
    let position = { top: 0, left: 0 };
    let actualPlacement = placement;

    // Calculate position based on placement
    switch (placement) {
      case 'top':
        position = {
          top: spotlightRect.top - tooltipRect.height - offset,
          left: spotlightRect.left + (spotlightRect.width / 2) - (tooltipRect.width / 2)
        };
        // Check if tooltip would go off screen
        if (position.top < 10) {
          // Switch to bottom
          actualPlacement = 'bottom';
          position.top = spotlightRect.top + spotlightRect.height + offset;
        }
        break;

      case 'bottom':
        position = {
          top: spotlightRect.top + spotlightRect.height + offset,
          left: spotlightRect.left + (spotlightRect.width / 2) - (tooltipRect.width / 2)
        };
        // Check if tooltip would go off screen
        if (position.top + tooltipRect.height > window.innerHeight - 10) {
          // Switch to top
          actualPlacement = 'top';
          position.top = spotlightRect.top - tooltipRect.height - offset;
        }
        break;

      case 'left':
        position = {
          top: spotlightRect.top + (spotlightRect.height / 2) - (tooltipRect.height / 2),
          left: spotlightRect.left - tooltipRect.width - offset
        };
        // Check if tooltip would go off screen
        if (position.left < 10) {
          // Switch to right
          actualPlacement = 'right';
          position.left = spotlightRect.left + spotlightRect.width + offset;
        }
        break;

      case 'right':
        position = {
          top: spotlightRect.top + (spotlightRect.height / 2) - (tooltipRect.height / 2),
          left: spotlightRect.left + spotlightRect.width + offset
        };
        // Check if tooltip would go off screen
        if (position.left + tooltipRect.width > window.innerWidth - 10) {
          // Switch to left
          actualPlacement = 'left';
          position.left = spotlightRect.left - tooltipRect.width - offset;
        }
        break;
    }

    // Ensure tooltip stays within viewport bounds
    position.left = Math.max(10, Math.min(position.left, window.innerWidth - tooltipRect.width - 10));
    position.top = Math.max(10, Math.min(position.top, window.innerHeight - tooltipRect.height - 10));

    setTooltipPosition(position);
    setTooltipPlacement(actualPlacement);
  };

  const handleNext = () => {
    if (isAnimating) return;

    // Mark current as seen
    if (currentMark) {
      const newSeenMarks = new Set([...seenMarks, currentMark.id]);
      setSeenMarks(newSeenMarks);
      localStorage.setItem('seenCoachMarks', JSON.stringify([...newSeenMarks]));
    }

    if (currentMarkIndex < activeMarks.length - 1) {
      setIsAnimating(true);
      setIsVisible(false);

      setTimeout(() => {
        setCurrentMarkIndex(currentMarkIndex + 1);
        setIsAnimating(false);
        showCurrentMark();
      }, 300);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (isAnimating || currentMarkIndex === 0) return;

    setIsAnimating(true);
    setIsVisible(false);

    setTimeout(() => {
      setCurrentMarkIndex(currentMarkIndex - 1);
      setIsAnimating(false);
      showCurrentMark();
    }, 300);
  };

  const handleComplete = () => {
    setIsVisible(false);
    
    // Mark all as seen
    const allMarkIds = activeMarks.map(m => m.id);
    localStorage.setItem('seenCoachMarks', JSON.stringify(allMarkIds));
    
    if (onComplete) {
      onComplete();
    }
  };

  const handleSkip = () => {
    setIsVisible(false);
    
    // Mark all as seen
    const allMarkIds = activeMarks.map(m => m.id);
    localStorage.setItem('seenCoachMarks', JSON.stringify(allMarkIds));
    
    // Optionally disable coach marks entirely
    localStorage.setItem('coachMarksDisabled', 'true');
    
    if (onSkip) {
      onSkip();
    }
  };

  const resetCoachMarks = () => {
    localStorage.removeItem('seenCoachMarks');
    localStorage.removeItem('coachMarksDisabled');
    setSeenMarks(new Set());
    setCurrentMarkIndex(0);
    showCurrentMark();
  };

  // Expose reset function globally for testing
  useEffect(() => {
    window.resetCoachMarks = resetCoachMarks;
    return () => {
      delete window.resetCoachMarks;
    };
  }, []);

  const getArrowIcon = () => {
    switch (tooltipPlacement) {
      case 'top': return ArrowDown;
      case 'bottom': return ArrowUp;
      case 'left': return ArrowRight;
      case 'right': return ArrowLeft;
      default: return ArrowUp;
    }
  };

  if (!isVisible || !currentMark) return null;

  const Icon = currentMark.icon || Info;
  const ArrowIcon = getArrowIcon();

  return (
    <div className="coach-marks-overlay" ref={overlayRef}>
      {/* Backdrop with spotlight */}
      <div className="coach-marks-backdrop">
        <svg className="spotlight-svg">
          <defs>
            <mask id="spotlight-mask">
              <rect x="0" y="0" width="100%" height="100%" fill="white" />
              {spotlightRect && (
                <rect
                  x={spotlightRect.left}
                  y={spotlightRect.top}
                  width={spotlightRect.width}
                  height={spotlightRect.height}
                  rx="8"
                  fill="black"
                />
              )}
            </mask>
          </defs>
          <rect
            x="0"
            y="0"
            width="100%"
            height="100%"
            fill="rgba(0, 0, 0, 0.7)"
            mask="url(#spotlight-mask)"
          />
        </svg>
      </div>

      {/* Spotlight border effect */}
      {spotlightRect && (
        <div
          className="spotlight-border"
          style={{
            top: `${spotlightRect.top}px`,
            left: `${spotlightRect.left}px`,
            width: `${spotlightRect.width}px`,
            height: `${spotlightRect.height}px`,
          }}
        >
          <div className="spotlight-pulse"></div>
        </div>
      )}

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className={`coach-mark-tooltip ${tooltipPlacement} ${isAnimating ? 'animating' : ''}`}
        style={{
          top: `${tooltipPosition.top}px`,
          left: `${tooltipPosition.left}px`,
        }}
      >
        {/* Arrow pointing to spotlight */}
        <div className={`tooltip-arrow ${tooltipPlacement}`}>
          <ArrowIcon className="w-6 h-6" />
        </div>

        {/* Tooltip content */}
        <div className="tooltip-content">
          <div className="tooltip-header">
            <div className="tooltip-icon">
              <Icon className="w-5 h-5" />
            </div>
            <h3 className="tooltip-title">{currentMark.title}</h3>
            <button className="tooltip-close" onClick={handleSkip}>
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <p className="tooltip-description">{currentMark.content}</p>
          
          {/* Try it indicator */}
          {currentMark.action && (
            <div className="tooltip-action">
              <Hand className="w-4 h-4" />
              <span>{currentMark.action}</span>
            </div>
          )}
          
          <div className="tooltip-footer">
            <div className="tooltip-progress">
              <span>{currentMarkIndex + 1} of {activeMarks.length}</span>
              <div className="progress-dots">
                {activeMarks.map((_, index) => (
                  <div
                    key={index}
                    className={`progress-dot ${index === currentMarkIndex ? 'active' : ''} ${index < currentMarkIndex ? 'completed' : ''}`}
                  />
                ))}
              </div>
            </div>
            
            <div className="tooltip-actions">
              {currentMarkIndex > 0 && (
                <button className="tooltip-button secondary" onClick={handlePrev}>
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </button>
              )}
              
              {currentMarkIndex < activeMarks.length - 1 ? (
                <button className="tooltip-button primary" onClick={handleNext}>
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button className="tooltip-button primary" onClick={handleComplete}>
                  <CheckCircle className="w-4 h-4" />
                  Got it!
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CoachMarks;