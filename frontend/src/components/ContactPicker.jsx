import React, { useState, useEffect } from 'react';
import { X, Search, User, Phone, Check, Loader, RefreshCw, WifiOff } from 'lucide-react';
import whatsappService from '../services/whatsappService';
import BottomSheet from './BottomSheet';
import './ContactPicker.css';

const ContactPicker = ({ isOpen, onClose, onSelectContact, excludedNumbers = [] }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedContact, setSelectedContact] = useState(null);
  const [allContacts, setAllContacts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [whatsappConnected, setWhatsappConnected] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  
  // Detect mobile viewport
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  // Fetch WhatsApp contacts when picker opens
  useEffect(() => {
    if (isOpen) {
      fetchWhatsAppContacts();
      checkWhatsAppStatus();
    }
  }, [isOpen]);
  
  // Check WhatsApp connection status
  const checkWhatsAppStatus = async () => {
    try {
      const status = await whatsappService.getStatus();
      setWhatsappConnected(status.isReady && status.isAuthenticated);
    } catch (error) {
      console.error('Error checking WhatsApp status:', error);
      setWhatsappConnected(false);
    }
  };
  
  // Fetch real WhatsApp contacts
  const fetchWhatsAppContacts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await whatsappService.fetchContacts();
      
      if (result.success) {
        setAllContacts(result.contacts);
        setWhatsappConnected(true);
      } else if (result.needsAuth) {
        setError('WhatsApp authentication required. Please connect your WhatsApp account.');
        setWhatsappConnected(false);
        // In a real implementation, you would show QR code here
      } else {
        setError(result.error || 'Failed to fetch contacts');
        setWhatsappConnected(false);
      }
    } catch (error) {
      console.error('Error fetching contacts:', error);
      setError('Failed to connect to WhatsApp service');
      setWhatsappConnected(false);
    } finally {
      setLoading(false);
    }
  };
  
  // Refresh contacts
  const handleRefresh = async () => {
    await fetchWhatsAppContacts();
  };
  
  // Filter out already selected contacts
  const availableContacts = allContacts.filter(
    contact => !excludedNumbers.includes(contact.phoneNumber)
  );
  
  // Filter contacts based on search
  const filteredContacts = availableContacts.filter(contact => {
    const query = searchQuery.toLowerCase();
    return (
      contact.name.toLowerCase().includes(query) ||
      contact.phoneNumber.includes(query) ||
      (contact.status && contact.status.toLowerCase().includes(query))
    );
  });
  
  const handleSelectContact = (contact) => {
    setSelectedContact(contact);
  };
  
  const handleConfirm = () => {
    if (selectedContact) {
      onSelectContact(selectedContact);
      setSelectedContact(null);
      setSearchQuery('');
      onClose();
    }
  };
  
  const handleClose = () => {
    setSelectedContact(null);
    setSearchQuery('');
    setError(null);
    onClose();
  };
  
  if (!isOpen) return null;
  
  // Mobile layout with BottomSheet
  if (isMobile) {
    return (
      <BottomSheet
        isOpen={isOpen}
        onClose={handleClose}
        title="Select Contact"
        height="75%"
        theme={document.documentElement.getAttribute('data-theme') || 'light'}
      >
        {/* Search Bar */}
        <div className="picker-search mobile">
          <div className="search-input-container">
            <Search className="search-icon" />
            <input
              type="text"
              placeholder="Search name or number..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
              autoFocus
              disabled={loading}
            />
            {!loading && (
              <button 
                className="refresh-btn" 
                onClick={handleRefresh}
                title="Refresh contacts"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        
        {/* Error Message */}
        {error && (
          <div className="error-message mobile">
            <p>{error}</p>
            <button onClick={handleRefresh} className="retry-btn">
              Try Again
            </button>
          </div>
        )}
        
        {/* Loading State */}
        {loading && (
          <div className="loading-container mobile">
            <Loader className="spinner" />
            <p>Fetching WhatsApp contacts...</p>
          </div>
        )}
        
        {/* Contacts List */}
        {!loading && !error && (
          <div className="contacts-list mobile">
            <div className="list-header">
              <span className="list-title">CONTACTS ON WHATSAPP</span>
              <span className="contact-count">{filteredContacts.length}</span>
            </div>
            
            {filteredContacts.length === 0 ? (
              <div className="no-contacts">
                <p>{searchQuery ? 'No contacts found' : 'No WhatsApp contacts'}</p>
              </div>
            ) : (
              filteredContacts.map(contact => (
                <div
                  key={contact.id}
                  className={`contact-item mobile ${selectedContact?.id === contact.id ? 'selected' : ''}`}
                  onClick={() => {
                    handleSelectContact(contact);
                    handleConfirm();
                  }}
                >
                  {contact.profilePicUrl ? (
                    <img 
                      src={contact.profilePicUrl} 
                      alt={contact.name}
                      className="contact-avatar-img"
                    />
                  ) : (
                    <div className="contact-avatar" style={{ background: contact.avatarColor }}>
                      <span className="avatar-text">{contact.initials}</span>
                    </div>
                  )}
                  <div className="contact-info">
                    <div className="contact-name">
                      {contact.name}
                    </div>
                    <div className="contact-status">
                      {contact.status || contact.phoneNumber}
                    </div>
                  </div>
                  {selectedContact?.id === contact.id && (
                    <div className="selected-indicator">
                      <Check className="w-5 h-5" />
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </BottomSheet>
    );
  }
  
  // Desktop layout (existing modal)
  return (
    <div className="contact-picker-overlay">
      <div className="contact-picker-modal">
        {/* Modal Header */}
        <div className="picker-header">
          <button className="close-btn" onClick={handleClose}>
            <X className="w-6 h-6" />
          </button>
          <div className="header-content">
            <h2 className="picker-title">Select contact</h2>
            {whatsappConnected && (
              <span className="connection-status connected">
                WhatsApp Connected
              </span>
            )}
            {!whatsappConnected && !loading && (
              <span className="connection-status disconnected">
                <WifiOff className="w-4 h-4" />
                WhatsApp Disconnected
              </span>
            )}
          </div>
          {selectedContact && (
            <button className="confirm-btn" onClick={handleConfirm}>
              <Check className="w-6 h-6" />
            </button>
          )}
        </div>
        
        {/* Search Bar */}
        <div className="picker-search">
          <div className="search-input-container">
            <Search className="search-icon" />
            <input
              type="text"
              placeholder="Search name or number..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
              autoFocus
              disabled={loading}
            />
            {!loading && (
              <button 
                className="refresh-btn" 
                onClick={handleRefresh}
                title="Refresh contacts"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        
        {/* New Contact Option */}
        <div className="new-contact-section">
          <div className="new-contact-item">
            <div className="new-contact-icon">
              <User className="w-5 h-5" />
            </div>
            <span className="new-contact-text">New contact</span>
          </div>
        </div>
        
        {/* Error Message */}
        {error && (
          <div className="error-message">
            <p>{error}</p>
            <button onClick={handleRefresh} className="retry-btn">
              Try Again
            </button>
          </div>
        )}
        
        {/* Loading State */}
        {loading && (
          <div className="loading-container">
            <Loader className="spinner" />
            <p>Fetching WhatsApp contacts...</p>
          </div>
        )}
        
        {/* Contacts List */}
        {!loading && !error && (
          <div className="contacts-list">
            <div className="list-header">
              <span className="list-title">CONTACTS ON WHATSAPP</span>
              <span className="contact-count">{filteredContacts.length}</span>
            </div>
            
            {filteredContacts.length === 0 ? (
              <div className="no-contacts">
                <p>{searchQuery ? 'No contacts found matching your search' : 'No WhatsApp contacts available'}</p>
              </div>
            ) : (
              filteredContacts.map(contact => (
                <div
                  key={contact.id}
                  className={`contact-item ${selectedContact?.id === contact.id ? 'selected' : ''}`}
                  onClick={() => handleSelectContact(contact)}
                >
                  {contact.profilePicUrl ? (
                    <img 
                      src={contact.profilePicUrl} 
                      alt={contact.name}
                      className="contact-avatar-img"
                    />
                  ) : (
                    <div className="contact-avatar" style={{ background: contact.avatarColor }}>
                      <span className="avatar-text">{contact.initials}</span>
                    </div>
                  )}
                  <div className="contact-info">
                    <div className="contact-name">
                      {contact.name}
                      {contact.isBusiness && (
                        <span className="business-badge">Business</span>
                      )}
                    </div>
                    <div className="contact-status">
                      {contact.status || contact.phoneNumber}
                    </div>
                  </div>
                  {selectedContact?.id === contact.id && (
                    <div className="selected-indicator">
                      <Check className="w-5 h-5" />
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
        
        {/* Quick Action Buttons */}
        {selectedContact && (
          <div className="picker-actions">
            <button className="action-button cancel" onClick={handleClose}>
              Cancel
            </button>
            <button className="action-button select" onClick={handleConfirm}>
              Add to Slot
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContactPicker;