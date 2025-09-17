// Onboarding Service
// Manages onboarding state, progress tracking, and analytics

class OnboardingService {
  constructor() {
    this.storageKeys = {
      onboardingCompleted: 'onboardingCompleted',
      onboardingSkipped: 'onboardingSkipped',
      onboardingStep: 'onboardingStep',
      userName: 'userName',
      userPreferences: 'userPreferences',
      seenCoachMarks: 'seenCoachMarks',
      coachMarksDisabled: 'coachMarksDisabled',
      onboardingAnalytics: 'onboardingAnalytics',
      firstMemoryCreated: 'firstMemoryCreated',
      firstContactAdded: 'firstContactAdded',
      completionTimestamp: 'onboardingCompletionTimestamp'
    };
    
    this.analyticsEvents = {
      ONBOARDING_STARTED: 'onboarding_started',
      ONBOARDING_STEP_COMPLETED: 'onboarding_step_completed',
      ONBOARDING_COMPLETED: 'onboarding_completed',
      ONBOARDING_SKIPPED: 'onboarding_skipped',
      COACH_MARK_VIEWED: 'coach_mark_viewed',
      COACH_MARK_COMPLETED: 'coach_mark_completed',
      COACH_MARKS_SKIPPED: 'coach_marks_skipped',
      FIRST_MEMORY_CREATED: 'first_memory_created',
      FIRST_CONTACT_ADDED: 'first_contact_added',
      FEATURE_DISCOVERED: 'feature_discovered'
    };
    
    this.onboardingSteps = [
      'welcome',
      'features',
      'contacts',
      'gamification',
      'personalization',
      'permissions',
      'complete'
    ];
    
    this.coachMarks = [
      'add-memory',
      'contact-slot',
      'rewards',
      'search',
      'voice-avatar'
    ];
  }

  // Check if user is first time visitor
  isFirstTimeUser() {
    const completed = localStorage.getItem(this.storageKeys.onboardingCompleted);
    const skipped = localStorage.getItem(this.storageKeys.onboardingSkipped);
    return !completed && !skipped;
  }

  // Check if onboarding is completed
  isOnboardingCompleted() {
    return localStorage.getItem(this.storageKeys.onboardingCompleted) === 'true';
  }

  // Check if onboarding was skipped
  isOnboardingSkipped() {
    return localStorage.getItem(this.storageKeys.onboardingSkipped) === 'true';
  }

  // Get current onboarding step
  getCurrentStep() {
    const step = localStorage.getItem(this.storageKeys.onboardingStep);
    return step ? parseInt(step, 10) : 0;
  }

  // Save current step
  saveCurrentStep(stepIndex) {
    localStorage.setItem(this.storageKeys.onboardingStep, stepIndex.toString());
    this.trackEvent(this.analyticsEvents.ONBOARDING_STEP_COMPLETED, {
      step: this.onboardingSteps[stepIndex],
      stepIndex
    });
  }

  // Complete onboarding
  completeOnboarding(userData = {}) {
    const completionTime = new Date().toISOString();
    
    localStorage.setItem(this.storageKeys.onboardingCompleted, 'true');
    localStorage.setItem(this.storageKeys.completionTimestamp, completionTime);
    
    if (userData.userName) {
      localStorage.setItem(this.storageKeys.userName, userData.userName);
    }
    
    if (userData.preferences) {
      localStorage.setItem(this.storageKeys.userPreferences, JSON.stringify(userData.preferences));
    }
    
    // Remove step tracking
    localStorage.removeItem(this.storageKeys.onboardingStep);
    
    // Track completion
    this.trackEvent(this.analyticsEvents.ONBOARDING_COMPLETED, {
      completionTime,
      ...userData
    });
    
    // Calculate and store onboarding metrics
    this.calculateOnboardingMetrics();
  }

