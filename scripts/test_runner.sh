#!/bin/bash

###############################################################################
# MemoApp Memory Bot - Test Runner Script
# Runs all tests with coverage reporting and validation
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MIN_COVERAGE=80  # Minimum code coverage percentage required
TEST_DIR="tests"
COVERAGE_DIR="htmlcov"
COVERAGE_FILE=".coverage"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MemoApp Memory Bot - Test Suite Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "success" ]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [ "$status" = "error" ]; then
        echo -e "${RED}✗${NC} $message"
    elif [ "$status" = "warning" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
    else
        echo -e "${BLUE}→${NC} $message"
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python installation
print_status "info" "Checking Python installation..."
if ! command_exists python3; then
    print_status "error" "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
print_status "success" "Python $PYTHON_VERSION found"

# Check and install required packages
print_status "info" "Checking required packages..."

# Install pytest and coverage if not present
if ! python3 -c "import pytest" 2>/dev/null; then
    print_status "warning" "pytest not found, installing..."
    pip3 install pytest pytest-asyncio --quiet
fi

if ! python3 -c "import coverage" 2>/dev/null; then
    print_status "warning" "coverage not found, installing..."
    pip3 install coverage pytest-cov --quiet
fi

print_status "success" "All required packages installed"

# Clean previous coverage data
print_status "info" "Cleaning previous coverage data..."
rm -rf $COVERAGE_DIR
rm -f $COVERAGE_FILE
rm -f .coverage.*

# Create test results directory
mkdir -p test_results

echo ""
echo -e "${BLUE}Running Test Suites${NC}"
echo -e "${BLUE}===================${NC}"
echo ""

# Run acceptance tests
print_status "info" "Running Acceptance Tests..."
if python3 -m pytest $TEST_DIR/test_acceptance.py -v --tb=short --cov=app --cov-append > test_results/acceptance.log 2>&1; then
    print_status "success" "Acceptance tests passed"
    ACCEPTANCE_PASS=1
else
    print_status "error" "Acceptance tests failed (see test_results/acceptance.log)"
    ACCEPTANCE_PASS=0
fi

# Run integration tests
print_status "info" "Running Integration Tests..."
if python3 -m pytest $TEST_DIR/test_integration.py -v --tb=short --cov=app --cov-append > test_results/integration.log 2>&1; then
    print_status "success" "Integration tests passed"
    INTEGRATION_PASS=1
else
    print_status "error" "Integration tests failed (see test_results/integration.log)"
    INTEGRATION_PASS=0
fi

# Run WhatsApp commands tests
print_status "info" "Running WhatsApp Commands Tests..."
if python3 -m pytest $TEST_DIR/test_whatsapp_commands.py -v --tb=short --cov=app --cov-append > test_results/commands.log 2>&1; then
    print_status "success" "WhatsApp commands tests passed"
    COMMANDS_PASS=1
else
    print_status "error" "WhatsApp commands tests failed (see test_results/commands.log)"
    COMMANDS_PASS=0
fi

# Run existing tests
print_status "info" "Running Existing Tests..."
EXISTING_TESTS=""
for test_file in $TEST_DIR/test_*.py; do
    basename=$(basename "$test_file")
    if [[ "$basename" != "test_acceptance.py" && "$basename" != "test_integration.py" && "$basename" != "test_whatsapp_commands.py" ]]; then
        EXISTING_TESTS="$EXISTING_TESTS $test_file"
    fi
done

if [ -n "$EXISTING_TESTS" ]; then
    if python3 -m pytest $EXISTING_TESTS -v --tb=short --cov=app --cov-append > test_results/existing.log 2>&1; then
        print_status "success" "Existing tests passed"
        EXISTING_PASS=1
    else
        print_status "warning" "Some existing tests failed (see test_results/existing.log)"
        EXISTING_PASS=0
    fi
else
    print_status "info" "No existing tests found"
    EXISTING_PASS=1
fi

echo ""
echo -e "${BLUE}Coverage Report${NC}"
echo -e "${BLUE}===============${NC}"
echo ""

# Generate coverage report
print_status "info" "Generating coverage report..."
python3 -m coverage report --precision=2 > test_results/coverage.txt 2>&1

# Extract coverage percentage
COVERAGE_PERCENT=$(python3 -m coverage report | grep -E "^TOTAL" | awk '{print $NF}' | sed 's/%//')

if [ -z "$COVERAGE_PERCENT" ]; then
    print_status "warning" "Could not determine coverage percentage"
    COVERAGE_PERCENT=0
fi

# Convert to integer for comparison
COVERAGE_INT=$(echo "$COVERAGE_PERCENT" | cut -d. -f1)

# Display coverage
if [ "$COVERAGE_INT" -ge "$MIN_COVERAGE" ]; then
    print_status "success" "Code coverage: ${COVERAGE_PERCENT}% (minimum: ${MIN_COVERAGE}%)"
    COVERAGE_PASS=1
else
    print_status "error" "Code coverage: ${COVERAGE_PERCENT}% (minimum: ${MIN_COVERAGE}%)"
    COVERAGE_PASS=0
fi

# Generate HTML coverage report
print_status "info" "Generating HTML coverage report..."
python3 -m coverage html --directory=$COVERAGE_DIR --precision=2

if [ -d "$COVERAGE_DIR" ]; then
    print_status "success" "HTML coverage report generated in $COVERAGE_DIR/"
    echo -e "    ${BLUE}→${NC} Open ${COVERAGE_DIR}/index.html to view detailed coverage"
fi

# Generate detailed coverage by module
echo ""
echo -e "${BLUE}Coverage by Module${NC}"
echo -e "${BLUE}==================${NC}"
python3 -m coverage report --precision=2 | head -20

echo ""
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}============${NC}"
echo ""

