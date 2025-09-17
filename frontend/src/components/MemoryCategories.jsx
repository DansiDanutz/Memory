import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft,
  User,
  Users,
  Calendar,
  StickyNote,
  Mic,
  Image,
  Shield,
  Brain,
  Heart,
  Briefcase,
  ChevronRight,
  Lock,
  Star,
  FileText,
  Clock,
  Inbox
} from 'lucide-react';
import './MemoryCategories.css';

const MemoryCategories = ({ contact, onBack, onSelectCategory, theme }) => {
  const [categoryCounts, setCategoryCounts] = useState({});
  const [loading, setLoading] = useState(false);
  
  // Define memory categories with icons and descriptions
  const categories = [
    {
      id: 'transcripts',
      name: 'Transcripts',
      icon: FileText,
      description: 'Raw conversation data awaiting analysis',
      color: '#8b5cf6',
      bgGradient: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(168, 85, 247, 0.08))',
      special: true,
      processingStatus: 'inbox'
    },
    {
      id: 'personal',
      name: 'Personal Memories',
      icon: User,
      description: 'Private thoughts and personal experiences',
      color: '#00ffa3',
      bgGradient: 'linear-gradient(135deg, rgba(0, 255, 163, 0.1), rgba(0, 255, 163, 0.05))'
    },
    {
      id: 'shared',
      name: 'Shared Experiences',
      icon: Users,
      description: 'Memories shared with this contact',
      color: '#25d366',
      bgGradient: 'linear-gradient(135deg, rgba(37, 211, 102, 0.1), rgba(37, 211, 102, 0.05))'
    },
    {
      id: 'important_dates',
      name: 'Important Dates',
      icon: Calendar,
      description: 'Birthdays, anniversaries, and special events',
      color: '#ffd700',
      bgGradient: 'linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(255, 215, 0, 0.05))'
    },
    {
      id: 'notes',
      name: 'Notes & Reminders',
      icon: StickyNote,
      description: 'Quick notes and reminders about this contact',
      color: '#ff6b6b',
      bgGradient: 'linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(255, 107, 107, 0.05))'
    },
    {
      id: 'voice',
      name: 'Voice Messages',
      icon: Mic,
      description: 'Audio recordings and voice notes',
      color: '#4facfe',
      bgGradient: 'linear-gradient(135deg, rgba(79, 172, 254, 0.1), rgba(79, 172, 254, 0.05))'
    },
    {
      id: 'media',
      name: 'Media & Photos',
      icon: Image,
      description: 'Photos, videos, and documents shared',
      color: '#f093fb',
      bgGradient: 'linear-gradient(135deg, rgba(240, 147, 251, 0.1), rgba(240, 147, 251, 0.05))'
    },
    {
      id: 'work',
      name: 'Professional',
      icon: Briefcase,
      description: 'Work-related conversations and tasks',
      color: '#667eea',
      bgGradient: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(102, 126, 234, 0.05))'
    },
    {
      id: 'confidential',
      name: 'Confidential',
      icon: Shield,
      description: 'Encrypted and sensitive information',
      color: '#ff4444',
      bgGradient: 'linear-gradient(135deg, rgba(255, 68, 68, 0.1), rgba(255, 68, 68, 0.05))',
      locked: true
    }
  ];

  // Load category counts on mount
  useEffect(() => {
    loadCategoryCounts();
  }, [contact]);

  const loadCategoryCounts = () => {
    // Mock data for now - will integrate with backend later
    const mockCounts = {
      transcripts: 0,  // Always shows as empty or processing
      personal: 24,
      shared: 18,
      important_dates: 7,
      notes: 15,
      voice: 3,
      media: 42,
      work: 9,
      confidential: 5
    };
    setCategoryCounts(mockCounts);
  };

  const handleCategoryClick = (category) => {
    if (category.locked) {
      // Show premium prompt or unlock dialog
      console.log('This category requires premium access');
      return;
    }
    onSelectCategory(category);
  };

  const getTotalMemories = () => {
    return Object.values(categoryCounts).reduce((sum, count) => sum + count, 0);
  };

  const getAvatarInitials = () => {
    if (!contact) return '?';
    const names = contact.name.split(' ');
    if (names.length >= 2) {
      return names[0][0] + names[1][0];
    }
    return contact.name.slice(0, 2).toUpperCase();
  };

  const getAvatarColor = () => {
    const colors = [
      'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
      'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
      'linear-gradient(135deg, #30cfd0 0%, #330867 100%)'
    ];
    
    // Generate consistent color based on contact name
    const charCode = contact?.name.charCodeAt(0) || 0;
    return colors[charCode % colors.length];
  };

  if (!contact) {
    return (
      <div className="memory-categories-empty">
        <Brain className="empty-icon" />
        <h3>No Contact Selected</h3>
        <p>Select a contact to view their memory categories</p>
      </div>
    );
  }

  return (
    <div className="memory-categories" data-theme={theme}>
      {/* Header */}
      <div className="categories-header">
        <button className="back-button" onClick={onBack}>
          <ArrowLeft className="w-5 h-5" />
        </button>
        
        <div className="contact-info">
          <div 
            className="contact-avatar"
            style={{ background: getAvatarColor() }}
          >
            <span className="avatar-text">{getAvatarInitials()}</span>
          </div>
          <div className="contact-details">
            <h2 className="contact-name">{contact.name}</h2>
            <p className="contact-phone">{contact.phoneNumber}</p>
          </div>
        </div>

        <div className="memory-stats">
          <div className="stat-item">
            <span className="stat-value">{getTotalMemories()}</span>
            <span className="stat-label">Total Memories</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{categories.length}</span>
            <span className="stat-label">Categories</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <button className="quick-action-btn featured">
          <Star className="w-4 h-4" />
          <span>Favorites</span>
          <span className="action-count">12</span>
        </button>
        <button className="quick-action-btn recent">
          <Brain className="w-4 h-4" />
          <span>Recent</span>
          <span className="action-count">8</span>
        </button>
        <button className="quick-action-btn emotional">
          <Heart className="w-4 h-4" />
          <span>Emotional</span>
          <span className="action-count">5</span>
        </button>
      </div>

      {/* Category Grid */}
      <div className="categories-grid">
        {categories.map((category) => {
          const IconComponent = category.icon;
          const count = categoryCounts[category.id] || 0;
          
          return (
            <div
              key={category.id}
              className={`category-card ${category.locked ? 'locked' : ''} ${category.special ? 'special-transcript' : ''} ${count === 0 && !category.special ? 'empty' : ''}`}
              onClick={() => handleCategoryClick(category)}
              style={{ background: category.bgGradient }}
            >
              <div className="category-header">
                <div 
                  className="category-icon"
                  style={{ color: category.color }}
                >
                  <IconComponent className="w-6 h-6" />
                </div>
                {category.locked && (
                  <Lock className="lock-icon w-4 h-4" />
                )}
                {category.special && (
                  <div className="processing-badge" title="Data waiting to be processed">
                    <Inbox className="w-4 h-4" />
                    <span>Inbox</span>
                  </div>
                )}
              </div>
              
              <div className="category-content">
                <h3 className="category-name">{category.name}</h3>
                <p className="category-description">{category.description}</p>
                
                <div className="category-footer">
                  <span className="memory-count">
                    {category.special ? (
                      <span className="processing-text">
                        <Clock className="w-3 h-3 inline-block mr-1" />
                        Processing...
                      </span>
                    ) : (
                      `${count} ${count === 1 ? 'memory' : 'memories'}`
                    )}
                  </span>
                  <ChevronRight className="arrow-icon w-4 h-4" />
                </div>
              </div>

              {count > 0 && (
                <div className="category-activity">
                  <div className="activity-bar" style={{
                    width: `${Math.min((count / 50) * 100, 100)}%`,
                    background: category.color
                  }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Recent Activity */}
      <div className="recent-activity">
        <h3 className="activity-title">Recent Activity</h3>
        <div className="activity-list">
          <div className="activity-item">
            <div className="activity-icon">
              <Brain className="w-4 h-4" />
            </div>
            <div className="activity-content">
              <p className="activity-text">New memory added to Personal</p>
              <span className="activity-time">2 hours ago</span>
            </div>
          </div>
          <div className="activity-item">
            <div className="activity-icon">
              <Image className="w-4 h-4" />
            </div>
            <div className="activity-content">
              <p className="activity-text">3 photos added to Media</p>
              <span className="activity-time">Yesterday</span>
            </div>
          </div>
          <div className="activity-item">
            <div className="activity-icon">
              <Calendar className="w-4 h-4" />
            </div>
            <div className="activity-content">
              <p className="activity-text">Birthday reminder set</p>
              <span className="activity-time">3 days ago</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MemoryCategories;