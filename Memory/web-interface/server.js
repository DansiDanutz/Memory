const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const multer = require('multer');
const uuid = require('uuid');
const path = require('path');
const fs = require('fs').promises;
const OpenAI = require('openai');

const app = express();

// 🧠 Initialize OpenAI for AI-powered relationship insights
// the newest OpenAI model is "gpt-5" which was released August 7, 2025. do not change this unless explicitly requested by the user
const openai = new OpenAI({ 
    apiKey: process.env.OPENAI_API_KEY 
});

// 🔧 BUG FIX: Enable trust proxy for Replit environment
app.set('trust proxy', true); // Required for X-Forwarded-For headers

const server = http.createServer(app);

// Performance optimizations
app.use(compression()); // Enable gzip compression

// 🔒 MILITARY-GRADE CSP: Maximum security with self-hosted assets only
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'"], // Only self-hosted scripts
            styleSrc: ["'self'"], // Only self-hosted styles  
            fontSrc: ["'self'"], // Only self-hosted fonts
            imgSrc: ["'self'", "data:"],
            connectSrc: ["'self'"],
            frameAncestors: ["'none'"], // Prevent clickjacking
            baseUri: ["'none'"], // Prevent base tag injection
            objectSrc: ["'none'"], // Prevent object/embed attacks
            formAction: ["'self'"], // Restrict form submissions
            upgradeInsecureRequests: []
        }
    }
}));

// 🔒 PRODUCTION SECURITY: Require explicit CORS configuration  
const allowedOrigins = process.env.ALLOWED_ORIGINS 
    ? process.env.ALLOWED_ORIGINS.split(',')
    : (process.env.NODE_ENV === 'production' 
        ? (() => {
            console.error('🚨 FATAL: ALLOWED_ORIGINS must be explicitly set in production!');
            console.error('Example: ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com');
            process.exit(1);
        })()
        : ['http://localhost:5000', 'http://127.0.0.1:5000', 'https://*.replit.dev', 'https://cbf27266-ed2a-4456-9f23-c2601cf03b57-00-3pa7wo550z3f4.riker.replit.dev']);

app.use(cors({
    origin: (origin, callback) => {
        // Allow same-origin requests (no origin header)
        if (!origin) {
            callback(null, true);
            return;
        }
        
        // Check against allowed origins with proper pattern matching
        const isAllowed = allowedOrigins.some(allowed => {
            if (allowed === origin) return true;
            if (allowed === 'https://*.replit.dev') {
                return /^https:\/\/[a-z0-9-]+\.replit\.dev$/.test(origin);
            }
            return false;
        });
        
        console.log(`🔍 CORS check: origin=${origin}, allowed=${isAllowed}`);
        
        if (isAllowed) {
            callback(null, true);
        } else {
            console.warn('🚫 CORS blocked origin:', origin);
            callback(new Error('Not allowed by CORS'));
        }
    },
    credentials: true
}));

// 🔒 CRITICAL FIX: Initialize Socket.IO after CORS config is defined
const io = socketIo(server, {
    cors: {
        origin: (origin, callback) => {
            // Use same CORS logic as Express
            if (!origin) {
                callback(null, true);
                return;
            }
            
            const isAllowed = allowedOrigins.some(allowed => {
                if (allowed === origin) return true;
                if (allowed === 'https://*.replit.dev') {
                    return /^https:\/\/[a-z0-9-]+\.replit\.dev$/.test(origin);
                }
                return false;
            });
            
            callback(null, isAllowed);
        },
        methods: ["GET", "POST"],
        credentials: true
    },
    transports: ['websocket', 'polling'], // Prefer websocket for better performance
    pingTimeout: 60000,
    pingInterval: 25000,
    connectTimeout: 45000,
    maxHttpBufferSize: 1e6 // 1MB buffer limit
});

// Health check endpoint
app.get('/api/status', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'Memory App Web Interface',
        timestamp: new Date().toISOString(),
        environment: process.env.NODE_ENV || 'development'
    });
});

// 🔒 CRITICAL SECURITY: JWT verification for Socket.IO
io.use((socket, next) => {
    const token = socket.handshake.auth.token;
    
    if (!token) {
        console.warn('🚫 Socket connection rejected: No JWT token provided');
        return next(new Error('Authentication required'));
    }
    
    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        socket.userId = decoded.userId;
        socket.username = decoded.username;
        console.log(`✅ Socket authenticated: ${decoded.username}`);
        next();
    } catch (error) {
        console.warn('🚫 Socket connection rejected: Invalid JWT token');
        next(new Error('Invalid authentication token'));
    }
});

// 🔧 BUG FIX: Disable rate limiting for development to fix authentication
if (process.env.NODE_ENV === 'production') {
    const limiter = rateLimit({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 100,
        message: { success: false, error: 'Too many requests from this IP, please try again later.' },
        standardHeaders: true,
        legacyHeaders: false
    });
    app.use('/api/', limiter);

    const authLimiter = rateLimit({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 5,
        skipSuccessfulRequests: true,
        message: { success: false, error: 'Too many login attempts, please try again later.' }
    });
    app.use('/api/auth/', authLimiter);
} else {
    console.log('📝 Rate limiting disabled for development');
}

// Optimized JSON parsing with size limits
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// 🔧 JSON Error Handling Middleware - Fixes critical parsing errors
app.use((err, req, res, next) => {
    if (err instanceof SyntaxError && 'body' in err && err.type === 'entity.parse.failed') {
        console.error(`🚨 JSON Parse Error on ${req.method} ${req.path}:`, err.message);
        console.error('Raw body causing error:', req.rawBody || 'undefined');
        return res.status(400).json({ 
            success: false, 
            error: 'Invalid JSON format in request body',
            details: 'Please check your request format and try again'
        });
    }
    next(err);
});

// Static file serving with NO caching for development
app.use(express.static('public', {
    maxAge: 0, // No caching for development
    etag: false,
    setHeaders: (res, path) => {
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
    }
}));

// File upload configuration with performance optimization
const upload = multer({
    dest: 'uploads/',
    limits: {
        fileSize: 5 * 1024 * 1024, // 5MB limit for better performance
        files: 5 // Maximum 5 files per request
    },
    fileFilter: (req, file, cb) => {
        // Allow only specific file types for security and performance
        const allowedTypes = /jpeg|jpg|png|gif|pdf|doc|docx|txt/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        const mimetype = allowedTypes.test(file.mimetype);
        
        if (mimetype && extname) {
            return cb(null, true);
        } else {
            cb(new Error('Invalid file type'));
        }
    }
});

// JWT Secret (use environment variable in production)
// 🔒 CRITICAL FIX: Use fixed JWT_SECRET for development to prevent token invalidation
let JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET) {
    if (process.env.NODE_ENV === 'production') {
        console.error('🚨 FATAL: JWT_SECRET environment variable MUST be set in production!');
        console.error('Application cannot start without proper JWT secret configuration.');
        process.exit(1);
    } else {
        // Use fixed secret for development to prevent token invalidation on restart
        JWT_SECRET = 'memory-app-dev-fixed-secret-2024-secure-token-key';
        process.env.JWT_SECRET = JWT_SECRET;
        console.log('🔑 Using fixed JWT_SECRET for development (prevents token invalidation on restart)');
    }
}

// Optimized in-memory stores with size limits for better performance
const sessions = new Map();
const connectedUsers = new Map(); // userId -> socketId
const promptHistory = new Map(); // userId -> array of generated prompts
const lastPromptDate = new Map(); // userId -> last prompt date
const MAX_SESSIONS = 10000; // Limit session storage
const MAX_CONNECTIONS = 5000; // Limit concurrent connections
const MAX_PROMPT_HISTORY = 100; // Keep last 100 prompts per user

