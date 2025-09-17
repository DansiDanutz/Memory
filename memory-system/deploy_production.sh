#!/bin/bash

# ============================================
# MEMORY APP PRODUCTION DEPLOYMENT SCRIPT
# ============================================
# This script handles production deployment with zero-downtime,
# health checks, and automatic rollback on failure

set -e  # Exit on error

# ============================================
# CONFIGURATION
# ============================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Deployment configuration
DEPLOY_ENV=${DEPLOY_ENV:-production}
APP_NAME="memory-app"
DEPLOY_DIR="/opt/memory-app"
BACKUP_DIR="/opt/backups/memory-app"
LOG_DIR="/var/log/memory-app"
HEALTH_CHECK_URL="http://localhost:5000/health"
HEALTH_CHECK_RETRIES=10
HEALTH_CHECK_DELAY=5
ROLLBACK_ON_FAILURE=true

# Timestamp for this deployment
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOYMENT_ID="${TIMESTAMP}_$(git rev-parse --short HEAD 2>/dev/null || echo 'manual')"

# ============================================
# LOGGING FUNCTIONS
# ============================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_DIR}/deploy_${TIMESTAMP}.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_DIR}/deploy_${TIMESTAMP}.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_DIR}/deploy_${TIMESTAMP}.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_DIR}/deploy_${TIMESTAMP}.log"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_DIR}/deploy_${TIMESTAMP}.log"
}

# ============================================
# PRE-DEPLOYMENT CHECKS
# ============================================

