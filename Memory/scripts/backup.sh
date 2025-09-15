#!/bin/bash
#######################################
# MemoApp Memory Bot Backup Script
# Backs up critical data and audit logs
# Maintains rotation of last 7 days
#######################################

# Configuration
BACKUP_DIR="/tmp/memoapp_backups"
DATA_DIR="memory-system"
AUDIT_DIR="data/audit"
TENANT_DIR="data/tenants"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="memoapp_backup_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MemoApp Memory Bot Backup${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo "Backup location: ${BACKUP_DIR}/${BACKUP_NAME}"
echo ""

# Function to display progress
show_progress() {
    echo -e "${YELLOW}[$(date +%H:%M:%S)]${NC} $1"
}

# Function to display error
show_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to display success
show_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Create temporary backup directory
TEMP_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}"
mkdir -p "${TEMP_BACKUP}"

# Backup memory system data
if [ -d "${DATA_DIR}" ]; then
    show_progress "Backing up memory system data..."
    
    # Count files for progress
    FILE_COUNT=$(find "${DATA_DIR}" -type f | wc -l)
    show_progress "Found ${FILE_COUNT} files to backup"
    
    # Create tarball with compression
    tar -czf "${TEMP_BACKUP}/memory_data.tar.gz" "${DATA_DIR}" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        SIZE=$(du -h "${TEMP_BACKUP}/memory_data.tar.gz" | cut -f1)
        show_success "Memory data backed up (${SIZE})"
    else
        show_error "Failed to backup memory data"
    fi
else
    show_error "Memory system directory not found: ${DATA_DIR}"
fi

# Backup audit logs
if [ -d "${AUDIT_DIR}" ]; then
    show_progress "Backing up audit logs..."
    
    # Count audit files
    AUDIT_COUNT=$(find "${AUDIT_DIR}" -name "*.jsonl" -type f | wc -l)
    show_progress "Found ${AUDIT_COUNT} audit log files"
    
    # Create tarball
    tar -czf "${TEMP_BACKUP}/audit_logs.tar.gz" "${AUDIT_DIR}" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        SIZE=$(du -h "${TEMP_BACKUP}/audit_logs.tar.gz" | cut -f1)
        show_success "Audit logs backed up (${SIZE})"
    else
        show_error "Failed to backup audit logs"
    fi
else
    show_progress "No audit logs found (directory: ${AUDIT_DIR})"
fi

# Backup tenant configuration
if [ -d "${TENANT_DIR}" ]; then
    show_progress "Backing up tenant configuration..."
    
    # Copy tenant configuration
    tar -czf "${TEMP_BACKUP}/tenant_config.tar.gz" "${TENANT_DIR}" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        SIZE=$(du -h "${TEMP_BACKUP}/tenant_config.tar.gz" | cut -f1)
        show_success "Tenant configuration backed up (${SIZE})"
    else
        show_error "Failed to backup tenant configuration"
    fi
else
    show_progress "No tenant configuration found (directory: ${TENANT_DIR})"
fi

# Backup database if PostgreSQL is available
if [ -n "${DATABASE_URL}" ]; then
    show_progress "Backing up PostgreSQL database..."
    
    # Extract database name from DATABASE_URL
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    
    # Use pg_dump if available
    if command -v pg_dump &> /dev/null; then
        pg_dump "${DATABASE_URL}" > "${TEMP_BACKUP}/database.sql" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            # Compress the SQL dump
            gzip "${TEMP_BACKUP}/database.sql"
            SIZE=$(du -h "${TEMP_BACKUP}/database.sql.gz" | cut -f1)
            show_success "Database backed up (${SIZE})"
        else
            show_error "Failed to backup database"
        fi
    else
        show_progress "pg_dump not available, skipping database backup"
    fi
else
    show_progress "No database configured, skipping database backup"
fi