// Cleanup function to prevent memory leaks
setInterval(() => {
    // Clean up old sessions (older than 24 hours)
    const dayAgo = Date.now() - (24 * 60 * 60 * 1000);
    for (const [sessionId, session] of sessions.entries()) {
        if (session.createdAt < dayAgo) {
            sessions.delete(sessionId);
        }
    }
    
    // Limit session count
    if (sessions.size > MAX_SESSIONS) {
        const oldestSessions = Array.from(sessions.entries())
            .sort((a, b) => a[1].createdAt - b[1].createdAt)
            .slice(0, sessions.size - MAX_SESSIONS);
        oldestSessions.forEach(([sessionId]) => sessions.delete(sessionId));
    }
}, 60 * 60 * 1000); // Run cleanup every hour

// Mock memory app interface (replace with actual Python integration)
class MemoryAppInterface {
    constructor() {
        this.users = new Map();
        this.memories = new Map();
        this.secrets = new Map();
        this.gamification = new Map();
    }

    async authenticateUser(username, password) {
        // Mock authentication - replace with actual voice auth integration
        const user = this.users.get(username);
        if (user && await bcrypt.compare(password, user.passwordHash)) {
            return {
                success: true,
                user: {
                    id: user.id,
                    username: user.username,
                    displayName: user.displayName,
                    email: user.email
                }
            };
        }
        return { success: false, message: 'Invalid credentials' };
    }

    async registerUser(userData) {
        const userId = uuid.v4();
        const passwordHash = await bcrypt.hash(userData.password, 10);
        
        const user = {
            id: userId,
            username: userData.username,
            displayName: userData.displayName,
            email: userData.email,
            passwordHash,
            createdAt: new Date().toISOString()
        };
        
        this.users.set(userData.username, user);
        
        // Initialize gamification
        this.gamification.set(userId, {
            level: 1,
            experience: 0,
            streak: 0,
            achievements: [],
            lastActive: new Date().toISOString()
        });

        return {
            success: true,
            user: {
                id: user.id,
                username: user.username,
                displayName: user.displayName,
                email: user.email
            }
        };
    }

    async getUserMemories(userId, category = 'all') {
        const userMemories = Array.from(this.memories.values())
            .filter(memory => memory.ownerId === userId && (category === 'all' || memory.category === category))
            .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        
        return {
            success: true,
            memories: userMemories,
            count: userMemories.length
        };
    }

    async createMemory(userId, memoryData) {
        const memoryId = uuid.v4();
        const memory = {
            id: memoryId,
            ownerId: userId,
            content: memoryData.content,
            category: memoryData.category || 'general',
            participants: memoryData.participants || [],
            createdAt: new Date().toISOString(),
            platform: 'web'
        };

        this.memories.set(memoryId, memory);
        
        // Award experience points
        await this.addExperience(userId, 'store_memory');

        return {
            success: true,
            memory: memory,
            memoryNumber: memoryId.slice(-6)
        };
    }

    async getUserSecrets(userId) {
        const userSecrets = Array.from(this.secrets.values())
            .filter(secret => secret.ownerId === userId || secret.designatedPersonId === userId)
            .map(secret => ({
                id: secret.id,
                title: secret.title,
                isOwner: secret.ownerId === userId,
                designatedPerson: secret.designatedPersonName,
                createdAt: secret.createdAt,
                isRomantic: secret.isRomantic
            }));

        return {
            success: true,
            secrets: userSecrets,
            count: userSecrets.length
        };
    }

    async createSecret(userId, secretData) {
        const secretId = uuid.v4();
        const secret = {
            id: secretId,
            ownerId: userId,
            title: secretData.title,
            content: secretData.content,
            designatedPersonId: secretData.designatedPersonId,
            designatedPersonName: secretData.designatedPersonName,
            isRomantic: secretData.isRomantic || false,
            createdAt: new Date().toISOString(),
            accessCount: 0
        };

        this.secrets.set(secretId, secret);
        
        // Check for mutual feelings
        const mutualMatch = await this.checkMutualFeelings(userId, secretData.designatedPersonId);
        
        // Award experience points
        await this.addExperience(userId, 'create_secret');
        
        if (mutualMatch.found) {
            await this.addExperience(userId, 'mutual_match');
            await this.addExperience(secretData.designatedPersonId, 'mutual_match');
        }

        return {
            success: true,
            secret: secret,
            mutualMatch: mutualMatch
        };
    }

    async checkMutualFeelings(userId, targetUserId) {
        // Check if both users have romantic secrets about each other
        const userSecret = Array.from(this.secrets.values())
            .find(s => s.ownerId === userId && s.designatedPersonId === targetUserId && s.isRomantic);
        
        const targetSecret = Array.from(this.secrets.values())
            .find(s => s.ownerId === targetUserId && s.designatedPersonId === userId && s.isRomantic);

        if (userSecret && targetSecret) {
            return {
                found: true,
                userSecretId: userSecret.id,
                targetSecretId: targetSecret.id,
                message: "💕 Mutual feelings detected! You can now communicate through AI Avatars."
            };
        }

        return { found: false };
    }

    async getUserStats(userId) {
        const userStats = this.gamification.get(userId) || {
            level: 1,
            experience: 0,
            streak: 0,
            achievements: [],
            lastActive: new Date().toISOString()
        };

        const memories = Array.from(this.memories.values())
            .filter(m => m.ownerId === userId);
        
        const secrets = Array.from(this.secrets.values())
            .filter(s => s.ownerId === userId);

        return {
            success: true,
            stats: {
                level: userStats.level,
                experience: userStats.experience,
                streak: userStats.streak,
                achievements: userStats.achievements,
                totalMemories: memories.length,
                totalSecrets: secrets.length,
                lastActive: userStats.lastActive
            }
        };
    }

    async addExperience(userId, activityType) {
        const experiencePoints = {
            'store_memory': 5,
            'create_secret': 15,
            'mutual_match': 25,
            'avatar_message': 10,
            'daily_login': 2
        };

        const stats = this.gamification.get(userId) || {
            level: 1,
            experience: 0,
            streak: 0,
            achievements: [],
            lastActive: new Date().toISOString()
        };

        const points = experiencePoints[activityType] || 1;
        stats.experience += points;
        stats.lastActive = new Date().toISOString();

        // Level up check
        const requiredExp = stats.level * 100;
        if (stats.experience >= requiredExp) {
            stats.level += 1;
            stats.experience -= requiredExp;
            
            // Emit level up notification
            this.emitNotification(userId, {
                type: 'level_up',
                title: `🎉 Level ${stats.level}!`,
                message: `Congratulations! You've reached level ${stats.level}!`,
                urgent: false
            });
        }

        this.gamification.set(userId, stats);
        return stats;
    }

    emitNotification(userId, notification) {
        const socketId = connectedUsers.get(userId);
        if (socketId) {
            io.to(socketId).emit('notification', {
                id: uuid.v4(),
                ...notification,
                timestamp: new Date().toISOString()
            });
        }
    }
}

const memoryApp = new MemoryAppInterface();

// Authentication middleware
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(401).json({ error: 'Access token required' });
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            return res.status(403).json({ error: 'Invalid token' });
        }
        req.user = user;
        next();
    });
};

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Authentication routes
app.post('/api/auth/register', async (req, res) => {
    try {
        const { username, password, displayName, email } = req.body;
        
        if (!username || !password || !displayName) {
            return res.status(400).json({ error: 'Missing required fields' });
        }

        const result = await memoryApp.registerUser({
            username,
            password,
            displayName,
            email
        });

        if (result.success) {
            console.log('✅ Registration successful, creating token...');
            const token = jwt.sign(
                { userId: result.user.id, username: result.user.username },
                JWT_SECRET,
                { expiresIn: '24h' }
            );

            res.json({
                success: true,
                token,
                user: result.user
            });
        } else {
            console.log('❌ Registration failed:', result);
            res.status(400).json(result);
        }
    } catch (error) {
        console.error('💥 Registration exception:', error);
        res.status(500).json({ error: 'Registration failed: ' + error.message });
    }
});

app.post('/api/auth/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        
        const result = await memoryApp.authenticateUser(username, password);
        
        if (result.success) {
            const token = jwt.sign(
                { userId: result.user.id, username: result.user.username },
                JWT_SECRET,
                { expiresIn: '24h' }
            );

            res.json({
                success: true,
                token,
                user: result.user
            });
        } else {
            res.status(401).json(result);
        }
    } catch (error) {
        res.status(500).json({ error: 'Login failed' });
    }
});

// Memory routes
app.get('/api/memories', authenticateToken, async (req, res) => {
    try {
        const { category } = req.query;
        const result = await memoryApp.getUserMemories(req.user.userId, category);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch memories' });
    }
});

app.post('/api/memories', authenticateToken, async (req, res) => {
    try {
        const result = await memoryApp.createMemory(req.user.userId, req.body);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to create memory' });
    }
});

// Secret memory routes
app.get('/api/secrets', authenticateToken, async (req, res) => {
    try {
        const result = await memoryApp.getUserSecrets(req.user.userId);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch secrets' });
    }
});

app.post('/api/secrets', authenticateToken, async (req, res) => {
    try {
        const secretData = {
            ...req.body,
            designatedPersonId: req.body.designatedPersonId || req.user.userId
        };
        const result = await memoryApp.createSecret(req.user.userId, secretData);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to create secret' });
    }
});

// Gamification routes
app.get('/api/stats', authenticateToken, async (req, res) => {
    try {
        const result = await memoryApp.getUserStats(req.user.userId);
        res.json(result);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch stats' });
    }
});

// 🌟 AI Memory Prompts - Personalized daily reflection prompts
app.get('/api/ai/daily-prompt', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        const today = new Date().toDateString();
        
        // Check if user already has a prompt for today
        const lastPrompt = lastPromptDate.get(userId);
        const userPromptHistory = promptHistory.get(userId) || [];
        
        if (lastPrompt === today && userPromptHistory.length > 0) {
            // Return today's existing prompt
            const todayPrompt = userPromptHistory[userPromptHistory.length - 1];
            return res.json({
                success: true,
                prompt: todayPrompt,
                isNew: false
            });
        }
        
        // Get user's memory history for context
        const memoriesResult = await memoryApp.getUserMemories(userId);
        const memories = memoriesResult.memories || [];
        
        // Analyze memory patterns
        const memoryAnalysis = analyzeMemoryPatterns(memories, userPromptHistory);
        
        // Generate personalized prompt using OpenAI
        const promptResponse = await openai.chat.completions.create({
            model: 'gpt-5',
            max_completion_tokens: 200,
            messages: [
                {
                    role: 'system',
                    content: `You are a thoughtful AI companion helping users reflect on their life journey. Generate a personalized memory prompt based on their history.
                    
                    Guidelines:
                    - Be warm, encouraging, and personal
                    - Reference specific past memories when relevant
                    - Encourage exploration of underrepresented categories
                    - Celebrate anniversaries and milestones
                    - Use seasonal/timely references when appropriate
                    - Keep prompts concise (1-2 sentences)
                    - Make the user feel seen and understood
                    - Avoid repeating recent prompts`
                },
                {
                    role: 'user',
                    content: `Generate a personalized memory prompt based on this analysis:
                    
                    Memory Stats:
                    - Total memories: ${memoryAnalysis.totalMemories}
                    - Most recent: ${memoryAnalysis.mostRecent}
                    - Least used category: ${memoryAnalysis.leastUsedCategory}
                    - Anniversary memories: ${memoryAnalysis.anniversaries}
                    - Common themes: ${memoryAnalysis.themes.join(', ')}
                    - Days since last memory: ${memoryAnalysis.daysSinceLastMemory}
                    - Current season: ${memoryAnalysis.season}
                    - Recent prompts to avoid: ${memoryAnalysis.recentPrompts.join('; ')}
                    
                    ${memoryAnalysis.specialContext}`
                }
            ]
        });
        
        const generatedPrompt = {
            id: uuid.v4(),
            text: promptResponse.choices[0].message.content.trim(),
            category: memoryAnalysis.suggestedCategory,
            generatedAt: new Date().toISOString(),
            context: memoryAnalysis.promptContext,
            type: memoryAnalysis.promptType
        };
        
        // Store prompt in history
        userPromptHistory.push(generatedPrompt);
        if (userPromptHistory.length > MAX_PROMPT_HISTORY) {
            userPromptHistory.shift(); // Remove oldest prompt
        }
        promptHistory.set(userId, userPromptHistory);
        lastPromptDate.set(userId, today);
        
        res.json({
            success: true,
            prompt: generatedPrompt,
            isNew: true
        });
        
    } catch (error) {
        console.error('Error generating AI prompt:', error);
        
        // Fallback to a generic but thoughtful prompt
        const fallbackPrompts = [
            "What small moment from today would you like to remember?",
            "Who made you smile recently, and why?",
            "What's something you're grateful for this week?",
            "Describe a place that brought you peace lately.",
            "What accomplishment, big or small, are you proud of?",
            "Share a moment when you felt truly yourself.",
            "What's a lesson you learned recently?",
            "Describe a beautiful thing you noticed today."
        ];
        
        const randomPrompt = fallbackPrompts[Math.floor(Math.random() * fallbackPrompts.length)];
        
        res.json({
            success: true,
            prompt: {
                id: uuid.v4(),
                text: randomPrompt,
                category: 'general',
                generatedAt: new Date().toISOString(),
                type: 'fallback'
            },
            isNew: true
        });
    }
});

// Helper function to analyze memory patterns
function analyzeMemoryPatterns(memories, promptHistory) {
    const now = new Date();
    const categories = { general: 0, work: 0, family: 0, personal: 0 };
    const themes = [];
    const anniversaries = [];
    
    // Analyze memories
    memories.forEach(memory => {
        if (memory.category) {
            categories[memory.category] = (categories[memory.category] || 0) + 1;
        }
        
        // Check for anniversaries (1 week, 1 month, 1 year ago)
        const memoryDate = new Date(memory.createdAt);
        const daysDiff = Math.floor((now - memoryDate) / (1000 * 60 * 60 * 24));
        
        if (daysDiff === 7) {
            anniversaries.push(`One week ago: "${memory.content.substring(0, 50)}..."`);
        } else if (daysDiff === 30) {
            anniversaries.push(`One month ago: "${memory.content.substring(0, 50)}..."`);
        } else if (daysDiff === 365) {
            anniversaries.push(`One year ago: "${memory.content.substring(0, 50)}..."`);
        }
        
        // Extract themes (simple keyword analysis)
        const keywords = memory.content.toLowerCase().match(/\b(family|love|work|travel|food|friend|happy|grateful|challenge|growth|learn)\b/g);
        if (keywords) {
            themes.push(...keywords);
        }
    });
    
    // Find least used category
    const leastUsedCategory = Object.entries(categories)
        .sort((a, b) => a[1] - b[1])[0][0];
    
    // Calculate days since last memory
    const mostRecentMemory = memories[0];
    const daysSinceLastMemory = mostRecentMemory 
        ? Math.floor((now - new Date(mostRecentMemory.createdAt)) / (1000 * 60 * 60 * 24))
        : 999;
    
    // Get current season
    const month = now.getMonth();
    const season = month >= 2 && month <= 4 ? 'spring' :
                  month >= 5 && month <= 7 ? 'summer' :
                  month >= 8 && month <= 10 ? 'autumn' : 'winter';
    
    // Get recent prompts to avoid repetition
    const recentPrompts = promptHistory.slice(-5).map(p => p.text.substring(0, 30));
    
    // Determine prompt type and context
    let promptType = 'general';
    let promptContext = '';
    let specialContext = '';
    
    if (anniversaries.length > 0) {
        promptType = 'anniversary';
        promptContext = anniversaries[0];
        specialContext = `Anniversary reflection opportunity: ${anniversaries[0]}`;
    } else if (daysSinceLastMemory > 7) {
        promptType = 'reengagement';
        specialContext = `User hasn't created a memory in ${daysSinceLastMemory} days. Encourage gentle re-engagement.`;
    } else if (categories[leastUsedCategory] === 0) {
        promptType = 'exploration';
        specialContext = `User has never created a ${leastUsedCategory} memory. Gently encourage exploration.`;
    } else {
        promptType = 'themed';
        const topTheme = themes.length > 0 ? 
            themes.sort((a, b) => themes.filter(t => t === b).length - themes.filter(t => t === a).length)[0] : 
            'general';
        specialContext = `User frequently writes about ${topTheme}. Build on this interest.`;
    }
    
    return {
        totalMemories: memories.length,
        mostRecent: mostRecentMemory ? mostRecentMemory.content.substring(0, 50) : 'none',
        leastUsedCategory,
        anniversaries: anniversaries.slice(0, 3),
        themes: [...new Set(themes)].slice(0, 5),
        daysSinceLastMemory,
        season,
        recentPrompts,
        promptType,
        promptContext,
        specialContext,
        suggestedCategory: leastUsedCategory
    };
}

