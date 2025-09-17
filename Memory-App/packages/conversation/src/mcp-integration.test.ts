// MCP Integration Test Suite
import { describe, test, expect, beforeEach } from 'vitest';
import { MCPEnhancedConversationEngine } from './mcp-enhanced-engine';
import { MCPConversationContext } from './mcp-enhanced-engine';

describe('MCP Enhanced Conversation Engine', () => {
  let mcpEngine: MCPEnhancedConversationEngine;
  let context: MCPConversationContext;

  beforeEach(() => {
    mcpEngine = new MCPEnhancedConversationEngine();
    context = {
      userId: 'test-user',
      sessionId: 'mcp-test-session',
      conversationHistory: [],
      securityLevel: 'General',
      enableMemoryPersistence: true,
      enableUIAutomation: true,
      memoryDomainFilter: ['Personal'],
      uiCapabilities: ['screenshot', 'navigate']
    };
  });

  test('should initialize MCP system successfully', async () => {
    await mcpEngine.initialize();
    
    const status = mcpEngine.getSystemStatus();
    expect(status.initialized).toBe(true);
    expect(status.connectedServers).toContain('supabase');
    expect(status.connectedServers).toContain('ui-tars');
    expect(status.enabledEngines).toContain('OpenAI');
    expect(status.enabledEngines).toContain('Claude');
    expect(status.enabledEngines).toContain('Grok');
    expect(status.uiTarsReady).toBe(true);
  });

  test('should process conversation with memory persistence', async () => {
    const response = await mcpEngine.processConversation(
      'Remember that I like pizza for dinner',
      context
    );

    expect(response).toBeDefined();
    expect(response.message).toContain('Memory persistence');
    expect(response.reasoning).toContain('Memory persistence active');
    expect(response.confidence).toBeGreaterThan(0.8);
  });

  test('should handle UI automation requests', async () => {
    const response = await mcpEngine.processConversation(
      'Take a screenshot of the current page',
      {
        ...context,
        enableUIAutomation: true
      }
    );

    expect(response).toBeDefined();
    expect(response.message).toContain('UI-TARS');
    expect(response.reasoning).toContain('Browser automation available');
  });

  test('should simulate database queries', async () => {
    const result = await mcpEngine.queryDatabase('test-user');
    
    expect(result.success).toBe(true);
    expect(result.message).toContain('Database query simulated');
    expect(result.data).toBeDefined();
    expect(result.data).toContain('supabase-connected');
  });

  test('should provide screenshot capability', async () => {
    const screenshot = await mcpEngine.takeScreenshot();
    
    expect(screenshot).toBeDefined();
    expect(typeof screenshot).toBe('string');
    expect(screenshot).toMatch(/^data:image\/png;base64,/);
  });

  test('should handle memory-disabled context gracefully', async () => {
    const contextNoMemory = {
      ...context,
      enableMemoryPersistence: false
    };

    const response = await mcpEngine.processConversation(
      'Test without memory persistence',
      contextNoMemory
    );

    expect(response).toBeDefined();
    expect(response.message).not.toContain('Memory persistence active');
  });

  test('should handle UI-disabled context gracefully', async () => {
    const contextNoUI = {
      ...context,
      enableUIAutomation: false
    };

    const response = await mcpEngine.processConversation(
      'Test without UI automation',
      contextNoUI
    );

    expect(response).toBeDefined();
    expect(response.message).not.toContain('Browser automation available');
  });

  test('should maintain high confidence in responses', async () => {
    const response = await mcpEngine.processConversation(
      'Test MCP system capabilities',
      context
    );

    expect(response.confidence).toBeGreaterThanOrEqual(0.9);
    expect(response.reasoning.length).toBeGreaterThan(3);
    expect(response.needsVerification).toBe(false);
  });

  test('should cleanup resources properly', async () => {
    await mcpEngine.initialize();
    
    let status = mcpEngine.getSystemStatus();
    expect(status.initialized).toBe(true);

    await mcpEngine.cleanup();
    
    // After cleanup, system should be properly reset
    status = mcpEngine.getSystemStatus();
    expect(status.initialized).toBe(false);
  });

  test('should handle complex multi-capability requests', async () => {
    const response = await mcpEngine.processConversation(
      'Remember my preferences and take a screenshot of the dashboard',
      context
    );

    expect(response).toBeDefined();
    expect(response.message).toContain('Memory persistence');
    expect(response.message).toContain('UI-TARS');
    expect(response.reasoning).toContain('Memory persistence active');
    expect(response.reasoning).toContain('Browser automation available');
    expect(response.confidence).toBeGreaterThan(0.9);
  });
});

describe('MCP System Status and Health', () => {
  let mcpEngine: MCPEnhancedConversationEngine;

  beforeEach(() => {
    mcpEngine = new MCPEnhancedConversationEngine();
  });

  test('should report system status before initialization', () => {
    const status = mcpEngine.getSystemStatus();
    
    expect(status.initialized).toBe(false);
    expect(status.connectedServers).toBeDefined();
    expect(status.enabledEngines).toBeDefined();
    expect(status.currentEngine).toBeDefined();
    expect(status.uiTarsReady).toBeDefined();
  });

  test('should report full system status after initialization', async () => {
    await mcpEngine.initialize();
    const status = mcpEngine.getSystemStatus();
    
    expect(status.initialized).toBe(true);
    expect(status.connectedServers.length).toBeGreaterThan(0);
    expect(status.enabledEngines.length).toBeGreaterThan(0);
    expect(status.currentEngine).toBe('GROK');
    expect(status.uiTarsReady).toBe(true);
  });
});