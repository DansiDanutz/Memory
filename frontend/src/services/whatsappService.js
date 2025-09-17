// WhatsApp Service for frontend integration
const WHATSAPP_API_URL = 'http://localhost:3001/api/whatsapp';

class WhatsAppService {
  constructor() {
    this.isConnected = false;
    this.contacts = [];
    this.status = null;
  }

  // Get WhatsApp connection status
  async getStatus() {
    try {
      const response = await fetch(`${WHATSAPP_API_URL}/status`);
      const data = await response.json();
      this.status = data;
      this.isConnected = data.isReady && data.isAuthenticated;
      return data;
    } catch (error) {
      console.error('Error getting WhatsApp status:', error);
      return {
        isReady: false,
        isAuthenticated: false,
        hasQR: false,
        error: error.message
      };
    }
  }

  // Get QR code for authentication
  async getQRCode() {
    try {
      const response = await fetch(`${WHATSAPP_API_URL}/qr`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error getting QR code:', error);
      return { error: error.message };
    }
  }

  // Initialize WhatsApp connection
  async initialize() {
    try {
      const response = await fetch(`${WHATSAPP_API_URL}/initialize`, {
        method: 'POST'
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error initializing WhatsApp:', error);
      return { success: false, error: error.message };
    }
  }

  // Fetch WhatsApp contacts
  async fetchContacts() {
    try {
      const response = await fetch(`${WHATSAPP_API_URL}/contacts`);
      
      if (!response.ok) {
        const errorData = await response.json();
        
        // Check if authentication is needed
        if (errorData.needsAuth) {
          return {
            success: false,
            needsAuth: true,
            message: 'WhatsApp authentication required',
            contacts: []
          };
        }
        
        throw new Error(errorData.error || 'Failed to fetch contacts');
      }
      
      const data = await response.json();
      this.contacts = data.contacts || [];
      
      return {
        success: true,
        contacts: this.contacts,
        total: data.total || 0
      };
    } catch (error) {
      console.error('Error fetching WhatsApp contacts:', error);
      return {
        success: false,
        error: error.message,
        contacts: []
      };
    }
  }

  // Refresh contacts
  async refreshContacts() {
    try {
      const response = await fetch(`${WHATSAPP_API_URL}/contacts/refresh`, {
        method: 'POST'
      });
      const data = await response.json();
      this.contacts = data.contacts || [];
      return data;
    } catch (error) {
      console.error('Error refreshing contacts:', error);
      return { error: error.message };
    }
  }

  // Send message (for future use)
  async sendMessage(phoneNumber, message) {
    try {
      const response = await fetch(`${WHATSAPP_API_URL}/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phoneNumber, message })
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error sending message:', error);
      return { success: false, error: error.message };
    }
  }

  // Logout WhatsApp
  async logout() {
    try {
      const response = await fetch(`${WHATSAPP_API_URL}/logout`, {
        method: 'POST'
      });
      const data = await response.json();
      this.isConnected = false;
      this.contacts = [];
      return data;
    } catch (error) {
      console.error('Error logging out:', error);
      return { success: false, error: error.message };
    }
  }

  // Check connection periodically
  async startStatusPolling(callback, interval = 5000) {
    // Initial check
    const status = await this.getStatus();
    if (callback) callback(status);
    
    // Set up polling
    return setInterval(async () => {
      const status = await this.getStatus();
      if (callback) callback(status);
    }, interval);
  }

  // Stop polling
  stopStatusPolling(intervalId) {
    if (intervalId) {
      clearInterval(intervalId);
    }
  }
}

// Export singleton instance
const whatsappService = new WhatsAppService();
export default whatsappService;