#!/bin/bash

# MemoApp Data Backup Script
# PR-1.1: Create timestamped backups of the data/ directory
# Usage: ./backup_data.sh [output_path]

# Configuration
DATA_DIR="data"
BACKUP_DIR="${1:-backups}"  # Use first argument or default to 'backups'
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="memoapp_backup_${TIMESTAMP}.tar.gz"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    print_error "Data directory '$DATA_DIR' not found!"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"
if [ $? -ne 0 ]; then
    print_error "Failed to create backup directory '$BACKUP_DIR'"
    exit 1
fi

# Get data directory size
DATA_SIZE=$(du -sh "$DATA_DIR" 2>/dev/null | cut -f1)
print_info "Starting backup of $DATA_DIR (Size: $DATA_SIZE)"

# Count number of user directories
USER_COUNT=$(find "$DATA_DIR/contacts" -maxdepth 1 -type d 2>/dev/null | wc -l)
print_info "Found $USER_COUNT user profiles to backup"

# Create the backup
print_info "Creating backup: $BACKUP_DIR/$BACKUP_NAME"
tar -czf "$BACKUP_DIR/$BACKUP_NAME" "$DATA_DIR" 2>/dev/null

if [ $? -eq 0 ]; then
    # Get backup file size
    BACKUP_SIZE=$(ls -lh "$BACKUP_DIR/$BACKUP_NAME" | awk '{print $5}')
    print_info "Backup completed successfully!"
    print_info "Backup file: $BACKUP_DIR/$BACKUP_NAME"
    print_info "Backup size: $BACKUP_SIZE"
    
    # Create a backup manifest
    MANIFEST_FILE="$BACKUP_DIR/backup_manifest.txt"
    echo "=== MemoApp Backup Manifest ===" >> "$MANIFEST_FILE"
    echo "Timestamp: $(date)" >> "$MANIFEST_FILE"
    echo "Backup File: $BACKUP_NAME" >> "$MANIFEST_FILE"
    echo "Data Size: $DATA_SIZE" >> "$MANIFEST_FILE"
    echo "Backup Size: $BACKUP_SIZE" >> "$MANIFEST_FILE"
    echo "User Count: $USER_COUNT" >> "$MANIFEST_FILE"
    echo "---" >> "$MANIFEST_FILE"
    
    # List old backups for cleanup consideration
    OLD_BACKUPS=$(find "$BACKUP_DIR" -name "memoapp_backup_*.tar.gz" -mtime +7 2>/dev/null | wc -l)
    if [ $OLD_BACKUPS -gt 0 ]; then
        print_warning "Found $OLD_BACKUPS backup(s) older than 7 days in $BACKUP_DIR"
        print_warning "Consider running cleanup to free disk space"
    fi
    
    # Verify backup integrity
    print_info "Verifying backup integrity..."
    tar -tzf "$BACKUP_DIR/$BACKUP_NAME" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_info "Backup integrity verified ✓"
    else
        print_error "Backup integrity check failed!"
        exit 1
    fi
    
else
    print_error "Backup failed!"
    exit 1
fi

# Show recent backups
print_info "Recent backups:"
ls -lht "$BACKUP_DIR"/memoapp_backup_*.tar.gz 2>/dev/null | head -5

exit 0