// Skip today's prompt
app.post('/api/ai/skip-prompt', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        const { promptId } = req.body;
        
        // Mark prompt as skipped
        const userPromptHistory = promptHistory.get(userId) || [];
        const prompt = userPromptHistory.find(p => p.id === promptId);
        if (prompt) {
            prompt.skipped = true;
            prompt.skippedAt = new Date().toISOString();
        }
        
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: 'Failed to skip prompt' });
    }
});

// Premium subscription endpoints
app.get('/api/subscription/plans', (req, res) => {
    const plans = {
        free: {
            tier: 'free',
            price_monthly: '0.00',
            price_yearly: '0.00',
            features: [],
            memory_limit: 100,
            avatar_voices: 1,
            priority_support: false,
            beta_access: false
        },
        basic: {
            tier: 'basic',
            price_monthly: '9.99',
            price_yearly: '99.99',
            features: ['unlimited_memories', 'advanced_analytics', 'export_backup'],
            memory_limit: null,
            avatar_voices: 3,
            priority_support: false,
            beta_access: false,
            savings_yearly: '19.89'
        },
        pro: {
            tier: 'pro',
            price_monthly: '19.99',
            price_yearly: '199.99',
            features: ['unlimited_memories', 'ai_voice_cloning', 'custom_avatars', 'advanced_analytics', 'family_sharing', 'export_backup', 'priority_support'],
            memory_limit: null,
            avatar_voices: 10,
            priority_support: true,
            beta_access: false,
            savings_yearly: '39.89'
        },
        elite: {
            tier: 'elite',
            price_monthly: '39.99',
            price_yearly: '399.99',
            features: ['unlimited_memories', 'ai_voice_cloning', 'custom_avatars', 'advanced_analytics', 'family_sharing', 'export_backup', 'priority_support', 'beta_access'],
            memory_limit: null,
            avatar_voices: 50,
            priority_support: true,
            beta_access: true,
            savings_yearly: '79.89'
        }
    };
    
    res.json({ plans });
});

