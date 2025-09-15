# Memory Harvester Agent - Replit Deployment Guide
## Complete Setup and Deployment Instructions

---

## 🚀 **Quick Start Deployment**

### **1. One-Click Replit Setup**

#### **Option A: Import from GitHub**
```bash
1. Go to https://replit.com
2. Click "Create Repl"
3. Select "Import from GitHub"
4. Enter repository URL or upload zip file
5. Replit will auto-detect Python and configure environment
```

#### **Option B: Manual Setup**
```bash
1. Create new Python Repl
2. Upload the memory-harvester files
3. Follow configuration steps below
```

---

## 📁 **Required File Structure**

```
memory-harvester-repl/
├── .replit                          # Replit configuration
├── replit.nix                       # Nix package configuration
├── pyproject.toml                   # Python project configuration
├── requirements.txt                 # Python dependencies
├── main.py                         # Main entry point
├── setup.py                        # Setup script
├── .env.example                    # Environment variables template
├── README.md                       # Project documentation
├── memory_system/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   └── memory_harvester.py     # Main agent implementation
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # Configuration settings
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py               # Logging utilities
│   │   └── helpers.py              # Helper functions
│   └── tests/
│       ├── __init__.py
│       ├── test_memory_harvester.py
│       └── test_data/
├── data/
│   ├── memories/                   # Memory storage
│   ├── cache/                      # Processing cache
│   └── logs/                       # Application logs
└── docs/
    ├── api.md                      # API documentation
    └── examples/                   # Usage examples
```

---

## ⚙️ **Configuration Files**

### **1. .replit Configuration**

```toml
# .replit
run = "python main.py"
modules = ["python-3.11"]

[nix]
channel = "stable-22_11"

[env]
PYTHONPATH = "${REPL_HOME}"
PYTHONUNBUFFERED = "1"

[gitHubImport]
requiredFiles = [".replit", "replit.nix", "requirements.txt", "main.py"]

[languages]

[languages.python3]
pattern = "**/*.py"

[languages.python3.languageServer]
start = "pylsp"

[deployment]
run = ["sh", "-c", "python main.py"]
deploymentTarget = "cloudrun"

[packager]
language = "python3"
ignoredPackages = ["unit_tests"]

[packager.features]
enabledForHosting = false
packageSearch = true
guessImports = true

[debugger]
support = true

[debugger.interactive]
transport = "localhost:5678"
startCommand = ["dap-python", "main.py"]

[debugger.interactive.integratedAdapter]
dapTcpAddress = "localhost:5678"

[unitTest]
language = "python3"

[interpreter]
command = [
  "prybar-python311",
  "-q",
  "--ps1",
  "\u0001\u001b[33m\u0002\u0001\u001b[00m\u0002 ",
  "-i"
]

[interpreter.env]
LD_LIBRARY_PATH = "$PYTHON_LD_LIBRARY_PATH"
```

### **2. replit.nix Configuration**

```nix
# replit.nix
{ pkgs }: {
  deps = [
    pkgs.python311Full
    pkgs.replitPackages.prybar-python311
    pkgs.replitPackages.stderred
    pkgs.replitPackages.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.python311Packages.virtualenv
    
    # System dependencies for image processing
    pkgs.tesseract
    pkgs.imagemagick
    pkgs.ffmpeg
    pkgs.poppler_utils
    
    # Audio processing dependencies
    pkgs.portaudio
    pkgs.flac
    
    # Development tools
    pkgs.git
    pkgs.curl
    pkgs.wget
    
    # Database support
    pkgs.sqlite
    
    # Additional utilities
    pkgs.tree
    pkgs.htop
  ];
  
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      pkgs.glib
      pkgs.xorg.libX11
    ];
    PYTHONHOME = "${pkgs.python311Full}";
    PYTHONBIN = "${pkgs.python311Full}/bin/python3.11";
    LANG = "en_US.UTF-8";
    STDERREDBIN = "${pkgs.replitPackages.stderred}/bin/stderred";
    PRYBAR_PYTHON_BIN = "${pkgs.replitPackages.prybar-python311}/bin/prybar-python311";
  };
}
```

### **3. requirements.txt**

```txt
# Core dependencies
asyncio-mqtt==0.16.1
aiofiles==23.2.1
aiohttp==3.9.1
httpx==0.25.2
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# AI and NLP
openai==1.3.7
langdetect==1.0.9
textblob==0.17.1
nltk==3.8.1

# Image processing
Pillow==10.1.0
pytesseract==0.3.10
opencv-python-headless==4.8.1.78

# Audio processing
SpeechRecognition==3.10.0
pydub==0.25.1
librosa==0.10.1

# Document processing
PyPDF2==3.0.1
python-docx==1.1.0
openpyxl==3.1.2

# Database
aiosqlite==0.19.0
sqlalchemy[asyncio]==2.0.23

# Utilities
python-dotenv==1.0.0
click==8.1.7
rich==13.7.0
typer==0.9.0

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0
mypy==1.7.1

# Monitoring and logging
structlog==23.2.0
prometheus-client==0.19.0

# Security
cryptography==41.0.8
bcrypt==4.1.2

# Date and time
python-dateutil==2.8.2
pytz==2023.3

# Web scraping (for web clips)
beautifulsoup4==4.12.2
requests==2.31.0

# Email processing
email-validator==2.1.0
```

### **4. pyproject.toml**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "memory-harvester-agent"
version = "1.0.0"
description = "Advanced Memory Harvester Agent for Personal Memory Management"
readme = "README.md"
authors = [
    {name = "Memory Assistant Team", email = "team@memoryassistant.ai"}
]
license = {text = "MIT"}
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
keywords = ["memory", "ai", "nlp", "personal-assistant", "automation"]
dependencies = [
    "asyncio-mqtt>=0.16.1",
    "aiofiles>=23.2.1",
    "aiohttp>=3.9.1",
    "httpx>=0.25.2",
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "openai>=1.3.7",
    "langdetect>=1.0.9",
    "textblob>=0.17.1",
    "Pillow>=10.1.0",
    "pytesseract>=0.3.10",
    "SpeechRecognition>=3.10.0",
    "python-dotenv>=1.0.0",
    "rich>=13.7.0",
    "aiosqlite>=0.19.0",
    "cryptography>=41.0.8",
]
requires-python = ">=3.11"

[project.urls]
Homepage = "https://github.com/memory-assistant/memory-harvester"
Documentation = "https://memory-harvester.readthedocs.io"
Repository = "https://github.com/memory-assistant/memory-harvester.git"
"Bug Tracker" = "https://github.com/memory-assistant/memory-harvester/issues"

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "black>=23.11.0",
    "flake8>=6.1.0",
    "mypy>=1.7.1",
]
audio = [
    "pydub>=0.25.1",
    "librosa>=0.10.1",
]
documents = [
    "PyPDF2>=3.0.1",
    "python-docx>=1.1.0",
    "openpyxl>=3.1.2",
]
web = [
    "beautifulsoup4>=4.12.2",
    "requests>=2.31.0",
]

