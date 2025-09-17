const express = require('express');
const cors = require('cors');
const { getWhatsAppClient } = require('./whatsapp_client');
const QRCode = require('qrcode');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.WHATSAPP_API_PORT || 3001;

// Middleware
app.use(cors({
  origin: ['http://localhost:5000', 'http://localhost:5173', '*'],
  credentials: true
}));
app.use(express.json());

// Get WhatsApp client instance
const whatsappClient = getWhatsAppClient();

// Store WebSocket connections for real-time updates
const wsConnections = new Set();

// API Routes

// Get WhatsApp connection status
app.get('/api/whatsapp/status', (req, res) => {
  const status = whatsappClient.getStatus();
  res.json(status);
});

// Get QR code for authentication
app.get('/api/whatsapp/qr', async (req, res) => {
  try {
    const status = whatsappClient.getStatus();
    
    if (status.isAuthenticated) {
      return res.json({ 
        authenticated: true, 
        message: 'Already authenticated' 
      });
    }
    
    if (status.qrCode) {
      // Generate QR code as data URL
      const qrDataUrl = await QRCode.toDataURL(status.qrCode);
      return res.json({ 
        authenticated: false, 
        qrCode: qrDataUrl,
        qrString: status.qrCode 
      });
    }
    
    // Initialize client if not started
    if (!status.isReady && !status.hasQR) {
      await whatsappClient.initialize();
      return res.json({ 
        authenticated: false, 
        message: 'Initializing WhatsApp client, please wait...' 
      });
    }
    
    res.json({ 
      authenticated: false, 
      message: 'Waiting for QR code...' 
    });
  } catch (error) {
    console.error('Error getting QR code:', error);
    res.status(500).json({ error: error.message });
  }
});

// Initialize WhatsApp connection
app.post('/api/whatsapp/initialize', async (req, res) => {
  try {
    const result = await whatsappClient.initialize();
    res.json({ success: result });
  } catch (error) {
    console.error('Error initializing WhatsApp:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get WhatsApp contacts
app.get('/api/whatsapp/contacts', async (req, res) => {
  try {
    const status = whatsappClient.getStatus();
    
    if (!status.isReady) {
      return res.status(503).json({ 
        error: 'WhatsApp not connected',
        needsAuth: !status.isAuthenticated,
        status 
      });
    }
    
    // Get cached contacts or fetch new ones
    let contacts = whatsappClient.contacts;
    if (!contacts.length) {
      contacts = await whatsappClient.fetchContacts();
    }
    
    // Format contacts for frontend
    const formattedContacts = contacts.map(contact => ({
      id: contact.id,
      phoneNumber: contact.phoneNumber,
      name: contact.name,
      status: contact.status,
      profilePicUrl: contact.profilePicUrl,
      initials: getInitials(contact.name),
      avatarColor: getAvatarColor(contact.name),
      isMyContact: contact.isMyContact,
      isBusiness: contact.isBusiness,
      pushname: contact.pushname
    }));
    
    res.json({ 
      contacts: formattedContacts,
      total: formattedContacts.length,
      status: 'connected'
    });
  } catch (error) {
    console.error('Error fetching contacts:', error);
    res.status(500).json({ error: error.message });
  }
});

// Refresh contacts
app.post('/api/whatsapp/contacts/refresh', async (req, res) => {
  try {
    const contacts = await whatsappClient.fetchContacts();
    res.json({ 
      contacts,
      total: contacts.length,
      message: 'Contacts refreshed successfully'
    });
  } catch (error) {
    console.error('Error refreshing contacts:', error);
    res.status(500).json({ error: error.message });
  }
});

// Send message (for future use)
app.post('/api/whatsapp/send', async (req, res) => {
  try {
    const { phoneNumber, message } = req.body;
    
    if (!phoneNumber || !message) {
      return res.status(400).json({ error: 'Phone number and message required' });
    }
    
    const result = await whatsappClient.sendMessage(phoneNumber, message);
    res.json({ success: true, result });
  } catch (error) {
    console.error('Error sending message:', error);
    res.status(500).json({ error: error.message });
  }
});

// Logout WhatsApp
app.post('/api/whatsapp/logout', async (req, res) => {
  try {
    await whatsappClient.logout();
    res.json({ success: true, message: 'Logged out successfully' });
  } catch (error) {
    console.error('Error logging out:', error);
    res.status(500).json({ error: error.message });
  }
});

// Helper functions
function getInitials(name) {
  if (!name) return '?';
  const parts = name.split(' ').filter(p => p.length > 0);
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }
  return parts.slice(0, 2).map(p => p[0]).join('').toUpperCase();
}

function getAvatarColor(name) {
  const colors = [
    '#25D366', '#075E54', '#128C7E', '#34B7F1', 
    '#9ACB3C', '#00BFA5', '#FFC107', '#E91E63',
    '#9C27B0', '#3F51B5', '#009688', '#FF5722',
    '#795548', '#607D8B', '#4CAF50'
  ];
  
  if (!name) return colors[0];
  
  // Generate consistent color based on name
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  return colors[Math.abs(hash) % colors.length];
}

// WhatsApp client event handlers
whatsappClient.on('qr', (qr) => {
  console.log('📱 New QR code generated');
  // Broadcast to all connected clients
  broadcastStatus();
});

whatsappClient.on('authenticated', () => {
  console.log('✅ WhatsApp authenticated');
  broadcastStatus();
});

whatsappClient.on('ready', () => {
  console.log('✅ WhatsApp ready');
  broadcastStatus();
});

whatsappClient.on('disconnected', () => {
  console.log('❌ WhatsApp disconnected');
  broadcastStatus();
});

function broadcastStatus() {
  const status = whatsappClient.getStatus();
  // This would broadcast to WebSocket connections if implemented
  console.log('Broadcasting status:', status);
}

// Start server
app.listen(PORT, () => {
  console.log(`🚀 WhatsApp API server running on port ${PORT}`);
  console.log(`📱 Initializing WhatsApp client...`);
  
  // Auto-initialize WhatsApp client on server start
  whatsappClient.initialize().then(() => {
    console.log('✅ WhatsApp client initialization started');
  }).catch(error => {
    console.error('❌ Failed to start WhatsApp client:', error);
  });
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down WhatsApp server...');
  await whatsappClient.destroy();
  process.exit(0);
});

module.exports = app;