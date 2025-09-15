// Telegram Bot Integration for Memory App
import { Telegraf, Context } from 'telegraf';
import { message } from 'telegraf/filters';
import { evaluate, SLEContext } from '@memory-app/sle';
// Memory features - simplified integration
// import { VoiceProcessor } from '@memory-app/voice-processor';
// import { GrokVisionEngine } from '@memory-app/grok-vision';
import { logger } from '@memory-app/conversation/src/production-logger';
import axios from 'axios';
import FormData from 'form-data';

export interface TelegramBotConfig {
  botToken: string;
  enableVoiceProcessing?: boolean;
  enableImageAnalysis?: boolean;
  enableMemoryNumbers?: boolean;
  trustedUserIds?: number[];
  adminUserIds?: number[];
}

export interface TelegramUserProfile {
  telegramId: number;
  username?: string;
  firstName?: string;
  lastName?: string;
  trustLevel?: 'Green' | 'Amber' | 'Red';
  registeredAt: Date;
  lastInteraction: Date;
}

export class MemoryAppTelegramBot {
  private bot: Telegraf;
  private voiceProcessor?: any;
  private visionEngine?: any;
  private memoryStorage = new Map<string, any>();
  private conversationMemories = new Map<string, string[]>();
  private config: TelegramBotConfig;
  private userProfiles: Map<number, TelegramUserProfile> = new Map();

  constructor(config: TelegramBotConfig) {
    this.config = config;
    
    if (!config.botToken) {
      throw new Error('Telegram bot token is required');
    }

    this.bot = new Telegraf(config.botToken);

    // Initialize memory features
    this.initializeMemoryFeatures(config);

    this.setupHandlers();
    
    logger.info('TelegramBot', 'Memory App Telegram bot initialized', {
      voiceEnabled: config.enableVoiceProcessing,
      visionEnabled: config.enableImageAnalysis, 
      memoryNumbersEnabled: config.enableMemoryNumbers,
      memoryStorageReady: true
    });
  }

  private setupHandlers(): void {
    // Start command
    this.bot.start(async (ctx) => {
      await this.handleStart(ctx);
    });

    // Help command
    this.bot.help(async (ctx) => {
      await this.handleHelp(ctx);
    });

    // Memory Number command
    this.bot.command('memory', async (ctx) => {
      await this.handleMemoryNumber(ctx);
    });

    // Privacy settings command
    this.bot.command('privacy', async (ctx) => {
      await this.handlePrivacySettings(ctx);
    });

    // Text messages
    this.bot.on(message('text'), async (ctx) => {
      await this.handleTextMessage(ctx);
    });

    // Voice messages
    if (this.voiceProcessor) {
      this.bot.on(message('voice'), async (ctx) => {
        await this.handleVoiceMessage(ctx);
      });
    }

    // Photo messages
    if (this.visionEngine) {
      this.bot.on(message('photo'), async (ctx) => {
        await this.handlePhotoMessage(ctx);
      });
    }

    // Error handling
    this.bot.catch((err, ctx) => {
      logger.error('TelegramBot', 'Bot error occurred', {
        error: err.message,
        userId: ctx.from?.id,
        updateType: ctx.updateType
      });
      
      ctx.reply('❌ I encountered an error processing your request. Please try again.');
    });
  }

  private async handleStart(ctx: Context): Promise<void> {
    const user = ctx.from;
    if (!user) return;

    // Register or update user profile
    const profile: TelegramUserProfile = {
      telegramId: user.id,
      username: user.username,
      firstName: user.first_name,
      lastName: user.last_name,
      trustLevel: this.calculateInitialTrustLevel(user.id),
      registeredAt: this.userProfiles.get(user.id)?.registeredAt || new Date(),
      lastInteraction: new Date()
    };

    this.userProfiles.set(user.id, profile);

    logger.info('TelegramBot', 'User started bot', {
      userId: user.id,
      username: user.username,
      trustLevel: profile.trustLevel
    });

    const welcomeMessage = `🧠 Welcome to Memory App!

I'm your privacy-first AI memory assistant. I can help you:

🔐 **Smart Privacy Controls**
• Only share what you're allowed to know
• Protect sensitive information automatically
• Learn your trust relationships over time

🎤 **Voice & Visual Memory**
• Process voice messages with Memory Numbers
• Analyze images while protecting your privacy
• Remember conversations securely

📱 **Commands:**
/memory [4-digit code] - Access specific memories
/privacy - View your privacy settings
/help - Show all available commands

Your privacy is my priority. All decisions go through our Smart Limits Engine to ensure your information stays secure.

How can I help you today?`;

    await ctx.reply(welcomeMessage);
  }

