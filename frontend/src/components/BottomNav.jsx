import React, { useState, useEffect } from 'react';
import { 
  Home, 
  MessageCircle, 
  Trophy, 
  Users, 
  User,
  Plus,
  Bell
} from 'lucide-react';
import './BottomNav.css';

const BottomNav = ({ 
  activeTab, 
  onTabChange, 
  unreadCount = 0, 
  hasNewRewards = false,
  theme 
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);
  const [showFloatingAction, setShowFloatingAction] = useState(false);
  
  // Navigation tabs configuration
  const tabs = [
    {
      id: 'home',
      label: 'Home',
      icon: Home,
      badge: null
    },
    {
      id: 'chat',
      label: 'Chat',
      icon: MessageCircle,
      badge: unreadCount > 0 ? unreadCount : null
    },
    {
      id: 'rewards',
      label: 'Rewards',
      icon: Trophy,
      badge: hasNewRewards ? 'NEW' : null,
      special: true // Special styling for rewards
    },
    {
      id: 'contacts',
      label: 'Contacts',
      icon: Users,
      badge: null
    },
    {
      id: 'profile',
      label: 'Profile',
      icon: User,
      badge: null
    }
  ];
  
  // Hide/show navigation on scroll
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      if (currentScrollY < 100) {
        setIsVisible(true);
      } else if (currentScrollY > lastScrollY) {
        // Scrolling down - hide
        setIsVisible(false);
        setShowFloatingAction(false);
      } else {
        // Scrolling up - show
        setIsVisible(true);
        setShowFloatingAction(true);
      }
      
      setLastScrollY(currentScrollY);
    };
    
    // Add passive listener for better performance
    window.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);
  
  // Handle tab press with haptic feedback simulation
  const handleTabPress = (tabId) => {
    // Trigger haptic feedback if available
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
    
    // Add press animation class
    const element = document.getElementById(`tab-${tabId}`);
    if (element) {
      element.classList.add('pressed');
      setTimeout(() => {
        element.classList.remove('pressed');
      }, 200);
    }
    
    onTabChange(tabId);
  };
  
  // Long press handler for additional actions
  const handleLongPress = (tabId) => {
    if (navigator.vibrate) {
      navigator.vibrate([10, 50, 10]);
    }
    
    // Could open quick actions menu
    console.log(`Long press on ${tabId}`);
  };
  
  // Touch event handlers
  const handleTouchStart = (e, tabId) => {
    const timer = setTimeout(() => {
      handleLongPress(tabId);
    }, 500);
    
    e.currentTarget.dataset.timer = timer;
  };
  
  const handleTouchEnd = (e) => {
    const timer = e.currentTarget.dataset.timer;
    if (timer) {
      clearTimeout(parseInt(timer));
    }
  };
  
  return (
    <>
      {/* Floating Action Button */}
      {showFloatingAction && (
        <button 
          className={`floating-action-btn ${theme === 'dark' ? 'dark' : ''}`}
          onClick={() => console.log('FAB clicked')}
          aria-label="Quick action"
        >
          <Plus className="w-6 h-6" />
          <span className="fab-tooltip">Quick Memory</span>
        </button>
      )}
      
      {/* Bottom Navigation Bar */}
      <nav 
        className={`bottom-nav ${isVisible ? '' : 'hidden'} ${theme === 'dark' ? 'dark' : ''}`}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="bottom-nav-container">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            
            return (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                className={`nav-tab ${isActive ? 'active' : ''} ${tab.special ? 'special' : ''}`}
                onClick={() => handleTabPress(tab.id)}
                onTouchStart={(e) => handleTouchStart(e, tab.id)}
                onTouchEnd={handleTouchEnd}
                aria-label={tab.label}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className="nav-tab-content">
                  <div className="icon-wrapper">
                    <Icon 
                      className={`tab-icon ${isActive ? 'active-icon' : ''}`}
                      size={24}
                    />
                    {tab.badge && (
                      <span className={`tab-badge ${typeof tab.badge === 'string' ? 'text-badge' : ''}`}>
                        {tab.badge}
                      </span>
                    )}
                  </div>
                  <span className={`tab-label ${isActive ? 'active-label' : ''}`}>
                    {tab.label}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
        
        {/* Safe area padding for notched devices */}
        <div className="safe-area-bottom" />
      </nav>
    </>
  );
};

export default BottomNav;