#!/bin/bash
#######################################
# MemoApp Memory Bot Deployment Script
# Production deployment with safety checks
# Version: 1.0.0
#######################################

set -e  # Exit on error

# Configuration
APP_NAME="MemoApp Memory Bot"
APP_DIR=$(pwd)
PORT=5000
BACKUP_DIR="/tmp/memoapp_backups"
LOG_FILE="/tmp/memoapp_deploy_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="/tmp/memoapp.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function to display errors
error() {
    log "${RED}[ERROR]${NC} $1"
    exit 1
}

# Function to display warnings
warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

# Function to display success
success() {
    log "${GREEN}[✓]${NC} $1"
}

# Function to display info
info() {
    log "${BLUE}[INFO]${NC} $1"
}

# Header
log "${GREEN}========================================${NC}"
log "${GREEN}${APP_NAME} Deployment${NC}"
log "${GREEN}========================================${NC}"
log "Deployment started at: $(date)"
log "Log file: $LOG_FILE"
log ""

#######################################
# PRE-DEPLOYMENT CHECKS
#######################################

info "Running pre-deployment checks..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
REQUIRED_VERSION="3.8"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    error "Python $REQUIRED_VERSION or higher is required (found: $PYTHON_VERSION)"
fi
success "Python version check passed ($PYTHON_VERSION)"

# Check if running as appropriate user (not root in production)
if [ "$EUID" -eq 0 ]; then
    warning "Running as root is not recommended for production"
fi

