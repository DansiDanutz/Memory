import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { MemoryProvider } from './contexts/MemoryContext';
import { SyncProvider } from './contexts/SyncContext';
import { VoiceProvider } from './contexts/VoiceContext';
import { NotificationProvider } from './contexts/NotificationContext';

// Pages
import WelcomePage from './pages/WelcomePage';
import ChatPage from './pages/ChatPage';
import SettingsPage from './pages/SettingsPage';
import SearchPage from './pages/SearchPage';
import VoicePage from './pages/VoicePage';
import SyncPage from './pages/SyncPage';
import ProfilePage from './pages/ProfilePage';

// Components
import Layout from './components/layout/Layout';
import LoadingScreen from './components/ui/LoadingScreen';
import ErrorBoundary from './components/ui/ErrorBoundary';
import NotificationContainer from './components/ui/NotificationContainer';

// Hooks
import { useLocalStorage } from './hooks/useLocalStorage';

// Utils
import { initializeApp } from './utils/initialization';

import './App.css';

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useLocalStorage('hasCompletedOnboarding', false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const initApp = async () => {
      try {
        setIsLoading(true);
        
        // Initialize app services
        await initializeApp();
        
        // Simulate loading time for better UX
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        setIsInitialized(true);
      } catch (err) {
        console.error('Failed to initialize app:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    initApp();
  }, []);

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-destructive mb-4">
            Failed to Initialize App
          </h1>
          <p className="text-muted-foreground mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <MemoryProvider>
          <SyncProvider>
            <VoiceProvider>
              <NotificationProvider>
                <Router>
                  <div className="memory-app">
                    <Routes>
                      {/* Welcome/Onboarding Route */}
                      <Route 
                        path="/welcome" 
                        element={
                          hasCompletedOnboarding ? 
                            <Navigate to="/chat" replace /> : 
                            <WelcomePage onComplete={() => setHasCompletedOnboarding(true)} />
                        } 
                      />
                      
                      {/* Main App Routes */}
                      <Route path="/" element={<Layout />}>
                        <Route 
                          index 
                          element={
                            hasCompletedOnboarding ? 
                              <Navigate to="/chat" replace /> : 
                              <Navigate to="/welcome" replace />
                          } 
                        />
                        <Route path="chat" element={<ChatPage />} />
                        <Route path="chat/:categoryId" element={<ChatPage />} />
                        <Route path="search" element={<SearchPage />} />
                        <Route path="voice" element={<VoicePage />} />
                        <Route path="sync" element={<SyncPage />} />
                        <Route path="settings" element={<SettingsPage />} />
                        <Route path="profile" element={<ProfilePage />} />
                      </Route>
                      
                      {/* Catch-all redirect */}
                      <Route 
                        path="*" 
                        element={
                          hasCompletedOnboarding ? 
                            <Navigate to="/chat" replace /> : 
                            <Navigate to="/welcome" replace />
                        } 
                      />
                    </Routes>
                    
                    {/* Global Notification Container */}
                    <NotificationContainer />
                  </div>
                </Router>
              </NotificationProvider>
            </VoiceProvider>
          </SyncProvider>
        </MemoryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;

