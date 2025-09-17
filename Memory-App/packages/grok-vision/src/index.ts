// Grok Vision Engine for Memory App - Image Analysis and Understanding
import OpenAI from 'openai';
import sharp from 'sharp';
import { logger } from '@memory-app/conversation/src/production-logger.js';

export interface ImageAnalysisRequest {
  image: Buffer | string; // Buffer or base64 string
  prompt?: string;
  analysisType: 'describe' | 'questions' | 'extract_text' | 'identify_objects' | 'memory_context';
  securityLevel?: 'General' | 'Secret' | 'Ultra' | 'C2' | 'C3';
  userId: string;
}

export interface ImageAnalysisResult {
  description: string;
  confidence: number;
  objects: Array<{
    name: string;
    confidence: number;
    coordinates?: { x: number; y: number; width: number; height: number };
  }>;
  text?: string;
  memoryRelevance?: {
    isMemoryCandidate: boolean;
    suggestedMemoryNumber?: string;
    tags: string[];
  };
  reasoning: string[];
  privacyFlags: string[];
}

export interface GrokVisionConfig {
  xaiApiKey?: string;
  openaiApiKey?: string; // Fallback
  maxImageSize: number;
  supportedFormats: string[];
  enablePrivacyDetection: boolean;
  enableMemoryExtraction: boolean;
}

export class GrokVisionEngine {
  private grokClient?: OpenAI; // Using OpenAI client for Grok API
  private openaiClient?: OpenAI;
  private config: GrokVisionConfig;

  constructor(config: Partial<GrokVisionConfig> = {}) {
    this.config = {
      maxImageSize: 10 * 1024 * 1024, // 10MB
      supportedFormats: ['jpeg', 'jpg', 'png', 'gif', 'webp'],
      enablePrivacyDetection: true,
      enableMemoryExtraction: true,
      ...config
    };

    const xaiKey = config.xaiApiKey || process.env.XAI_API_KEY;
    const openaiKey = config.openaiApiKey || process.env.OPENAI_API_KEY;

    if (!xaiKey && !openaiKey) {
      throw new Error('Either XAI_API_KEY or OPENAI_API_KEY must be provided');
    }

    // Initialize Grok client (using xAI API)
    if (xaiKey) {
      this.grokClient = new OpenAI({
        apiKey: xaiKey,
        baseURL: 'https://api.x.ai/v1'
      });
    }

    // Initialize OpenAI client as fallback
    if (openaiKey) {
      this.openaiClient = new OpenAI({
        apiKey: openaiKey
      });
    }

    logger.info('GrokVisionEngine', 'Grok Vision engine initialized', {
      maxImageSize: this.config.maxImageSize,
      supportedFormats: this.config.supportedFormats,
      privacyDetection: this.config.enablePrivacyDetection,
      hasGrokKey: !!xaiKey,
      hasOpenAIKey: !!openaiKey
    });
  }