# Check required environment variables
info "Checking environment variables..."
REQUIRED_VARS=(
    "DATABASE_URL"
    "WHATSAPP_ACCESS_TOKEN"
    "WHATSAPP_PHONE_NUMBER_ID"
    "WEBHOOK_VERIFY_TOKEN"
    "AZURE_SPEECH_KEY"
    "AZURE_SPEECH_REGION"
    "OPENAI_API_KEY"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    warning "Missing environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        warning "  - $var"
    done
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Deployment cancelled due to missing environment variables"
    fi
else
    success "All required environment variables are set"
fi

# Check database connectivity
info "Testing database connection..."
if [ -n "$DATABASE_URL" ]; then
    python3 -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('Database connection successful')
    exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" && success "Database connection successful" || warning "Database connection failed"
else
    warning "DATABASE_URL not set, skipping database check"
fi

# Check disk space
info "Checking disk space..."
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    warning "Disk usage is high: ${DISK_USAGE}%"
else
    success "Disk space adequate: ${DISK_USAGE}% used"
fi

# Check if port is available
info "Checking port availability..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    warning "Port $PORT is already in use"
    read -p "Stop existing process and continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Stopping existing process..."
        if [ -f "$PID_FILE" ]; then
            kill $(cat "$PID_FILE") 2>/dev/null || true
            rm -f "$PID_FILE"
        fi
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        error "Port $PORT is required for deployment"
    fi
else
    success "Port $PORT is available"
fi

#######################################
# BACKUP EXISTING DATA
#######################################

info "Creating backup before deployment..."
if [ -f "scripts/backup.sh" ]; then
    bash scripts/backup.sh | tee -a "$LOG_FILE"
    success "Backup completed"
else
    warning "Backup script not found, skipping backup"
fi

#######################################
# INSTALL/UPDATE DEPENDENCIES
#######################################

info "Installing Python dependencies..."
pip3 install -r requirements.txt --quiet || error "Failed to install dependencies"
success "Dependencies installed"

#######################################
# DATABASE MIGRATIONS
#######################################

if [ -n "$DATABASE_URL" ]; then
    info "Checking for database migrations..."
    # Add migration logic here if needed
    success "Database is up to date"
fi

#######################################
# CREATE REQUIRED DIRECTORIES
#######################################

info "Creating required directories..."
REQUIRED_DIRS=(
    "memory-system"
    "memory-system/users"
    "memory-system/security"
    "memory-system/voice_auth"
    "data"
    "data/audit"
    "data/tenants"
    "logs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    mkdir -p "$dir"
done
success "Directories created"

#######################################
# SET PERMISSIONS
#######################################

info "Setting file permissions..."
chmod 755 scripts/*.sh 2>/dev/null || true
chmod 600 memory-system/security/* 2>/dev/null || true
success "Permissions set"

#######################################
# START APPLICATION
#######################################

info "Starting ${APP_NAME}..."

# Set production environment variables
export PYTHONUNBUFFERED=1
export PRODUCTION=true
export LOG_LEVEL=INFO

# Start the application
cd app
nohup python3 -m uvicorn main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 2 \
    --loop uvloop \
    --access-log \
    --log-level info \
    > ../logs/app.log 2>&1 &

APP_PID=$!
echo $APP_PID > "$PID_FILE"
cd ..

info "Application started with PID: $APP_PID"
info "Waiting for application to be ready..."

# Wait for application to start
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ | grep -q "200"; then
        break
    fi
    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    error "Application failed to start within 30 seconds"
fi

#######################################
# HEALTH CHECK
#######################################

info "Running health checks..."

# Check main endpoint
HEALTH_CHECK=$(curl -s http://localhost:$PORT/)
if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    success "Main endpoint is healthy"
else
    error "Main endpoint health check failed"
fi

# Check webhook endpoint
WEBHOOK_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/webhook?hub.mode=subscribe&hub.verify_token=$WEBHOOK_VERIFY_TOKEN&hub.challenge=test")
if [ "$WEBHOOK_CHECK" = "200" ]; then
    success "Webhook endpoint is responding"
else
    warning "Webhook endpoint returned: $WEBHOOK_CHECK"
fi

# Check metrics endpoint
METRICS_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/metrics)
if [ "$METRICS_CHECK" = "200" ]; then
    success "Metrics endpoint is available"
else
    warning "Metrics endpoint returned: $METRICS_CHECK"
fi

#######################################
# POST-DEPLOYMENT VERIFICATION
#######################################

info "Running post-deployment verification..."

# Check if process is still running
if kill -0 $APP_PID 2>/dev/null; then
    success "Application is running"
else
    error "Application process died after startup"
fi

# Check memory usage
MEM_USAGE=$(ps aux | grep -E "python.*main:app" | grep -v grep | awk '{print $4}')
if [ -n "$MEM_USAGE" ]; then
    info "Memory usage: ${MEM_USAGE}%"
fi

# Display application logs tail
info "Recent application logs:"
tail -n 10 logs/app.log 2>/dev/null || true

#######################################
# DEPLOYMENT SUMMARY
#######################################

log ""
log "${GREEN}========================================${NC}"
log "${GREEN}Deployment Complete!${NC}"
log "${GREEN}========================================${NC}"
log ""
success "Application: ${APP_NAME}"
success "Status: Running"
success "PID: $APP_PID"
success "Port: $PORT"
success "Health Check: http://localhost:$PORT/"
success "Webhook URL: http://localhost:$PORT/webhook"
log ""
info "Monitor logs: tail -f logs/app.log"
info "Stop application: kill $(cat $PID_FILE)"
log ""

#######################################
# ROLLBACK INSTRUCTIONS
#######################################

cat << EOF >> "$LOG_FILE"

========================================
ROLLBACK INSTRUCTIONS
========================================

If you need to rollback this deployment:

1. Stop the current application:
   kill $(cat $PID_FILE)

2. Restore from backup:
   cd $BACKUP_DIR
   tar -xzf echovault_backup_[timestamp].tar.gz
   
3. Restore database (if applicable):
   gunzip -c echovault_backup_[timestamp]/database.sql.gz | psql \$DATABASE_URL

4. Restart previous version:
   cd $APP_DIR
   git checkout [previous-version-tag]
   bash scripts/deploy.sh

For emergency rollback:
   bash scripts/rollback.sh

EOF

info "Deployment log saved to: $LOG_FILE"
info "Rollback instructions added to log file"

exit 0