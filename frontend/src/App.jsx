import React, { useState, useEffect } from 'react';
import './App.css';
import WhatsAppMemoryApp from './components/WhatsAppMemoryApp';
import IntegrationTest from './components/IntegrationTest';
import OnboardingFlow from './components/OnboardingFlow';
import CoachMarks from './components/CoachMarks';
import { ThemeProvider } from './contexts/ThemeContext';
import onboardingService from './services/onboardingService';

function App() {
  const [showTest, setShowTest] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showCoachMarks, setShowCoachMarks] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    // Check if user needs onboarding
    const checkOnboardingStatus = () => {
      if (onboardingService.isFirstTimeUser()) {
        setShowOnboarding(true);
        setIsLoading(false);
      } else {
        setIsLoading(false);
        
        // Check if should show coach marks
        const nextMark = onboardingService.getNextCoachMark();
        if (nextMark && onboardingService.isOnboardingCompleted()) {
          // Delay coach marks slightly to let main app load
          setTimeout(() => {
            setShowCoachMarks(true);
          }, 2000);
        }
      }
    };
    
    checkOnboardingStatus();
  }, []);
  
  const handleOnboardingComplete = (userData) => {
    console.log('Onboarding completed:', userData);
    onboardingService.completeOnboarding(userData);
    setShowOnboarding(false);
    
    // Show coach marks after a delay
    setTimeout(() => {
      setShowCoachMarks(true);
    }, 1500);
  };
  
  const handleOnboardingSkip = () => {
    console.log('Onboarding skipped');
    onboardingService.skipOnboarding();
    setShowOnboarding(false);
  };
  
  const handleCoachMarksComplete = () => {
    console.log('Coach marks completed');
    onboardingService.completeAllCoachMarks();
    setShowCoachMarks(false);
  };
  
  const handleCoachMarksSkip = () => {
    console.log('Coach marks skipped');
    onboardingService.disableCoachMarks();
    setShowCoachMarks(false);
  };
  
  // Loading state
  if (isLoading) {
    return (
      <ThemeProvider>
        <div className="App" style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          height: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        }}>
          <div style={{ 
            color: 'white', 
            fontSize: '24px',
            animation: 'pulse 1.5s ease-in-out infinite'
          }}>
            Loading MemoApp...
          </div>
        </div>
      </ThemeProvider>
    );
  }
  
  return (
    <ThemeProvider>
      <div className="App">
        {/* Main App Content */}
        {!showOnboarding && (
          <>
            <button 
              onClick={() => setShowTest(!showTest)}
              style={{ 
                position: 'fixed', 
                top: 10, 
                right: 10, 
                zIndex: 9999,
                padding: '10px',
                background: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                cursor: 'pointer'
              }}
            >
              {showTest ? 'Hide Test' : 'Show Integration Test'}
            </button>
            
            {/* Debug buttons for testing */}
            {process.env.NODE_ENV === 'development' && (
              <div style={{
                position: 'fixed',
                bottom: 10,
                right: 10,
                zIndex: 9999,
                display: 'flex',
                flexDirection: 'column',
                gap: '5px'
              }}>
                <button
                  onClick={() => {
                    onboardingService.resetOnboarding();
                    window.location.reload();
                  }}
                  style={{
                    padding: '8px',
                    background: '#ff6b6b',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  Reset Onboarding
                </button>
                <button
                  onClick={() => {
                    onboardingService.resetCoachMarks();
                    setShowCoachMarks(true);
                  }}
                  style={{
                    padding: '8px',
                    background: '#4ecdc4',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  Show Coach Marks
                </button>
              </div>
            )}
            
            {showTest ? <IntegrationTest /> : <WhatsAppMemoryApp />}
          </>
        )}
        
        {/* Onboarding Flow */}
        {showOnboarding && (
          <OnboardingFlow 
            onComplete={handleOnboardingComplete}
            onSkip={handleOnboardingSkip}
          />
        )}
        
        {/* Coach Marks */}
        {showCoachMarks && !showOnboarding && (
          <CoachMarks
            onComplete={handleCoachMarksComplete}
            onSkip={handleCoachMarksSkip}
          />
        )}
      </div>
    </ThemeProvider>
  );
}

export default App;