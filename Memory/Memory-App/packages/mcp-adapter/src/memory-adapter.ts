// Memory Adapter - Knowledge graph-based persistent memory system
import { MemoryRecord, MCPMemoryContext, SupabaseQuery } from './types';
import { MCPClient } from './mcp-client';

export class MemoryAdapter {
  private mcpClient: MCPClient;
  private memoryStore: Map<string, MemoryRecord[]> = new Map();

  constructor(mcpClient: MCPClient) {
    this.mcpClient = mcpClient;
  }

  async storeMemory(
    userId: string, 
    content: string, 
    domain: string,
    securityLabel: 'General' | 'Secret' | 'Ultra' | 'C2' | 'C3' = 'General',
    tags: string[] = [],
    metadata: Record<string, any> = {}
  ): Promise<MemoryRecord> {
    const memory: MemoryRecord = {
      id: `mem_${userId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      userId,
      content,
      domain,
      timestamp: Date.now(),
      securityLabel,
      tags,
      metadata
    };

    // Store in local memory map
    const userMemories = this.memoryStore.get(userId) || [];
    userMemories.push(memory);
    this.memoryStore.set(userId, userMemories);

    // Try to persist to Supabase if available
    if (this.mcpClient.isConnected('supabase')) {
      try {
        await this.mcpClient.callTool('supabase', 'query', {
          sql: `
            INSERT INTO memories (id, user_id, content, domain, timestamp, security_label, tags, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (id) DO NOTHING
          `,
          params: [
            memory.id,
            memory.userId,
            memory.content,
            memory.domain,
            new Date(memory.timestamp).toISOString(),
            memory.securityLabel,
            JSON.stringify(memory.tags),
            JSON.stringify(memory.metadata)
          ]
        });
      } catch (error) {
        console.warn('Failed to persist memory to Supabase:', error);
      }
    }

    return memory;
  }

  async retrieveMemories(
    userId: string, 
    domain?: string,
    securityLabel?: string,
    limit: number = 50
  ): Promise<MemoryRecord[]> {
    let memories: MemoryRecord[] = [];

    // Try to get from Supabase first if available
    if (this.mcpClient.isConnected('supabase')) {
      try {
        let sql = 'SELECT * FROM memories WHERE user_id = $1';
        const params: any[] = [userId];
        let paramCount = 1;

        if (domain) {
          paramCount++;
          sql += ` AND domain = $${paramCount}`;
          params.push(domain);
        }

        if (securityLabel) {
          paramCount++;
          sql += ` AND security_label = $${paramCount}`;
          params.push(securityLabel);
        }

        sql += ' ORDER BY timestamp DESC';
        
        if (limit) {
          paramCount++;
          sql += ` LIMIT $${paramCount}`;
          params.push(limit);
        }

        const result = await this.mcpClient.callTool('supabase', 'query', {
          sql,
          params
        });

        if (result.result && result.result.length > 0) {
          memories = result.result.map((row: any) => ({
            id: row.id,
            userId: row.user_id,
            content: row.content,
            domain: row.domain,
            timestamp: new Date(row.timestamp).getTime(),
            securityLabel: row.security_label,
            tags: JSON.parse(row.tags || '[]'),
            metadata: JSON.parse(row.metadata || '{}')
          }));
        }
      } catch (error) {
        console.warn('Failed to retrieve memories from Supabase:', error);
      }
    }

    // Fallback to local memory store
    if (memories.length === 0) {
      const userMemories = this.memoryStore.get(userId) || [];
      memories = userMemories
        .filter(mem => !domain || mem.domain === domain)
        .filter(mem => !securityLabel || mem.securityLabel === securityLabel)
        .sort((a, b) => b.timestamp - a.timestamp)
        .slice(0, limit);
    }

    return memories;
  }

  async searchMemories(
    userId: string,
    query: string,
    domain?: string,
    limit: number = 20
  ): Promise<MemoryRecord[]> {
    // Try semantic search via Supabase if available
    if (this.mcpClient.isConnected('supabase')) {
      try {
        let sql = `
          SELECT *, 
                 ts_rank(to_tsvector('english', content), plainto_tsquery('english', $2)) as rank
          FROM memories 
          WHERE user_id = $1 
          AND to_tsvector('english', content) @@ plainto_tsquery('english', $2)
        `;
        const params: any[] = [userId, query];
        let paramCount = 2;

        if (domain) {
          paramCount++;
          sql += ` AND domain = $${paramCount}`;
          params.push(domain);
        }

        sql += ' ORDER BY rank DESC, timestamp DESC';
        
        if (limit) {
          paramCount++;
          sql += ` LIMIT $${paramCount}`;
          params.push(limit);
        }

        const result = await this.mcpClient.callTool('supabase', 'query', {
          sql,
          params
        });

        if (result.result && result.result.length > 0) {
          return result.result.map((row: any) => ({
            id: row.id,
            userId: row.user_id,
            content: row.content,
            domain: row.domain,
            timestamp: new Date(row.timestamp).getTime(),
            securityLabel: row.security_label,
            tags: JSON.parse(row.tags || '[]'),
            metadata: JSON.parse(row.metadata || '{}')
          }));
        }
      } catch (error) {
        console.warn('Failed to search memories in Supabase:', error);
      }
    }

    // Fallback to local text search
    const userMemories = this.memoryStore.get(userId) || [];
    const queryLower = query.toLowerCase();
    
    return userMemories
      .filter(mem => 
        mem.content.toLowerCase().includes(queryLower) ||
        mem.tags.some(tag => tag.toLowerCase().includes(queryLower))
      )
      .filter(mem => !domain || mem.domain === domain)
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, limit);
  }

  async buildMemoryContext(
    userId: string, 
    sessionId: string,
    currentDomain?: string
  ): Promise<MCPMemoryContext> {
    // Get recent relevant memories
    const recentMemories = await this.retrieveMemories(
      userId, 
      currentDomain, 
      undefined, 
      10
    );

    return {
      sessionId,
      userId,
      recentMemories,
      activeQueries: [],
      uiActions: [],
      securityLevel: 'General'
    };
  }

  async updateProvenance(
    memoryId: string,
    source: string,
    confidence: number
  ): Promise<void> {
    // Update local store
    for (const [userId, memories] of this.memoryStore.entries()) {
      const memory = memories.find(m => m.id === memoryId);
      if (memory) {
        memory.provenance = {
          source,
          confidence,
          timestamp: Date.now()
        };
        break;
      }
    }

    // Update Supabase if available
    if (this.mcpClient.isConnected('supabase')) {
      try {
        await this.mcpClient.callTool('supabase', 'query', {
          sql: `
            UPDATE memories 
            SET metadata = jsonb_set(metadata, '{provenance}', $2::jsonb)
            WHERE id = $1
          `,
          params: [
            memoryId,
            JSON.stringify({
              source,
              confidence,
              timestamp: Date.now()
            })
          ]
        });
      } catch (error) {
        console.warn('Failed to update provenance in Supabase:', error);
      }
    }
  }

  // Initialize memory tables in Supabase
  async initializeSchema(): Promise<void> {
    if (!this.mcpClient.isConnected('supabase')) {
      console.log('ℹ️  Supabase not connected, using local memory store only');
      return;
    }

    try {
      await this.mcpClient.callTool('supabase', 'query', {
        sql: `
          CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            domain TEXT NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            security_label TEXT NOT NULL DEFAULT 'General',
            tags JSONB DEFAULT '[]',
            metadata JSONB DEFAULT '{}'
          );
          
          CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
          CREATE INDEX IF NOT EXISTS idx_memories_domain ON memories(domain);
          CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);
          CREATE INDEX IF NOT EXISTS idx_memories_content_search ON memories USING gin(to_tsvector('english', content));
        `
      });
      
      console.log('✅ Memory schema initialized in Supabase');
    } catch (error) {
      console.warn('Failed to initialize memory schema:', error);
    }
  }

  getLocalMemoryCount(userId: string): number {
    return this.memoryStore.get(userId)?.length || 0;
  }

  clearLocalMemories(userId: string): void {
    this.memoryStore.delete(userId);
  }
}