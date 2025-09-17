import React, { useState, useEffect } from 'react';
import SignupPage from './components/SignupPage';
import LoginPage from './components/LoginPage';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('login'); // 'login', 'signup', 'chat'
  const [user, setUser] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);

  useEffect(() => {
    // Check if user is already logged in
    const savedUser = localStorage.getItem('memory_user');
    const savedToken = localStorage.getItem('memory_session_token');
    
    if (savedUser && savedToken) {
      setUser(JSON.parse(savedUser));
      setSessionToken(savedToken);
      setCurrentView('chat');
    }
  }, []);

  const handleSignupSuccess = (userData) => {
    setUser(userData);
    localStorage.setItem('memory_user', JSON.stringify(userData));
    setCurrentView('login'); // Redirect to login after successful signup
  };

  const handleLoginSuccess = (userData, token) => {
    setUser(userData);
    setSessionToken(token);
    localStorage.setItem('memory_user', JSON.stringify(userData));
    localStorage.setItem('memory_session_token', token);
    setCurrentView('chat');
  };

  const handleLogout = () => {
    setUser(null);
    setSessionToken(null);
    localStorage.removeItem('memory_user');
    localStorage.removeItem('memory_session_token');
    setCurrentView('login');
    
    // Call logout API
    fetch('http://localhost:5000/api/logout', {
      method: 'POST',
      credentials: 'include'
    }).catch(err => console.error('Logout error:', err));
  };

  const switchToSignup = () => {
    setCurrentView('signup');
  };

  const switchToLogin = () => {
    setCurrentView('login');
  };

  // Render based on current view
  if (currentView === 'signup') {
    return (
      <SignupPage 
        onSignupSuccess={handleSignupSuccess}
        onSwitchToLogin={switchToLogin}
      />
    );
  }

  if (currentView === 'login') {
    return (
      <LoginPage 
        onLoginSuccess={handleLoginSuccess}
        onSwitchToSignup={switchToSignup}
      />
    );
  }

  if (currentView === 'chat' && user) {
    return (
      <ChatInterface 
        user={user}
        sessionToken={sessionToken}
        onLogout={handleLogout}
      />
    );
  }

  // Default fallback
  return (
    <LoginPage 
      onLoginSuccess={handleLoginSuccess}
      onSwitchToSignup={switchToSignup}
    />
  );
}

export default App;
