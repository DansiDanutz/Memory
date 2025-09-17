# Memory Assistant - WhatsApp Style Mobile App

A sophisticated AI-powered memory management system with a beautiful WhatsApp-style interface. This application helps users capture, organize, and retrieve their life's moments through intelligent conversation classification and secure storage.

## 🌟 Features

### 📱 Mobile-First Design
- **Phone Mockup Interface**: Realistic mobile phone frame design
- **WhatsApp-Style UI**: Familiar green gradient and glassmorphic design
- **Responsive Layout**: Perfect for both desktop and mobile devices

### 🧠 AI-Powered Memory Management
- **Intelligent Classification**: Automatically categorizes conversations into:
  - Chronological (timeline events)
  - General (reusable facts)
  - Confidential (private information)
  - Secret (restricted access)
  - Ultra-secret (biometric protection)

### 🔒 Advanced Security
- **Multi-Level Protection**: Different security levels for different types of memories
- **Encryption**: All data is encrypted and secure
- **Biometric Authentication**: Voice and biometric protection for sensitive data

### 💬 Chat Interface
- **WhatsApp-Style Chat**: Familiar messaging interface for interacting with your AI assistant
- **Real-time Conversations**: Instant responses and memory retrieval
- **Message History**: Complete conversation history with your memory assistant

### 📊 Daily Insights
- **Daily Digests**: AI-generated summaries of important memories
- **Memory Analytics**: Track and analyze your memory patterns
- **Smart Reminders**: Never forget important events or tasks

## 🚀 Technology Stack

### Frontend
- **React 18**: Modern React with hooks and functional components
- **CSS3**: Custom glassmorphic design with advanced animations
- **Responsive Design**: Mobile-first approach with phone mockup

### Backend
- **Flask**: Python web framework for API development
- **SQLite**: Lightweight database for user and memory storage
- **OpenAI Integration**: GPT-powered conversation classification
- **RESTful API**: Clean API design for frontend-backend communication

### AI & Memory System
- **MD File Manager**: Sophisticated markdown file management system
- **Conversation Classifier**: AI-powered message categorization
- **Daily Memory Manager**: Automated memory organization and insights
- **Confidential Manager**: Multi-level security and access control

## 📁 Project Structure

```
memory-phase2/
├── memory-app/                 # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── SignupPage.jsx  # User registration with phone mockup
│   │   │   ├── LoginPage.jsx   # User authentication
│   │   │   └── ChatInterface.jsx # WhatsApp-style chat
│   │   ├── App.jsx             # Main application component
│   │   └── App.css             # Glassmorphic styling
│   └── package.json
├── memory-api/                 # Flask Backend
│   ├── src/
│   │   ├── routes/
│   │   │   ├── memory.py       # Memory management endpoints
│   │   │   └── user.py         # User authentication endpoints
│   │   ├── models/
│   │   │   └── user.py         # User data models
│   │   └── main.py             # Flask application entry point
│   └── requirements.txt
├── memory-system/              # Core Memory Management
│   ├── md_file_manager.py      # Markdown file operations
│   ├── conversation_classifier.py # AI message classification
│   ├── enhanced_user_onboarding.py # User setup and welcome flow
│   ├── daily_memory_manager.py # Daily insights and organization
│   └── confidential_manager.py # Security and access control
└── README.md
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- OpenAI API Key

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd memory-phase2/memory-api
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export OPENAI_API_BASE="https://api.openai.com/v1"
   ```

5. Start the Flask server:
   ```bash
   python src/main.py
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd memory-phase2/memory-app
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and visit `http://localhost:5173`

## 🎨 Design Features

### Glassmorphic UI
- **Translucent Cards**: Beautiful glass-like effects with backdrop blur
- **Gradient Backgrounds**: WhatsApp-inspired green gradients
- **Smooth Animations**: Hover effects and transitions
- **Modern Typography**: Clean, readable fonts with proper hierarchy

### Phone Mockup
- **Realistic Frame**: Authentic mobile phone appearance
- **Top Notch**: Modern smartphone design elements
- **Home Indicator**: Bottom navigation indicator
- **Responsive Content**: Perfectly scaled content within phone frame

### WhatsApp-Style Elements
- **Green Color Scheme**: Signature WhatsApp green (#25D366)
- **Message Bubbles**: Familiar chat bubble design
- **Input Fields**: WhatsApp-style form elements
- **Button Styling**: Consistent with messaging app conventions

## 🔧 API Endpoints

### Authentication
- `POST /api/signup` - User registration
- `POST /api/login` - User authentication
- `POST /api/logout` - User logout

### Memory Management
- `POST /api/chat` - Send message to AI assistant
- `GET /api/memories` - Retrieve user memories
- `GET /api/search` - Search through memories
- `GET /api/daily-digest` - Get daily memory summary

## 🚀 Deployment

### Development
The application is ready for development with hot reloading on both frontend and backend.

### Production
For production deployment:
1. Build the React frontend: `npm run build`
2. Configure Flask for production environment
3. Set up proper database (PostgreSQL recommended)
4. Configure environment variables
5. Deploy to your preferred hosting platform

## 🔐 Security Features

### Data Protection
- **Encryption**: All sensitive data is encrypted at rest
- **Secure Authentication**: Password hashing with bcrypt
- **Session Management**: Secure session handling
- **CORS Protection**: Proper cross-origin request handling

### Privacy
- **Local Storage**: Memories stored locally with user control
- **No Data Sharing**: Personal data never shared with third parties
- **Transparent Processing**: Clear information about data usage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for GPT integration
- React team for the amazing framework
- Flask community for the lightweight backend solution
- WhatsApp for design inspiration

## 📞 Support

For support, email support@memoryassistant.com or create an issue in the repository.

---

**Memory Assistant** - Your Second Brain for Life's Moments 🧠✨

