import axios from 'axios';
import { API_CONFIG, API_ENDPOINTS, ERROR_MESSAGES } from '../utils/constants';

// Create axios instance with default configuration
const api = axios.create({
  baseURL: API_CONFIG.baseUrl,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication and logging
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Log requests in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
    }
    
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and logging
api.interceptors.response.use(
  (response) => {
    // Log responses in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    }
    
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    
    // Handle common error scenarios
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('auth_token');
      window.location.href = '/welcome';
    } else if (error.response?.status === 403) {
      // Forbidden
      throw new Error('Access denied. Please check your permissions.');
    } else if (error.response?.status >= 500) {
      // Server error
      throw new Error('Server error. Please try again later.');
    } else if (error.code === 'NETWORK_ERROR') {
      // Network error
      throw new Error(ERROR_MESSAGES.NETWORK_ERROR);
    }
    
    return Promise.reject(error);
  }
);

// Retry mechanism for failed requests
const retryRequest = async (fn, retries = API_CONFIG.retryAttempts) => {
  try {
    return await fn();
  } catch (error) {
    if (retries > 0 && error.response?.status >= 500) {
      await new Promise(resolve => setTimeout(resolve, API_CONFIG.retryDelay));
      return retryRequest(fn, retries - 1);
    }
    throw error;
  }
};

// Authentication API
export const authAPI = {
  login: (credentials) => retryRequest(() => api.post(`${API_ENDPOINTS.AUTH}/login`, credentials)),
  register: (userData) => retryRequest(() => api.post(`${API_ENDPOINTS.AUTH}/register`, userData)),
  logout: () => retryRequest(() => api.post(`${API_ENDPOINTS.AUTH}/logout`)),
  refreshToken: () => retryRequest(() => api.post(`${API_ENDPOINTS.AUTH}/refresh`)),
  verifyToken: () => retryRequest(() => api.get(`${API_ENDPOINTS.AUTH}/verify`)),
  resetPassword: (email) => retryRequest(() => api.post(`${API_ENDPOINTS.AUTH}/reset-password`, { email })),
  changePassword: (passwords) => retryRequest(() => api.post(`${API_ENDPOINTS.AUTH}/change-password`, passwords)),
};

// Memory Management API
export const memoryAPI = {
  // Get all memories
  getMemories: (params = {}) => retryRequest(() => api.get(API_ENDPOINTS.MEMORIES, { params })),
  
  // Get memory by ID
  getMemory: (id) => retryRequest(() => api.get(`${API_ENDPOINTS.MEMORIES}/${id}`)),
  
  // Create new memory
  createMemory: (memoryData) => retryRequest(() => api.post(API_ENDPOINTS.MEMORIES, memoryData)),
  
  // Update memory
  updateMemory: (id, memoryData) => retryRequest(() => api.put(`${API_ENDPOINTS.MEMORIES}/${id}`, memoryData)),
  
  // Delete memory
  deleteMemory: (id) => retryRequest(() => api.delete(`${API_ENDPOINTS.MEMORIES}/${id}`)),
  
  // Get memories by category
  getMemoriesByCategory: (categoryId, params = {}) => 
    retryRequest(() => api.get(`${API_ENDPOINTS.MEMORIES}/category/${categoryId}`, { params })),
  
  // Search memories
  searchMemories: (query, filters = {}) => 
    retryRequest(() => api.get(`${API_ENDPOINTS.MEMORIES}/search`, { params: { q: query, ...filters } })),
  
  // Get memory statistics
  getMemoryStats: () => retryRequest(() => api.get(`${API_ENDPOINTS.MEMORIES}/stats`)),
  
  // Export memories
  exportMemories: (format = 'json', filters = {}) => 
    retryRequest(() => api.get(`${API_ENDPOINTS.MEMORIES}/export`, { params: { format, ...filters } })),
  
  // Import memories
  importMemories: (data) => retryRequest(() => api.post(`${API_ENDPOINTS.MEMORIES}/import`, data)),
};

