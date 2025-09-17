# 🚀 Replit Implementation Code - Memory App Design

**Complete WhatsApp-like Interface with Professional Dark Neon Theme**

---

## 📋 Quick Setup for Replit

### 1. **Create New React App in Replit**
```bash
# In Replit terminal
npx create-react-app memo-app
cd memo-app
npm install lucide-react crypto-js
```

### 2. **Replace Files with Code Below**

---

## 📱 **Main App Component**

### `src/App.js`
```jsx
import React, { useState, useEffect } from 'react';
import './App.css';
import MemoryApp from './components/MemoryApp';
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  return (
    <ThemeProvider>
      <div className="App">
        <MemoryApp />
      </div>
    </ThemeProvider>
  );
}

export default App;
```

---

## 🎨 **Main Styling**

### `src/App.css`
```css
/* Memory App - Professional Dark Neon Theme */
:root {
  /* Light Theme - Photosynthesis Green */
  --primary-green: #2ECC40;
  --primary-green-dark: #1B8B2B;
  --primary-green-light: #D4F4DD;
  --background-light: #f0f2f5;
  --surface-light: #ffffff;
  --text-light: #111b21;
  --text-secondary-light: #667781;
  --border-light: #e9edef;
  
  /* Dark Theme - Professional Neon */
  --dark-bg-primary: #0D1117;
  --dark-bg-secondary: #161B22;
  --dark-bg-tertiary: #21262D;
  --dark-surface: #30363D;
  --dark-text-primary: #E6EDF3;
  --dark-text-secondary: #8B949E;
  --dark-border: #30363D;
  --neon-green: #39FF14;
  --neon-cyan: #00D9FF;
  --neon-purple: #BF40BF;
  --neon-glow: rgba(57, 255, 20, 0.3);
  
  /* Common */
  --border-radius: 8px;
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  --transition: all 0.3s ease;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: var(--background-light);
  color: var(--text-light);
  transition: var(--transition);
}

/* Dark Theme */
[data-theme="dark"] {
  --background-light: var(--dark-bg-primary);
  --surface-light: var(--dark-bg-secondary);
  --text-light: var(--dark-text-primary);
  --text-secondary-light: var(--dark-text-secondary);
  --border-light: var(--dark-border);
}

[data-theme="dark"] body {
  background: var(--dark-bg-primary);
  color: var(--dark-text-primary);
}

.App {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: var(--background-light);
}

::-webkit-scrollbar-thumb {
  background: var(--primary-green);
  border-radius: 3px;
}

[data-theme="dark"] ::-webkit-scrollbar-thumb {
  background: var(--neon-green);
  box-shadow: 0 0 10px var(--neon-glow);
}

/* Animations */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes glow {
  0%, 100% { 
    box-shadow: 0 0 5px var(--neon-green);
  }
  50% { 
    box-shadow: 0 0 20px var(--neon-green), 0 0 30px var(--neon-green);
  }
}

.pulse {
  animation: pulse 2s infinite;
}

.glow {
  animation: glow 2s infinite;
}

/* Responsive Design */
@media (max-width: 768px) {
  .App {
    height: 100vh;
    height: 100dvh; /* Dynamic viewport height for mobile */
  }
}
```

---

## 🧠 **Memory App Main Component**

