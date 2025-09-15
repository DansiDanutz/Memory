// Production-ready logging system for Memory App
export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
  CRITICAL = 'critical'
}

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  module: string;
  message: string;
  metadata?: any;
  userId?: string;
  sessionId?: string;
}

export class ProductionLogger {
  private static instance: ProductionLogger;
  private logQueue: LogEntry[] = [];
  private isProduction = process.env.NODE_ENV === 'production';

  private constructor() {}

  static getInstance(): ProductionLogger {
    if (!ProductionLogger.instance) {
      ProductionLogger.instance = new ProductionLogger();
    }
    return ProductionLogger.instance;
  }

  log(level: LogLevel, module: string, message: string, metadata?: any): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      module,
      message,
      metadata
    };

    // Add to queue for potential remote logging
    this.logQueue.push(entry);

    // Console output in development
    if (!this.isProduction) {
      const logMethod = level === LogLevel.ERROR || level === LogLevel.CRITICAL ? console.error 
                       : level === LogLevel.WARN ? console.warn 
                       : console.log;
      
      logMethod(`[${entry.timestamp}] [${level.toUpperCase()}] [${module}] ${message}`, 
                metadata ? JSON.stringify(metadata, null, 2) : '');
    }

    // Critical errors should be handled immediately
    if (level === LogLevel.CRITICAL) {
      this.handleCriticalError(entry);
    }

    // Rotate log queue to prevent memory leaks
    if (this.logQueue.length > 1000) {
      this.logQueue = this.logQueue.slice(-500);
    }
  }

  debug(module: string, message: string, metadata?: any): void {
    this.log(LogLevel.DEBUG, module, message, metadata);
  }

  info(module: string, message: string, metadata?: any): void {
    this.log(LogLevel.INFO, module, message, metadata);
  }

  warn(module: string, message: string, metadata?: any): void {
    this.log(LogLevel.WARN, module, message, metadata);
  }

  error(module: string, message: string, metadata?: any): void {
    this.log(LogLevel.ERROR, module, message, metadata);
  }

  critical(module: string, message: string, metadata?: any): void {
    this.log(LogLevel.CRITICAL, module, message, metadata);
  }

  // SLE-specific logging methods
  sleDecision(callerId: string, outcome: string, reasoning: string[], metadata?: any): void {
    this.info('SLE', `Decision: ${outcome} for caller ${callerId}`, {
      callerId,
      outcome,
      reasoning,
      ...metadata
    });
  }

  sleViolation(callerId: string, violation: string, metadata?: any): void {
    this.warn('SLE_SECURITY', `Security violation: ${violation} by caller ${callerId}`, {
      callerId,
      violation,
      ...metadata
    });
  }

  conversationStart(userId: string, sessionId: string): void {
    this.info('CONVERSATION', `Started session for user ${userId}`, {
      userId,
      sessionId,
      action: 'session_start'
    });
  }

  conversationEnd(userId: string, sessionId: string, messageCount: number): void {
    this.info('CONVERSATION', `Ended session for user ${userId} (${messageCount} messages)`, {
      userId,
      sessionId,
      messageCount,
      action: 'session_end'
    });
  }

  mcpOperation(operation: string, success: boolean, metadata?: any): void {
    const level = success ? LogLevel.INFO : LogLevel.ERROR;
    this.log(level, 'MCP', `${operation}: ${success ? 'SUCCESS' : 'FAILED'}`, metadata);
  }

  private handleCriticalError(entry: LogEntry): void {
    // In production, this would send alerts, notifications, etc.
    console.error('CRITICAL ERROR DETECTED:', entry);
    
    // Could implement:
    // - Email notifications
    // - Slack alerts
    // - PagerDuty integration
    // - Database logging for audit trails
  }

  // Get recent logs for debugging
  getRecentLogs(count: number = 100): LogEntry[] {
    return this.logQueue.slice(-count);
  }

  // Get logs filtered by level
  getLogsByLevel(level: LogLevel, count: number = 50): LogEntry[] {
    return this.logQueue
      .filter(entry => entry.level === level)
      .slice(-count);
  }
}

// Export singleton instance
export const logger = ProductionLogger.getInstance();