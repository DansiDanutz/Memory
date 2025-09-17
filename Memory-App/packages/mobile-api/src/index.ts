// Mobile App Integration APIs for Memory App
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { RateLimiterMemory } from 'rate-limiter-flexible';
import jwt from 'jsonwebtoken';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '@memory-app/conversation/src/production-logger.js';

export interface MobileSession {
  sessionId: string;
  userId: string;
  deviceId: string;
  platform: 'ios' | 'android';
  appVersion: string;
  createdAt: Date;
  lastActivity: Date;
  isActive: boolean;
}

export interface MobileRequest {
  sessionId: string;
  messageType: 'text' | 'voice' | 'image';
  content: string | Buffer;
  metadata?: {
    location?: { latitude: number; longitude: number };
    deviceInfo?: Record<string, any>;
    timestamp: Date;
  };
}

export interface MobileResponse {
  success: boolean;
  data?: any;
  error?: string;
  sessionId: string;
  timestamp: Date;
}

export class MobileAPIServer {
  private app: express.Application;
  private sessions = new Map<string, MobileSession>();
  private rateLimiter: RateLimiterMemory;
  private upload: multer.Multer;
  private jwtSecret: string;

  constructor(options: {
    port?: number;
    jwtSecret?: string;
    corsOrigins?: string[];
    rateLimitRequests?: number;
  } = {}) {
    this.app = express();
    
    // Require JWT secret - no fallback for security
    const jwtSecret = options.jwtSecret || process.env.JWT_SECRET;
    if (!jwtSecret) {
      throw new Error('JWT_SECRET must be provided via environment variable or constructor options');
    }
    this.jwtSecret = jwtSecret;
    
    // Rate limiting: 100 requests per minute per IP
    this.rateLimiter = new RateLimiterMemory({
      keyPrefix: 'mobile_api',
      points: options.rateLimitRequests || 100,
      duration: 60
    });

    // File upload configuration
    this.upload = multer({
      storage: multer.memoryStorage(),
      limits: {
        fileSize: 10 * 1024 * 1024 // 10MB limit
      },
      fileFilter: (req, file, cb) => {
        // Allow audio and image files
        if (file.mimetype.startsWith('audio/') || file.mimetype.startsWith('image/')) {
          cb(null, true);
        } else {
          cb(new Error('Only audio and image files are allowed'));
        }
      }
    });

    this.setupMiddleware(options.corsOrigins);
    this.setupRoutes();
    this.setupErrorHandling();

    logger.info('MobileAPIServer', 'Mobile API server initialized');
  }