// Message API
export const messageAPI = {
  // Get messages for a memory/category
  getMessages: (memoryId, params = {}) => 
    retryRequest(() => api.get(`${API_ENDPOINTS.MESSAGES}/${memoryId}`, { params })),
  
  // Send message
  sendMessage: (memoryId, messageData) => 
    retryRequest(() => api.post(`${API_ENDPOINTS.MESSAGES}/${memoryId}`, messageData)),
  
  // Update message
  updateMessage: (messageId, messageData) => 
    retryRequest(() => api.put(`${API_ENDPOINTS.MESSAGES}/message/${messageId}`, messageData)),
  
  // Delete message
  deleteMessage: (messageId) => 
    retryRequest(() => api.delete(`${API_ENDPOINTS.MESSAGES}/message/${messageId}`)),
  
  // Mark messages as read
  markAsRead: (memoryId, messageIds) => 
    retryRequest(() => api.post(`${API_ENDPOINTS.MESSAGES}/${memoryId}/read`, { messageIds })),
  
  // Get message history
  getMessageHistory: (params = {}) => 
    retryRequest(() => api.get(`${API_ENDPOINTS.MESSAGES}/history`, { params })),
};

// Synchronization API
export const syncAPI = {
  // Get sync status
  getSyncStatus: () => retryRequest(() => api.get(`${API_ENDPOINTS.SYNC}/status`)),
  
  // Start sync
  startSync: () => retryRequest(() => api.post(`${API_ENDPOINTS.SYNC}/start`)),
  
  // Stop sync
  stopSync: () => retryRequest(() => api.post(`${API_ENDPOINTS.SYNC}/stop`)),
  
  // Get sync settings
  getSyncSettings: () => retryRequest(() => api.get(`${API_ENDPOINTS.SYNC}/settings`)),
  
  // Update sync settings
  updateSyncSettings: (settings) => retryRequest(() => api.put(`${API_ENDPOINTS.SYNC}/settings`, settings)),
  
  // Get sync history
  getSyncHistory: (params = {}) => retryRequest(() => api.get(`${API_ENDPOINTS.SYNC}/history`, { params })),
  
  // Force sync
  forceSync: () => retryRequest(() => api.post(`${API_ENDPOINTS.SYNC}/force`)),
  
  // WhatsApp specific sync
  syncWhatsApp: () => retryRequest(() => api.post(`${API_ENDPOINTS.SYNC}/whatsapp`)),
  
  // Get WhatsApp connection status
  getWhatsAppStatus: () => retryRequest(() => api.get(`${API_ENDPOINTS.SYNC}/whatsapp/status`)),
  
  // Connect to WhatsApp
  connectWhatsApp: (credentials) => retryRequest(() => api.post(`${API_ENDPOINTS.SYNC}/whatsapp/connect`, credentials)),
  
  // Disconnect from WhatsApp
  disconnectWhatsApp: () => retryRequest(() => api.post(`${API_ENDPOINTS.SYNC}/whatsapp/disconnect`)),
};