### `src/components/MemoryApp.js`
```jsx
import React, { useState, useContext } from 'react';
import { 
  Search, 
  MoreVertical, 
  Phone, 
  Video, 
  Settings,
  Moon,
  Sun,
  Wifi,
  WifiOff,
  MessageCircle,
  Brain,
  Smartphone,
  Sync
} from 'lucide-react';
import { ThemeContext } from '../contexts/ThemeContext';
import './MemoryApp.css';

const MemoryApp = () => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  const [selectedMemory, setSelectedMemory] = useState('memo');
  const [searchQuery, setSearchQuery] = useState('');
  const [isOnline, setIsOnline] = useState(true);
  const [view, setView] = useState('chat'); // 'chat' or 'integration'

  const memories = [
    {
      id: 'memo',
      name: 'Memo',
      subtitle: 'Personal AI Brain',
      lastMessage: 'Ready to help you remember everything...',
      time: 'now',
      unread: 0,
      avatar: '🧠',
      isActive: true,
      syncStatus: 'synced'
    },
    {
      id: 'work',
      name: 'Work Memories',
      subtitle: 'Professional notes & meetings',
      lastMessage: 'Meeting with marketing team scheduled',
      time: '2:30 PM',
      unread: 3,
      avatar: '💼',
      syncStatus: 'syncing'
    },
    {
      id: 'personal',
      name: 'Personal Life',
      subtitle: 'Family, friends & personal notes',
      lastMessage: 'Remember to call mom on Sunday',
      time: '1:45 PM',
      unread: 1,
      avatar: '🏠',
      syncStatus: 'synced'
    },
    {
      id: 'health',
      name: 'Health & Fitness',
      subtitle: 'Medical appointments & wellness',
      lastMessage: 'Doctor appointment next Tuesday',
      time: '12:15 PM',
      unread: 0,
      avatar: '🏥',
      syncStatus: 'synced'
    },
    {
      id: 'learning',
      name: 'Learning & Growth',
      subtitle: 'Courses, books & knowledge',
      lastMessage: 'Finished chapter 5 of React course',
      time: '11:30 AM',
      unread: 2,
      avatar: '📚',
      syncStatus: 'synced'
    },
    {
      id: 'travel',
      name: 'Travel Plans',
      subtitle: 'Trips, bookings & itineraries',
      lastMessage: 'Flight confirmation for Paris trip',
      time: 'Yesterday',
      unread: 0,
      avatar: '✈️',
      syncStatus: 'synced'
    }
  ];

  const currentMemory = memories.find(m => m.id === selectedMemory);

  const getSyncIcon = (status) => {
    switch (status) {
      case 'syncing':
        return <Sync className="w-3 h-3 animate-spin text-yellow-500" />;
      case 'synced':
        return <Wifi className="w-3 h-3 text-green-500" />;
      case 'offline':
        return <WifiOff className="w-3 h-3 text-red-500" />;
      default:
        return <Wifi className="w-3 h-3 text-green-500" />;
    }
  };

  return (
    <div className="memory-app" data-theme={theme}>
      <div className="app-container">
        {/* Sidebar */}
        <div className="sidebar">
          {/* Sidebar Header */}
          <div className="sidebar-header">
            <div className="header-left">
              <div className="app-title">
                <Brain className="w-6 h-6 text-primary" />
                <span>Memo</span>
              </div>
            </div>
            <div className="header-actions">
              <button 
                className="action-btn"
                onClick={() => setView(view === 'chat' ? 'integration' : 'chat')}
                title="WhatsApp Integration"
              >
                <Smartphone className="w-5 h-5" />
              </button>
              <button 
                className="action-btn"
                onClick={toggleTheme}
                title="Toggle Theme"
              >
                {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
              <button className="action-btn" title="Settings">
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Sync Status */}
          <div className="sync-status">
            <div className="sync-indicator">
              <span className="sync-text">Memo App ⟷ WhatsApp</span>
              <div className="sync-status-dot synced"></div>
            </div>
          </div>

          {/* Search Bar */}
          <div className="search-container">
            <div className="search-bar">
              <Search className="w-4 h-4 text-secondary" />
              <input
                type="text"
                placeholder="Search memories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
            </div>
          </div>

          {/* Memory List */}
          <div className="memory-list">
            {memories
              .filter(memory => 
                memory.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                memory.subtitle.toLowerCase().includes(searchQuery.toLowerCase())
              )
              .map((memory) => (
                <div
                  key={memory.id}
                  className={`memory-item ${selectedMemory === memory.id ? 'active' : ''}`}
                  onClick={() => setSelectedMemory(memory.id)}
                >
                  <div className="memory-avatar">
                    <span className="avatar-emoji">{memory.avatar}</span>
                    <div className="sync-badge">
                      {getSyncIcon(memory.syncStatus)}
                    </div>
                  </div>
                  <div className="memory-content">
                    <div className="memory-header">
                      <h3 className="memory-name">{memory.name}</h3>
                      <span className="memory-time">{memory.time}</span>
                    </div>
                    <div className="memory-preview">
                      <p className="memory-subtitle">{memory.subtitle}</p>
                      {memory.unread > 0 && (
                        <span className="unread-badge">{memory.unread}</span>
                      )}
                    </div>
                    <p className="memory-last-message">{memory.lastMessage}</p>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="main-content">
          {view === 'chat' ? (
            <>
              {/* Chat Header */}
              <div className="chat-header">
                <div className="chat-info">
                  <div className="chat-avatar">
                    <span className="avatar-emoji">{currentMemory?.avatar}</span>
                  </div>
                  <div className="chat-details">
                    <h2 className="chat-name">{currentMemory?.name}</h2>
                    <div className="chat-status">
                      <span className="status-text">{currentMemory?.subtitle}</span>
                      {currentMemory?.id === 'memo' && (
                        <span className="whatsapp-badge">WhatsApp Synced</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="chat-actions">
                  <button className="action-btn" title="Voice Call">
                    <Phone className="w-5 h-5" />
                  </button>
                  <button className="action-btn" title="Video Call">
                    <Video className="w-5 h-5" />
                  </button>
                  <button className="action-btn" title="More Options">
                    <MoreVertical className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="chat-messages">
                <div className="welcome-message">
                  <div className="welcome-content">
                    <Brain className="w-12 h-12 text-primary mb-4" />
                    <h3>Welcome to Memo - Your Personal AI Brain</h3>
                    <p>I'm here to help you remember everything important. Start a conversation and I'll intelligently organize your memories.</p>
                    <div className="features-grid">
                      <div className="feature-item">
                        <MessageCircle className="w-5 h-5 text-primary" />
                        <span>Smart Conversations</span>
                      </div>
                      <div className="feature-item">
                        <Sync className="w-5 h-5 text-primary" />
                        <span>WhatsApp Sync</span>
                      </div>
                      <div className="feature-item">
                        <Brain className="w-5 h-5 text-primary" />
                        <span>AI Memory</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Message Input */}
              <div className="message-input-container">
                <div className="message-input">
                  <input
                    type="text"
                    placeholder="Type a message to Memo..."
                    className="message-text-input"
                  />
                  <button className="send-button">
                    <MessageCircle className="w-5 h-5" />
                  </button>
                </div>
                <p className="sync-status-text">Synced across platforms</p>
              </div>
            </>
          ) : (
            /* WhatsApp Integration View */
            <div className="integration-view">
              <div className="integration-header">
                <button 
                  className="back-button"
                  onClick={() => setView('chat')}
                >
                  ← Back to Chat
                </button>
                <h2>WhatsApp Integration</h2>
              </div>
              
              <div className="integration-content">
                <div className="sync-status-card">
                  <div className="status-header">
                    <Smartphone className="w-8 h-8 text-primary" />
                    <div>
                      <h3>Synchronization Status</h3>
                      <p className="status-connected">Connected & Syncing</p>
                    </div>
                  </div>
                  
                  <div className="sync-features">
                    <div className="feature-row">
                      <Wifi className="w-5 h-5 text-green-500" />
                      <span>Message Sync</span>
                      <span className="feature-status active">Active</span>
                    </div>
                    <div className="feature-row">
                      <Phone className="w-5 h-5 text-green-500" />
                      <span>Voice Calls</span>
                      <span className="feature-status active">Active</span>
                    </div>
                    <div className="feature-row">
                      <Video className="w-5 h-5 text-green-500" />
                      <span>Video Calls</span>
                      <span className="feature-status active">Active</span>
                    </div>
                  </div>
                </div>

                <div className="activity-feed">
                  <h4>Recent Cross-Platform Activity</h4>
                  <div className="activity-list">
                    <div className="activity-item">
                      <div className="activity-icon whatsapp">📱</div>
                      <div className="activity-content">
                        <p><strong>WhatsApp:</strong> Memory saved: "Meeting notes from marketing team"</p>
                        <span className="activity-time">2:30 PM</span>
                      </div>
                    </div>
                    <div className="activity-item">
                      <div className="activity-icon memo">🧠</div>
                      <div className="activity-content">
                        <p><strong>Memo App:</strong> Voice memo recorded and transcribed</p>
                        <span className="activity-time">2:15 PM</span>
                      </div>
                    </div>
                    <div className="activity-item">
                      <div className="activity-icon whatsapp">📱</div>
                      <div className="activity-content">
                        <p><strong>WhatsApp:</strong> Retrieved family birthday memories</p>
                        <span className="activity-time">1:45 PM</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MemoryApp;
```

