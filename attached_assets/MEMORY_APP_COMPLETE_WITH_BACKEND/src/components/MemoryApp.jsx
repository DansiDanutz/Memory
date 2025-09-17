import React, { useState } from 'react';
import { Search, MoreVertical, Phone, VideoIcon, Smile, Paperclip, Mic, Send, Settings, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import SyncIndicator from './SyncIndicator';
import WhatsAppIntegration from './WhatsAppIntegration';
import ThemeToggle from './ThemeToggle';
import './MemoryApp.css';

const MemoryApp = () => {
  const [currentView, setCurrentView] = useState('chat'); // 'chat', 'sync', 'integration'
  const [selectedMemory, setSelectedMemory] = useState({
    id: 1,
    name: 'Memo',
    subtitle: 'Personal AI Brain',
    lastMessage: 'Ready to help you capture and organize your memories',
    timestamp: 'online',
    unread: 0,
    avatar: 'M',
    online: true
  });
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: 'Hello! I\'m Memo, your Personal AI Brain. I can help you capture, store, and organize your memories, thoughts, and important information. What would you like to remember today?',
      timestamp: '2:25 PM'
    }
  ]);

  // Sample memory categories for the sidebar (recent conversations/topics)
  const memoryCategories = [
    {
      id: 1,
      name: 'Memo',
      subtitle: 'Personal AI Brain',
      lastMessage: 'Ready to help you capture and organize your memories',
      timestamp: 'online',
      unread: 0,
      avatar: 'M',
      online: true,
      isMain: true
    },
    {
      id: 2,
      name: 'Work Meeting Notes',
      lastMessage: 'Project deadline discussion from today',
      timestamp: '1:15 PM',
      unread: 0,
      avatar: 'W',
      online: false,
      category: 'work'
    },
    {
      id: 3,
      name: 'Personal Ideas',
      lastMessage: 'Weekend plans and creative thoughts',
      timestamp: '11:45 AM',
      unread: 0,
      avatar: 'P',
      online: false,
      category: 'personal'
    },
    {
      id: 4,
      name: 'Family Memories',
      lastMessage: 'Birthday celebration photos and notes',
      timestamp: 'Yesterday',
      unread: 0,
      avatar: 'F',
      online: false,
      category: 'family'
    },
    {
      id: 5,
      name: 'Learning Notes',
      lastMessage: 'Course materials and insights',
      timestamp: 'Yesterday',
      unread: 0,
      avatar: 'L',
      online: false,
      category: 'learning'
    }
  ];

  // Sample messages for selected memory
  const sampleMessages = [
    {
      id: 1,
      type: 'ai',
      content: 'Hello! I\'m your Memory Assistant. I can help you store, organize, and recall your memories. What would you like to remember today?',
      timestamp: '2:25 PM'
    },
    {
      id: 2,
      type: 'user',
      content: 'I want to save notes from my meeting with the marketing team',
      timestamp: '2:26 PM'
    },
    {
      id: 3,
      type: 'ai',
      content: 'Perfect! I\'ll help you capture those meeting notes. Please share the details and I\'ll organize them for easy retrieval later.',
      timestamp: '2:26 PM'
    }
  ];

  const handleSendMessage = () => {
    if (message.trim()) {
      const newMessage = {
        id: messages.length + 1,
        type: 'user',
        content: message,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages([...messages, newMessage]);
      setMessage('');
      
      // Simulate AI response
      setTimeout(() => {
        const aiResponse = {
          id: messages.length + 2,
          type: 'ai',
          content: 'I\'ve captured that memory. It\'s now safely stored and organized for future retrieval.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, aiResponse]);
      }, 1000);
    }
  };

  const handleMemorySelect = (memory) => {
    setSelectedMemory(memory);
    setMessages(sampleMessages);
  };

  return (
    <div className="memory-app">
      {/* Left Sidebar - Memory Categories */}
      <div className="sidebar">
        {/* Header */}
        <div className="sidebar-header">
          <div className="sidebar-title">
            <Avatar className="w-10 h-10">
              <AvatarImage src="/api/placeholder/40/40" />
              <AvatarFallback className="bg-primary text-primary-foreground">MA</AvatarFallback>
            </Avatar>
            <span className="font-semibold text-lg">Memory App</span>
          </div>
          <div className="sidebar-actions">
            <ThemeToggle />
            <Button 
              variant="ghost" 
              size="icon" 
              className={`text-muted-foreground hover:text-foreground ${currentView === 'integration' ? 'bg-accent' : ''}`}
              onClick={() => setCurrentView(currentView === 'integration' ? 'chat' : 'integration')}
              title="WhatsApp Integration"
            >
              <Smartphone className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
              <MoreVertical className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="search-container">
          <div className="search-bar">
            <Search className="w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Search memories..." 
              className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>
        </div>

        {/* Sync Indicator */}
        <div className="sync-indicator-container">
          <SyncIndicator isConnected={true} />
        </div>

        {/* Memory Categories List */}
        <div className="memory-list">
          {memoryCategories.map((memory) => (
            <div 
              key={memory.id}
              className={`memory-item ${selectedMemory?.id === memory.id ? 'selected' : ''}`}
              onClick={() => handleMemorySelect(memory)}
            >
              <div className="memory-avatar">
                <Avatar className="w-12 h-12">
                  <AvatarFallback className="bg-primary text-primary-foreground font-semibold">
                    {memory.avatar}
                  </AvatarFallback>
                </Avatar>
                {memory.online && <div className="online-indicator"></div>}
              </div>
              <div className="memory-info">
                <div className="memory-header">
                  <span className="memory-name">{memory.name}</span>
                  <span className="memory-time">{memory.timestamp}</span>
                </div>
                <div className="memory-preview">
                  <span className="last-message">
                    {memory.isMain && memory.subtitle ? memory.subtitle : memory.lastMessage}
                  </span>
                  {memory.unread > 0 && (
                    <span className="unread-badge">{memory.unread}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-area">
        {currentView === 'integration' ? (
          <div className="integration-view">
            <div className="integration-header">
              <h2 className="text-xl font-semibold">WhatsApp Integration</h2>
              <Button 
                variant="outline" 
                onClick={() => setCurrentView('chat')}
              >
                Back to Chat
              </Button>
            </div>
            <WhatsAppIntegration />
          </div>
        ) : selectedMemory ? (
          <>
            {/* Chat Header */}
            <div className="chat-header">
              <div className="chat-info">
                <Avatar className="w-10 h-10">
                  <AvatarFallback className="bg-primary text-primary-foreground">
                    {selectedMemory.avatar}
                  </AvatarFallback>
                </Avatar>
                <div className="chat-details">
                  <div className="chat-name-container">
                    <span className="chat-name">{selectedMemory.name}</span>
                    <Badge variant="outline" className="ml-2 bg-green-50 text-green-700 border-green-200 text-xs">
                      WhatsApp Synced
                    </Badge>
                  </div>
                  <span className="chat-status">
                    {selectedMemory.online ? 'Active now • Synced across platforms' : 'Last seen recently'}
                  </span>
                </div>
              </div>
              <div className="chat-actions">
                <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                  <Phone className="w-5 h-5" />
                </Button>
                <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                  <VideoIcon className="w-5 h-5" />
                </Button>
                <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                  <MoreVertical className="w-5 h-5" />
                </Button>
              </div>
            </div>

            {/* Messages Area */}
            <div className="messages-area">
              {messages.map((msg) => (
                <div key={msg.id} className={`message ${msg.type}`}>
                  <div className="message-bubble">
                    <span className="message-text">{msg.content}</span>
                    <span className="message-time">{msg.timestamp}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Input Area */}
            <div className="input-area">
              <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                <Smile className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                <Paperclip className="w-5 h-5" />
              </Button>
              <div className="message-input">
                <Input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Type a message..."
                  className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                />
              </div>
              <Button 
                onClick={handleSendMessage}
                size="icon" 
                className="bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                {message.trim() ? <Send className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </Button>
            </div>
          </>
        ) : (
          <div className="welcome-screen">
            <div className="welcome-content">
              <div className="welcome-icon">
                <Avatar className="w-24 h-24">
                  <AvatarFallback className="bg-primary text-primary-foreground text-2xl">
                    MA
                  </AvatarFallback>
                </Avatar>
              </div>
              <h2 className="welcome-title">Welcome to Memory App</h2>
              <p className="welcome-subtitle">
                Select a memory category to start capturing and organizing your thoughts, 
                ideas, and important moments.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MemoryApp;

