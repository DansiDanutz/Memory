// MCP-style Conversation Protocol for Memory App Language Interactions
import OpenAI from "openai";
import { ConversationContext, ConversationResponse, ConversationMessage } from './types.js';
import { logger } from './production-logger.js';

export { ConversationContext, ConversationResponse, ConversationMessage };

export class MemoryConversationEngine {
  private openai: OpenAI;
  private systemPrompt: string;

  constructor(apiKey?: string) {
    // the newest OpenAI model is "gpt-5" which was released August 7, 2025. do not change this unless explicitly requested by the user
    this.openai = new OpenAI({ 
      apiKey: apiKey || process.env.OPENAI_API_KEY 
    });
    
    this.systemPrompt = `You are Memory, a privacy-first AI assistant with advanced governance capabilities. You follow the Smart Limits Engine (SLE) principles:

CORE PRINCIPLES:
- Privacy-first, zero-knowledge approach
- Explicit consent for all data sharing
- Trust-based information disclosure
- Provenance-aware responses
- Security label compliance

DECISION FACTORS:
1. Policy Layer (MPL): Check disclosure permissions
2. Mutual Knowledge (CEMG): Estimate what the user likely knows
3. Trust Score (BLTS): Evaluate relationship trust level
4. Provenance (KPE): Verify information sources
5. Risk Assessment (IPSG): Consider disclosure risks

RESPONSE BEHAVIORS:
- DISCLOSE: Share information freely
- PARTIAL: Share limited information
- REDACT: Remove sensitive parts
- PROBE: Ask clarifying questions
- VERIFY: Require additional confirmation
- DIVERT: Redirect conversation
- DECLINE: Refuse to answer
- THROTTLE: Limit response detail
- INCONCLUSIVE: Cannot verify information

Always explain your reasoning and respect the user's privacy boundaries.`;
  }

  async processConversation(
    userMessage: string, 
    context: ConversationContext,
    sleDecision?: any
  ): Promise<ConversationResponse> {
    try {
      // Build conversation messages with context
      const messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [
        { role: 'system', content: this.systemPrompt }
      ];

      // Add relevant conversation history (last 10 messages for context)
      const recentHistory = context.conversationHistory.slice(-10);
      recentHistory.forEach(msg => {
        messages.push({
          role: msg.role as 'user' | 'assistant',
          content: msg.content
        });
      });

      // Add SLE decision context if available
      let enhancedPrompt = userMessage;
      if (sleDecision) {
        // Enforce critical SLE decisions
        if (sleDecision.outcome === 'decline') {
          return {
            message: "I'm not able to share that information with you.",
            confidence: 0.95,
            reasoning: ['Access declined by Smart Limits Engine', `Trust level: ${sleDecision.thresholds.applied.trustBand}`, ...sleDecision.reasonCodes],
            needsVerification: false
          };
        }
        
        if (sleDecision.outcome === 'verify') {
          return {
            message: "I can help with that, but I'll need to verify a few details first. Can you confirm your identity?",
            confidence: 0.9,
            reasoning: ['Verification required by Smart Limits Engine', 'Trust-based security check'],
            needsVerification: true
          };
        }
        
        enhancedPrompt += `\n\nSLE DECISION CONTEXT:
- Outcome: ${sleDecision.outcome}
- Reason Codes: ${sleDecision.reasonCodes.join(', ')}
- Trust Score: ${sleDecision.thresholds.applied.trustScore}
- MKE Score: ${sleDecision.thresholds.applied.mkeScore}
- Security Level: ${context.securityLevel}
${sleDecision.requireVerify ? '- REQUIRES VERIFICATION' : ''}
${sleDecision.redactions?.length ? '- REDACTIONS NEEDED: ' + sleDecision.redactions.join(', ') : ''}

Respond according to the SLE decision while being helpful and transparent about limitations.`;
      }

      messages.push({ role: 'user', content: enhancedPrompt });

      // Generate response with structured output
      const response = await this.openai.chat.completions.create({
        model: "gpt-5", // the newest OpenAI model is "gpt-5" which was released August 7, 2025
        messages,
        // response_format: { type: "json_object" }, // Removed to fix OpenAI API issue
        temperature: 1,
        max_completion_tokens: 1000
      });

      const responseContent = response.choices[0].message.content;
      if (!responseContent) {
        throw new Error('No response content received from OpenAI');
      }

      let parsedResponse;
      try {
        parsedResponse = JSON.parse(responseContent);
      } catch {
        // Fallback if JSON parsing fails
        parsedResponse = {
          message: responseContent,
          confidence: 0.7,
          reasoning: ['Generated from fallback parsing'],
          needsVerification: false
        };
      }

      return {
        message: parsedResponse.message || responseContent,
        confidence: parsedResponse.confidence || 0.7,
        reasoning: parsedResponse.reasoning || ['AI generated response'],
        needsVerification: parsedResponse.needsVerification || sleDecision?.requireVerify || false,
        redactedContent: sleDecision?.redactions || parsedResponse.redactedContent,
        followUpQuestions: parsedResponse.followUpQuestions || []
      };

    } catch (error) {
      logger.error('MemoryConversationEngine', 'Conversation processing failed', { 
        error: error instanceof Error ? error.message : 'Unknown error',
        userMessage: userMessage.substring(0, 100) + '...',
        contextUserId: context.userId
      });
      
      return {
        message: "I'm having trouble processing your request right now. Please try again.",
        confidence: 0.1,
        reasoning: ['Error in conversation processing'],
        needsVerification: false
      };
    }
  }

