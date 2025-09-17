/**
 * Claude AI Service
 * Handles all Claude AI-related API operations
 */
import api from './apiService';

class ClaudeService {
  /**
   * Check Claude service status
   */
  async getStatus() {
    try {
      return await api.get('/claude/status');
    } catch (error) {
      console.error('Error getting Claude status:', error);
      throw error;
    }
  }

  /**
   * Perform health check
   */
  async healthCheck() {
    try {
      return await api.get('/claude/health');
    } catch (error) {
      console.error('Error checking Claude health:', error);
      throw error;
    }
  }

  /**
   * Analyze message for sentiment, intent, and categorization
   */
  async analyzeMessage(message, context = null) {
    try {
      return await api.post('/claude/analyze', {
        message,
        context
      });
    } catch (error) {
      console.error('Error analyzing message:', error);
      throw error;
    }
  }

  /**
   * Generate AI response
   */
  async generateResponse(message, context = null, tone = 'friendly', maxLength = null) {
    try {
      return await api.post('/claude/generate', {
        message,
        context,
        tone,
        max_length: maxLength
      });
    } catch (error) {
      console.error('Error generating response:', error);
      throw error;
    }
  }

  /**
   * Summarize conversation
   */
  async summarizeConversation(messages, maxLength = 200, focusTopics = null) {
    try {
      return await api.post('/claude/summarize', {
        messages,
        max_length: maxLength,
        focus_topics: focusTopics
      });
    } catch (error) {
      console.error('Error summarizing conversation:', error);
      throw error;
    }
  }

  /**
   * Extract memories from text
   */
  async extractMemories(text, context = null) {
    try {
      return await api.post('/claude/extract-memory', {
        text,
        context
      });
    } catch (error) {
      console.error('Error extracting memories:', error);
      throw error;
    }
  }

  /**
   * Get usage statistics
   */
  async getUsageStats() {
    try {
      return await api.get('/claude/usage');
    } catch (error) {
      console.error('Error getting usage stats:', error);
      throw error;
    }
  }
}

export default new ClaudeService();