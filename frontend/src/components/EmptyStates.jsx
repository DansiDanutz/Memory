import React from 'react';
import { 
  Brain, 
  Users, 
  Trophy, 
  MessageCircle,
  Plus,
  Sparkles,
  Heart,
  Target,
  Gift,
  Lock,
  Unlock,
  Star,
  ArrowRight,
  Zap,
  BookOpen,
  Search,
  Mic,
  X,
  Shield,
  WifiOff,
  RefreshCw,
  Info
} from 'lucide-react';
import '../styles/onboarding.css';

const EmptyStates = ({ type, onAction, context = {} }) => {
  const states = {
    noMemories: {
      icon: Brain,
      illustration: (
        <div className="empty-illustration memories">
          <div className="floating-thoughts">
            <div className="thought-bubble bubble-1">
              <MessageCircle className="w-6 h-6" />
            </div>
            <div className="thought-bubble bubble-2">
              <Heart className="w-6 h-6" />
            </div>
            <div className="thought-bubble bubble-3">
              <Star className="w-6 h-6" />
            </div>
          </div>
          <div className="main-icon">
            <Brain className="w-24 h-24" />
            <div className="pulse-effect"></div>
          </div>
        </div>
      ),
      title: 'Start Your Memory Journey',
      subtitle: 'Your thoughts are worth remembering',
      description: 'Create your first memory and let our AI organize it for you. Every moment counts!',
      features: [
        { icon: Zap, text: 'Instant categorization' },
        { icon: Search, text: 'Lightning-fast search' },
        { icon: Shield, text: 'Secure & private' }
      ],
      primaryAction: {
        text: 'Create Your First Memory',
        icon: Plus,
        onClick: () => onAction('createMemory')
      },
      secondaryAction: {
        text: 'Learn More',
        icon: BookOpen,
        onClick: () => onAction('learnMore')
      }
    },
    
    noContacts: {
      icon: Users,
      illustration: (
        <div className="empty-illustration contacts">
          <div className="contact-slots-preview">
            {[1, 2, 3, 4, 5].map(slot => (
              <div key={slot} className="slot-preview">
                <div className="slot-number">{slot}</div>
                <div className="slot-placeholder">
                  {slot === 1 && <Plus className="w-6 h-6" />}
                  {slot > 1 && <Lock className="w-5 h-5" />}
                </div>
              </div>
            ))}
          </div>
          <div className="connection-lines">
            <svg viewBox="0 0 300 100">
              <path d="M50,50 Q150,20 250,50" stroke="var(--primary)" strokeWidth="2" fill="none" opacity="0.3" />
              <path d="M50,50 Q150,80 250,50" stroke="var(--primary)" strokeWidth="2" fill="none" opacity="0.3" />
            </svg>
          </div>
        </div>
      ),
      title: 'Connect Your Important People',
      subtitle: 'Link memories to the people who matter',
      description: 'Add up to 5 contacts in the free version. Each contact gets their own memory timeline!',
      benefits: [
        { icon: Heart, text: 'Never forget birthdays or anniversaries' },
        { icon: MessageCircle, text: 'Track conversation highlights' },
        { icon: Target, text: 'Personal insights for each relationship' },
        { icon: Gift, text: 'Relationship milestones & memories' }
      ],
      primaryAction: {
        text: 'Add Your First Contact',
        icon: Plus,
        onClick: () => onAction('addContact')
      },
      tips: [
        'Tip: Start with your most important relationships',
        'You can change contacts later (limited changes per slot)'
      ]
    },
    
    noAchievements: {
      icon: Trophy,
      illustration: (
        <div className="empty-illustration achievements">
          <div className="achievement-showcase">
            <div className="achievement-card unlocked">
              <Trophy className="w-8 h-8" />
              <span>First Memory</span>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: '0%' }}></div>
              </div>
              <span className="progress-text">0/1</span>
            </div>
            <div className="achievement-card locked">
              <Lock className="w-8 h-8" />
              <span>Memory Master</span>
              <div className="mystery-text">???</div>
            </div>
            <div className="achievement-card locked">
              <Lock className="w-8 h-8" />
              <span>Social Butterfly</span>
              <div className="mystery-text">???</div>
            </div>
          </div>
          <div className="sparkle-effects">
            <Sparkles className="sparkle sparkle-1" />
            <Sparkles className="sparkle sparkle-2" />
            <Sparkles className="sparkle sparkle-3" />
          </div>
        </div>
      ),
      title: 'Unlock Amazing Achievements',
      subtitle: 'Turn memory-building into a rewarding journey',
      description: 'Complete challenges, maintain streaks, and unlock premium features through engagement!',
      previewAchievements: [
        { name: 'First Steps', requirement: 'Create your first memory', reward: '50 credits' },
        { name: '7-Day Streak', requirement: 'Create memories for 7 days', reward: 'Voice Avatar' },
        { name: 'Memory Master', requirement: 'Store 100 memories', reward: 'Premium Theme' },
        { name: 'Social Butterfly', requirement: 'Fill all 5 contact slots', reward: '500 credits' }
      ],
      primaryAction: {
        text: 'Start Earning Rewards',
        icon: Star,
        onClick: () => onAction('startChallenge')
      },
      motivationalText: 'Every journey begins with a single step!'
    },
    
    noVoiceAvatar: {
      icon: Mic,
      illustration: (
        <div className="empty-illustration voice-avatar">
          <div className="avatar-preview">
            <div className="avatar-silhouette">
              <Mic className="w-16 h-16" />
              <div className="sound-waves">
                <div className="wave wave-1"></div>
                <div className="wave wave-2"></div>
                <div className="wave wave-3"></div>
              </div>
            </div>
            <div className="unlock-progress">
              <div className="progress-ring">
                <svg viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="var(--border)" strokeWidth="8" />
                  <circle 
                    cx="50" 
                    cy="50" 
                    r="45" 
                    fill="none" 
                    stroke="var(--primary)" 
                    strokeWidth="8"
                    strokeDasharray={`${(context.progress || 0) * 2.83} 283`}
                    transform="rotate(-90 50 50)"
                  />
                </svg>
                <div className="progress-text">
                  <span className="progress-value">{context.progress || 0}%</span>
                  <span className="progress-label">Complete</span>
                </div>
              </div>
            </div>
          </div>
          <div className="feature-preview">
            <div className="feature-badge">
              <Zap className="w-5 h-5" />
              <span>AI-Powered Voices</span>
            </div>
            <div className="feature-badge">
              <Heart className="w-5 h-5" />
              <span>Personalized Tones</span>
            </div>
          </div>
        </div>
      ),
      title: 'Unlock Your AI Voice Avatar',
      subtitle: 'Give your memories a voice',
      description: 'Earn credits through daily engagement to unlock AI voice avatars that can speak your memories!',
      howToEarn: [
        { action: 'Create a memory', credits: 10 },
        { action: 'Complete daily challenge', credits: 50 },
        { action: 'Maintain 7-day streak', credits: 200 },
        { action: 'Invite a friend', credits: 100 }
      ],
      currentCredits: context.credits || 0,
      requiredCredits: 500,
      primaryAction: {
        text: 'View How to Earn',
        icon: Gift,
        onClick: () => onAction('viewRewards')
      },
      progressBar: true
    },
    
    noSearchResults: {
      icon: Search,
      illustration: (
        <div className="empty-illustration search">
          <div className="search-animation">
            <Search className="w-20 h-20" />
            <div className="search-pulse"></div>
          </div>
        </div>
      ),
      title: 'No Memories Found',
      subtitle: `No results for "${context.query || 'your search'}"`,
      description: 'Try different keywords, check spelling, or broaden your search terms.',
      suggestions: [
        'Use simpler keywords',
        'Check for typos',
        'Try related terms',
        'Remove filters'
      ],
      primaryAction: {
        text: 'Clear Search',
        icon: X,
        onClick: () => onAction('clearSearch')
      },
      secondaryAction: {
        text: 'Browse All Memories',
        icon: BookOpen,
        onClick: () => onAction('browseAll')
      }
    },
    
    connectionError: {
      icon: WifiOff,
      illustration: (
        <div className="empty-illustration error">
          <div className="error-icon">
            <WifiOff className="w-20 h-20" />
            <div className="error-pulse"></div>
          </div>
        </div>
      ),
      title: 'Connection Lost',
      subtitle: 'Unable to sync your memories',
      description: 'Don\'t worry, your memories are safe. We\'ll sync automatically when connection is restored.',
      tips: [
        'Check your internet connection',
        'Your memories are saved locally',
        'Sync will resume automatically'
      ],
      primaryAction: {
        text: 'Retry Connection',
        icon: RefreshCw,
        onClick: () => onAction('retry')
      }
    }
  };

  const state = states[type];
  if (!state) return null;

  const Icon = state.icon;

  return (
    <div className="empty-state-container">
      {state.illustration}
      
      <div className="empty-state-content">
        <div className="empty-state-icon">
          <Icon className="w-8 h-8" />
        </div>
        
        <h2 className="empty-state-title">{state.title}</h2>
        <h3 className="empty-state-subtitle">{state.subtitle}</h3>
        <p className="empty-state-description">{state.description}</p>
        
        {state.features && (
          <div className="feature-list">
            {state.features.map((feature, index) => {
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
        
        {state.benefits && (
          <div className="benefits-list">
            <h4>Why add contacts?</h4>
            {state.benefits.map((benefit, index) => {
              const BenefitIcon = benefit.icon;
              return (
                <div key={index} className="benefit-item">
                  <BenefitIcon className="w-5 h-5" />
                  <span>{benefit.text}</span>
                </div>
              );
            })}
          </div>
        )}
        
        {state.previewAchievements && (
          <div className="achievements-preview">
            <h4>Achievements you can unlock:</h4>
            {state.previewAchievements.map((achievement, index) => (
              <div key={index} className="achievement-item">
                <div className="achievement-info">
                  <strong>{achievement.name}</strong>
                  <span>{achievement.requirement}</span>
                </div>
                <div className="achievement-reward">
                  <Gift className="w-4 h-4" />
                  <span>{achievement.reward}</span>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {state.howToEarn && (
          <div className="earn-credits-list">
            <h4>How to earn credits:</h4>
            <div className="credits-table">
              {state.howToEarn.map((item, index) => (
                <div key={index} className="credit-row">
                  <span className="credit-action">{item.action}</span>
                  <span className="credit-amount">+{item.credits} credits</span>
                </div>
              ))}
            </div>
            {state.progressBar && (
              <div className="credits-progress">
                <div className="progress-info">
                  <span>Your credits: {state.currentCredits}</span>
                  <span>Required: {state.requiredCredits}</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${Math.min(100, (state.currentCredits / state.requiredCredits) * 100)}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        )}
        
        {state.suggestions && (
          <div className="suggestions-list">
            <h4>Search tips:</h4>
            <ul>
              {state.suggestions.map((suggestion, index) => (
                <li key={index}>{suggestion}</li>
              ))}
            </ul>
          </div>
        )}
        
        {state.tips && (
          <div className="tips-list">
            {state.tips.map((tip, index) => (
              <div key={index} className="tip-item">
                <Info className="w-4 h-4" />
                <span>{tip}</span>
              </div>
            ))}
          </div>
        )}
        
        {state.motivationalText && (
          <div className="motivational-text">
            <Sparkles className="w-5 h-5" />
            <span>{state.motivationalText}</span>
          </div>
        )}
        
        <div className="empty-state-actions">
          {state.primaryAction && (
            <button 
              className="action-button primary"
              onClick={state.primaryAction.onClick}
            >
              <state.primaryAction.icon className="w-5 h-5" />
              <span>{state.primaryAction.text}</span>
            </button>
          )}
          
          {state.secondaryAction && (
            <button 
              className="action-button secondary"
              onClick={state.secondaryAction.onClick}
            >
              <state.secondaryAction.icon className="w-5 h-5" />
              <span>{state.secondaryAction.text}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Export individual empty state components for convenience
export const NoMemories = (props) => <EmptyStates type="noMemories" {...props} />;
export const NoContacts = (props) => <EmptyStates type="noContacts" {...props} />;
export const NoAchievements = (props) => <EmptyStates type="noAchievements" {...props} />;
export const NoVoiceAvatar = (props) => <EmptyStates type="noVoiceAvatar" {...props} />;
export const NoSearchResults = (props) => <EmptyStates type="noSearchResults" {...props} />;
export const ConnectionError = (props) => <EmptyStates type="connectionError" {...props} />;

export default EmptyStates;