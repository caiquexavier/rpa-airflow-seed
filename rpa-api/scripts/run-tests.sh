#!/bin/bash
# Bash script to run tests with coverage

set -e

# Default values
TEST_TYPE="all"
COVERAGE_THRESHOLD="80"
GENERATE_REPORT=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -c|--coverage)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        -r|--report)
            GENERATE_REPORT=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -t, --type TYPE        Test type: unit, integration, all (default: all)"
            echo "  -c, --coverage THRESH  Coverage threshold (default: 80)"
            echo "  -r, --report           Generate HTML reports"
            echo "  -v, --verbose          Verbose output"
            echo "  -h, --help             Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo "Running RPA API Tests..."

# Set environment variables
export PYTHONPATH="src"

# Install test dependencies if needed
if ! command -v pytest &> /dev/null; then
    echo "Installing test dependencies..."
    pip install -r requirements-test.txt
fi

# Base pytest command
PYTEST_CMD="pytest"

# Add coverage options
PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing --cov-fail-under=$COVERAGE_THRESHOLD"

# Add HTML report if requested
if [ "$GENERATE_REPORT" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov-report=html:htmlcov --html=reports/test-report.html --self-contained-html"
    mkdir -p reports
fi

# Add verbose output if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
fi

# Select test type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD -m unit"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD -m integration"
        ;;
    all)
        ;;
    *)
        echo "Invalid test type. Use: unit, integration, or all"
        exit 1
        ;;
esac

echo "Executing: $PYTEST_CMD"
eval $PYTEST_CMD

if [ $? -eq 0 ]; then
    echo "All tests passed!"
    
    if [ "$GENERATE_REPORT" = true ]; then
        echo "Test report generated: reports/test-report.html"
        echo "Coverage report generated: htmlcov/index.html"
    fi
else
    echo "Tests failed!"
    exit 1
fi