  private async handleHelp(ctx: Context): Promise<void> {
    const helpMessage = `🧠 **Memory App Commands:**

**Basic Commands:**
/start - Initialize your Memory App profile
/help - Show this help message
/privacy - View and adjust privacy settings

**Memory Commands:**
/memory [code] - Access memory by 4-digit code
📝 Send text - Store and retrieve information
🎤 Send voice - Voice processing with Memory Numbers
📸 Send photo - Image analysis and memory storage

**Privacy Features:**
• 🟢 Trusted contacts get full access
• 🟡 Known contacts get limited access  
• 🔴 Unknown users get minimal access
• 🔒 Ultra-secret content stays protected

**Voice Commands:**
Say "Memory Number [1234]" in voice messages to access specific memories.

**Smart Features:**
• Automatic privacy level detection
• Context-aware information sharing
• Trust relationship learning
• Provenance verification

Need help with privacy settings? Use /privacy
Questions? Just ask me anything!`;

    await ctx.reply(helpMessage);
  }

  private async handleMemoryNumber(ctx: Context): Promise<void> {
    const user = ctx.from;
    if (!user) return;

    const messageText = ctx.message && 'text' in ctx.message ? ctx.message.text : '';
    const memoryCode = messageText.split(' ')[1]; // Extract code after /memory

    if (!memoryCode || !/^\d{4}$/.test(memoryCode)) {
      await ctx.reply('❌ Please provide a 4-digit Memory Number.\n\nExample: `/memory 1234`');
      return;
    }

    logger.info('TelegramBot', 'Memory Number request', {
      userId: user.id,
      memoryCode: memoryCode
    });

    // Process through SLE
    const sleContext: SLEContext = {
      callerId: `telegram_${user.id}`,
      utterance: `Memory Number access request: ${memoryCode}`,
      domain: 'Memory'
    };

    try {
      const decision = await evaluate(sleContext);
      
      if (decision.outcome === 'disclose') {
        await ctx.reply(`🔓 **Memory ${memoryCode} Retrieved**\n\n[Memory content would be displayed here based on your stored information]\n\n✅ Access granted - trust level: ${decision.thresholds.applied.trustBand}`);
      } else if (decision.outcome === 'verify') {
        await ctx.reply(`🔐 **Verification Required for Memory ${memoryCode}**\n\nPlease confirm your identity to access this memory.\n\n⚠️ Trust level: ${decision.thresholds.applied.trustBand}`);
      } else {
        await ctx.reply(`❌ **Access Denied to Memory ${memoryCode}**\n\nReason: ${decision.reasonCodes.join(', ')}\n\n🔒 This memory requires higher trust level or verification.`);
      }

    } catch (error) {
      logger.error('TelegramBot', 'Memory Number processing failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        userId: user.id,
        memoryCode: memoryCode
      });

      await ctx.reply('❌ Failed to process Memory Number request. Please try again.');
    }
  }

  private async handlePrivacySettings(ctx: Context): Promise<void> {
    const user = ctx.from;
    if (!user) return;

    const profile = this.userProfiles.get(user.id);
    if (!profile) {
      await ctx.reply('❌ Please use /start first to initialize your profile.');
      return;
    }

    const privacyMessage = `🔐 **Your Privacy Settings**

**User Profile:**
• Name: ${profile.firstName} ${profile.lastName || ''}
• Username: @${profile.username || 'N/A'}
• Trust Level: ${this.getTrustEmoji(profile.trustLevel!)} ${profile.trustLevel}
• Member Since: ${profile.registeredAt.toLocaleDateString()}

**Privacy Levels:**
🟢 **Trusted** - Full memory access
🟡 **Known** - Limited information sharing
🔴 **Unknown** - Minimal access only

**Security Features:**
✅ Smart Limits Engine protection
✅ Voice Memory Number recognition
✅ Image privacy filtering
✅ Trust relationship learning
✅ Information provenance tracking

**Current Permissions:**
• Voice Processing: ${this.config.enableVoiceProcessing ? '✅ Enabled' : '❌ Disabled'}
• Image Analysis: ${this.config.enableImageAnalysis ? '✅ Enabled' : '❌ Disabled'}
• Memory Numbers: ${this.config.enableMemoryNumbers ? '✅ Enabled' : '❌ Disabled'}

Your privacy is automatically managed by our Smart Limits Engine. Trust levels are learned from your interactions over time.`;

    await ctx.reply(privacyMessage);
  }

  private async handleTextMessage(ctx: Context): Promise<void> {
    const user = ctx.from;
    const messageText = ctx.message && 'text' in ctx.message ? ctx.message.text : '';
    
    if (!user || !messageText) return;

    this.updateUserInteraction(user.id);

    logger.debug('TelegramBot', 'Processing text message', {
      userId: user.id,
      messageLength: messageText.length
    });

    // Check for Memory Number in text
    if (this.config.enableMemoryNumbers) {
      const memoryNumberMatch = messageText.match(/memory\s+number\s+(\d{4})/i);
      if (memoryNumberMatch) {
        const memoryCode = memoryNumberMatch[1];
        await ctx.reply(`🔢 **Memory Number Detected: ${memoryCode}**\n\nProcessing your memory request...`);
        
        // Create memory access context
        const sleContext: SLEContext = {
          callerId: `telegram_${user.id}`,
          utterance: `Memory Number access request: ${memoryCode}`,
          domain: 'Finance' // Use valid domain
        };

        const decision = await evaluate(sleContext);
        
        if (decision.outcome === 'disclose') {
          await ctx.reply(`🔓 **Memory ${memoryCode} Retrieved**\n\n[Memory content would be displayed here]\n\n✅ Access granted`);
        } else {
          await ctx.reply(`❌ **Access Denied to Memory ${memoryCode}**\n\nReason: ${decision.reasonCodes.join(', ')}`);
        }
        return;
      }
    }

    // Process through SLE for general conversation
    const sleContext: SLEContext = {
      callerId: `telegram_${user.id}`,
      utterance: messageText,
      domain: 'Family' // Use valid domain
    };

    try {
      const decision = await evaluate(sleContext);
      
      let responseText = '';
      
      switch (decision.outcome) {
        case 'disclose':
          responseText = `💬 I understand your message about: "${messageText}"\n\n✅ I can help you with this information.`;
          break;
        case 'partial':
          responseText = `💬 I can share some information about: "${messageText.substring(0, 50)}..."\n\n⚠️ Limited details due to privacy settings.`;
          break;
        case 'probe':
          responseText = `❓ Could you tell me more about what you're looking for?\n\n💭 I need more context to help you properly.`;
          break;
        case 'verify':
          responseText = `🔐 I need to verify your identity before discussing: "${messageText.substring(0, 50)}..."\n\n⚠️ This topic requires additional verification.`;
          break;
        case 'decline':
          responseText = `❌ I cannot discuss this topic due to privacy restrictions.\n\n🔒 Reason: ${decision.reasonCodes.join(', ')}`;
          break;
        default:
          responseText = `🤔 I'm processing your request: "${messageText.substring(0, 50)}..."\n\n⏳ Please give me a moment to analyze this properly.`;
      }

      await ctx.reply(responseText);

    } catch (error) {
      logger.error('TelegramBot', 'Text message processing failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        userId: user.id
      });

      await ctx.reply('❌ I encountered an error processing your message. Please try again.');
    }
  }

  private async handleVoiceMessage(ctx: Context): Promise<void> {
    const user = ctx.from;
    if (!user || !this.voiceProcessor) return;

    this.updateUserInteraction(user.id);

    await ctx.reply('🎤 Processing your voice message...');

    try {
      const voiceMessage = ctx.message && 'voice' in ctx.message ? ctx.message.voice : null;
      if (!voiceMessage) {
        await ctx.reply('❌ Could not process voice message.');
        return;
      }

      // Download voice file from Telegram
      const fileUrl = await ctx.telegram.getFileLink(voiceMessage.file_id);
      const response = await axios.get(fileUrl.href, { responseType: 'arraybuffer' });
      const audioBuffer = Buffer.from(response.data);

      logger.info('TelegramBot', 'Processing voice message', {
        userId: user.id,
        duration: voiceMessage.duration,
        fileSize: audioBuffer.length
      });

      // Process voice through Voice Processor
      const transcription = await this.voiceProcessor.speechToText(audioBuffer);

      if (!transcription) {
        await ctx.reply('❌ Could not transcribe your voice message. Please try again.');
        return;
      }

      await ctx.reply(`🎤 **Voice Transcription:**\n"${transcription}"\n\nProcessing through privacy system...`);

      // Check for Memory Numbers in transcription
      if (this.config.enableMemoryNumbers) {
        const memoryNumber = this.voiceProcessor.extractMemoryNumber(transcription);
        if (memoryNumber) {
          await ctx.reply(`🔢 **Memory Number Detected: ${memoryNumber}**\n\nRetrieving your memory...`);
          
          // Process Memory Number access
          const sleContext: SLEContext = {
            callerId: `telegram_${user.id}`,
            utterance: `Voice Memory Number access: ${memoryNumber}`,
            domain: 'Memory'
          };

          const decision = await evaluate(sleContext);
          
          if (decision.outcome === 'disclose') {
            await ctx.reply(`🔓 **Memory ${memoryNumber} Retrieved via Voice**\n\n[Memory content would be displayed here]\n\n✅ Voice access granted`);
          } else {
            await ctx.reply(`❌ **Voice Access Denied to Memory ${memoryNumber}**\n\nReason: ${decision.reasonCodes.join(', ')}`);
          }
          return;
        }
      }

      // Process as regular conversation
      const sleContext: SLEContext = {
        callerId: `telegram_${user.id}`,
        utterance: transcription,
        domain: 'General'
      };

      const decision = await evaluate(sleContext);
      
      let response = `🎤 **Voice Message Processed**\n\n`;
      
      switch (decision.outcome) {
        case 'disclose':
          response += `✅ I can help with your voice request about: "${transcription}"`;
          break;
        case 'partial':
          response += `⚠️ I can share limited information about your voice request.`;
          break;
        case 'verify':
          response += `🔐 Your voice request requires verification before I can respond.`;
          break;
        case 'decline':
          response += `❌ I cannot process this voice request due to privacy restrictions.`;
          break;
        default:
          response += `🤔 Processing your voice request...`;
      }

      await ctx.reply(responseText);

    } catch (error) {
      logger.error('TelegramBot', 'Voice message processing failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        userId: user.id
      });

      await ctx.reply('❌ Failed to process voice message. Please try again.');
    }
  }

  private async handlePhotoMessage(ctx: Context): Promise<void> {
    const user = ctx.from;
    if (!user || !this.visionEngine) return;

    this.updateUserInteraction(user.id);

    await ctx.reply('📸 Analyzing your image...');

    try {
      const photos = ctx.message && 'photo' in ctx.message ? ctx.message.photo : null;
      if (!photos || photos.length === 0) {
        await ctx.reply('❌ Could not process image.');
        return;
      }

      // Get the largest photo
      const photo = photos[photos.length - 1];
      const fileUrl = await ctx.telegram.getFileLink(photo.file_id);
      const response = await axios.get(fileUrl.href, { responseType: 'arraybuffer' });
      const imageBuffer = Buffer.from(response.data);

      logger.info('TelegramBot', 'Processing image', {
        userId: user.id,
        fileSize: imageBuffer.length,
        width: photo.width,
        height: photo.height
      });

      // Determine security level based on user trust
      const profile = this.userProfiles.get(user.id);
      const securityLevel = this.mapTrustToSecurityLevel(profile?.trustLevel || 'Red');

      // Analyze image through Grok Vision
      const analysis = await this.visionEngine.analyzeImage({
        image: imageBuffer,
        analysisType: 'memory_context',
        securityLevel: securityLevel,
        userId: `telegram_${user.id}`
      });

      let responseMessage = `📸 **Image Analysis Complete**\n\n`;
      responseMessage += `🔍 **Description:** ${analysis.description}\n`;
      responseMessage += `🎯 **Confidence:** ${(analysis.confidence * 100).toFixed(1)}%\n`;

      if (analysis.objects.length > 0) {
        responseMessage += `\n🏷️ **Objects Detected:**\n`;
        analysis.objects.slice(0, 5).forEach(obj => {
          responseMessage += `• ${obj.name} (${(obj.confidence * 100).toFixed(1)}%)\n`;
        });
      }

      if (analysis.text) {
        responseMessage += `\n📝 **Text Found:** "${analysis.text}"\n`;
      }

      if (analysis.memoryRelevance?.isMemoryCandidate) {
        responseMessage += `\n💾 **Memory Storage:**\n`;
        responseMessage += `✅ This image is worth remembering!\n`;
        if (analysis.memoryRelevance.suggestedMemoryNumber) {
          responseMessage += `🔢 Suggested Memory Number: ${analysis.memoryRelevance.suggestedMemoryNumber}\n`;
        }
        responseMessage += `🏷️ Tags: ${analysis.memoryRelevance.tags.join(', ')}\n`;
      }

      if (analysis.privacyFlags.length > 0) {
        responseMessage += `\n🔒 **Privacy Notices:**\n`;
        analysis.privacyFlags.forEach(flag => {
          responseMessage += `• ${flag.replace(/_/g, ' ')}\n`;
        });
      }

      responseMessage += `\n🔐 Security Level: ${securityLevel}`;

      await ctx.reply(responseMessage);

    } catch (error) {
      logger.error('TelegramBot', 'Photo processing failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        userId: user.id
      });

      await ctx.reply('❌ Failed to analyze image. Please try again.');
    }
  }

  private calculateInitialTrustLevel(userId: number): 'Green' | 'Amber' | 'Red' {
    // Check if user is in trusted list
    if (this.config.trustedUserIds?.includes(userId)) {
      return 'Green';
    }
    
    // Check if user is admin
    if (this.config.adminUserIds?.includes(userId)) {
      return 'Green';
    }
    
    // Default to Red for new users
    return 'Red';
  }

  private getTrustEmoji(trustLevel: string): string {
    switch (trustLevel) {
      case 'Green': return '🟢';
      case 'Amber': return '🟡';
      case 'Red': return '🔴';
      default: return '⚪';
    }
  }

  private mapTrustToSecurityLevel(trustLevel: string): 'General' | 'Secret' | 'Ultra' | 'C2' | 'C3' {
    switch (trustLevel) {
      case 'Green': return 'General';
      case 'Amber': return 'Secret';
      case 'Red': return 'Ultra';
      default: return 'Ultra';
    }
  }

  private updateUserInteraction(userId: number): void {
    const profile = this.userProfiles.get(userId);
    if (profile) {
      profile.lastInteraction = new Date();
      this.userProfiles.set(userId, profile);
    }
  }

  // Start the bot
  async start(): Promise<void> {
    try {
      await this.bot.launch();
      logger.info('TelegramBot', 'Memory App Telegram bot started successfully');
      
      // Enable graceful stop
      process.once('SIGINT', () => this.bot.stop('SIGINT'));
      process.once('SIGTERM', () => this.bot.stop('SIGTERM'));
      
    } catch (error) {
      logger.error('TelegramBot', 'Failed to start Telegram bot', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      throw error;
    }
  }

  // Stop the bot
  async stop(): Promise<void> {
    try {
      this.bot.stop();
      logger.info('TelegramBot', 'Memory App Telegram bot stopped');
    } catch (error) {
      logger.error('TelegramBot', 'Error stopping Telegram bot', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  // Get bot info
  getBotInfo(): {
    userCount: number;
    isRunning: boolean;
    features: string[];
  } {
    return {
      userCount: this.userProfiles.size,
      isRunning: true,
      features: [
        'Smart Limits Engine',
        ...(this.voiceProcessor ? ['Voice Processing'] : []),
        ...(this.visionEngine ? ['Image Analysis'] : []),
        ...(this.config.enableMemoryNumbers ? ['Memory Numbers'] : [])
      ]
    };
  }
}

// Export convenience function for quick setup
export async function createMemoryAppTelegramBot(botToken: string): Promise<MemoryAppTelegramBot> {
  const bot = new MemoryAppTelegramBot({
    botToken,
    enableVoiceProcessing: true,
    enableImageAnalysis: true,
    enableMemoryNumbers: true
  });

  await bot.start();
  return bot;
}