app.post('/api/subscription/checkout', authenticateToken, async (req, res) => {
    try {
        const { tier, billing_cycle = 'monthly' } = req.body;
        const userId = req.user.userId;
        
        const checkoutSession = {
            success: true,
            checkout_url: `https://checkout.stripe.com/pay/cs_test_mock_${Date.now()}`,
            session_id: `cs_test_${Date.now()}`,
            plan_details: {
                tier,
                price: billing_cycle === 'yearly' ? '99.99' : '9.99',
                billing_cycle,
                features: ['unlimited_memories', 'advanced_analytics']
            }
        };
        
        res.json(checkoutSession);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/subscription/status', authenticateToken, (req, res) => {
    const status = {
        tier: 'free',
        active: false,
        features: [],
        expires_at: null,
        upgrade_available: true,
        memory_limit: 100,
        avatar_voices: 1,
        priority_support: false,
        beta_access: false
    };
    
    res.json(status);
});

app.post('/api/premium/avatar-chat', authenticateToken, async (req, res) => {
    try {
        const { message } = req.body;
        const response = {
            success: true,
            avatar_name: 'AI Assistant',
            response: 'Hello! I\'m your premium AI Avatar. I can help you with personalized insights and advanced memory analysis. What would you like to explore today?',
            personality_used: 'empathetic_intelligent',
            emotional_intelligence: 0.85
        };
        
        res.json(response);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/premium/analytics', authenticateToken, async (req, res) => {
    try {
        const analytics = {
            success: true,
            premium_insights: {
                relationship_patterns: {
                    strongest_connections: ['Family', 'Close Friends'],
                    communication_frequency: 'High',
                    emotional_support_network: 'Strong'
                },
                memory_quality_score: 8.5,
                emotional_trends: {
                    happiness_trend: 'Increasing',
                    stress_indicators: 'Low',
                    overall_wellbeing: 'Positive'
                },
                personalized_recommendations: [
                    'Consider scheduling more family time based on your memory patterns',
                    'Your work-life balance appears optimal',
                    'Strong social connections detected - maintain these relationships'
                ]
            },
            generated_at: new Date().toISOString(),
            subscription_tier: 'pro'
        };
        
        res.json(analytics);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// 🧠 AI-POWERED RELATIONSHIP INSIGHTS SYSTEM
// Revolutionary AI analysis for relationship intelligence

async function analyzeRelationshipPatterns(userId, memories) {
    try {
        // Extract memory content for analysis
        const memoryTexts = memories.map(m => m.content).join('\n');
        
        const prompt = `Analyze these personal memories for relationship insights. Provide actionable relationship intelligence in JSON format:

Memory Content:
${memoryTexts}

Respond with JSON containing:
{
  "relationshipHealth": {
    "score": 1-100,
    "summary": "brief assessment"
  },
  "keyInsights": [
    "insight 1",
    "insight 2",
    "insight 3"
  ],
  "relationshipPatterns": {
    "communication": "analysis",
    "emotional": "analysis", 
    "growth": "analysis"
  },
  "actionableAdvice": [
    "specific suggestion 1",
    "specific suggestion 2"
  ],
  "riskFactors": ["any concerning patterns"],
  "strengthAreas": ["positive relationship aspects"]
}`;

        const response = await openai.chat.completions.create({
            model: "gpt-5", // the newest OpenAI model is "gpt-5" which was released August 7, 2025
            messages: [
                {
                    role: "system",
                    content: "You are a relationship psychology expert. Analyze memory patterns to provide meaningful relationship insights while being supportive and constructive."
                },
                {
                    role: "user", 
                    content: prompt
                }
            ],
            response_format: { type: "json_object" },
            max_completion_tokens: 2000
        });

        return JSON.parse(response.choices[0].message.content);
    } catch (error) {
        console.error('AI Relationship Analysis Error:', error);
        return {
            relationshipHealth: { score: 50, summary: "Analysis temporarily unavailable" },
            keyInsights: ["AI analysis will be available shortly"],
            relationshipPatterns: {},
            actionableAdvice: ["Keep documenting your memories"],
            riskFactors: [],
            strengthAreas: ["Active memory documentation"]
        };
    }
}

// AI Relationship Insights API Endpoint
app.get('/api/ai/relationship-insights', authenticateToken, async (req, res) => {
    try {
        console.log(`🧠 Generating AI relationship insights for user ${req.user.username}`);
        
        // Get user memories for analysis
        const memoriesResult = await memoryApp.getUserMemories(req.user.userId);
        
        if (!memoriesResult.success || memoriesResult.memories.length === 0) {
            return res.json({
                success: true,
                insights: {
                    relationshipHealth: { score: 0, summary: "No memories to analyze yet" },
                    keyInsights: ["Start documenting your memories to receive AI insights"],
                    message: "Add some memories to unlock AI relationship intelligence!"
                }
            });
        }

        const aiInsights = await analyzeRelationshipPatterns(req.user.userId, memoriesResult.memories);
        
        res.json({
            success: true,
            insights: aiInsights,
            generatedAt: new Date().toISOString()
        });

    } catch (error) {
        console.error('❌ AI Insights Error:', error);
        res.status(500).json({ 
            success: false, 
            error: 'Failed to generate AI insights' 
        });
    }
});

// AI Memory Analysis for Smart Recommendations
app.post('/api/ai/analyze-memory', authenticateToken, async (req, res) => {
    try {
        const { content, category } = req.body;
        
        const prompt = `Analyze this memory entry and provide smart insights:

Memory: "${content}"
Category: ${category}

Provide analysis in JSON format:
{
  "sentiment": {
    "score": 1-10,
    "emotion": "primary emotion",
    "tone": "overall tone"
  },
  "themes": ["key themes"],
  "relationships_mentioned": ["people/relationships referenced"],
  "suggested_tags": ["relevant tags"],
  "follow_up_questions": ["questions to deepen reflection"],
  "memory_value": {
    "significance": 1-10,
    "emotional_weight": 1-10,
    "relationship_impact": 1-10
  }
}`;

        const response = await openai.chat.completions.create({
            model: "gpt-5", // the newest OpenAI model is "gpt-5" which was released August 7, 2025
            messages: [
                {
                    role: "system",
                    content: "You are a memory analysis expert. Provide insightful analysis of personal memories."
                },
                {
                    role: "user",
                    content: prompt
                }
            ],
            response_format: { type: "json_object" }
        });

        const analysis = JSON.parse(response.choices[0].message.content);
        
        res.json({
            success: true,
            analysis,
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('❌ Memory Analysis Error:', error);
        res.status(500).json({ 
            success: false, 
            error: 'Failed to analyze memory' 
        });
    }
});

// 💳 PREMIUM SUBSCRIPTION SYSTEM - Revolutionary monetization

// Subscription tiers configuration
const SUBSCRIPTION_TIERS = {
    FREE: {
        name: 'Free',
        price: 0,
        priceId: null,
        features: {
            memories: 50,
            aiInsights: 5,
            storage: '100MB',
            categories: 4,
            avatarMessages: 0,
            emergencyContacts: 1,
            voiceCloning: false,
            prioritySupport: false
        }
    },
    BASIC: {
        name: 'Basic',
        price: 4.99,
        priceId: 'price_basic_monthly',
        features: {
            memories: 500,
            aiInsights: 50,
            storage: '1GB',
            categories: 8,
            avatarMessages: 10,
            emergencyContacts: 3,
            voiceCloning: false,
            prioritySupport: false
        }
    },
    PRO: {
        name: 'Pro',
        price: 9.99,
        priceId: 'price_pro_monthly',
        features: {
            memories: -1, // unlimited
            aiInsights: 200,
            storage: '10GB',
            categories: -1, // unlimited
            avatarMessages: 100,
            emergencyContacts: 10,
            voiceCloning: true,
            prioritySupport: true
        }
    },
    ELITE: {
        name: 'Elite',
        price: 19.99,
        priceId: 'price_elite_monthly',
        features: {
            memories: -1, // unlimited
            aiInsights: -1, // unlimited
            storage: '100GB',
            categories: -1, // unlimited
            avatarMessages: -1, // unlimited
            emergencyContacts: -1, // unlimited
            voiceCloning: true,
            prioritySupport: true,
            customAvatars: true,
            familySharing: true,
            betaAccess: true
        }
    }
};

// Premium subscription endpoints
app.get('/api/subscription/tiers', (req, res) => {
    res.json({
        success: true,
        tiers: SUBSCRIPTION_TIERS
    });
});

app.get('/api/subscription/status', authenticateToken, async (req, res) => {
    try {
        const user = await memoryApp.getUser(req.user.userId);
        const currentTier = user.subscriptionTier || 'FREE';
        
        res.json({
            success: true,
            subscription: {
                tier: currentTier,
                features: SUBSCRIPTION_TIERS[currentTier].features,
                usage: {
                    memories: user.memoryCount || 0,
                    aiInsights: user.aiInsightsUsed || 0,
                    storage: user.storageUsed || 0
                }
            }
        });
    } catch (error) {
        res.status(500).json({ error: 'Failed to get subscription status' });
    }
});

app.post('/api/subscription/upgrade', authenticateToken, async (req, res) => {
    try {
        const { tier } = req.body;
        
        if (!SUBSCRIPTION_TIERS[tier]) {
            return res.status(400).json({ error: 'Invalid subscription tier' });
        }
        
        if (tier === 'FREE') {
            return res.status(400).json({ error: 'Cannot downgrade via this endpoint' });
        }
        
        // For now, simulate subscription upgrade
        // In production, this would integrate with Stripe
        const result = await memoryApp.upgradeSubscription(req.user.userId, tier);
        
        res.json({
            success: true,
            message: `Successfully upgraded to ${tier}`,
            subscription: {
                tier: tier,
                features: SUBSCRIPTION_TIERS[tier].features
            }
        });
        
    } catch (error) {
        res.status(500).json({ error: 'Failed to upgrade subscription' });
    }
});

// Premium AI features endpoint  
app.get('/api/ai/premium-insights', authenticateToken, async (req, res) => {
    try {
        const user = await memoryApp.getUser(req.user.userId);
        const currentTier = user.subscriptionTier || 'FREE';
        const tierFeatures = SUBSCRIPTION_TIERS[currentTier].features;
        
        // Check if user has AI insights quota
        const aiInsightsUsed = user.aiInsightsUsed || 0;
        if (tierFeatures.aiInsights !== -1 && aiInsightsUsed >= tierFeatures.aiInsights) {
            return res.status(403).json({
                error: 'AI insights quota exceeded',
                upgrade: true,
                message: 'Upgrade your subscription to unlock more AI insights'
            });
        }
        
        // Premium AI analysis with deeper insights
        const memoriesResult = await memoryApp.getUserMemories(req.user.userId);
        
        if (!memoriesResult.success || memoriesResult.memories.length === 0) {
            return res.json({
                success: true,
                insights: {
                    type: 'premium',
                    message: 'Create more memories to unlock premium AI insights',
                    recommendations: ['Document daily experiences', 'Share meaningful moments']
                }
            });
        }
        
        const premiumInsights = await generatePremiumAIInsights(req.user.userId, memoriesResult.memories, currentTier);
        
        // Track usage
        await memoryApp.incrementAIInsightsUsage(req.user.userId);
        
        res.json({
            success: true,
            insights: premiumInsights,
            tier: currentTier,
            remainingInsights: tierFeatures.aiInsights === -1 ? -1 : tierFeatures.aiInsights - aiInsightsUsed - 1
        });
        
    } catch (error) {
        console.error('Premium AI Insights Error:', error);
        res.status(500).json({ error: 'Failed to generate premium insights' });
    }
});

async function generatePremiumAIInsights(userId, memories, tier) {
    try {
        const memoryTexts = memories.map(m => m.content).join('\n');
        
        let analysisDepth = 'basic';
        if (tier === 'PRO') analysisDepth = 'advanced';
        if (tier === 'ELITE') analysisDepth = 'comprehensive';
        
        const prompt = `Provide ${analysisDepth} premium relationship and personal development insights:

Memory Content:
${memoryTexts}

Generate premium insights in JSON format:
{
  "personalGrowthTrajectory": {
    "currentPhase": "assessment of personal development stage",
    "growthAreas": ["specific areas for improvement"],
    "strengths": ["key personal strengths identified"]
  },
  "relationshipDynamics": {
    "communicationStyle": "detailed analysis",
    "attachmentPattern": "assessment",
    "conflictResolution": "evaluation"
  },
  "futureRecommendations": {
    "shortTerm": ["next 30 days actions"],
    "mediumTerm": ["next 90 days goals"],
    "longTerm": ["annual vision"]
  },
  "premiumInsights": [
    "exclusive insight 1",
    "exclusive insight 2",
    "exclusive insight 3"
  ],
  "personalizationLevel": "${tier.toLowerCase()}"
}`;

        const response = await openai.chat.completions.create({
            model: "gpt-5", // the newest OpenAI model is "gpt-5" which was released August 7, 2025
            messages: [
                {
                    role: "system",
                    content: "You are a premium AI relationship and personal development expert providing detailed, actionable insights for subscription users."
                },
                {
                    role: "user",
                    content: prompt
                }
            ],
            response_format: { type: "json_object" },
            max_completion_tokens: 3000
        });

        return JSON.parse(response.choices[0].message.content);
    } catch (error) {
        console.error('Premium AI Analysis Error:', error);
        return {
            personalGrowthTrajectory: { currentPhase: "Analysis in progress" },
            relationshipDynamics: { communicationStyle: "Premium analysis temporarily unavailable" },
            futureRecommendations: { shortTerm: ["Continue documenting memories"] },
            premiumInsights: ["Premium AI analysis will be available shortly"],
            personalizationLevel: tier.toLowerCase()
        };
    }
}

// 🌍 REVOLUTIONARY SOCIAL PLATFORM APIS - Ultimate Social Experience

// Social statistics endpoint
app.get('/api/social/stats', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Get user's social statistics
        const stats = {
            connections: 0,
            sharedMemories: 0,
            mutualMatches: 0
        };
        
        // In production, these would be actual database queries
        // For now, returning demo data
        
        res.json({
            success: true,
            stats: stats
        });
    } catch (error) {
        console.error('Social stats error:', error);
        res.status(500).json({ error: 'Failed to load social statistics' });
    }
});

// Get user connections
app.get('/api/social/connections', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // In production, this would query a connections table
        const connections = [
            {
                id: 'conn_1',
                displayName: 'Sarah Johnson',
                status: 'Connected',
                connectedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString() // 7 days ago
            },
            {
                id: 'conn_2', 
                displayName: 'Michael Chen',
                status: 'Connected',
                connectedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString() // 2 days ago
            }
        ];
        
        res.json({
            success: true,
            connections: connections
        });
    } catch (error) {
        console.error('Connections error:', error);
        res.status(500).json({ error: 'Failed to load connections' });
    }
});

// Search for potential connections
app.post('/api/social/search', authenticateToken, async (req, res) => {
    try {
        const { query } = req.body;
        const userId = req.user.userId;
        
        if (!query || query.length < 2) {
            return res.json({
                success: true,
                results: []
            });
        }
        
        // Demo search results - in production would query user database
        const searchResults = [
            {
                id: 'user_search_1',
                displayName: 'Emily Rodriguez',
                interests: 'Travel, Photography, Family memories',
                location: 'San Francisco, CA'
            },
            {
                id: 'user_search_2',
                displayName: 'David Kim',
                interests: 'Music, Relationships, Personal growth',
                location: 'New York, NY'
            },
            {
                id: 'user_search_3',
                displayName: 'Lisa Thompson',
                interests: 'Art, Writing, Life experiences',
                location: 'Austin, TX'
            }
        ].filter(person => 
            person.displayName.toLowerCase().includes(query.toLowerCase()) ||
            person.interests.toLowerCase().includes(query.toLowerCase()) ||
            person.location.toLowerCase().includes(query.toLowerCase())
        );
        
        res.json({
            success: true,
            results: searchResults
        });
    } catch (error) {
        console.error('Search error:', error);
        res.status(500).json({ error: 'Search failed' });
    }
});

// Send connection request
app.post('/api/social/connect', authenticateToken, async (req, res) => {
    try {
        const { targetUserId } = req.body;
        const userId = req.user.userId;
        
        if (userId === targetUserId) {
            return res.status(400).json({ error: 'Cannot connect to yourself' });
        }
        
        // In production, this would:
        // 1. Check if connection already exists
        // 2. Create connection request
        // 3. Send notification to target user
        
        console.log(`Connection request from ${userId} to ${targetUserId}`);
        
        res.json({
            success: true,
            message: 'Connection request sent successfully'
        });
    } catch (error) {
        console.error('Connection request error:', error);
        res.status(500).json({ error: 'Failed to send connection request' });
    }
});

// Share memory with social network
app.post('/api/social/share-memory', authenticateToken, async (req, res) => {
    try {
        const { memoryId, visibility, message } = req.body;
        const userId = req.user.userId;
        
        if (!memoryId) {
            return res.status(400).json({ error: 'Memory ID is required' });
        }
        
        // Verify user owns the memory
        const memory = await memoryApp.getMemory(userId, memoryId);
        if (!memory.success) {
            return res.status(404).json({ error: 'Memory not found' });
        }
        
        // In production, this would:
        // 1. Create a shared memory record
        // 2. Set appropriate visibility permissions
        // 3. Notify relevant users based on visibility setting
        // 4. Update user's social stats
        
        console.log(`Memory ${memoryId} shared by ${userId} with ${visibility} visibility`);
        
        res.json({
            success: true,
            message: 'Memory shared successfully',
            sharedMemory: {
                id: `shared_${Date.now()}`,
                originalMemoryId: memoryId,
                visibility: visibility,
                message: message,
                sharedAt: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('Share memory error:', error);
        res.status(500).json({ error: 'Failed to share memory' });
    }
});

// Check mutual feelings
app.get('/api/social/mutual-feelings', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // In production, this would analyze super secret memories
        // for romantic content and match with other users
        
        // Demo mutual feelings - using existing super secret functionality
        const secretMemoriesResult = await memoryApp.getSecretMemories(userId);
        let mutualFeelings = [];
        
        if (secretMemoriesResult.success && secretMemoriesResult.secrets.length > 0) {
            // Check for romantic content in memories
            const romanticMemories = secretMemoriesResult.secrets.filter(secret => 
                secret.isRomantic || 
                secret.content.toLowerCase().includes('love') ||
                secret.content.toLowerCase().includes('feelings') ||
                secret.content.toLowerCase().includes('romantic')
            );
            
            // Demo: If user has romantic memories, show demo mutual match
            if (romanticMemories.length > 0) {
                mutualFeelings = [
                    {
                        personId: 'demo_match_1',
                        personName: 'Alex Rivera',
                        detectedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
                        confidenceScore: 0.92
                    }
                ];
            }
        }
        
        res.json({
            success: true,
            feelings: mutualFeelings
        });
    } catch (error) {
        console.error('Mutual feelings error:', error);
        res.status(500).json({ error: 'Failed to check mutual feelings' });
    }
});

// Avatar system endpoints
app.post('/api/avatar/activate', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // In production, this would:
        // 1. Mark user's avatar as active
        // 2. Start matching with other active avatars
        // 3. Initialize AI conversation capabilities
        
        console.log(`Avatar activated for user ${userId}`);
        
        res.json({
            success: true,
            message: 'Avatar activated successfully',
            avatar: {
                status: 'active',
                activatedAt: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('Avatar activation error:', error);
        res.status(500).json({ error: 'Failed to activate avatar' });
    }
});

app.post('/api/avatar/deactivate', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        console.log(`Avatar deactivated for user ${userId}`);
        
        res.json({
            success: true,
            message: 'Avatar deactivated'
        });
    } catch (error) {
        console.error('Avatar deactivation error:', error);
        res.status(500).json({ error: 'Failed to deactivate avatar' });
    }
});

app.get('/api/avatar/conversations', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Demo avatar conversations
        const conversations = [
            {
                id: 'conv_1',
                otherUserId: 'demo_user_1',
                otherUserName: 'Emma Watson',
                lastMessage: 'Your avatar shared a beautiful memory about family traditions. My avatar found it deeply meaningful.',
                lastMessageAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
                status: 'active'
            },
            {
                id: 'conv_2',
                otherUserId: 'demo_user_2', 
                otherUserName: 'James Patterson',
                lastMessage: 'Our avatars discussed the importance of preserving memories for future generations.',
                lastMessageAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(), // 6 hours ago
                status: 'active'
            }
        ];
        
        res.json({
            success: true,
            conversations: conversations
        });
    } catch (error) {
        console.error('Avatar conversations error:', error);
        res.status(500).json({ error: 'Failed to load avatar conversations' });
    }
});

// 🔔 REVOLUTIONARY SMART NOTIFICATION SYSTEM APIS - AI-Powered Intelligence

// Get notification preferences
app.get('/api/notifications/preferences', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Default notification preferences
        const defaultPreferences = {
            'memory-reminders': true,
            'relationship-insights': true,
            'social-updates': true,
            'avatar-activity': true,
            'emergency-alerts': true
        };
        
        // In production, this would fetch from database
        res.json({
            success: true,
            preferences: defaultPreferences
        });
    } catch (error) {
        console.error('Notification preferences error:', error);
        res.status(500).json({ error: 'Failed to load notification preferences' });
    }
});

