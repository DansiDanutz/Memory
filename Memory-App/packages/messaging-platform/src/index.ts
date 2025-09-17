// Unified Messaging Platform Manager for Memory App
import { MemoryAppTelegramBot, TelegramBotConfig } from '@memory-app/telegram-bot';
import { MemoryAppWhatsAppBot, WhatsAppBotConfig } from '@memory-app/whatsapp-bot';
import { logger } from '@memory-app/conversation/src/production-logger';

export interface MessagingPlatformConfig {
  telegram?: {
    enabled: boolean;
    botToken?: string;
    config?: Partial<TelegramBotConfig>;
  };
  whatsapp?: {
    enabled: boolean;
    config?: Partial<WhatsAppBotConfig>;
  };
  enableVoiceProcessing?: boolean;
  enableImageAnalysis?: boolean;
  enableMemoryNumbers?: boolean;
}

export interface PlatformStats {
  platform: 'telegram' | 'whatsapp';
  userCount: number;
  isActive: boolean;
  features: string[];
  status: 'running' | 'stopped' | 'error' | 'initializing';
}

export class MessagingPlatformManager {
  private telegramBot?: MemoryAppTelegramBot;
  private whatsappBot?: MemoryAppWhatsAppBot;
  private config: MessagingPlatformConfig;
  private isStarted: boolean = false;

  constructor(config: MessagingPlatformConfig) {
    this.config = config;
    
    logger.info('MessagingPlatform', 'Messaging Platform Manager initialized', {
      telegramEnabled: config.telegram?.enabled || false,
      whatsappEnabled: config.whatsapp?.enabled || false,
      voiceProcessing: config.enableVoiceProcessing || false,
      imageAnalysis: config.enableImageAnalysis || false,
      memoryNumbers: config.enableMemoryNumbers || false
    });
  }

  // Start all enabled platforms
  async start(): Promise<void> {
    try {
      logger.info('MessagingPlatform', 'Starting messaging platforms');

      const promises: Promise<void>[] = [];

      // Start Telegram bot if enabled
      if (this.config.telegram?.enabled && this.config.telegram.botToken) {
        promises.push(this.startTelegramBot());
      }

      // Start WhatsApp bot if enabled
      if (this.config.whatsapp?.enabled) {
        promises.push(this.startWhatsAppBot());
      }

      if (promises.length === 0) {
        throw new Error('No messaging platforms enabled. Please enable at least one platform.');
      }

      await Promise.all(promises);
      this.isStarted = true;

      logger.info('MessagingPlatform', 'All enabled messaging platforms started successfully');

    } catch (error) {
      logger.error('MessagingPlatform', 'Failed to start messaging platforms', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      throw error;
    }
  }

  // Start Telegram bot
  private async startTelegramBot(): Promise<void> {
    try {
      if (!this.config.telegram?.botToken) {
        throw new Error('Telegram bot token is required');
      }

      logger.info('MessagingPlatform', 'Starting Telegram bot');

      this.telegramBot = new MemoryAppTelegramBot({
        botToken: this.config.telegram.botToken,
        enableVoiceProcessing: this.config.enableVoiceProcessing || false,
        enableImageAnalysis: this.config.enableImageAnalysis || false,
        enableMemoryNumbers: this.config.enableMemoryNumbers || false,
        ...this.config.telegram.config
      });

      await this.telegramBot.start();
      
      logger.info('MessagingPlatform', 'Telegram bot started successfully');

    } catch (error) {
      logger.error('MessagingPlatform', 'Failed to start Telegram bot', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      throw new Error(`Telegram bot initialization failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Start WhatsApp bot
  private async startWhatsAppBot(): Promise<void> {
    try {
      logger.info('MessagingPlatform', 'Starting WhatsApp bot');

      this.whatsappBot = new MemoryAppWhatsAppBot({
        enableVoiceProcessing: this.config.enableVoiceProcessing || false,
        enableImageAnalysis: this.config.enableImageAnalysis || false,
        enableMemoryNumbers: this.config.enableMemoryNumbers || false,
        businessName: 'Memory App',
        businessDescription: 'Privacy-first AI Memory Assistant',
        ...this.config.whatsapp?.config
      });

      await this.whatsappBot.start();
      
      logger.info('MessagingPlatform', 'WhatsApp bot started successfully');

    } catch (error) {
      logger.error('MessagingPlatform', 'Failed to start WhatsApp bot', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      throw new Error(`WhatsApp bot initialization failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Stop all platforms
  async stop(): Promise<void> {
    try {
      logger.info('MessagingPlatform', 'Stopping messaging platforms');

      const promises: Promise<void>[] = [];

      if (this.telegramBot) {
        promises.push(this.telegramBot.stop());
      }

      if (this.whatsappBot) {
        promises.push(this.whatsappBot.stop());
      }

      await Promise.all(promises);
      this.isStarted = false;

      logger.info('MessagingPlatform', 'All messaging platforms stopped');

    } catch (error) {
      logger.error('MessagingPlatform', 'Error stopping messaging platforms', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  // Get statistics for all platforms
  getStats(): PlatformStats[] {
    const stats: PlatformStats[] = [];

    if (this.telegramBot) {
      const telegramInfo = this.telegramBot.getBotInfo();
      stats.push({
        platform: 'telegram',
        userCount: telegramInfo.userCount,
        isActive: telegramInfo.isRunning,
        features: telegramInfo.features,
        status: telegramInfo.isRunning ? 'running' : 'stopped'
      });
    }

    if (this.whatsappBot) {
      const whatsappInfo = this.whatsappBot.getBotInfo();
      stats.push({
        platform: 'whatsapp',
        userCount: whatsappInfo.userCount,
        isActive: whatsappInfo.isReady,
        features: whatsappInfo.features,
        status: whatsappInfo.isReady ? 'running' : 'initializing'
      });
    }

    return stats;
  }

  // Get overall platform status
  getStatus(): {
    isStarted: boolean;
    platformCount: number;
    totalUsers: number;
    enabledFeatures: string[];
    platforms: PlatformStats[];
  } {
    const stats = this.getStats();
    const totalUsers = stats.reduce((sum, stat) => sum + stat.userCount, 0);
    const enabledFeatures = [...new Set(stats.flatMap(stat => stat.features))];

    return {
      isStarted: this.isStarted,
      platformCount: stats.length,
      totalUsers,
      enabledFeatures,
      platforms: stats
    };
  }

  // Restart specific platform
  async restartPlatform(platform: 'telegram' | 'whatsapp'): Promise<void> {
    try {
      logger.info('MessagingPlatform', `Restarting ${platform} platform`);

      if (platform === 'telegram' && this.telegramBot) {
        await this.telegramBot.stop();
        this.telegramBot = undefined;
        await this.startTelegramBot();
      }

      if (platform === 'whatsapp' && this.whatsappBot) {
        await this.whatsappBot.stop();
        this.whatsappBot = undefined;
        await this.startWhatsAppBot();
      }

      logger.info('MessagingPlatform', `${platform} platform restarted successfully`);

    } catch (error) {
      logger.error('MessagingPlatform', `Failed to restart ${platform} platform`, {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      throw error;
    }
  }

  // Check if platform is enabled
  isPlatformEnabled(platform: 'telegram' | 'whatsapp'): boolean {
    if (platform === 'telegram') {
      return this.config.telegram?.enabled || false;
    }
    if (platform === 'whatsapp') {
      return this.config.whatsapp?.enabled || false;
    }
    return false;
  }

  // Update configuration
  updateConfig(newConfig: Partial<MessagingPlatformConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    logger.info('MessagingPlatform', 'Configuration updated', {
      telegramEnabled: this.config.telegram?.enabled || false,
      whatsappEnabled: this.config.whatsapp?.enabled || false
    });
  }
}

// Convenience function for quick setup
export async function createMessagingPlatform(config: MessagingPlatformConfig): Promise<MessagingPlatformManager> {
  const manager = new MessagingPlatformManager(config);
  await manager.start();
  return manager;
}

// Helper function to create configuration with environment variables
export function createConfigFromEnv(): MessagingPlatformConfig {
  const telegramToken = process.env.TELEGRAM_BOT_TOKEN;
  
  return {
    telegram: {
      enabled: !!telegramToken,
      botToken: telegramToken,
      config: {
        trustedUserIds: process.env.TELEGRAM_TRUSTED_USERS?.split(',').map(Number) || [],
        adminUserIds: process.env.TELEGRAM_ADMIN_USERS?.split(',').map(Number) || []
      }
    },
    whatsapp: {
      enabled: process.env.WHATSAPP_ENABLED === 'true',
      config: {
        trustedContacts: process.env.WHATSAPP_TRUSTED_CONTACTS?.split(',') || [],
        adminContacts: process.env.WHATSAPP_ADMIN_CONTACTS?.split(',') || []
      }
    },
    enableVoiceProcessing: process.env.ENABLE_VOICE_PROCESSING !== 'false',
    enableImageAnalysis: process.env.ENABLE_IMAGE_ANALYSIS !== 'false',
    enableMemoryNumbers: process.env.ENABLE_MEMORY_NUMBERS !== 'false'
  };
}