# Calculate totals
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Count test results
for log_file in test_results/*.log; do
    if [ -f "$log_file" ]; then
        # Extract test counts from pytest output
        if grep -q "passed" "$log_file"; then
            passed=$(grep -oP '\d+(?= passed)' "$log_file" | tail -1)
            PASSED_TESTS=$((PASSED_TESTS + ${passed:-0}))
        fi
        if grep -q "failed" "$log_file"; then
            failed=$(grep -oP '\d+(?= failed)' "$log_file" | tail -1)
            FAILED_TESTS=$((FAILED_TESTS + ${failed:-0}))
        fi
    fi
done

TOTAL_TESTS=$((PASSED_TESTS + FAILED_TESTS))

# Display summary
echo "Test Results:"
echo "  • Total Tests Run: $TOTAL_TESTS"
echo "  • Tests Passed: $PASSED_TESTS"
echo "  • Tests Failed: $FAILED_TESTS"
echo ""
echo "Suite Results:"
[ "$ACCEPTANCE_PASS" -eq 1 ] && print_status "success" "Acceptance Tests: PASSED" || print_status "error" "Acceptance Tests: FAILED"
[ "$INTEGRATION_PASS" -eq 1 ] && print_status "success" "Integration Tests: PASSED" || print_status "error" "Integration Tests: FAILED"
[ "$COMMANDS_PASS" -eq 1 ] && print_status "success" "Commands Tests: PASSED" || print_status "error" "Commands Tests: FAILED"
[ "$EXISTING_PASS" -eq 1 ] && print_status "success" "Existing Tests: PASSED" || print_status "error" "Existing Tests: FAILED"
[ "$COVERAGE_PASS" -eq 1 ] && print_status "success" "Coverage Check: PASSED (${COVERAGE_PERCENT}%)" || print_status "error" "Coverage Check: FAILED (${COVERAGE_PERCENT}%)"

echo ""
echo -e "${BLUE}========================================${NC}"

# Determine exit code
EXIT_CODE=0

if [ "$ACCEPTANCE_PASS" -eq 0 ] || [ "$INTEGRATION_PASS" -eq 0 ] || [ "$COMMANDS_PASS" -eq 0 ]; then
    print_status "error" "CRITICAL: Core test suites failed!"
    EXIT_CODE=1
fi

if [ "$COVERAGE_PASS" -eq 0 ]; then
    print_status "warning" "WARNING: Coverage below minimum threshold"
    if [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=2  # Non-critical failure
    fi
fi

if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed successfully!${NC}"
    echo -e "${BLUE}========================================${NC}"
else
    echo -e "${RED}✗ Test suite failed with errors${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "To view detailed test results:"
    echo "  • Acceptance tests: cat test_results/acceptance.log"
    echo "  • Integration tests: cat test_results/integration.log"
    echo "  • Commands tests: cat test_results/commands.log"
    echo "  • Coverage report: cat test_results/coverage.txt"
fi

echo ""

# Optionally run specific test in verbose mode
if [ "$1" = "--verbose" ] || [ "$1" = "-v" ]; then
    echo -e "${BLUE}Running tests in verbose mode...${NC}"
    python3 -m pytest $TEST_DIR -v --tb=long
fi

# Optionally run with debugging
if [ "$1" = "--debug" ] || [ "$1" = "-d" ]; then
    echo -e "${BLUE}Running tests with debugging enabled...${NC}"
    python3 -m pytest $TEST_DIR -vvv --tb=long --capture=no
fi

# Exit with appropriate code for CI/CD
exit $EXIT_CODE