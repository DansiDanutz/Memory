// Triple AI Engine - Unified OpenAI, Claude, and Grok interface
import OpenAI from "openai";

// Inline MemoryConversationEngine functionality to avoid circular imports
class MemoryConversationEngine {
  private openai: OpenAI;

  constructor(apiKey?: string) {
    this.openai = new OpenAI({ 
      apiKey: apiKey || process.env.OPENAI_API_KEY 
    });
  }

  async processConversation(
    userMessage: string,
    context: ConversationContext,
    sleDecision?: any
  ): Promise<ConversationResponse> {
    try {
      const response = await this.openai.chat.completions.create({
        model: "gpt-4-turbo",
        messages: [
          { role: "system", content: "You are Memory, a privacy-first AI assistant." },
          { role: "user", content: userMessage }
        ],
        max_tokens: 1000,
        temperature: 0.7
      });

      return {
        message: response.choices[0]?.message?.content || "I apologize, but I couldn't process your request.",
        confidence: 0.85,
        reasoning: ["OpenAI GPT-4 response"],
        needsVerification: false
      };
    } catch (error) {
      throw new Error(`OpenAI API error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}
import { ClaudeConversationEngine } from './claude-engine.js'; 
import { GrokConversationEngine } from './grok-engine.js';
import { ConversationContext, ConversationResponse } from './types.js';

export type AIEngine = 'openai' | 'claude' | 'grok';

export class TripleAIConversationEngine {
  private memoryEngine: MemoryConversationEngine;
  private claudeEngine: ClaudeConversationEngine;
  private grokEngine: GrokConversationEngine;
  private currentEngine: AIEngine;
  
  constructor(preferredEngine: AIEngine = 'grok') {
    this.memoryEngine = new MemoryConversationEngine();
    this.claudeEngine = new ClaudeConversationEngine();
    this.grokEngine = new GrokConversationEngine();
    this.currentEngine = preferredEngine;
  }

  async processConversation(
    userMessage: string,
    context: ConversationContext,
    sleDecision?: any
  ): Promise<ConversationResponse> {
    const engines: { [K in AIEngine]: () => Promise<ConversationResponse> } = {
      openai: () => this.memoryEngine.processConversation(userMessage, context, sleDecision),
      claude: () => this.claudeEngine.processConversation(userMessage, context, sleDecision),
      grok: () => this.grokEngine.processConversation(userMessage, context, sleDecision)
    };

    // Try engines in order with fallback
    const engineOrder: AIEngine[] = this.getEngineOrder();
    
    for (const engine of engineOrder) {
      try {
        const response = await engines[engine]();
        response.reasoning = [`Used ${engine.toUpperCase()} engine`, ...(response.reasoning || [])];
        return response;
      } catch (error) {
        console.warn(`${engine.toUpperCase()} engine failed:`, error instanceof Error ? error.message : error);
        continue;
      }
    }

    // All engines failed
    throw new Error('All AI engines failed');
  }

  private getEngineOrder(): AIEngine[] {
    const engines: AIEngine[] = ['openai', 'claude', 'grok'];
    // Move current engine to front
    const filtered = engines.filter(e => e !== this.currentEngine);
    return [this.currentEngine, ...filtered];
  }

  getEnabledEngines(): string[] {
    const engines: string[] = [];
    
    // Check which engines have API keys
    if (process.env.OPENAI_API_KEY) engines.push('OpenAI');
    if (process.env.ANTHROPIC_API_KEY) engines.push('Claude'); 
    if (process.env.XAI_API_KEY) engines.push('Grok');
    
    return engines;
  }

  getCurrentEngine(): string {
    return this.currentEngine.toUpperCase();
  }

  setEngine(engine: AIEngine): void {
    this.currentEngine = engine;
  }
}