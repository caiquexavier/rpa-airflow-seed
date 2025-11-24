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
robot -d results robot/tests/

# Run specific test file
robot -d results robot/tests/protocolo_devolucao_main.robot

# Run specific test file
robot -d results robot/tests/protocolo_devolucao_main.robot

# Run with saga variables (from Airflow/listener)
robot -d results -v EXEC_ID:123 -v RPA_KEY_ID:456 -v STEP_ID:step-01 robot/tests/protocolo_devolucao_main.robot

# Run with specific browser
robot -d results --variable BROWSER:chrome robot/tests/
```

## Project Structure
The project follows a clean, layered architecture:

```
robot/
  tests/              # Test suites organized by domain
    protocolo_devolucao_main.robot
  resources/
    infra/             # Infrastructure keywords (HTTP, browser, filesystem, UI, Windows)
      browser_keywords.robot
      http_keywords.robot
      filesystem_keywords.robot
      ui_keywords.robot
      windows_keywords.robot
    saga/              # Saga/CQRS orchestration keywords
      saga_context_keywords.robot
      saga_lifecycle_keywords.robot
    domain/            # Domain-specific business keywords
      protocolo_devolucao_keywords.robot
  libs/                # Python libraries (pure functions)
    saga_client.py
    rpa_api_client.py
    parsing_utils.py
    loop_detector.py
  variables/           # Environment and default variables
    env_dev.robot
    env_prod.robot
    saga_defaults.robot
  config/              # Documentation and configuration
    README.md
    robot_cli_examples.md
results/               # Test execution results
```

## Available Tests
- `protocolo_devolucao` - Protocolo de devolução automation (e-Cargo pod download)

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

### General Issues
- Ensure all dependencies are installed
- Run `rfbrowser init` if browser initialization fails
- Check that test files exist in `robot/tests/` directory
- Verify browser resources are properly configured
- Check logs in `results/` directory for detailed error information

## Documentation

- **Project Structure**: See `robot/config/README.md` for detailed structure explanation
- **CLI Examples**: See `robot/config/robot_cli_examples.md` for command-line usage examples

## Integration

Tests are executed by:
- **Airflow**: Via `RobotFrameworkOperator` with saga context
- **Listener**: Via `rpa-listener` which receives RabbitMQ messages and executes tests
- **Manual**: Direct CLI execution (see examples above)

All execution methods pass saga context variables (`EXEC_ID`, `RPA_KEY_ID`, `STEP_ID`, `data`) to enable saga/CQRS orchestration.

