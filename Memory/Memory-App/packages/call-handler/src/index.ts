// AI Call Handling and Conversation Management for Memory App
import { v4 as uuidv4 } from 'uuid';
import { evaluate, SLEContext } from '@memory-app/sle';
import { VoiceProcessor, VoiceTranscription } from '@memory-app/voice-processor';
import { MemoryStorageSystem, RelationshipProfile, ConversationEntry } from '@memory-app/memory-storage';
import { logger } from '@memory-app/conversation/src/production-logger';

export interface CallSession {
  id: string;
  callerId: string;
  callerName?: string;
  platform: 'whatsapp' | 'telegram';
  startTime: Date;
  endTime?: Date;
  status: 'ringing' | 'active' | 'ended' | 'failed';
  transcript: CallTranscriptEntry[];
  summary?: string;
  outcome: 'completed' | 'hung_up' | 'error';
  aiControlled: boolean;
}

export interface CallTranscriptEntry {
  speaker: 'caller' | 'ai';
  timestamp: Date;
  content: string;
  audioBuffer?: Buffer;
  confidence: number;
}

export interface CallHandlerConfig {
  maxCallDuration: number; // seconds
  autoAnswer: boolean;
  greetingMessage: string;
  endingMessage: string;
  emergencyContacts: string[];
  allowedCallers: string[];
  voiceSettings: {
    voice: 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer';
    speed: number;
    language: string;
  };
}

export class AICallHandler {
  private voiceProcessor: VoiceProcessor;
  private memoryStorage: MemoryStorageSystem;
  private config: CallHandlerConfig;
  private activeCalls: Map<string, CallSession> = new Map();
  private isEnabled = false;

  constructor(config: Partial<CallHandlerConfig> = {}) {
    this.config = {
      maxCallDuration: 300, // 5 minutes default
      autoAnswer: true,
      greetingMessage: "Hello! This is your AI assistant. I'm handling this call for you. How can I help?",
      endingMessage: "Thank you for calling. I'll make sure to share this conversation. Have a great day!",
      emergencyContacts: [],
      allowedCallers: [],
      voiceSettings: {
        voice: 'nova',
        speed: 1.0,
        language: 'en'
      },
      ...config
    };

    this.voiceProcessor = new VoiceProcessor({
      ttsVoice: this.config.voiceSettings.voice,
      voiceLanguage: this.config.voiceSettings.language
    });

    this.memoryStorage = new MemoryStorageSystem();

    logger.info('CallHandler', 'AI call handler initialized', {
      autoAnswer: this.config.autoAnswer,
      maxDuration: this.config.maxCallDuration,
      voiceSettings: this.config.voiceSettings
    });
  }

  // PRIORITY 2: Handle incoming calls with AI conversation
  async handleIncomingCall(
    callerId: string, 
    callerName: string | undefined,
    platform: 'whatsapp' | 'telegram'
  ): Promise<CallSession> {
    try {
      logger.info('CallHandler', 'Incoming call detected', {
        callerId,
        callerName,
        platform
      });

      // Check if caller is allowed for AI handling
      const profile = this.memoryStorage.getRelationshipProfile(callerId);
      const shouldHandle = await this.shouldHandleCall(callerId, profile);

      if (!shouldHandle) {
        logger.info('CallHandler', 'Call handling skipped - not authorized', {
          callerId,
          profile: profile?.relationshipType || 'unknown'
        });
        
        return {
          id: uuidv4(),
          callerId,
          callerName,
          platform,
          startTime: new Date(),
          status: 'failed',
          transcript: [],
          outcome: 'error',
          aiControlled: false
        };
      }

      // Create call session
      const session: CallSession = {
        id: uuidv4(),
        callerId,
        callerName,
        platform,
        startTime: new Date(),
        status: 'ringing',
        transcript: [],
        outcome: 'completed',
        aiControlled: true
      };

      this.activeCalls.set(session.id, session);

      // Answer the call and start AI conversation
      await this.answerCall(session);
      
      return session;

    } catch (error) {
      logger.error('CallHandler', 'Failed to handle incoming call', {
        error: error instanceof Error ? error.message : 'Unknown error',
        callerId,
        platform
      });

      throw error;
    }
  }

  private async shouldHandleCall(callerId: string, profile: RelationshipProfile | null): Promise<boolean> {
    // Emergency contacts always get through
    if (this.config.emergencyContacts.includes(callerId)) {
      return true;
    }

    // Check allowed callers list
    if (this.config.allowedCallers.length > 0 && !this.config.allowedCallers.includes(callerId)) {
      return false;
    }

    // Check relationship profile permissions
    if (profile) {
      return profile.preferences.allowCallHandling && 
             (profile.trustLevel === 'Green' || profile.relationshipType === 'family' || profile.relationshipType === 'friend');
    }

    // Default: don't handle unknown callers
    return false;
  }

  private async answerCall(session: CallSession): Promise<void> {
    try {
      session.status = 'active';
      
      logger.info('CallHandler', 'Call answered by AI', {
        sessionId: session.id,
        callerId: session.callerId
      });

      // Generate and send greeting
      const greeting = await this.generatePersonalizedGreeting(session);
      await this.speakToCall(session, greeting);

      // Start conversation loop
      await this.runConversationLoop(session);

      // End call gracefully
      await this.endCall(session);

    } catch (error) {
      logger.error('CallHandler', 'Error during AI call handling', {
        error: error instanceof Error ? error.message : 'Unknown error',
        sessionId: session.id
      });

      session.status = 'failed';
      session.outcome = 'error';
    }
  }

  private async generatePersonalizedGreeting(session: CallSession): Promise<string> {
    const profile = this.memoryStorage.getRelationshipProfile(session.callerId);
    
    if (profile) {
      const relationshipContext = profile.relationshipType === 'family' 
        ? `Hi ${profile.name}!` 
        : `Hello ${profile.name}`;

      return `${relationshipContext} This is your AI assistant handling calls today. I'm here to help and will make sure to pass along our conversation. What's going on?`;
    }

    return this.config.greetingMessage;
  }

  private async runConversationLoop(session: CallSession): Promise<void> {
    const maxDuration = this.config.maxCallDuration * 1000; // Convert to milliseconds
    const startTime = Date.now();

    try {
      while (session.status === 'active' && (Date.now() - startTime) < maxDuration) {
        // Listen for caller input
        const callerInput = await this.listenForCallerInput(session);
        
        if (!callerInput || callerInput.length === 0) {
          // Handle silence or call ended
          break;
        }

        // Add caller input to transcript
        session.transcript.push({
          speaker: 'caller',
          timestamp: new Date(),
          content: callerInput,
          confidence: 0.9
        });

        // Generate AI response based on conversation context
        const aiResponse = await this.generateAIResponse(session, callerInput);

        // Add AI response to transcript
        session.transcript.push({
          speaker: 'ai',
          timestamp: new Date(),
          content: aiResponse,
          confidence: 1.0
        });

        // Speak AI response
        await this.speakToCall(session, aiResponse);

        // Check if caller wants to end call
        if (this.isCallEndingRequest(callerInput)) {
          break;
        }
      }

    } catch (error) {
      logger.error('CallHandler', 'Error in conversation loop', {
        error: error instanceof Error ? error.message : 'Unknown error',
        sessionId: session.id
      });

      // Try to end gracefully
      await this.speakToCall(session, "I'm having some technical difficulties. I'll make sure to save our conversation so far.");
    }
  }

  private async listenForCallerInput(session: CallSession): Promise<string> {
    try {
      // In a real implementation, this would:
      // 1. Listen to audio stream from WhatsApp/Telegram call
      // 2. Detect speech and silence
      // 3. Transcribe audio to text
      
      // For demonstration, we'll simulate this
      // In production, integrate with platform-specific call APIs
      
      logger.debug('CallHandler', 'Listening for caller input', {
        sessionId: session.id
      });

      // Simulate listening period (in real implementation, this would be actual audio processing)
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Return simulated caller input (in production, this would be real transcription)
      return "This is simulated caller input - in production this would be real speech-to-text";

    } catch (error) {
      logger.error('CallHandler', 'Failed to listen for caller input', {
        error: error instanceof Error ? error.message : 'Unknown error',
        sessionId: session.id
      });

      return "";
    }
  }

  private async generateAIResponse(session: CallSession, callerInput: string): Promise<string> {
    try {
      // Get relationship context
      const profile = this.memoryStorage.getRelationshipProfile(session.callerId);
      
      // Search relevant memories
      const memorySearch = await this.memoryStorage.searchMemory({
        query: callerInput,
        searchType: 'semantic',
        contactFilter: [session.callerId]
      }, session.callerId);

      // Check SLE for response permissions
      const sleContext: SLEContext = {
        callerId: session.callerId,
        utterance: callerInput,
        domain: profile?.relationshipType === 'family' ? 'Family' : 'Work'
      };

      const sleDecision = await evaluate(sleContext);

      // Generate contextual response
      let response = "I understand what you're saying. ";

      if (sleDecision.outcome === 'disclose' && memorySearch.entries.length > 0) {
        response += `I remember we discussed similar things before. ${memorySearch.summary}`;
      } else if (sleDecision.outcome === 'probe') {
        response += "Could you tell me more about that? I want to make sure I understand correctly.";
      } else {
        response += "I'm here to listen and help however I can.";
      }

      // Add relationship-specific context
      if (profile?.relationshipType === 'family') {
        response += " I'll make sure to let them know we talked about this.";
      }

      return response;

    } catch (error) {
      logger.error('CallHandler', 'Failed to generate AI response', {
        error: error instanceof Error ? error.message : 'Unknown error',
        sessionId: session.id
      });

      return "I'm listening. Please continue.";
    }
  }

