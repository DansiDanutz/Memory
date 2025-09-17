import React, { useState, useEffect } from 'react';
import { 
  ChevronRight, 
  ChevronLeft, 
  X, 
  Brain, 
  MessageCircle, 
  Trophy, 
  Users, 
  Shield, 
  Smartphone,
  Bell,
  Sparkles,
  Star,
  Heart,
  Zap,
  CheckCircle,
  ArrowRight,
  Gift,
  Lock,
  Unlock,
  User
} from 'lucide-react';
import '../styles/onboarding.css';

const OnboardingFlow = ({ onComplete, onSkip }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [userName, setUserName] = useState('');
  const [preferences, setPreferences] = useState({
    notifications: false,
    whatsapp: false,
    theme: 'light',
    frequency: 'daily'
  });
  const [isAnimating, setIsAnimating] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);

  const steps = [
    {
      id: 'welcome',
      type: 'welcome',
      icon: Brain,
      title: 'Welcome to MemoApp',
      subtitle: 'Your Personal Memory Guardian',
      description: 'Never forget important moments, conversations, and insights again.',
      illustration: (
        <div className="welcome-illustration">
          <div className="floating-brain">
            <Brain className="w-24 h-24" />
            <div className="pulse-ring"></div>
            <div className="pulse-ring delay-1"></div>
            <div className="pulse-ring delay-2"></div>
          </div>
          <div className="floating-icons">
            <MessageCircle className="float-icon icon-1" />
            <Trophy className="float-icon icon-2" />
            <Heart className="float-icon icon-3" />
            <Star className="float-icon icon-4" />
          </div>
        </div>
      )
    },
    {
      id: 'features',
      type: 'feature',
      icon: Sparkles,
      title: 'Smart Memory Management',
      subtitle: 'AI-Powered Organization',
      description: 'Our AI automatically categorizes and tags your memories for instant retrieval.',
      features: [
        { icon: Brain, text: 'Intelligent categorization' },
        { icon: Zap, text: 'Lightning-fast search' },
        { icon: Shield, text: 'Secure encryption' }
      ],
      illustration: (
        <div className="feature-illustration">
          <div className="memory-cards">
            <div className="memory-card card-1">
              <div className="card-tag">Work</div>
              <div className="card-content">Meeting notes...</div>
            </div>
            <div className="memory-card card-2">
              <div className="card-tag">Personal</div>
              <div className="card-content">Birthday ideas...</div>
            </div>
            <div className="memory-card card-3">
              <div className="card-tag">Ideas</div>
              <div className="card-content">App concept...</div>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'contacts',
      type: 'feature',
      icon: Users,
      title: 'Contact-Based Memories',
      subtitle: 'Remember Everything About Everyone',
      description: 'Link memories to specific contacts and never forget important details about your relationships.',
      features: [
        { icon: Users, text: 'Up to 5 contacts free' },
        { icon: MessageCircle, text: 'Conversation history' },
        { icon: Heart, text: 'Personal insights' }
      ],
      illustration: (
        <div className="contacts-illustration">
          <div className="contact-circle-container">
            <div className="contact-avatar avatar-center">👤</div>
            <div className="contact-avatar avatar-1">👨</div>
            <div className="contact-avatar avatar-2">👩</div>
            <div className="contact-avatar avatar-3">👴</div>
            <div className="contact-avatar avatar-4">👶</div>
            <div className="contact-avatar avatar-5">👧</div>
            <div className="connecting-lines">
              <svg viewBox="0 0 200 200">
                <line x1="100" y1="100" x2="50" y2="50" stroke="var(--primary)" strokeWidth="2" opacity="0.3" />
                <line x1="100" y1="100" x2="150" y2="50" stroke="var(--primary)" strokeWidth="2" opacity="0.3" />
                <line x1="100" y1="100" x2="150" y2="150" stroke="var(--primary)" strokeWidth="2" opacity="0.3" />
                <line x1="100" y1="100" x2="50" y2="150" stroke="var(--primary)" strokeWidth="2" opacity="0.3" />
              </svg>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'gamification',
      type: 'feature',
      icon: Trophy,
      title: 'Earn Rewards & Achievements',
      subtitle: 'Make Memory-Building Fun',
      description: 'Complete challenges, maintain streaks, and unlock premium features through engagement.',
      features: [
        { icon: Trophy, text: 'Daily challenges' },
        { icon: Gift, text: 'Unlock voice avatars' },
        { icon: Star, text: 'Achievement badges' }
      ],
      illustration: (
        <div className="gamification-illustration">
          <div className="achievement-grid">
            <div className="achievement-badge badge-gold">
              <Trophy className="w-8 h-8" />
              <span>Memory Master</span>
            </div>
            <div className="achievement-badge badge-silver">
              <Star className="w-8 h-8" />
              <span>7-Day Streak</span>
            </div>
            <div className="achievement-badge badge-bronze">
              <Zap className="w-8 h-8" />
              <span>Quick Learner</span>
            </div>
            <div className="achievement-badge badge-locked">
              <Lock className="w-8 h-8" />
              <span>???</span>
            </div>
          </div>
          <div className="points-counter">
            <span className="points-value">0</span>
            <span className="points-label">points earned</span>
          </div>
        </div>
      )
    },
    {
      id: 'personalization',
      type: 'input',
      icon: Heart,
      title: 'Personalize Your Experience',
      subtitle: 'Let\'s get to know you',
      description: 'Tell us your name and preferences to customize your memory journey.',
      inputs: [
        {
          type: 'text',
          placeholder: 'What should we call you?',
          value: userName,
          onChange: setUserName,
          icon: User
        }
      ]
    },
    {
      id: 'permissions',
      type: 'permissions',
      icon: Shield,
      title: 'Enable Key Features',
      subtitle: 'Get the most out of MemoApp',
      description: 'Enable these features for the best experience.',
      permissions: [
        {
          id: 'notifications',
          icon: Bell,
          title: 'Notifications',
          description: 'Get reminders for daily memories and achievements',
          value: preferences.notifications,
          onChange: (val) => setPreferences({...preferences, notifications: val})
        },
        {
          id: 'whatsapp',
          icon: Smartphone,
          title: 'WhatsApp Integration',
          description: 'Sync conversations and create memories from chats',
          value: preferences.whatsapp,
          onChange: (val) => setPreferences({...preferences, whatsapp: val})
        }
      ]
    },
    {
      id: 'complete',
      type: 'complete',
      icon: CheckCircle,
      title: `Welcome aboard${userName ? ', ' + userName : ''}!`,
      subtitle: 'You\'re all set',
      description: 'Start creating your first memory and explore all the amazing features.',
      illustration: (
        <div className="complete-illustration">
          <div className="confetti-container">
            {[...Array(20)].map((_, i) => (
              <div key={i} className={`confetti confetti-${i % 4 + 1}`}></div>
            ))}
          </div>
          <div className="success-checkmark">
            <CheckCircle className="w-24 h-24 text-success" />
          </div>
        </div>
      )
    }
  ];

  const currentStepData = steps[currentStep];
  const totalSteps = steps.length;
  const progress = ((currentStep + 1) / totalSteps) * 100;

  useEffect(() => {
    // Track step views
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('onboarding-step', currentStep.toString());
    }
  }, [currentStep]);

  useEffect(() => {
    // Auto-progress welcome screen after 5 seconds if no interaction
    if (currentStep === 0 && !hasInteracted) {
      const timer = setTimeout(() => {
        if (!hasInteracted) {
          handleNext();
        }
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [currentStep, hasInteracted]);

  const handleNext = () => {
    if (isAnimating) return;
    
    setHasInteracted(true);
    
    // Validation for input steps
    if (currentStepData.type === 'input' && !userName.trim()) {
      // Shake animation for empty input
      const inputElement = document.querySelector('.onboarding-input');
      if (inputElement) {
        inputElement.classList.add('shake');
        setTimeout(() => inputElement.classList.remove('shake'), 500);
      }
      return;
    }

    if (currentStep < totalSteps - 1) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentStep(currentStep + 1);
        setIsAnimating(false);
      }, 300);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (isAnimating || currentStep === 0) return;
    
    setHasInteracted(true);
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentStep(currentStep - 1);
      setIsAnimating(false);
    }, 300);
  };

  const handleComplete = () => {
    // Save onboarding completion
    localStorage.setItem('onboardingCompleted', 'true');
    localStorage.setItem('userName', userName);
    localStorage.setItem('userPreferences', JSON.stringify(preferences));
    
    // Trigger completion callback
    onComplete({
      userName,
      preferences,
      completedAt: new Date().toISOString()
    });
  };

  const handleSkip = () => {
    if (window.confirm('Are you sure you want to skip the onboarding? You can always access help from the settings.')) {
      localStorage.setItem('onboardingSkipped', 'true');
      onSkip();
    }
  };

  const renderStepContent = () => {
    const Icon = currentStepData.icon;

    switch (currentStepData.type) {
      case 'welcome':
      case 'feature':
        return (
          <div className="step-content">
            {currentStepData.illustration}
            <div className="step-text">
              <div className="step-icon">
                <Icon className="w-8 h-8" />
              </div>
              <h2 className="step-title">{currentStepData.title}</h2>
              <h3 className="step-subtitle">{currentStepData.subtitle}</h3>
              <p className="step-description">{currentStepData.description}</p>
              {currentStepData.features && (
                <div className="feature-list">
                  {currentStepData.features.map((feature, index) => {
                    const FeatureIcon = feature.icon;
                    return (
                      <div key={index} className="feature-item">
                        <FeatureIcon className="w-5 h-5" />
                        <span>{feature.text}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        );

      case 'input':
        return (
          <div className="step-content">
            <div className="step-text">
              <div className="step-icon">
                <Icon className="w-8 h-8" />
              </div>
              <h2 className="step-title">{currentStepData.title}</h2>
              <h3 className="step-subtitle">{currentStepData.subtitle}</h3>
              <p className="step-description">{currentStepData.description}</p>
              <div className="input-container">
                <input
                  type="text"
                  className="onboarding-input"
                  placeholder="What should we call you?"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleNext()}
                  autoFocus
                />
                <div className="input-hint">
                  Press Enter or click Continue
                </div>
              </div>
            </div>
          </div>
        );

      case 'permissions':
        return (
          <div className="step-content">
            <div className="step-text">
              <div className="step-icon">
                <Icon className="w-8 h-8" />
              </div>
              <h2 className="step-title">{currentStepData.title}</h2>
              <h3 className="step-subtitle">{currentStepData.subtitle}</h3>
              <p className="step-description">{currentStepData.description}</p>
              <div className="permissions-list">
                {currentStepData.permissions.map((permission) => {
                  const PermIcon = permission.icon;
                  return (
                    <div key={permission.id} className="permission-item">
                      <div className="permission-info">
                        <PermIcon className="w-6 h-6" />
                        <div>
                          <h4>{permission.title}</h4>
                          <p>{permission.description}</p>
                        </div>
                      </div>
                      <label className="toggle-switch">
                        <input
                          type="checkbox"
                          checked={permission.value}
                          onChange={(e) => permission.onChange(e.target.checked)}
                        />
                        <span className="toggle-slider"></span>
                      </label>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );

      case 'complete':
        return (
          <div className="step-content">
            {currentStepData.illustration}
            <div className="step-text">
              <div className="step-icon success">
                <Icon className="w-8 h-8" />
              </div>
              <h2 className="step-title">{currentStepData.title}</h2>
              <h3 className="step-subtitle">{currentStepData.subtitle}</h3>
              <p className="step-description">{currentStepData.description}</p>
              <button className="cta-button primary" onClick={handleComplete}>
                <span>Start Your Journey</span>
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="onboarding-overlay">
      <div className={`onboarding-container ${isAnimating ? 'animating' : ''}`}>
        {/* Header */}
        <div className="onboarding-header">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <button className="skip-button" onClick={handleSkip}>
            <X className="w-5 h-5" />
            <span>Skip</span>
          </button>
        </div>

        {/* Content */}
        <div className="onboarding-content">
          <div className={`step-container step-${currentStep}`}>
            {renderStepContent()}
          </div>
        </div>

        {/* Footer */}
        <div className="onboarding-footer">
          <div className="step-indicators">
            {steps.map((_, index) => (
              <div
                key={index}
                className={`step-dot ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
              />
            ))}
          </div>
          
          <div className="navigation-buttons">
            {currentStep > 0 && currentStepData.type !== 'complete' && (
              <button className="nav-button prev" onClick={handlePrev}>
                <ChevronLeft className="w-5 h-5" />
                <span>Back</span>
              </button>
            )}
            
            {currentStepData.type !== 'complete' && (
              <button className="nav-button next" onClick={handleNext}>
                <span>{currentStep === totalSteps - 1 ? 'Complete' : 'Continue'}</span>
                <ChevronRight className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingFlow;