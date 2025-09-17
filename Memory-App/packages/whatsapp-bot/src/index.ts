// WhatsApp Business API Integration for Memory App
import { Client, Message, MessageMedia, Contact } from 'whatsapp-web.js';
import qrcode from 'qrcode-terminal';
import { evaluate, SLEContext } from '@memory-app/sle';
import { VoiceProcessor } from '@memory-app/voice-processor';
import { GrokVisionEngine } from '@memory-app/grok-vision';
import { logger } from '@memory-app/conversation/src/production-logger';
import axios from 'axios';
import mime from 'mime-types';

export interface WhatsAppBotConfig {
  sessionPath?: string;
  enableVoiceProcessing?: boolean;
  enableImageAnalysis?: boolean;
  enableMemoryNumbers?: boolean;
  businessName?: string;
  businessDescription?: string;
  trustedContacts?: string[]; // Phone numbers
  adminContacts?: string[];
}

export interface WhatsAppUserProfile {
  phoneNumber: string;
  contactName?: string;
  isContact: boolean;
  trustLevel: 'Green' | 'Amber' | 'Red';
  registeredAt: Date;
  lastInteraction: Date;
  messageCount: number;
}

export class MemoryAppWhatsAppBot {
  private client: Client;
  private voiceProcessor?: VoiceProcessor;
  private visionEngine?: GrokVisionEngine;
  private config: WhatsAppBotConfig;
  private userProfiles: Map<string, WhatsAppUserProfile> = new Map();
  private isReady: boolean = false;

  constructor(config: WhatsAppBotConfig = {}) {
    this.config = {
      sessionPath: config.sessionPath || './whatsapp-session',
      businessName: config.businessName || 'Memory App',
      businessDescription: config.businessDescription || 'Privacy-first AI Memory Assistant',
      ...config
    };

    // Initialize WhatsApp client
    this.client = new Client({
      authStrategy: undefined, // Use default LocalAuth
      puppeteer: {
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--single-process',
          '--disable-gpu'
        ]
      }
    });

    // Initialize optional services
    if (config.enableVoiceProcessing) {
      this.voiceProcessor = new VoiceProcessor();
    }

    if (config.enableImageAnalysis) {
      this.visionEngine = new GrokVisionEngine();
    }

    this.setupEventHandlers();
    
