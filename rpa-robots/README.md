# RPA Robots

Robot Framework automation tests for RPA operations.

## Prerequisites
- Python 3.11+
- Virtual environment (venv)
- Dependencies installed
- Robot Framework Browser initialized

## Quick Start

### 1. Navigate to rpa-robots directory
```bash
cd rpa-robots
```

### 2. Create and activate virtual environment
```bash
# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Robot Framework Browser
```bash
# This downloads Playwright and browser dependencies
rfbrowser init
```

### 5. Create results directory (if needed)
```bash
# Windows:
mkdir results
# Linux/Mac:
mkdir -p results
```

### 6. Run Robot Framework tests
```bash
# Run all tests
robot -d results tests/

# Run specific test
robot -d results tests/ecargo_pod_download.robot

# Run with specific browser
robot -d results --variable BROWSER:chrome tests/
```

## Test Structure
- **Tests Directory**: `tests/`
- **Resources**: `resources/`
  - `browser/` - Browser automation resources
  - `pod_download/` - Pod download specific resources
- **Results**: `results/` - Test execution results

## Available Tests
- `ecargo_pod_download.robot` - e-Cargo pod download automation

## Test Results
After execution, check the `results/` directory for:
- `log.html` - Detailed test execution log
- `report.html` - Test execution report
- `output.xml` - Machine-readable test results

## Docker Alternative
```bash
# Build and run with Docker
docker build -t rpa-robots .
docker run -v $(pwd)/results:/app/results rpa-robots
```

## Troubleshooting
- Ensure all dependencies are installed
- Run `rfbrowser init` if browser initialization fails
- Check that test files exist in `tests/` directory
- Verify browser resources are properly configured
- Check logs in `results/` directory for detailed error information

## Manual Test Execution
You can also run individual test steps by examining the robot files and running them manually through the Robot Framework IDE or command line with specific options.

