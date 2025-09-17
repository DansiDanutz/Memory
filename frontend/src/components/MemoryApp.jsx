import React, { useState, useContext, useEffect, useCallback, useRef } from 'react';
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
  RefreshCw,
  Send,
  AlertCircle,
  Loader,
  Plus,
  X,
  UserPlus,
  Shield,
  Lock,
  AlertTriangle,
  Info,
  Trophy,
  Home,
  User,
  Crown
} from 'lucide-react';
import { ThemeContext } from '../contexts/ThemeContext';
import { memoryService, claudeService, wsService, gamificationService } from '../services';
import whatsappService from '../services/whatsappService';
import ContactPicker from './ContactPicker';
import MemoryCategories from './MemoryCategories';
import RewardsTab from './RewardsTab';
import BottomNav from './BottomNav';
import './MemoryApp.css';
import './MemoryApp.mobile.css';

const MemoryApp = () => {
  const { theme, toggleTheme } = useContext(ThemeContext);
  
  // State management
  const [selectedContact, setSelectedContact] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isOnline, setIsOnline] = useState(false);
  const [view, setView] = useState('contacts'); // 'contacts', 'categories', 'chat', 'integration', or 'rewards'
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [messageInput, setMessageInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [syncStatus, setSyncStatus] = useState('offline');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [activities, setActivities] = useState([]);
  const [isPremium, setIsPremium] = useState(false); // FREE version by default
  const [showContactPicker, setShowContactPicker] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [contactSlots, setContactSlots] = useState(new Array(5).fill(null));
  const [whatsappStatus, setWhatsappStatus] = useState({
    isReady: false,
    isAuthenticated: false,
    contactCount: 0
  });
  const [slotChangeCounts, setSlotChangeCounts] = useState(new Array(5).fill(0));
  const [showChangeWarning, setShowChangeWarning] = useState(false);
  const [warningSlotIndex, setWarningSlotIndex] = useState(null);
  const [pendingContactChange, setPendingContactChange] = useState(null);
  
  // Mobile detection and navigation state
  const [isMobile, setIsMobile] = useState(false);
  const [activeTab, setActiveTab] = useState('home');
  const [isPullRefreshing, setIsPullRefreshing] = useState(false);
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const [showBottomSheet, setShowBottomSheet] = useState(false);
  const [bottomSheetContent, setBottomSheetContent] = useState(null);
  const [hasNewRewards, setHasNewRewards] = useState(false);
  
  // Refs for mobile interactions
  const scrollContainerRef = useRef(null);
  const pullToRefreshRef = useRef(null);
  
  // User ID - in production, this would come from authentication
  const userId = localStorage.getItem('userId') || 'default_user';
  
  // FREE version limit
  const MAX_FREE_CONTACTS = 5;
  const MAX_CHANGES_PER_SLOT = 2; // Initial fill + 1 change
  
  // Check if all slots are filled (slots are locked when all 5 are filled)
  const areAllSlotsFilled = Array.isArray(contactSlots) ? 
    contactSlots.filter(slot => slot !== null).length === MAX_FREE_CONTACTS : 
    false;
  
  // Check if a slot can be changed
  const canChangeSlot = (slotIndex) => {
    if (!Array.isArray(slotChangeCounts)) return true;
    if (!slotChangeCounts[slotIndex]) return true; // Never used
    return slotChangeCounts[slotIndex] < MAX_CHANGES_PER_SLOT;
  };
  
  // Get remaining changes for a slot
  const getRemainingChanges = (slotIndex) => {
    if (!Array.isArray(slotChangeCounts)) return MAX_CHANGES_PER_SLOT;
    const changes = slotChangeCounts[slotIndex] || 0;
    return Math.max(0, MAX_CHANGES_PER_SLOT - changes);
  };

  // Initialize user ID and load saved contacts
  useEffect(() => {
    if (!localStorage.getItem('userId')) {
      localStorage.setItem('userId', 'user_' + Date.now());
    }
    
    // Load saved contact slots from localStorage
    const savedSlots = localStorage.getItem('contactSlots');
    if (savedSlots) {
      try {
        const slots = JSON.parse(savedSlots);
        // Ensure slots is an array and has the correct structure
        if (Array.isArray(slots) && slots.length === 5) {
          setContactSlots(slots);
          // Set first filled slot as selected
          const firstFilled = slots.find(slot => slot !== null);
          if (firstFilled) {
            setSelectedContact(firstFilled);
          }
        } else {
          // If invalid structure, reset to empty slots
          console.warn('Invalid contact slots structure, resetting to default');
          setContactSlots(new Array(5).fill(null));
        }
      } catch (e) {
        console.error('Error parsing contact slots from localStorage:', e);
        // Reset to empty slots on parse error
        setContactSlots(new Array(5).fill(null));
      }
    } else {
      // Initialize with 5 empty slots
      setContactSlots(new Array(5).fill(null));
    }
    
    // Load saved change counts from localStorage
    const savedChangeCounts = localStorage.getItem('slotChangeCounts');
    if (savedChangeCounts) {
      try {
        const counts = JSON.parse(savedChangeCounts);
        if (Array.isArray(counts) && counts.length === 5) {
          setSlotChangeCounts(counts);
        }
      } catch (e) {
        console.error('Error parsing change counts from localStorage:', e);
      }
    }
  }, []);
  
  // Mobile detection and viewport setup
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    // Initial check
    checkMobile();
    
    // Listen for resize events
    window.addEventListener('resize', checkMobile);
    
    // Set viewport height for mobile browsers
    const setViewportHeight = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
    };
    
    setViewportHeight();
    window.addEventListener('resize', setViewportHeight);
    
    return () => {
      window.removeEventListener('resize', checkMobile);
      window.removeEventListener('resize', setViewportHeight);
    };
  }, []);
  
  // Pull-to-refresh functionality
  const handleTouchStart = useCallback((e) => {
    if (scrollContainerRef.current?.scrollTop === 0) {
      setTouchStart(e.targetTouches[0].clientY);
    }
  }, []);
  
  const handleTouchMove = useCallback((e) => {
    if (!touchStart) return;
    
    const touchY = e.targetTouches[0].clientY;
    const touchDiff = touchY - touchStart;
    
    if (touchDiff > 0 && scrollContainerRef.current?.scrollTop === 0) {
      const pullDistance = Math.min(touchDiff * 0.5, 100);
      if (pullToRefreshRef.current) {
        pullToRefreshRef.current.style.height = `${pullDistance}px`;
        pullToRefreshRef.current.style.opacity = pullDistance / 100;
      }
      
      if (pullDistance > 80 && !isPullRefreshing) {
        // Trigger haptic feedback if available
        if (navigator.vibrate) {
          navigator.vibrate(10);
        }
      }
    }
  }, [touchStart, isPullRefreshing]);
  
  const handleTouchEnd = useCallback(async (e) => {
    if (!touchStart) return;
    
    const touchY = e.changedTouches[0].clientY;
    const touchDiff = touchY - touchStart;
    const pullDistance = Math.min(touchDiff * 0.5, 100);
    
    if (pullDistance > 80 && scrollContainerRef.current?.scrollTop === 0) {
      setIsPullRefreshing(true);
      
      // Trigger refresh
      await handleRefresh();
      
      setIsPullRefreshing(false);
    }
    
    // Reset pull-to-refresh indicator
    if (pullToRefreshRef.current) {
      pullToRefreshRef.current.style.height = '0px';
      pullToRefreshRef.current.style.opacity = '0';
    }
    
    setTouchStart(null);
    setTouchEnd(null);
  }, [touchStart]);
  
  // Swipe gesture detection for tab switching
  const handleSwipeStart = useCallback((e) => {
    setTouchStart(e.targetTouches[0].clientX);
  }, []);
  
  const handleSwipeEnd = useCallback((e) => {
    if (!touchStart) return;
    
    const touchEndX = e.changedTouches[0].clientX;
    const swipeDiff = touchStart - touchEndX;
    const minSwipeDistance = 50;
    
    if (Math.abs(swipeDiff) > minSwipeDistance) {
      const tabs = ['home', 'chat', 'rewards', 'contacts', 'profile'];
      const currentIndex = tabs.indexOf(activeTab);
      
      if (swipeDiff > 0 && currentIndex < tabs.length - 1) {
        // Swipe left - next tab
        setActiveTab(tabs[currentIndex + 1]);
      } else if (swipeDiff < 0 && currentIndex > 0) {
        // Swipe right - previous tab
        setActiveTab(tabs[currentIndex - 1]);
      }
    }
    
    setTouchStart(null);
  }, [touchStart, activeTab]);
  
  // Handle tab change from bottom navigation
  const handleTabChange = useCallback((tab) => {
    setActiveTab(tab);
    
    // Update view based on tab
    switch(tab) {
      case 'home':
        setView('contacts');
        break;
      case 'chat':
        setView('chat');
        break;
      case 'rewards':
        setView('rewards');
        break;
      case 'contacts':
        setView('categories');
        break;
      case 'profile':
        setView('integration');
        break;
      default:
        setView('contacts');
    }
  }, []);
  
  // Handle refresh action
  const handleRefresh = async () => {
    try {
      // Refresh data based on current view
      if (selectedContact) {
        await fetchMemories();
      }
      await checkWhatsAppStatus();
      
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (error) {
      console.error('Refresh failed:', error);
    }
  };

  // Save contact slots to localStorage whenever they change
  useEffect(() => {
    if (contactSlots.length > 0) {
      localStorage.setItem('contactSlots', JSON.stringify(contactSlots));
    }
  }, [contactSlots]);
  
  // Save change counts to localStorage whenever they change
  useEffect(() => {
    if (slotChangeCounts.length > 0) {
      localStorage.setItem('slotChangeCounts', JSON.stringify(slotChangeCounts));
    }
  }, [slotChangeCounts]);
  
  // Fetch memories when contact changes
  useEffect(() => {
    if (selectedContact) {
      fetchMemories();
    }
  }, [selectedContact]);

  // Set up WebSocket connection
  useEffect(() => {
    connectWebSocket();
    checkWhatsAppStatus();
    
    // Check WhatsApp status periodically
    const statusInterval = setInterval(checkWhatsAppStatus, 10000);
    
    // Cleanup on unmount
    return () => {
      wsService.disconnect();
      clearInterval(statusInterval);
    };
  }, [userId]);

  // Search with debounce
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchQuery.trim()) {
        performSearch();
      } else {
        setSearchResults([]);
      }
    }, 500);

    return () => clearTimeout(debounceTimer);
  }, [searchQuery]);
  
  // Check for new rewards periodically
  useEffect(() => {
    const checkRewards = () => {
      // This would check for new achievements/rewards
      const hasNew = Math.random() > 0.7; // Mock check
      setHasNewRewards(hasNew);
    };
    
    checkRewards();
    const interval = setInterval(checkRewards, 30000); // Check every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  // Fetch memories from backend
  const fetchMemories = async () => {
    if (!selectedContact) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Use the current user's memories but filter by contact context
      // In production, this would be contact-specific
      const response = await memoryService.retrieveMemories(
        userId, // Use current user ID for now
        'GENERAL', // Default category
        50,
        0
      );
      
      // Add some mock memories for selected contact
      const mockMemories = [
        {
          id: Date.now() + 1,
          content: selectedContact.lastMessage,
          category: 'GENERAL',
          timestamp: new Date().toISOString(),
          tags: ['conversation'],
          contact: selectedContact.name
        },
        {
          id: Date.now() + 2,
          content: `Previous conversation with ${selectedContact.name}`,
          category: 'GENERAL',
          timestamp: new Date(Date.now() - 86400000).toISOString(),
          tags: ['memory'],
          contact: selectedContact.name
        }
      ];
      
      setMemories([...mockMemories, ...(response || [])]);
    } catch (err) {
      console.error('Error fetching memories:', err);
      setError('Failed to load memories. Please try again.');
      setMemories([]);
    } finally {
      setLoading(false);
    }
  };

  // Search contacts
  const performSearch = async () => {
    try {
      setIsSearching(true);
      
      // Filter filled slots based on search query
      const filledContacts = contactSlots.filter(contact => contact !== null);
      const filteredContacts = filledContacts.filter(contact => 
        contact.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        contact.phoneNumber.includes(searchQuery) ||
        (contact.lastMessage && contact.lastMessage.toLowerCase().includes(searchQuery.toLowerCase()))
      );
      
      setSearchResults(filteredContacts);
    } catch (err) {
      console.error('Error searching:', err);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };
  
  // Handle adding contact to slot
  const handleAddContact = (slotIndex) => {
    // Check if slot has reached max changes
    if (!canChangeSlot(slotIndex)) {
      // Slot is locked
      console.log(`Slot ${slotIndex + 1} is locked - max changes reached`);
      return;
    }
    
    // If slot already has a contact, show warning
    if (contactSlots[slotIndex] !== null) {
      setWarningSlotIndex(slotIndex);
      setShowChangeWarning(true);
      return;
    }
    
    setSelectedSlot(slotIndex);
    setShowContactPicker(true);
  };
  
  // Handle selecting contact from picker
  const handleSelectContactFromPicker = (contact) => {
    const newSlots = [...contactSlots];
    const newCounts = [...slotChangeCounts];
    
    // Increment change count for this slot
    newCounts[selectedSlot] = (newCounts[selectedSlot] || 0) + 1;
    
    // Add additional properties for the slot
    const slotContact = {
      ...contact,
      lastMessage: contact.status || 'Start a conversation',
      lastMessageTime: 'Now',
      unread: 0,
      isTyping: false,
      isPinned: false
    };
    newSlots[selectedSlot] = slotContact;
    
    setContactSlots(newSlots);
    setSlotChangeCounts(newCounts);
    setSelectedContact(slotContact);
    setShowContactPicker(false);
    setSelectedSlot(null);
  };
  
  // Handle removing contact from slot
  const handleRemoveContact = (slotIndex, e) => {
    e.stopPropagation(); // Prevent selecting the contact
    
    // Check if slot can be changed
    if (!canChangeSlot(slotIndex)) {
      console.log(`Slot ${slotIndex + 1} is locked - no changes allowed`);
      return;
    }
    
    // Show warning about using the last change
    if (getRemainingChanges(slotIndex) === 1) {
      setWarningSlotIndex(slotIndex);
      setPendingContactChange({ action: 'remove', slotIndex });
      setShowChangeWarning(true);
      return;
    }
    
    performRemoveContact(slotIndex);
  };
  
  // Actually perform the contact removal
  const performRemoveContact = (slotIndex) => {
    const newSlots = [...contactSlots];
    const removedContact = newSlots[slotIndex];
    newSlots[slotIndex] = null;
    setContactSlots(newSlots);
    
    // If removed contact was selected, clear selection
    if (selectedContact?.id === removedContact?.id) {
      setSelectedContact(null);
    }
  };
  
  // Handle confirming contact change after warning
  const handleConfirmChange = () => {
    if (pendingContactChange?.action === 'remove') {
      performRemoveContact(pendingContactChange.slotIndex);
    } else if (warningSlotIndex !== null) {
      // Changing to a new contact
      setSelectedSlot(warningSlotIndex);
      setShowContactPicker(true);
    }
    
    setShowChangeWarning(false);
    setWarningSlotIndex(null);
    setPendingContactChange(null);
  };

  // Check WhatsApp status
  const checkWhatsAppStatus = async () => {
    try {
      const status = await whatsappService.getStatus();
      setWhatsappStatus({
        isReady: status.isReady,
        isAuthenticated: status.isAuthenticated,
        contactCount: status.contactCount || 0
      });
    } catch (error) {
      console.error('Error checking WhatsApp status:', error);
      setWhatsappStatus({
        isReady: false,
        isAuthenticated: false,
        contactCount: 0
      });
    }
  };

  // Connect to WebSocket
  const connectWebSocket = () => {
    wsService.connect(
      userId,
      () => {
        console.log('WebSocket connected');
        setWsConnected(true);
        setSyncStatus('synced');
        setIsOnline(true);
      },
      () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        setSyncStatus('offline');
        setIsOnline(false);
      }
    );

    // Listen for WebSocket events
    wsService.on('memory_created', (data) => {
      console.log('New memory created:', data);
      fetchMemories();
      addActivity('Memory created', 'memo');
    });

    wsService.on('memory_updated', (data) => {
      console.log('Memory updated:', data);
      fetchMemories();
    });

    wsService.on('whatsapp_message', (data) => {
      console.log('WhatsApp message received:', data);
      addActivity(`WhatsApp: ${data.message}`, 'whatsapp');
      fetchMemories();
    });

    wsService.on('sync_status', (data) => {
      setSyncStatus(data.status);
      console.log('Sync status:', data);
    });
  };

  // Add activity to feed
  const addActivity = (message, source) => {
    const activity = {
      id: Date.now(),
      message,
      source,
      timestamp: new Date().toLocaleTimeString(),
      icon: source === 'whatsapp' ? '📱' : '🧠'
    };
    
    setActivities(prev => [activity, ...prev].slice(0, 10));
  };

  // Send message / Create memory
  const handleSendMessage = async () => {
    if (!messageInput.trim() || sendingMessage) return;
    
    try {
      setSendingMessage(true);
      setError(null);
      
      // First analyze the message with Claude
      const analysis = await claudeService.analyzeMessage(messageInput);
      
      // Create memory with AI-enhanced categorization for selected contact
      const memory = {
        user_id: selectedContact ? selectedContact.phoneNumber.replace(/[^0-9]/g, '') : userId,
        content: messageInput,
        category: analysis.category || 'GENERAL',
        tags: analysis.tags || [],
        sentiment: analysis.sentiment,
        importance: analysis.priority || 5,
        contact_phone: selectedContact?.phoneNumber
      };
      
      await memoryService.createMemory(memory);
      
      // Clear input
      setMessageInput('');
      
      // Refresh memories
      fetchMemories();
      
      // Add to activity feed
      addActivity(`Memory saved: "${messageInput.substring(0, 50)}..."`, 'memo');
      
      // Send through WebSocket for sync
      wsService.send('memory_created', memory);
      
    } catch (err) {
      console.error('Error creating memory:', err);
      setError('Failed to save memory. Please try again.');
    } finally {
      setSendingMessage(false);
    }
  };

  // Get sync icon based on status
  const getSyncIcon = (status) => {
    switch (status) {
      case 'syncing':
        return <RefreshCw className="w-3 h-3 animate-spin text-yellow-500" />;
      case 'synced':
        return <Wifi className="w-3 h-3 text-green-500" />;
      case 'offline':
        return <WifiOff className="w-3 h-3 text-red-500" />;
      default:
        return <Wifi className="w-3 h-3 text-gray-400" />;
    }
  };

  // Get avatar initials or emoji
  const getAvatar = (contact) => {
    if (contact.avatar) return contact.avatar;
    return contact.initials;
  };

  // Format display data
  const displayContacts = searchQuery.trim() ? searchResults : contactSlots;
  const displayMemories = memories;
  
  // Get excluded phone numbers for contact picker
  const excludedNumbers = Array.isArray(contactSlots) ? 
    contactSlots
      .filter(slot => slot !== null)
      .map(contact => contact.phoneNumber) : 
    [];

  // Render mobile layout
  if (isMobile) {
    return (
      <div className="memory-app mobile" data-theme={theme}>
        {/* Pull-to-refresh indicator */}
        <div ref={pullToRefreshRef} className="pull-to-refresh">
          <RefreshCw className={`refresh-icon ${isPullRefreshing ? 'spinning' : ''}`} />
        </div>
        
        {/* Mobile Content Container */}
        <div 
          ref={scrollContainerRef}
          className="mobile-container"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          {/* Mobile Header */}
          <div className="mobile-header">
            <div className="mobile-header-content">
              <div className="app-title">
                <Brain className="w-6 h-6" />
                <span>MemoApp</span>
              </div>
              <div className="header-actions">
                <button className="action-btn" onClick={toggleTheme}>
                  {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
                </button>
                <button className="action-btn">
                  <Search className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
          
          {/* Dynamic Content Based on Active Tab */}
          <div className="mobile-content">
            {activeTab === 'home' && (
              <div className="contact-slots-mobile">
                <h2 className="section-title">Your Contacts</h2>
                {contactSlots.map((contact, index) => (
                  <div key={index} className="contact-card-mobile">
                    {contact === null ? (
                      <div 
                        className="empty-slot-card"
                        onClick={() => handleAddContact(index)}
                      >
                        <div className="empty-slot-icon">
                          {!canChangeSlot(index) ? (
                            <Lock className="w-8 h-8" />
                          ) : (
                            <Plus className="w-8 h-8" />
                          )}
                        </div>
                        <p className="slot-label">Slot {index + 1}</p>
                        <p className="slot-status">
                          {!canChangeSlot(index) ? 'Locked' : 'Tap to add'}
                        </p>
                      </div>
                    ) : (
                      <div 
                        className="contact-card"
                        onClick={() => {
                          setSelectedContact(contact);
                          setActiveTab('chat');
                        }}
                      >
                        <div className="contact-avatar" style={{background: contact.avatarColor}}>
                          {getAvatar(contact)}
                        </div>
                        <div className="contact-info">
                          <h3>{contact.name}</h3>
                          <p>{contact.lastMessage}</p>
                        </div>
                        {canChangeSlot(index) && (
                          <button
                            className="remove-btn-mobile"
                            onClick={(e) => handleRemoveContact(index, e)}
                          >
                            <X className="w-5 h-5" />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {activeTab === 'chat' && selectedContact && (
              <div className="chat-view-mobile">
                <div className="chat-header-mobile">
                  <div className="chat-contact-info">
                    <div className="chat-avatar-mobile" style={{background: selectedContact.avatarColor}}>
                      {getAvatar(selectedContact)}
                    </div>
                    <div>
                      <h3>{selectedContact.name}</h3>
                      <p className="status">{selectedContact.phoneNumber}</p>
                    </div>
                  </div>
                  <button className="action-btn">
                    <Phone className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="chat-messages-mobile">
                  {loading ? (
                    <div className="loading-state">
                      <Loader className="animate-spin" />
                      <p>Loading memories...</p>
                    </div>
                  ) : memories.length > 0 ? (
                    <div className="messages-list">
                      {memories.map(memory => (
                        <div key={memory.id} className="message-bubble">
                          <p>{memory.content}</p>
                          <span className="time">{new Date(memory.timestamp).toLocaleTimeString()}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <MessageCircle className="w-12 h-12" />
                      <p>No messages yet</p>
                    </div>
                  )}
                </div>
                
                <div className="message-input-mobile">
                  <input
                    type="text"
                    placeholder="Type a message"
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  />
                  <button onClick={handleSendMessage}>
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
            
            {activeTab === 'rewards' && (
              <RewardsTab
                userId={userId}
                theme={theme}
                gamificationService={gamificationService}
                wsService={wsService}
              />
            )}
            
            {activeTab === 'contacts' && (
              <MemoryCategories
                contact={selectedContact}
                onBack={() => setActiveTab('home')}
                onSelectCategory={(category) => {
                  setSelectedCategory(category);
                  setActiveTab('chat');
                }}
                theme={theme}
              />
            )}
            
            {activeTab === 'profile' && (
              <div className="profile-view-mobile">
                <h2>Profile & Settings</h2>
                <div className="profile-card">
                  <div className="profile-avatar">
                    <User className="w-12 h-12" />
                  </div>
                  <h3>User Profile</h3>
                  <p>{userId}</p>
                </div>
                <div className="settings-list">
                  <button className="setting-item">
                    <Settings className="w-5 h-5" />
                    <span>Settings</span>
                  </button>
                  <button className="setting-item" onClick={() => alert('Premium coming soon!')}>
                    <Crown className="w-5 h-5" />
                    <span>Upgrade to Premium</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Bottom Navigation */}
        <BottomNav
          activeTab={activeTab}
          onTabChange={handleTabChange}
          unreadCount={contactSlots.filter(c => c?.unread > 0).length}
          hasNewRewards={hasNewRewards}
          theme={theme}
        />
        
        {/* Contact Picker Modal */}
        {showContactPicker && (
          <ContactPicker
            isOpen={showContactPicker}
            onClose={() => {
              setShowContactPicker(false);
              setSelectedSlot(null);
            }}
            onSelectContact={handleSelectContactFromPicker}
            excludedNumbers={excludedNumbers}
          />
        )}
      </div>
    );
  }
  
  // Desktop layout (existing code)
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
                className={`action-btn ${view === 'rewards' ? 'active' : ''}`}
                onClick={() => setView('rewards')}
                title="Rewards & Achievements"
              >
                <Trophy className="w-5 h-5" />
              </button>
              <button 
                className="action-btn"
                onClick={() => setView(view === 'integration' ? 'contacts' : 'integration')}
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
              <div className={`sync-status-dot ${syncStatus}`}>
                {getSyncIcon(syncStatus)}
              </div>
            </div>
            {/* WhatsApp Status Indicator */}
            {whatsappStatus.isReady && (
              <div className="whatsapp-status-badge">
                <MessageCircle className="w-3 h-3" />
                <span>{whatsappStatus.contactCount} contacts</span>
              </div>
            )}
            {/* Locked Slots Indicator */}
            {areAllSlotsFilled && (
              <div className="locked-slots-badge">
                <span>🔒 All slots locked</span>
              </div>
            )}
          </div>

          {/* Search Bar */}
          <div className="search-container">
            <div className="search-bar">
              <Search className="w-4 h-4 text-secondary" />
              <input
                type="text"
                placeholder="Search or start new chat"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
              {isSearching && <Loader className="w-4 h-4 animate-spin" />}
            </div>
          </div>

          {/* Contact List - 5 Slots */}
          <div className="memory-list">
            {/* Display 5 contact slots */}
            {Array.isArray(contactSlots) && contactSlots.map((contact, index) => (
              <div key={`slot-${index}`}>
                {contact === null ? (
                  // Empty slot
                  <div
                    className={`memory-item empty-slot ${!canChangeSlot(index) ? 'slot-locked' : ''}`}
                    onClick={() => handleAddContact(index)}
                  >
                    <div className="memory-avatar empty-avatar">
                      {!canChangeSlot(index) ? (
                        <Lock className="w-6 h-6" />
                      ) : (
                        <Plus className="w-6 h-6" />
                      )}
                    </div>
                    <div className="memory-content">
                      <div className="memory-header">
                        <h3 className="memory-name">Slot {index + 1}</h3>
                        {slotChangeCounts[index] > 0 && (
                          <div className="changes-badge">
                            {getRemainingChanges(index) > 0 ? (
                              <span className="changes-remaining">
                                {getRemainingChanges(index)} change left
                              </span>
                            ) : (
                              <span className="no-changes">
                                <Lock className="w-3 h-3" /> Locked
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="memory-preview">
                        <p className="memory-last-message">
                          {!canChangeSlot(index) ? 'Slot locked - no changes remaining' : 'Tap to add contact'}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  // Filled slot
                  <div
                    className={`memory-item ${selectedContact?.id === contact.id ? 'active' : ''} ${!canChangeSlot(index) ? 'slot-locked' : ''}`}
                    onClick={() => {
                      setSelectedContact(contact);
                      setView('categories');
                    }}
                  >
                    <div className="memory-avatar" style={{background: contact.avatarColor}}>
                      <span className="avatar-text">{getAvatar(contact)}</span>
                      {contact.isPinned && (
                        <div className="pin-badge">
                          📌
                        </div>
                      )}
                      {!canChangeSlot(index) && (
                        <div className="lock-badge">
                          <Lock className="w-3 h-3" />
                        </div>
                      )}
                    </div>
                    <div className="memory-content">
                      <div className="memory-header">
                        <h3 className="memory-name">{contact.name}</h3>
                        <div className="contact-actions">
                          {getRemainingChanges(index) === 1 && (
                            <span className="change-warning">
                              <AlertTriangle className="w-3 h-3" /> 1 change left
                            </span>
                          )}
                          {getRemainingChanges(index) === 0 && (
                            <span className="locked-indicator">
                              <Lock className="w-3 h-3" /> Locked
                            </span>
                          )}
                          <span className={`memory-time ${contact.unread > 0 ? 'unread-time' : ''}`}>
                            {contact.lastMessageTime}
                          </span>
                          {/* Only show remove button if slot can be changed */}
                          {canChangeSlot(index) && (
                            <button
                              className="remove-contact-btn"
                              onClick={(e) => handleRemoveContact(index, e)}
                              title="Remove contact"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                      <div className="memory-preview">
                        {contact.isTyping ? (
                          <p className="typing-indicator">typing...</p>
                        ) : (
                          <p className="memory-last-message">{contact.lastMessage}</p>
                        )}
                        {contact.unread > 0 && (
                          <span className="unread-badge">{contact.unread}</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {/* Upgrade to Premium Slot */}
            {!isPremium && (
              <div className="memory-item upgrade-slot" onClick={() => alert('Premium features coming soon!')}>
                <div className="memory-avatar premium">
                  <span className="avatar-text">⭐</span>
                </div>
                <div className="memory-content">
                  <div className="memory-header">
                    <h3 className="memory-name premium-text">Upgrade to Premium</h3>
                  </div>
                  <div className="memory-preview">
                    <p className="memory-last-message premium-subtitle">
                      Unlimited contacts • Advanced AI • Priority sync
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="main-content">
          {view === 'categories' ? (
            <MemoryCategories
              contact={selectedContact}
              onBack={() => setView('contacts')}
              onSelectCategory={(category) => {
                setSelectedCategory(category);
                setView('chat');
              }}
              theme={theme}
            />
          ) : view === 'chat' ? (
            <>
              {/* Chat Header */}
              <div className="chat-header">
                <div className="chat-info">
                  <div className="chat-avatar" style={{background: selectedContact?.avatarColor || '#25D366'}}>
                    <span className="avatar-emoji">{selectedContact ? getAvatar(selectedContact) : '👤'}</span>
                  </div>
                  <div className="chat-details">
                    <h2 className="chat-name">{selectedContact?.name || 'Select a contact'}</h2>
                    <div className="chat-status">
                      {selectedContact ? (
                        <>
                          {selectedContact.isTyping ? (
                            <span className="typing-text">typing...</span>
                          ) : (
                            <span className="status-text">{selectedContact.phoneNumber}</span>
                          )}
                          {wsConnected && (
                            <span className="whatsapp-badge">WhatsApp Synced</span>
                          )}
                        </>
                      ) : (
                        <span className="status-text">Start a conversation</span>
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

              {/* Chat Messages / Memories Display */}
              <div className="chat-messages">
                {error && (
                  <div className="error-message">
                    <AlertCircle className="w-5 h-5" />
                    <span>{error}</span>
                  </div>
                )}
                
                {loading ? (
                  <div className="loading-container">
                    <Loader className="w-8 h-8 animate-spin text-primary" />
                    <p>Loading memories...</p>
                  </div>
                ) : displayMemories && displayMemories.length > 0 ? (
                  <div className="memories-container">
                    {displayMemories && displayMemories.map((memory) => (
                      <div key={memory.id} className="memory-card">
                        <div className="memory-card-header">
                          <span className="memory-category">{memory.category}</span>
                          <span className="memory-timestamp">
                            {new Date(memory.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <div className="memory-card-content">
                          <p>{memory.content}</p>
                        </div>
                        {memory.tags && Array.isArray(memory.tags) && memory.tags.length > 0 && (
                          <div className="memory-tags">
                            {memory.tags.map((tag, index) => (
                              <span key={index} className="memory-tag">#{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="welcome-message">
                    <div className="welcome-content">
                      <div className="whatsapp-style-welcome">
                        <div className="locked-icon">🔒</div>
                        <h3>Messages are end-to-end encrypted</h3>
                        <p>No one outside of this chat can read or listen to them. Click to learn more.</p>
                      </div>
                      {selectedContact && (
                        <div className="contact-intro">
                          <div className="intro-avatar" style={{background: selectedContact.avatarColor}}>
                            {getAvatar(selectedContact)}
                          </div>
                          <h4>{selectedContact.name}</h4>
                          <p className="phone-number">{selectedContact.phoneNumber}</p>
                          <p className="intro-text">This is the beginning of your conversation with {selectedContact.name}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Message Input */}
              <div className="message-input-container">
                <div className="message-input">
                  <input
                    type="text"
                    placeholder={selectedContact ? `Message ${selectedContact.name}` : 'Select a contact to start messaging'}
                    className="message-text-input"
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                    disabled={sendingMessage}
                  />
                  <button 
                    className="send-button"
                    onClick={handleSendMessage}
                    disabled={sendingMessage || !messageInput.trim()}
                  >
                    {sendingMessage ? (
                      <Loader className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
                <p className="sync-status-text">
                  {wsConnected ? 'Synced across platforms' : 'Offline - memories will sync when connected'}
                </p>
              </div>
            </>
          ) : view === 'rewards' ? (
            /* Rewards Tab View */
            <RewardsTab
              userId={userId}
              theme={theme}
              gamificationService={gamificationService}
              wsService={wsService}
            />
          ) : view === 'contacts' ? (
            /* Welcome View */
            <div className="welcome-view">
              <div className="welcome-content">
                <Brain className="welcome-icon" />
                <h2 className="welcome-title">Welcome to Memo</h2>
                <p className="welcome-subtitle">Select a contact to view their memory categories</p>
                <div className="welcome-features">
                  <div className="feature-item">
                    <MessageCircle className="feature-icon" />
                    <span>WhatsApp Sync</span>
                  </div>
                  <div className="feature-item">
                    <Brain className="feature-icon" />
                    <span>AI-Powered Memories</span>
                  </div>
                  <div className="feature-item">
                    <Shield className="feature-icon" />
                    <span>Secure Storage</span>
                  </div>
                </div>
              </div>
            </div>
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
                      <p className={`status-${wsConnected ? 'connected' : 'disconnected'}`}>
                        {wsConnected ? 'Connected & Syncing' : 'Disconnected'}
                      </p>
                    </div>
                  </div>
                  
                  <div className="sync-features">
                    <div className="feature-row">
                      <Wifi className={`w-5 h-5 ${wsConnected ? 'text-green-500' : 'text-red-500'}`} />
                      <span>Message Sync</span>
                      <span className={`feature-status ${wsConnected ? 'active' : 'inactive'}`}>
                        {wsConnected ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="feature-row">
                      <Phone className={`w-5 h-5 ${wsConnected ? 'text-green-500' : 'text-red-500'}`} />
                      <span>Voice Calls</span>
                      <span className={`feature-status ${wsConnected ? 'active' : 'inactive'}`}>
                        {wsConnected ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="feature-row">
                      <Video className={`w-5 h-5 ${wsConnected ? 'text-green-500' : 'text-red-500'}`} />
                      <span>Video Calls</span>
                      <span className={`feature-status ${wsConnected ? 'active' : 'inactive'}`}>
                        {wsConnected ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="activity-feed">
                  <h4>Recent Cross-Platform Activity</h4>
                  <div className="activity-list">
                    {activities && activities.length > 0 ? (
                      activities.map((activity) => (
                        <div key={activity.id} className="activity-item">
                          <div className={`activity-icon ${activity.source}`}>
                            {activity.icon}
                          </div>
                          <div className="activity-content">
                            <p><strong>{activity.source === 'whatsapp' ? 'WhatsApp' : 'Memo App'}:</strong> {activity.message}</p>
                            <span className="activity-time">{activity.timestamp}</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="no-activity">No recent activity</p>
                    )}
                  </div>
                </div>

                <div className="integration-info">
                  <h4>How to Use WhatsApp Integration</h4>
                  <ol>
                    <li>Save the bot number: +1 (555) 123-4567</li>
                    <li>Send "Hi" to start</li>
                    <li>Your messages will automatically sync here</li>
                    <li>Use voice messages for instant transcription</li>
                  </ol>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Contact Picker Modal */}
      <ContactPicker
        isOpen={showContactPicker}
        onClose={() => {
          setShowContactPicker(false);
          setSelectedSlot(null);
        }}
        onSelectContact={handleSelectContactFromPicker}
        excludedNumbers={excludedNumbers}
      />
      
      {/* Change Warning Modal */}
      {showChangeWarning && (
        <div className="modal-backdrop" onClick={() => setShowChangeWarning(false)}>
          <div className="warning-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <AlertTriangle className="warning-icon" />
              <h2>Contact Change Limit</h2>
            </div>
            
            <div className="modal-content">
              <div className="warning-message">
                <Info className="info-icon" />
                <div>
                  <p className="warning-title">Free Plan Limitation</p>
                  <p className="warning-text">
                    {pendingContactChange?.action === 'remove' ? (
                      <>You are about to use your <strong>last change</strong> for Slot {warningSlotIndex + 1}. 
                      After this, the slot will be <strong>permanently locked</strong> and cannot be changed again.</>
                    ) : (
                      <>You can only change each contact slot <strong>once</strong> on the Free plan. 
                      This slot already has a contact. Changing it will use your one allowed change.</>
                    )}
                  </p>
                </div>
              </div>
              
              <div className="upgrade-notice">
                <Shield className="shield-icon" />
                <div>
                  <p className="upgrade-title">Upgrade to Premium</p>
                  <p className="upgrade-text">Get unlimited contact changes, advanced AI features, and priority sync</p>
                </div>
              </div>
            </div>
            
            <div className="modal-actions">
              <button 
                className="btn-cancel" 
                onClick={() => {
                  setShowChangeWarning(false);
                  setWarningSlotIndex(null);
                  setPendingContactChange(null);
                }}
              >
                Cancel
              </button>
              <button 
                className="btn-confirm" 
                onClick={handleConfirmChange}
              >
                {pendingContactChange?.action === 'remove' ? 'Remove Contact' : 'Continue'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoryApp;