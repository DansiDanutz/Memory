#!/bin/bash

# Development run script for MemoApp WhatsApp Bot

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Environment setup
export PORT=${PORT:-5000}
export ENVIRONMENT=${ENVIRONMENT:-development}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export DATA_DIR=${DATA_DIR:-data}
export TZ=${TZ:-UTC}

echo -e "${GREEN}Starting MemoApp WhatsApp Bot${NC}"
echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
echo -e "${YELLOW}Port: $PORT${NC}"
echo -e "${YELLOW}Data Directory: $DATA_DIR${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    if [ -f .env.example ]; then
        echo -e "${YELLOW}Creating .env from .env.example${NC}"
        cp .env.example .env
        echo -e "${RED}Please configure your .env file with actual values${NC}"
    fi
fi

# Create necessary directories
echo -e "${GREEN}Creating necessary directories...${NC}"
mkdir -p $DATA_DIR/contacts
mkdir -p $DATA_DIR/audit
mkdir -p $DATA_DIR/tenants
mkdir -p backups
mkdir -p logs

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed${NC}"
    exit 1
fi

# Check required Python packages
echo -e "${GREEN}Checking dependencies...${NC}"
python3 -c "import fastapi" 2>/dev/null || {
    echo -e "${RED}FastAPI not installed. Installing dependencies...${NC}"
    pip install -r requirements.txt
}

# Check Azure Speech SDK
python3 -c "import azure.cognitiveservices.speech" 2>/dev/null || {
    echo -e "${YELLOW}Azure Speech SDK not found. Installing...${NC}"
    pip install azure-cognitiveservices-speech
}

# Check FFmpeg installation
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}Warning: FFmpeg not installed. Voice features may not work.${NC}"
    echo -e "${YELLOW}Install with: apt-get install ffmpeg${NC}"
fi

# Start the application
echo -e "${GREEN}Starting application on port $PORT...${NC}"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload --log-level $LOG_LEVEL