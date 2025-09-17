// Memory Storage System for Conversation Transcripts and Voice Retrieval
import { v4 as uuidv4 } from 'uuid';
import { evaluate, SLEContext } from '@memory-app/sle';
// Voice processor will be injected - avoiding import issues
// import { VoiceProcessor } from '@memory-app/voice-processor';
import { logger } from '@memory-app/conversation/src/production-logger';

export interface ConversationEntry {
  id: string;
  memoryNumber?: string;
  participants: string[];
  content: string;
  summary?: string;
  timestamp: Date;
  platform: 'whatsapp' | 'telegram' | 'call';
  messageType: 'text' | 'voice' | 'image' | 'call_transcript';
  metadata: {
    duration?: number;
    callType?: 'incoming' | 'outgoing' | 'missed';
    voiceAnalysis?: {
      sentiment: 'positive' | 'negative' | 'neutral';
      topics: string[];
      keyPhrases: string[];
    };
  };
  privacyLevel: 'public' | 'private' | 'confidential';
  approved: boolean;
  tags: string[];
}

export interface RelationshipProfile {
  contactId: string;
  name: string;
  platform: 'whatsapp' | 'telegram';
  relationshipType: 'family' | 'friend' | 'colleague' | 'acquaintance';
  trustLevel: 'Green' | 'Amber' | 'Red';
  conversationHistory: ConversationEntry[];
  insights: {
    commonTopics: string[];
    communicationStyle: string;
    preferredTimes: string[];
    lastSummaryDate: Date;
    approvedSummaries: ConversationEntry[];
    rejectedSummaries: ConversationEntry[];
  };
  preferences: {
    allowCallHandling: boolean;
    autoSummary: boolean;
    memorySharing: 'full' | 'limited' | 'minimal';
  };
}

export interface MemorySearchRequest {
  query: string;
  voiceQuery?: boolean;
  contactFilter?: string[];
  dateRange?: { from: Date; to: Date };
  memoryNumber?: string;
  searchType: 'exact' | 'semantic' | 'voice_activated';
}

export interface MemorySearchResult {
  entries: ConversationEntry[];
  summary: string;
  confidence: number;
  searchTime: number;
  totalFound: number;
}

export class MemoryStorageSystem {
  private conversations: Map<string, ConversationEntry> = new Map();
  private profiles: Map<string, RelationshipProfile> = new Map();
  private memoryNumbers: Map<string, string> = new Map(); // memoryNumber -> conversationId
  private voiceProcessor: any; // Flexible typing to avoid import issues
  private nextMemoryNumber = 1000;

  constructor(voiceProcessor?: any) {
    this.voiceProcessor = voiceProcessor || {
      transcribeAudio: async () => ({ text: '', confidence: 0 }),
      extractMemoryNumber: () => null
    };
    
    logger.info('MemoryStorage', 'Memory storage system initialized', {
      voiceProcessingEnabled: true,
      memoryNumberStart: this.nextMemoryNumber
    });
  }

  // PRIORITY 1: Store conversations and enable voice-activated retrieval
  async storeConversation(entry: Partial<ConversationEntry>): Promise<ConversationEntry> {
    const conversationEntry: ConversationEntry = {
      id: entry.id || uuidv4(),
      memoryNumber: entry.memoryNumber || this.generateMemoryNumber(),
      participants: entry.participants || [],
      content: entry.content || '',
      summary: entry.summary,
      timestamp: entry.timestamp || new Date(),
      platform: entry.platform || 'telegram',
      messageType: entry.messageType || 'text',
      metadata: entry.metadata || {},
      privacyLevel: entry.privacyLevel || 'private',
      approved: entry.approved !== undefined ? entry.approved : false,
      tags: entry.tags || []
    };

    this.conversations.set(conversationEntry.id, conversationEntry);
    
    if (conversationEntry.memoryNumber) {
      this.memoryNumbers.set(conversationEntry.memoryNumber, conversationEntry.id);
    }

    // Update relationship profiles
    for (const participant of conversationEntry.participants) {
      await this.updateRelationshipProfile(participant, conversationEntry);
    }

    logger.info('MemoryStorage', 'Conversation stored', {
      id: conversationEntry.id,
      memoryNumber: conversationEntry.memoryNumber,
      participants: conversationEntry.participants.length,
      approved: conversationEntry.approved
    });

    return conversationEntry;
  }

