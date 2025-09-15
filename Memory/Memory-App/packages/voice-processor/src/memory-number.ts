// Memory Number System - Voice-activated memory access
import { logger } from '@memory-app/conversation/src/production-logger.js';

export interface MemoryEntry {
  memoryNumber: string;
  content: string;
  createdAt: Date;
  lastAccessed: Date;
  accessCount: number;
  tags: string[];
  securityLevel: 'General' | 'Secret' | 'Ultra' | 'C2' | 'C3';
  userId: string;
}

export interface MemoryNumberConfig {
  maxMemoryNumbers: number;
  numberLength: number;
  expirationDays?: number;
  securityMode: 'strict' | 'standard';
}

export class MemoryNumberSystem {
  private memories = new Map<string, MemoryEntry>();
  private userMemories = new Map<string, Set<string>>();
  private config: MemoryNumberConfig;

  constructor(config: Partial<MemoryNumberConfig> = {}) {
    this.config = {
      maxMemoryNumbers: 10000,
      numberLength: 4,
      securityMode: 'standard',
      expirationDays: 365,
      ...config
    };

    logger.info('MemoryNumberSystem', 'Memory Number System initialized', {
      maxMemoryNumbers: this.config.maxMemoryNumbers,
      numberLength: this.config.numberLength,
      securityMode: this.config.securityMode
    });
  }

  // Generate a new memory number
  generateMemoryNumber(): string {
    const length = this.config.numberLength;
    let memoryNumber: string;
    let attempts = 0;
    const maxAttempts = 1000;

    do {
      memoryNumber = Math.floor(Math.random() * Math.pow(10, length))
        .toString()
        .padStart(length, '0');
      attempts++;
    } while (this.memories.has(memoryNumber) && attempts < maxAttempts);

    if (attempts >= maxAttempts) {
      throw new Error('Unable to generate unique memory number');
    }

    return memoryNumber;
  }

  // Store content with a memory number
  async storeMemory(
    content: string,
    userId: string,
    options: {
      memoryNumber?: string;
      tags?: string[];
      securityLevel?: MemoryEntry['securityLevel'];
    } = {}
  ): Promise<string> {
    const memoryNumber = options.memoryNumber || this.generateMemoryNumber();

    // Validate memory number format
    if (!this.isValidMemoryNumber(memoryNumber)) {
      throw new Error(`Invalid memory number format: ${memoryNumber}`);
    }

    // Check if memory number already exists
    if (this.memories.has(memoryNumber)) {
      throw new Error(`Memory number ${memoryNumber} already exists`);
    }

    // Check user memory limits
    const userMemorySet = this.userMemories.get(userId) || new Set();
    if (userMemorySet.size >= this.config.maxMemoryNumbers) {
      throw new Error(`User ${userId} has reached maximum memory numbers limit`);
    }

    const memoryEntry: MemoryEntry = {
      memoryNumber,
      content,
      createdAt: new Date(),
      lastAccessed: new Date(),
      accessCount: 0,
      tags: options.tags || [],
      securityLevel: options.securityLevel || 'General',
      userId
    };

    // Store memory
    this.memories.set(memoryNumber, memoryEntry);
    userMemorySet.add(memoryNumber);
    this.userMemories.set(userId, userMemorySet);

    logger.info('MemoryNumberSystem', 'Memory stored successfully', {
      memoryNumber,
      userId,
      contentLength: content.length,
      securityLevel: memoryEntry.securityLevel,
      tags: memoryEntry.tags
    });

    return memoryNumber;
  }

  // Retrieve memory by number
  async retrieveMemory(
    memoryNumber: string,
    requestingUserId: string,
    trustScore?: number
  ): Promise<MemoryEntry | null> {
    // Validate memory number format
    if (!this.isValidMemoryNumber(memoryNumber)) {
      logger.warn('MemoryNumberSystem', 'Invalid memory number format attempted', { 
        memoryNumber, 
        requestingUserId 
      });
      return null;
    }

    const memory = this.memories.get(memoryNumber);
    if (!memory) {
      logger.info('MemoryNumberSystem', 'Memory number not found', { 
        memoryNumber, 
        requestingUserId 
      });
      return null;
    }

    // Security checks
    const accessAllowed = await this.checkAccess(memory, requestingUserId, trustScore);
    if (!accessAllowed) {
      logger.warn('MemoryNumberSystem', 'Memory access denied', {
        memoryNumber,
        requestingUserId,
        originalUserId: memory.userId,
        securityLevel: memory.securityLevel
      });
      return null;
    }

    // Update access tracking
    memory.lastAccessed = new Date();
    memory.accessCount++;

    logger.info('MemoryNumberSystem', 'Memory retrieved successfully', {
      memoryNumber,
      requestingUserId,
      accessCount: memory.accessCount,
      securityLevel: memory.securityLevel
    });

    return { ...memory }; // Return a copy to prevent external modification
  }

