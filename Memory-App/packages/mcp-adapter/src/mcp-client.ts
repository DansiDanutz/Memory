// MCP Client - Core Model Context Protocol client implementation
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { MCPServerConfig, MCPToolCall, MCPMemoryContext } from './types';

export class MCPClient {
  private clients: Map<string, Client> = new Map();
  private transports: Map<string, StdioClientTransport> = new Map();
  
  constructor() {}

  async connectToServer(config: MCPServerConfig): Promise<void> {
    try {
      // Create transport for the MCP server
      const transport = new StdioClientTransport({
        command: config.command,
        args: config.args,
        env: {
          ...(process.env as Record<string, string>),
          ...(config.env || {})
        }
      });

      // Create client and connect
      const client = new Client({
        name: `memory-app-${config.name}`,
        version: '1.0.0'
      });

      await client.connect(transport);
      
      this.clients.set(config.name, client);
      this.transports.set(config.name, transport);
      
      console.log(`✅ Connected to MCP server: ${config.name}`);
    } catch (error) {
      console.error(`❌ Failed to connect to MCP server ${config.name}:`, error);
      throw error;
    }
  }

  async disconnect(serverName: string): Promise<void> {
    const client = this.clients.get(serverName);
    const transport = this.transports.get(serverName);
    
    if (client) {
      await client.close();
      this.clients.delete(serverName);
    }
    
    if (transport) {
      await transport.close();
      this.transports.delete(serverName);
    }
    
    console.log(`🔌 Disconnected from MCP server: ${serverName}`);
  }

  async disconnectAll(): Promise<void> {
    const serverNames = Array.from(this.clients.keys());
    await Promise.all(serverNames.map(name => this.disconnect(name)));
  }

  async callTool(
    serverName: string, 
    toolName: string, 
    args: Record<string, any>
  ): Promise<MCPToolCall> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`No connection to MCP server: ${serverName}`);
    }

    const toolCall: MCPToolCall = {
      tool: `${serverName}:${toolName}`,
      arguments: args,
      timestamp: Date.now()
    };

    try {
      const result = await client.callTool({
        name: toolName,
        arguments: args
      });
      
      toolCall.result = result;
      return toolCall;
    } catch (error) {
      toolCall.error = error instanceof Error ? error.message : 'Unknown error';
      throw error;
    }
  }

  async listTools(serverName: string): Promise<any[]> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`No connection to MCP server: ${serverName}`);
    }

    const response = await client.listTools();
    return response.tools || [];
  }

  async getResource(
    serverName: string, 
    resourceUri: string
  ): Promise<any> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`No connection to MCP server: ${serverName}`);
    }

    const response = await client.readResource({ uri: resourceUri });
    return response;
  }

  async listResources(serverName: string): Promise<any[]> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`No connection to MCP server: ${serverName}`);
    }

    const response = await client.listResources();
    return response.resources || [];
  }

  getConnectedServers(): string[] {
    return Array.from(this.clients.keys());
  }

  isConnected(serverName: string): boolean {
    return this.clients.has(serverName);
  }

  // Initialize standard MCP servers for Memory App
  async initializeStandardServers(): Promise<void> {
    const servers: MCPServerConfig[] = [
      {
        name: 'supabase',
        command: 'npx',
        args: [
          '-y',
          '@supabase/mcp-server-supabase',
          '--read-only' // Safety first!
        ],
        env: {
          DATABASE_URL: process.env.DATABASE_URL || ''
        }
      }
    ];

    for (const server of servers) {
      try {
        await this.connectToServer(server);
      } catch (error) {
        console.warn(`⚠️  Could not connect to ${server.name} server:`, error instanceof Error ? error.message : 'Unknown error');
      }
    }
  }

  // Memory-specific MCP operations
  async queryMemoryContext(context: MCPMemoryContext): Promise<any> {
    const tools = [];
    
    // Try to get memory-related resources from connected servers
    for (const serverName of this.getConnectedServers()) {
      try {
        const resources = await this.listResources(serverName);
        const memoryResources = resources.filter(r => 
          r.name?.includes('memory') || 
          r.name?.includes('context') ||
          r.uri?.includes('memory')
        );
        
        tools.push({
          server: serverName,
          resources: memoryResources
        });
      } catch (error) {
        console.warn(`Could not query ${serverName}:`, error);
      }
    }
    
    return {
      availableTools: tools,
      context: context,
      timestamp: Date.now()
    };
  }
}