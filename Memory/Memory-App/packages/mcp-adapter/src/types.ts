// MCP Adapter Types

export interface MCPServerConfig {
  name: string;
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export interface MemoryRecord {
  id: string;
  userId: string;
  content: string;
  domain: string;
  timestamp: number;
  securityLabel: 'General' | 'Secret' | 'Ultra' | 'C2' | 'C3';
  provenance?: {
    source: string;
    confidence: number;
    timestamp: number;
  };
  tags: string[];
  metadata: Record<string, any>;
}

export interface MCPToolCall {
  tool: string;
  arguments: Record<string, any>;
  timestamp: number;
  result?: any;
  error?: string;
}

export interface UITarsAction {
  type: 'click' | 'type' | 'scroll' | 'navigate' | 'screenshot' | 'extract';
  target?: string;
  value?: string;
  coordinates?: { x: number; y: number };
  selector?: string;
}

export interface UITarsResult {
  success: boolean;
  screenshot?: string; // base64
  extractedData?: any;
  error?: string;
  timestamp: number;
}

export interface SupabaseQuery {
  table: string;
  operation: 'select' | 'insert' | 'update' | 'delete';
  data?: any;
  conditions?: Record<string, any>;
  fields?: string[];
}

export interface SupabaseResult {
  success: boolean;
  data?: any[];
  error?: string;
  rowCount?: number;
  timestamp: number;
}

export interface MCPMemoryContext {
  sessionId: string;
  userId: string;
  recentMemories: MemoryRecord[];
  activeQueries: SupabaseQuery[];
  uiActions: UITarsAction[];
  securityLevel: string;
}