[project.scripts]
memory-harvester = "memory_system.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["memory_system*"]

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-ignore = ['E203', 'W503']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["memory_system/tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
asyncio_mode = "auto"
```

### **5. main.py - Entry Point**

```python
# main.py
"""
Memory Harvester Agent - Replit Entry Point
Main application entry point for running the Memory Harvester Agent on Replit.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from memory_system.config.settings import Settings
from memory_system.agents.memory_harvester import MemoryHarvesterAgent, RawMemoryInput, SourceType
from memory_system.utils.logger import setup_logging
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

async def main():
    """Main application entry point"""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Display welcome message
    welcome_text = Text("Memory Harvester Agent", style="bold blue")
    welcome_panel = Panel(
        welcome_text,
        subtitle="🧠 Advanced Personal Memory Processing System",
        border_style="blue"
    )
    console.print(welcome_panel)
    
    try:
        # Load configuration
        settings = Settings()
        logger.info("Configuration loaded successfully")
        
        # Initialize Memory Harvester Agent
        console.print("🔍 Initializing Memory Harvester Agent...", style="yellow")
        agent = MemoryHarvesterAgent(config=settings.dict())
        await agent.initialize()
        console.print("✅ Memory Harvester Agent initialized successfully!", style="green")
        
        # Run interactive demo
        await run_interactive_demo(agent)
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        console.print(f"❌ Error: {e}", style="red")
        return 1
    
    finally:
        if 'agent' in locals():
            await agent.shutdown()
            console.print("🛑 Memory Harvester Agent shutdown complete", style="blue")
    
    return 0

async def run_interactive_demo(agent: MemoryHarvesterAgent):
    """Run interactive demo of the Memory Harvester Agent"""
    
    console.print("\n🎯 Memory Harvester Agent Demo", style="bold green")
    console.print("Enter memories to process, or type 'quit' to exit\n")
    
    while True:
        try:
            # Get user input
            user_input = console.input("[bold cyan]Enter a memory: [/bold cyan]")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input.strip():
                continue
            
            # Create raw memory input
            raw_input = RawMemoryInput(
                content=user_input,
                source_type=SourceType.MANUAL_ENTRY,
                source_metadata={'platform': 'replit_demo'},
                user_id='demo_user',
                timestamp=None  # Will use current time
            )
            
            # Process memory
            console.print("🔄 Processing memory...", style="yellow")
            processed_memory = await agent.process_memory(raw_input)
            
            # Display results
            display_processed_memory(processed_memory)
            
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!", style="blue")
            break
        except Exception as e:
            console.print(f"❌ Processing error: {e}", style="red")

def display_processed_memory(memory):
    """Display processed memory results"""
    
    # Create result panel
    result_text = f"""
📝 Content: {memory.content[:100]}{'...' if len(memory.content) > 100 else ''}
🏷️  Tags: {', '.join(memory.tags[:5])}
😊 Sentiment: {memory.sentiment.get('label', 'unknown')} ({memory.sentiment.get('score', 0):.2f})
⭐ Quality: {memory.quality_level.value} ({memory.quality_score:.2f})
🌍 Language: {memory.language}
👥 Participants: {', '.join(memory.participants[:3])}
🆔 ID: {memory.id}
    """.strip()
    
    result_panel = Panel(
        result_text,
        title="✅ Memory Processed Successfully",
        border_style="green"
    )
    console.print(result_panel)

async def run_batch_test():
    """Run batch processing test"""
    
    console.print("\n🧪 Running Batch Processing Test...", style="bold yellow")
    
    # Load configuration
    settings = Settings()
    
    # Initialize agent
    agent = MemoryHarvesterAgent(config=settings.dict())
    await agent.initialize()
    
    # Test data
    test_memories = [
        "Had coffee with John this morning at Starbucks",
        "Meeting with the team at 2 PM about the new project",
        "Mom called to check in, she's doing well",
        "Finished reading 'The Great Gatsby' - amazing book!",
        "Went for a run in Central Park, beautiful weather"
    ]
    
    # Create raw inputs
    raw_inputs = []
    for i, content in enumerate(test_memories):
        raw_input = RawMemoryInput(
            content=content,
            source_type=SourceType.MANUAL_ENTRY,
            source_metadata={'platform': 'batch_test'},
            user_id=f'test_user_{i}',
            timestamp=None
        )
        raw_inputs.append(raw_input)
    
    # Process batch
    processed_memories = await agent.process_batch(raw_inputs)
    
    # Display results
    console.print(f"✅ Processed {len(processed_memories)} memories", style="green")
    
    # Show statistics
    stats = await agent.get_processing_stats()
    stats_text = f"""
Total Processed: {stats['total_processed']}
Average Processing Time: {stats.get('avg_processing_time', 0):.3f}s
Quality Distribution: {stats['quality_distribution']}
    """.strip()
    
    stats_panel = Panel(
        stats_text,
        title="📊 Processing Statistics",
        border_style="blue"
    )
    console.print(stats_panel)
    
    await agent.shutdown()

if __name__ == "__main__":
    # Check if running batch test
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        asyncio.run(run_batch_test())
    else:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
```

### **6. setup.py - Installation Script**

```python
# setup.py
"""
Setup script for Memory Harvester Agent
Handles installation and configuration on Replit
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def install_system_dependencies():
    """Install system dependencies using nix-env"""
    print("📦 Installing system dependencies...")
    
    dependencies = [
        "tesseract",
        "imagemagick", 
        "ffmpeg",
        "poppler_utils"
    ]
    
    for dep in dependencies:
        try:
            subprocess.run(["nix-env", "-iA", f"nixpkgs.{dep}"], check=True)
            print(f"✅ Installed {dep}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to install {dep}")

def setup_directories():
    """Create necessary directories"""
    print("📁 Setting up directories...")
    
    directories = [
        "data/memories",
        "data/cache", 
        "data/logs",
        "memory_system/config",
        "memory_system/utils",
        "memory_system/tests/test_data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def install_python_dependencies():
    """Install Python dependencies"""
    print("🐍 Installing Python dependencies...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Python dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        return False
    
    return True

def download_nltk_data():
    """Download required NLTK data"""
    print("📚 Downloading NLTK data...")
    
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('vader_lexicon', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("✅ NLTK data downloaded successfully")
    except Exception as e:
        print(f"⚠️  Failed to download NLTK data: {e}")

def create_env_file():
    """Create .env file from template"""
    print("⚙️  Creating environment configuration...")
    
    env_content = """# Memory Harvester Agent Configuration
# Copy this file to .env and fill in your values

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=sqlite:///data/memories.db

# Security Settings
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# Processing Settings
MAX_BATCH_SIZE=100
CACHE_TTL=3600
PROCESSING_TIMEOUT=30

# Feature Flags
ENABLE_OCR=true
ENABLE_SPEECH_RECOGNITION=true
ENABLE_IMAGE_ANALYSIS=true
ENABLE_WEB_SCRAPING=true

# Replit Specific
REPL_SLUG=${REPL_SLUG}
REPL_OWNER=${REPL_OWNER}
"""
    
    with open('.env.example', 'w') as f:
        f.write(env_content)
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file")
    else:
        print("ℹ️  .env file already exists")

def run_tests():
    """Run basic tests to verify installation"""
    print("🧪 Running installation tests...")
    
    try:
        # Test imports
        from memory_system.agents.memory_harvester import MemoryHarvesterAgent
        from memory_system.config.settings import Settings
        print("✅ Core imports successful")
        
        # Test configuration
        settings = Settings()
        print("✅ Configuration loading successful")
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Memory Harvester Agent for Replit...")
    print("=" * 50)
    
    # Setup steps
    setup_directories()
    create_env_file()
    
    # Install dependencies
    if not install_python_dependencies():
        print("❌ Setup failed during Python dependency installation")
        return 1
    
    # Download additional data
    download_nltk_data()
    
    # Run tests
    if not run_tests():
        print("⚠️  Setup completed with test failures")
        return 1
    
    print("=" * 50)
    print("🎉 Memory Harvester Agent setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python main.py")
    print("3. Or run batch test: python main.py batch")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
```

---

## 🔧 **Configuration Files**

### **7. memory_system/config/settings.py**

```python
# memory_system/config/settings.py
"""
Configuration settings for Memory Harvester Agent
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_api_base: str = Field(default="https://api.openai.com/v1", env="OPENAI_API_BASE")
    
    # Database
    database_url: str = Field(default="sqlite:///data/memories.db", env="DATABASE_URL")
    
    # Security
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    encryption_key: Optional[str] = Field(default=None, env="ENCRYPTION_KEY")
    
    # Processing
    max_batch_size: int = Field(default=100, env="MAX_BATCH_SIZE")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    processing_timeout: int = Field(default=30, env="PROCESSING_TIMEOUT")
    
    # Feature flags
    enable_ocr: bool = Field(default=True, env="ENABLE_OCR")
    enable_speech_recognition: bool = Field(default=True, env="ENABLE_SPEECH_RECOGNITION")
    enable_image_analysis: bool = Field(default=True, env="ENABLE_IMAGE_ANALYSIS")
    enable_web_scraping: bool = Field(default=True, env="ENABLE_WEB_SCRAPING")
    
    # Paths
    data_dir: Path = Field(default=Path("data"))
    cache_dir: Path = Field(default=Path("data/cache"))
    logs_dir: Path = Field(default=Path("data/logs"))
    
    # Replit specific
    repl_slug: Optional[str] = Field(default=None, env="REPL_SLUG")
    repl_owner: Optional[str] = Field(default=None, env="REPL_OWNER")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
```

### **8. memory_system/utils/logger.py**

```python
# memory_system/utils/logger.py
"""
Logging configuration for Memory Harvester Agent
"""

import logging
import sys
from pathlib import Path
from rich.logging import RichHandler
import structlog

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup structured logging with Rich handler"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup standard logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path("data/logs") / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        logging.getLogger().addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
```

---

## 🚀 **Deployment Steps**

### **Step 1: Create Replit Project**

```bash
# Option A: Fork from template
1. Go to https://replit.com/@your-username/memory-harvester-template
2. Click "Fork" button
3. Rename your fork

# Option B: Create new project
1. Go to https://replit.com
2. Click "Create Repl"
3. Select "Python" template
4. Name it "memory-harvester-agent"
```

### **Step 2: Upload Files**

```bash
# Upload all files from the deployment package
1. Drag and drop the zip file into Replit
2. Or use the file upload interface
3. Ensure all files are in correct structure
```

### **Step 3: Run Setup**

```bash
# In Replit shell, run:
python setup.py

# This will:
# - Install all dependencies
# - Create necessary directories
# - Download NLTK data
# - Create configuration files
# - Run basic tests
```

### **Step 4: Configure Environment**

```bash
# Edit .env file with your settings:
1. Click on .env file in file explorer
2. Add your OpenAI API key
3. Configure other settings as needed

# Example .env configuration:
OPENAI_API_KEY=sk-your-actual-openai-key-here
DEBUG=true
LOG_LEVEL=INFO
ENABLE_OCR=true
```

### **Step 5: Test Installation**

```bash
# Run the main application:
python main.py

# Or run batch test:
python main.py batch

# Check logs:
cat data/logs/memory_harvester.log
```

### **Step 6: Deploy to Production**

```bash
# For production deployment:
1. Click "Deploy" button in Replit
2. Choose deployment type (Reserved VM recommended)
3. Configure domain and SSL
4. Set production environment variables
```

---

## 🧪 **Testing and Validation**

### **Run Comprehensive Tests**

```bash
# Run all tests:
python -m pytest memory_system/tests/ -v

# Run specific test:
python -m pytest memory_system/tests/test_memory_harvester.py -v

# Run with coverage:
python -m pytest --cov=memory_system memory_system/tests/
```

### **Interactive Testing**

```python
# Test in Replit console:
from memory_system.agents.memory_harvester import *
import asyncio

async def test():
    agent = MemoryHarvesterAgent()
    await agent.initialize()
    
    # Test processing
    raw_input = RawMemoryInput(
        content="Test memory content",
        source_type=SourceType.MANUAL_ENTRY,
        source_metadata={},
        user_id="test_user"
    )
    
    result = await agent.process_memory(raw_input)
    print(f"Processed: {result.id}")
    
    await agent.shutdown()

asyncio.run(test())
```

---

## 📊 **Monitoring and Maintenance**

### **Health Check Endpoint**

```python
# Add to main.py for health monitoring:
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "memory-harvester-agent",
        "version": "1.0.0"
    }

@app.get("/metrics")
async def get_metrics():
    # Return processing statistics
    stats = await agent.get_processing_stats()
    return stats
```

### **Log Monitoring**

```bash
# Monitor logs in real-time:
tail -f data/logs/memory_harvester.log

# Check error logs:
grep ERROR data/logs/memory_harvester.log

# Monitor resource usage:
htop
```

---

## 🔧 **Troubleshooting**

### **Common Issues and Solutions**

#### **1. Import Errors**
```bash
# Fix Python path issues:
export PYTHONPATH="${REPL_HOME}:${PYTHONPATH}"

# Or add to .replit:
[env]
PYTHONPATH = "${REPL_HOME}"
```

#### **2. Missing Dependencies**
```bash
# Reinstall dependencies:
pip install -r requirements.txt --force-reinstall

# Install specific package:
pip install package-name --upgrade
```

#### **3. OCR Not Working**
```bash
# Install tesseract:
nix-env -iA nixpkgs.tesseract

# Check tesseract installation:
tesseract --version
```

#### **4. Audio Processing Issues**
```bash
# Install audio dependencies:
nix-env -iA nixpkgs.portaudio
nix-env -iA nixpkgs.flac

# Test audio processing:
python -c "import speech_recognition; print('Audio OK')"
```

#### **5. Database Issues**
```bash
# Reset database:
rm data/memories.db

# Check database permissions:
ls -la data/
```

---

## 🚀 **Performance Optimization**

### **Replit-Specific Optimizations**

```python
# In settings.py, add Replit optimizations:
class ReplitSettings(Settings):
    # Reduce memory usage
    max_batch_size: int = 50
    cache_ttl: int = 1800
    
    # Optimize for Replit's environment
    processing_timeout: int = 15
    enable_image_analysis: bool = False  # Disable heavy processing
    
    # Use Replit's database
    database_url: str = "sqlite:///data/memories.db?check_same_thread=False"
```

### **Resource Management**

```python
# Add resource monitoring:
import psutil

def check_resources():
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent()
    
    if memory.percent > 80:
        logger.warning(f"High memory usage: {memory.percent}%")
    
    if cpu > 80:
        logger.warning(f"High CPU usage: {cpu}%")
```

---

## 📈 **Scaling and Production**

### **Production Deployment Checklist**

- [ ] Set production environment variables
- [ ] Configure proper logging levels
- [ ] Set up monitoring and alerts
- [ ] Configure backup strategy
- [ ] Set up SSL certificates
- [ ] Configure rate limiting
- [ ] Set up error tracking
- [ ] Configure performance monitoring

### **Scaling Options**

1. **Vertical Scaling**: Upgrade to Reserved VM
2. **Horizontal Scaling**: Deploy multiple instances
3. **Database Scaling**: Use external database
4. **Caching**: Implement Redis caching
5. **CDN**: Use CDN for static assets

---

## 🎯 **Success Metrics**

### **Key Performance Indicators**

- **Processing Speed**: < 1 second per memory
- **Quality Score**: > 0.8 average quality
- **Error Rate**: < 1% processing errors
- **Uptime**: > 99.9% availability
- **Memory Usage**: < 512MB RAM
- **CPU Usage**: < 50% average

### **Monitoring Dashboard**

```python
# Create monitoring dashboard:
from rich.live import Live
from rich.table import Table

def create_dashboard():
    table = Table(title="Memory Harvester Agent Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Status", style="yellow")
    
    # Add metrics
    table.add_row("Processed Memories", "1,234", "✅ Normal")
    table.add_row("Average Quality", "0.87", "✅ Good")
    table.add_row("Error Rate", "0.3%", "✅ Low")
    table.add_row("Memory Usage", "245MB", "✅ Normal")
    
    return table
```

This comprehensive deployment guide provides everything needed to successfully deploy and run the Memory Harvester Agent on Replit! 🚀