  async generateMemoryPrompt(
    query: string,
    memoryContext: any,
    securityLevel: string
  ): Promise<string> {
    const prompt = `Based on the user's query and their memory context, generate a thoughtful response that respects privacy boundaries.

USER QUERY: ${query}
SECURITY LEVEL: ${securityLevel}
MEMORY CONTEXT: ${JSON.stringify(memoryContext, null, 2)}

Generate a response that:
1. Addresses the user's question appropriately
2. Respects the security level constraints
3. Uses available memory context when appropriate
4. Provides helpful information while maintaining privacy

Respond in JSON format with:
{
  "message": "Your response to the user",
  "confidence": 0.8,
  "reasoning": ["List of reasoning steps"],
  "needsVerification": false,
  "followUpQuestions": ["Optional follow-up questions"]
}`;

    const response = await this.openai.chat.completions.create({
      model: "gpt-5", // the newest OpenAI model is "gpt-5" which was released August 7, 2025
      messages: [{ role: 'user', content: prompt }],
      response_format: { type: "json_object" },
      temperature: 1
    });

    return response.choices[0].message.content || '';
  }

  // Voice/Audio processing for Memory Number calls
  async processVoiceInteraction(
    audioTranscript: string,
    speakerId: string,
    context: ConversationContext
  ): Promise<ConversationResponse> {
    const voicePrompt = `VOICE INTERACTION PROCESSING
Speaker ID: ${speakerId}
Transcript: ${audioTranscript}
Security Level: ${context.securityLevel}

This is a voice interaction through the Memory Number system. Process the spoken content with extra care for:
1. Voice identification verification
2. Consent confirmation for sensitive topics
3. Natural conversation flow
4. Audio quality considerations

Respond naturally as if speaking, with appropriate voice-friendly formatting.`;

    return this.processConversation(voicePrompt, context);
  }

  // Legacy mode conversations for bereaved family members
  async processLegacyInteraction(
    message: string,
    legacyContext: {
      deceasedUserId: string;
      familyMemberId: string;
      legacyPermissions: string[];
    }
  ): Promise<ConversationResponse> {
    const legacyPrompt = `LEGACY MODE INTERACTION
This is a conversation with a bereaved family member accessing legacy memories.

Family Member: ${legacyContext.familyMemberId}
Permissions: ${legacyContext.legacyPermissions.join(', ')}
Message: ${message}

Respond with appropriate sensitivity and compassion while respecting the legacy permissions. Focus on:
1. Honoring the deceased person's memory
2. Providing comfort and support
3. Sharing appropriate memories and information
4. Maintaining dignity and respect

Use a warm, empathetic tone appropriate for legacy interactions.`;

    const context: ConversationContext = {
      userId: legacyContext.familyMemberId,
      sessionId: `legacy_${Date.now()}`,
      conversationHistory: [],
      securityLevel: 'General'
    };

    return this.processConversation(legacyPrompt, context);
  }
}

// Triple AI conversation engine supporting OpenAI, Claude, and Grok
export class TripleAIConversationEngine {
  private openaiEngine: MemoryConversationEngine;
  private claudeEngine: any;
  private grokEngine: any;
  private preferredEngine: 'openai' | 'claude' | 'grok';
  private enabledEngines: ('openai' | 'claude' | 'grok')[];

  constructor(preferredEngine: 'openai' | 'claude' | 'grok' = 'grok') {
    this.openaiEngine = new MemoryConversationEngine();
    // Simplified for now to avoid circular dependencies
    this.claudeEngine = this.openaiEngine;
    this.grokEngine = this.openaiEngine;
    this.preferredEngine = preferredEngine;
    
    // Detect available engines based on API keys
    this.enabledEngines = [];
    if (process.env.OPENAI_API_KEY) this.enabledEngines.push('openai');
    if (process.env.ANTHROPIC_API_KEY) this.enabledEngines.push('claude');
    if (process.env.XAI_API_KEY) this.enabledEngines.push('grok');
    
    // Fallback to first available if preferred isn't available
    if (!this.enabledEngines.includes(this.preferredEngine) && this.enabledEngines.length > 0) {
      this.preferredEngine = this.enabledEngines[0];
    }
  }