# Create backup metadata
show_progress "Creating backup metadata..."
cat > "${TEMP_BACKUP}/backup_info.json" << EOF
{
    "timestamp": "${TIMESTAMP}",
    "date": "$(date -Iseconds)",
    "version": "1.0.0",
    "components": {
        "memory_data": $([ -f "${TEMP_BACKUP}/memory_data.tar.gz" ] && echo "true" || echo "false"),
        "audit_logs": $([ -f "${TEMP_BACKUP}/audit_logs.tar.gz" ] && echo "true" || echo "false"),
        "tenant_config": $([ -f "${TEMP_BACKUP}/tenant_config.tar.gz" ] && echo "true" || echo "false"),
        "database": $([ -f "${TEMP_BACKUP}/database.sql.gz" ] && echo "true" || echo "false")
    },
    "sizes": {
        "total": "$(du -sh ${TEMP_BACKUP} | cut -f1)",
        "memory_data": "$([ -f ${TEMP_BACKUP}/memory_data.tar.gz ] && du -h ${TEMP_BACKUP}/memory_data.tar.gz | cut -f1 || echo 'N/A')",
        "audit_logs": "$([ -f ${TEMP_BACKUP}/audit_logs.tar.gz ] && du -h ${TEMP_BACKUP}/audit_logs.tar.gz | cut -f1 || echo 'N/A')",
        "tenant_config": "$([ -f ${TEMP_BACKUP}/tenant_config.tar.gz ] && du -h ${TEMP_BACKUP}/tenant_config.tar.gz | cut -f1 || echo 'N/A')",
        "database": "$([ -f ${TEMP_BACKUP}/database.sql.gz ] && du -h ${TEMP_BACKUP}/database.sql.gz | cut -f1 || echo 'N/A')"
    }
}
EOF

# Create final backup archive
show_progress "Creating final backup archive..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"

if [ $? -eq 0 ]; then
    # Remove temporary directory
    rm -rf "${TEMP_BACKUP}"
    
    FINAL_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
    show_success "Backup completed: ${BACKUP_NAME}.tar.gz (${FINAL_SIZE})"
else
    show_error "Failed to create final backup archive"
    exit 1
fi

# Rotation: Remove backups older than RETENTION_DAYS
show_progress "Rotating old backups (keeping last ${RETENTION_DAYS} days)..."

DELETED_COUNT=0
for backup in $(find "${BACKUP_DIR}" -name "echovault_backup_*.tar.gz" -type f -mtime +${RETENTION_DAYS}); do
    rm -f "${backup}"
    ((DELETED_COUNT++))
    show_progress "Removed old backup: $(basename ${backup})"
done

if [ ${DELETED_COUNT} -eq 0 ]; then
    show_progress "No old backups to remove"
else
    show_success "Removed ${DELETED_COUNT} old backup(s)"
fi

# List current backups
echo ""
echo -e "${GREEN}Current backups in ${BACKUP_DIR}:${NC}"
ls -lh "${BACKUP_DIR}"/echovault_backup_*.tar.gz 2>/dev/null | tail -5

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Backup saved to: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo ""
echo -e "${YELLOW}RESTORE INSTRUCTIONS:${NC}"
echo "1. Extract the backup archive:"
echo "   tar -xzf ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo ""
echo "2. Restore memory data:"
echo "   tar -xzf ${BACKUP_NAME}/memory_data.tar.gz"
echo ""
echo "3. Restore audit logs:"
echo "   tar -xzf ${BACKUP_NAME}/audit_logs.tar.gz"
echo ""
echo "4. Restore tenant configuration:"
echo "   tar -xzf ${BACKUP_NAME}/tenant_config.tar.gz"
echo ""
echo "5. Restore database (if applicable):"
echo "   gunzip ${BACKUP_NAME}/database.sql.gz"
echo "   psql \$DATABASE_URL < ${BACKUP_NAME}/database.sql"
echo ""
echo -e "${YELLOW}AUTOMATED BACKUP:${NC}"
echo "Add to crontab for daily backups at 2 AM:"
echo "0 2 * * * /path/to/scripts/backup.sh > /var/log/echovault_backup.log 2>&1"
echo ""