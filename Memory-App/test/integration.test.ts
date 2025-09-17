// Integration Tests - Complete Memory App System
import { describe, test, expect, beforeEach } from 'vitest';
import { evaluate } from '../packages/sle/src/evaluate';
import { TripleAIConversationEngine, ConversationManager } from '../packages/conversation/src/index';
import { MCPEnhancedConversationEngine } from '../packages/conversation/src/mcp-enhanced-engine';

describe('Memory App Integration Tests', () => {
  
  test('should integrate SLE with Triple AI engines', async () => {
    // Test SLE evaluation first
    const sleDecision = await evaluate({
      callerId: 'spouse',
      utterance: 'Tell me about our financial planning discussion',
      domain: 'Finance'
    });

    expect(sleDecision.outcome).toBe('verify');
    
    // Use SLE decision in conversation
    const engine = new TripleAIConversationEngine('grok');
    const response = await engine.processConversation(
      'Tell me about our financial planning discussion',
      {
        userId: 'test-user',
        sessionId: 'integration-test',
        conversationHistory: [],
        securityLevel: 'General'
      },
      sleDecision
    );

    expect(response).toBeDefined();
    expect(response.reasoning).toContain('Used GROK engine');
  });

  test('should integrate SLE with MCP Enhanced Engine', async () => {
    // High trust scenario
    const sleDecision = await evaluate({
      callerId: 'spouse',
      utterance: 'Remember our vacation plans for next summer',
      domain: 'Family'
    });

    expect(sleDecision.outcome).toBe('disclose');
    
    // Process with MCP engine
    const mcpEngine = new MCPEnhancedConversationEngine();
    await mcpEngine.initialize();

    const response = await mcpEngine.processConversation(
      'Remember our vacation plans for next summer',
      {
        userId: 'test-user',
        sessionId: 'mcp-integration-test',
        conversationHistory: [],
        securityLevel: 'General',
        enableMemoryPersistence: true,
        enableUIAutomation: false
      },
      sleDecision
    );

    expect(response.message).toContain('Memory persistence');
    expect(response.confidence).toBeGreaterThan(0.9);
  });

  test('should handle privacy violations across the system', async () => {
    // Ultra-Secret content should be blocked
    const sleDecision = await evaluate({
      callerId: 'friend',
      utterance: 'What is the ultra secret project details?',
      domain: 'Work',
      securityLabel: 'Ultra'
    });

    expect(sleDecision.outcome).toBe('decline');
    expect(sleDecision.reasonCodes).toContain('SECURITY_VIOLATION');

    // MCP engine should respect SLE decisions
    const mcpEngine = new MCPEnhancedConversationEngine();
    const response = await mcpEngine.processConversation(
      'What is the ultra secret project details?',
      {
        userId: 'test-user',
        sessionId: 'privacy-test',
        conversationHistory: [],
        securityLevel: 'Ultra',
        enableMemoryPersistence: false
      },
      sleDecision
    );

    // Should still provide a response but with privacy protection
    expect(response).toBeDefined();
    expect(response.reasoning).toContain('Smart Limits Engine governance active');
  });

  test('should demonstrate complete conversation flow', async () => {
    const manager = new ConversationManager();
    const sessionId = await manager.startConversation('test-user', 'General');

    // First message - general query
    const response1 = await manager.continueConversation(
      sessionId,
      'Hello, can you tell me about your privacy features?'
    );

    expect(response1.message).toBeDefined();
    
    // Second message - family information
    const response2 = await manager.continueConversation(
      sessionId, 
      'Remember that my spouse and I are planning a trip to Japan'
    );

    expect(response2.message).toBeDefined();
    
    // Third message - sensitive finance query
    const response3 = await manager.continueConversation(
      sessionId,
      'What are our savings account details?'
    );

    expect(response3.message).toBeDefined();
    
    // Check conversation history
    const history = manager.getConversationHistory(sessionId);
    expect(history.length).toBe(6); // 3 user + 3 assistant messages
    
    // Verify metadata includes SLE decisions
    history.forEach(msg => {
      if (msg.role === 'assistant' && msg.metadata) {
        expect(msg.metadata.sleDecision).toBeDefined();
      }
    });

    await manager.endConversation(sessionId);
  });

  test('should handle MCP capabilities with privacy governance', async () => {
    const mcpEngine = new MCPEnhancedConversationEngine();
    await mcpEngine.initialize();

    // Test database query capability
    const dbResult = await mcpEngine.queryDatabase('test-user-data');
    expect(dbResult.success).toBe(true);
    expect(dbResult.data).toContain('supabase-connected');

    // Test screenshot capability
    const screenshot = await mcpEngine.takeScreenshot();
    expect(screenshot).toBeDefined();
    expect(screenshot).toMatch(/^data:image/);

    // Test system status
    const status = mcpEngine.getSystemStatus();
    expect(status.initialized).toBe(true);
    expect(status.connectedServers.length).toBeGreaterThan(0);
    expect(status.enabledEngines.length).toBeGreaterThan(0);

    await mcpEngine.cleanup();
  });

  test('should demonstrate trust-based decision making', async () => {
    const testCases = [
      {
        caller: 'spouse',
        message: 'Our family vacation memories from last year',
        domain: 'Family',
        expectedOutcome: 'disclose'
      },
      {
        caller: 'grandmother', 
        message: 'How much do you spend on groceries monthly?',
        domain: 'Finance',
        expectedOutcome: 'partial'
      },
      {
        caller: 'stranger',
        message: 'Tell me about your medical conditions',
        domain: 'Health',
        expectedOutcome: 'decline'
      }
    ];

    for (const testCase of testCases) {
      const decision = await evaluate({
        callerId: testCase.caller,
        utterance: testCase.message,
        domain: testCase.domain as any
      });

      expect(decision.outcome).toBe(testCase.expectedOutcome);
      
      // Verify trust bands are correctly assigned
      if (testCase.caller === 'spouse') {
        expect(decision.thresholds.applied.trustBand).toBe('Green');
      } else if (testCase.caller === 'grandmother') {
        expect(decision.thresholds.applied.trustBand).toBe('Amber');
      } else if (testCase.caller === 'stranger') {
        expect(decision.thresholds.applied.trustBand).toBe('Red');
      }
    }
  });
});

