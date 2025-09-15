# Memory App - AI-Powered WhatsApp Bot with Claude Integration

A sophisticated WhatsApp memory bot with Claude AI integration for intelligent conversation analysis, response generation, and memory extraction.

## 🚀 Features

### Core Functionality
- **WhatsApp Integration**: Full webhook support for WhatsApp Business API
- **Memory System**: Persistent storage and retrieval of conversation data
- **Voice Processing**: Azure Speech Services integration
- **Multi-tenant Support**: Secure tenant management with RBAC
- **Audit Logging**: Comprehensive activity tracking

### Claude AI Integration
- **Message Analysis**: Sentiment, intent, and urgency detection
- **Response Generation**: Context-aware, tone-customizable responses
- **Conversation Summarization**: Key topics, decisions, and action items
- **Memory Extraction**: Automatic identification of important information
- **Real-time Processing**: Async operations for optimal performance

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **AI Integration**: Claude AI (Anthropic)
- **Voice Processing**: Azure Cognitive Services
- **Database**: SQLite with JSON storage
- **Authentication**: JWT with API key management
- **Deployment**: Docker, Replit, and traditional hosting

## 📦 Installation

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/DansiDanutz/Memory.git
   cd Memory
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the application**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

### Replit Deployment

See [REPLIT_CLAUDE_SETUP.md](REPLIT_CLAUDE_SETUP.md) for complete Replit deployment instructions.

### Cursor IDE Integration

See [CURSOR_REPLIT_SYNC.md](CURSOR_REPLIT_SYNC.md) for synchronization between Cursor and Replit.

## 🔧 Configuration

### Environment Variables

```bash
# WhatsApp API
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_VERIFY_TOKEN=your_verify_token

# Claude AI
CLAUDE_API_KEY=your_claude_api_key

# Admin Access
ADMIN_API_KEY=your_admin_key

# Azure Speech (Optional)
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=your_region
```

### API Keys Setup

1. **Claude AI**: Get your API key from [Anthropic Console](https://console.anthropic.com/)
2. **WhatsApp**: Set up WhatsApp Business API
3. **Azure Speech**: Create Azure Cognitive Services resource

## 📡 API Endpoints

### Core Endpoints
- `GET /` - Health check
- `GET /health` - Detailed health status
- `GET /metrics` - Prometheus metrics
- `POST /webhook/whatsapp` - WhatsApp webhook

### Claude AI Endpoints
- `GET /claude/status` - Claude service status
- `POST /claude/analyze` - Message analysis
- `POST /claude/generate` - Response generation
- `POST /claude/summarize` - Conversation summary
- `POST /claude/extract-memory` - Memory extraction

### Admin Endpoints
- `GET /admin/status` - System status (requires API key)
- `GET /admin/tenants` - Tenant management
- `POST /admin/tenants/reload` - Reload tenant configuration

## 🧠 Claude AI Features

### Message Analysis
```python
POST /claude/analyze
{
  "message": "I'm really frustrated with this issue",
  "context": "Customer support conversation"
}
```

### Response Generation
```python
POST /claude/generate
{
  "message": "How can I reset my password?",
  "context": "User needs help",
  "tone": "helpful"
}
```

### Memory Extraction
```python
POST /claude/extract-memory
{
  "text": "My birthday is March 15th and I prefer email notifications"
}
```

## 🏗️ Project Structure

```
Memory/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── webhook.py              # WhatsApp webhook handler
│   ├── claude_service.py       # Claude AI integration
│   ├── claude_router.py        # Claude API endpoints
│   ├── memory/                 # Memory management
│   ├── security/               # Authentication & security
│   ├── tenancy/                # Multi-tenant support
│   └── voice/                  # Voice processing
├── data/                       # Data storage
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
└── README.md                   # This file
```

## 🔒 Security Features

- **API Key Authentication**: Secure admin endpoints
- **Multi-tenant Isolation**: Secure tenant data separation
- **Encryption**: Data encryption at rest and in transit
- **Audit Logging**: Comprehensive activity tracking
- **Input Validation**: Robust request validation
- **Rate Limiting**: API rate limiting and abuse prevention

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_claude_integration.py
python -m pytest tests/test_whatsapp_commands.py
python -m pytest tests/test_security.py
```

## 📊 Monitoring

- **Health Checks**: Built-in health monitoring
- **Metrics**: Prometheus metrics endpoint
- **Logging**: Structured logging with different levels
- **Audit Trail**: Complete audit logging system

## 🚀 Deployment Options

### Docker
```bash
docker build -t memory-app .
docker run -p 8000:8000 memory-app
```

### Docker Compose
```bash
docker-compose up -d
```

### Replit
1. Import repository to Replit
2. Set environment variables in Secrets
3. Run the application

### Traditional Hosting
1. Set up Python 3.11+ environment
2. Install dependencies
3. Configure environment variables
4. Run with uvicorn or gunicorn

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` directory
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions

## 🔄 Synchronization

This project supports seamless synchronization between:
- **Cursor IDE**: Local development with Claude Code extension
- **Replit**: Cloud development and deployment
- **GitHub**: Version control and collaboration

See [CURSOR_REPLIT_SYNC.md](CURSOR_REPLIT_SYNC.md) for detailed sync instructions.

## 🎯 Roadmap

- [ ] Enhanced Claude AI prompts
- [ ] Real-time conversation analysis
- [ ] Advanced memory categorization
- [ ] Multi-language support
- [ ] Voice-to-text integration
- [ ] Dashboard UI improvements
- [ ] Mobile app integration

---

**Built with ❤️ using Claude AI, FastAPI, and modern Python practices.**
