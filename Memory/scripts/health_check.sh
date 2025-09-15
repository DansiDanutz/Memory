#!/bin/bash
#######################################
# MemoApp Memory Bot Health Check Script
# Monitors application health and alerts on issues
# Version: 1.0.0
#######################################

# Configuration
APP_NAME="MemoApp Memory Bot"
HOST="localhost"
PORT=5000
PID_FILE="/tmp/memoapp.pid"
LOG_DIR="logs"
AUDIT_DIR="data/audit"
ALERT_EMAIL="${ALERT_EMAIL:-admin@example.com}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

# Thresholds
MAX_RESPONSE_TIME=5  # seconds
MAX_MEMORY_PERCENT=80
MAX_CPU_PERCENT=75
MAX_DISK_PERCENT=85
MIN_FREE_SPACE_GB=1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
HEALTH_STATUS="HEALTHY"
ISSUES=()

# Function to display colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        OK)
            echo -e "${GREEN}[✓]${NC} $message"
            ;;
        WARNING)
            echo -e "${YELLOW}[⚠]${NC} $message"
            HEALTH_STATUS="WARNING"
            ISSUES+=("WARNING: $message")
            ;;
        ERROR)
            echo -e "${RED}[✗]${NC} $message"
            HEALTH_STATUS="CRITICAL"
            ISSUES+=("ERROR: $message")
            ;;
        INFO)
            echo -e "${BLUE}[i]${NC} $message"
            ;;
    esac
}

# Function to send alerts
send_alert() {
    local severity=$1
    local message=$2
    
    # Log to file
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$severity] $message" >> "$LOG_DIR/health_check.log"
    
    # Send email alert if configured
    if [ -n "$ALERT_EMAIL" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "[$severity] $APP_NAME Health Alert" "$ALERT_EMAIL"
    fi
    
    # Send Slack alert if configured
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[$severity] $APP_NAME: $message\"}" \
            "$SLACK_WEBHOOK" 2>/dev/null
    fi
}

# Header
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}$APP_NAME Health Check${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

#######################################
# 1. CHECK IF APPLICATION IS RUNNING
#######################################

print_status INFO "Checking application process..."

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        print_status OK "Application is running (PID: $PID)"
        
        # Check process details
        PROCESS_INFO=$(ps -p "$PID" -o comm=,etime=,%cpu=,%mem=,rss= | tail -1)
        if [ -n "$PROCESS_INFO" ]; then
            UPTIME=$(echo "$PROCESS_INFO" | awk '{print $2}')
            CPU_USAGE=$(echo "$PROCESS_INFO" | awk '{print $3}')
            MEM_USAGE=$(echo "$PROCESS_INFO" | awk '{print $4}')
            RSS_KB=$(echo "$PROCESS_INFO" | awk '{print $5}')
            RSS_MB=$((RSS_KB / 1024))
            
            print_status INFO "Uptime: $UPTIME"
            print_status INFO "CPU Usage: ${CPU_USAGE}%"
            print_status INFO "Memory Usage: ${MEM_USAGE}% (${RSS_MB}MB)"
            
            # Check resource usage thresholds
            if (( $(echo "$CPU_USAGE > $MAX_CPU_PERCENT" | bc -l) )); then
                print_status WARNING "High CPU usage: ${CPU_USAGE}%"
            fi
            
            if (( $(echo "$MEM_USAGE > $MAX_MEMORY_PERCENT" | bc -l) )); then
                print_status WARNING "High memory usage: ${MEM_USAGE}%"
            fi
        fi
    else
        print_status ERROR "Application process not found (PID: $PID)"
        send_alert "CRITICAL" "Application process is not running"
    fi
else
    print_status ERROR "PID file not found. Application may not be running."
    send_alert "CRITICAL" "Application PID file not found"
fi

echo ""

#######################################
# 2. CHECK ENDPOINT HEALTH
#######################################

print_status INFO "Checking HTTP endpoints..."

# Check main health endpoint
START_TIME=$(date +%s%N)
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://$HOST:$PORT/ 2>/dev/null)
END_TIME=$(date +%s%N)
RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))  # Convert to milliseconds

HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    print_status OK "Main endpoint responding (${RESPONSE_TIME}ms)"
    if echo "$RESPONSE_BODY" | grep -q "healthy"; then
        print_status OK "Health status: healthy"
    else
        print_status WARNING "Unexpected health response"
    fi
else
    print_status ERROR "Main endpoint returned HTTP $HTTP_CODE"
    send_alert "CRITICAL" "Main endpoint is not responding correctly (HTTP $HTTP_CODE)"
fi

# Check webhook endpoint
WEBHOOK_CHECK=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://$HOST:$PORT/webhook?hub.mode=subscribe&hub.verify_token=test&hub.challenge=test" 2>/dev/null)

if [ "$WEBHOOK_CHECK" = "200" ] || [ "$WEBHOOK_CHECK" = "403" ]; then
    print_status OK "Webhook endpoint accessible"
else
    print_status WARNING "Webhook endpoint returned HTTP $WEBHOOK_CHECK"
fi

# Check metrics endpoint
METRICS_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/metrics 2>/dev/null)
if [ "$METRICS_CHECK" = "200" ]; then
    print_status OK "Metrics endpoint available"
else
    print_status WARNING "Metrics endpoint returned HTTP $METRICS_CHECK"
fi

# Check response time
if [ "$RESPONSE_TIME" -gt $((MAX_RESPONSE_TIME * 1000)) ]; then
    print_status WARNING "Slow response time: ${RESPONSE_TIME}ms"
    send_alert "WARNING" "Application response time is slow: ${RESPONSE_TIME}ms"
fi

echo ""