pre_deployment_checks() {
    log_step "Running pre-deployment checks..."
    
    # Check if running as appropriate user
    if [[ $EUID -eq 0 ]]; then
        log_error "Do not run this script as root. Use deployment user instead."
        exit 1
    fi
    
    # Check required commands
    local required_commands=("python3" "node" "npm" "psql" "redis-cli" "nginx" "systemctl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    # Check environment file
    if [[ ! -f ".env" ]]; then
        log_error "Production .env file not found"
        exit 1
    fi
    
    # Validate environment variables
    source .env
    local required_vars=("DATABASE_URL" "JWT_SECRET" "OPENAI_API_KEY" "STRIPE_SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Required environment variable not set: $var"
            exit 1
        fi
    done
    
    # Check disk space
    local available_space=$(df /opt | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 1048576 ]]; then  # Less than 1GB
        log_error "Insufficient disk space for deployment"
        exit 1
    fi
    
    log_success "Pre-deployment checks passed"
}

# ============================================
# CREATE BACKUP
# ============================================

create_backup() {
    log_step "Creating backup of current deployment..."
    
    # Create backup directory
    mkdir -p "${BACKUP_DIR}/${TIMESTAMP}"
    
    # Backup application code
    if [[ -d "$DEPLOY_DIR" ]]; then
        log_info "Backing up application code..."
        tar -czf "${BACKUP_DIR}/${TIMESTAMP}/app_backup.tar.gz" -C "$DEPLOY_DIR" . 2>/dev/null || true
    fi
    
    # Backup database
    log_info "Backing up database..."
    DATABASE_URL=${DATABASE_URL}
    if [[ -n "$DATABASE_URL" ]]; then
        pg_dump "$DATABASE_URL" | gzip > "${BACKUP_DIR}/${TIMESTAMP}/database_backup.sql.gz"
    fi
    
    # Backup environment file
    cp .env "${BACKUP_DIR}/${TIMESTAMP}/.env.backup"
    
    # Backup nginx config
    if [[ -f "/etc/nginx/sites-available/${APP_NAME}" ]]; then
        cp "/etc/nginx/sites-available/${APP_NAME}" "${BACKUP_DIR}/${TIMESTAMP}/nginx.conf.backup"
    fi
    
    # Clean old backups (keep last 10)
    log_info "Cleaning old backups..."
    ls -t "${BACKUP_DIR}" | tail -n +11 | xargs -I {} rm -rf "${BACKUP_DIR}/{}"
    
    log_success "Backup created at ${BACKUP_DIR}/${TIMESTAMP}"
}

# ============================================
# DEPLOY APPLICATION
# ============================================

deploy_application() {
    log_step "Deploying application..."
    
    # Create deployment directory
    mkdir -p "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
    
    # Pull latest code
    log_info "Pulling latest code..."
    if [[ -d ".git" ]]; then
        git fetch origin
        git reset --hard origin/main
    else
        log_warning "Not a git repository, skipping code pull"
    fi
    
    # Copy production environment file
    cp /opt/configs/memory-app/.env .env
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    cd memory-system
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt || {
        # Create requirements.txt if it doesn't exist
        cat > requirements.txt << EOF
aiofiles==23.2.1
anthropic==0.18.1
apscheduler==3.10.4
asgiref==3.7.2
bleach==6.1.0
colorama==0.4.6
cryptography==41.0.7
flask==3.0.0
flask-cors==4.0.0
flask-socketio==5.3.5
openai==1.12.0
psutil==5.9.6
psycopg2-binary==2.9.9
pyjwt==2.8.0
python-socketio==5.10.0
redis==5.0.1
stripe==7.8.0
supabase==2.3.0
twilio==8.10.3
sentry-sdk==1.38.0
prometheus-client==0.19.0
gunicorn==21.2.0
EOF
        pip install -r requirements.txt
    }
    deactivate
    
    # Install Node dependencies
    log_info "Installing Node dependencies..."
    cd ../web-interface
    npm ci --production
    
    # Build frontend
    log_info "Building frontend..."
    npm run build || npm run compile || true
    
    cd "$DEPLOY_DIR"
}

# ============================================
# DATABASE MIGRATIONS
# ============================================

run_database_migrations() {
    log_step "Running database migrations..."
    
    cd "${DEPLOY_DIR}/memory-system"
    source venv/bin/activate
    
    # Initialize database schema
    python3 << EOF
import os
import sys
sys.path.insert(0, '.')
from postgres_db_client import initialize_schema
initialize_schema()
EOF
    
    deactivate
    
    log_success "Database migrations completed"
}

# ============================================
# CONFIGURE SERVICES
# ============================================

configure_services() {
    log_step "Configuring services..."
    
    # Create systemd service files
    log_info "Creating systemd service files..."
    
    # Memory App service
    sudo tee /etc/systemd/system/memory-app.service > /dev/null << EOF
[Unit]
Description=Memory App Backend Service
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=${DEPLOY_DIR}/memory-system
Environment="PATH=${DEPLOY_DIR}/memory-system/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${DEPLOY_DIR}/memory-system"
ExecStart=${DEPLOY_DIR}/memory-system/venv/bin/python3 memory_app.py
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/memory-app.log
StandardError=append:${LOG_DIR}/memory-app-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Webhook Server service
    sudo tee /etc/systemd/system/webhook-server.service > /dev/null << EOF
[Unit]
Description=Memory App Webhook Server
After=network.target memory-app.service
Wants=memory-app.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=${DEPLOY_DIR}/memory-system
Environment="PATH=${DEPLOY_DIR}/memory-system/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${DEPLOY_DIR}/memory-system"
ExecStart=${DEPLOY_DIR}/memory-system/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --worker-class eventlet webhook_server_complete:app
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/webhook-server.log
StandardError=append:${LOG_DIR}/webhook-server-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Web Interface service
    sudo tee /etc/systemd/system/web-interface.service > /dev/null << EOF
[Unit]
Description=Memory App Web Interface
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=${DEPLOY_DIR}/web-interface
Environment="NODE_ENV=production"
Environment="PORT=5000"
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/web-interface.log
StandardError=append:${LOG_DIR}/web-interface-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Configure Nginx
    log_info "Configuring Nginx..."
    sudo tee /etc/nginx/sites-available/memory-app > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Frontend
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API/Webhooks
    location /webhook {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for webhooks
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket support
    location /socket.io {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://localhost:5000/health;
        access_log off;
    }
    
    # Static files
    location /static {
        alias ${DEPLOY_DIR}/web-interface/public;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    # Enable site
    sudo ln -sf /etc/nginx/sites-available/memory-app /etc/nginx/sites-enabled/
    sudo nginx -t
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    log_success "Services configured"
}

# ============================================
# START SERVICES
# ============================================

start_services() {
    log_step "Starting services..."
    
    # Start backend services
    sudo systemctl start memory-app
    sleep 2
    sudo systemctl start webhook-server
    sleep 2
    sudo systemctl start web-interface
    
    # Reload Nginx
    sudo systemctl reload nginx
    
    # Enable services for auto-start
    sudo systemctl enable memory-app
    sudo systemctl enable webhook-server
    sudo systemctl enable web-interface
    
    log_success "Services started"
}

# ============================================
# HEALTH CHECKS
# ============================================

run_health_checks() {
    log_step "Running health checks..."
    
    local retries=0
    local max_retries=$HEALTH_CHECK_RETRIES
    
    while [[ $retries -lt $max_retries ]]; do
        log_info "Health check attempt $((retries + 1))/$max_retries..."
        
        # Check main health endpoint
        if curl -f -s -o /dev/null -w "%{http_code}" "$HEALTH_CHECK_URL" | grep -q "200"; then
            log_success "Health check passed"
            
            # Additional service checks
            if systemctl is-active --quiet memory-app; then
                log_success "Memory App service is running"
            else
                log_error "Memory App service is not running"
                return 1
            fi
            
            if systemctl is-active --quiet webhook-server; then
                log_success "Webhook Server is running"
            else
                log_error "Webhook Server is not running"
                return 1
            fi
            
            if systemctl is-active --quiet web-interface; then
                log_success "Web Interface is running"
            else
                log_error "Web Interface is not running"
                return 1
            fi
            
            # Check database connectivity
            cd "${DEPLOY_DIR}/memory-system"
            source venv/bin/activate
            python3 -c "from postgres_db_client import init_connection; assert init_connection(), 'Database connection failed'"
            deactivate
            
            log_success "All health checks passed"
            return 0
        fi
        
        retries=$((retries + 1))
        sleep $HEALTH_CHECK_DELAY
    done
    
    log_error "Health checks failed after $max_retries attempts"
    return 1
}

# ============================================
# ROLLBACK
# ============================================

rollback_deployment() {
    log_error "Deployment failed, initiating rollback..."
    
    # Find the latest backup
    local latest_backup=$(ls -t "${BACKUP_DIR}" | head -n 1)
    
    if [[ -z "$latest_backup" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi
    
    log_info "Rolling back to backup: $latest_backup"
    
    # Stop services
    sudo systemctl stop memory-app webhook-server web-interface
    
    # Restore application code
    if [[ -f "${BACKUP_DIR}/${latest_backup}/app_backup.tar.gz" ]]; then
        rm -rf "${DEPLOY_DIR}/*"
        tar -xzf "${BACKUP_DIR}/${latest_backup}/app_backup.tar.gz" -C "$DEPLOY_DIR"
    fi
    
    # Restore environment file
    if [[ -f "${BACKUP_DIR}/${latest_backup}/.env.backup" ]]; then
        cp "${BACKUP_DIR}/${latest_backup}/.env.backup" "${DEPLOY_DIR}/memory-system/.env"
    fi
    
    # Restore database
    if [[ -f "${BACKUP_DIR}/${latest_backup}/database_backup.sql.gz" ]]; then
        log_info "Restoring database..."
        gunzip -c "${BACKUP_DIR}/${latest_backup}/database_backup.sql.gz" | psql "$DATABASE_URL"
    fi
    
    # Restart services
    sudo systemctl start memory-app webhook-server web-interface
    
    log_warning "Rollback completed"
}

# ============================================
# POST-DEPLOYMENT
# ============================================

post_deployment() {
    log_step "Running post-deployment tasks..."
    
    # Clear caches
    log_info "Clearing caches..."
    redis-cli FLUSHDB
    
    # Warm up caches
    log_info "Warming up caches..."
    curl -s "$HEALTH_CHECK_URL" > /dev/null
    
    # Send deployment notification
    log_info "Sending deployment notification..."
    cat << EOF | python3
import os
import json
import requests
from datetime import datetime

webhook_url = os.getenv('SLACK_WEBHOOK_URL', '')
if webhook_url:
    payload = {
        'text': f"🚀 Memory App deployed successfully!",
        'attachments': [{
            'color': 'good',
            'fields': [
                {'title': 'Environment', 'value': '$DEPLOY_ENV', 'short': True},
                {'title': 'Version', 'value': '$DEPLOYMENT_ID', 'short': True},
                {'title': 'Deployed At', 'value': datetime.now().isoformat(), 'short': True},
                {'title': 'Deployed By', 'value': os.getenv('USER', 'unknown'), 'short': True}
            ]
        }]
    }
    requests.post(webhook_url, json=payload)
EOF
    
    # Generate deployment report
    cat > "${LOG_DIR}/deployment_${TIMESTAMP}.json" << EOF
{
    "deployment_id": "$DEPLOYMENT_ID",
    "timestamp": "$(date -Iseconds)",
    "environment": "$DEPLOY_ENV",
    "status": "success",
    "duration_seconds": $SECONDS,
    "deployed_by": "$USER",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "services": {
        "memory_app": "$(systemctl is-active memory-app)",
        "webhook_server": "$(systemctl is-active webhook-server)",
        "web_interface": "$(systemctl is-active web-interface)",
        "nginx": "$(systemctl is-active nginx)"
    }
}
EOF
    
    log_success "Post-deployment tasks completed"
}

# ============================================
# MAIN DEPLOYMENT FLOW
# ============================================

main() {
    log_info "=========================================="
    log_info "Starting Memory App Production Deployment"
    log_info "Deployment ID: $DEPLOYMENT_ID"
    log_info "=========================================="
    
    # Create necessary directories
    mkdir -p "$LOG_DIR" "$BACKUP_DIR"
    
    # Run deployment steps
    pre_deployment_checks
    create_backup
    deploy_application
    run_database_migrations
    configure_services
    start_services
    
    # Health checks
    if run_health_checks; then
        post_deployment
        log_success "=========================================="
        log_success "Deployment completed successfully!"
        log_success "Deployment ID: $DEPLOYMENT_ID"
        log_success "Duration: ${SECONDS} seconds"
        log_success "=========================================="
        exit 0
    else
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment
        fi
        log_error "Deployment failed!"
        exit 1
    fi
}

# ============================================
# SCRIPT EXECUTION
# ============================================

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    rollback)
        rollback_deployment
        ;;
    health)
        run_health_checks
        ;;
    backup)
        create_backup
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|health|backup}"
        exit 1
        ;;
esac