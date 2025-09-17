/**
 * Main API Service Configuration
 * Handles axios setup and base configuration
 */
import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Request interceptor to add auth headers if needed
api.interceptors.request.use(
  (config) => {
    // Add HMAC signature if required
    const timestamp = new Date().toISOString();
    config.headers['X-Timestamp'] = timestamp;
    
    // Add user ID from localStorage if available
    const userId = localStorage.getItem('userId');
    if (userId) {
      config.headers['X-User-ID'] = userId;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.data);
      
      if (error.response.status === 401) {
        // Handle unauthorized
        console.error('Unauthorized access');
      } else if (error.response.status === 429) {
        // Rate limit exceeded
        console.error('Rate limit exceeded');
      }
    } else if (error.request) {
      // Request made but no response
      console.error('Network error:', error.request);
    } else {
      // Something else happened
      console.error('Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default api;