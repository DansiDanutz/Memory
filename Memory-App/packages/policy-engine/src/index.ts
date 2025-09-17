// YAML-based Policy Configuration Engine for Memory App
import * as fs from 'fs/promises';
import * as yaml from 'yaml';
import * as chokidar from 'chokidar';
import { logger } from '@memory-app/conversation/src/production-logger.js';

export interface PolicyRule {
  id: string;
  name: string;
  description?: string;
  domain: string[];
  securityLevel: string[];
  conditions: {
    trustScore?: { min?: number; max?: number };
    mkeScore?: { min?: number; max?: number };
    timeRestrictions?: { allowedHours?: number[]; allowedDays?: string[] };
    userRoles?: string[];
    geolocation?: { allowedCountries?: string[]; blockedCountries?: string[] };
  };
  actions: {
    allow: boolean;
    requireVerify?: boolean;
    redactions?: string[];
    customResponse?: string;
    logLevel?: 'info' | 'warn' | 'error';
  };
  priority: number;
  enabled: boolean;
  metadata?: Record<string, any>;
}

export interface PolicyConfiguration {
  version: string;
  metadata: {
    name: string;
    description: string;
    author?: string;
    created: string;
    lastModified: string;
  };
  defaults: {
    trustThresholds: Record<string, number>;
    mkeThresholds: {
      divert: number;
      probe: number;
      partial: number;
      disclose: number;
      verify: number;
    };
    securityPolicies: Record<string, {
      maxTrustRequired: number;
      requireVerify: boolean;
      allowExternal: boolean;
    }>;
  };
  rules: PolicyRule[];
  inheritance: {
    domain: Record<string, string[]>; // domain inheritance hierarchy
    securityLevel: Record<string, string[]>; // security level inheritance
  };
}

export class PolicyEngine {
  private config: PolicyConfiguration | null = null;
  private configPath: string;
  private watcher: chokidar.FSWatcher | null = null;
  private isWatching = false;

  constructor(configPath: string) {
    this.configPath = configPath;
    logger.info('PolicyEngine', 'Policy engine initialized', { configPath });
  }