#######################################
# 3. CHECK DATABASE CONNECTIVITY
#######################################

print_status INFO "Checking database connectivity..."

if [ -n "$DATABASE_URL" ]; then
    DB_CHECK=$(python3 -c "
import os
import psycopg2
import sys
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    result = cursor.fetchone()
    conn.close()
    if result[0] == 1:
        print('SUCCESS')
    else:
        print('FAILED')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1)
    
    if echo "$DB_CHECK" | grep -q "SUCCESS"; then
        print_status OK "Database connection successful"
    else
        print_status ERROR "Database connection failed: $DB_CHECK"
        send_alert "CRITICAL" "Database connection failed"
    fi
else
    print_status WARNING "DATABASE_URL not configured"
fi

echo ""

#######################################
# 4. CHECK AUDIT LOGGING
#######################################

print_status INFO "Checking audit logging..."

if [ -d "$AUDIT_DIR" ]; then
    AUDIT_FILES=$(find "$AUDIT_DIR" -name "*.jsonl" -type f 2>/dev/null | wc -l)
    if [ "$AUDIT_FILES" -gt 0 ]; then
        # Check if audit log has recent entries (within last hour)
        RECENT_ENTRIES=$(find "$AUDIT_DIR" -name "*.jsonl" -mmin -60 -type f 2>/dev/null | wc -l)
        if [ "$RECENT_ENTRIES" -gt 0 ]; then
            print_status OK "Audit logging active ($AUDIT_FILES files)"
        else
            print_status WARNING "No recent audit log entries"
        fi
    else
        print_status WARNING "No audit log files found"
    fi
else
    print_status ERROR "Audit directory not found"
fi

echo ""

#######################################
# 5. CHECK DISK SPACE
#######################################

print_status INFO "Checking disk space..."

DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
DISK_FREE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')

if [ "$DISK_USAGE" -lt "$MAX_DISK_PERCENT" ]; then
    print_status OK "Disk usage: ${DISK_USAGE}% (${DISK_FREE_GB}GB free)"
else
    print_status ERROR "High disk usage: ${DISK_USAGE}% (${DISK_FREE_GB}GB free)"
    send_alert "WARNING" "Disk usage is high: ${DISK_USAGE}%"
fi

if [ "$DISK_FREE_GB" -lt "$MIN_FREE_SPACE_GB" ]; then
    print_status ERROR "Low disk space: ${DISK_FREE_GB}GB free"
    send_alert "CRITICAL" "Low disk space: only ${DISK_FREE_GB}GB free"
fi

echo ""

#######################################
# 6. CHECK LOG FILES
#######################################

print_status INFO "Checking application logs..."

if [ -d "$LOG_DIR" ]; then
    # Check for recent errors in log files
    ERROR_COUNT=$(grep -i "ERROR" "$LOG_DIR"/*.log 2>/dev/null | wc -l)
    RECENT_ERRORS=$(find "$LOG_DIR" -name "*.log" -mmin -10 -exec grep -l "ERROR" {} \; 2>/dev/null | wc -l)
    
    if [ "$RECENT_ERRORS" -eq 0 ]; then
        print_status OK "No recent errors in logs"
    else
        print_status WARNING "Found $RECENT_ERRORS log files with recent errors"
        
        # Show last few errors
        echo "  Recent errors:"
        grep -i "ERROR" "$LOG_DIR"/*.log 2>/dev/null | tail -3 | while read -r line; do
            echo "    - ${line:0:100}..."
        done
    fi
else
    print_status WARNING "Log directory not found"
fi

echo ""

#######################################
# 7. CHECK MEMORY DATA INTEGRITY
#######################################

print_status INFO "Checking memory data integrity..."

if [ -d "memory-system" ]; then
    USER_DIRS=$(find memory-system/users -maxdepth 1 -type d 2>/dev/null | wc -l)
    if [ "$USER_DIRS" -gt 1 ]; then
        print_status OK "Memory system active ($((USER_DIRS - 1)) users)"
    else
        print_status INFO "No user data yet"
    fi
    
    # Check for corrupt index files
    CORRUPT_COUNT=$(find memory-system -name "index.json" -exec sh -c 'python3 -m json.tool "$1" > /dev/null 2>&1 || echo "$1"' _ {} \; 2>/dev/null | wc -l)
    if [ "$CORRUPT_COUNT" -eq 0 ]; then
        print_status OK "All index files valid"
    else
        print_status ERROR "$CORRUPT_COUNT corrupt index files found"
        send_alert "WARNING" "Found $CORRUPT_COUNT corrupt index files"
    fi
else
    print_status ERROR "Memory system directory not found"
fi

echo ""

#######################################
# SUMMARY
#######################################

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Health Check Summary${NC}"
echo -e "${GREEN}========================================${NC}"

case $HEALTH_STATUS in
    HEALTHY)
        echo -e "${GREEN}Overall Status: HEALTHY ✓${NC}"
        ;;
    WARNING)
        echo -e "${YELLOW}Overall Status: WARNING ⚠${NC}"
        echo ""
        echo "Issues found:"
        for issue in "${ISSUES[@]}"; do
            echo "  - $issue"
        done
        ;;
    CRITICAL)
        echo -e "${RED}Overall Status: CRITICAL ✗${NC}"
        echo ""
        echo "Critical issues:"
        for issue in "${ISSUES[@]}"; do
            echo "  - $issue"
        done
        send_alert "CRITICAL" "Health check failed with critical issues"
        ;;
esac

echo ""
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

# Exit with appropriate code
case $HEALTH_STATUS in
    HEALTHY)
        exit 0
        ;;
    WARNING)
        exit 1
        ;;
    CRITICAL)
        exit 2
        ;;
esac