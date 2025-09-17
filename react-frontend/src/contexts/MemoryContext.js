import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { memoryAPI, messageAPI } from '../services/api';
import { MEMORY_CATEGORIES, MESSAGE_STATUS, STORAGE_KEYS } from '../utils/constants';

const MemoryContext = createContext();

export const useMemory = () => {
  const context = useContext(MemoryContext);
  if (!context) {
    throw new Error('useMemory must be used within a MemoryProvider');
  }
  return context;
};

// Action types
const MEMORY_ACTIONS = {
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_MEMORIES: 'SET_MEMORIES',
  ADD_MEMORY: 'ADD_MEMORY',
  UPDATE_MEMORY: 'UPDATE_MEMORY',
  DELETE_MEMORY: 'DELETE_MEMORY',
  SET_ACTIVE_MEMORY: 'SET_ACTIVE_MEMORY',
  SET_MESSAGES: 'SET_MESSAGES',
  ADD_MESSAGE: 'ADD_MESSAGE',
  UPDATE_MESSAGE: 'UPDATE_MESSAGE',
  DELETE_MESSAGE: 'DELETE_MESSAGE',
  SET_TYPING: 'SET_TYPING',
  SET_DRAFT: 'SET_DRAFT',
  CLEAR_DRAFT: 'CLEAR_DRAFT',
  SET_SEARCH_RESULTS: 'SET_SEARCH_RESULTS',
  CLEAR_SEARCH: 'CLEAR_SEARCH',
};

// Initial state
const initialState = {
  memories: [],
  activeMemory: null,
  messages: {},
  loading: false,
  error: null,
  typing: false,
  drafts: {},
  searchResults: [],
  searchQuery: '',
  stats: {
    totalMemories: 0,
    totalMessages: 0,
    categoryCounts: {},
  },
};

// Reducer function
const memoryReducer = (state, action) => {
  switch (action.type) {
    case MEMORY_ACTIONS.SET_LOADING:
      return { ...state, loading: action.payload };
    
    case MEMORY_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload, loading: false };
    
    case MEMORY_ACTIONS.SET_MEMORIES:
      return { 
        ...state, 
        memories: action.payload,
        loading: false,
        error: null,
      };
    
    case MEMORY_ACTIONS.ADD_MEMORY:
      return {
        ...state,
        memories: [action.payload, ...state.memories],
      };
    
    case MEMORY_ACTIONS.UPDATE_MEMORY:
      return {
        ...state,
        memories: state.memories.map(memory =>
          memory.id === action.payload.id ? action.payload : memory
        ),
        activeMemory: state.activeMemory?.id === action.payload.id 
          ? action.payload 
          : state.activeMemory,
      };
    
    case MEMORY_ACTIONS.DELETE_MEMORY:
      return {
        ...state,
        memories: state.memories.filter(memory => memory.id !== action.payload),
        activeMemory: state.activeMemory?.id === action.payload ? null : state.activeMemory,
        messages: {
          ...state.messages,
          [action.payload]: undefined,
        },
      };
    
    case MEMORY_ACTIONS.SET_ACTIVE_MEMORY:
      return { ...state, activeMemory: action.payload };
    
    case MEMORY_ACTIONS.SET_MESSAGES:
      return {
        ...state,
        messages: {
          ...state.messages,
          [action.payload.memoryId]: action.payload.messages,
        },
      };
    
    case MEMORY_ACTIONS.ADD_MESSAGE:
      const memoryId = action.payload.memoryId;
      return {
        ...state,
        messages: {
          ...state.messages,
          [memoryId]: [
            ...(state.messages[memoryId] || []),
            action.payload.message,
          ],
        },
      };
    
    case MEMORY_ACTIONS.UPDATE_MESSAGE:
      const updateMemoryId = action.payload.memoryId;
      return {
        ...state,
        messages: {
          ...state.messages,
          [updateMemoryId]: (state.messages[updateMemoryId] || []).map(msg =>
            msg.id === action.payload.message.id ? action.payload.message : msg
          ),
        },
      };
    
    case MEMORY_ACTIONS.DELETE_MESSAGE:
      const deleteMemoryId = action.payload.memoryId;
      return {
        ...state,
        messages: {
          ...state.messages,
          [deleteMemoryId]: (state.messages[deleteMemoryId] || []).filter(
            msg => msg.id !== action.payload.messageId
          ),
        },
      };
    
    case MEMORY_ACTIONS.SET_TYPING:
      return { ...state, typing: action.payload };
    
    case MEMORY_ACTIONS.SET_DRAFT:
      return {
        ...state,
        drafts: {
          ...state.drafts,
          [action.payload.memoryId]: action.payload.draft,
        },
      };
    
    case MEMORY_ACTIONS.CLEAR_DRAFT:
      const { [action.payload]: removed, ...remainingDrafts } = state.drafts;
      return { ...state, drafts: remainingDrafts };
    
    case MEMORY_ACTIONS.SET_SEARCH_RESULTS:
      return {
        ...state,
        searchResults: action.payload.results,
        searchQuery: action.payload.query,
      };
    
    case MEMORY_ACTIONS.CLEAR_SEARCH:
      return {
        ...state,
        searchResults: [],
        searchQuery: '',
      };
    
    default:
      return state;
  }
};

