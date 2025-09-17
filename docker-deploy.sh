#!/bin/bash

# ============================================
# MEMORY APP DOCKER DEPLOYMENT SCRIPT
# ============================================
# Manages Docker-based deployment of Memory App Platform

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

# Deployment settings
PROJECT_NAME="memory-app"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="./docker-backups"
DEPLOY_ENV=${DEPLOY_ENV:-production}

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ============================================
# FUNCTIONS
# ============================================

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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        # Try Docker Compose V2
        if ! docker compose version &> /dev/null; then
            log_error "Docker Compose is not installed"
            exit 1
        fi
        # Use Docker Compose V2
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    log_success "Docker Compose found"
    
    # Check environment file
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "Environment file not found. Creating from template..."
        if [[ -f ".env.production" ]]; then
            cp .env.production .env
            log_info "Please edit .env file with your production values"
            read -p "Press enter after editing .env file..."
        else
            log_error ".env.production template not found"
            exit 1
        fi
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# Build images
build_images() {
    log_step "Building Docker images..."
    
    # Set build arguments
    export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    export VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')
    export VERSION=$(grep 'APP_VERSION' .env | cut -d '=' -f2 || echo '1.0.0')
    
    # Build with no cache for production
    if [[ "$DEPLOY_ENV" == "production" ]]; then
        log_info "Building production images (no cache)..."
        $DOCKER_COMPOSE build --no-cache --parallel
    else
        log_info "Building development images..."
        $DOCKER_COMPOSE build --parallel
    fi
    
    log_success "Images built successfully"
}

# Create backup
create_backup() {
    log_step "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup volumes
    if [[ "$($DOCKER_COMPOSE ps -q)" ]]; then
        log_info "Backing up Docker volumes..."
        
        # Backup database
        docker exec ${PROJECT_NAME}-db pg_dump -U memory_app memory_app | \
            gzip > "$BACKUP_DIR/db_backup_${TIMESTAMP}.sql.gz"
        
        # Backup Redis
        docker exec ${PROJECT_NAME}-redis redis-cli --rdb /tmp/redis_backup.rdb
        docker cp ${PROJECT_NAME}-redis:/tmp/redis_backup.rdb \
            "$BACKUP_DIR/redis_backup_${TIMESTAMP}.rdb"
    fi
    
    # Backup environment
    cp .env "$BACKUP_DIR/.env.backup_${TIMESTAMP}"
    
    log_success "Backup created in $BACKUP_DIR"
}

# Deploy application
deploy() {
    log_step "Deploying application..."
    
    # Pull latest images if using external registry
    if [[ -n "${DOCKER_REGISTRY}" ]]; then
        log_info "Pulling images from registry..."
        $DOCKER_COMPOSE pull
    fi
    
    # Start services with zero downtime
    log_info "Starting services..."
    $DOCKER_COMPOSE up -d --remove-orphans
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check health
    check_health
    
    log_success "Application deployed successfully"
}

# Check health
check_health() {
    log_step "Checking service health..."
    
    local all_healthy=true
    
    # Check each service
    for service in postgres redis backend frontend nginx; do
        if docker ps --filter "name=${PROJECT_NAME}-${service}" --filter "health=healthy" | grep -q "${PROJECT_NAME}-${service}"; then
            log_success "$service is healthy"
        else
            log_warning "$service is not healthy"
            all_healthy=false
        fi
    done
    
    # Check endpoints
    log_info "Checking endpoints..."
    
    # Backend health
    if curl -f -s -o /dev/null "http://localhost:5000/health"; then
        log_success "Backend API is responding"
    else
        log_error "Backend API is not responding"
        all_healthy=false
    fi
    
    # Frontend health
    if curl -f -s -o /dev/null "http://localhost:5000"; then
        log_success "Frontend is responding"
    else
        log_error "Frontend is not responding"
        all_healthy=false
    fi
    
    if [[ "$all_healthy" == "false" ]]; then
        log_error "Some services are not healthy"
        return 1
    fi
    
    log_success "All services are healthy"
}

# Stop services
stop_services() {
    log_step "Stopping services..."
    $DOCKER_COMPOSE down
    log_success "Services stopped"
}

# Restart services
restart_services() {
    log_step "Restarting services..."
    $DOCKER_COMPOSE restart
    log_success "Services restarted"
}

# View logs
view_logs() {
    local service=$1
    if [[ -n "$service" ]]; then
        $DOCKER_COMPOSE logs -f "$service"
    else
        $DOCKER_COMPOSE logs -f
    fi
}

# Scale service
scale_service() {
    local service=$1
    local count=$2
    
    if [[ -z "$service" ]] || [[ -z "$count" ]]; then
        log_error "Usage: $0 scale <service> <count>"
        exit 1
    fi
    
    log_step "Scaling $service to $count instances..."
    $DOCKER_COMPOSE up -d --scale "$service=$count"
    log_success "$service scaled to $count instances"
}

