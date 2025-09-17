import React, { useState, useEffect } from 'react';
import { Smartphone, MessageCircle, Phone, Wifi, WifiOff } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const SyncIndicator = ({ isConnected = true }) => {
  const [syncStatus, setSyncStatus] = useState('synced');
  const [lastSync, setLastSync] = useState(new Date());

  useEffect(() => {
    // Simulate sync status updates
    const interval = setInterval(() => {
      setLastSync(new Date());
      setSyncStatus('synced');
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="sync-indicator">
      <div className="sync-status">
        <div className="sync-platforms">
          <div className="platform-item">
            <Smartphone className="w-4 h-4" />
            <span>Memo App</span>
            <Badge variant={isConnected ? "default" : "secondary"} className="ml-2">
              {isConnected ? "Online" : "Offline"}
            </Badge>
          </div>
          <div className="sync-arrow">⟷</div>
          <div className="platform-item">
            <MessageCircle className="w-4 h-4" />
            <span>WhatsApp</span>
            <Badge variant={isConnected ? "default" : "secondary"} className="ml-2">
              {isConnected ? "Synced" : "Pending"}
            </Badge>
          </div>
        </div>
        
        <div className="sync-features">
          <div className="feature-item">
            <MessageCircle className="w-3 h-3" />
            <span>Messages</span>
            {isConnected && <div className="sync-dot active"></div>}
          </div>
          <div className="feature-item">
            <Phone className="w-3 h-3" />
            <span>Voice Calls</span>
            {isConnected && <div className="sync-dot active"></div>}
          </div>
          <div className="feature-item">
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            <span>Real-time Sync</span>
            {isConnected && <div className="sync-dot active"></div>}
          </div>
        </div>
        
        <div className="last-sync">
          <span className="sync-text">
            Last sync: {formatTime(lastSync)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SyncIndicator;