  // Main image analysis method
  async analyzeImage(request: ImageAnalysisRequest): Promise<ImageAnalysisResult> {
    try {
      logger.debug('GrokVisionEngine', 'Starting image analysis', {
        userId: request.userId,
        analysisType: request.analysisType,
        securityLevel: request.securityLevel
      });

      // Validate inputs
      if (!request.image || !request.userId) {
        throw new Error('Image and userId are required');
      }

      // Preprocess image
      const processedImage = await this.preprocessImage(request.image);
      
      // Perform main analysis with Grok (fallback to OpenAI)
      const analysis = await this.performVisionAnalysis(processedImage, request);

      // Apply privacy filtering based on security level
      const filteredResult = await this.applyPrivacyFiltering(analysis, request);

      // Add memory relevance assessment if enabled
      if (this.config.enableMemoryExtraction) {
        filteredResult.memoryRelevance = await this.assessMemoryRelevance(analysis, request);
      }

      logger.info('GrokVisionEngine', 'Image analysis completed', {
        userId: request.userId,
        confidence: filteredResult.confidence,
        objectsDetected: filteredResult.objects.length,
        privacyFlags: filteredResult.privacyFlags.length
      });

      return filteredResult;

    } catch (error) {
      logger.error('GrokVisionEngine', 'Image analysis failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        userId: request.userId,
        analysisType: request.analysisType
      });

      // Return safe fallback result
      return {
        description: 'I was unable to analyze this image at the moment.',
        confidence: 0.1,
        objects: [],
        reasoning: ['Analysis failed: ' + (error instanceof Error ? error.message : 'Unknown error')],
        privacyFlags: ['analysis_error']
      };
    }
  }

  // Preprocess image for analysis
  private async preprocessImage(image: Buffer | string): Promise<string> {
    let imageBuffer: Buffer;

    try {
      // Convert to buffer if base64 string
      if (typeof image === 'string') {
        // Remove data URL prefix if present
        const base64Data = image.replace(/^data:image\/\w+;base64,/, '');
        imageBuffer = Buffer.from(base64Data, 'base64');
      } else {
        imageBuffer = image;
      }

      // Validate file size
      if (imageBuffer.length > this.config.maxImageSize) {
        throw new Error(`Image size ${imageBuffer.length} exceeds maximum ${this.config.maxImageSize}`);
      }

      // Optimize and convert using Sharp
      const processedBuffer = await sharp(imageBuffer)
        .resize(1024, 1024, { 
          fit: 'inside', 
          withoutEnlargement: true 
        })
        .jpeg({ quality: 85 })
        .toBuffer();

      // Convert to base64 for API
      return `data:image/jpeg;base64,${processedBuffer.toString('base64')}`;

    } catch (error) {
      throw new Error(`Image preprocessing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Perform analysis using available vision API
  private async performVisionAnalysis(
    imageBase64: string, 
    request: ImageAnalysisRequest
  ): Promise<ImageAnalysisResult> {
    const prompt = this.buildAnalysisPrompt(request);

    // Try Grok first if available
    if (this.grokClient) {
      try {
        const response = await this.grokClient.chat.completions.create({
          model: "grok-vision-beta", 
          messages: [
            {
              role: "user",
              content: [
                { type: "text", text: prompt },
                { type: "image_url", image_url: { url: imageBase64 }}
              ]
            }
          ],
          max_tokens: 1000,
          temperature: 0.3
        });

        const analysisText = response.choices[0]?.message?.content || '';
        return this.parseAnalysisResponse(analysisText, request.analysisType);

      } catch (error) {
        logger.warn('GrokVisionEngine', 'Grok analysis failed, trying OpenAI fallback', {
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    // Fallback to OpenAI GPT-4 Vision
    if (this.openaiClient) {
      const response = await this.openaiClient.chat.completions.create({
        model: "gpt-4o",
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: prompt },
              { type: "image_url", image_url: { url: imageBase64 }}
            ]
          }
        ],
        max_tokens: 1000,
        temperature: 0.3
      });

      const analysisText = response.choices[0]?.message?.content || '';
      return this.parseAnalysisResponse(analysisText, request.analysisType);
    }

    throw new Error('No vision API available for analysis');
  }

  // Build analysis prompt based on request type
  private buildAnalysisPrompt(request: ImageAnalysisRequest): string {
    const basePrompt = `You are an advanced AI vision system with privacy-aware analysis capabilities. 
Security Level: ${request.securityLevel || 'General'}

Analyze this image and provide structured information including:
1. Description of what you see
2. Objects detected
3. Any text visible
4. Privacy considerations

Focus on being helpful while respecting privacy boundaries.
`;

    switch (request.analysisType) {
      case 'describe':
        return basePrompt + 'Provide a detailed description of the image content.';
      case 'questions':
        return basePrompt + 'Generate thoughtful questions this image might answer.';
      case 'extract_text':
        return basePrompt + 'Focus on extracting any text visible in the image.';
      case 'identify_objects':
        return basePrompt + 'Identify and list all objects visible in the image.';
      case 'memory_context':
        return basePrompt + 'Analyze this image for its potential value as a memory.';
      default:
        return basePrompt + (request.prompt || 'Provide a comprehensive analysis of this image.');
    }
  }

  // Parse the analysis response into structured format
  private parseAnalysisResponse(analysisText: string, analysisType: string): ImageAnalysisResult {
    const result: ImageAnalysisResult = {
      description: analysisText.split('\n')[0] || 'Image analysis completed',
      confidence: 0.8,
      objects: [],
      reasoning: ['Vision analysis completed'],
      privacyFlags: []
    };

    // Extract objects (simple pattern matching)
    const lines = analysisText.split('\n');
    lines.forEach(line => {
      const objectMatch = line.match(/([A-Za-z\s]+):\s*(\d+\.?\d*)%?/);
      if (objectMatch) {
        result.objects.push({
          name: objectMatch[1].trim(),
          confidence: parseFloat(objectMatch[2]) / 100 || 0.8
        });
      }
    });

    // Extract text if present
    const textMatch = analysisText.match(/Text:\s*(.+?)(?:\n|$)/i);
    if (textMatch) {
      result.text = textMatch[1].trim();
    }

    // Check for privacy indicators
    if (analysisText.toLowerCase().includes('private') || 
        analysisText.toLowerCase().includes('personal') ||
        analysisText.toLowerCase().includes('sensitive')) {
      result.privacyFlags.push('potentially_sensitive');
    }

    return result;
  }

  // Apply privacy filtering based on security level
  private async applyPrivacyFiltering(
    analysis: ImageAnalysisResult, 
    request: ImageAnalysisRequest
  ): Promise<ImageAnalysisResult> {
    if (!this.config.enablePrivacyDetection) {
      return analysis;
    }

    const securityLevel = request.securityLevel || 'General';
    
    switch (securityLevel) {
      case 'Ultra':
        analysis.description = 'Image contains restricted content.';
        analysis.objects = [];
        analysis.text = '[REDACTED]';
        analysis.privacyFlags.push('ultra_security_redaction');
        break;

      case 'Secret':
        if (analysis.text && analysis.text.length > 50) {
          analysis.text = analysis.text.substring(0, 50) + '[REDACTED]';
        }
        analysis.objects = analysis.objects.filter(obj => obj.confidence > 0.7);
        analysis.privacyFlags.push('secret_level_filtering');
        break;

      case 'General':
      default:
        // Minimal filtering for general content
        break;
    }

    return analysis;
  }

  // Assess memory relevance for potential storage
  private async assessMemoryRelevance(
    analysis: ImageAnalysisResult,
    request: ImageAnalysisRequest
  ): Promise<ImageAnalysisResult['memoryRelevance']> {
    const isMemoryCandidate = 
      analysis.objects.length > 2 || 
      (analysis.text && analysis.text.length > 10) || 
      analysis.description.toLowerCase().includes('person') || 
      analysis.description.toLowerCase().includes('event');

    const tags: string[] = [];
    
    analysis.objects.forEach(obj => {
      if (obj.confidence > 0.7) {
        tags.push(obj.name.toLowerCase().replace(/\s+/g, '_'));
      }
    });

    tags.push(request.analysisType);
    if (request.securityLevel) {
      tags.push(`security_${request.securityLevel.toLowerCase()}`);
    }

    return {
      isMemoryCandidate,
      suggestedMemoryNumber: isMemoryCandidate ? 
        Math.floor(1000 + Math.random() * 9000).toString() : undefined,
      tags: [...new Set(tags)]
    };
  }

  // Get vision engine capabilities and status
  getCapabilities(): {
    supportedAnalysisTypes: string[];
    maxImageSize: number;
    supportedFormats: string[];
    enginesAvailable: { grok: boolean; openai: boolean };
    privacyFeaturesEnabled: boolean;
  } {
    return {
      supportedAnalysisTypes: ['describe', 'questions', 'extract_text', 'identify_objects', 'memory_context'],
      maxImageSize: this.config.maxImageSize,
      supportedFormats: this.config.supportedFormats,
      enginesAvailable: {
        grok: !!this.grokClient,
        openai: !!this.openaiClient
      },
      privacyFeaturesEnabled: this.config.enablePrivacyDetection
    };
  }
}

// Convenience function for quick image analysis
export async function quickImageAnalysis(
  image: Buffer | string,
  prompt?: string,
  userId: string = 'anonymous'
): Promise<string> {
  const engine = new GrokVisionEngine();
  const result = await engine.analyzeImage({
    image,
    prompt,
    analysisType: 'describe',
    userId
  });
  return result.description;
}