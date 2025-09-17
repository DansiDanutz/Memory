import React, { useState, useEffect, useRef } from 'react';
import { Clock, AlertTriangle, Flame } from 'lucide-react';
import './CountdownTimer.css';

const CountdownTimer = ({ 
  endTime, 
  onExpire, 
  format = 'short', 
  urgent = false, 
  compact = false,
  showIcon = true,
  pulseOnUrgent = true,
  colorTransition = true
}) => {
  const [timeLeft, setTimeLeft] = useState(null);
  const [urgencyLevel, setUrgencyLevel] = useState('normal');
  const intervalRef = useRef(null);

  useEffect(() => {
    calculateTimeLeft();
    intervalRef.current = setInterval(calculateTimeLeft, 1000);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [endTime]);

  const calculateTimeLeft = () => {
    const now = new Date().getTime();
    const end = new Date(endTime).getTime();
    const difference = end - now;

    if (difference <= 0) {
      setTimeLeft(null);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (onExpire) {
        onExpire();
      }
      return;
    }

    const days = Math.floor(difference / (1000 * 60 * 60 * 24));
    const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((difference % (1000 * 60)) / 1000);

    setTimeLeft({ days, hours, minutes, seconds, totalSeconds: difference / 1000 });
    
    // Determine urgency level
    if (difference < 60000) { // Less than 1 minute
      setUrgencyLevel('critical');
    } else if (difference < 300000) { // Less than 5 minutes
      setUrgencyLevel('high');
    } else if (difference < 3600000) { // Less than 1 hour
      setUrgencyLevel('medium');
    } else {
      setUrgencyLevel('normal');
    }
  };

  const formatTime = () => {
    if (!timeLeft) return 'Expired';

    const { days, hours, minutes, seconds } = timeLeft;

    switch (format) {
      case 'full':
        const parts = [];
        if (days > 0) parts.push(`${days}d`);
        if (hours > 0) parts.push(`${hours}h`);
        if (minutes > 0) parts.push(`${minutes}m`);
        if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`);
        return parts.join(' ');

      case 'short':
        if (days > 0) return `${days}d ${hours}h`;
        if (hours > 0) return `${hours}h ${minutes}m`;
        if (minutes > 0) return `${minutes}m ${seconds}s`;
        return `${seconds}s`;

      case 'minimal':
        if (days > 0) return `${days}d`;
        if (hours > 0) return `${hours}h`;
        if (minutes > 0) return `${minutes}m`;
        return `${seconds}s`;

      case 'clock':
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

      default:
        return `${hours}h ${minutes}m ${seconds}s`;
    }
  };

  const getIcon = () => {
    if (urgencyLevel === 'critical') return <Flame className="timer-icon flame" />;
    if (urgencyLevel === 'high') return <AlertTriangle className="timer-icon alert" />;
    return <Clock className="timer-icon" />;
  };

  const getUrgencyClass = () => {
    let classes = ['countdown-timer'];
    
    if (compact) classes.push('compact');
    if (urgencyLevel !== 'normal') classes.push(urgencyLevel);
    if (urgent || urgencyLevel === 'high' || urgencyLevel === 'critical') {
      classes.push('urgent');
      if (pulseOnUrgent) classes.push('pulse');
    }
    if (colorTransition) classes.push('color-transition');
    
    return classes.join(' ');
  };

  const getProgressPercentage = () => {
    if (!timeLeft) return 0;
    
    // Calculate based on last 24 hours for visual progress
    const maxTime = 24 * 60 * 60; // 24 hours in seconds
    const remaining = timeLeft.totalSeconds;
    
    if (remaining > maxTime) return 100;
    return (remaining / maxTime) * 100;
  };

  if (!timeLeft) {
    return (
      <div className="countdown-timer expired">
        <span className="expired-text">Expired</span>
      </div>
    );
  }

  return (
    <div className={getUrgencyClass()}>
      {showIcon && getIcon()}
      <span className="time-display">{formatTime()}</span>
      
      {!compact && colorTransition && (
        <div className="progress-ring">
          <svg width="40" height="40">
            <circle
              className="progress-ring-bg"
              cx="20"
              cy="20"
              r="18"
              strokeWidth="2"
            />
            <circle
              className="progress-ring-fill"
              cx="20"
              cy="20"
              r="18"
              strokeWidth="2"
              strokeDasharray={`${2 * Math.PI * 18}`}
              strokeDashoffset={`${2 * Math.PI * 18 * (1 - getProgressPercentage() / 100)}`}
            />
          </svg>
        </div>
      )}
    </div>
  );
};

export default CountdownTimer;