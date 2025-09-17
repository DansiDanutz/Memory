/**
 * Memo App Backend - Main Entry Point
 * Enterprise-grade backend with HMAC-SHA256 security
 * 
 * @author Senior Development Team
 * @version 1.0.0
 * @security HMAC-SHA256 Authentication
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import { config } from './config';
import { logger, securityLogger } from './utils/logger';
import { securityHeaders, apiRateLimit } from './middleware/security';
import { metricsMiddleware } from './middleware/metrics';
import { errorHandler } from './middleware/error-handler';
import { rawBodyMiddleware } from './middleware/raw-body';

// Import routes
import memoriesRouter from './routes/memories';
import whatsappRouter from './routes/whatsapp';
import aiRouter from './routes/ai';
import syncRouter from './routes/sync';
import healthRouter from './routes/health';
import adminRouter from './routes/admin';

// Import services
import { DatabaseService } from './services/database';
import { RedisService } from './services/redis';
import { AIService } from './services/ai';
import { WhatsAppService } from './services/whatsapp';

class MemoAppServer {
  private app: express.Application;
  private server: any;

  constructor() {
    this.app = express();
    this.initializeMiddleware();
    this.initializeRoutes();
    this.initializeErrorHandling();
  }

  /**
   * Initialize middleware stack with security focus
   */
  private initializeMiddleware(): void {
    // Security headers (must be first)
    this.app.use(securityHeaders);

    // CORS configuration
    this.app.use(cors({
      origin: config.env === 'production' 
        ? ['https://memo-app.com', 'https://app.memo-app.com']
        : ['http://localhost:3000', 'http://localhost:3001'],
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: [
        'Content-Type',
        'Authorization',
        'X-Memo-Signature',
        'X-Memo-Timestamp',
        'X-Hub-Signature-256',
        'X-Timestamp'
      ]
    }));

    // Request logging
    this.app.use(morgan('combined', {
      stream: {
        write: (message: string) => {
          logger.info(message.trim());
        }
      }
    }));

    // Compression
    this.app.use(compression());

    // Raw body middleware (for HMAC verification)
    this.app.use(rawBodyMiddleware);

    // JSON parsing with size limits
    this.app.use(express.json({ 
      limit: '10mb',
      verify: (req: any, res, buf) => {
        req.rawBody = buf;
      }
    }));

    this.app.use(express.urlencoded({ 
      extended: true, 
      limit: '10mb' 
    }));

    // Rate limiting
    this.app.use('/api', apiRateLimit);

    // Performance metrics
    this.app.use(metricsMiddleware);

    // Request ID for tracing
    this.app.use((req: any, res, next) => {
      req.requestId = require('uuid').v4();
      res.setHeader('X-Request-ID', req.requestId);
      next();
    });

    logger.info('Middleware initialized successfully');
  }

  /**
   * Initialize API routes
   */
  private initializeRoutes(): void {
    // Health check (no auth required)
    this.app.use('/health', healthRouter);

    // API routes (with HMAC authentication)
    this.app.use('/api/memories', memoriesRouter);
    this.app.use('/api/whatsapp', whatsappRouter);
    this.app.use('/api/ai', aiRouter);
    this.app.use('/api/sync', syncRouter);

    // Admin routes (with strict authentication)
    this.app.use('/admin', adminRouter);

    // API documentation
    this.app.get('/api/docs', (req, res) => {
      res.json(require('./docs/api-docs').apiDocumentation);
    });

    // Root endpoint
    this.app.get('/', (req, res) => {
      res.json({
        name: 'Memo App Backend',
        version: '1.0.0',
        description: 'Personal AI Brain with HMAC-SHA256 Security',
        status: 'operational',
        timestamp: new Date().toISOString(),
        security: 'HMAC-SHA256 Enabled',
        endpoints: {
          health: '/health',
          api: '/api',
          docs: '/api/docs'
        }
      });
    });

    // 404 handler
    this.app.use('*', (req, res) => {
      logger.warn('404 - Route not found', { 
        path: req.originalUrl,
        method: req.method,
        ip: req.ip 
      });
      
      res.status(404).json({
        error: 'Route not found',
        code: 'ROUTE_NOT_FOUND',
        path: req.originalUrl,
        method: req.method
      });
    });

    logger.info('Routes initialized successfully');
  }

  /**
   * Initialize error handling
   */
  private initializeErrorHandling(): void {
    this.app.use(errorHandler);
    
    // Uncaught exception handler
    process.on('uncaughtException', (error) => {
      logger.error('Uncaught Exception', { 
        error: error.message,
        stack: error.stack 
      });
      
      securityLogger.error('Uncaught Exception - Potential Security Issue', {
        error: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
      
      process.exit(1);
    });

    // Unhandled promise rejection handler
    process.on('unhandledRejection', (reason, promise) => {
      logger.error('Unhandled Rejection', { 
        reason,
        promise 
      });
      
      securityLogger.error('Unhandled Promise Rejection', {
        reason: String(reason),
        timestamp: new Date().toISOString()
      });
    });

    logger.info('Error handling initialized successfully');
  }

  /**
   * Initialize database and external services
   */
  private async initializeServices(): Promise<void> {
    try {
      // Initialize database
      await DatabaseService.initialize();
      logger.info('Database service initialized');

      // Initialize Redis
      await RedisService.initialize();
      logger.info('Redis service initialized');

      // Initialize AI service
      await AIService.initialize();
      logger.info('AI service initialized');

      // Initialize WhatsApp service
      await WhatsAppService.initialize();
      logger.info('WhatsApp service initialized');

      logger.info('All services initialized successfully');
    } catch (error) {
      logger.error('Service initialization failed', { 
        error: error.message,
        stack: error.stack 
      });
      throw error;
    }
  }

  /**
   * Start the server
   */
  public async start(): Promise<void> {
    try {
      // Initialize services
      await this.initializeServices();

      // Start HTTP server
      this.server = this.app.listen(config.port, '0.0.0.0', () => {
        logger.info(`🚀 Memo App Backend started successfully`, {
          port: config.port,
          environment: config.env,
          security: 'HMAC-SHA256 Enabled',
          timestamp: new Date().toISOString()
        });

        securityLogger.info('Server started with security enabled', {
          port: config.port,
          environment: config.env,
          securityLevel: 'Enterprise',
          hmacEnabled: true,
          timestamp: new Date().toISOString()
        });
      });

      // Graceful shutdown handling
      this.setupGracefulShutdown();

    } catch (error) {
      logger.error('Failed to start server', { 
        error: error.message,
        stack: error.stack 
      });
      process.exit(1);
    }
  }

  /**
   * Setup graceful shutdown
   */
  private setupGracefulShutdown(): void {
    const gracefulShutdown = async (signal: string) => {
      logger.info(`Received ${signal}. Starting graceful shutdown...`);

      // Stop accepting new connections
      this.server.close(async () => {
        logger.info('HTTP server closed');

        try {
          // Close database connections
          await DatabaseService.close();
          logger.info('Database connections closed');

          // Close Redis connections
          await RedisService.close();
          logger.info('Redis connections closed');

          // Close AI service connections
          await AIService.close();
          logger.info('AI service connections closed');

          // Close WhatsApp service
          await WhatsAppService.close();
          logger.info('WhatsApp service closed');

          logger.info('Graceful shutdown completed');
          process.exit(0);

        } catch (error) {
          logger.error('Error during graceful shutdown', { 
            error: error.message 
          });
          process.exit(1);
        }
      });

      // Force shutdown after 30 seconds
      setTimeout(() => {
        logger.error('Forced shutdown after timeout');
        process.exit(1);
      }, 30000);
    };

    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));
  }

  /**
   * Get Express app instance
   */
  public getApp(): express.Application {
    return this.app;
  }
}

// Start server if this file is run directly
if (require.main === module) {
  const server = new MemoAppServer();
  server.start().catch((error) => {
    logger.error('Failed to start application', { 
      error: error.message,
      stack: error.stack 
    });
    process.exit(1);
  });
}

export { MemoAppServer };
export default MemoAppServer;

