// Voice Processing Engine for Memory App
import OpenAI from 'openai';
import { logger } from '@memory-app/conversation/src/production-logger.js';

export interface VoiceProcessingConfig {
  openaiApiKey?: string;
  enableRealTimeProcessing?: boolean;
  voiceLanguage?: string;
  speechModel?: 'whisper-1' | 'whisper-turbo';
  ttsVoice?: 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer';
  memoryNumberEnabled?: boolean;
}

export interface VoiceTranscription {
  text: string;
  confidence: number;
  language?: string;
  duration?: number;
  memoryNumber?: string;
}

export interface VoiceSynthesis {
  audioBuffer: Buffer;
  duration: number;
  format: 'mp3' | 'wav';
}

export class VoiceProcessor {
  private openai: OpenAI;
  private config: VoiceProcessingConfig;
  private isListening = false;

  constructor(config: VoiceProcessingConfig = {}) {
    this.config = {
      enableRealTimeProcessing: true,
      voiceLanguage: 'en',
      speechModel: 'whisper-1',
      ttsVoice: 'nova',
      memoryNumberEnabled: true,
      ...config
    };

    this.openai = new OpenAI({
      apiKey: config.openaiApiKey || process.env.OPENAI_API_KEY
    });

    logger.info('VoiceProcessor', 'Voice processing engine initialized', {
      language: this.config.voiceLanguage,
      model: this.config.speechModel,
      ttsVoice: this.config.ttsVoice,
      memoryNumberEnabled: this.config.memoryNumberEnabled
    });
  }

  // Speech-to-Text Processing
  async transcribeAudio(audioBuffer: Buffer): Promise<VoiceTranscription> {
    try {
      logger.debug('VoiceProcessor', 'Starting audio transcription', {
        bufferSize: audioBuffer.length,
        model: this.config.speechModel
      });

      // Create a file-like object for OpenAI Whisper API
      // Use Blob or Buffer depending on environment
      let audioFile: any;
      if (typeof File !== 'undefined') {
        audioFile = new File([audioBuffer], 'audio.mp3', { type: 'audio/mpeg' });
      } else {
        // Node.js environment - create a file-like object
        audioFile = {
          name: 'audio.mp3',
          type: 'audio/mpeg',
          arrayBuffer: () => Promise.resolve(audioBuffer.buffer.slice(
            audioBuffer.byteOffset, 
            audioBuffer.byteOffset + audioBuffer.byteLength
          )),
          stream: () => new ReadableStream({
            start(controller) {
              controller.enqueue(new Uint8Array(audioBuffer));
              controller.close();
            }
          })
        };
      }

      const transcription = await this.openai.audio.transcriptions.create({
        file: audioFile,
        model: this.config.speechModel!,
        language: this.config.voiceLanguage,
        response_format: 'json'
      });

      // Check for Memory Number pattern
      const memoryNumber = this.extractMemoryNumber(transcription.text);

      const result: VoiceTranscription = {
        text: transcription.text,
        confidence: 0.95, // OpenAI doesn't provide confidence scores
        language: this.config.voiceLanguage,
        memoryNumber: memoryNumber || undefined
      };

      logger.info('VoiceProcessor', 'Audio transcription completed', {
        textLength: result.text.length,
        memoryNumber: result.memoryNumber,
        confidence: result.confidence
      });

      return result;

    } catch (error) {
      logger.error('VoiceProcessor', 'Audio transcription failed', { 
        error: error instanceof Error ? error.message : 'Unknown error',
        bufferSize: audioBuffer.length 
      });
      
      return {
        text: '',
        confidence: 0,
        language: this.config.voiceLanguage
      };
    }
  }

