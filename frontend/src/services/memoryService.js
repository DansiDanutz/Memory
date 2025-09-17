/**
 * Memory Service
 * Handles all memory-related API operations
 */
import api from './apiService';

class MemoryService {
  /**
   * Create a new memory
   */
  async createMemory(memory) {
    try {
      return await api.post('/memories/create', memory);
    } catch (error) {
      console.error('Error creating memory:', error);
      throw error;
    }
  }

  /**
   * Retrieve memories for a user
   */
  async retrieveMemories(userId, category = null, limit = 20, offset = 0) {
    try {
      const params = { limit, offset };
      if (category) params.category = category;
      
      return await api.get(`/memories/list/${userId}`, { params });
    } catch (error) {
      console.error('Error retrieving memories:', error);
      throw error;
    }
  }

  /**
   * Search memories
   */
  async searchMemories(searchRequest) {
    try {
      return await api.post('/memories/search', searchRequest);
    } catch (error) {
      console.error('Error searching memories:', error);
      throw error;
    }
  }

  /**
   * Get memory by ID
   */
  async getMemory(memoryId, userId) {
    try {
      return await api.get(`/memories/${memoryId}`, {
        params: { user_id: userId }
      });
    } catch (error) {
      console.error('Error getting memory:', error);
      throw error;
    }
  }

  /**
   * Update a memory
   */
  async updateMemory(memoryId, updates) {
    try {
      return await api.put(`/memories/${memoryId}`, updates);
    } catch (error) {
      console.error('Error updating memory:', error);
      throw error;
    }
  }

  /**
   * Delete a memory
   */
  async deleteMemory(memoryId) {
    try {
      return await api.delete(`/memories/${memoryId}`);
    } catch (error) {
      console.error('Error deleting memory:', error);
      throw error;
    }
  }

  /**
   * Get category summary
   */
  async getCategorySummary(userId) {
    try {
      return await api.get(`/memories/summary/${userId}/categories`);
    } catch (error) {
      console.error('Error getting category summary:', error);
      throw error;
    }
  }

  /**
   * Get daily digest
   */
  async getDailyDigest(userId, date = null) {
    try {
      const params = date ? { date: date.toISOString() } : {};
      return await api.get(`/memories/digest/${userId}`, { params });
    } catch (error) {
      console.error('Error getting daily digest:', error);
      throw error;
    }
  }

  /**
   * Analyze memory content
   */
  async analyzeMemory(content) {
    try {
      return await api.post('/memories/analyze', { content });
    } catch (error) {
      console.error('Error analyzing memory:', error);
      throw error;
    }
  }

  /**
   * Export memories
   */
  async exportMemories(userId, format = 'json') {
    try {
      return await api.get(`/memories/export/${userId}`, {
        params: { format },
        responseType: 'blob'
      });
    } catch (error) {
      console.error('Error exporting memories:', error);
      throw error;
    }
  }
}

export default new MemoryService();