# Database operations
db_migrate() {
    log_step "Running database migrations..."
    
    docker exec ${PROJECT_NAME}-backend python3 << EOF
from postgres_db_client import initialize_schema
initialize_schema()
print("Database migrations completed")
EOF
    
    log_success "Database migrations completed"
}

db_backup() {
    log_step "Creating database backup..."
    
    docker exec ${PROJECT_NAME}-db pg_dump -U memory_app memory_app | \
        gzip > "db_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    log_success "Database backup created"
}

db_restore() {
    local backup_file=$1
    
    if [[ -z "$backup_file" ]] || [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_step "Restoring database from $backup_file..."
    
    gunzip -c "$backup_file" | docker exec -i ${PROJECT_NAME}-db psql -U memory_app memory_app
    
    log_success "Database restored"
}

# Clean up
cleanup() {
    log_step "Cleaning up..."
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (careful!)
    read -p "Remove unused volumes? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    # Clean old backups (keep last 10)
    if [[ -d "$BACKUP_DIR" ]]; then
        log_info "Cleaning old backups..."
        ls -t "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | tail -n +11 | xargs rm -f
    fi
    
    log_success "Cleanup completed"
}

# Monitor services
monitor() {
    log_step "Monitoring services (Ctrl+C to exit)..."
    
    while true; do
        clear
        echo "========================================="
        echo "Memory App Docker Services Monitor"
        echo "Time: $(date)"
        echo "========================================="
        echo
        
        # Show container status
        docker ps --filter "label=com.docker.compose.project=${PROJECT_NAME}" \
            --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        echo
        echo "========================================="
        echo "Resource Usage:"
        docker stats --no-stream --filter "label=com.docker.compose.project=${PROJECT_NAME}"
        
        sleep 5
    done
}

# Production deployment
production_deploy() {
    log_step "Starting production deployment..."
    
    # Safety check
    read -p "Deploy to PRODUCTION? This will affect live users. (yes/NO) " -r
    if [[ ! $REPLY == "yes" ]]; then
        log_warning "Deployment cancelled"
        exit 0
    fi
    
    # Set production environment
    export DEPLOY_ENV=production
    
    # Run deployment steps
    check_prerequisites
    create_backup
    build_images
    
    # Blue-green deployment
    log_info "Performing blue-green deployment..."
    
    # Start new containers alongside old ones
    $DOCKER_COMPOSE up -d --no-deps --scale backend=2 backend
    $DOCKER_COMPOSE up -d --no-deps --scale frontend=2 frontend
    
    # Wait for new containers to be healthy
    sleep 30
    check_health
    
    # Remove old containers
    $DOCKER_COMPOSE up -d --no-deps --scale backend=1 backend
    $DOCKER_COMPOSE up -d --no-deps --scale frontend=1 frontend
    
    # Run migrations
    db_migrate
    
    # Final health check
    check_health
    
    log_success "Production deployment completed successfully!"
}

# Show help
show_help() {
    echo "Memory App Docker Deployment Script"
    echo
    echo "Usage: $0 [command] [options]"
    echo
    echo "Commands:"
    echo "  deploy          Deploy the application"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  build           Build Docker images"
    echo "  logs [service]  View logs (optionally for specific service)"
    echo "  health          Check service health"
    echo "  scale <svc> <n> Scale a service to n instances"
    echo "  backup          Create backup"
    echo "  monitor         Monitor services (live)"
    echo "  cleanup         Clean up Docker resources"
    echo "  db:migrate      Run database migrations"
    echo "  db:backup       Backup database"
    echo "  db:restore <f>  Restore database from file"
    echo "  production      Production deployment (with confirmations)"
    echo "  help            Show this help message"
    echo
    echo "Examples:"
    echo "  $0 deploy                    # Deploy application"
    echo "  $0 logs backend              # View backend logs"
    echo "  $0 scale backend 3           # Scale backend to 3 instances"
    echo "  $0 db:restore backup.sql.gz  # Restore database"
    echo "  $0 production                # Production deployment"
}

# ============================================
# MAIN EXECUTION
# ============================================

case "${1:-help}" in
    deploy)
        check_prerequisites
        build_images
        deploy
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    build)
        check_prerequisites
        build_images
        ;;
    logs)
        view_logs "$2"
        ;;
    health)
        check_health
        ;;
    scale)
        scale_service "$2" "$3"
        ;;
    backup)
        create_backup
        ;;
    monitor)
        monitor
        ;;
    cleanup)
        cleanup
        ;;
    db:migrate)
        db_migrate
        ;;
    db:backup)
        db_backup
        ;;
    db:restore)
        db_restore "$2"
        ;;
    production)
        production_deploy
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac