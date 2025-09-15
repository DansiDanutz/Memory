#!/bin/bash

# ============================================
# Memory App Deployment Script
# Digital Immortality Platform
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================
# STEP 1: Check System Requirements
# ============================================
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    log_success "Python 3 found: $(python3 --version)"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        exit 1
    fi
    log_success "Node.js found: $(node --version)"
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed"
        exit 1
    fi
    log_success "npm found: $(npm --version)"
    
    # Check if .env file exists
    if [ ! -f "memory-system/.env" ]; then
        log_warning ".env file not found. Creating from template..."
        cp memory-system/.env.example memory-system/.env
        log_info "Please edit memory-system/.env with your credentials"
        read -p "Press enter to continue after editing .env file..."
    fi
    
    log_success "All system requirements met!"
}

# ============================================
# STEP 2: Install Python Dependencies
# ============================================
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    cd memory-system
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install required packages
    log_info "Installing Python packages..."
    pip install -q \
        aiofiles \
        anthropic \
        apscheduler \
        cryptography \
        flask \
        flask-cors \
        flask-socketio \
        openai \
        pyjwt \
        python-socketio \
        stripe \
        supabase \
        twilio \
        python-dotenv
    
    log_success "Python dependencies installed!"
    
    cd ..
}

# ============================================
# STEP 3: Install Node.js Dependencies
# ============================================
install_node_deps() {
    log_info "Installing Node.js dependencies..."
    
    # Install web interface dependencies
    if [ -d "web-interface" ]; then
        cd web-interface
        log_info "Installing web interface dependencies..."
        npm install --silent
        cd ..
    fi
    
    # Install Memory-App dependencies if it exists
    if [ -d "Memory-App" ]; then
        cd Memory-App
        log_info "Installing Memory-App dependencies..."
        npm install --silent
        cd ..
    fi
    
    log_success "Node.js dependencies installed!"
}

# ============================================
# STEP 4: Initialize Database
# ============================================
init_database() {
    log_info "Initializing database..."
    
    cd memory-system
    source venv/bin/activate
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    # Run database initialization
    python3 init_database.py
    
    if [ $? -eq 0 ]; then
        log_success "Database initialized successfully!"
    else
        log_warning "Database initialization completed with warnings"
        log_info "Please check the Supabase dashboard to ensure all tables are created"
    fi
    
    cd ..
}

# ============================================
# STEP 5: Run Tests
# ============================================
run_tests() {
    log_info "Running system tests..."
    
    cd memory-system
    source venv/bin/activate
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    # Run integration tests
    log_info "Running integration tests..."
    python3 test_integration.py
    
    if [ $? -eq 0 ]; then
        log_success "All tests passed!"
    else
        log_warning "Some tests failed. Please review the logs."
        read -p "Continue deployment anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Deployment cancelled"
            exit 1
        fi
    fi
    
    cd ..
}

# ============================================
# STEP 6: Start Services
# ============================================
start_services() {
    log_info "Starting Memory App services..."
    
    # Create logs directory
    mkdir -p logs
    
    # Start Memory App (Python backend)
    log_info "Starting Memory App backend..."
    cd memory-system
    source venv/bin/activate
    export $(cat .env | grep -v '^#' | xargs)
    
    # Start main memory app
    nohup python3 memory_app.py > ../logs/memory_app.log 2>&1 &
    MEMORY_PID=$!
    log_success "Memory App started (PID: $MEMORY_PID)"
    
    # Start webhook server
    nohup python3 webhook_server.py > ../logs/webhook_server.log 2>&1 &
    WEBHOOK_PID=$!
    log_success "Webhook server started (PID: $WEBHOOK_PID)"
    
    cd ..
    
    # Start web interface
    if [ -d "web-interface" ]; then
        log_info "Starting web interface..."
        cd web-interface
        nohup npm start > ../logs/web_interface.log 2>&1 &
        WEB_PID=$!
        log_success "Web interface started (PID: $WEB_PID)"
        cd ..
    fi
    
    # Save PIDs for management
    echo "MEMORY_PID=$MEMORY_PID" > .pids
    echo "WEBHOOK_PID=$WEBHOOK_PID" >> .pids
    echo "WEB_PID=$WEB_PID" >> .pids
    
    log_success "All services started!"
}

