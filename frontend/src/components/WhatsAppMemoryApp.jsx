import React, { useState, useContext, useEffect, useCallback, useRef } from 'react';
import { 
  Search, MoreVertical, Phone, Video, Settings, Moon, Sun,
  MessageCircle, Brain, Smartphone, RefreshCw, Send, AlertCircle, 
  Loader, Plus, X, Trophy, Star, Gift, Crown, Zap, Sparkles,
  Check, CheckCheck, Volume2, Mic, Play, Pause, Download,
  Archive, Pin, VolumeX, Info, Edit, Trash2, Camera, Paperclip,
  Smile, ArrowLeft, Menu, Bell, Lock
} from 'lucide-react';
import { ThemeContext } from '../contexts/ThemeContext';
import { memoryService, claudeService, wsService, gamificationService } from '../services';
import whatsappService from '../services/whatsappService';
import '../styles/whatsapp-theme.css';
import './WhatsAppMemoryApp.css';
import './locked-slot-styles.css';
import ContactCardsGrid from './ContactCardsGrid';

const WhatsAppMemoryApp = () => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  
  // Core state
  const [selectedChat, setSelectedChat] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [view, setView] = useState('chats'); // 'chats', 'memory', 'rewards'
  const [messages, setMessages] = useState({});
  const [messageInput, setMessageInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [wsConnected, setWsConnected] = useState(false);
  
  // Chat data
  const [chats, setChats] = useState([]);
  const [contactSlots, setContactSlots] = useState([
    ...Array(5).fill(null).map((_, index) => ({
      id: `slot_${index}`,
      isEmpty: true,
      canChange: true,
      contact: null,
      transcripts: [],
      memoryCategories: {}
    })),
    // Sixth premium slot - simple lock and text only
    {
      id: 'slot_premium',
      isEmpty: true,
      isPremium: true,
      canChange: false,
      contact: null,
      transcripts: [],
      memoryCategories: {}
    }
  ]);
  const [memories, setMemories] = useState([]);
  const [userStats, setUserStats] = useState({
    level: 1,
    points: 0,
    streak: 0,
    achievements: 0,
    voiceCredits: 0
  });
  
  // UI state
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showChatInfo, setShowChatInfo] = useState(false);
  const [showNotifications, setShowNotifications] = useState([]);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [showSidebar, setShowSidebar] = useState(!isMobile);
  
  // Contact selection state
  const [showContactSelector, setShowContactSelector] = useState(false);
  const [selectedSlotId, setSelectedSlotId] = useState(null);
  const [selectedContact, setSelectedContact] = useState(null);
  const [showChangeWarning, setShowChangeWarning] = useState(false);
  const [showImportPermission, setShowImportPermission] = useState(false);
  const [whatsappContacts, setWhatsappContacts] = useState([]);
  
  // Refs
  const messageInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  
  // User ID
  const userId = localStorage.getItem('userId') || 'default_user';

  // Mock chat data - similar to WhatsApp
  useEffect(() => {
    const mockChats = [
      {
        id: 'memo_ai',
        name: 'Memo AI Assistant',
        avatar: '🧠',
        lastMessage: 'I\'m here to help with your memories!',
        time: 'now',
        unread: 0,
        status: 'online',
        type: 'ai',
        pinned: true
      },
      {
        id: 'memory_guardian',
        name: 'Memory Guardian',
        avatar: '🛡️',
        lastMessage: 'Your memories are safe with me',
        time: '2 min',
        unread: 1,
        status: 'online',
        type: 'system'
      },
      {
        id: 'achievements',
        name: 'Achievements',
        avatar: '🏆',
        lastMessage: 'You unlocked a new achievement!',
        time: '5 min',
        unread: 2,
        status: 'away',
        type: 'gamification'
      },
      {
        id: 'voice_studio',
        name: 'Voice Studio',
        avatar: '🎙️',
        lastMessage: 'Ready to create your voice avatar?',
        time: '10 min',
        unread: 0,
        status: 'offline',
        type: 'premium'
      }
    ];
    
    setChats(mockChats);
    
    // Set default messages for each chat
    const defaultMessages = {
      'memo_ai': [
        {
          id: '1',
          content: 'Hello! I\'m Memo, your AI memory assistant. I can help you store, organize, and recall your memories. What would you like to remember today?',
          sender: 'ai',
          timestamp: new Date(Date.now() - 120000),
          status: 'delivered'
        }
      ],
      'memory_guardian': [
        {
          id: '1',
          content: 'Welcome to your secure memory vault! 🛡️ All your memories are encrypted and protected.',
          sender: 'system',
          timestamp: new Date(Date.now() - 300000),
          status: 'delivered'
        },
        {
          id: '2',
          content: 'You have 0 memories stored. Start by sharing something important with Memo!',
          sender: 'system',
          timestamp: new Date(Date.now() - 120000),
          status: 'delivered'
        }
      ],
      'achievements': [
        {
          id: '1',
          content: '🎉 Welcome to MemoApp! You\'ve earned your first points.',
          sender: 'system',
          timestamp: new Date(Date.now() - 600000),
          status: 'delivered'
        },
        {
          id: '2',
          content: 'Complete daily check-ins to maintain your streak! 🔥',
          sender: 'system',
          timestamp: new Date(Date.now() - 300000),
          status: 'delivered'
        }
      ],
      'voice_studio': [
        {
          id: '1',
          content: '🎙️ Voice Studio is ready! Record voice messages to create your personal voice avatar.',
          sender: 'system',
          timestamp: new Date(Date.now() - 600000),
          status: 'delivered'
        },
        {
          id: '2',
          content: '👑 Upgrade to Premium to unlock voice cloning features!',
          sender: 'system',
          timestamp: new Date(Date.now() - 600000),
          status: 'delivered'
        }
      ]
    };
    
    setMessages(defaultMessages);
  }, []);

  // Initialize app
  useEffect(() => {
    initializeApp();
    setupEventListeners();
  }, []);

  const initializeApp = async () => {
    if (!localStorage.getItem('userId')) {
      localStorage.setItem('userId', 'user_' + Date.now());
    }
    
    try {
      await loadUserStats();
      await connectWebSocket();
    } catch (error) {
      console.error('Failed to initialize app:', error);
    }
  };

  const loadUserStats = async () => {
    try {
      const stats = await gamificationService.getUserStats(userId);
      if (stats) {
        setUserStats({
          level: stats.level || 1,
          points: stats.points || 0,
          streak: stats.daily_streak || 0,
          achievements: stats.achievements_unlocked || 0,
          voiceCredits: stats.voice_credits || 0
        });
      }
    } catch (error) {
      console.error('Failed to load user stats:', error);
    }
  };

  const connectWebSocket = async () => {
    try {
      await wsService.connect(userId);
      setWsConnected(true);
      
      wsService.on('new_memory', (data) => {
        showNotification('New memory saved!', 'success');
        loadUserStats();
      });
      
      wsService.on('achievement_unlocked', (data) => {
        showAchievementNotification(data.achievement);
        loadUserStats();
      });
      
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      setWsConnected(false);
    }
  };

  const setupEventListeners = () => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      setShowSidebar(!mobile || !selectedChat);
    };
    
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('resize', handleResize);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  };

  // Message handling
  const sendMessage = async () => {
    if (!messageInput.trim() || sendingMessage || !selectedChat) return;
    
    const message = messageInput.trim();
    const newMessage = {
      id: Date.now().toString(),
      content: message,
      sender: 'user',
      timestamp: new Date(),
      status: 'sending'
    };
    
    // Add message to UI immediately
    setMessages(prev => ({
      ...prev,
      [selectedChat]: [...(prev[selectedChat] || []), newMessage]
    }));
    
    setMessageInput('');
    setSendingMessage(true);
    
    try {
      // Update message status
      setMessages(prev => ({
        ...prev,
        [selectedChat]: prev[selectedChat].map(msg => 
          msg.id === newMessage.id ? { ...msg, status: 'sent' } : msg
        )
      }));
      
      // Handle different chat types
      if (selectedChat === 'memo_ai') {
        await handleAIResponse(message, newMessage.id);
      } else {
        await handleSystemResponse(message, selectedChat, newMessage.id);
      }
      
    } catch (error) {
      console.error('Failed to send message:', error);
      // Update message status to failed
      setMessages(prev => ({
        ...prev,
        [selectedChat]: prev[selectedChat].map(msg => 
          msg.id === newMessage.id ? { ...msg, status: 'failed' } : msg
        )
      }));
    } finally {
      setSendingMessage(false);
      scrollToBottom();
    }
  };

  const handleAIResponse = async (userMessage, userMessageId) => {
    try {
      // Mark user message as delivered
      setTimeout(() => {
        setMessages(prev => ({
          ...prev,
          [selectedChat]: prev[selectedChat].map(msg => 
            msg.id === userMessageId ? { ...msg, status: 'delivered' } : msg
          )
        }));
      }, 500);
      
      // Show typing indicator
      const typingMessage = {
        id: 'typing',
        content: 'Memo is typing...',
        sender: 'ai',
        timestamp: new Date(),
        isTyping: true
      };
      
      setMessages(prev => ({
        ...prev,
        [selectedChat]: [...(prev[selectedChat] || []), typingMessage]
      }));
      
      // Get AI response
      const response = await claudeService.sendMessage(userMessage, userId);
      
      // Remove typing indicator and add real response
      const aiMessage = {
        id: Date.now().toString(),
        content: response?.content || 'I\'m here to help with your memories!',
        sender: 'ai',
        timestamp: new Date(),
        status: 'delivered'
      };
      
      setMessages(prev => ({
        ...prev,
        [selectedChat]: prev[selectedChat].filter(msg => msg.id !== 'typing').concat(aiMessage)
      }));
      
    } catch (error) {
      console.error('AI response failed:', error);
      // Remove typing indicator
      setMessages(prev => ({
        ...prev,
        [selectedChat]: prev[selectedChat].filter(msg => msg.id !== 'typing')
      }));
    }
  };

  const handleSystemResponse = async (userMessage, chatId, userMessageId) => {
    // Mark user message as delivered
    setTimeout(() => {
      setMessages(prev => ({
        ...prev,
        [chatId]: prev[chatId].map(msg => 
          msg.id === userMessageId ? { ...msg, status: 'delivered' } : msg
        )
      }));
    }, 500);
    
    // Generate appropriate system response
    let responseContent = '';
    
    switch (chatId) {
      case 'memory_guardian':
        responseContent = '🛡️ Memory secured! Your data is safe and encrypted.';
        break;
      case 'achievements':
        responseContent = '🎉 Great job! Keep up the engagement to unlock more achievements.';
        break;
      case 'voice_studio':
        responseContent = '🎙️ Voice message received! Continue recording to build your voice profile.';
        break;
      default:
        responseContent = 'Message received!';
    }
    
    setTimeout(() => {
      const systemMessage = {
        id: Date.now().toString(),
        content: responseContent,
        sender: 'system',
        timestamp: new Date(),
        status: 'delivered'
      };
      
      setMessages(prev => ({
        ...prev,
        [chatId]: [...(prev[chatId] || []), systemMessage]
      }));
    }, 1000);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Contact slot management
  const handleSlotClick = async (slot) => {
    if (slot.isEmpty) {
      // Show change warning if this slot has been used before
      if (!slot.canChange) {
        setShowChangeWarning(true);
        setSelectedSlotId(slot.id);
        return;
      }
      
      // Open WhatsApp contact selector
      setSelectedSlotId(slot.id);
      await loadWhatsAppContacts();
      setShowContactSelector(true);
    } else {
      // Open the contact's memory view
      setSelectedChat(slot.id);
      if (isMobile) setShowSidebar(false);
    }
  };

  const loadWhatsAppContacts = async () => {
    try {
      // Simulate loading WhatsApp contacts - In real implementation, this would
      // interface with WhatsApp Web.js or WhatsApp Business API
      const mockContacts = [
        { id: '1', name: 'John Smith', phone: '+1234567890', avatar: '👤' },
        { id: '2', name: 'Sarah Johnson', phone: '+1234567891', avatar: '👩' },
        { id: '3', name: 'Mike Wilson', phone: '+1234567892', avatar: '👨' },
        { id: '4', name: 'Emily Davis', phone: '+1234567893', avatar: '👱‍♀️' },
        { id: '5', name: 'Alex Brown', phone: '+1234567894', avatar: '🧑' },
        { id: '6', name: 'Lisa Garcia', phone: '+1234567895', avatar: '👩‍🦰' },
        { id: '7', name: 'David Miller', phone: '+1234567896', avatar: '👨‍💼' },
        { id: '8', name: 'Jennifer Lee', phone: '+1234567897', avatar: '👩‍💻' }
      ];
      
      setWhatsappContacts(mockContacts);
    } catch (error) {
      console.error('Failed to load WhatsApp contacts:', error);
      showNotification('Failed to load contacts. Please try again.', 'error');
    }
  };

  const handleContactSelection = (contact) => {
    // Store the selected contact
    setSelectedContact(contact);
    
    // Show one-time change warning before confirming
    if (selectedSlotId) {
      const currentSlot = contactSlots.find(slot => slot.id === selectedSlotId);
      
      // If slot can still be changed, show warning
      if (currentSlot && currentSlot.canChange) {
        setShowContactSelector(false);
        setShowChangeWarning(true);
        return;
      }
    }
  };

  const confirmContactSelection = async (contact) => {
    try {
      // Update the contact slot
      setContactSlots(prev => prev.map(slot => 
        slot.id === selectedSlotId 
          ? {
              ...slot,
              isEmpty: false,
              canChange: false, // Mark as unchangeable after first assignment
              contact: contact
            }
          : slot
      ));

      // Close contact selector
      setShowContactSelector(false);
      setShowChangeWarning(false);
      
      // Show import permission dialog
      setShowImportPermission(true);
      
      showNotification(`Contact ${contact.name} added to slot!`, 'success');
    } catch (error) {
      console.error('Failed to add contact:', error);
      showNotification('Failed to add contact. Please try again.', 'error');
    }
  };

  const handleImportChatHistory = async (contact) => {
    try {
      // Show loading state
      showNotification('Importing chat history...', 'info');
      
      // Simulate chat history import - In real implementation, this would
      // import actual WhatsApp chat history via WhatsApp Web.js
      const mockChatHistory = [
        {
          id: '1',
          content: 'Hey, how are you doing?',
          sender: contact.name,
          timestamp: new Date(Date.now() - 86400000), // Yesterday
          type: 'text'
        },
        {
          id: '2', 
          content: 'I\'m doing great! Just finished that project we discussed.',
          sender: 'user',
          timestamp: new Date(Date.now() - 82800000),
          type: 'text'
        },
        {
          id: '3',
          content: 'That\'s awesome! Can we schedule a call to discuss the next steps?',
          sender: contact.name,
          timestamp: new Date(Date.now() - 79200000),
          type: 'text'
        },
        {
          id: '4',
          content: 'Sure! How about tomorrow at 3 PM?',
          sender: 'user', 
          timestamp: new Date(Date.now() - 75600000),
          type: 'text'
        }
      ];

      // Update the contact slot with imported transcripts
      setContactSlots(prev => prev.map(slot => 
        slot.id === selectedSlotId 
          ? {
              ...slot,
              transcripts: mockChatHistory,
              memoryCategories: {
                personal: [],
                professional: [],
                important: [],
                events: []
              }
            }
          : slot
      ));

      // Close import dialog
      setShowImportPermission(false);
      
      // Process the imported data with AI (simulate)
      setTimeout(() => {
        processImportedData(selectedSlotId, mockChatHistory);
      }, 2000);

      showNotification(`Chat history imported for ${contact.name}!`, 'success');
      
    } catch (error) {
      console.error('Failed to import chat history:', error);
      showNotification('Failed to import chat history. Please try again.', 'error');
    }
  };

  const processImportedData = async (slotId, transcripts) => {
    try {
      // Simulate AI processing of chat data into memory categories
      showNotification('AI is analyzing and categorizing your conversations...', 'info');
      
      // Simulate processing delay
      setTimeout(() => {
        const categorizedMemories = {
          personal: [
            { text: 'Discussed personal well-being', timestamp: transcripts[0].timestamp, importance: 'medium' }
          ],
          professional: [
            { text: 'Completed project discussion', timestamp: transcripts[1].timestamp, importance: 'high' },
            { text: 'Scheduled follow-up meeting for 3 PM', timestamp: transcripts[3].timestamp, importance: 'high' }
          ],
          important: [
            { text: 'Next steps planning session scheduled', timestamp: transcripts[2].timestamp, importance: 'high' }
          ],
          events: [
            { text: 'Meeting scheduled for tomorrow 3 PM', timestamp: transcripts[3].timestamp, importance: 'high' }
          ]
        };

        // Update slot with categorized memories
        setContactSlots(prev => prev.map(slot => 
          slot.id === slotId 
            ? { ...slot, memoryCategories: categorizedMemories }
            : slot
        ));

        showNotification('🧠 AI analysis complete! Memories have been categorized.', 'success');
      }, 3000);
      
    } catch (error) {
      console.error('Failed to process imported data:', error);
      showNotification('Failed to process chat data. Please try again.', 'error');
    }
  };

  // Unlock slot functionality
  const handleSubscriptionUpgrade = async () => {
    try {
      // Integrate with existing subscription service
      showNotification('Redirecting to subscription upgrade...', 'info');
      
      // Close expansion
      setExpandedPremiumId(null);
      
      // In real implementation, this would integrate with existing subscription_service.py
      // For now, simulate subscription upgrade
      setTimeout(() => {
        // Update user stats to show premium status
        setUserStats(prev => ({
          ...prev,
          subscriptionType: 'premium',
          premiumFeatures: true
        }));
        
        // Unlock the slot
        setContactSlots(prev => prev.map(slot => 
          slot.id === 'slot_locked' 
            ? { ...slot, isLocked: false, isEmpty: true, canChange: true }
            : slot
        ));
        
        showNotification('🎉 Premium upgrade successful! Slot 6 unlocked!', 'success');
      }, 2000);
      
    } catch (error) {
      console.error('Subscription upgrade failed:', error);
      showNotification('Subscription upgrade failed. Please try again.', 'error');
    }
  };

  const handleFriendInvitation = async () => {
    try {
      // Integrate with existing gamification system
      showNotification('Opening friend invitation system...', 'info');
      
      // Close expansion
      setExpandedPremiumId(null);
      
      // In real implementation, this would integrate with existing invitation system
      // from gamification/invitation_dashboard_secure.py
      
      // Simulate invitation flow
      const inviteLink = `https://memoapp.com/invite/${userStats.userId || 'user123'}`;
      
      // Show share options (simulate WhatsApp sharing)
      if (navigator.share) {
        await navigator.share({
          title: 'Join MemoApp - Your AI Memory Guardian!',
          text: 'I\'m using MemoApp to enhance my memory with AI. Join me and get smarter conversations!',
          url: inviteLink
        });
      } else {
        // Fallback to clipboard
        await navigator.clipboard.writeText(inviteLink);
        showNotification('Invitation link copied to clipboard!', 'success');
      }
      
      // Update friend invitation count (simulate successful invitation)
      setTimeout(() => {
        setUserStats(prev => {
          const newInvitations = (prev.friendInvitations || 0) + 1;
          const updated = {
            ...prev,
            friendInvitations: newInvitations
          };
          
          // Unlock slot if 5 friends invited
          if (newInvitations >= 5) {
            setContactSlots(prevSlots => prevSlots.map(slot => 
              slot.id === 'slot_locked' 
                ? { ...slot, isLocked: false, isEmpty: true, canChange: true }
                : slot
            ));
            showNotification('🎉 5 friends invited! Slot 6 unlocked!', 'success');
          } else {
            showNotification(`Friend invited! Progress: ${newInvitations}/5`, 'success');
          }
          
          return updated;
        });
      }, 1000);
      
    } catch (error) {
      console.error('Friend invitation failed:', error);
      showNotification('Failed to share invitation. Please try again.', 'error');
    }
  };

  // Notification system
  const showNotification = useCallback((message, type = 'info') => {
    const notification = {
      id: Date.now().toString(),
      message,
      type,
      timestamp: Date.now()
    };
    
    setShowNotifications(prev => [...prev, notification]);
    
    setTimeout(() => {
      setShowNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 4000);
  }, []);

  const showAchievementNotification = useCallback((achievement) => {
    showNotification(`🏆 Achievement unlocked: ${achievement.name}!`, 'achievement');
  }, [showNotification]);

  // Render functions
  const renderHeader = () => (
    <header className="wa-header">
      <div className="wa-header-content">
        {selectedChat && isMobile && (
          <button 
            className="wa-back-button"
            onClick={() => {
              setSelectedChat(null);
              setShowSidebar(true);
            }}
          >
            <ArrowLeft size={24} />
          </button>
        )}
        
        <div className="wa-app-info">
          <Brain className="wa-app-icon" />
          <div className="wa-app-title">
            <h1>MemoApp</h1>
            <span className="wa-app-subtitle">Your Memory Guardian</span>
          </div>
        </div>
        
        <div className="wa-header-actions">
          <div className="wa-connection-status">
            <div className={`wa-status-dot ${wsConnected ? 'online' : 'offline'}`} />
            <span>{wsConnected ? 'Connected' : 'Connecting...'}</span>
          </div>
          
          <button className="wa-icon-button" onClick={toggleTheme}>
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          
          <button className="wa-icon-button">
            <MoreVertical size={20} />
          </button>
        </div>
      </div>
    </header>
  );

  const renderSidebar = () => (
    <div className={`wa-sidebar ${!showSidebar ? 'hidden' : ''}`}>
      {/* Chat List Header */}
      <div className="wa-sidebar-header">
        <div className="wa-sidebar-title">
          <h2>Chats</h2>
          <div className="wa-sidebar-actions">
            <button className="wa-icon-button">
              <MessageCircle size={20} />
            </button>
            <button className="wa-icon-button">
              <MoreVertical size={20} />
            </button>
          </div>
        </div>
        
        {/* Search */}
        <div className="wa-search-container">
          <div className="wa-search-wrapper">
            <Search className="wa-search-icon" size={16} />
            <input
              type="text"
              className="wa-search"
              placeholder="Search or start new chat"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
        
        {/* Navigation Tabs */}
        <div className="wa-nav-tabs">
          <button 
            className={`wa-nav-tab ${view === 'chats' ? 'active' : ''}`}
            onClick={() => setView('chats')}
          >
            <MessageCircle size={16} />
            <span>Chats</span>
            {chats.reduce((sum, chat) => sum + chat.unread, 0) > 0 && (
              <div className="wa-badge">
                {chats.reduce((sum, chat) => sum + chat.unread, 0)}
              </div>
            )}
          </button>
          <button 
            className={`wa-nav-tab ${view === 'memory' ? 'active' : ''}`}
            onClick={() => setView('memory')}
          >
            <Brain size={16} />
            <span>Memory</span>
          </button>
          <button 
            className={`wa-nav-tab ${view === 'rewards' ? 'active' : ''}`}
            onClick={() => setView('rewards')}
          >
            <Trophy size={16} />
            <span>Rewards</span>
            {userStats.achievements > 0 && (
              <div className="wa-badge">{userStats.achievements}</div>
            )}
          </button>
        </div>
      </div>
      
      {/* WhatsApp-Style Contact Cards */}
      <ContactCardsGrid
        slots={contactSlots}
        onSlotSelect={handleSlotClick}
      />
    </div>
  );

  const renderChatArea = () => {
    if (!selectedChat) {
      return (
        <div className="wa-no-chat">
          <div className="wa-no-chat-content">
            <Brain size={80} className="wa-no-chat-icon" />
            <h2>Welcome to MemoApp</h2>
            <p>Your personal memory guardian powered by AI</p>
            <div className="wa-quick-stats">
              <div className="wa-quick-stat">
                <Zap className="stat-icon" />
                <span>{userStats.points} Points</span>
              </div>
              <div className="wa-quick-stat">
                <Sparkles className="stat-icon" />
                <span>Level {userStats.level}</span>
              </div>
              <div className="wa-quick-stat">
                <Trophy className="stat-icon" />
                <span>{userStats.streak} Day Streak</span>
              </div>
            </div>
            <p className="wa-get-started">Select a chat to get started</p>
          </div>
        </div>
      );
    }

    const currentChat = chats.find(chat => chat.id === selectedChat);
    const chatMessages = messages[selectedChat] || [];

    return (
      <div className="wa-chat-area">
        {/* Chat Header */}
        <div className="wa-chat-header">
          <div className="wa-chat-info">
            <div className="wa-avatar wa-avatar-sm">
              <span>{currentChat?.avatar}</span>
            </div>
            <div className="wa-chat-details">
              <h3 className="wa-chat-name">{currentChat?.name}</h3>
              <span className="wa-chat-status">
                {currentChat?.status === 'online' ? 'online' : 
                 currentChat?.status === 'away' ? 'away' : 'last seen recently'}
              </span>
            </div>
          </div>
          
          <div className="wa-chat-actions">
            <button className="wa-icon-button">
              <Phone size={20} />
            </button>
            <button className="wa-icon-button">
              <Video size={20} />
            </button>
            <button className="wa-icon-button" onClick={() => setShowChatInfo(!showChatInfo)}>
              <Info size={20} />
            </button>
          </div>
        </div>
        
        {/* Messages */}
        <div className="wa-messages" ref={chatContainerRef}>
          <div className="wa-messages-container">
            {chatMessages.map((message, index) => (
              <div
                key={message.id}
                className={`wa-message ${message.sender === 'user' ? 'wa-message-out' : 'wa-message-in'} ${message.isTyping ? 'wa-message-typing' : ''}`}
              >
                <div className="wa-message-content">
                  {message.isTyping ? (
                    <div className="wa-typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  ) : (
                    <>
                      <p className="wa-message-text">{message.content}</p>
                      <div className="wa-message-meta">
                        <span className="wa-message-time">
                          {message.timestamp.toLocaleTimeString([], { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                          })}
                        </span>
                        {message.sender === 'user' && (
                          <div className="wa-message-status">
                            {message.status === 'sending' && <Loader size={12} className="wa-spinning" />}
                            {message.status === 'sent' && <Check size={12} />}
                            {message.status === 'delivered' && <CheckCheck size={12} />}
                            {message.status === 'failed' && <AlertCircle size={12} className="wa-text-red" />}
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>
        
        {/* Message Input */}
        <div className="wa-message-input-container">
          <div className="wa-message-input-wrapper">
            <button className="wa-icon-button">
              <Plus size={20} />
            </button>
            
            <div className="wa-input-container">
              <input
                ref={messageInputRef}
                type="text"
                className="wa-message-input"
                placeholder="Type a message"
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              />
              <button 
                className="wa-icon-button"
                onClick={() => setShowEmojiPicker(!showEmojiPicker)}
              >
                <Smile size={20} />
              </button>
            </div>
            
            {messageInput.trim() ? (
              <button 
                className="wa-send-button"
                onClick={sendMessage}
                disabled={sendingMessage}
              >
                <Send size={20} />
              </button>
            ) : (
              <button className="wa-icon-button">
                <Mic size={20} />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderNotifications = () => (
    <div className="wa-notifications">
      {showNotifications.map(notification => (
        <div
          key={notification.id}
          className={`wa-notification wa-notification-${notification.type}`}
        >
          <div className="wa-notification-content">
            {notification.type === 'achievement' && <Trophy size={16} />}
            <span>{notification.message}</span>
          </div>
          <button 
            className="wa-notification-close"
            onClick={() => setShowNotifications(prev => 
              prev.filter(n => n.id !== notification.id)
            )}
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );

  return (
    <div className={`wa-app ${theme}`} data-theme={theme}>
      {renderHeader()}
      
      <div className="wa-main">
        {renderSidebar()}
        {renderChatArea()}
      </div>
      
      {renderNotifications()}
      

      {/* Contact Selector Modal */}
      {showContactSelector && (
        <div className="wa-modal-overlay">
          <div className="wa-modal">
            <div className="wa-modal-header">
              <h3>Select WhatsApp Contact</h3>
              <button 
                className="wa-modal-close"
                onClick={() => setShowContactSelector(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="wa-modal-content">
              <div className="wa-contacts-list">
                {whatsappContacts.map(contact => (
                  <div
                    key={contact.id}
                    className="wa-contact-item"
                    onClick={() => handleContactSelection(contact)}
                  >
                    <div className="wa-avatar">
                      <span>{contact.avatar}</span>
                    </div>
                    <div className="wa-contact-info">
                      <h4>{contact.name}</h4>
                      <span>{contact.phone}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Change Warning Modal */}
      {showChangeWarning && (
        <div className="wa-modal-overlay">
          <div className="wa-modal">
            <div className="wa-modal-header">
              <h3>⚠️ One-Time Change Warning</h3>
              <button 
                className="wa-modal-close"
                onClick={() => setShowChangeWarning(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="wa-modal-content">
              <p>You can only change this contact slot <strong>once</strong> before it becomes permanent. Are you sure you want to proceed?</p>
              <div className="wa-modal-actions">
                <button 
                  className="wa-button-secondary"
                  onClick={() => setShowChangeWarning(false)}
                >
                  Cancel
                </button>
                <button 
                  className="wa-button-primary"
                  onClick={() => {
                    setShowChangeWarning(false);
                    if (selectedContact) {
                      confirmContactSelection(selectedContact);
                    }
                  }}
                >
                  Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Import Permission Modal */}
      {showImportPermission && (
        <div className="wa-modal-overlay">
          <div className="wa-modal">
            <div className="wa-modal-header">
              <h3>Import Chat History</h3>
              <button 
                className="wa-modal-close"
                onClick={() => setShowImportPermission(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="wa-modal-content">
              <p>Would you like to import the chat history for this contact? This will help our AI provide better memory analysis and insights.</p>
              <div className="wa-modal-actions">
                <button 
                  className="wa-button-secondary"
                  onClick={() => setShowImportPermission(false)}
                >
                  Skip for Now
                </button>
                <button 
                  className="wa-button-primary"
                  onClick={() => {
                    const currentSlot = contactSlots.find(slot => slot.id === selectedSlotId);
                    if (currentSlot?.contact) {
                      handleImportChatHistory(currentSlot.contact);
                    }
                  }}
                >
                  Import History
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Mobile overlay for sidebar */}
      {isMobile && showSidebar && (
        <div 
          className="wa-sidebar-overlay"
          onClick={() => setShowSidebar(false)}
        />
      )}
    </div>
  );
};

export default WhatsAppMemoryApp;