  private setupMiddleware(corsOrigins?: string[]): void {
    // Security headers
    this.app.use(helmet({
      crossOriginResourcePolicy: { policy: "cross-origin" }
    }));

    // CORS configuration
    this.app.use(cors({
      origin: corsOrigins || ['http://localhost:3000', 'https://memory-app.com'],
      methods: ['GET', 'POST', 'PUT', 'DELETE'],
      allowedHeaders: ['Content-Type', 'Authorization'],
      credentials: true
    }));

    // Body parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Rate limiting middleware
    this.app.use(async (req, res, next) => {
      try {
        await this.rateLimiter.consume(req.ip || req.socket.remoteAddress || 'unknown');
        next();
      } catch (rejRes: any) {
        res.status(429).json({
          success: false,
          error: 'Too many requests',
          retryAfter: Math.round(rejRes.msBeforeNext / 1000) || 1
        });
      }
    });

    // Request logging
    this.app.use((req, res, next) => {
      logger.info('MobileAPI', `${req.method} ${req.path}`, {
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        sessionId: req.headers['x-session-id']
      });
      next();
    });
  }

  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', (req, res) => {
      res.json({
        success: true,
        status: 'healthy',
        timestamp: new Date(),
        version: '1.0.0'
      });
    });

    // Authentication endpoint
    this.app.post('/auth/login', this.handleAuth.bind(this));

    // Session management
    this.app.post('/sessions', this.authenticateToken, this.createSession.bind(this));
    this.app.get('/sessions/:sessionId', this.authenticateToken, this.getSession.bind(this));
    this.app.delete('/sessions/:sessionId', this.authenticateToken, this.endSession.bind(this));

    // Text conversation endpoint
    this.app.post('/conversation/text', this.authenticateToken, this.handleTextConversation.bind(this));

    // Voice processing endpoints
    this.app.post('/conversation/voice', 
      this.authenticateToken, 
      this.upload.single('audio'), 
      this.handleVoiceConversation.bind(this)
    );

    // Image processing endpoint
    this.app.post('/conversation/image', 
      this.authenticateToken, 
      this.upload.single('image'), 
      this.handleImageConversation.bind(this)
    );

    // Memory Number endpoints
    this.app.post('/memory/store', this.authenticateToken, this.storeMemory.bind(this));
    this.app.get('/memory/:memoryNumber', this.authenticateToken, this.retrieveMemory.bind(this));
    this.app.delete('/memory/:memoryNumber', this.authenticateToken, this.deleteMemory.bind(this));

    // User preferences endpoint
    this.app.get('/user/preferences', this.authenticateToken, this.getUserPreferences.bind(this));
    this.app.put('/user/preferences', this.authenticateToken, this.updateUserPreferences.bind(this));

    // System status endpoint
    this.app.get('/status', this.authenticateToken, this.getSystemStatus.bind(this));
  }

  private setupErrorHandling(): void {
    // Global error handler
    this.app.use((error: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
      logger.error('MobileAPI', 'Unhandled error', {
        error: error.message,
        stack: error.stack,
        path: req.path,
        method: req.method
      });

      res.status(500).json({
        success: false,
        error: 'Internal server error',
        sessionId: req.headers['x-session-id'] || 'unknown',
        timestamp: new Date()
      });
    });

    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({
        success: false,
        error: 'Endpoint not found',
        timestamp: new Date()
      });
    });
  }

  // JWT Authentication middleware
  private authenticateToken(req: express.Request, res: express.Response, next: express.NextFunction): void {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
      res.status(401).json({
        success: false,
        error: 'Access token required'
      });
      return;
    }

    jwt.verify(token, this.jwtSecret, (err: any, decoded: any) => {
      if (err) {
        logger.warn('MobileAPI', 'Invalid token attempted', { 
          ip: req.ip,
          error: err.message 
        });
        res.status(403).json({
          success: false,
          error: 'Invalid or expired token'
        });
        return;
      }

      (req as any).user = decoded;
      next();
    });
  }

  // Authentication handler
  private async handleAuth(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { userId, deviceId, platform, appVersion } = req.body;

      if (!userId || !deviceId) {
        res.status(400).json({
          success: false,
          error: 'Missing required fields: userId, deviceId'
        });
        return;
      }

      // Generate JWT token
      const token = jwt.sign(
        { userId, deviceId, platform },
        this.jwtSecret,
        { expiresIn: '7d' }
      );

      logger.info('MobileAPI', 'User authenticated successfully', {
        userId,
        deviceId,
        platform,
        appVersion
      });

      res.json({
        success: true,
        data: {
          token,
          expiresIn: '7d'
        },
        timestamp: new Date()
      });

    } catch (error) {
      logger.error('MobileAPI', 'Authentication failed', { 
        error: error instanceof Error ? error.message : 'Unknown error' 
      });
      res.status(500).json({
        success: false,
        error: 'Authentication failed'
      });
    }
  }

  // Create new conversation session
  private async createSession(req: express.Request, res: express.Response): Promise<void> {
    try {
      const user = (req as any).user;
      const { platform, appVersion } = req.body;

      const sessionId = uuidv4();
      const session: MobileSession = {
        sessionId,
        userId: user.userId,
        deviceId: user.deviceId,
        platform: platform || 'unknown',
        appVersion: appVersion || 'unknown',
        createdAt: new Date(),
        lastActivity: new Date(),
        isActive: true
      };

      this.sessions.set(sessionId, session);

      logger.info('MobileAPI', 'Session created', {
        sessionId,
        userId: user.userId,
        deviceId: user.deviceId
      });

      res.json({
        success: true,
        data: { sessionId },
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to create session'
      });
    }
  }

  // Get session information
  private async getSession(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { sessionId } = req.params;
      const session = this.sessions.get(sessionId);

      if (!session) {
        res.status(404).json({
          success: false,
          error: 'Session not found'
        });
        return;
      }

      res.json({
        success: true,
        data: session,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get session'
      });
    }
  }

  // End session
  private async endSession(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { sessionId } = req.params;
      const session = this.sessions.get(sessionId);

      if (session) {
        session.isActive = false;
        this.sessions.delete(sessionId);
      }

      res.json({
        success: true,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to end session'
      });
    }
  }

  // Handle text conversation
  private async handleTextConversation(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { sessionId, message, context } = req.body;
      const user = (req as any).user;

      // Here you would integrate with your conversation engine
      const conversationResponse = {
        message: `Echo: ${message}`,
        confidence: 0.95,
        reasoning: ['Mobile API response'],
        needsVerification: false
      };

      logger.info('MobileAPI', 'Text conversation processed', {
        sessionId,
        userId: user.userId,
        messageLength: message?.length || 0
      });

      res.json({
        success: true,
        data: conversationResponse,
        sessionId,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to process conversation'
      });
    }
  }

  // Handle voice conversation
  private async handleVoiceConversation(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { sessionId } = req.body;
      const user = (req as any).user;
      const audioFile = req.file;

      if (!audioFile) {
        res.status(400).json({
          success: false,
          error: 'Audio file required'
        });
        return;
      }

      // Here you would integrate with your voice processor
      const voiceResponse = {
        transcription: 'Voice processing simulated',
        response: 'Voice response generated',
        confidence: 0.90,
        memoryNumber: null
      };

      logger.info('MobileAPI', 'Voice conversation processed', {
        sessionId,
        userId: user.userId,
        audioSize: audioFile.size
      });

      res.json({
        success: true,
        data: voiceResponse,
        sessionId,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to process voice conversation'
      });
    }
  }

  // Handle image conversation
  private async handleImageConversation(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { sessionId, prompt } = req.body;
      const user = (req as any).user;
      const imageFile = req.file;

      if (!imageFile) {
        res.status(400).json({
          success: false,
          error: 'Image file required'
        });
        return;
      }

      // Here you would integrate with Grok vision capabilities
      const imageResponse = {
        description: 'Image analysis simulated',
        response: 'Image understanding generated',
        confidence: 0.85,
        objects_detected: ['sample', 'objects']
      };

      logger.info('MobileAPI', 'Image conversation processed', {
        sessionId,
        userId: user.userId,
        imageSize: imageFile.size
      });

      res.json({
        success: true,
        data: imageResponse,
        sessionId,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to process image conversation'
      });
    }
  }

  // Store memory with number
  private async storeMemory(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { content, tags, securityLevel } = req.body;
      const user = (req as any).user;

      // Here you would integrate with your memory number system
      const memoryNumber = Math.floor(1000 + Math.random() * 9000).toString();

      logger.info('MobileAPI', 'Memory stored', {
        userId: user.userId,
        memoryNumber,
        contentLength: content?.length || 0
      });

      res.json({
        success: true,
        data: { memoryNumber },
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to store memory'
      });
    }
  }

  // Retrieve memory by number
  private async retrieveMemory(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { memoryNumber } = req.params;
      const user = (req as any).user;

      // Here you would integrate with your memory number system
      const memory = {
        memoryNumber,
        content: 'Sample memory content',
        createdAt: new Date(),
        tags: ['sample']
      };

      res.json({
        success: true,
        data: memory,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to retrieve memory'
      });
    }
  }

  // Delete memory
  private async deleteMemory(req: express.Request, res: express.Response): Promise<void> {
    try {
      const { memoryNumber } = req.params;
      const user = (req as any).user;

      logger.info('MobileAPI', 'Memory deleted', {
        userId: user.userId,
        memoryNumber
      });

      res.json({
        success: true,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to delete memory'
      });
    }
  }

  // Get user preferences
  private async getUserPreferences(req: express.Request, res: express.Response): Promise<void> {
    try {
      const user = (req as any).user;

      const preferences = {
        voiceEnabled: true,
        imageAnalysisEnabled: true,
        memoryNumbersEnabled: true,
        notificationSettings: {
          push: true,
          email: false
        },
        privacyLevel: 'standard'
      };

      res.json({
        success: true,
        data: preferences,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get user preferences'
      });
    }
  }

  // Update user preferences
  private async updateUserPreferences(req: express.Request, res: express.Response): Promise<void> {
    try {
      const user = (req as any).user;
      const preferences = req.body;

      logger.info('MobileAPI', 'User preferences updated', {
        userId: user.userId,
        preferences: Object.keys(preferences)
      });

      res.json({
        success: true,
        data: preferences,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to update user preferences'
      });
    }
  }

  // Get system status
  private async getSystemStatus(req: express.Request, res: express.Response): Promise<void> {
    try {
      const status = {
        activeSessions: this.sessions.size,
        memorySystemStatus: 'operational',
        voiceProcessingStatus: 'operational',
        aiEnginesStatus: {
          openai: 'operational',
          claude: 'operational',
          grok: 'operational'
        },
        uptimeSeconds: process.uptime()
      };

      res.json({
        success: true,
        data: status,
        timestamp: new Date()
      });

    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get system status'
      });
    }
  }

  // Start the server
  start(port: number = 3001): void {
    this.app.listen(port, () => {
      logger.info('MobileAPIServer', `Mobile API server started on port ${port}`);
    });
  }

  // Get Express app instance
  getApp(): express.Application {
    return this.app;
  }
}