// Update notification preferences
app.post('/api/notifications/preferences', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        const preferences = req.body;
        
        // In production, this would save to database
        console.log(`Updating notification preferences for user ${userId}:`, preferences);
        
        res.json({
            success: true,
            message: 'Notification preferences updated successfully'
        });
    } catch (error) {
        console.error('Update preferences error:', error);
        res.status(500).json({ error: 'Failed to update notification preferences' });
    }
});

// Get recent notifications
app.get('/api/notifications/recent', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Demo notifications - in production would query notifications table
        const notifications = [
            {
                id: 'notif_1',
                type: 'relationship',
                title: 'New Relationship Insight',
                message: 'AI detected improved communication patterns in your recent memories. Your relationship health score increased by 5 points!',
                read: false,
                createdAt: new Date(Date.now() - 30 * 60 * 1000).toISOString() // 30 minutes ago
            },
            {
                id: 'notif_2',
                type: 'memory',
                title: 'Anniversary Reminder',
                message: 'Tomorrow marks 1 year since your memory about "First date at the coffee shop". Consider celebrating this special milestone!',
                read: false,
                createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() // 2 hours ago
            },
            {
                id: 'notif_3',
                type: 'social',
                title: 'New Connection Request',
                message: 'Sarah Johnson wants to connect with you. You share interests in family memories and travel experiences.',
                read: true,
                createdAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString() // 4 hours ago
            },
            {
                id: 'notif_4',
                type: 'avatar',
                title: 'Avatar Conversation',
                message: 'Your avatar had a meaningful conversation with Emma Watson\'s avatar about preserving family traditions.',
                read: true,
                createdAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString() // 6 hours ago
            }
        ];
        
        res.json({
            success: true,
            notifications: notifications
        });
    } catch (error) {
        console.error('Recent notifications error:', error);
        res.status(500).json({ error: 'Failed to load recent notifications' });
    }
});

