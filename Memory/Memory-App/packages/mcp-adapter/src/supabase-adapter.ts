// Supabase Adapter - Database operations via MCP protocol
import { MCPClient } from './mcp-client';
import { SupabaseQuery, SupabaseResult } from './types';

export class SupabaseAdapter {
  private mcpClient: MCPClient;

  constructor(mcpClient: MCPClient) {
    this.mcpClient = mcpClient;
  }

  async executeQuery(query: SupabaseQuery): Promise<SupabaseResult> {
    if (!this.mcpClient.isConnected('supabase')) {
      return {
        success: false,
        error: 'Supabase MCP server not connected',
        timestamp: Date.now()
      };
    }

    try {
      let sql = '';
      let params: any[] = [];

      switch (query.operation) {
        case 'select':
          sql = this.buildSelectQuery(query);
          break;
        case 'insert':
          sql = this.buildInsertQuery(query);
          params = Object.values(query.data || {});
          break;
        case 'update':
          const updateResult = this.buildUpdateQuery(query);
          sql = updateResult.sql;
          params = updateResult.params;
          break;
        case 'delete':
          const deleteResult = this.buildDeleteQuery(query);
          sql = deleteResult.sql;
          params = deleteResult.params;
          break;
      }

      const toolCall = await this.mcpClient.callTool('supabase', 'query', {
        sql,
        params: params.length > 0 ? params : undefined
      });

      return {
        success: true,
        data: toolCall.result,
        rowCount: Array.isArray(toolCall.result) ? toolCall.result.length : 1,
        timestamp: Date.now()
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown database error',
        timestamp: Date.now()
      };
    }
  }

  private buildSelectQuery(query: SupabaseQuery): string {
    const fields = query.fields?.join(', ') || '*';
    let sql = `SELECT ${fields} FROM ${query.table}`;
    
    if (query.conditions && Object.keys(query.conditions).length > 0) {
      const whereClause = Object.entries(query.conditions)
        .map(([key, value], index) => `${key} = $${index + 1}`)
        .join(' AND ');
      sql += ` WHERE ${whereClause}`;
    }
    
    return sql;
  }

  private buildInsertQuery(query: SupabaseQuery): string {
    if (!query.data) {
      throw new Error('Insert operation requires data');
    }
    
    const columns = Object.keys(query.data).join(', ');
    const placeholders = Object.keys(query.data)
      .map((_, index) => `$${index + 1}`)
      .join(', ');
    
    return `INSERT INTO ${query.table} (${columns}) VALUES (${placeholders})`;
  }

  private buildUpdateQuery(query: SupabaseQuery): { sql: string; params: any[] } {
    if (!query.data) {
      throw new Error('Update operation requires data');
    }
    
    const params: any[] = [];
    const setClause = Object.entries(query.data)
      .map(([key, value]) => {
        params.push(value);
        return `${key} = $${params.length}`;
      })
      .join(', ');
    
    let sql = `UPDATE ${query.table} SET ${setClause}`;
    
    if (query.conditions && Object.keys(query.conditions).length > 0) {
      const whereClause = Object.entries(query.conditions)
        .map(([key, value]) => {
          params.push(value);
          return `${key} = $${params.length}`;
        })
        .join(' AND ');
      sql += ` WHERE ${whereClause}`;
    }
    
    return { sql, params };
  }

  private buildDeleteQuery(query: SupabaseQuery): { sql: string; params: any[] } {
    let sql = `DELETE FROM ${query.table}`;
    const params: any[] = [];
    
    if (query.conditions && Object.keys(query.conditions).length > 0) {
      const whereClause = Object.entries(query.conditions)
        .map(([key, value]) => {
          params.push(value);
          return `${key} = $${params.length}`;
        })
        .join(' AND ');
      sql += ` WHERE ${whereClause}`;
    } else {
      throw new Error('Delete operation requires conditions to prevent accidental data loss');
    }
    
    return { sql, params };
  }

  async testConnection(): Promise<boolean> {
    try {
      await this.executeQuery({
        table: 'information_schema.tables',
        operation: 'select',
        fields: ['table_name'],
        conditions: { table_schema: 'public' }
      });
      return true;
    } catch {
      return false;
    }
  }

  async listTables(): Promise<string[]> {
    try {
      const result = await this.executeQuery({
        table: 'information_schema.tables',
        operation: 'select',
        fields: ['table_name'],
        conditions: { table_schema: 'public' }
      });
      
      if (result.success && result.data) {
        return result.data.map((row: any) => row.table_name);
      }
      return [];
    } catch {
      return [];
    }
  }

  async getTableSchema(tableName: string): Promise<any[]> {
    try {
      const result = await this.executeQuery({
        table: 'information_schema.columns',
        operation: 'select',
        fields: ['column_name', 'data_type', 'is_nullable'],
        conditions: { 
          table_schema: 'public',
          table_name: tableName
        }
      });
      
      return result.success ? result.data || [] : [];
    } catch {
      return [];
    }
  }
}