  async searchMemoryByVoice(audioBuffer: Buffer, callerId: string): Promise<MemorySearchResult> {
    try {
      logger.debug('MemoryStorage', 'Processing voice memory search', {
        callerId,
        audioSize: audioBuffer.length
      });

      // Transcribe voice query
      const transcription = await this.voiceProcessor.transcribeAudio(audioBuffer);
      
      if (!transcription.text) {
        throw new Error('Could not transcribe voice query');
      }

      // Check for Memory Number in speech
      if (transcription.memoryNumber) {
        return await this.retrieveByMemoryNumber(transcription.memoryNumber, callerId);
      }

      // Semantic search based on voice content
      return await this.searchMemory({
        query: transcription.text,
        voiceQuery: true,
        searchType: 'voice_activated'
      }, callerId);

    } catch (error) {
      logger.error('MemoryStorage', 'Voice memory search failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        callerId
      });

      return {
        entries: [],
        summary: 'Voice search failed',
        confidence: 0,
        searchTime: 0,
        totalFound: 0
      };
    }
  }

  async retrieveByMemoryNumber(memoryNumber: string, callerId: string): Promise<MemorySearchResult> {
    const startTime = Date.now();

    try {
      // Check SLE permissions
      const sleContext: SLEContext = {
        callerId,
        utterance: `Access Memory Number ${memoryNumber}`,
        domain: 'Memories'
      };

      const decision = await evaluate(sleContext);
      
      if (decision.outcome !== 'disclose') {
        logger.warn('MemoryStorage', 'Memory Number access denied', {
          memoryNumber,
          callerId,
          reason: decision.reasonCodes
        });

        return {
          entries: [],
          summary: `Access denied to Memory Number ${memoryNumber}. Reason: ${decision.reasonCodes.join(', ')}`,
          confidence: 1.0,
          searchTime: Date.now() - startTime,
          totalFound: 0
        };
      }

      const conversationId = this.memoryNumbers.get(memoryNumber);
      if (!conversationId) {
        return {
          entries: [],
          summary: `Memory Number ${memoryNumber} not found`,
          confidence: 1.0,
          searchTime: Date.now() - startTime,
          totalFound: 0
        };
      }

      const conversation = this.conversations.get(conversationId);
      if (!conversation) {
        return {
          entries: [],
          summary: `Memory Number ${memoryNumber} points to invalid conversation`,
          confidence: 1.0,
          searchTime: Date.now() - startTime,
          totalFound: 0
        };
      }

      logger.info('MemoryStorage', 'Memory Number retrieved successfully', {
        memoryNumber,
        callerId,
        conversationId: conversation.id
      });

      return {
        entries: [conversation],
        summary: conversation.summary || conversation.content.substring(0, 200) + '...',
        confidence: 1.0,
        searchTime: Date.now() - startTime,
        totalFound: 1
      };

    } catch (error) {
      logger.error('MemoryStorage', 'Memory Number retrieval failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        memoryNumber,
        callerId
      });

      return {
        entries: [],
        summary: 'Memory retrieval failed',
        confidence: 0,
        searchTime: Date.now() - startTime,
        totalFound: 0
      };
    }
  }

  async searchMemory(request: MemorySearchRequest, callerId: string): Promise<MemorySearchResult> {
    const startTime = Date.now();
    const results: ConversationEntry[] = [];

    try {
      logger.debug('MemoryStorage', 'Searching memory', {
        query: request.query,
        searchType: request.searchType,
        callerId
      });

      // Search through conversations
      for (const [id, conversation] of this.conversations) {
        if (this.matchesSearchCriteria(conversation, request)) {
          // Check SLE permissions for this conversation
          const sleContext: SLEContext = {
            callerId,
            utterance: `Access conversation: ${request.query}`,
            domain: 'Memories'
          };

          const decision = await evaluate(sleContext);
          
          if (decision.outcome === 'disclose') {
            results.push(conversation);
          }
        }
      }

      // Sort by relevance and timestamp
      results.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

      const summary = this.generateSearchSummary(results, request.query);

      logger.info('MemoryStorage', 'Memory search completed', {
        query: request.query,
        resultsFound: results.length,
        searchTime: Date.now() - startTime,
        callerId
      });

      return {
        entries: results.slice(0, 10), // Limit to 10 most relevant
        summary,
        confidence: results.length > 0 ? 0.8 : 0.1,
        searchTime: Date.now() - startTime,
        totalFound: results.length
      };

    } catch (error) {
      logger.error('MemoryStorage', 'Memory search failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        query: request.query,
        callerId
      });

      return {
        entries: [],
        summary: 'Search failed',
        confidence: 0,
        searchTime: Date.now() - startTime,
        totalFound: 0
      };
    }
  }

  // PRIORITY 2: Get relationship profile for call handling
  getRelationshipProfile(contactId: string): RelationshipProfile | null {
    return this.profiles.get(contactId) || null;
  }

  async updateRelationshipProfile(contactId: string, conversation: ConversationEntry): Promise<void> {
    let profile = this.profiles.get(contactId);

    if (!profile) {
      profile = {
        contactId,
        name: contactId, // Will be updated with actual name
        platform: conversation.platform,
        relationshipType: 'acquaintance',
        trustLevel: 'Red',
        conversationHistory: [],
        insights: {
          commonTopics: [],
          communicationStyle: 'neutral',
          preferredTimes: [],
          lastSummaryDate: new Date(),
          approvedSummaries: [],
          rejectedSummaries: []
        },
        preferences: {
          allowCallHandling: false,
          autoSummary: true,
          memorySharing: 'minimal'
        }
      };
    }

    // Add conversation to history
    profile.conversationHistory.push(conversation);

    // Update insights based on conversation
    await this.analyzeConversationInsights(profile, conversation);

    this.profiles.set(contactId, profile);

    logger.debug('MemoryStorage', 'Relationship profile updated', {
      contactId,
      conversationCount: profile.conversationHistory.length,
      trustLevel: profile.trustLevel
    });
  }

  // PRIORITY 3: Generate daily summaries
  async generateDailySummary(date: Date = new Date()): Promise<{
    summaries: ConversationEntry[];
    pendingApproval: ConversationEntry[];
  }> {
    const startOfDay = new Date(date);
    startOfDay.setHours(0, 0, 0, 0);
    
    const endOfDay = new Date(date);
    endOfDay.setHours(23, 59, 59, 999);

    const dailyConversations = Array.from(this.conversations.values())
      .filter(conv => conv.timestamp >= startOfDay && conv.timestamp <= endOfDay)
      .filter(conv => !conv.summary); // Only conversations without summaries

    const summaries: ConversationEntry[] = [];
    const pendingApproval: ConversationEntry[] = [];

    for (const conversation of dailyConversations) {
      const summary = await this.createConversationSummary(conversation);
      
      const summaryEntry: ConversationEntry = {
        ...conversation,
        summary: summary,
        approved: false, // Requires user approval
        tags: [...conversation.tags, 'daily_summary', 'pending_approval']
      };

      pendingApproval.push(summaryEntry);
    }

    logger.info('MemoryStorage', 'Daily summary generated', {
      date: date.toISOString().split('T')[0],
      conversationsProcessed: dailyConversations.length,
      pendingApproval: pendingApproval.length
    });

    return {
      summaries,
      pendingApproval
    };
  }

  async approveSummary(conversationId: string, approved: boolean): Promise<void> {
    const conversation = this.conversations.get(conversationId);
    if (!conversation) {
      throw new Error(`Conversation ${conversationId} not found`);
    }

    conversation.approved = approved;
    conversation.tags = conversation.tags.filter(tag => tag !== 'pending_approval');
    
    if (approved) {
      conversation.tags.push('approved_summary');
      
      // Update relationship profiles with approved summary
      for (const participant of conversation.participants) {
        const profile = this.profiles.get(participant);
        if (profile) {
          profile.insights.approvedSummaries.push(conversation);
        }
      }
    } else {
      conversation.tags.push('rejected_summary');
      
      // Track rejected summaries for learning
      for (const participant of conversation.participants) {
        const profile = this.profiles.get(participant);
        if (profile) {
          profile.insights.rejectedSummaries.push(conversation);
        }
      }
    }

    this.conversations.set(conversationId, conversation);

    logger.info('MemoryStorage', 'Summary approval processed', {
      conversationId,
      approved,
      participants: conversation.participants.length
    });
  }

  // Helper methods
  private generateMemoryNumber(): string {
    const memoryNumber = this.nextMemoryNumber.toString();
    this.nextMemoryNumber++;
    return memoryNumber;
  }

  private matchesSearchCriteria(conversation: ConversationEntry, request: MemorySearchRequest): boolean {
    const query = request.query.toLowerCase();
    
    // Check content match
    const contentMatch = conversation.content.toLowerCase().includes(query) ||
                        (conversation.summary && conversation.summary.toLowerCase().includes(query));
    
    // Check participant filter
    const participantMatch = !request.contactFilter || 
                           request.contactFilter.some(contact => 
                             conversation.participants.includes(contact));
    
    // Check date range
    const dateMatch = !request.dateRange || 
                     (conversation.timestamp >= request.dateRange.from && 
                      conversation.timestamp <= request.dateRange.to);
    
    return contentMatch && participantMatch && dateMatch;
  }

  private generateSearchSummary(results: ConversationEntry[], query: string): string {
    if (results.length === 0) {
      return `No memories found for "${query}"`;
    }

    if (results.length === 1) {
      return results[0].summary || results[0].content.substring(0, 100) + '...';
    }

    const topics = new Set<string>();
    results.forEach(result => {
      result.tags.forEach(tag => topics.add(tag));
    });

    return `Found ${results.length} memories about "${query}". Main topics: ${Array.from(topics).slice(0, 5).join(', ')}`;
  }

  private async analyzeConversationInsights(profile: RelationshipProfile, conversation: ConversationEntry): Promise<void> {
    // Extract topics from conversation
    const words = conversation.content.toLowerCase().split(/\s+/);
    const topics = words.filter(word => word.length > 4);
    
    // Update common topics
    topics.forEach(topic => {
      if (!profile.insights.commonTopics.includes(topic)) {
        profile.insights.commonTopics.push(topic);
      }
    });

    // Keep only top 10 most common topics
    profile.insights.commonTopics = profile.insights.commonTopics.slice(0, 10);

    // Update communication style based on content
    if (conversation.content.includes('!') || conversation.content.includes('CAPS')) {
      profile.insights.communicationStyle = 'energetic';
    } else if (conversation.content.length > 200) {
      profile.insights.communicationStyle = 'detailed';
    } else {
      profile.insights.communicationStyle = 'concise';
    }
  }

  private async createConversationSummary(conversation: ConversationEntry): Promise<string> {
    // Simple extractive summary - in production, use advanced NLP
    const sentences = conversation.content.split(/[.!?]+/).filter(s => s.length > 10);
    
    if (sentences.length <= 2) {
      return conversation.content;
    }

    // Return first and last sentence as summary
    return `${sentences[0].trim()}. ${sentences[sentences.length - 1].trim()}.`;
  }

  // Status and statistics
  getStorageStats(): {
    totalConversations: number;
    totalProfiles: number;
    totalMemoryNumbers: number;
    pendingApprovals: number;
    storageSize: string;
  } {
    const pendingApprovals = Array.from(this.conversations.values())
      .filter(conv => conv.tags.includes('pending_approval')).length;

    return {
      totalConversations: this.conversations.size,
      totalProfiles: this.profiles.size,
      totalMemoryNumbers: this.memoryNumbers.size,
      pendingApprovals,
      storageSize: `${Math.round(JSON.stringify(Array.from(this.conversations.values())).length / 1024)}KB`
    };
  }
}

// Export convenience functions
export async function storeConversationMemory(
  content: string,
  participants: string[],
  platform: 'whatsapp' | 'telegram' | 'call' = 'telegram'
): Promise<ConversationEntry> {
  const storage = new MemoryStorageSystem();
  return await storage.storeConversation({
    content,
    participants,
    platform,
    messageType: 'text',
    timestamp: new Date()
  });
}

export async function searchMemoryByVoice(audioBuffer: Buffer, callerId: string): Promise<MemorySearchResult> {
  const storage = new MemoryStorageSystem();
  return await storage.searchMemoryByVoice(audioBuffer, callerId);
}