  // Skip onboarding
  skipOnboarding() {
    localStorage.setItem(this.storageKeys.onboardingSkipped, 'true');
    localStorage.removeItem(this.storageKeys.onboardingStep);
    
    this.trackEvent(this.analyticsEvents.ONBOARDING_SKIPPED, {
      stepSkippedAt: this.getCurrentStep(),
      timestamp: new Date().toISOString()
    });
  }

  // Get user preferences
  getUserPreferences() {
    const prefs = localStorage.getItem(this.storageKeys.userPreferences);
    return prefs ? JSON.parse(prefs) : {
      notifications: false,
      whatsapp: false,
      theme: 'light',
      frequency: 'daily'
    };
  }

  // Get user name
  getUserName() {
    return localStorage.getItem(this.storageKeys.userName) || '';
  }

  // Coach Marks Management
  getSeenCoachMarks() {
    const seen = localStorage.getItem(this.storageKeys.seenCoachMarks);
    return seen ? JSON.parse(seen) : [];
  }

  // Mark coach mark as seen
  markCoachMarkSeen(markId) {
    const seen = this.getSeenCoachMarks();
    if (!seen.includes(markId)) {
      seen.push(markId);
      localStorage.setItem(this.storageKeys.seenCoachMarks, JSON.stringify(seen));
      
      this.trackEvent(this.analyticsEvents.COACH_MARK_VIEWED, {
        markId,
        timestamp: new Date().toISOString()
      });
    }
  }

  // Complete all coach marks
  completeAllCoachMarks() {
    localStorage.setItem(this.storageKeys.seenCoachMarks, JSON.stringify(this.coachMarks));
    
    this.trackEvent(this.analyticsEvents.COACH_MARK_COMPLETED, {
      timestamp: new Date().toISOString()
    });
  }

  // Check if coach marks are disabled
  areCoachMarksDisabled() {
    return localStorage.getItem(this.storageKeys.coachMarksDisabled) === 'true';
  }

  // Disable coach marks
  disableCoachMarks() {
    localStorage.setItem(this.storageKeys.coachMarksDisabled, 'true');
    
    this.trackEvent(this.analyticsEvents.COACH_MARKS_SKIPPED, {
      timestamp: new Date().toISOString()
    });
  }

  // Enable coach marks
  enableCoachMarks() {
    localStorage.removeItem(this.storageKeys.coachMarksDisabled);
  }

  // First actions tracking
  trackFirstMemory() {
    if (!localStorage.getItem(this.storageKeys.firstMemoryCreated)) {
      localStorage.setItem(this.storageKeys.firstMemoryCreated, new Date().toISOString());
      
      this.trackEvent(this.analyticsEvents.FIRST_MEMORY_CREATED, {
        timestamp: new Date().toISOString()
      });
    }
  }

  trackFirstContact() {
    if (!localStorage.getItem(this.storageKeys.firstContactAdded)) {
      localStorage.setItem(this.storageKeys.firstContactAdded, new Date().toISOString());
      
      this.trackEvent(this.analyticsEvents.FIRST_CONTACT_ADDED, {
        timestamp: new Date().toISOString()
      });
    }
  }

  // Feature discovery tracking
  trackFeatureDiscovery(featureName) {
    this.trackEvent(this.analyticsEvents.FEATURE_DISCOVERED, {
      feature: featureName,
      timestamp: new Date().toISOString()
    });
  }

  // Analytics tracking
  trackEvent(eventName, data = {}) {
    // Get existing analytics
    const analytics = this.getAnalytics();
    
    // Add new event
    analytics.events.push({
      event: eventName,
      data,
      timestamp: new Date().toISOString()
    });
    
    // Update counts
    if (!analytics.eventCounts[eventName]) {
      analytics.eventCounts[eventName] = 0;
    }
    analytics.eventCounts[eventName]++;
    
    // Save analytics
    localStorage.setItem(this.storageKeys.onboardingAnalytics, JSON.stringify(analytics));
    
    // Send to analytics service if available
    if (window.gtag) {
      window.gtag('event', eventName, data);
    }
    
    // Console log for debugging
    console.log(`[Onboarding] ${eventName}`, data);
  }