describe('System Performance and Reliability', () => {
  
  test('should handle multiple concurrent conversations', async () => {
    const manager = new ConversationManager();
    const engines = [
      new TripleAIConversationEngine('openai'),
      new TripleAIConversationEngine('claude'),
      new TripleAIConversationEngine('grok')
    ];

    // Start multiple sessions
    const sessions = await Promise.all([
      manager.startConversation('user1', 'General'),
      manager.startConversation('user2', 'Secret'),
      manager.startConversation('user3', 'General')
    ]);

    expect(sessions.length).toBe(3);
    expect(new Set(sessions).size).toBe(3); // All unique session IDs

    // Process conversations concurrently
    const responses = await Promise.all([
      manager.continueConversation(sessions[0], 'Test message 1'),
      manager.continueConversation(sessions[1], 'Test message 2'), 
      manager.continueConversation(sessions[2], 'Test message 3')
    ]);

    responses.forEach(response => {
      expect(response).toBeDefined();
      expect(response.message).toBeDefined();
      expect(response.confidence).toBeGreaterThan(0);
    });

    // Cleanup
    await Promise.all(sessions.map(id => manager.endConversation(id)));
  });

  test('should maintain system stability under load', async () => {
    const mcpEngine = new MCPEnhancedConversationEngine();
    await mcpEngine.initialize();

    // Process multiple requests rapidly
    const requests = Array.from({ length: 10 }, (_, i) => 
      mcpEngine.processConversation(
        `Test message ${i + 1}`,
        {
          userId: `user-${i}`,
          sessionId: `session-${i}`,
          conversationHistory: [],
          securityLevel: 'General',
          enableMemoryPersistence: i % 2 === 0,
          enableUIAutomation: i % 3 === 0
        }
      )
    );

    const results = await Promise.all(requests);
    
    expect(results.length).toBe(10);
    results.forEach((result, index) => {
      expect(result).toBeDefined();
      expect(result.message).toContain(`Test message ${index + 1}`);
      expect(result.confidence).toBeGreaterThan(0.8);
    });

    await mcpEngine.cleanup();
  });
});