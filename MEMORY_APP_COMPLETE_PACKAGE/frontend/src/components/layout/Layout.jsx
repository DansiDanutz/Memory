import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';
import { useMemory } from '../../contexts/MemoryContext';
import { useSync } from '../../contexts/SyncContext';

// Components
import Sidebar from './Sidebar';
import Header from './Header';
import MobileNavigation from './MobileNavigation';
import SyncIndicator from '../sync/SyncIndicator';
import NotificationContainer from '../ui/NotificationContainer';

// Hooks
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { BREAKPOINTS } from '../../utils/constants';

const Layout = () => {
  const location = useLocation();
  const { isDark } = useTheme();
  const { activeMemory } = useMemory();
  const { syncStatus } = useSync();
  const isMobile = useMediaQuery(`(max-width: ${BREAKPOINTS.MD}px)`);
  
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [isLoading, setIsLoading] = useState(true);

  // Close sidebar on mobile when route changes
  useEffect(() => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  }, [location.pathname, isMobile]);

  // Handle loading state
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  // Toggle sidebar
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Close sidebar (for mobile)
  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="text-muted-foreground">Loading Memory App...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`memory-app ${isDark ? 'dark' : ''}`}>
      <div className="app-layout">
        {/* Sidebar */}
        <div className={`sidebar-container ${isMobile && !sidebarOpen ? 'hidden' : ''}`}>
          <Sidebar onClose={closeSidebar} />
        </div>

        {/* Mobile Overlay */}
        {isMobile && sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={closeSidebar}
          />
        )}

        {/* Main Content */}
        <div className="main-content">
          {/* Header */}
          <Header 
            onToggleSidebar={toggleSidebar}
            sidebarOpen={sidebarOpen}
            activeMemory={activeMemory}
          />

          {/* Sync Indicator */}
          {syncStatus !== 'disconnected' && (
            <div className="px-4 py-2 border-b border-border">
              <SyncIndicator />
            </div>
          )}

          {/* Page Content */}
          <main className="flex-1 overflow-hidden">
            <Outlet />
          </main>

          {/* Mobile Navigation */}
          {isMobile && (
            <MobileNavigation />
          )}
        </div>
      </div>

      {/* Global Notifications */}
      <NotificationContainer />
    </div>
  );
};

export default Layout;

