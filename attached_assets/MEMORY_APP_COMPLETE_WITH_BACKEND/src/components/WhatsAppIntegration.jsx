import React, { useState } from 'react';
import { MessageCircle, Phone, Video, Settings, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const WhatsAppIntegration = () => {
  const [integrationStatus, setIntegrationStatus] = useState('connected');
  
  const syncFeatures = [
    {
      icon: MessageCircle,
      title: 'Message Sync',
      description: 'All conversations with Memo are synchronized between apps',
      status: 'active',
      lastSync: '2 minutes ago'
    },
    {
      icon: Phone,
      title: 'Voice Calls',
      description: 'Voice Memory Numbers work across both platforms',
      status: 'active',
      lastSync: '1 minute ago'
    },
    {
      icon: Video,
      title: 'Video Calls',
      description: 'Video calls with screen sharing for memory capture',
      status: 'active',
      lastSync: 'Just now'
    }
  ];

  const recentActivity = [
    {
      type: 'message',
      platform: 'whatsapp',
      content: 'Memory saved: Meeting notes from marketing team',
      timestamp: '2:30 PM',
      synced: true
    },
    {
      type: 'voice',
      platform: 'memo-app',
      content: 'Voice memo recorded and transcribed',
      timestamp: '2:15 PM',
      synced: true
    },
    {
      type: 'message',
      platform: 'whatsapp',
      content: 'Retrieved family birthday memories',
      timestamp: '1:45 PM',
      synced: true
    }
  ];

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'syncing':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    }
  };

  const getPlatformBadge = (platform) => {
    return platform === 'whatsapp' ? (
      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
        WhatsApp
      </Badge>
    ) : (
      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
        Memo App
      </Badge>
    );
  };

  return (
    <div className="whatsapp-integration">
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-green-600" />
            WhatsApp Integration Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="integration-status">
            <div className="status-header">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="font-semibold text-green-700">Connected & Syncing</span>
              </div>
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </Button>
            </div>
            
            <div className="sync-features-grid">
              {syncFeatures.map((feature, index) => (
                <div key={index} className="feature-card">
                  <div className="feature-header">
                    <feature.icon className="w-5 h-5 text-gray-600" />
                    <span className="feature-title">{feature.title}</span>
                    {getStatusIcon(feature.status)}
                  </div>
                  <p className="feature-description">{feature.description}</p>
                  <span className="last-sync">Last sync: {feature.lastSync}</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Cross-Platform Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="activity-list">
            {recentActivity.map((activity, index) => (
              <div key={index} className="activity-item">
                <div className="activity-content">
                  <div className="activity-header">
                    {getPlatformBadge(activity.platform)}
                    <span className="activity-time">{activity.timestamp}</span>
                  </div>
                  <p className="activity-text">{activity.content}</p>
                </div>
                <div className="sync-status">
                  {activity.synced ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : (
                    <Clock className="w-4 h-4 text-yellow-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default WhatsAppIntegration;