// Voice API
export const voiceAPI = {
  // Upload voice recording
  uploadVoice: (audioBlob, metadata = {}) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('metadata', JSON.stringify(metadata));
    
    return retryRequest(() => api.post(`${API_ENDPOINTS.VOICE}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }));
  },
  
  // Transcribe audio
  transcribeAudio: (audioId) => retryRequest(() => api.post(`${API_ENDPOINTS.VOICE}/transcribe`, { audioId })),
  
  // Get transcription
  getTranscription: (transcriptionId) => retryRequest(() => api.get(`${API_ENDPOINTS.VOICE}/transcription/${transcriptionId}`)),
  
  // Text to speech
  textToSpeech: (text, options = {}) => 
    retryRequest(() => api.post(`${API_ENDPOINTS.VOICE}/tts`, { text, ...options })),
  
  // Get voice settings
  getVoiceSettings: () => retryRequest(() => api.get(`${API_ENDPOINTS.VOICE}/settings`)),
  
  // Update voice settings
  updateVoiceSettings: (settings) => retryRequest(() => api.put(`${API_ENDPOINTS.VOICE}/settings`, settings)),
  
  // Get supported languages
  getSupportedLanguages: () => retryRequest(() => api.get(`${API_ENDPOINTS.VOICE}/languages`)),
  
  // Get voice recordings
  getVoiceRecordings: (params = {}) => retryRequest(() => api.get(`${API_ENDPOINTS.VOICE}/recordings`, { params })),
};

// File Management API
export const fileAPI = {
  // Upload file
  uploadFile: (file, metadata = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('metadata', JSON.stringify(metadata));
    
    return retryRequest(() => api.post(`${API_ENDPOINTS.FILES}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        // Emit progress event
        window.dispatchEvent(new CustomEvent('fileUploadProgress', { detail: { progress, file } }));
      },
    }));
  },
  
  // Get file
  getFile: (fileId) => retryRequest(() => api.get(`${API_ENDPOINTS.FILES}/${fileId}`)),
  
  // Delete file
  deleteFile: (fileId) => retryRequest(() => api.delete(`${API_ENDPOINTS.FILES}/${fileId}`)),
  
  // Get file metadata
  getFileMetadata: (fileId) => retryRequest(() => api.get(`${API_ENDPOINTS.FILES}/${fileId}/metadata`)),
  
  // Update file metadata
  updateFileMetadata: (fileId, metadata) => 
    retryRequest(() => api.put(`${API_ENDPOINTS.FILES}/${fileId}/metadata`, metadata)),
  
  // Get user files
  getUserFiles: (params = {}) => retryRequest(() => api.get(`${API_ENDPOINTS.FILES}/user`, { params })),
  
  // Generate file thumbnail
  generateThumbnail: (fileId, options = {}) => 
    retryRequest(() => api.post(`${API_ENDPOINTS.FILES}/${fileId}/thumbnail`, options)),
  
  // Get file download URL
  getDownloadUrl: (fileId) => retryRequest(() => api.get(`${API_ENDPOINTS.FILES}/${fileId}/download-url`)),
};

// Search API
export const searchAPI = {
  // Global search
  search: (query, filters = {}) => 
    retryRequest(() => api.get(API_ENDPOINTS.SEARCH, { params: { q: query, ...filters } })),
  
  // Search suggestions
  getSuggestions: (query) => 
    retryRequest(() => api.get(`${API_ENDPOINTS.SEARCH}/suggestions`, { params: { q: query } })),
  
  // Search history
  getSearchHistory: () => retryRequest(() => api.get(`${API_ENDPOINTS.SEARCH}/history`)),
  
  // Clear search history
  clearSearchHistory: () => retryRequest(() => api.delete(`${API_ENDPOINTS.SEARCH}/history`)),
  
  // Advanced search
  advancedSearch: (criteria) => retryRequest(() => api.post(`${API_ENDPOINTS.SEARCH}/advanced`, criteria)),
  
  // Search analytics
  getSearchAnalytics: () => retryRequest(() => api.get(`${API_ENDPOINTS.SEARCH}/analytics`)),
};

// Settings API
export const settingsAPI = {
  // Get user settings
  getSettings: () => retryRequest(() => api.get(API_ENDPOINTS.SETTINGS)),
  
  // Update settings
  updateSettings: (settings) => retryRequest(() => api.put(API_ENDPOINTS.SETTINGS, settings)),
  
  // Reset settings to default
  resetSettings: () => retryRequest(() => api.post(`${API_ENDPOINTS.SETTINGS}/reset`)),
  
  // Get setting by key
  getSetting: (key) => retryRequest(() => api.get(`${API_ENDPOINTS.SETTINGS}/${key}`)),
  
  // Update setting by key
  updateSetting: (key, value) => retryRequest(() => api.put(`${API_ENDPOINTS.SETTINGS}/${key}`, { value })),
  
  // Export settings
  exportSettings: () => retryRequest(() => api.get(`${API_ENDPOINTS.SETTINGS}/export`)),
  
  // Import settings
  importSettings: (settings) => retryRequest(() => api.post(`${API_ENDPOINTS.SETTINGS}/import`, settings)),
};