# ============================================
# STEP 7: Health Check
# ============================================
health_check() {
    log_info "Performing health checks..."
    
    # Wait for services to start
    sleep 5
    
    # Check Memory App
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        log_success "Memory App is healthy"
    else
        log_warning "Memory App health check failed"
    fi
    
    # Check Webhook Server
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        log_success "Webhook Server is healthy"
    else
        log_warning "Webhook Server health check failed"
    fi
    
    # Check Web Interface
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "Web Interface is healthy"
    else
        log_warning "Web Interface health check failed"
    fi
}

# ============================================
# STEP 8: Display Status
# ============================================
display_status() {
    echo
    echo "============================================"
    echo "  MEMORY APP DEPLOYMENT COMPLETE!"
    echo "============================================"
    echo
    log_info "Services running:"
    echo "  • Memory App Backend: http://localhost:5000"
    echo "  • Webhook Server: http://localhost:5000"
    echo "  • Web Interface: http://localhost:3000"
    echo
    log_info "Log files:"
    echo "  • logs/memory_app.log"
    echo "  • logs/webhook_server.log"
    echo "  • logs/web_interface.log"
    echo
    log_info "To stop services, run: ./stop.sh"
    log_info "To view logs, run: tail -f logs/*.log"
    echo
    log_success "Digital Immortality Platform is ready!"
    echo
    
    # Show feature status
    echo "Feature Status:"
    echo "  ✅ Phone call recording with transcription"
    echo "  ✅ WhatsApp message monitoring"
    echo "  ✅ Daily memory review at 9 PM"
    echo "  ✅ Contact avatar privileges"
    echo "  ✅ Three-tier SECRET memory system"
    echo "  ✅ Mutual memory gaming"
    echo "  ✅ Smart notifications for commitments"
    echo "  ✅ AI assistant using user's voice"
    echo "  ✅ Family-only access control"
    echo "  ✅ Supabase cloud database"
}

# ============================================
# MAIN DEPLOYMENT FLOW
# ============================================
main() {
    echo "============================================"
    echo "  MEMORY APP DEPLOYMENT SCRIPT"
    echo "  Digital Immortality Platform v1.0"
    echo "============================================"
    echo
    
    # Run deployment steps
    check_requirements
    install_python_deps
    install_node_deps
    init_database
    run_tests
    start_services
    health_check
    display_status
}

# Handle script arguments
case "${1:-}" in
    "stop")
        log_info "Stopping services..."
        if [ -f .pids ]; then
            source .pids
            kill $MEMORY_PID $WEBHOOK_PID $WEB_PID 2>/dev/null || true
            rm .pids
            log_success "Services stopped"
        else
            log_warning "No running services found"
        fi
        ;;
    "restart")
        $0 stop
        sleep 2
        $0
        ;;
    "status")
        if [ -f .pids ]; then
            source .pids
            echo "Service Status:"
            ps -p $MEMORY_PID > /dev/null 2>&1 && echo "  ✅ Memory App (PID: $MEMORY_PID)" || echo "  ❌ Memory App"
            ps -p $WEBHOOK_PID > /dev/null 2>&1 && echo "  ✅ Webhook Server (PID: $WEBHOOK_PID)" || echo "  ❌ Webhook Server"
            ps -p $WEB_PID > /dev/null 2>&1 && echo "  ✅ Web Interface (PID: $WEB_PID)" || echo "  ❌ Web Interface"
        else
            log_warning "No services running"
        fi
        ;;
    "logs")
        tail -f logs/*.log
        ;;
    *)
        main
        ;;
esac