---

## 🎨 **Memory App Styling**

### `src/components/MemoryApp.css`
```css
/* Memory App Component Styles */
.memory-app {
  height: 100vh;
  background: var(--background-light);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-container {
  display: flex;
  height: 100%;
  max-width: 1400px;
  margin: 0 auto;
  box-shadow: var(--shadow);
}

/* Sidebar Styles */
.sidebar {
  width: 350px;
  background: var(--surface-light);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  transition: var(--transition);
}

[data-theme="dark"] .sidebar {
  background: var(--dark-bg-secondary);
  border-right-color: var(--dark-border);
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface-light);
}

[data-theme="dark"] .sidebar-header {
  background: var(--dark-bg-secondary);
  border-bottom-color: var(--dark-border);
}

.app-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 18px;
  color: var(--text-light);
}

.app-title .w-6 {
  color: var(--primary-green);
}

[data-theme="dark"] .app-title .w-6 {
  color: var(--neon-green);
  filter: drop-shadow(0 0 8px var(--neon-glow));
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px;
  border: none;
  background: transparent;
  border-radius: var(--border-radius);
  cursor: pointer;
  color: var(--text-secondary-light);
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: var(--primary-green-light);
  color: var(--primary-green-dark);
}

[data-theme="dark"] .action-btn:hover {
  background: var(--dark-surface);
  color: var(--neon-green);
  box-shadow: 0 0 10px var(--neon-glow);
}

/* Sync Status */
.sync-status {
  padding: 12px 16px;
  background: var(--primary-green-light);
  border-bottom: 1px solid var(--border-light);
}

[data-theme="dark"] .sync-status {
  background: var(--dark-bg-tertiary);
  border-bottom-color: var(--dark-border);
}

.sync-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary-light);
}

[data-theme="dark"] .sync-indicator {
  color: var(--neon-green);
}

.sync-text {
  font-weight: 500;
}

.sync-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary-green);
}

.sync-status-dot.synced {
  background: #10b981;
  animation: pulse 2s infinite;
}

[data-theme="dark"] .sync-status-dot.synced {
  background: var(--neon-green);
  box-shadow: 0 0 10px var(--neon-glow);
}

/* Search Bar */
.search-container {
  padding: 16px;
  border-bottom: 1px solid var(--border-light);
}

[data-theme="dark"] .search-container {
  border-bottom-color: var(--dark-border);
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--background-light);
  border-radius: 20px;
  border: 1px solid var(--border-light);
  transition: var(--transition);
}

[data-theme="dark"] .search-bar {
  background: var(--dark-bg-primary);
  border-color: var(--dark-border);
}

.search-bar:focus-within {
  border-color: var(--primary-green);
}

[data-theme="dark"] .search-bar:focus-within {
  border-color: var(--neon-green);
  box-shadow: 0 0 10px var(--neon-glow);
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  color: var(--text-light);
  font-size: 14px;
}

.search-input::placeholder {
  color: var(--text-secondary-light);
}

/* Memory List */
.memory-list {
  flex: 1;
  overflow-y: auto;
}

.memory-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-light);
  transition: var(--transition);
  position: relative;
}

[data-theme="dark"] .memory-item {
  border-bottom-color: var(--dark-border);
}

.memory-item:hover {
  background: var(--primary-green-light);
}

[data-theme="dark"] .memory-item:hover {
  background: var(--dark-surface);
}

.memory-item.active {
  background: var(--primary-green-light);
  border-right: 3px solid var(--primary-green);
}

[data-theme="dark"] .memory-item.active {
  background: var(--dark-surface);
  border-right-color: var(--neon-green);
  box-shadow: inset 0 0 20px var(--neon-glow);
}

.memory-avatar {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--background-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: 2px solid var(--border-light);
}

[data-theme="dark"] .memory-avatar {
  background: var(--dark-bg-primary);
  border-color: var(--dark-border);
}

.sync-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  background: var(--surface-light);
  border-radius: 50%;
  padding: 2px;
  border: 1px solid var(--border-light);
}

[data-theme="dark"] .sync-badge {
  background: var(--dark-bg-secondary);
  border-color: var(--dark-border);
}

.memory-content {
  flex: 1;
  min-width: 0;
}

.memory-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.memory-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-light);
  margin: 0;
}

.memory-time {
  font-size: 12px;
  color: var(--text-secondary-light);
}

.memory-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.memory-subtitle {
  font-size: 12px;
  color: var(--text-secondary-light);
  margin: 0;
}

.unread-badge {
  background: var(--primary-green);
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

[data-theme="dark"] .unread-badge {
  background: var(--neon-green);
  color: var(--dark-bg-primary);
  box-shadow: 0 0 10px var(--neon-glow);
}

.memory-last-message {
  font-size: 13px;
  color: var(--text-secondary-light);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--background-light);
}

[data-theme="dark"] .main-content {
  background: var(--dark-bg-primary);
}

/* Chat Header */
.chat-header {
  padding: 16px 24px;
  background: var(--surface-light);
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

[data-theme="dark"] .chat-header {
  background: var(--dark-bg-secondary);
  border-bottom-color: var(--dark-border);
}

.chat-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--background-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  border: 2px solid var(--border-light);
}

[data-theme="dark"] .chat-avatar {
  background: var(--dark-bg-primary);
  border-color: var(--dark-border);
}

.chat-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-light);
  margin: 0 0 4px 0;
}

.chat-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-text {
  font-size: 13px;
  color: var(--text-secondary-light);
}

.whatsapp-badge {
  background: var(--primary-green);
  color: white;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 8px;
}

[data-theme="dark"] .whatsapp-badge {
  background: var(--neon-green);
  color: var(--dark-bg-primary);
  box-shadow: 0 0 8px var(--neon-glow);
}

.chat-actions {
  display: flex;
  gap: 8px;
}

/* Chat Messages */
.chat-messages {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-message {
  text-align: center;
  max-width: 500px;
}

.welcome-content h3 {
  font-size: 24px;
  color: var(--text-light);
  margin-bottom: 12px;
}

.welcome-content p {
  font-size: 16px;
  color: var(--text-secondary-light);
  margin-bottom: 24px;
  line-height: 1.5;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--surface-light);
  border-radius: var(--border-radius);
  border: 1px solid var(--border-light);
}

[data-theme="dark"] .feature-item {
  background: var(--dark-bg-secondary);
  border-color: var(--dark-border);
}

.feature-item span {
  font-size: 14px;
  color: var(--text-light);
}

/* Message Input */
.message-input-container {
  padding: 16px 24px;
  background: var(--surface-light);
  border-top: 1px solid var(--border-light);
}

[data-theme="dark"] .message-input-container {
  background: var(--dark-bg-secondary);
  border-top-color: var(--dark-border);
}

.message-input {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--background-light);
  border-radius: 24px;
  border: 1px solid var(--border-light);
  margin-bottom: 8px;
}

[data-theme="dark"] .message-input {
  background: var(--dark-bg-primary);
  border-color: var(--dark-border);
}

.message-text-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  color: var(--text-light);
  font-size: 14px;
}

.message-text-input::placeholder {
  color: var(--text-secondary-light);
}

.send-button {
  padding: 8px;
  border: none;
  background: var(--primary-green);
  color: white;
  border-radius: 50%;
  cursor: pointer;
  transition: var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
}

[data-theme="dark"] .send-button {
  background: var(--neon-green);
  color: var(--dark-bg-primary);
  box-shadow: 0 0 15px var(--neon-glow);
}

.send-button:hover {
  transform: scale(1.05);
}

.sync-status-text {
  text-align: center;
  font-size: 12px;
  color: var(--text-secondary-light);
  margin: 0;
}

[data-theme="dark"] .sync-status-text {
  color: var(--neon-green);
}

/* Integration View */
.integration-view {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.back-button {
  padding: 8px 16px;
  border: 1px solid var(--border-light);
  background: var(--surface-light);
  color: var(--text-light);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: var(--transition);
}

[data-theme="dark"] .back-button {
  border-color: var(--dark-border);
  background: var(--dark-bg-secondary);
  color: var(--dark-text-primary);
}

.back-button:hover {
  background: var(--primary-green-light);
}

[data-theme="dark"] .back-button:hover {
  background: var(--dark-surface);
  border-color: var(--neon-green);
}

.integration-header h2 {
  font-size: 24px;
  color: var(--text-light);
  margin: 0;
}

.sync-status-card {
  background: var(--surface-light);
  border: 1px solid var(--border-light);
  border-radius: var(--border-radius);
  padding: 24px;
  margin-bottom: 24px;
}

[data-theme="dark"] .sync-status-card {
  background: var(--dark-bg-secondary);
  border-color: var(--dark-border);
}

.status-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.status-header h3 {
  font-size: 18px;
  color: var(--text-light);
  margin: 0 0 4px 0;
}

.status-connected {
  font-size: 14px;
  color: #10b981;
  font-weight: 600;
}

[data-theme="dark"] .status-connected {
  color: var(--neon-green);
}

.sync-features {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--background-light);
  border-radius: var(--border-radius);
}

[data-theme="dark"] .feature-row {
  background: var(--dark-bg-primary);
}

.feature-row span:first-of-type {
  flex: 1;
  color: var(--text-light);
}

.feature-status {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 12px;
}

.feature-status.active {
  background: #dcfce7;
  color: #166534;
}

[data-theme="dark"] .feature-status.active {
  background: var(--neon-green);
  color: var(--dark-bg-primary);
}

.activity-feed {
  background: var(--surface-light);
  border: 1px solid var(--border-light);
  border-radius: var(--border-radius);
  padding: 24px;
}

[data-theme="dark"] .activity-feed {
  background: var(--dark-bg-secondary);
  border-color: var(--dark-border);
}

.activity-feed h4 {
  font-size: 16px;
  color: var(--text-light);
  margin: 0 0 16px 0;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: var(--background-light);
  border-radius: var(--border-radius);
}

[data-theme="dark"] .activity-item {
  background: var(--dark-bg-primary);
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.activity-icon.whatsapp {
  background: #25d366;
}

.activity-icon.memo {
  background: var(--primary-green);
}

[data-theme="dark"] .activity-icon.memo {
  background: var(--neon-green);
}

.activity-content {
  flex: 1;
}

.activity-content p {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: var(--text-light);
}

.activity-time {
  font-size: 12px;
  color: var(--text-secondary-light);
}

/* Responsive Design */
@media (max-width: 768px) {
  .app-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    height: 40%;
  }
  
  .main-content {
    height: 60%;
  }
  
  .memory-item {
    padding: 12px 16px;
  }
  
  .chat-header {
    padding: 12px 16px;
  }
  
  .chat-messages {
    padding: 16px;
  }
  
  .message-input-container {
    padding: 12px 16px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    height: 50%;
  }
  
  .main-content {
    height: 50%;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .welcome-content h3 {
    font-size: 20px;
  }
  
  .welcome-content p {
    font-size: 14px;
  }
}
```