// Analytics API
export const analyticsAPI = {
  // Track event
  trackEvent: (event, properties = {}) => 
    retryRequest(() => api.post(`${API_ENDPOINTS.ANALYTICS}/event`, { event, properties })),
  
  // Get user analytics
  getUserAnalytics: (params = {}) => 
    retryRequest(() => api.get(`${API_ENDPOINTS.ANALYTICS}/user`, { params })),
  
  // Get usage statistics
  getUsageStats: (period = '30d') => 
    retryRequest(() => api.get(`${API_ENDPOINTS.ANALYTICS}/usage`, { params: { period } })),
  
  // Get memory insights
  getMemoryInsights: () => retryRequest(() => api.get(`${API_ENDPOINTS.ANALYTICS}/insights`)),
  
  // Get performance metrics
  getPerformanceMetrics: () => retryRequest(() => api.get(`${API_ENDPOINTS.ANALYTICS}/performance`)),
};

// Health Check API
export const healthAPI = {
  // Check API health
  checkHealth: () => retryRequest(() => api.get(API_ENDPOINTS.HEALTH)),
  
  // Get system status
  getSystemStatus: () => retryRequest(() => api.get(`${API_ENDPOINTS.HEALTH}/status`)),
  
  // Get version info
  getVersionInfo: () => retryRequest(() => api.get(`${API_ENDPOINTS.HEALTH}/version`)),
};

// OpenAI Integration API
export const openaiAPI = {
  // Chat completion
  chatCompletion: (messages, options = {}) => {
    return retryRequest(() => api.post('/openai/chat', {
      messages,
      model: options.model || 'gpt-4',
      max_tokens: options.maxTokens || 2000,
      temperature: options.temperature || 0.7,
      ...options,
    }));
  },
  
  // Generate embeddings
  generateEmbeddings: (text) => {
    return retryRequest(() => api.post('/openai/embeddings', { text }));
  },
  
  // Analyze sentiment
  analyzeSentiment: (text) => {
    return retryRequest(() => api.post('/openai/sentiment', { text }));
  },
  
  // Summarize text
  summarizeText: (text, maxLength = 100) => {
    return retryRequest(() => api.post('/openai/summarize', { text, maxLength }));
  },
  
  // Extract keywords
  extractKeywords: (text) => {
    return retryRequest(() => api.post('/openai/keywords', { text }));
  },
  
  // Categorize content
  categorizeContent: (text) => {
    return retryRequest(() => api.post('/openai/categorize', { text }));
  },
};

// Media Generation API
export const mediaAPI = {
  // Generate image
  generateImage: (prompt, options = {}) => {
    return retryRequest(() => api.post('/media/generate-image', {
      prompt,
      size: options.size || '1024x1024',
      quality: options.quality || 'standard',
      style: options.style || 'natural',
      ...options,
    }));
  },
  
  // Refine image
  refineImage: (imageUrl, prompt, options = {}) => {
    return retryRequest(() => api.post('/media/refine-image', {
      imageUrl,
      prompt,
      ...options,
    }));
  },
  
  // Generate video
  generateVideo: (prompt, options = {}) => {
    return retryRequest(() => api.post('/media/generate-video', {
      prompt,
      duration: options.duration || 5,
      quality: options.quality || 'standard',
      ...options,
    }));
  },
  
  // Generate speech
  generateSpeech: (text, options = {}) => {
    return retryRequest(() => api.post('/media/generate-speech', {
      text,
      voice: options.voice || 'alloy',
      speed: options.speed || 1.0,
      ...options,
    }));
  },
  
  // Transcribe audio
  transcribeAudio: (audioUrl, options = {}) => {
    return retryRequest(() => api.post('/media/transcribe-audio', {
      audioUrl,
      language: options.language || 'en',
      ...options,
    }));
  },
};

// Export all APIs
export default {
  authAPI,
  memoryAPI,
  messageAPI,
  syncAPI,
  voiceAPI,
  fileAPI,
  searchAPI,
  settingsAPI,
  analyticsAPI,
  healthAPI,
  openaiAPI,
  mediaAPI,
};

// Export the axios instance for custom requests
export { api };

