import React from 'react';
import ContactCard from './ContactCard';

const ContactCardsGrid = ({ slots, onSlotSelect, className = '' }) => {
  const filledSlots = slots.filter(slot => !slot.isEmpty).length;
  const emptySlots = slots.filter(slot => slot.isEmpty && !slot.isPremium);
  const hasEmptySlots = emptySlots.length > 0;
  
  const handleAddContact = () => {
    if (hasEmptySlots) {
      // Trigger the first empty slot
      onSlotSelect(emptySlots[0]);
    }
  };

  // DEFINITIVE FIX: Ensure only ONE premium slot and deduplicate filled slots
  const premiumSlot = slots.find(s => s.isPremium);
  const filledById = new Map(slots.filter(s => !s.isEmpty && !s.isPremium).map(s => [s.id, s]));
  const slotsToShow = [premiumSlot, ...filledById.values()].filter(Boolean);

  return (
    <div className={`wa-contacts-grid ${className}`}>
      <div className="wa-contacts-header">
        <div>
          <h2 className="wa-section-title">
            Your Memory Contacts
            <span className="wa-contact-counter">{filledSlots}/6</span>
          </h2>
          <p className="wa-section-subtitle">
            Import WhatsApp chat history to create AI-powered memories
          </p>
        </div>
        {hasEmptySlots && (
          <button className="wa-smart-add-btn" onClick={handleAddContact}>
            <span className="wa-add-icon">+</span>
            Add Contact
          </button>
        )}
      </div>
      
      <div className="wa-cards-container">
        {slotsToShow.map((slot) => (
          <ContactCard
            key={slot.id}
            slot={slot}
            onSelect={() => onSlotSelect(slot)}
          />
        ))}
      </div>
      
      {/* Floating Action Button - Alternative approach */}
      {hasEmptySlots && (
        <button className="wa-add-contact-fab" onClick={handleAddContact} title="Add Contact">
          +
        </button>
      )}
      
      <div className="wa-contacts-footer">
        <div className="wa-footer-info">
          <span className="wa-slot-count">
            {slots.filter(slot => !slot.isEmpty && !slot.isPremium).length}/6 slots filled
          </span>
        </div>
      </div>
    </div>
  );
};

export default ContactCardsGrid;