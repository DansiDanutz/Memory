// App Configuration Constants
export const APP_CONFIG = {
  name: 'Memo - Personal AI Brain',
  version: '1.0.0',
  description: 'AI-powered memory management with WhatsApp-like interface',
  author: 'Manus AI',
  supportEmail: 'support@memo-ai.com',
  websiteUrl: 'https://memo-ai.com',
  privacyUrl: 'https://memo-ai.com/privacy',
  termsUrl: 'https://memo-ai.com/terms',
};

// API Configuration
export const API_CONFIG = {
  baseUrl: process.env.REACT_APP_API_URL || 'http://localhost:3001/api',
  socketUrl: process.env.REACT_APP_SOCKET_URL || 'http://localhost:3001',
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000,
};

// OpenAI Configuration
export const OPENAI_CONFIG = {
  apiKey: process.env.REACT_APP_OPENAI_API_KEY,
  model: 'gpt-4',
  maxTokens: 2000,
  temperature: 0.7,
  presencePenalty: 0.1,
  frequencyPenalty: 0.1,
};

// WhatsApp Integration Configuration
export const WHATSAPP_CONFIG = {
  apiKey: process.env.REACT_APP_WHATSAPP_API_KEY,
  webhookUrl: process.env.REACT_APP_WHATSAPP_WEBHOOK_URL,
  phoneNumberId: process.env.REACT_APP_WHATSAPP_PHONE_NUMBER_ID,
  businessAccountId: process.env.REACT_APP_WHATSAPP_BUSINESS_ACCOUNT_ID,
};

// Memory Categories
export const MEMORY_CATEGORIES = {
  MEMO: {
    id: 'memo',
    name: 'Memo',
    subtitle: 'Personal AI Brain',
    icon: 'Brain',
    color: '#39FF14',
    description: 'Direct chat with your AI memory assistant',
    isMain: true,
  },
  WORK: {
    id: 'work',
    name: 'Work Meeting Notes',
    subtitle: 'Project discussions and deadlines',
    icon: 'Briefcase',
    color: '#00D9FF',
    description: 'Professional meetings, project updates, and work-related memories',
  },
  PERSONAL: {
    id: 'personal',
    name: 'Personal Ideas',
    subtitle: 'Creative thoughts and plans',
    icon: 'Lightbulb',
    color: '#FF6B6B',
    description: 'Personal thoughts, creative ideas, and future plans',
  },
  FAMILY: {
    id: 'family',
    name: 'Family Memories',
    subtitle: 'Special moments and events',
    icon: 'Heart',
    color: '#4ECDC4',
    description: 'Family events, celebrations, and precious moments',
  },
  LEARNING: {
    id: 'learning',
    name: 'Learning Notes',
    subtitle: 'Knowledge and insights',
    icon: 'BookOpen',
    color: '#45B7D1',
    description: 'Educational content, courses, and learning materials',
  },
  TRAVEL: {
    id: 'travel',
    name: 'Travel Journal',
    subtitle: 'Adventures and experiences',
    icon: 'MapPin',
    color: '#96CEB4',
    description: 'Travel experiences, places visited, and adventure memories',
  },
  HEALTH: {
    id: 'health',
    name: 'Health Records',
    subtitle: 'Wellness and medical info',
    icon: 'Activity',
    color: '#FFEAA7',
    description: 'Health information, medical records, and wellness tracking',
  },
  FINANCE: {
    id: 'finance',
    name: 'Financial Notes',
    subtitle: 'Money matters and planning',
    icon: 'DollarSign',
    color: '#FD79A8',
    description: 'Financial planning, expenses, and money-related memories',
  },
  CREATIVE: {
    id: 'creative',
    name: 'Creative Projects',
    subtitle: 'Art and creative endeavors',
    icon: 'Palette',
    color: '#A29BFE',
    description: 'Creative projects, artistic ideas, and design inspiration',
  },
};

// Message Types
export const MESSAGE_TYPES = {
  TEXT: 'text',
  VOICE: 'voice',
  IMAGE: 'image',
  VIDEO: 'video',
  DOCUMENT: 'document',
  LOCATION: 'location',
  CONTACT: 'contact',
  SYSTEM: 'system',
};

