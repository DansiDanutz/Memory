import React from 'react';
import { User, Plus, UserPlus, CheckCircle2, Lock } from 'lucide-react';

const ContactCard = ({ slot, onSelect, className = '' }) => {
  const handleClick = () => {
    if (slot.isPremium) {
      // Premium slot - do nothing for now
      return;
    } else if (slot.isEmpty) {
      onSelect();
    } else {
      // Open chat with selected contact
      console.log('Opening chat with:', slot.contact?.name);
    }
  };

  // Determine card state class
  const stateClass = slot.isPremium ? 'locked' : (slot.isEmpty ? 'empty' : '');
  
  return (
    <div 
      className={`wa-chat-item wa-contact-card ${stateClass} ${className}`}
      onClick={handleClick}
      data-empty={slot.isEmpty}
      role="button"
      tabIndex={0}
      aria-label={
        slot.isPremium
          ? 'Premium slot (locked)'
          : slot.isEmpty 
            ? 'Empty contact slot - click to add contact'
            : `Contact: ${slot.contact?.name}`
      }
    >
      {/* WhatsApp Chat Item Layout - Avatar + Content + Meta */}
      <div className="wa-chat-avatar">
        {slot.isPremium ? (
          <div className="wa-avatar locked-premium">
            <Lock size={20} className="wa-crown-icon" />
          </div>
        ) : slot.isEmpty ? (
          <div className="wa-avatar empty-slot">
            <Plus size={22} className="wa-plus-icon" />
          </div>
        ) : (
          <div className="wa-avatar contact-filled">
            {slot.contact?.avatar ? (
              <img src={slot.contact.avatar} alt={slot.contact.name} className="wa-avatar-img" />
            ) : (
              <>
                <User size={18} className="wa-user-icon" />
                {slot.contact?.initials && (
                  <span className="wa-avatar-text">
                    {slot.contact.initials}
                  </span>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Chat Item Content - Matches WhatsApp layout exactly */}
      <div className="wa-chat-content">
        <div className="wa-chat-header">
          <h3 className="wa-chat-name">
            {slot.isPremium
              ? 'Premium Slot'
              : slot.isEmpty 
                ? 'Add Contact' 
                : slot.contact?.name || 'WhatsApp Contact'
            }
          </h3>
          <span className="wa-chat-time">
            {slot.isPremium
              ? 'Locked'
              : slot.isEmpty 
                ? 'Empty'
                : slot.contact?.lastMessageTime || 'now'
            }
          </span>
        </div>
        
        <div className="wa-chat-preview">
          <p className="wa-last-message">
            {slot.isPremium ? (
              <>
                <Lock size={14} className="wa-inline-icon premium" />
                <span>Upgrade to unlock this slot</span>
              </>
            ) : slot.isEmpty ? (
              <>
                <Plus size={14} className="wa-inline-icon" />
                <span>Tap to select WhatsApp contact & import chats</span>
              </>
            ) : (
              <>
                {slot.contact?.lastMessage ? (
                  <>
                    <CheckCircle2 size={14} className="wa-inline-icon wa-delivered" />
                    <span>{slot.contact.lastMessage}</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={14} className="wa-inline-icon" />
                    <span>{slot.contact.memories?.length || 0} memories imported</span>
                  </>
                )}
              </>
            )}
          </p>
          
          {/* Unread badge for empty slots only */}
          {slot.isEmpty && !slot.isPremium && (
            <div className="wa-unread-badge">
              +
            </div>
          )}
        </div>
      </div>

      {/* Selection indicator - WhatsApp green pill */}
      {slot.isSelected && (
        <div className="wa-selection-indicator"></div>
      )}
    </div>
  );
};

export default ContactCard;