  // Check if user has access to memory based on security level and trust
  private async checkAccess(
    memory: MemoryEntry,
    requestingUserId: string,
    trustScore: number = 0.5
  ): Promise<boolean> {
    // Owner always has access
    if (memory.userId === requestingUserId) {
      return true;
    }

    // Security level checks
    switch (memory.securityLevel) {
      case 'Ultra':
        return false; // Ultra secrets are self-only

      case 'Secret':
        return trustScore >= 0.8; // High trust required

      case 'C2':
        return trustScore >= 0.75; // C2 clearance level

      case 'C3':
        return trustScore >= 0.7; // C3 clearance level

      case 'General':
      default:
        return trustScore >= 0.5; // Standard trust threshold
    }
  }

  // List all memories for a user
  getUserMemories(userId: string): MemoryEntry[] {
    const userMemoryNumbers = this.userMemories.get(userId) || new Set();
    return Array.from(userMemoryNumbers)
      .map(number => this.memories.get(number))
      .filter((memory): memory is MemoryEntry => memory !== undefined)
      .sort((a, b) => b.lastAccessed.getTime() - a.lastAccessed.getTime());
  }

  // Search memories by content or tags
  searchMemories(
    userId: string,
    query: string,
    options: {
      searchTags?: boolean;
      searchContent?: boolean;
      securityLevel?: MemoryEntry['securityLevel'][];
    } = {}
  ): MemoryEntry[] {
    const userMemories = this.getUserMemories(userId);
    const searchTags = options.searchTags !== false;
    const searchContent = options.searchContent !== false;
    const queryLower = query.toLowerCase();

    return userMemories.filter(memory => {
      // Security level filter
      if (options.securityLevel && !options.securityLevel.includes(memory.securityLevel)) {
        return false;
      }

      // Search in content
      if (searchContent && memory.content.toLowerCase().includes(queryLower)) {
        return true;
      }

      // Search in tags
      if (searchTags && memory.tags.some(tag => tag.toLowerCase().includes(queryLower))) {
        return true;
      }

      return false;
    });
  }

  // Delete a memory
  async deleteMemory(memoryNumber: string, userId: string): Promise<boolean> {
    const memory = this.memories.get(memoryNumber);
    if (!memory) {
      return false;
    }

    // Only owner can delete
    if (memory.userId !== userId) {
      logger.warn('MemoryNumberSystem', 'Unauthorized memory deletion attempt', {
        memoryNumber,
        requestingUserId: userId,
        actualUserId: memory.userId
      });
      return false;
    }

    // Remove from storage
    this.memories.delete(memoryNumber);
    const userMemorySet = this.userMemories.get(userId);
    if (userMemorySet) {
      userMemorySet.delete(memoryNumber);
    }

    logger.info('MemoryNumberSystem', 'Memory deleted successfully', {
      memoryNumber,
      userId
    });

    return true;
  }

  // Clean up expired memories
  cleanupExpiredMemories(): number {
    if (!this.config.expirationDays) {
      return 0;
    }

    const expirationDate = new Date();
    expirationDate.setDate(expirationDate.getDate() - this.config.expirationDays);

    let deletedCount = 0;
    for (const [memoryNumber, memory] of this.memories.entries()) {
      if (memory.lastAccessed < expirationDate) {
        this.memories.delete(memoryNumber);
        const userMemorySet = this.userMemories.get(memory.userId);
        if (userMemorySet) {
          userMemorySet.delete(memoryNumber);
        }
        deletedCount++;
      }
    }

    if (deletedCount > 0) {
      logger.info('MemoryNumberSystem', 'Expired memories cleaned up', {
        deletedCount,
        expirationDays: this.config.expirationDays
      });
    }

    return deletedCount;
  }

  // Validate memory number format
  private isValidMemoryNumber(memoryNumber: string): boolean {
    const pattern = new RegExp(`^\\d{${this.config.numberLength}}$`);
    return pattern.test(memoryNumber);
  }

  // Get system statistics
  getStatistics(): {
    totalMemories: number;
    totalUsers: number;
    memoriesBySecurityLevel: Record<string, number>;
    averageAccessCount: number;
  } {
    const memoriesBySecurityLevel: Record<string, number> = {};
    let totalAccessCount = 0;

    for (const memory of this.memories.values()) {
      memoriesBySecurityLevel[memory.securityLevel] = 
        (memoriesBySecurityLevel[memory.securityLevel] || 0) + 1;
      totalAccessCount += memory.accessCount;
    }

    return {
      totalMemories: this.memories.size,
      totalUsers: this.userMemories.size,
      memoriesBySecurityLevel,
      averageAccessCount: this.memories.size > 0 ? totalAccessCount / this.memories.size : 0
    };
  }
}