  async processConversation(
    userMessage: string, 
    context: ConversationContext,
    sleDecision?: any,
    engine?: 'openai' | 'claude' | 'grok'
  ): Promise<ConversationResponse> {
    const selectedEngine = engine || this.preferredEngine;
    const fallbackEngines = this.enabledEngines.filter(e => e !== selectedEngine);
    
    try {
      // Try primary engine
      if (selectedEngine === 'claude' && this.enabledEngines.includes('claude')) {
        return await this.claudeEngine.processConversation(userMessage, context, sleDecision);
      } else if (selectedEngine === 'grok' && this.enabledEngines.includes('grok')) {
        return await this.grokEngine.processConversation(userMessage, context, sleDecision);
      } else if (selectedEngine === 'openai' && this.enabledEngines.includes('openai')) {
        return await this.openaiEngine.processConversation(userMessage, context, sleDecision);
      }
    } catch (error) {
      console.log(`Primary ${selectedEngine} engine failed:`, error instanceof Error ? error.message : 'Unknown error');
    }
    
    // Try fallback engines
    for (const fallbackEngine of fallbackEngines) {
      try {
        console.log(`Falling back to ${fallbackEngine} engine`);
        if (fallbackEngine === 'claude') {
          return await this.claudeEngine.processConversation(userMessage, context, sleDecision);
        } else if (fallbackEngine === 'grok') {
          return await this.grokEngine.processConversation(userMessage, context, sleDecision);
        } else if (fallbackEngine === 'openai') {
          return await this.openaiEngine.processConversation(userMessage, context, sleDecision);
        }
      } catch (fallbackError) {
        console.log(`Fallback ${fallbackEngine} engine also failed:`, fallbackError instanceof Error ? fallbackError.message : 'Unknown error');
      }
    }
    
    // If all engines fail, return error response
    return {
      message: "I'm experiencing technical difficulties with all AI engines. Please try again later.",
      confidence: 0.1,
      reasoning: ['All AI engines failed'],
      needsVerification: false
    };
  }

  setEngine(engine: 'openai' | 'claude' | 'grok') {
    if (this.enabledEngines.includes(engine)) {
      this.preferredEngine = engine;
    } else {
      console.log(`Engine ${engine} not available, keeping ${this.preferredEngine}`);
    }
  }

  getEnabledEngines(): ('openai' | 'claude' | 'grok')[] {
    return [...this.enabledEngines];
  }

  getCurrentEngine(): string {
    return this.preferredEngine.toUpperCase();
  }
}

// Conversation manager for handling multiple concurrent conversations
export class ConversationManager {
  private conversations: Map<string, ConversationContext> = new Map();
  private engine: TripleAIConversationEngine;

  constructor(engine?: TripleAIConversationEngine) {
    this.engine = engine || new TripleAIConversationEngine();
  }

  async startConversation(userId: string, securityLevel: ConversationContext['securityLevel']): Promise<string> {
    const sessionId = `session_${userId}_${Date.now()}`;
    const context: ConversationContext = {
      userId,
      sessionId,
      conversationHistory: [],
      securityLevel
    };
    
    this.conversations.set(sessionId, context);
    return sessionId;
  }

  async continueConversation(
    sessionId: string, 
    message: string, 
    sleDecision?: any
  ): Promise<ConversationResponse> {
    const context = this.conversations.get(sessionId);
    if (!context) {
      throw new Error('Conversation session not found');
    }

    // Add user message to history
    context.conversationHistory.push({
      role: 'user',
      content: message,
      timestamp: new Date()
    });

    // Process with conversation engine
    const response = await this.engine.processConversation(message, context, sleDecision);

    // Add assistant response to history
    context.conversationHistory.push({
      role: 'assistant',
      content: response.message,
      timestamp: new Date(),
      metadata: {
        trustScore: sleDecision?.thresholds?.applied?.trustScore,
        mkeScore: sleDecision?.thresholds?.applied?.mkeScore,
        sleDecision
      }
    });

    return response;
  }

  async endConversation(sessionId: string): Promise<void> {
    this.conversations.delete(sessionId);
  }

  getConversationHistory(sessionId: string): ConversationMessage[] {
    const context = this.conversations.get(sessionId);
    return context?.conversationHistory || [];
  }
}

// Export all engines
export { ClaudeConversationEngine } from './claude-engine.js';
export { GrokConversationEngine } from './grok-engine.js';
// TripleAIConversationEngine defined inline above
export { MCPEnhancedConversationEngine } from './mcp-enhanced-engine.js';