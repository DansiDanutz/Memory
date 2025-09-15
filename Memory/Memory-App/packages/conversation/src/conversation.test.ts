// Triple AI Conversation Engine Test Suite
import { describe, test, expect, beforeEach } from 'vitest';
import { TripleAIConversationEngine, ConversationManager } from './index';
import { ConversationContext } from './types';

describe('Triple AI Conversation Engine', () => {
  let engine: TripleAIConversationEngine;
  let context: ConversationContext;

  beforeEach(() => {
    engine = new TripleAIConversationEngine('grok');
    context = {
      userId: 'test-user',
      sessionId: 'test-session',
      conversationHistory: [],
      securityLevel: 'General'
    };
  });

  test('should initialize with preferred engine', () => {
    expect(engine.getCurrentEngine()).toBe('GROK');
    expect(engine.getEnabledEngines()).toContain('OpenAI');
  });

  test('should process conversation successfully', async () => {
    const response = await engine.processConversation(
      'Hello, test the Triple AI system',
      context
    );

    expect(response).toBeDefined();
    expect(response.message).toBeDefined();
    expect(response.confidence).toBeGreaterThan(0);
    expect(response.confidence).toBeLessThanOrEqual(1);
    expect(response.reasoning).toBeDefined();
    expect(Array.isArray(response.reasoning)).toBe(true);
  });

  test('should handle engine failover gracefully', async () => {
    // Test with all engines potentially failing
    const response = await engine.processConversation(
      'Test failover mechanism',
      context
    );

    expect(response).toBeDefined();
    expect(response.reasoning).toContain('Used GROK engine');
  });

  test('should switch engines correctly', () => {
    engine.setEngine('claude');
    expect(engine.getCurrentEngine()).toBe('CLAUDE');
    
    engine.setEngine('openai');
    expect(engine.getCurrentEngine()).toBe('OPENAI');
  });

  test('should detect available engines based on API keys', () => {
    const enabledEngines = engine.getEnabledEngines();
    expect(Array.isArray(enabledEngines)).toBe(true);
    // Should detect at least one engine
    expect(enabledEngines.length).toBeGreaterThan(0);
  });
});

describe('Conversation Manager', () => {
  let manager: ConversationManager;

  beforeEach(() => {
    manager = new ConversationManager();
  });

  test('should start conversation session', async () => {
    const sessionId = await manager.startConversation('test-user', 'General');
    
    expect(sessionId).toBeDefined();
    expect(typeof sessionId).toBe('string');
    expect(sessionId.length).toBeGreaterThan(0);
  });

  test('should process conversation with SLE integration', async () => {
    const sessionId = await manager.startConversation('test-user', 'General');
    
    const response = await manager.continueConversation(
      sessionId,
      'Tell me about privacy protection features'
    );

    expect(response).toBeDefined();
    expect(response.message).toBeDefined();
    expect(response.reasoning).toBeDefined();
  });

  test('should maintain conversation history', async () => {
    const sessionId = await manager.startConversation('test-user', 'General');
    
    await manager.continueConversation(sessionId, 'First message');
    await manager.continueConversation(sessionId, 'Second message');
    
    const history = manager.getConversationHistory(sessionId);
    
    expect(history.length).toBe(4); // 2 user messages + 2 assistant responses
    expect(history[0].role).toBe('user');
    expect(history[0].content).toBe('First message');
    expect(history[1].role).toBe('assistant');
    expect(history[2].role).toBe('user');
    expect(history[2].content).toBe('Second message');
  });

  test('should end conversation session', async () => {
    const sessionId = await manager.startConversation('test-user', 'General');
    
    await manager.endConversation(sessionId);
    
    const history = manager.getConversationHistory(sessionId);
    expect(history).toEqual([]);
  });

  test('should handle multiple concurrent sessions', async () => {
    const session1 = await manager.startConversation('user1', 'General');
    const session2 = await manager.startConversation('user2', 'Secret');
    
    expect(session1).not.toBe(session2);
    
    await manager.continueConversation(session1, 'Message for session 1');
    await manager.continueConversation(session2, 'Message for session 2');
    
    const history1 = manager.getConversationHistory(session1);
    const history2 = manager.getConversationHistory(session2);
    
    expect(history1[0].content).toBe('Message for session 1');
    expect(history2[0].content).toBe('Message for session 2');
  });
});