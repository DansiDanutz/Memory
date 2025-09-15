// Claude Conversation Engine for Memory App
import Anthropic from '@anthropic-ai/sdk';
import { ConversationContext, ConversationMessage, ConversationResponse } from './index.js';

/*
The newest Anthropic model is "claude-sonnet-4-20250514", not "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022" nor "claude-3-sonnet-20240229". 
Always prefer using "claude-sonnet-4-20250514" as it is the latest model unless explicitly requested otherwise.
*/

// <important_do_not_delete>
const DEFAULT_MODEL_STR = "claude-sonnet-4-20250514";
// </important_do_not_delete>

export class ClaudeConversationEngine {
  private anthropic: Anthropic;
  private systemPrompt: string;

  constructor(apiKey?: string) {
    this.anthropic = new Anthropic({
      apiKey: apiKey || process.env.ANTHROPIC_API_KEY,
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

Always explain your reasoning and respect the user's privacy boundaries. Respond in JSON format with: message, confidence, reasoning, needsVerification, followUpQuestions.`;
  }

  async processConversation(
    userMessage: string, 
    context: ConversationContext,
    sleDecision?: any
  ): Promise<ConversationResponse> {
    try {
      // Build conversation messages with context
      const messages: Anthropic.Messages.MessageParam[] = [];

      // Add relevant conversation history (last 10 messages for context)
      const recentHistory = context.conversationHistory.slice(-10);
      recentHistory.forEach(msg => {
        if (msg.role !== 'system') {
          messages.push({
            role: msg.role === 'assistant' ? 'assistant' : 'user',
            content: msg.content
          });
        }
      });

      // Add SLE decision context if available
      let enhancedPrompt = userMessage;
      if (sleDecision) {
        enhancedPrompt += `\n\nSLE DECISION CONTEXT:
- Outcome: ${sleDecision.outcome}
- Reason Codes: ${sleDecision.reasonCodes.join(', ')}
- Trust Score: ${sleDecision.thresholds.applied.trustScore}
- MKE Score: ${sleDecision.thresholds.applied.mkeScore}
- Security Level: ${context.securityLevel}
${sleDecision.requireVerify ? '- REQUIRES VERIFICATION' : ''}
${sleDecision.redactions?.length ? '- REDACTIONS NEEDED: ' + sleDecision.redactions.join(', ') : ''}

Respond according to the SLE decision while being helpful and transparent about limitations. Return response as JSON with: message, confidence, reasoning, needsVerification, followUpQuestions.`;
      } else {
        enhancedPrompt += '\n\nReturn response as JSON with: message, confidence, reasoning, needsVerification, followUpQuestions.';
      }

      messages.push({ role: 'user', content: enhancedPrompt });

      // Generate response with Claude
      const response = await this.anthropic.messages.create({
        model: DEFAULT_MODEL_STR, // "claude-sonnet-4-20250514"
        system: this.systemPrompt,
        messages,
        max_tokens: 1000,
        temperature: 0.7
      });

      const responseContent = response.content[0]?.type === 'text' ? response.content[0].text : '';
      if (!responseContent) {
        throw new Error('No response content received from Claude');
      }

      let parsedResponse;
      try {
        parsedResponse = JSON.parse(responseContent);
      } catch {
        // Fallback if JSON parsing fails
        parsedResponse = {
          message: responseContent,
          confidence: 0.8,
          reasoning: ['Generated from Claude with fallback parsing'],
          needsVerification: false
        };
      }

      return {
        message: parsedResponse.message || responseContent,
        confidence: parsedResponse.confidence || 0.8,
        reasoning: parsedResponse.reasoning || ['Claude generated response'],
        needsVerification: parsedResponse.needsVerification || sleDecision?.requireVerify || false,
        redactedContent: sleDecision?.redactions || parsedResponse.redactedContent,
        followUpQuestions: parsedResponse.followUpQuestions || []
      };

    } catch (error) {
      console.error('Claude conversation processing error:', error);
      return {
        message: "I'm having trouble processing your request right now. Please try again.",
        confidence: 0.1,
        reasoning: ['Error in Claude conversation processing'],
        needsVerification: false
      };
    }
  }

  async generateMemoryPrompt(
    query: string,
    memoryContext: any,
    securityLevel: string
  ): Promise<string> {
    const response = await this.anthropic.messages.create({
      model: DEFAULT_MODEL_STR, // "claude-sonnet-4-20250514"
      system: `Based on the user's query and their memory context, generate a thoughtful response that respects privacy boundaries.

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
}`,
      messages: [{
        role: 'user',
        content: `USER QUERY: ${query}
SECURITY LEVEL: ${securityLevel}
MEMORY CONTEXT: ${JSON.stringify(memoryContext, null, 2)}`
      }],
      max_tokens: 800,
      temperature: 0.6
    });

    return response.content[0]?.type === 'text' ? response.content[0].text : '';
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