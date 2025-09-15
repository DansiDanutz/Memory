// API Configuration
// Using relative URLs since Vite proxy handles the backend connection
export const API_BASE_URL = '';  // Empty string means use relative URLs

export const API_ENDPOINTS = {
  SIGNUP: '/api/signup',
  LOGIN: '/api/login',
  LOGOUT: '/api/logout',
  MEMORIES: '/api/memories',
  CHAT: '/api/chat',
  SEARCH: '/api/search',
  STATS: '/api/stats'
};

// Helper function to get full API URL
export const getApiUrl = (endpoint) => {
  return `${API_BASE_URL}${endpoint}`;
};