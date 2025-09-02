#!/bin/bash
# Integration test runner for elysiactl sync pipeline.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/tests/integration"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=${VERBOSE:-false}
BENCHMARK=${BENCHMARK:-false}
SLOW_TESTS=${SLOW_TESTS:-false}
COVERAGE=${COVERAGE:-false}

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -v, --verbose       Enable verbose output
    -b, --benchmark     Run performance benchmarks
    -s, --slow          Include slow tests
    -c, --coverage      Generate coverage report
    -h, --help         Show this help message

Environment Variables:
    ELYSIACTL_TEST_WCD_URL    URL for test Weaviate instance (default: http://localhost:8080)
    ELYSIACTL_TEST_COLLECTION      Test collection name (default: TEST_COLLECTION)

Examples:
    $0                              # Run basic integration tests
    $0 --verbose                    # Run with verbose output
    $0 --benchmark                  # Run performance benchmarks
    $0 --slow --benchmark           # Run all tests including slow ones
    $0 --coverage                   # Run with coverage reporting
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -b|--benchmark)
            BENCHMARK=true
            shift
            ;;
        -s|--slow)
            SLOW_TESTS=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            print_usage
            exit 1
            ;;
    esac
done

echo -e "${BLUE}ElysiaCtl Integration Test Suite${NC}"
echo "=================================="

# Check dependencies
echo -e "\n${YELLOW}Checking dependencies...${NC}"

if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv not found. Please install uv package manager.${NC}"
    exit 1
fi

# Set test environment
export ELYSIACTL_DEBUG=true
export ELYSIACTL_BATCH_SIZE=10
export ELYSIACTL_MAX_WORKERS=2
export ELYSIACTL_WCD_URL=${ELYSIACTL_TEST_WCD_URL:-"http://localhost:8080"}
export ELYSIACTL_DEFAULT_SOURCE_COLLECTION=${ELYSIACTL_TEST_COLLECTION:-"TEST_COLLECTION"}

echo "Test environment:"
echo "  Weaviate URL: $ELYSIACTL_WCD_URL"
echo "  Collection: $ELYSIACTL_DEFAULT_SOURCE_COLLECTION"
echo "  Workers: $ELYSIACTL_MAX_WORKERS"
echo "  Batch Size: $ELYSIACTL_BATCH_SIZE"

# Build pytest command
PYTEST_CMD="uv run pytest"
PYTEST_ARGS=()

# Base arguments
PYTEST_ARGS+=("$TEST_DIR")
PYTEST_ARGS+=("--tb=short")

if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_ARGS+=("-v")
    PYTEST_ARGS+=("--durations=10")
else
    PYTEST_ARGS+=("-q")
fi

# Test selection
TEST_MARKERS=()
if [[ "$BENCHMARK" == "true" ]]; then
    TEST_MARKERS+=("benchmark")
fi

if [[ "$SLOW_TESTS" == "false" ]]; then
    if [[ ${#TEST_MARKERS[@]} -eq 0 ]]; then
        PYTEST_ARGS+=("-m" "not slow")
    else
        # Combine markers
        MARKER_EXPR=$(IFS=" or "; echo "${TEST_MARKERS[*]}")
        PYTEST_ARGS+=("-m" "$MARKER_EXPR and not slow")
    fi
elif [[ ${#TEST_MARKERS[@]} -gt 0 ]]; then
    MARKER_EXPR=$(IFS=" or "; echo "${TEST_MARKERS[*]}")
    PYTEST_ARGS+=("-m" "$MARKER_EXPR")
fi

# Coverage
if [[ "$COVERAGE" == "true" ]]; then
    PYTEST_ARGS+=("--cov=elysiactl")
    PYTEST_ARGS+=("--cov-report=term-missing")
    PYTEST_ARGS+=("--cov-report=html:coverage_html")
fi

# Run tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
echo "Command: $PYTEST_CMD ${PYTEST_ARGS[*]}"

cd "$PROJECT_ROOT"
START_TIME=$(date +%s)

if $PYTEST_CMD "${PYTEST_ARGS[@]}"; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo -e "\n${GREEN}✓ Integration tests passed in ${DURATION}s${NC}"

    if [[ "$COVERAGE" == "true" ]]; then
        echo -e "\n${BLUE}Coverage report generated in coverage_html/index.html${NC}"
    fi

    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo -e "\n${RED}✗ Integration tests failed after ${DURATION}s${NC}"

    # Show recent logs for debugging
    echo -e "\n${YELLOW}Recent error logs:${NC}"
    if [[ -f "/tmp/elysiactl/sync.log" ]]; then
        tail -20 "/tmp/elysiactl/sync.log" || true
    fi

    exit 1
fi