  // Load policy configuration from YAML file
  async loadConfiguration(): Promise<void> {
    try {
      logger.debug('PolicyEngine', 'Loading policy configuration', { path: this.configPath });

      const configData = await fs.readFile(this.configPath, 'utf8');
      const parsedConfig = yaml.parse(configData) as PolicyConfiguration;

      // Validate configuration structure
      this.validateConfiguration(parsedConfig);

      // Update last modified timestamp
      parsedConfig.metadata.lastModified = new Date().toISOString();

      this.config = parsedConfig;

      logger.info('PolicyEngine', 'Policy configuration loaded successfully', {
        version: parsedConfig.version,
        rulesCount: parsedConfig.rules.length,
        enabledRules: parsedConfig.rules.filter(r => r.enabled).length
      });

    } catch (error) {
      logger.error('PolicyEngine', 'Failed to load policy configuration', {
        error: error instanceof Error ? error.message : 'Unknown error',
        path: this.configPath
      });
      throw new Error(`Failed to load policy configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Start watching for configuration file changes
  startWatching(): void {
    if (this.isWatching) {
      return;
    }

    this.watcher = chokidar.watch(this.configPath, {
      persistent: true,
      ignoreInitial: true
    });

    this.watcher.on('change', async () => {
      logger.info('PolicyEngine', 'Policy configuration file changed, reloading...');
      try {
        await this.loadConfiguration();
        logger.info('PolicyEngine', 'Policy configuration reloaded successfully');
      } catch (error) {
        logger.error('PolicyEngine', 'Failed to reload policy configuration', {
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    });

    this.isWatching = true;
    logger.info('PolicyEngine', 'Started watching policy configuration file');
  }

  // Stop watching for file changes
  stopWatching(): void {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
      this.isWatching = false;
      logger.info('PolicyEngine', 'Stopped watching policy configuration file');
    }
  }

  // Evaluate policy for a given context
  async evaluatePolicy(context: {
    domain: string;
    securityLevel: string;
    trustScore: number;
    mkeScore: number;
    userId: string;
    userRoles?: string[];
    geolocation?: { country: string };
    timestamp?: Date;
  }): Promise<{
    allow: boolean;
    requireVerify: boolean;
    redactions: string[];
    customResponse?: string;
    matchedRules: string[];
    reasoning: string[];
  }> {
    if (!this.config) {
      throw new Error('Policy configuration not loaded');
    }

    const matchedRules: PolicyRule[] = [];
    const reasoning: string[] = [];

    // Find all matching rules
    for (const rule of this.config.rules) {
      if (!rule.enabled) continue;

      if (this.ruleMatches(rule, context)) {
        matchedRules.push(rule);
        reasoning.push(`Rule '${rule.name}' (${rule.id}) matched`);
      }
    }

    // Sort by priority (higher priority first)
    matchedRules.sort((a, b) => b.priority - a.priority);

    // Apply the highest priority rule, or use defaults
    let result = {
      allow: true,
      requireVerify: false,
      redactions: [] as string[],
      customResponse: undefined as string | undefined,
      matchedRules: matchedRules.map(r => r.id),
      reasoning
    };

    if (matchedRules.length > 0) {
      const topRule = matchedRules[0];
      result.allow = topRule.actions.allow;
      result.requireVerify = topRule.actions.requireVerify || false;
      result.redactions = topRule.actions.redactions || [];
      result.customResponse = topRule.actions.customResponse;
      
      reasoning.push(`Applied rule '${topRule.name}' with priority ${topRule.priority}`);

      // Log rule application
      const logLevel = topRule.actions.logLevel || 'info';
      logger[logLevel]('PolicyEngine', `Policy rule applied: ${topRule.name}`, {
        ruleId: topRule.id,
        userId: context.userId,
        domain: context.domain,
        securityLevel: context.securityLevel,
        allow: result.allow,
        requireVerify: result.requireVerify
      });
    } else {
      reasoning.push('No specific rules matched, using default policy');
      
      // Apply default thresholds
      const domainThreshold = this.config.defaults.trustThresholds[context.domain] || 0.5;
      const securityPolicy = this.config.defaults.securityPolicies[context.securityLevel];
      
      if (context.trustScore < domainThreshold) {
        result.allow = false;
        reasoning.push(`Trust score ${context.trustScore} below domain threshold ${domainThreshold}`);
      }
      
      if (securityPolicy && context.trustScore < securityPolicy.maxTrustRequired) {
        result.requireVerify = securityPolicy.requireVerify;
        reasoning.push(`Security policy requires verification for level ${context.securityLevel}`);
      }
    }

    return result;
  }

  // Check if a rule matches the given context
  private ruleMatches(rule: PolicyRule, context: any): boolean {
    // Domain matching (with inheritance)
    if (!this.matchesWithInheritance(context.domain, rule.domain, this.config!.inheritance.domain)) {
      return false;
    }

    // Security level matching (with inheritance)
    if (!this.matchesWithInheritance(context.securityLevel, rule.securityLevel, this.config!.inheritance.securityLevel)) {
      return false;
    }

    // Trust score conditions
    if (rule.conditions.trustScore) {
      if (rule.conditions.trustScore.min !== undefined && context.trustScore < rule.conditions.trustScore.min) {
        return false;
      }
      if (rule.conditions.trustScore.max !== undefined && context.trustScore > rule.conditions.trustScore.max) {
        return false;
      }
    }

    // MKE score conditions
    if (rule.conditions.mkeScore) {
      if (rule.conditions.mkeScore.min !== undefined && context.mkeScore < rule.conditions.mkeScore.min) {
        return false;
      }
      if (rule.conditions.mkeScore.max !== undefined && context.mkeScore > rule.conditions.mkeScore.max) {
        return false;
      }
    }

    // Time restrictions
    if (rule.conditions.timeRestrictions) {
      const now = context.timestamp || new Date();
      const currentHour = now.getHours();
      const currentDay = now.toLocaleDateString('en-US', { weekday: 'long' });

      if (rule.conditions.timeRestrictions.allowedHours && 
          !rule.conditions.timeRestrictions.allowedHours.includes(currentHour)) {
        return false;
      }

      if (rule.conditions.timeRestrictions.allowedDays && 
          !rule.conditions.timeRestrictions.allowedDays.includes(currentDay)) {
        return false;
      }
    }

    // User role matching
    if (rule.conditions.userRoles && context.userRoles) {
      const hasRequiredRole = rule.conditions.userRoles.some(role => 
        context.userRoles.includes(role)
      );
      if (!hasRequiredRole) {
        return false;
      }
    }

    // Geolocation matching
    if (rule.conditions.geolocation && context.geolocation) {
      const { allowedCountries, blockedCountries } = rule.conditions.geolocation;
      
      if (allowedCountries && !allowedCountries.includes(context.geolocation.country)) {
        return false;
      }
      
      if (blockedCountries && blockedCountries.includes(context.geolocation.country)) {
        return false;
      }
    }

    return true;
  }

  // Check if value matches any of the allowed values, considering inheritance
  private matchesWithInheritance(
    value: string, 
    allowedValues: string[], 
    inheritance: Record<string, string[]>
  ): boolean {
    if (allowedValues.includes(value)) {
      return true;
    }

    // Check inheritance hierarchy
    for (const allowedValue of allowedValues) {
      const inherited = inheritance[allowedValue] || [];
      if (inherited.includes(value)) {
        return true;
      }
    }

    return false;
  }

  // Validate configuration structure
  private validateConfiguration(config: PolicyConfiguration): void {
    if (!config.version) {
      throw new Error('Policy configuration missing version');
    }

    if (!config.metadata || !config.metadata.name) {
      throw new Error('Policy configuration missing metadata');
    }

    if (!config.defaults) {
      throw new Error('Policy configuration missing defaults');
    }

    if (!Array.isArray(config.rules)) {
      throw new Error('Policy configuration rules must be an array');
    }

    // Validate each rule
    config.rules.forEach((rule, index) => {
      if (!rule.id || !rule.name) {
        throw new Error(`Rule at index ${index} missing id or name`);
      }

      if (!Array.isArray(rule.domain) || !Array.isArray(rule.securityLevel)) {
        throw new Error(`Rule ${rule.id} must have domain and securityLevel as arrays`);
      }

      if (typeof rule.priority !== 'number') {
        throw new Error(`Rule ${rule.id} must have numeric priority`);
      }

      if (typeof rule.enabled !== 'boolean') {
        throw new Error(`Rule ${rule.id} must have boolean enabled flag`);
      }
    });
  }

  // Get current configuration
  getConfiguration(): PolicyConfiguration | null {
    return this.config;
  }

  // Get policy statistics
  getStatistics(): {
    totalRules: number;
    enabledRules: number;
    rulesByDomain: Record<string, number>;
    rulesBySecurityLevel: Record<string, number>;
  } {
    if (!this.config) {
      return {
        totalRules: 0,
        enabledRules: 0,
        rulesByDomain: {},
        rulesBySecurityLevel: {}
      };
    }

    const stats = {
      totalRules: this.config.rules.length,
      enabledRules: this.config.rules.filter(r => r.enabled).length,
      rulesByDomain: {} as Record<string, number>,
      rulesBySecurityLevel: {} as Record<string, number>
    };

    this.config.rules.forEach(rule => {
      rule.domain.forEach(domain => {
        stats.rulesByDomain[domain] = (stats.rulesByDomain[domain] || 0) + 1;
      });

      rule.securityLevel.forEach(level => {
        stats.rulesBySecurityLevel[level] = (stats.rulesBySecurityLevel[level] || 0) + 1;
      });
    });

    return stats;
  }
}