    logger.info('WhatsAppBot', 'Memory App WhatsApp bot initialized', {
      voiceEnabled: !!this.voiceProcessor,
      visionEnabled: !!this.visionEngine,
      memoryNumbersEnabled: config.enableMemoryNumbers,
      businessName: this.config.businessName
    });
  }

  private setupEventHandlers(): void {
    // QR Code for authentication
    this.client.on('qr', (qr) => {
      logger.info('WhatsAppBot', 'QR Code generated for WhatsApp authentication');
      console.log('🔗 WhatsApp QR Code:');
      qrcode.generate(qr, { small: true });
      console.log('📱 Scan this QR code with your WhatsApp to connect Memory App');
    });

    // Client ready
    this.client.on('ready', async () => {
      this.isReady = true;
      const clientInfo = this.client.info;
      
      logger.info('WhatsAppBot', 'WhatsApp client ready', {
        businessName: this.config.businessName,
        platform: clientInfo.platform,
        clientVersion: clientInfo.phone?.wa_version
      });

      console.log('✅ Memory App WhatsApp Bot is ready!');
      console.log(`📱 Connected as: ${clientInfo.pushname || 'Memory App'}`);
    });

    // Incoming messages
    this.client.on('message', async (message) => {
      await this.handleIncomingMessage(message);
    });

    // Authentication failure
    this.client.on('auth_failure', (msg) => {
      logger.error('WhatsAppBot', 'WhatsApp authentication failed', { error: msg });
      console.error('❌ WhatsApp authentication failed:', msg);
    });

    // Disconnected
    this.client.on('disconnected', (reason) => {
      this.isReady = false;
      logger.warn('WhatsAppBot', 'WhatsApp client disconnected', { reason });
      console.log('⚠️ WhatsApp disconnected:', reason);
    });
  }

  private async handleIncomingMessage(message: Message): Promise<void> {
    try {
      // Skip messages from self or groups (for now)
      if (message.fromMe || message.from.includes('@g.us')) {
        return;
      }

      const contact = await message.getContact();
      const userProfile = await this.getOrCreateUserProfile(contact);
      
      logger.debug('WhatsAppBot', 'Processing incoming message', {
        from: contact.number,
        type: message.type,
        hasMedia: message.hasMedia
      });

      // Update user interaction
      this.updateUserInteraction(contact.number);

      // Handle different message types
      switch (message.type) {
        case 'chat':
          await this.handleTextMessage(message, userProfile);
          break;
        case 'ptt': // Voice message
          if (this.voiceProcessor) {
            await this.handleVoiceMessage(message, userProfile);
          } else {
            await message.reply('🎤 Voice processing is not enabled. Please send a text message instead.');
          }
          break;
        case 'image':
          if (this.visionEngine) {
            await this.handleImageMessage(message, userProfile);
          } else {
            await message.reply('📸 Image analysis is not enabled. Please describe the image in text.');
          }
          break;
        default:
          await this.handleUnsupportedMessage(message, userProfile);
      }

    } catch (error) {
      logger.error('WhatsAppBot', 'Error handling incoming message', {
        error: error instanceof Error ? error.message : 'Unknown error',
        messageType: message.type
      });

      await message.reply('❌ I encountered an error processing your message. Please try again.');
    }
  }

  private async handleTextMessage(message: Message, userProfile: WhatsAppUserProfile): Promise<void> {
    const messageBody = message.body.trim();

    // Check for special commands
    if (messageBody.toLowerCase().startsWith('help') || messageBody === '❓') {
      await this.sendHelpMessage(message);
      return;
    }

    if (messageBody.toLowerCase().startsWith('privacy') || messageBody === '🔐') {
      await this.sendPrivacyInfo(message, userProfile);
      return;
    }

    if (messageBody.toLowerCase().startsWith('memory ') && this.config.enableMemoryNumbers) {
      await this.handleMemoryNumberCommand(message, messageBody, userProfile);
      return;
    }

    // Check for Memory Number in text
    if (this.config.enableMemoryNumbers) {
      const memoryNumberMatch = messageBody.match(/memory\s+number\s+(\d{4})/i);
      if (memoryNumberMatch) {
        const memoryCode = memoryNumberMatch[1];
        await message.reply(`🔢 *Memory Number Detected: ${memoryCode}*\n\nProcessing your memory request...`);
        await this.processMemoryNumberAccess(message, memoryCode, userProfile);
        return;
      }
    }

    // Process through SLE for general conversation
    const sleContext: SLEContext = {
      callerId: `whatsapp_${userProfile.phoneNumber}`,
      utterance: messageBody,
      domain: 'General'
    };

    const decision = await evaluate(sleContext);
    
    let response = '';
    
    switch (decision.outcome) {
      case 'disclose':
        response = `💬 I understand your message.\n\n✅ I can help you with this information.\n\n*Trust Level: ${userProfile.trustLevel}*`;
        break;
      case 'partial':
        response = `💬 I can share some information about your request.\n\n⚠️ Limited details due to privacy settings.\n\n*Trust Level: ${userProfile.trustLevel}*`;
        break;
      case 'probe':
        response = `❓ Could you tell me more about what you're looking for?\n\n💭 I need more context to help you properly.`;
        break;
      case 'verify':
        response = `🔐 I need to verify your identity before discussing this topic.\n\n⚠️ This requires additional verification.`;
        break;
      case 'decline':
        response = `❌ I cannot discuss this topic due to privacy restrictions.\n\n🔒 Reason: ${decision.reasonCodes.join(', ')}`;
        break;
      default:
        response = `🤔 I'm processing your request...\n\n⏳ Please give me a moment to analyze this properly.`;
    }

    await message.reply(response);
  }

  private async handleVoiceMessage(message: Message, userProfile: WhatsAppUserProfile): Promise<void> {
    if (!this.voiceProcessor) return;

    await message.reply('🎤 Processing your voice message...');

    try {
      const media = await message.downloadMedia();
      if (!media) {
        await message.reply('❌ Could not download voice message.');
        return;
      }

      // Convert base64 to buffer
      const audioBuffer = Buffer.from(media.data, 'base64');

      logger.info('WhatsAppBot', 'Processing voice message', {
        from: userProfile.phoneNumber,
        fileSize: audioBuffer.length,
        mimeType: media.mimetype
      });

      // Process voice through Voice Processor
      const transcription = await this.voiceProcessor.speechToText(audioBuffer);

      if (!transcription) {
        await message.reply('❌ Could not transcribe your voice message. Please try again.');
        return;
      }

      await message.reply(`🎤 *Voice Transcription:*\n"${transcription}"\n\nProcessing through privacy system...`);

      // Check for Memory Numbers in transcription
      if (this.config.enableMemoryNumbers) {
        const memoryNumber = this.voiceProcessor.extractMemoryNumber(transcription);
        if (memoryNumber) {
          await message.reply(`🔢 *Memory Number Detected: ${memoryNumber}*\n\nRetrieving your memory...`);
          await this.processMemoryNumberAccess(message, memoryNumber, userProfile);
          return;
        }
      }

      // Process as regular conversation
      const sleContext: SLEContext = {
        callerId: `whatsapp_${userProfile.phoneNumber}`,
        utterance: transcription,
        domain: 'General'
      };

      const decision = await evaluate(sleContext);
      
      let response = `🎤 *Voice Message Processed*\n\n`;
      
      switch (decision.outcome) {
        case 'disclose':
          response += `✅ I can help with your voice request.`;
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

      await message.reply(response);

    } catch (error) {
      logger.error('WhatsAppBot', 'Voice message processing failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        from: userProfile.phoneNumber
      });

      await message.reply('❌ Failed to process voice message. Please try again.');
    }
  }

  private async handleImageMessage(message: Message, userProfile: WhatsAppUserProfile): Promise<void> {
    if (!this.visionEngine) return;

    await message.reply('📸 Analyzing your image...');

    try {
      const media = await message.downloadMedia();
      if (!media) {
        await message.reply('❌ Could not download image.');
        return;
      }

      // Convert base64 to buffer
      const imageBuffer = Buffer.from(media.data, 'base64');

      logger.info('WhatsAppBot', 'Processing image', {
        from: userProfile.phoneNumber,
        fileSize: imageBuffer.length,
        mimeType: media.mimetype
      });

      // Determine security level based on user trust
      const securityLevel = this.mapTrustToSecurityLevel(userProfile.trustLevel);

      // Analyze image through Grok Vision
      const analysis = await this.visionEngine.analyzeImage({
        image: imageBuffer,
        analysisType: 'memory_context',
        securityLevel: securityLevel,
        userId: `whatsapp_${userProfile.phoneNumber}`
      });

      let responseMessage = `📸 *Image Analysis Complete*\n\n`;
      responseMessage += `🔍 *Description:* ${analysis.description}\n`;
      responseMessage += `🎯 *Confidence:* ${(analysis.confidence * 100).toFixed(1)}%\n`;

      if (analysis.objects.length > 0) {
        responseMessage += `\n🏷️ *Objects Detected:*\n`;
        analysis.objects.slice(0, 5).forEach(obj => {
          responseMessage += `• ${obj.name} (${(obj.confidence * 100).toFixed(1)}%)\n`;
        });
      }

      if (analysis.text) {
        responseMessage += `\n📝 *Text Found:* "${analysis.text}"\n`;
      }

      if (analysis.memoryRelevance?.isMemoryCandidate) {
        responseMessage += `\n💾 *Memory Storage:*\n`;
        responseMessage += `✅ This image is worth remembering!\n`;
        if (analysis.memoryRelevance.suggestedMemoryNumber) {
          responseMessage += `🔢 Suggested Memory Number: ${analysis.memoryRelevance.suggestedMemoryNumber}\n`;
        }
        responseMessage += `🏷️ Tags: ${analysis.memoryRelevance.tags.join(', ')}\n`;
      }

      if (analysis.privacyFlags.length > 0) {
        responseMessage += `\n🔒 *Privacy Notices:*\n`;
        analysis.privacyFlags.forEach(flag => {
          responseMessage += `• ${flag.replace(/_/g, ' ')}\n`;
        });
      }

      responseMessage += `\n🔐 Security Level: ${securityLevel}`;

      await message.reply(responseMessage);

    } catch (error) {
      logger.error('WhatsAppBot', 'Image processing failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        from: userProfile.phoneNumber
      });

      await message.reply('❌ Failed to analyze image. Please try again.');
    }
  }

  private async handleUnsupportedMessage(message: Message, userProfile: WhatsAppUserProfile): Promise<void> {
    const response = `❓ I received a ${message.type} message, but I can currently only process:\n\n` +
                    `💬 Text messages\n` +
                    `${this.voiceProcessor ? '🎤 Voice messages\n' : ''}` +
                    `${this.visionEngine ? '📸 Images\n' : ''}` +
                    `\nPlease send a supported message type or type "help" for more information.`;

    await message.reply(response);
  }

  private async sendHelpMessage(message: Message): Promise<void> {
    const helpMessage = `🧠 *Memory App - Privacy-First AI Assistant*\n\n` +
                       `I'm your personal AI memory system with smart privacy controls.\n\n` +
                       `*Available Commands:*\n` +
                       `💬 Send any text message\n` +
                       `${this.voiceProcessor ? '🎤 Send voice messages\n' : ''}` +
                       `${this.visionEngine ? '📸 Send images for analysis\n' : ''}` +
                       `${this.config.enableMemoryNumbers ? '🔢 "memory [4-digit code]" - Access specific memories\n' : ''}` +
                       `🔐 "privacy" - View your privacy settings\n` +
                       `❓ "help" - Show this message\n\n` +
                       `*Privacy Features:*\n` +
                       `• 🟢 Trusted contacts get full access\n` +
                       `• 🟡 Known contacts get limited access\n` +
                       `• 🔴 Unknown numbers get minimal access\n` +
                       `• 🔒 Ultra-secret content stays protected\n\n` +
                       `*Smart Features:*\n` +
                       `• Automatic privacy level detection\n` +
                       `• Context-aware information sharing\n` +
                       `• Trust relationship learning\n` +
                       `• Provenance verification\n\n` +
                       `Your privacy is my priority. All decisions go through our Smart Limits Engine.`;

    await message.reply(helpMessage);
  }

  private async sendPrivacyInfo(message: Message, userProfile: WhatsAppUserProfile): Promise<void> {
    const privacyMessage = `🔐 *Your Privacy Settings*\n\n` +
                          `*Contact Information:*\n` +
                          `• Phone: ${userProfile.phoneNumber}\n` +
                          `• Name: ${userProfile.contactName || 'N/A'}\n` +
                          `• Trust Level: ${this.getTrustEmoji(userProfile.trustLevel)} ${userProfile.trustLevel}\n` +
                          `• Contact Status: ${userProfile.isContact ? 'In your contacts' : 'Not in contacts'}\n` +
                          `• Member Since: ${userProfile.registeredAt.toLocaleDateString()}\n` +
                          `• Messages: ${userProfile.messageCount}\n\n` +
                          `*Privacy Levels:*\n` +
                          `🟢 *Trusted* - Full memory access\n` +
                          `🟡 *Known* - Limited information sharing\n` +
                          `🔴 *Unknown* - Minimal access only\n\n` +
                          `*Security Features:*\n` +
                          `✅ Smart Limits Engine protection\n` +
                          `${this.voiceProcessor ? '✅ Voice Memory Number recognition\n' : '❌ Voice processing disabled\n'}` +
                          `${this.visionEngine ? '✅ Image privacy filtering\n' : '❌ Image analysis disabled\n'}` +
                          `${this.config.enableMemoryNumbers ? '✅ Memory Numbers enabled\n' : '❌ Memory Numbers disabled\n'}` +
                          `✅ Trust relationship learning\n` +
                          `✅ Information provenance tracking\n\n` +
                          `Your privacy is automatically managed by our Smart Limits Engine. Trust levels are learned from your interactions over time.`;

    await message.reply(privacyMessage);
  }

  private async handleMemoryNumberCommand(message: Message, messageBody: string, userProfile: WhatsAppUserProfile): Promise<void> {
    const memoryCode = messageBody.split(' ')[1]; // Extract code after "memory"

    if (!memoryCode || !/^\d{4}$/.test(memoryCode)) {
      await message.reply('❌ Please provide a 4-digit Memory Number.\n\nExample: "memory 1234"');
      return;
    }

    await this.processMemoryNumberAccess(message, memoryCode, userProfile);
  }

  private async processMemoryNumberAccess(message: Message, memoryCode: string, userProfile: WhatsAppUserProfile): Promise<void> {
    logger.info('WhatsAppBot', 'Memory Number request', {
      from: userProfile.phoneNumber,
      memoryCode: memoryCode
    });

    // Process through SLE
    const sleContext: SLEContext = {
      callerId: `whatsapp_${userProfile.phoneNumber}`,
      utterance: `Memory Number access request: ${memoryCode}`,
      domain: 'Memory'
    };

    try {
      const decision = await evaluate(sleContext);
      
      if (decision.outcome === 'disclose') {
        await message.reply(`🔓 *Memory ${memoryCode} Retrieved*\n\n[Memory content would be displayed here based on your stored information]\n\n✅ Access granted - trust level: ${decision.thresholds.applied.trustBand}`);
      } else if (decision.outcome === 'verify') {
        await message.reply(`🔐 *Verification Required for Memory ${memoryCode}*\n\nPlease confirm your identity to access this memory.\n\n⚠️ Trust level: ${decision.thresholds.applied.trustBand}`);
      } else {
        await message.reply(`❌ *Access Denied to Memory ${memoryCode}*\n\nReason: ${decision.reasonCodes.join(', ')}\n\n🔒 This memory requires higher trust level or verification.`);
      }

    } catch (error) {
      logger.error('WhatsAppBot', 'Memory Number processing failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        from: userProfile.phoneNumber,
        memoryCode: memoryCode
      });

      await message.reply('❌ Failed to process Memory Number request. Please try again.');
    }
  }

  private async getOrCreateUserProfile(contact: Contact): Promise<WhatsAppUserProfile> {
    const phoneNumber = contact.number;
    let profile = this.userProfiles.get(phoneNumber);

    if (!profile) {
      profile = {
        phoneNumber: phoneNumber,
        contactName: contact.name || contact.pushname || undefined,
        isContact: contact.isWAContact,
        trustLevel: this.calculateInitialTrustLevel(phoneNumber, contact.isWAContact),
        registeredAt: new Date(),
        lastInteraction: new Date(),
        messageCount: 0
      };

      this.userProfiles.set(phoneNumber, profile);
      
      logger.info('WhatsAppBot', 'New user registered', {
        phoneNumber: phoneNumber,
        contactName: profile.contactName,
        trustLevel: profile.trustLevel,
        isContact: profile.isContact
      });
    }

    return profile;
  }

  private calculateInitialTrustLevel(phoneNumber: string, isContact: boolean): 'Green' | 'Amber' | 'Red' {
    // Check if user is in trusted list
    if (this.config.trustedContacts?.includes(phoneNumber)) {
      return 'Green';
    }
    
    // Check if user is admin
    if (this.config.adminContacts?.includes(phoneNumber)) {
      return 'Green';
    }
    
    // If they're in contacts, start with Amber
    if (isContact) {
      return 'Amber';
    }
    
    // Default to Red for unknown numbers
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

  private updateUserInteraction(phoneNumber: string): void {
    const profile = this.userProfiles.get(phoneNumber);
    if (profile) {
      profile.lastInteraction = new Date();
      profile.messageCount += 1;
      this.userProfiles.set(phoneNumber, profile);
    }
  }

  // Start the bot
  async start(): Promise<void> {
    try {
      await this.client.initialize();
      logger.info('WhatsAppBot', 'Memory App WhatsApp bot initialization started');
      console.log('🔄 Initializing WhatsApp connection...');
      
    } catch (error) {
      logger.error('WhatsAppBot', 'Failed to start WhatsApp bot', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      throw error;
    }
  }

  // Stop the bot
  async stop(): Promise<void> {
    try {
      await this.client.destroy();
      this.isReady = false;
      logger.info('WhatsAppBot', 'Memory App WhatsApp bot stopped');
    } catch (error) {
      logger.error('WhatsAppBot', 'Error stopping WhatsApp bot', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  // Get bot info
  getBotInfo(): {
    userCount: number;
    isReady: boolean;
    features: string[];
    businessInfo: { name: string; description: string };
  } {
    return {
      userCount: this.userProfiles.size,
      isReady: this.isReady,
      features: [
        'Smart Limits Engine',
        ...(this.voiceProcessor ? ['Voice Processing'] : []),
        ...(this.visionEngine ? ['Image Analysis'] : []),
        ...(this.config.enableMemoryNumbers ? ['Memory Numbers'] : [])
      ],
      businessInfo: {
        name: this.config.businessName!,
        description: this.config.businessDescription!
      }
    };
  }
}

// Export convenience function for quick setup
export async function createMemoryAppWhatsAppBot(config: Partial<WhatsAppBotConfig> = {}): Promise<MemoryAppWhatsAppBot> {
  const bot = new MemoryAppWhatsAppBot({
    enableVoiceProcessing: true,
    enableImageAnalysis: true,
    enableMemoryNumbers: true,
    ...config
  });

  await bot.start();
  return bot;
}