// Get smart reminders
app.get('/api/notifications/reminders', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Demo smart reminders - in production would analyze memories and generate AI-powered reminders
        const reminders = [
            {
                id: 'reminder_1',
                title: 'Mom\'s Birthday',
                description: 'AI detected this important date from your family memories. Consider calling or visiting.',
                date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days from now
                type: 'family',
                priority: 'high'
            },
            {
                id: 'reminder_2',
                title: 'Monthly Date Night',
                description: 'You and your partner have been creating beautiful memories together. Plan something special!',
                date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 1 week from now
                type: 'relationship',
                priority: 'medium'
            },
            {
                id: 'reminder_3',
                title: 'Work Anniversary',
                description: 'Congratulations on reaching this milestone! Time to reflect on your professional growth.',
                date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(), // 2 weeks from now
                type: 'career',
                priority: 'medium'
            }
        ];
        
        res.json({
            success: true,
            reminders: reminders
        });
    } catch (error) {
        console.error('Smart reminders error:', error);
        res.status(500).json({ error: 'Failed to load smart reminders' });
    }
});

// Get achievements
app.get('/api/achievements', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Demo achievements - in production would calculate based on user activity
        const achievements = [
            {
                id: 'ach_1',
                title: 'Memory Keeper',
                description: 'Created your first 10 memories',
                icon: 'fas fa-brain',
                unlocked: true,
                unlockedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
                progress: 100
            },
            {
                id: 'ach_2',
                title: 'Social Butterfly',
                description: 'Made 5 meaningful connections',
                icon: 'fas fa-users',
                unlocked: true,
                unlockedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
                progress: 100
            },
            {
                id: 'ach_3',
                title: 'AI Whisperer',
                description: 'Used AI insights 25 times',
                icon: 'fas fa-lightbulb',
                unlocked: false,
                progress: 72
            },
            {
                id: 'ach_4',
                title: 'Heart Matcher',
                description: 'Found your first mutual feeling',
                icon: 'fas fa-heart',
                unlocked: false,
                progress: 45
            },
            {
                id: 'ach_5',
                title: 'Premium Explorer',
                description: 'Upgrade to premium subscription',
                icon: 'fas fa-crown',
                unlocked: false,
                progress: 0
            }
        ];
        
        res.json({
            success: true,
            achievements: achievements
        });
    } catch (error) {
        console.error('Achievements error:', error);
        res.status(500).json({ error: 'Failed to load achievements' });
    }
});

// Mark notification as read
app.post('/api/notifications/:id/read', authenticateToken, async (req, res) => {
    try {
        const { id } = req.params;
        const userId = req.user.userId;
        
        // In production, this would update notification in database
        console.log(`Marking notification ${id} as read for user ${userId}`);
        
        res.json({
            success: true,
            message: 'Notification marked as read'
        });
    } catch (error) {
        console.error('Mark notification read error:', error);
        res.status(500).json({ error: 'Failed to mark notification as read' });
    }
});

// Delete notification
app.delete('/api/notifications/:id', authenticateToken, async (req, res) => {
    try {
        const { id } = req.params;
        const userId = req.user.userId;
        
        // In production, this would delete notification from database
        console.log(`Deleting notification ${id} for user ${userId}`);
        
        res.json({
            success: true,
            message: 'Notification deleted'
        });
    } catch (error) {
        console.error('Delete notification error:', error);
        res.status(500).json({ error: 'Failed to delete notification' });
    }
});

// AI Memory Pattern Analysis
app.post('/api/ai/analyze-patterns', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Get user's memories for pattern analysis
        const memoriesResult = await memoryApp.getUserMemories(userId);
        
        if (!memoriesResult.success || memoriesResult.memories.length === 0) {
            return res.json({
                success: true,
                message: 'Not enough memories for pattern analysis yet'
            });
        }
        
        // In production, this would perform advanced AI analysis
        console.log(`Analyzing memory patterns for user ${userId} with ${memoriesResult.memories.length} memories`);
        
        // Simulate processing time
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        res.json({
            success: true,
            message: 'Memory pattern analysis completed',
            insights: {
                totalMemories: memoriesResult.memories.length,
                frequentThemes: ['family', 'relationships', 'personal growth'],
                emotionalTrends: 'Positive trajectory with increasing happiness indicators',
                recommendedActions: [
                    'Schedule more family time',
                    'Document relationship milestones',
                    'Create goal-oriented memories'
                ]
            }
        });
    } catch (error) {
        console.error('AI pattern analysis error:', error);
        res.status(500).json({ error: 'Failed to analyze memory patterns' });
    }
});

// 🚨 REVOLUTIONARY EMERGENCY CONTACTS & MEMORY INHERITANCE APIS

// Get emergency dashboard stats
app.get('/api/emergency/dashboard', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Calculate emergency contact stats
        const stats = {
            emergencyContacts: 0,
            protectedMemories: 0,
            inheritancePlan: 'Not Set'
        };
        
        // In production, these would be actual database queries
        // For now, return demo stats
        
        res.json({
            success: true,
            stats: stats
        });
    } catch (error) {
        console.error('Emergency dashboard error:', error);
        res.status(500).json({ error: 'Failed to load emergency dashboard' });
    }
});

// Get emergency contacts
app.get('/api/emergency/contacts', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Demo emergency contacts - in production would query emergency_contacts table
        const contacts = [
            {
                id: 'ec_1',
                name: 'Sarah Johnson',
                relationship: 'spouse',
                phone: '+1 (555) 123-4567',
                email: 'sarah@example.com',
                accessLevel: 'full',
                crisisConditions: ['medical', 'missing', 'eol'],
                status: 'verified',
                createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString() // 30 days ago
            },
            {
                id: 'ec_2',
                name: 'Michael Chen',
                relationship: 'friend',
                phone: '+1 (555) 987-6543',
                email: 'michael@example.com',
                accessLevel: 'personal',
                crisisConditions: ['medical', 'missing'],
                status: 'verified',
                createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString() // 15 days ago
            }
        ];
        
        res.json({
            success: true,
            contacts: contacts
        });
    } catch (error) {
        console.error('Emergency contacts error:', error);
        res.status(500).json({ error: 'Failed to load emergency contacts' });
    }
});