  // Get analytics data
  getAnalytics() {
    const analytics = localStorage.getItem(this.storageKeys.onboardingAnalytics);
    return analytics ? JSON.parse(analytics) : {
      events: [],
      eventCounts: {},
      metrics: {}
    };
  }

  // Calculate onboarding metrics
  calculateOnboardingMetrics() {
    const analytics = this.getAnalytics();
    const startTime = analytics.events.find(e => e.event === this.analyticsEvents.ONBOARDING_STARTED)?.timestamp;
    const endTime = localStorage.getItem(this.storageKeys.completionTimestamp);
    
    if (startTime && endTime) {
      const duration = new Date(endTime) - new Date(startTime);
      analytics.metrics.completionTime = duration;
      analytics.metrics.completionRate = 100;
    }
    
    // Count steps completed
    const stepsCompleted = analytics.eventCounts[this.analyticsEvents.ONBOARDING_STEP_COMPLETED] || 0;
    analytics.metrics.stepsCompleted = stepsCompleted;
    analytics.metrics.stepCompletionRate = (stepsCompleted / this.onboardingSteps.length) * 100;
    
    // Save metrics
    localStorage.setItem(this.storageKeys.onboardingAnalytics, JSON.stringify(analytics));
  }

  // Get onboarding metrics
  getMetrics() {
    const analytics = this.getAnalytics();
    return analytics.metrics || {};
  }

  // Reset onboarding (for testing)
  resetOnboarding() {
    // Remove all onboarding-related keys
    Object.values(this.storageKeys).forEach(key => {
      localStorage.removeItem(key);
    });
    
    console.log('[Onboarding] Reset complete');
  }

  // Reset only coach marks
  resetCoachMarks() {
    localStorage.removeItem(this.storageKeys.seenCoachMarks);
    localStorage.removeItem(this.storageKeys.coachMarksDisabled);
    
    console.log('[Onboarding] Coach marks reset');
  }

  // Check if should show coach mark
  shouldShowCoachMark(markId) {
    if (this.areCoachMarksDisabled()) return false;
    if (!this.isOnboardingCompleted()) return false;
    
    const seenMarks = this.getSeenCoachMarks();
    return !seenMarks.includes(markId);
  }

  // Get next unseen coach mark
  getNextCoachMark() {
    if (this.areCoachMarksDisabled()) return null;
    if (!this.isOnboardingCompleted()) return null;
    
    const seenMarks = this.getSeenCoachMarks();
    return this.coachMarks.find(mark => !seenMarks.includes(mark));
  }

  // Get onboarding progress
  getProgress() {
    const currentStep = this.getCurrentStep();
    const totalSteps = this.onboardingSteps.length;
    return {
      currentStep,
      totalSteps,
      percentage: (currentStep / totalSteps) * 100,
      stepName: this.onboardingSteps[currentStep]
    };
  }

  // Check specific feature states
  hasCreatedFirstMemory() {
    return !!localStorage.getItem(this.storageKeys.firstMemoryCreated);
  }

  hasAddedFirstContact() {
    return !!localStorage.getItem(this.storageKeys.firstContactAdded);
  }

  // Export/Import user data (for migration)
  exportUserData() {
    const data = {};
    Object.entries(this.storageKeys).forEach(([key, storageKey]) => {
      const value = localStorage.getItem(storageKey);
      if (value) {
        data[key] = value;
      }
    });
    return data;
  }

  importUserData(data) {
    Object.entries(data).forEach(([key, value]) => {
      if (this.storageKeys[key]) {
        localStorage.setItem(this.storageKeys[key], value);
      }
    });
  }
}

// Create singleton instance
const onboardingService = new OnboardingService();

// Expose for debugging in console
if (typeof window !== 'undefined') {
  window.onboardingService = onboardingService;
}

export default onboardingService;