// Message Status
export const MESSAGE_STATUS = {
  SENDING: 'sending',
  SENT: 'sent',
  DELIVERED: 'delivered',
  READ: 'read',
  FAILED: 'failed',
};

// Sync Status
export const SYNC_STATUS = {
  CONNECTED: 'connected',
  CONNECTING: 'connecting',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
  SYNCING: 'syncing',
};

// Voice Recording States
export const VOICE_STATES = {
  IDLE: 'idle',
  RECORDING: 'recording',
  PROCESSING: 'processing',
  TRANSCRIBING: 'transcribing',
  COMPLETED: 'completed',
  ERROR: 'error',
};

// Theme Options
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system',
};

// Notification Types
export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

// File Upload Limits
export const FILE_LIMITS = {
  MAX_SIZE: 50 * 1024 * 1024, // 50MB
  MAX_FILES: 10,
  ALLOWED_TYPES: {
    IMAGE: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    VIDEO: ['video/mp4', 'video/webm', 'video/ogg'],
    AUDIO: ['audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a'],
    DOCUMENT: ['application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  },
};

// Search Filters
export const SEARCH_FILTERS = {
  ALL: 'all',
  TEXT: 'text',
  VOICE: 'voice',
  IMAGES: 'images',
  DOCUMENTS: 'documents',
  TODAY: 'today',
  WEEK: 'week',
  MONTH: 'month',
  YEAR: 'year',
};

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: 'memo_theme',
  ONBOARDING: 'memo_onboarding_completed',
  USER_PREFERENCES: 'memo_user_preferences',
  SYNC_SETTINGS: 'memo_sync_settings',
  VOICE_SETTINGS: 'memo_voice_settings',
  SEARCH_HISTORY: 'memo_search_history',
  DRAFT_MESSAGES: 'memo_draft_messages',
  OFFLINE_QUEUE: 'memo_offline_queue',
};

// Animation Durations (in milliseconds)
export const ANIMATION_DURATIONS = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
  EXTRA_SLOW: 1000,
};

// Breakpoints for responsive design
export const BREAKPOINTS = {
  SM: 640,
  MD: 768,
  LG: 1024,
  XL: 1280,
  '2XL': 1536,
};

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network connection failed. Please check your internet connection.',
  SYNC_ERROR: 'Failed to sync with WhatsApp. Please check your connection settings.',
  VOICE_ERROR: 'Voice recording failed. Please check microphone permissions.',
  FILE_TOO_LARGE: 'File size exceeds the maximum limit of 50MB.',
  UNSUPPORTED_FILE: 'File type not supported. Please choose a different file.',
  TRANSCRIPTION_ERROR: 'Failed to transcribe audio. Please try again.',
  AI_ERROR: 'AI service is temporarily unavailable. Please try again later.',
  STORAGE_FULL: 'Local storage is full. Please clear some data.',
  PERMISSION_DENIED: 'Permission denied. Please grant the required permissions.',
};

// Success Messages
export const SUCCESS_MESSAGES = {
  SYNC_SUCCESS: 'Successfully synced with WhatsApp.',
  VOICE_SAVED: 'Voice message saved successfully.',
  FILE_UPLOADED: 'File uploaded successfully.',
  SETTINGS_SAVED: 'Settings saved successfully.',
  MEMORY_CREATED: 'Memory created successfully.',
  MEMORY_UPDATED: 'Memory updated successfully.',
  MEMORY_DELETED: 'Memory deleted successfully.',
  EXPORT_SUCCESS: 'Data exported successfully.',
  IMPORT_SUCCESS: 'Data imported successfully.',
};

// Feature Flags
export const FEATURE_FLAGS = {
  VOICE_RECORDING: true,
  VIDEO_CALLS: true,
  FILE_SHARING: true,
  WHATSAPP_SYNC: true,
  AI_SUGGESTIONS: true,
  OFFLINE_MODE: true,
  ANALYTICS: true,
  PUSH_NOTIFICATIONS: true,
  BIOMETRIC_AUTH: false, // Future feature
  COLLABORATIVE_MEMORIES: false, // Future feature
};