  private async speakToCall(session: CallSession, text: string): Promise<void> {
    try {
      logger.debug('CallHandler', 'AI speaking to call', {
        sessionId: session.id,
        textLength: text.length
      });

      // Generate speech audio
      const audioResult = await this.voiceProcessor.synthesizeVoice(text);

      // In production, this would:
      // 1. Send audio buffer to WhatsApp/Telegram call stream
      // 2. Play audio through call connection
      
      // For now, we log that speech would be played
      logger.info('CallHandler', 'AI speech generated and would be played', {
        sessionId: session.id,
        audioSize: audioResult.audioBuffer.length,
        duration: audioResult.duration
      });

    } catch (error) {
      logger.error('CallHandler', 'Failed to speak to call', {
        error: error instanceof Error ? error.message : 'Unknown error',
        sessionId: session.id,
        text: text.substring(0, 50)
      });
    }
  }

  private isCallEndingRequest(input: string): boolean {
    const endingPhrases = [
      'goodbye', 'bye', 'talk later', 'gotta go', 'have to run',
      'hang up', 'end call', 'that\'s all', 'thanks bye'
    ];

    const lowerInput = input.toLowerCase();
    return endingPhrases.some(phrase => lowerInput.includes(phrase));
  }

  private async endCall(session: CallSession): Promise<void> {
    try {
      // Send ending message
      await this.speakToCall(session, this.config.endingMessage);

      // Update session status
      session.status = 'ended';
      session.endTime = new Date();

      // Generate call summary
      session.summary = await this.generateCallSummary(session);

      // Store call transcript in memory system
      await this.storeCallTranscript(session);

      logger.info('CallHandler', 'Call ended successfully', {
        sessionId: session.id,
        duration: session.endTime.getTime() - session.startTime.getTime(),
        transcriptEntries: session.transcript.length
      });

      // Remove from active calls
      this.activeCalls.delete(session.id);

    } catch (error) {
      logger.error('CallHandler', 'Error ending call', {
        error: error instanceof Error ? error.message : 'Unknown error',
        sessionId: session.id
      });

      session.status = 'failed';
      session.outcome = 'error';
    }
  }

  private async generateCallSummary(session: CallSession): Promise<string> {
    if (session.transcript.length === 0) {
      return "Call completed with no conversation recorded.";
    }

    const callerMessages = session.transcript
      .filter(entry => entry.speaker === 'caller')
      .map(entry => entry.content)
      .join(' ');

    const topics = this.extractTopicsFromText(callerMessages);
    const duration = session.endTime 
      ? Math.round((session.endTime.getTime() - session.startTime.getTime()) / 1000)
      : 0;

    return `Call lasted ${duration} seconds. Main topics discussed: ${topics.slice(0, 3).join(', ')}. Full transcript available with ${session.transcript.length} exchanges.`;
  }

  private extractTopicsFromText(text: string): string[] {
    // Simple keyword extraction - in production, use advanced NLP
    const words = text.toLowerCase()
      .replace(/[^\w\s]/g, '')
      .split(/\s+/)
      .filter(word => word.length > 4);

    const wordCounts = new Map<string, number>();
    words.forEach(word => {
      wordCounts.set(word, (wordCounts.get(word) || 0) + 1);
    });

    return Array.from(wordCounts.entries())
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([word]) => word);
  }

  private async storeCallTranscript(session: CallSession): Promise<void> {
    try {
      const fullTranscript = session.transcript
        .map(entry => `[${entry.speaker.toUpperCase()}]: ${entry.content}`)
        .join('\n');

      const conversationEntry: Partial<ConversationEntry> = {
        content: fullTranscript,
        summary: session.summary,
        participants: [session.callerId],
        platform: session.platform,
        messageType: 'call_transcript',
        metadata: {
          duration: session.endTime 
            ? Math.round((session.endTime.getTime() - session.startTime.getTime()) / 1000)
            : 0,
          callType: 'incoming'
        },
        privacyLevel: 'private',
        approved: false, // Requires user review
        tags: ['call_transcript', 'ai_handled', 'pending_approval']
      };

      await this.memoryStorage.storeConversation(conversationEntry);

      logger.info('CallHandler', 'Call transcript stored in memory', {
        sessionId: session.id,
        transcriptLength: fullTranscript.length,
        participants: conversationEntry.participants
      });

    } catch (error) {
      logger.error('CallHandler', 'Failed to store call transcript', {
        error: error instanceof Error ? error.message : 'Unknown error',
        sessionId: session.id
      });
    }
  }

  // Get call session details
  getCallSession(sessionId: string): CallSession | null {
    return this.activeCalls.get(sessionId) || null;
  }

  // Enable/disable call handling
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
    logger.info('CallHandler', `Call handling ${enabled ? 'enabled' : 'disabled'}`);
  }

  // Get handler status
  getStatus(): {
    enabled: boolean;
    activeCalls: number;
    totalCallsHandled: number;
    config: CallHandlerConfig;
  } {
    return {
      enabled: this.isEnabled,
      activeCalls: this.activeCalls.size,
      totalCallsHandled: 0, // Would track this in production
      config: this.config
    };
  }
}

// Export convenience functions
export async function handleIncomingCall(
  callerId: string,
  callerName: string,
  platform: 'whatsapp' | 'telegram'
): Promise<CallSession> {
  const handler = new AICallHandler();
  return await handler.handleIncomingCall(callerId, callerName, platform);
}

export function createCallHandler(config: Partial<CallHandlerConfig> = {}): AICallHandler {
  return new AICallHandler(config);
}