---

## 🎯 **Theme Context**

### `src/contexts/ThemeContext.js`
```jsx
import React, { createContext, useState, useEffect } from 'react';

export const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    const savedTheme = localStorage.getItem('memo-theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('memo-theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
```

---

## 📱 **Package.json Dependencies**

### `package.json` (add these dependencies)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.294.0",
    "crypto-js": "^4.2.0"
  }
}
```

---

## 🚀 **Replit Setup Instructions**

### 1. **Create New Replit Project**
```bash
# Choose "React" template in Replit
# Or create blank and run:
npx create-react-app .
```

### 2. **Install Dependencies**
```bash
npm install lucide-react crypto-js
```

### 3. **Create Directory Structure**
```
src/
├── components/
│   └── MemoryApp.js
│   └── MemoryApp.css
├── contexts/
│   └── ThemeContext.js
├── App.js
├── App.css
└── index.js
```

### 4. **Replace Files**
- Copy all the code above into respective files
- Make sure to create the `components` and `contexts` folders

### 5. **Run the Application**
```bash
npm start
```

---

## 🎨 **Features Included**

### ✅ **WhatsApp-like Interface**
- Familiar sidebar with memory categories
- Chat-style main interface
- Real-time sync indicators
- Professional message layout

### ✅ **Professional Dark Neon Theme**
- Sophisticated dark backgrounds
- Subtle neon green accents
- Professional appearance (not flashy)
- Smooth theme switching

### ✅ **Mobile Responsive**
- Touch-friendly interface
- Responsive breakpoints
- Mobile-optimized navigation
- Professional mobile experience

### ✅ **Interactive Features**
- Theme toggle (light/dark)
- WhatsApp integration view
- Real-time sync status
- Smooth animations and transitions

---

## 🔧 **Customization Options**

### **Colors (in App.css)**
```css
/* Change primary colors */
--primary-green: #2ECC40;        /* Main green */
--neon-green: #39FF14;           /* Dark theme accent */
--neon-cyan: #00D9FF;            /* Secondary accent */
```

### **Layout (in MemoryApp.css)**
```css
/* Adjust sidebar width */
.sidebar {
  width: 350px; /* Change this value */
}

/* Modify spacing */
.memory-item {
  padding: 16px; /* Adjust padding */
}
```

---

**🚀 This code is ready for immediate deployment in Replit! Just copy the files and run `npm start` to see the complete WhatsApp-like interface with professional dark neon theme.**