// Add emergency contact
app.post('/api/emergency/contacts', authenticateToken, async (req, res) => {
    try {
        const { name, relationship, phone, email, accessLevel, crisisConditions } = req.body;
        const userId = req.user.userId;
        
        // Validate required fields
        if (!name || !relationship || !phone || !email || !accessLevel) {
            return res.status(400).json({ error: 'All required fields must be provided' });
        }
        
        if (!crisisConditions || crisisConditions.length === 0) {
            return res.status(400).json({ error: 'At least one crisis condition must be selected' });
        }
        
        // Validate access level
        const validAccessLevels = ['essential', 'general', 'personal', 'full'];
        if (!validAccessLevels.includes(accessLevel)) {
            return res.status(400).json({ error: 'Invalid access level' });
        }
        
        // Validate crisis conditions
        const validConditions = ['medical', 'missing', 'legal', 'eol'];
        const invalidConditions = crisisConditions.filter(condition => !validConditions.includes(condition));
        if (invalidConditions.length > 0) {
            return res.status(400).json({ error: `Invalid crisis conditions: ${invalidConditions.join(', ')}` });
        }
        
        // In production, this would:
        // 1. Save to emergency_contacts table
        // 2. Send verification email to contact
        // 3. Generate unique emergency access codes
        // 4. Set up monitoring for crisis scenarios
        
        const newContact = {
            id: `ec_${Date.now()}`,
            userId: userId,
            name: name,
            relationship: relationship,
            phone: phone,
            email: email,
            accessLevel: accessLevel,
            crisisConditions: crisisConditions,
            status: 'pending_verification',
            createdAt: new Date().toISOString()
        };
        
        console.log(`Emergency contact added for user ${userId}:`, newContact);
        
        res.json({
            success: true,
            message: 'Emergency contact added successfully',
            contact: newContact
        });
    } catch (error) {
        console.error('Add emergency contact error:', error);
        res.status(500).json({ error: 'Failed to add emergency contact' });
    }
});

// Remove emergency contact
app.delete('/api/emergency/contacts/:contactId', authenticateToken, async (req, res) => {
    try {
        const { contactId } = req.params;
        const userId = req.user.userId;
        
        // In production, this would:
        // 1. Verify contact belongs to user
        // 2. Remove from database
        // 3. Update inheritance plans
        // 4. Notify contact of removal
        
        console.log(`Removing emergency contact ${contactId} for user ${userId}`);
        
        res.json({
            success: true,
            message: 'Emergency contact removed successfully'
        });
    } catch (error) {
        console.error('Remove emergency contact error:', error);
        res.status(500).json({ error: 'Failed to remove emergency contact' });
    }
});

// Get inheritance plan
app.get('/api/emergency/inheritance', authenticateToken, async (req, res) => {
    try {
        const userId = req.user.userId;
        
        // Demo inheritance plan - in production would query inheritance_plans table
        const inheritancePlan = {
            id: 'ip_1',
            userId: userId,
            type: 'family',
            timeline: 'immediate',
            recipients: ['ec_1', 'ec_2'],
            status: 'active',
            createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
            updatedAt: new Date().toISOString()
        };
        
        res.json({
            success: true,
            plan: inheritancePlan
        });
    } catch (error) {
        console.error('Inheritance plan error:', error);
        res.status(500).json({ error: 'Failed to load inheritance plan' });
    }
});

// Save inheritance plan
app.post('/api/emergency/inheritance', authenticateToken, async (req, res) => {
    try {
        const { type, timeline, recipients } = req.body;
        const userId = req.user.userId;
        
        // Validate inheritance type
        const validTypes = ['essential', 'family', 'full'];
        if (!validTypes.includes(type)) {
            return res.status(400).json({ error: 'Invalid inheritance type' });
        }
        
        // Validate timeline
        const validTimelines = ['immediate', '72hours', '1week', '1month'];
        if (!validTimelines.includes(timeline)) {
            return res.status(400).json({ error: 'Invalid timeline' });
        }
        
        // Validate recipients
        if (!recipients || recipients.length === 0) {
            return res.status(400).json({ error: 'At least one recipient must be selected' });
        }
        
        // In production, this would:
        // 1. Save inheritance plan to database
        // 2. Set up automated triggers
        // 3. Generate legal documentation
        // 4. Notify recipients of their designation
        
        const inheritancePlan = {
            id: `ip_${Date.now()}`,
            userId: userId,
            type: type,
            timeline: timeline,
            recipients: recipients,
            status: 'active',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };
        
        console.log(`Inheritance plan saved for user ${userId}:`, inheritancePlan);
        
        res.json({
            success: true,
            message: 'Memory inheritance plan saved successfully',
            plan: inheritancePlan
        });
    } catch (error) {
        console.error('Save inheritance plan error:', error);
        res.status(500).json({ error: 'Failed to save inheritance plan' });
    }
});

// Crisis activation endpoint (for emergency contacts to use)
app.post('/api/emergency/activate-crisis', async (req, res) => {
    try {
        const { contactId, userId, crisisType, documentation } = req.body;
        
        // In production, this would:
        // 1. Verify emergency contact identity
        // 2. Validate crisis documentation
        // 3. Start 24-48 hour verification process
        // 4. Notify backup contacts
        // 5. Begin memory access preparation
        
        console.log(`Crisis activation requested by contact ${contactId} for user ${userId}, type: ${crisisType}`);
        
        res.json({
            success: true,
            message: 'Crisis activation request received. Verification process initiated.',
            estimatedApprovalTime: '24-48 hours',
            referenceNumber: `CRISIS_${Date.now()}`
        });
    } catch (error) {
        console.error('Crisis activation error:', error);
        res.status(500).json({ error: 'Failed to process crisis activation' });
    }
});

// Socket.IO for real-time features
io.use((socket, next) => {
    const token = socket.handshake.auth.token;
    
    if (!token) {
        return next(new Error('Authentication error'));
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            return next(new Error('Authentication error'));
        }
        socket.user = user;
        next();
    });
});

io.on('connection', (socket) => {
    console.log(`User ${socket.user.username} connected`);
    
    // Register user connection
    connectedUsers.set(socket.user.userId, socket.id);
    
    // Record daily login
    memoryApp.addExperience(socket.user.userId, 'daily_login');

    socket.on('disconnect', () => {
        console.log(`User ${socket.user.username} disconnected`);
        connectedUsers.delete(socket.user.userId);
    });

    // Handle real-time memory creation
    socket.on('create_memory', async (data) => {
        try {
            const result = await memoryApp.createMemory(socket.user.userId, data);
            socket.emit('memory_created', result);
            
            if (result.success) {
                // Emit achievement notifications if any
                const stats = await memoryApp.getUserStats(socket.user.userId);
                socket.emit('stats_updated', stats);
            }
        } catch (error) {
            socket.emit('error', { message: 'Failed to create memory' });
        }
    });

    // Handle mutual feelings check
    socket.on('check_mutual_feelings', async () => {
        try {
            // This would integrate with the actual mutual feelings detection
            socket.emit('mutual_feelings_update', { found: false });
        } catch (error) {
            socket.emit('error', { message: 'Failed to check mutual feelings' });
        }
    });
});

// For Replit hosting, use environment PORT or fallback to 5000
const PORT = Number(process.env.PORT) || 5000;
server.listen(PORT, '0.0.0.0', () => {
    const domain = process.env.REPLIT_DEV_DOMAIN;
    console.log(`🌐 Memory App Web Interface running on port ${PORT}`);
    console.log(`🔗 Binding to 0.0.0.0:${PORT} for external access`);
    console.log(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
    
    if (domain) {
        console.log(`🚀 PUBLIC URL: https://${domain}`);
        console.log(`🌍 Access your WhatsApp-style Memory App at: https://${domain}`);
    } else {
        console.log(`🏠 Local access: http://localhost:${PORT}`);
    }
}).on('error', (err) => {
    console.error('❌ Server error:', err);
    process.exit(1);
});