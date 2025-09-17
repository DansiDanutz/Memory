/**
 * WebSocket Service
 * Handles real-time connections and updates
 */
class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.listeners = new Map();
    this.userId = null;
    this.isConnected = false;
  }

  /**
   * Connect to WebSocket server
   */
  connect(userId, onConnect = null, onDisconnect = null) {
    this.userId = userId;
    
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    // Create WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/connect?user_id=${userId}`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      // Connection opened
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // Send initial authentication
        this.send('auth', { userId });
        
        if (onConnect) onConnect();
        this.emit('connected', { userId });
      };
      
      // Message received
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          
          // Handle different message types
          this.handleMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      // Connection closed
      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnected = false;
        
        if (onDisconnect) onDisconnect();
        this.emit('disconnected', { code: event.code, reason: event.reason });
        
        // Attempt reconnection
        this.reconnect();
      };
      
      // Error occurred
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', error);
      };
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.reconnect();
    }
  }

  /**
   * Handle incoming messages
   */
  handleMessage(data) {
    const { type, payload } = data;
    
    switch (type) {
      case 'memory_created':
        this.emit('memory_created', payload);
        break;
        
      case 'memory_updated':
        this.emit('memory_updated', payload);
        break;
        
      case 'memory_deleted':
        this.emit('memory_deleted', payload);
        break;
        
      case 'sync_status':
        this.emit('sync_status', payload);
        break;
        
      case 'whatsapp_message':
        this.emit('whatsapp_message', payload);
        break;
        
      case 'notification':
        this.emit('notification', payload);
        break;
        
      case 'pong':
        // Heartbeat response
        break;
        
      default:
        console.log('Unknown message type:', type);
        this.emit(type, payload);
    }
  }

  /**
   * Send message through WebSocket
   */
  send(type, payload) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ type, payload, timestamp: new Date().toISOString() });
      this.ws.send(message);
      return true;
    } else {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }
  }

  /**
   * Reconnect to WebSocket server
   */
  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('max_reconnect_failed');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      if (this.userId) {
        this.connect(this.userId);
      }
    }, delay);
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }

  /**
   * Add event listener
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  /**
   * Remove event listener
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  /**
   * Emit event to listeners
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket listener for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Send heartbeat
   */
  startHeartbeat() {
    setInterval(() => {
      if (this.isConnected) {
        this.send('ping', {});
      }
    }, 30000); // Every 30 seconds
  }

  /**
   * Check connection status
   */
  isConnectedStatus() {
    return this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// Create singleton instance
const wsService = new WebSocketService();

export default wsService;