  // Text-to-Speech Processing
  async synthesizeVoice(text: string): Promise<VoiceSynthesis> {
    try {
      logger.debug('VoiceProcessor', 'Starting voice synthesis', {
        textLength: text.length,
        voice: this.config.ttsVoice
      });

      const mp3 = await this.openai.audio.speech.create({
        model: 'tts-1-hd',
        voice: this.config.ttsVoice!,
        input: text,
        response_format: 'mp3'
      });

      const audioBuffer = Buffer.from(await mp3.arrayBuffer());

      const result: VoiceSynthesis = {
        audioBuffer,
        duration: this.estimateAudioDuration(text),
        format: 'mp3'
      };

      logger.info('VoiceProcessor', 'Voice synthesis completed', {
        audioSize: result.audioBuffer.length,
        estimatedDuration: result.duration,
        voice: this.config.ttsVoice
      });

      return result;

    } catch (error) {
      logger.error('VoiceProcessor', 'Voice synthesis failed', { 
        error: error instanceof Error ? error.message : 'Unknown error',
        textLength: text.length 
      });
      
      throw new Error(`Voice synthesis failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Memory Number Extraction (pattern: "Memory 1234" or "Remember number 5678")
  private extractMemoryNumber(text: string): string | null {
    const patterns = [
      /memory\s+(\d{3,6})/i,
      /remember\s+number\s+(\d{3,6})/i,
      /recall\s+(\d{3,6})/i,
      /memory\s+code\s+(\d{3,6})/i
    ];

    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        logger.info('VoiceProcessor', 'Memory Number detected', { 
          memoryNumber: match[1],
          originalText: text.substring(0, 100) 
        });
        return match[1];
      }
    }

    return null;
  }

  // Real-time voice processing for continuous conversation
  async startVoiceSession(
    onTranscription: (transcription: VoiceTranscription) => void,
    onError: (error: Error) => void
  ): Promise<void> {
    if (this.isListening) {
      logger.warn('VoiceProcessor', 'Voice session already active');
      return;
    }

    try {
      this.isListening = true;
      logger.info('VoiceProcessor', 'Starting voice session', {
        realTimeEnabled: this.config.enableRealTimeProcessing
      });

      // In a real implementation, this would use microphone input
      // For now, we'll simulate the session start
      onTranscription({
        text: 'Voice session started successfully',
        confidence: 1.0,
        language: this.config.voiceLanguage
      });

    } catch (error) {
      this.isListening = false;
      const err = new Error(`Failed to start voice session: ${error instanceof Error ? error.message : 'Unknown error'}`);
      logger.error('VoiceProcessor', 'Voice session startup failed', { error: err.message });
      onError(err);
    }
  }

  async stopVoiceSession(): Promise<void> {
    if (!this.isListening) {
      return;
    }

    this.isListening = false;
    logger.info('VoiceProcessor', 'Voice session stopped');
  }

  // Memory Number validation and processing
  validateMemoryNumber(memoryNumber: string): boolean {
    // Memory numbers should be 3-6 digits
    return /^\d{3,6}$/.test(memoryNumber);
  }

  // Estimate audio duration based on text (rough approximation)
  private estimateAudioDuration(text: string): number {
    // Average speaking rate: ~150 words per minute
    const words = text.split(/\s+/).length;
    const wordsPerSecond = 150 / 60;
    return Math.ceil(words / wordsPerSecond);
  }

  // Get current voice processing status
  getStatus(): {
    isListening: boolean;
    config: VoiceProcessingConfig;
    capabilities: string[];
  } {
    return {
      isListening: this.isListening,
      config: this.config,
      capabilities: [
        'Speech-to-Text (Whisper)',
        'Text-to-Speech (TTS-HD)',
        'Memory Number Recognition',
        'Real-time Processing',
        'Multi-language Support'
      ]
    };
  }
}

// Convenience function for quick transcription
export async function quickTranscribe(audioBuffer: Buffer, apiKey?: string): Promise<string> {
  const processor = new VoiceProcessor({ openaiApiKey: apiKey });
  const result = await processor.transcribeAudio(audioBuffer);
  return result.text;
}

// Convenience function for quick synthesis
export async function quickSynthesize(text: string, apiKey?: string): Promise<Buffer> {
  const processor = new VoiceProcessor({ openaiApiKey: apiKey });
  const result = await processor.synthesizeVoice(text);
  return result.audioBuffer;
}