// Default Settings
export const DEFAULT_SETTINGS = {
  theme: THEMES.SYSTEM,
  notifications: {
    enabled: true,
    sound: true,
    vibration: true,
    showPreviews: true,
  },
  sync: {
    autoSync: true,
    syncInterval: 300000, // 5 minutes
    syncOnWiFiOnly: false,
  },
  voice: {
    autoTranscribe: true,
    language: 'en-US',
    quality: 'high',
  },
  privacy: {
    analytics: true,
    crashReporting: true,
    dataCollection: true,
  },
  accessibility: {
    fontSize: 'medium',
    highContrast: false,
    reduceMotion: false,
  },
};

// API Endpoints
export const API_ENDPOINTS = {
  AUTH: '/auth',
  MEMORIES: '/memories',
  MESSAGES: '/messages',
  SYNC: '/sync',
  VOICE: '/voice',
  FILES: '/files',
  SEARCH: '/search',
  SETTINGS: '/settings',
  ANALYTICS: '/analytics',
  HEALTH: '/health',
};

// WebSocket Events
export const SOCKET_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  MESSAGE_RECEIVED: 'message_received',
  MESSAGE_SENT: 'message_sent',
  SYNC_STATUS: 'sync_status',
  TYPING_START: 'typing_start',
  TYPING_STOP: 'typing_stop',
  USER_ONLINE: 'user_online',
  USER_OFFLINE: 'user_offline',
  MEMORY_UPDATED: 'memory_updated',
  SYNC_COMPLETE: 'sync_complete',
};

// Regular Expressions
export const REGEX_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PHONE: /^\+?[\d\s\-\(\)]+$/,
  URL: /^https?:\/\/.+/,
  MENTION: /@[\w\d_]+/g,
  HASHTAG: /#[\w\d_]+/g,
  EMOJI: /[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu,
};

// Date Formats
export const DATE_FORMATS = {
  SHORT: 'MMM d',
  MEDIUM: 'MMM d, yyyy',
  LONG: 'MMMM d, yyyy',
  TIME: 'h:mm a',
  DATETIME: 'MMM d, yyyy h:mm a',
  ISO: "yyyy-MM-dd'T'HH:mm:ss.SSSxxx",
};

// Color Palette
export const COLORS = {
  PRIMARY: '#39FF14',
  SECONDARY: '#00D9FF',
  SUCCESS: '#10B981',
  WARNING: '#F59E0B',
  ERROR: '#EF4444',
  INFO: '#3B82F6',
  DARK_BG: '#0D1117',
  DARK_SURFACE: '#161B22',
  DARK_BORDER: '#30363D',
  LIGHT_BG: '#FFFFFF',
  LIGHT_SURFACE: '#F8F9FA',
  LIGHT_BORDER: '#E5E7EB',
};

// Z-Index Layers
export const Z_INDEX = {
  DROPDOWN: 1000,
  STICKY: 1020,
  FIXED: 1030,
  MODAL_BACKDROP: 1040,
  MODAL: 1050,
  POPOVER: 1060,
  TOOLTIP: 1070,
  TOAST: 1080,
};

export default {
  APP_CONFIG,
  API_CONFIG,
  OPENAI_CONFIG,
  WHATSAPP_CONFIG,
  MEMORY_CATEGORIES,
  MESSAGE_TYPES,
  MESSAGE_STATUS,
  SYNC_STATUS,
  VOICE_STATES,
  THEMES,
  NOTIFICATION_TYPES,
  FILE_LIMITS,
  SEARCH_FILTERS,
  STORAGE_KEYS,
  ANIMATION_DURATIONS,
  BREAKPOINTS,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  FEATURE_FLAGS,
  DEFAULT_SETTINGS,
  API_ENDPOINTS,
  SOCKET_EVENTS,
  REGEX_PATTERNS,
  DATE_FORMATS,
  COLORS,
  Z_INDEX,
};

