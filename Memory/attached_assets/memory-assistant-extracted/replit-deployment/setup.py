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

