import React from 'react';
import './SkeletonLoaders.css';

// Message skeleton loader
export const MessageSkeleton = ({ count = 3 }) => {
  return (
    <div className="skeleton-messages">
      {[...Array(count)].map((_, index) => (
        <div key={index} className={`skeleton-message ${index % 2 === 0 ? 'sent' : 'received'}`}>
          {index % 2 !== 0 && (
            <div className="skeleton-avatar skeleton-pulse"></div>
          )}
          <div className="skeleton-bubble">
            <div className="skeleton-text skeleton-shimmer"></div>
            <div className="skeleton-text skeleton-shimmer short delay-100"></div>
            <div className="skeleton-time skeleton-shimmer delay-200"></div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Contact card skeleton loader
export const ContactSkeleton = ({ count = 5 }) => {
  return (
    <div className="skeleton-contacts">
      {[...Array(count)].map((_, index) => (
        <div key={index} className="skeleton-contact glass-card">
          <div className="skeleton-contact-avatar skeleton-pulse"></div>
          <div className="skeleton-contact-info">
            <div className="skeleton-name skeleton-shimmer"></div>
            <div className="skeleton-status skeleton-shimmer delay-100"></div>
          </div>
          <div className="skeleton-badge skeleton-pulse delay-200"></div>
        </div>
      ))}
    </div>
  );
};

// Category card skeleton loader
export const CategorySkeleton = ({ count = 6 }) => {
  return (
    <div className="skeleton-categories">
      {[...Array(count)].map((_, index) => (
        <div key={index} className="skeleton-category glass-card">
          <div className="skeleton-category-header">
            <div className="skeleton-icon skeleton-pulse"></div>
            <div className="skeleton-count skeleton-pulse delay-100"></div>
          </div>
          <div className="skeleton-category-content">
            <div className="skeleton-title skeleton-shimmer"></div>
            <div className="skeleton-description skeleton-shimmer delay-100"></div>
            <div className="skeleton-description skeleton-shimmer short delay-200"></div>
          </div>
          <div className="skeleton-category-footer">
            <div className="skeleton-tag skeleton-shimmer"></div>
            <div className="skeleton-tag skeleton-shimmer delay-100"></div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Memory item skeleton loader
export const MemorySkeleton = ({ count = 4 }) => {
  return (
    <div className="skeleton-memories">
      {[...Array(count)].map((_, index) => (
        <div key={index} className="skeleton-memory glass-card">
          <div className="skeleton-memory-header">
            <div className="skeleton-date skeleton-shimmer"></div>
            <div className="skeleton-category-badge skeleton-pulse"></div>
          </div>
          <div className="skeleton-memory-content">
            <div className="skeleton-text skeleton-shimmer"></div>
            <div className="skeleton-text skeleton-shimmer delay-100"></div>
            <div className="skeleton-text skeleton-shimmer short delay-200"></div>
          </div>
          <div className="skeleton-memory-footer">
            <div className="skeleton-emotion skeleton-pulse"></div>
            <div className="skeleton-actions">
              <div className="skeleton-action skeleton-pulse delay-100"></div>
              <div className="skeleton-action skeleton-pulse delay-200"></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Profile skeleton loader
export const ProfileSkeleton = () => {
  return (
    <div className="skeleton-profile glass-card">
      <div className="skeleton-profile-header">
        <div className="skeleton-profile-avatar skeleton-pulse"></div>
        <div className="skeleton-profile-info">
          <div className="skeleton-profile-name skeleton-shimmer"></div>
          <div className="skeleton-profile-status skeleton-shimmer delay-100"></div>
          <div className="skeleton-profile-bio skeleton-shimmer delay-200"></div>
        </div>
      </div>
      <div className="skeleton-profile-stats">
        <div className="skeleton-stat glass-card">
          <div className="skeleton-stat-value skeleton-pulse"></div>
          <div className="skeleton-stat-label skeleton-shimmer delay-100"></div>
        </div>
        <div className="skeleton-stat glass-card">
          <div className="skeleton-stat-value skeleton-pulse delay-100"></div>
          <div className="skeleton-stat-label skeleton-shimmer delay-200"></div>
        </div>
        <div className="skeleton-stat glass-card">
          <div className="skeleton-stat-value skeleton-pulse delay-200"></div>
          <div className="skeleton-stat-label skeleton-shimmer delay-300"></div>
        </div>
      </div>
    </div>
  );
};

// Loading spinner with glass effect
export const GlassSpinner = ({ size = 'medium', text = 'Loading...' }) => {
  return (
    <div className={`glass-spinner ${size}`}>
      <div className="spinner-container">
        <div className="spinner-ring"></div>
        <div className="spinner-ring delay-100"></div>
        <div className="spinner-ring delay-200"></div>
      </div>
      {text && <p className="spinner-text">{text}</p>}
    </div>
  );
};

// Progress bar with glass effect
export const GlassProgress = ({ value = 0, max = 100, label = '' }) => {
  const percentage = Math.min((value / max) * 100, 100);
  
  return (
    <div className="glass-progress">
      {label && <div className="progress-label">{label}</div>}
      <div className="progress-bar glass">
        <div 
          className="progress-fill"
          style={{ width: `${percentage}%` }}
        >
          <div className="progress-glow"></div>
        </div>
      </div>
      <div className="progress-value">{Math.round(percentage)}%</div>
    </div>
  );
};

// Wave loading animation
export const WaveLoader = ({ text = 'Processing' }) => {
  return (
    <div className="wave-loader">
      <div className="wave-text">
        {text.split('').map((char, index) => (
          <span 
            key={index} 
            className="wave-char"
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            {char}
          </span>
        ))}
      </div>
      <div className="wave-dots">
        <span className="wave-dot"></span>
        <span className="wave-dot delay-200"></span>
        <span className="wave-dot delay-400"></span>
      </div>
    </div>
  );
};

// Typing indicator
export const TypingIndicator = () => {
  return (
    <div className="typing-indicator glass">
      <div className="typing-dot"></div>
      <div className="typing-dot delay-100"></div>
      <div className="typing-dot delay-200"></div>
    </div>
  );
};

// Page transition wrapper
export const PageTransition = ({ children, isLoading }) => {
  if (isLoading) {
    return (
      <div className="page-transition loading">
        <div className="transition-overlay glass"></div>
        <GlassSpinner size="large" text="Loading page..." />
      </div>
    );
  }
  
  return (
    <div className="page-transition loaded">
      {children}
    </div>
  );
};

// Skeleton container with fade transition
export const SkeletonContainer = ({ isLoading, skeleton, children }) => {
  return (
    <div className="skeleton-container">
      <div className={`skeleton-wrapper ${!isLoading ? 'fade-out' : ''}`}>
        {skeleton}
      </div>
      <div className={`content-wrapper ${!isLoading ? 'fade-in' : ''}`}>
        {children}
      </div>
    </div>
  );
};

// Card loading placeholder
export const CardPlaceholder = ({ type = 'default' }) => {
  return (
    <div className={`card-placeholder glass-card ${type}`}>
      <div className="placeholder-shimmer"></div>
    </div>
  );
};

// Image loading placeholder
export const ImagePlaceholder = ({ aspectRatio = '1:1' }) => {
  return (
    <div className={`image-placeholder skeleton-pulse aspect-${aspectRatio.replace(':', '-')}`}>
      <div className="image-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor" opacity="0.3">
          <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
        </svg>
      </div>
    </div>
  );
};

export default {
  MessageSkeleton,
  ContactSkeleton,
  CategorySkeleton,
  MemorySkeleton,
  ProfileSkeleton,
  GlassSpinner,
  GlassProgress,
  WaveLoader,
  TypingIndicator,
  PageTransition,
  SkeletonContainer,
  CardPlaceholder,
  ImagePlaceholder
};