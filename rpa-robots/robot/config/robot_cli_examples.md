# Robot Framework CLI Examples

This document provides examples of how to run Robot Framework tests from the command line.

## Basic Test Execution

### Run All Tests
```bash
robot -d results robot/tests/
```

### Run Specific Test Suite
```bash
# Protocolo de devolução
robot -d results robot/tests/protocolo_devolucao_main.robot
```

### Run Specific Test File
```bash
robot -d results robot/tests/protocolo_devolucao_main.robot
```

## Running with Saga Variables

When tests are executed by Airflow or the listener, saga context variables are passed via command line.

### Basic Saga Variables
```bash
robot -d results \
  -v EXEC_ID:123 \
  -v RPA_KEY_ID:456 \
  -v STEP_ID:step-01 \
  robot/tests/protocolo_devolucao/
```

### With SAGA Data
```bash
robot -d results \
  -v EXEC_ID:123 \
  -v RPA_KEY_ID:456 \
  -v STEP_ID:step-01 \
  -V robot/variables/saga_defaults.robot \
  robot/tests/protocolo_devolucao/
```

### With Environment Variables
```bash
# Development
robot -d results \
  -V robot/variables/env_dev.robot \
  -v EXEC_ID:123 \
  robot/tests/protocolo_devolucao/

# Production
robot -d results \
  -V robot/variables/env_prod.robot \
  -v EXEC_ID:123 \
  robot/tests/protocolo_devolucao/
```

## Advanced Options

### Set Output Directory
```bash
robot -d results robot/tests/
```

### Set Log Level
```bash
robot -d results --loglevel DEBUG robot/tests/
robot -d results --loglevel TRACE robot/tests/
```

### Run Specific Test Case
```bash
robot -d results -t "Pod Download" robot/tests/protocolo_devolucao_main.robot
```

### Run Tests Matching Pattern
```bash
robot -d results -i smoke robot/tests/
robot -d results -e regression robot/tests/
```

### Set Variables
```bash
robot -d results \
  --variable BROWSER:chrome \
  --variable HEADLESS:True \
  robot/tests/
```

### Set Environment Variables
```bash
# Set RPA API base URL
export RPA_API_BASE_URL=http://localhost:3000
robot -d results robot/tests/
```

### Include Tags
```bash
robot -d results --include smoke robot/tests/
```

### Exclude Tags
```bash
robot -d results --exclude slow robot/tests/
```

## Integration Examples

### From Airflow
Tests are executed via `RobotFrameworkOperator` which passes saga context automatically.

### From Listener
The listener (`rpa-listener`) automatically:
1. Receives messages from RabbitMQ
2. Extracts saga context (EXEC_ID, RPA_KEY_ID, STEP_ID, data)
3. Creates variable file with saga data
4. Executes robot tests with proper variables

### Manual Execution with SAGA Context
```bash
# Simulate what listener does
robot -d results \
  -v EXEC_ID:123 \
  -v RPA_KEY_ID:456 \
  -v STEP_ID:step-01 \
  --variablefile results/input_variables.json \
  robot/tests/protocolo_devolucao/
```

## Common Patterns

### Dry Run (Validate Syntax)
```bash
robot --dryrun robot/tests/
```

### Re-run Failed Tests
```bash
robot -d results --rerunfailed results/output.xml robot/tests/
```

### Combine Results
```bash
rebot --outputdir results \
  --output output.xml \
  --log log.html \
  --report report.html \
  results/run1/output.xml \
  results/run2/output.xml
```

### Set Timeout
```bash
robot -d results --testtimeout 5m robot/tests/
```

## Troubleshooting

### Verbose Output
```bash
robot -d results --loglevel TRACE robot/tests/
```

### Stop on First Failure
```bash
robot -d results --exitonfailure robot/tests/
```

### Continue on Failure
```bash
robot -d results --exitonerror robot/tests/
```

### Show Console Output
```bash
robot -d results --console verbose robot/tests/
```

