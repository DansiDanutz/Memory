// Shared types for conversation engine
export interface ConversationContext {
  userId: string;
  sessionId: string;
  conversationHistory: ConversationMessage[];
  memoryContext?: any;
  securityLevel: 'General' | 'Secret' | 'Ultra' | 'C2' | 'C3';
}

export interface ConversationMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: {
    trustScore?: number;
    mkeScore?: number;
    sleDecision?: any;
  };
}

export interface ConversationResponse {
  message: string;
  confidence: number;
  reasoning: string[];
  needsVerification: boolean;
  redactedContent?: string[];
  followUpQuestions?: string[];
}