export const MemoryProvider = ({ children }) => {
  const [state, dispatch] = useReducer(memoryReducer, initialState);

  // Load memories on mount
  useEffect(() => {
    loadMemories();
    loadDrafts();
  }, []);

  // Save drafts to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.DRAFT_MESSAGES, JSON.stringify(state.drafts));
  }, [state.drafts]);

  // Load memories from API
  const loadMemories = async () => {
    try {
      dispatch({ type: MEMORY_ACTIONS.SET_LOADING, payload: true });
      const response = await memoryAPI.getMemories();
      dispatch({ type: MEMORY_ACTIONS.SET_MEMORIES, payload: response.data });
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
    }
  };

  // Load drafts from localStorage
  const loadDrafts = () => {
    try {
      const savedDrafts = localStorage.getItem(STORAGE_KEYS.DRAFT_MESSAGES);
      if (savedDrafts) {
        const drafts = JSON.parse(savedDrafts);
        Object.entries(drafts).forEach(([memoryId, draft]) => {
          dispatch({
            type: MEMORY_ACTIONS.SET_DRAFT,
            payload: { memoryId, draft },
          });
        });
      }
    } catch (error) {
      console.error('Failed to load drafts:', error);
    }
  };

  // Create new memory
  const createMemory = async (memoryData) => {
    try {
      const response = await memoryAPI.createMemory(memoryData);
      dispatch({ type: MEMORY_ACTIONS.ADD_MEMORY, payload: response.data });
      return response.data;
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
      throw error;
    }
  };

  // Update memory
  const updateMemory = async (memoryId, memoryData) => {
    try {
      const response = await memoryAPI.updateMemory(memoryId, memoryData);
      dispatch({ type: MEMORY_ACTIONS.UPDATE_MEMORY, payload: response.data });
      return response.data;
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
      throw error;
    }
  };

  // Delete memory
  const deleteMemory = async (memoryId) => {
    try {
      await memoryAPI.deleteMemory(memoryId);
      dispatch({ type: MEMORY_ACTIONS.DELETE_MEMORY, payload: memoryId });
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
      throw error;
    }
  };

  // Set active memory
  const setActiveMemory = (memory) => {
    dispatch({ type: MEMORY_ACTIONS.SET_ACTIVE_MEMORY, payload: memory });
    if (memory) {
      loadMessages(memory.id);
    }
  };

  // Load messages for a memory
  const loadMessages = async (memoryId) => {
    try {
      const response = await messageAPI.getMessages(memoryId);
      dispatch({
        type: MEMORY_ACTIONS.SET_MESSAGES,
        payload: { memoryId, messages: response.data },
      });
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
    }
  };

  // Send message
  const sendMessage = async (memoryId, messageData) => {
    try {
      // Add optimistic message
      const optimisticMessage = {
        id: `temp_${Date.now()}`,
        ...messageData,
        status: MESSAGE_STATUS.SENDING,
        timestamp: new Date().toISOString(),
      };
      
      dispatch({
        type: MEMORY_ACTIONS.ADD_MESSAGE,
        payload: { memoryId, message: optimisticMessage },
      });

      // Send to API
      const response = await messageAPI.sendMessage(memoryId, messageData);
      
      // Update with real message
      dispatch({
        type: MEMORY_ACTIONS.UPDATE_MESSAGE,
        payload: { memoryId, message: response.data },
      });

      // Clear draft
      dispatch({ type: MEMORY_ACTIONS.CLEAR_DRAFT, payload: memoryId });

      return response.data;
    } catch (error) {
      // Update message status to failed
      dispatch({
        type: MEMORY_ACTIONS.UPDATE_MESSAGE,
        payload: {
          memoryId,
          message: { ...optimisticMessage, status: MESSAGE_STATUS.FAILED },
        },
      });
      throw error;
    }
  };

  // Update message
  const updateMessage = async (memoryId, messageId, messageData) => {
    try {
      const response = await messageAPI.updateMessage(messageId, messageData);
      dispatch({
        type: MEMORY_ACTIONS.UPDATE_MESSAGE,
        payload: { memoryId, message: response.data },
      });
      return response.data;
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
      throw error;
    }
  };

  // Delete message
  const deleteMessage = async (memoryId, messageId) => {
    try {
      await messageAPI.deleteMessage(messageId);
      dispatch({
        type: MEMORY_ACTIONS.DELETE_MESSAGE,
        payload: { memoryId, messageId },
      });
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
      throw error;
    }
  };

  // Set typing indicator
  const setTyping = (isTyping) => {
    dispatch({ type: MEMORY_ACTIONS.SET_TYPING, payload: isTyping });
  };

  // Save draft message
  const saveDraft = (memoryId, draft) => {
    dispatch({
      type: MEMORY_ACTIONS.SET_DRAFT,
      payload: { memoryId, draft },
    });
  };

  // Clear draft message
  const clearDraft = (memoryId) => {
    dispatch({ type: MEMORY_ACTIONS.CLEAR_DRAFT, payload: memoryId });
  };

  // Search memories
  const searchMemories = async (query, filters = {}) => {
    try {
      const response = await memoryAPI.searchMemories(query, filters);
      dispatch({
        type: MEMORY_ACTIONS.SET_SEARCH_RESULTS,
        payload: { results: response.data, query },
      });
      return response.data;
    } catch (error) {
      dispatch({ type: MEMORY_ACTIONS.SET_ERROR, payload: error.message });
      throw error;
    }
  };

  // Clear search results
  const clearSearch = () => {
    dispatch({ type: MEMORY_ACTIONS.CLEAR_SEARCH });
  };

  // Get memory by category
  const getMemoriesByCategory = (categoryId) => {
    return state.memories.filter(memory => memory.categoryId === categoryId);
  };

  // Get memory statistics
  const getMemoryStats = () => {
    const stats = {
      totalMemories: state.memories.length,
      totalMessages: Object.values(state.messages).reduce(
        (total, messages) => total + messages.length,
        0
      ),
      categoryCounts: {},
    };

    // Count memories by category
    Object.values(MEMORY_CATEGORIES).forEach(category => {
      stats.categoryCounts[category.id] = state.memories.filter(
        memory => memory.categoryId === category.id
      ).length;
    });

    return stats;
  };

  const value = {
    // State
    ...state,
    
    // Actions
    loadMemories,
    createMemory,
    updateMemory,
    deleteMemory,
    setActiveMemory,
    loadMessages,
    sendMessage,
    updateMessage,
    deleteMessage,
    setTyping,
    saveDraft,
    clearDraft,
    searchMemories,
    clearSearch,
    
    // Computed values
    getMemoriesByCategory,
    getMemoryStats,
  };

  return (
    <MemoryContext.Provider value={value}>
      {children}
    </MemoryContext.Provider>
  );
};

